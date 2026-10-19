# core/store.py
import uuid
from datetime import datetime, timezone

import lancedb
import numpy as np
import pyarrow as pa

from core.config import cfg
from utils.logger import log

# ── Schema ────────────────────────────────────────────────────────────
_SCHEMA = pa.schema([
    pa.field("text",       pa.utf8()),
    pa.field("department", pa.utf8()),   # ABAC isolation key
    pa.field("source",     pa.utf8()),   # original filename
    pa.field("chunk_idx",  pa.int32()),
    pa.field("vector",     pa.list_(pa.float32(), cfg.embed_dimensions)),
])
_RECYCLE_SCHEMA = pa.schema([
    *_SCHEMA,
    pa.field("deletion_id", pa.utf8()),
    pa.field("deleted_at", pa.utf8()),
])


class VectorStore:
    """
    LanceDB-backed persistent vector store with ABAC department isolation.
    Every query is hard-filtered by department at the DB level.
    """

    def __init__(self):
        self.db = lancedb.connect(cfg.db_path)

    # ── Internal helpers ──────────────────────────────────────────────

    def _get_table(self):
        if cfg.table_name in self.db.table_names():
            return self.db.open_table(cfg.table_name)
        # Create empty table with schema on first use
        return self.db.create_table(cfg.table_name, schema=_SCHEMA)

    def _get_recycle_table(self):
        name = f"{cfg.table_name}_recycle_bin"
        if name in self.db.table_names():
            return self.db.open_table(name)
        return self.db.create_table(name, schema=_RECYCLE_SCHEMA)

    @staticmethod
    def _quote_filter_value(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    @staticmethod
    def _row_records(frame, deletion_id: str, deleted_at: str) -> list[dict]:
        records = []
        for _, row in frame.iterrows():
            records.append({
                "text": row["text"],
                "department": row["department"],
                "source": row["source"],
                "chunk_idx": int(row["chunk_idx"]),
                "vector": np.asarray(row["vector"], dtype=np.float32).tolist(),
                "deletion_id": deletion_id,
                "deleted_at": deleted_at,
            })
        return records

    # ── Public API ────────────────────────────────────────────────────

    def add_documents(
        self,
        chunks: list[dict],
        embeddings: np.ndarray,
        department: str,
        source: str,
    ) -> int:
        """
        Index documents under a specific department.
        APPENDS to existing table — other departments are not affected.
        """
        records = [
            {
                "text":       c["text"],
                "department": department.lower(),
                "source":     source,
                "chunk_idx":  c["chunk_idx"],
                "vector":     e.tolist(),
            }
            for c, e in zip(chunks, embeddings)
        ]
        tbl = self._get_table()
        tbl.add(records)
        log.info(f"Indexed {len(records)} chunks — dept={department}, source={source}")
        return len(records)

    def search(
        self,
        query_vec: np.ndarray,
        department: str,
        top_k: int = None,
    ) -> list[dict]:
        """
        ABAC-enforced ANN search.
        The department filter is ALWAYS applied — no user can bypass it.
        """
        top_k = top_k or cfg.top_k
        dept = department.lower()
        tbl = self._get_table()

        results = (
            tbl.search(query_vec.tolist())
               .where(f"department = '{dept}'")   # ← ABAC enforcement
               .limit(top_k * 3)                  # over-fetch for BM25 re-rank
               .to_pandas()
        )

        if results.empty:
            return []

        return [
            {
                "text":       row["text"],
                "department": row["department"],
                "source":     row["source"],
                "score":      float(1.0 - row.get("_distance", 0.0)),
            }
            for _, row in results.iterrows()
        ]

    def delete_department(self, department: str):
        """Move all documents for a department to the recycle bin."""
        dept = department.lower()
        for source in self.list_sources(dept):
            self.delete_source(dept, source)
        log.info(f"Moved all documents for department='{dept}' to the recycle bin")

    def delete_source(self, department: str, source: str):
        """Move one document from the active index into the recycle bin."""
        dept = department.lower()
        tbl = self._get_table()
        source_value = self._quote_filter_value(source)
        filter_expr = (
            f"department = {self._quote_filter_value(dept)} "
            f"AND source = {source_value}"
        )
        frame = tbl.search().where(filter_expr).to_pandas()
        if frame.empty:
            return

        deletion_id = str(uuid.uuid4())
        deleted_at = datetime.now(timezone.utc).isoformat()
        recycle = self._get_recycle_table()
        recycle.add(self._row_records(frame, deletion_id, deleted_at))
        tbl.delete(filter_expr)
        log.info(
            f"Moved source='{source}' from department='{dept}' to recycle bin "
            f"(deletion_id={deletion_id})"
        )

    def list_recycle_bin(self) -> list[dict]:
        """Return restorable document deletion records."""
        name = f"{cfg.table_name}_recycle_bin"
        if name not in self.db.table_names():
            return []
        frame = self.db.open_table(name).search().select(
            ["deletion_id", "department", "source", "deleted_at"]
        ).to_pandas()
        if frame.empty:
            return []
        return [
            {
                "deletion_id": deletion_id,
                "department": department,
                "source": source,
                "deleted_at": deleted_at,
            }
            for (deletion_id, department, source, deleted_at), _ in frame.groupby(
                ["deletion_id", "department", "source", "deleted_at"]
            )
        ]

    def restore_source(self, deletion_id: str):
        """Restore a previously deleted document to the active index."""
        recycle = self._get_recycle_table()
        filter_expr = (
            f"deletion_id = {self._quote_filter_value(deletion_id)}"
        )
        frame = recycle.search().where(filter_expr).to_pandas()
        if frame.empty:
            raise ValueError("The selected recycle-bin entry no longer exists.")

        department = str(frame.iloc[0]["department"])
        source = str(frame.iloc[0]["source"])
        active_filter = (
            f"department = {self._quote_filter_value(department)} "
            f"AND source = {self._quote_filter_value(source)}"
        )
        active = self._get_table().search().where(active_filter).select(
            ["source"]
        ).to_pandas()
        if not active.empty:
            raise ValueError(
                f"'{source}' is already indexed in {department}; remove the active "
                "copy before restoring this version."
            )

        records = [
            {
                "text": row["text"],
                "department": row["department"],
                "source": row["source"],
                "chunk_idx": int(row["chunk_idx"]),
                "vector": np.asarray(row["vector"], dtype=np.float32).tolist(),
            }
            for _, row in frame.iterrows()
        ]
        self._get_table().add(records)
        recycle.delete(filter_expr)
        log.info(
            f"Restored source='{source}' to department='{department}' "
            f"(deletion_id={deletion_id})"
        )

    def list_sources(self, department: str) -> list[str]:
        """Return unique document filenames indexed for a department."""
        dept = department.lower()
        try:
            tbl = self._get_table()
            # Select only 'source' column to prevent loading heavy vector arrays into pandas memory
            df = tbl.search().where(f"department = '{dept}'").select(["source"]).to_pandas()
            if df.empty:
                return []
            return sorted(df["source"].unique().tolist())
        except Exception:
            return []

    def get_stats(self) -> dict:
        """Return chunk counts per department (for admin dashboard)."""
        try:
            tbl = self._get_table()
            df = tbl.search().select(["department"]).to_pandas()
            if df.empty:
                return {}
            return df["department"].value_counts().to_dict()
        except Exception:
            return {}

    def is_empty(self, department: str) -> bool:
        """Check whether a department has any indexed documents."""
        return len(self.list_sources(department)) == 0


# Singleton — import and use everywhere
store = VectorStore()
