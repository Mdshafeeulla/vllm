# 🏢 Enterprise RAG — Multi-Department Knowledge Assistant

A **local-first**, **privacy-preserving** RAG (Retrieval-Augmented Generation) system that lets different company departments query their own documents via an LLM — with **strict department-level data isolation (ABAC)**.

> **No data leaves your machine.** Everything runs locally; embeddings use CUDA when available and CPU otherwise.

---

## ✨ Features

- 🔒 **ABAC Data Isolation** — HR can't see Finance docs. Enforced at the DB layer.
- 🧠 **Hybrid Retrieval** — ANN vector search + BM25 keyword re-ranking
- ⚡ **Sub-2s Latency** — GPU-accelerated embeddings + quantized LLM
- 💾 **Persistent Storage** — LanceDB survives restarts (no re-indexing!)
- 🎯 **MRL Embeddings** — 256-dim Matryoshka embeddings for fast ANN search
- 📄 **PDF + TXT Upload** — PyMuPDF for fast, accurate text extraction
- 💬 **Chat Interface** — Multi-turn Q&A with source attribution
- 📋 **Copy Chat History** — Copy the full current conversation as a transcript
- 🔑 **Admin Panel** — Upload docs, manage departments, view stats

---

## 🖥️ Hardware Requirements

| Component | Minimum |
|---|---|
| GPU | Optional; NVIDIA GPU for acceleration |
| RAM | 16 GB recommended; CPU inference uses more time and memory |
| CUDA | Only required for the optional NVIDIA Docker setup |
| Disk | ~10 GB (models + DB) |

---

## 🐳 Run with Docker

Docker Compose starts the Streamlit app and Ollama. The default image installs CPU-only PyTorch and runs on systems without a GPU.

```bash
docker compose up --build -d
docker compose exec ollama ollama pull llama3.2:1b
```

Open `http://localhost:8501`. The LanceDB files are persisted under `data/`, and downloaded Ollama models are stored in a named Docker volume. To stop the services, run `docker compose down`; this keeps both sets of data.

### Admin login, monitoring, and recovery

The admin console and its **Monitoring & Dashboard** tab require the same login.
The first visit to **Admin Console** displays an in-app form to create the admin
account; enter `MSU` as the username and choose and confirm an admin password.
No terminal or secrets-file setup is needed. The app stores a salted password
hash in `data/admin_account.json`, not the plain-text password. This file is
excluded from Git and persists with the existing `data/` Docker volume. Protect
and back up the data directory; deleting the account file requires creating the
admin account again on the next visit.

The monitoring dashboard reports CPU cores, system CPU use, effective/available
RAM, app CPU and RAM use during indexing, indexing peaks/status, and the capacity
of the filesystem containing the LanceDB database. Linux container RAM limits
are used when cgroup data is available. Refresh the dashboard to update live
system readings. An out-of-memory failure is reported with guidance to increase
server or container memory.

### Chat context window

The Chat sidebar has a **Context window (tokens)** control, defaulting to 8,192.
Raise it when the model needs more document or conversation context; this
increases Ollama RAM/VRAM requirements, and the selected model/server must support
the requested size. RAG requests include retrieved document passages and recent
chat turns, within separate budgets so there is still room for the answer.

Removing documents from the admin console moves their indexed content to the
recycle bin, where it can be restored unless a same-named document is already
active. The app does not retain the original uploaded file bytes; the recycle
bin restores the document's indexed content. Protect the `data/` directory with
regular backups to recover from manual deletion of database files or host data.

For NVIDIA acceleration, install the NVIDIA Container Toolkit and use a Docker runtime that supports GPU reservations. Build and start with the GPU override:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec ollama ollama pull llama3.2:1b
```

The embedding model selects CUDA when it is available and falls back to CPU otherwise. The default Docker configuration is CPU-only; use the GPU override only on a host configured for NVIDIA containers.

To run the prebuilt Linux image in a VMware Linux VM without rebuilding, copy `enterprise-rag-linux-amd64.tar` and `docker-compose.yml` to the VM, then run:

```bash
docker load -i enterprise-rag-linux-amd64.tar
docker compose up --no-build -d
docker compose exec ollama ollama pull llama3.2:1b
```

The archive is about 808 MB. The VM needs Docker Engine and the Docker Compose plugin; Ollama will be pulled automatically by Compose.

## 🚀 Local Quick Start

### 1. Clone & Enter Project

```bash
cd e:\project\enterprise-rag
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install PyTorch

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

> For NVIDIA acceleration, install `torch` and `torchvision` from the matching CUDA index instead. Check CUDA availability with:
> ```bash
> python -c "import torch; print(torch.cuda.is_available())"
> ```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Pull an LLM via Ollama

Make sure [Ollama](https://ollama.com) is installed and running, then:

```bash
ollama pull qwen2.5:7b-instruct-q4_K_M
```

Other options:
```bash
ollama pull mistral           # Smart answers, but need more RAM
ollama pull phi4-mini          # Fastest, lowest VRAM
ollama pull gemma3:4b          # Google, balanced
```

### 6. Run the App

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## 📖 How to Use

### As Admin

1. Open the app → click **"Open Admin →"**
2. Select a **department** from the dropdown (e.g., HR, Finance, IT)
3. Upload **PDF or TXT** files containing department documents
4. Click **"Index Documents"** — chunks are embedded and stored in LanceDB
5. View stats and manage documents in the other tabs

### As Employee

1. Open the app → click **"Open Chat →"**
2. Select **your department** from the sidebar
3. Ask questions in natural language
4. The system retrieves relevant chunks **only from your department's documents**
5. The LLM generates a grounded answer; source chunks are available separately

The support documents are used as internal knowledge: the assistant should explain
the relevant answer or steps directly in chat rather than asking employees to read
the documents. Source chunks remain available separately when a user wants to check
the supporting material.

---

## 🔒 Security Model (ABAC)

Every document chunk in LanceDB carries a `department` metadata tag:

```
┌────────────────────────────────────────────────┐
│  User selects: department = "finance"          │
│                                                │
│  → LanceDB query:                              │
│     WHERE department = 'finance'   ← ENFORCED  │
│                                                │
│  → Only finance chunks reach the LLM           │
│  → HR, IT, Legal = physically unreachable      │
└────────────────────────────────────────────────┘
```

This filter is applied **server-side** in `core/store.py`. No user input can bypass it.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Streamlit UI                      │
│  ┌─────────────┐    ┌────────────────────────────┐  │
│  │ Admin Panel  │    │ Chat (dept-scoped)         │  │
│  └──────┬───────┘    └──────────┬─────────────────┘  │
│         │                       │                    │
│  ┌──────▼───────────────────────▼─────────────────┐  │
│  │             core/pipeline.py                    │  │
│  │  index_documents()    query_department()        │  │
│  └──┬──────┬──────┬──────┬──────┬─────────────────┘  │
│     │      │      │      │      │                    │
│  chunker embedder store retriever llm                │
│     │      │      │      │      │                    │
│     │   nomic   LanceDB  BM25  Ollama                │
│     │   (CUDA)  (ABAC)  re-rank (local)              │
└─────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
enterprise-rag/
├── app.py                  # Home page (role selector)
├── pages/
│   ├── 1_Admin_Panel.py    # Upload & manage documents
│   └── 2_Chat.py           # Employee Q&A chat
├── core/
│   ├── config.py           # Central configuration
│   ├── embedder.py         # nomic-embed-text-v1.5 + CUDA + MRL
│   ├── chunker.py          # Word-based overlapping chunks
│   ├── store.py            # LanceDB + ABAC filtering
│   ├── retriever.py        # Hybrid ANN + BM25 re-ranking
│   ├── llm.py              # Ollama wrapper
│   ├── pipeline.py         # Orchestrator
│   └── prompt_builder.py   # Department-aware prompts
├── utils/
│   ├── pdf_parser.py       # PyMuPDF text extraction
│   └── logger.py           # Structured logging
├── data/
│   └── lancedb/            # Persistent vector store (auto-created)
├── requirements.txt
└── .gitignore
```

---

## ⚙️ Configuration

Edit `core/config.py` to customize:

| Setting | Default | Description |
|---|---|---|
| `departments` | hr, finance, it, sales, ... | Company departments |
| `embed_dimensions` | 256 | MRL truncation (256 of 768) |
| `chunk_size` | 300 words | Words per chunk |
| `top_k` | 6 | Chunks retrieved per query |
| `semantic_weight` | 0.65 | ANN vs BM25 balance |
| `ollama_model` | qwen2.5:7b-instruct-q4_K_M | Default LLM |
| `ollama_num_ctx` | 1024 | Ollama context window in tokens; lower values use less RAM/VRAM, but may not fit long prompts |

---

## 🔧 Tech Stack

| Component | Technology |
|---|---|
| LLM | Ollama (Mistral Q4) |
| Embedder | nomic-embed-text-v1.5 (CUDA when available, otherwise CPU) |
| Vector DB | LanceDB (embedded, Rust) |
| Search | Hybrid ANN + BM25 |
| Filtering | ABAC via LanceDB metadata |
| PDF Parser | PyMuPDF |
| UI | Streamlit |

---

## 📝 License

MIT
