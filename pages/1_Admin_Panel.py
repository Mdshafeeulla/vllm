# pages/1_Admin_Panel.py — Document Management (Redesigned)
import streamlit as st
from core.pipeline import index_documents
from core.store import store
from core.config import cfg
from core.admin_auth import require_admin_access
from core.monitoring import format_bytes, is_out_of_memory_error, resource_snapshot
from utils.pdf_parser import extract_pdf_text
from utils.image_parser import extract_image_text
from utils.word_parser import extract_word_text
import json
import time

st.set_page_config(page_title="MSU Corp Admin", page_icon="🔑", layout="wide")
require_admin_access()


def show_memory_error(error):
    if not is_out_of_memory_error(error):
        raise error
    st.error(
        "Indexing stopped because the process ran out of memory. The available "
        "memory is not enough to run this workload; increase the server/container "
        "memory and try again."
    )
    st.stop()

# ── Premium CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ── Admin Header ────────────────────────────────── */
    .admin-header {
        text-align: center;
        padding: 2rem 1rem 1.5rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.08) 50%, rgba(236, 72, 153, 0.08) 100%);
        border-radius: 20px;
        border: 1px solid rgba(99, 102, 241, 0.15);
    }

    .admin-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818cf8 0%, #a78bfa 40%, #c084fc 70%, #e879f9 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        letter-spacing: -0.02em;
    }

    .admin-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        font-weight: 400;
    }

    /* ── Stat Cards ──────────────────────────────────── */
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin: 1.5rem 0;
    }

    .stat-card {
        background: linear-gradient(145deg, rgba(30, 30, 50, 0.6), rgba(40, 40, 65, 0.4));
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }

    .stat-card:hover {
        transform: translateY(-3px);
        border-color: rgba(129, 140, 248, 0.3);
        box-shadow: 0 8px 32px rgba(129, 140, 248, 0.1);
    }

    .stat-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }

    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: #e2e8f0;
        line-height: 1.2;
    }

    .stat-label {
        font-size: 0.78rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin-top: 0.3rem;
    }

    /* ── Upload Zone ─────────────────────────────────── */
    .upload-zone {
        background: linear-gradient(145deg, rgba(30, 30, 50, 0.5), rgba(25, 25, 45, 0.5));
        border: 2px dashed rgba(129, 140, 248, 0.25);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
        margin: 1rem 0;
    }

    .upload-zone:hover {
        border-color: rgba(129, 140, 248, 0.5);
        background: linear-gradient(145deg, rgba(35, 35, 55, 0.6), rgba(30, 30, 50, 0.6));
    }

    /* ── Section Headers ─────────────────────────────── */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-size: 1.15rem;
        font-weight: 600;
        color: #e2e8f0;
        margin: 1.5rem 0 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    /* ── Document List Items ─────────────────────────── */
    .doc-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.8rem 1.2rem;
        background: rgba(30, 30, 50, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        margin-bottom: 0.5rem;
        transition: all 0.2s ease;
    }

    .doc-item:hover {
        background: rgba(40, 40, 60, 0.5);
        border-color: rgba(129, 140, 248, 0.2);
    }

    .doc-name {
        font-size: 0.9rem;
        color: #cbd5e1;
        font-weight: 500;
    }

    /* ── Status Badges ───────────────────────────────── */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-success {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.2);
    }

    .badge-info {
        background: rgba(99, 102, 241, 0.15);
        color: #818cf8;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }

    .badge-warning {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.2);
    }

    /* ── Progress Steps ──────────────────────────────── */
    .progress-step {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.6rem 1rem;
        border-radius: 10px;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
        color: #94a3b8;
    }

    .progress-step.active {
        background: rgba(99, 102, 241, 0.1);
        color: #818cf8;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }

    .progress-step.done {
        background: rgba(34, 197, 94, 0.08);
        color: #4ade80;
    }

    /* ── Info Banner ──────────────────────────────────── */
    .info-banner {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        padding: 1rem 1.5rem;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.08));
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 14px;
        margin-bottom: 1.5rem;
        font-size: 0.9rem;
        color: #c4b5fd;
    }

    .info-banner-icon {
        font-size: 1.3rem;
    }

    /* ── Tab styling overrides ────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(15, 15, 30, 0.3);
        padding: 0.4rem;
        border-radius: 14px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 0.6rem 1.5rem;
        font-weight: 500;
    }

    /* ── Footer ──────────────────────────────────────── */
    .admin-footer {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.6rem;
        padding: 1rem;
        margin-top: 2rem;
        color: #475569;
        font-size: 0.8rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* ── Smooth animations ───────────────────────────── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 20px rgba(129, 140, 248, 0.1); }
        50% { box-shadow: 0 0 30px rgba(129, 140, 248, 0.2); }
    }

    .animate-in {
        animation: fadeInUp 0.4s ease-out;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────
st.markdown("""
<div class="admin-header animate-in">
    <div class="admin-title">🔑 MSU Corp Admin Console</div>
    <div class="admin-subtitle">Upload documents · Monitor knowledge base · Manage support content</div>
</div>
""", unsafe_allow_html=True)

# ── Quick Stats ───────────────────────────────────────────────────────
stats = store.get_stats()
total_chunks = sum(stats.values()) if stats else 0
total_depts = len(stats) if stats else 0
total_sources = 0
for dept in cfg.departments:
    total_sources += len(store.list_sources(dept))

st.markdown(f"""
<div class="stat-grid animate-in">
    <div class="stat-card">
        <div class="stat-icon">📦</div>
        <div class="stat-value">{total_chunks:,}</div>
        <div class="stat-label">Total Chunks</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">📄</div>
        <div class="stat-value">{total_sources}</div>
        <div class="stat-label">Documents</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">⚡</div>
        <div class="stat-value">{cfg.embed_dimensions}</div>
        <div class="stat-label">Vector Dims</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────
tab_upload, tab_manage, tab_stats, tab_recycle = st.tabs([
    "📥  Upload Documents",
    "🗂️  Manage Documents",
    "📊  Monitoring & Dashboard",
    "♻️  Recycle Bin",
])

# ━━ Tab 1: Upload ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_upload:
    st.markdown("""
    <div class="info-banner">
        <span class="info-banner-icon">📂</span>
        <span>All documents will be indexed into the <strong>IT Support</strong> knowledge base with ABAC isolation.</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">📎 Document Upload</div>', unsafe_allow_html=True)

    files = st.file_uploader(
        "Upload PDF, Word, TXT, or Image files (DOC, DOCX, PNG, JPG, JPEG, WEBP, BMP)",
        type=["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg", "webp", "bmp"],
        accept_multiple_files=True,
        help="Upload multiple files at once. Limit 200MB per file. Large files are processed in batches to prevent CPU overload.",
    )

    # Show file size info
    if files:
        total_size = sum(f.size for f in files)
        size_str = f"{total_size / (1024*1024):.1f} MB" if total_size > 1024*1024 else f"{total_size / 1024:.1f} KB"
        file_count = len(files)

        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.markdown(f"""
            <div class="stat-card" style="padding: 1rem;">
                <div style="font-size: 1.4rem; font-weight: 700; color: #818cf8;">{file_count}</div>
                <div class="stat-label">Files Selected</div>
            </div>
            """, unsafe_allow_html=True)
        with col_info2:
            st.markdown(f"""
            <div class="stat-card" style="padding: 1rem;">
                <div style="font-size: 1.4rem; font-weight: 700; color: #c084fc;">{size_str}</div>
                <div class="stat-label">Total Size</div>
            </div>
            """, unsafe_allow_html=True)
        with col_info3:
            st.markdown(f"""
            <div class="stat-card" style="padding: 1rem;">
                <div style="font-size: 1.4rem; font-weight: 700; color: #4ade80;">IT Support</div>
                <div class="stat-label">Target Department</div>
            </div>
            """, unsafe_allow_html=True)

        # Large file warning
        for f in files:
            if f.size > 10 * 1024 * 1024:  # > 10MB
                st.warning(
                    f"⚠️ **{f.name}** ({f.size / (1024*1024):.1f} MB) is large. "
                    f"Processing will be done in batches to prevent CPU overload. This may take a few minutes."
                )

    if st.button("🚀 Index Documents", type="primary", disabled=not files, use_container_width=True):
        dept_lower = "it"
        overall_progress = st.progress(0, text="Preparing...")
        status_container = st.container()

        for i, f in enumerate(files):
            fname = f.name.lower()
            file_size_mb = f.size / (1024 * 1024)

            with status_container:
                st.markdown(f"""
                <div class="progress-step active">
                    ⏳ Processing <strong>{f.name}</strong> ({file_size_mb:.1f} MB)...
                </div>
                """, unsafe_allow_html=True)

            step_status = st.empty()

            t0 = time.time()

            try:
                file_bytes = f.read()
                if fname.endswith(".pdf"):
                    step_status.info(f"📄 Extracting text from PDF: {f.name}...")
                    text = extract_pdf_text(file_bytes)
                elif any(fname.endswith(ext) for ext in [".doc", ".docx"]):
                    step_status.info(f"📝 Extracting text from Word: {f.name}...")
                    text = extract_word_text(file_bytes, filename=f.name)
                elif any(fname.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]):
                    step_status.info(f"🖼️ Running OCR on image: {f.name}...")
                    text = extract_image_text(file_bytes)
                else:
                    step_status.info(f"📃 Reading text file: {f.name}...")
                    try:
                        text = file_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        text = file_bytes.decode("latin-1")
            except (MemoryError, RuntimeError) as error:
                show_memory_error(error)

            extract_time = time.time() - t0

            if not text.strip():
                step_status.warning(f"⚠️ {f.name} — no text could be extracted, skipping.")
                continue

            # Show extraction stats
            word_count = len(text.split())
            step_status.info(
                f"📊 Extracted **{word_count:,}** words from **{f.name}** "
                f"in {extract_time:.1f}s — now indexing..."
            )

            # Index with batched processing
            t1 = time.time()

            def report_index_progress(phase, current, total):
                snapshot = resource_snapshot()
                step_status.info(
                    f"Indexing {f.name} — {phase}: {current}/{total} · "
                    f"CPU {snapshot['indexing']['cpu_percent']:.1f}% · "
                    f"RAM {snapshot['indexing']['memory_mb']:.0f} MB"
                )

            try:
                n = index_documents(
                    text,
                    department=dept_lower,
                    source=f.name,
                    progress_callback=report_index_progress,
                )
            except (MemoryError, RuntimeError) as error:
                show_memory_error(error)
            index_time = time.time() - t1

            step_status.empty()

            st.success(
                f"✅ **{f.name}** → **{n}** chunks indexed "
                f"({extract_time:.1f}s extract + {index_time:.1f}s index)"
            )

            overall_progress.progress(
                (i + 1) / len(files),
                text=f"Completed {i + 1}/{len(files)} files"
            )

        overall_progress.empty()
        st.balloons()
        st.markdown("""
        <div class="badge badge-success" style="padding: 0.5rem 1.2rem; font-size: 0.9rem;">
            ✅ All documents indexed successfully!
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── JSON Ingestion ────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔗 Direct JSON Ingestion</div>', unsafe_allow_html=True)
    st.caption("Paste JSON containing `title` (optional) and `content` fields to auto-index into IT Support.")

    json_input = st.text_area(
        "Paste JSON here",
        height=200,
        placeholder='[\n  {\n    "id": "it_guide_001",\n    "title": "VPN Troubleshooting Guide",\n    "content": "To connect to corporate VPN..."\n  }\n]'
    )

    if st.button("🚀 Index JSON", type="primary", disabled=not json_input.strip(), use_container_width=True):
        try:
            data = json.loads(json_input)
            if isinstance(data, dict):
                data = [data]

            if not isinstance(data, list):
                st.error("JSON must be an object or an array of objects.")
            else:
                progress_bar = st.progress(0)
                status = st.empty()
                success_count = 0

                for i, item in enumerate(data):
                    dept = str(item.get("department", "it")).lower().strip() or "it"
                    title = str(item.get("title", item.get("id", f"json_doc_{i}")))
                    content = str(item.get("content", ""))

                    status.info(f"Processing {title}...")

                    if not content.strip():
                        st.warning(f"⚠️ **{title}** — missing 'content', skipping.")
                        continue

                    def report_json_index_progress(phase, current, total):
                        snapshot = resource_snapshot()
                        status.info(
                            f"Indexing {title} — {phase}: {current}/{total} · "
                            f"CPU {snapshot['indexing']['cpu_percent']:.1f}% · "
                            f"RAM {snapshot['indexing']['memory_mb']:.0f} MB"
                        )

                    n = index_documents(
                        content,
                        department=dept,
                        source=title,
                        progress_callback=report_json_index_progress,
                    )
                    st.success(f"✅ **{title}** → {n} chunks indexed")
                    success_count += 1

                    progress_bar.progress((i + 1) / len(data))

                status.empty()
                progress_bar.empty()
                if success_count > 0:
                    st.balloons()
        except (MemoryError, RuntimeError) as error:
            show_memory_error(error)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format: {e}")

# ━━ Tab 2: Manage ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_manage:
    st.markdown('<div class="section-header">🗂️ Indexed Documents by Department</div>', unsafe_allow_html=True)

    has_any = False
    for dept in cfg.departments:
        sources = store.list_sources(dept)
        if not sources:
            continue
        has_any = True

        with st.expander(f"🔒 **{dept.upper()}** — {len(sources)} document(s)", expanded=True):
            for src in sources:
                col_name, col_del = st.columns([4, 1])
                col_name.markdown(f"📄 `{src}`")
                if col_del.button("🗑️ Remove", key=f"del_{dept}_{src}", type="secondary"):
                    store.delete_source(dept, src)
                    st.success(f"Deleted '{src}' from {dept.upper()}")
                    st.rerun()

            st.divider()
            if st.button(f"🗑️ Delete ALL {dept.upper()} documents", key=f"del_all_{dept}", type="secondary"):
                store.delete_department(dept)
                st.warning(f"All documents for {dept.upper()} have been deleted.")
                st.rerun()

    if not has_any:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem; color: #64748b;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📭</div>
            <div style="font-size: 1.1rem; font-weight: 500;">No documents indexed yet</div>
            <div style="font-size: 0.85rem; margin-top: 0.5rem;">Go to the Upload tab to add documents to the knowledge base.</div>
        </div>
        """, unsafe_allow_html=True)

# ━━ Tab 3: Recycle Bin ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_recycle:
    st.markdown('<div class="section-header">♻️ Recover deleted documents</div>', unsafe_allow_html=True)
    deleted_documents = store.list_recycle_bin()
    if not deleted_documents:
        st.info("The recycle bin is empty. Documents removed from the index will appear here.")
    else:
        st.caption(
            "Documents removed from the knowledge base are retained here until restored. "
            "Restoring is blocked if a document with the same name is already indexed."
        )
        for item in deleted_documents:
            col_document, col_deleted, col_restore = st.columns([3, 2, 1])
            col_document.markdown(
                f"📄 **{item['source']}** · {item['department'].upper()}"
            )
            col_deleted.caption(f"Deleted: {item['deleted_at']}")
            if col_restore.button(
                "Restore",
                key=f"restore_{item['deletion_id']}",
                use_container_width=True,
            ):
                try:
                    store.restore_source(item["deletion_id"])
                except ValueError as error:
                    st.warning(str(error))
                else:
                    st.success(f"Restored '{item['source']}'.")
                    st.rerun()

# ━━ Tab 3: Dashboard ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_stats:
    st.markdown('<div class="section-header">🖥️ Server resource monitoring</div>', unsafe_allow_html=True)
    if st.button("Refresh system metrics", key="refresh_system_metrics"):
        st.rerun()

    resources = resource_snapshot()
    memory_percent = (
        resources["memory_used_bytes"] / resources["memory_total_bytes"]
        if resources["memory_total_bytes"]
        else 0.0
    )
    disk_percent = (
        resources["disk_used_bytes"] / resources["disk_total_bytes"]
        if resources["disk_total_bytes"]
        else 0.0
    )
    cpu_cols = st.columns(3)
    cpu_cols[0].metric("Logical CPU cores", resources["cpu_cores"])
    cpu_cols[1].metric("Cores available to process", resources["cpu_cores_available"])
    cpu_cols[2].metric("System CPU utilization", f"{resources['system_cpu_percent']:.1f}%")

    memory_cols = st.columns(3)
    memory_cols[0].metric("Total / effective RAM", format_bytes(resources["memory_total_bytes"]))
    memory_cols[1].metric("RAM in use", format_bytes(resources["memory_used_bytes"]))
    memory_cols[2].metric("RAM remaining", format_bytes(resources["memory_available_bytes"]))
    st.progress(min(memory_percent, 1.0), text=f"Memory use: {memory_percent:.1%}")

    disk_cols = st.columns(3)
    disk_cols[0].metric("Storage capacity", format_bytes(resources["disk_total_bytes"]))
    disk_cols[1].metric("Storage used", format_bytes(resources["disk_used_bytes"]))
    disk_cols[2].metric("Storage remaining", format_bytes(resources["disk_free_bytes"]))
    st.progress(min(disk_percent, 1.0), text=f"Storage use: {disk_percent:.1%}")
    st.caption(
        f"Storage is measured on the filesystem containing `{cfg.db_path}`. "
        "RAM reflects the container limit when Linux cgroup limits are available."
    )

    indexing = resources["indexing"]
    st.markdown("#### Indexing computation")
    if indexing["active"]:
        st.info(
            f"Indexing **{indexing['source']}** · phase: **{indexing['phase']}** · "
            f"elapsed: {indexing['elapsed_seconds']:.1f}s"
        )
    else:
        st.caption(
            f"Most recent job: {indexing['source'] or 'None'} · "
            f"status: {indexing['status']}"
        )
    index_cols = st.columns(3)
    index_cols[0].metric("App CPU use", f"{indexing['cpu_percent']:.1f}%")
    index_cols[1].metric("App RAM use", f"{indexing['memory_mb']:.0f} MB")
    index_cols[2].metric("Peak RAM during indexing", f"{indexing['peak_memory_mb']:.0f} MB")
    st.caption(
        f"Peak app CPU during indexing: {indexing['peak_cpu_percent']:.1f}%. "
        "Process CPU can exceed 100% when multiple cores are used."
    )
    if indexing["status"] == "Out of memory":
        st.error(
            "The last indexing job ran out of memory. Available memory was not "
            "enough to run the workload; increase server/container memory before retrying."
        )

    st.divider()
    st.markdown('<div class="section-header">📊 Knowledge Base Analytics</div>', unsafe_allow_html=True)

    if stats:
        # Metrics row
        total_chunks = sum(stats.values())
        total_depts = len(stats)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Chunks", f"{total_chunks:,}")
        m2.metric("Active Departments", total_depts)
        m3.metric("Vector Dimensions", cfg.embed_dimensions)

        st.divider()

        # Bar chart
        import pandas as pd
        df = pd.DataFrame(
            [{"Department": k.upper(), "Chunks": v} for k, v in stats.items()]
        ).sort_values("Chunks", ascending=False)

        st.bar_chart(df.set_index("Department"))

        # Table
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem; color: #64748b;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
            <div style="font-size: 1.1rem; font-weight: 500;">No analytics data available</div>
            <div style="font-size: 0.85rem; margin-top: 0.5rem;">Index some documents to see statistics here.</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # System info
    st.markdown(f"""
    <div class="admin-footer">
        <span>⚙️ Embedder: <code>{cfg.embed_model}</code></span>
        <span>·</span>
        <span>📐 Dims: {cfg.embed_dimensions} (MRL)</span>
        <span>·</span>
        <span>💾 DB: LanceDB</span>
        <span>·</span>
        <span>🤖 LLM: {cfg.ollama_model}</span>
    </div>
    """, unsafe_allow_html=True)
