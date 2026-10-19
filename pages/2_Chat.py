# pages/2_Chat.py — Employee Q&A Interface (Redesigned)
import threading
import time
import streamlit as st
from core.pipeline import query_department, is_greeting
from core.store import store
from core.config import cfg
from core.llm import prewarm_model

st.set_page_config(page_title="MSU Corp Support", page_icon="🛡️", layout="wide")

# ── Premium Styles ────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ── Chat Header ─────────────────────────────────── */
    .chat-header {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        padding: 1rem 0;
        margin-bottom: 0.5rem;
    }

    .chat-header-title {
        font-size: 1.6rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }

    .chat-header-sub {
        font-size: 0.82rem;
        color: #64748b;
        margin-top: 0.1rem;
    }

    /* ── Department Badge ────────────────────────────── */
    .dept-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.12));
        border: 1px solid rgba(99, 102, 241, 0.25);
        color: #a5b4fc;
        padding: 0.35rem 0.85rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* ── Sidebar Styling ─────────────────────────────── */
    .sidebar-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 0.3rem;
    }

    .sidebar-section {
        background: rgba(30, 30, 50, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 12px;
        padding: 0.8rem;
        margin: 0.5rem 0;
    }

    .sidebar-section-title {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .doc-entry {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0;
        font-size: 0.78rem;
        color: #94a3b8;
    }

    .doc-entry-icon {
        font-size: 0.7rem;
        color: #4ade80;
    }

    /* ── Online Status ───────────────────────────────── */
    .online-status {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.75rem;
        color: #4ade80;
        font-weight: 500;
    }

    .online-dot {
        width: 6px;
        height: 6px;
        background: #4ade80;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.3); }
    }

    /* ── Metadata pills ──────────────────────────────── */
    .meta-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-top: 0.5rem;
    }

    .meta-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.2rem 0.6rem;
        background: rgba(30, 30, 50, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 20px;
        font-size: 0.7rem;
        color: #64748b;
    }

    /* ── Footer ──────────────────────────────────────── */
    .sidebar-footer {
        padding: 0.8rem 0;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        margin-top: 1rem;
    }

    .sidebar-footer-text {
        font-size: 0.72rem;
        color: #475569;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar: Department & Settings ────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 0.5rem 0;">
        <div class="sidebar-title">🛡️ MSU Corp Support</div>
        <div class="online-status"><div class="online-dot"></div> Online & Ready</div>
    </div>
    """, unsafe_allow_html=True)

    department = "it"

    st.markdown(
        '<div class="dept-badge">🔒 IT SUPPORT</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown('<div class="sidebar-section-title">⚙️ Model Settings</div>', unsafe_allow_html=True)
    model = st.selectbox("LLM Model", cfg.available_models, label_visibility="collapsed")
    top_k = st.slider("Chunks to retrieve", min_value=3, max_value=15, value=cfg.top_k)
    context_window = st.slider(
        "Context window (tokens)",
        min_value=2048,
        max_value=32768,
        step=1024,
        value=min(max(cfg.ollama_num_ctx, 2048), 32768),
        help=(
            "Larger windows let the model use more document and chat history, "
            "but require more RAM/VRAM from the Ollama server."
        ),
    )

    # Pre-warm model in background thread when selected
    if (
        st.session_state.get("active_model") != model
        or st.session_state.get("active_context_window") != context_window
    ):
        st.session_state.active_model = model
        st.session_state.active_context_window = context_window
        threading.Thread(
            target=prewarm_model,
            args=(model, context_window),
            daemon=True,
        ).start()

    st.divider()

    # Show indexed support documents
    sources = store.list_sources(department)
    if sources:
        st.markdown('<div class="sidebar-section-title">📚 Knowledge Base</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        for s in sources:
            st.markdown(f"""
            <div class="doc-entry">
                <span class="doc-entry-icon">●</span>
                <span>{s}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning(
            "⚠️ No support documents indexed yet.\n\n"
            "Ask an Admin to upload FAQs, manuals, and guides first."
        )

    st.markdown(f"""
    <div class="sidebar-footer">
        <div class="sidebar-footer-text">
            🤖 Model: <code>{model}</code><br>
            🔒 Powered by MSU Corp Knowledge Base<br>
            ⏰ Available 24/7 · No ticket needed
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Main Chat Area ────────────────────────────────────────────────────
st.markdown("""
<div class="chat-header">
    <div>
        <div class="chat-header-title">🛡️ MSU Corp Support</div>
        <div class="chat-header-sub">AI-powered L1 customer support · Describe your issue and get instant help</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Session state for chat history ────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "active_dept" not in st.session_state:
    st.session_state.active_dept = department

# Clear chat when department changes
if st.session_state.active_dept != department:
    st.session_state.messages = []
    st.session_state.active_dept = department

# Make the current conversation easy to copy as a single transcript.
if st.session_state.messages:
    transcript = "\n\n".join(
        f"{msg['role'].capitalize()}:\n{msg['content']}"
        for msg in st.session_state.messages
    )
    with st.expander("📋 Copy conversation"):
        st.caption("Use the copy icon on the transcript to copy the full conversation.")
        st.code(transcript, language=None)

# Render existing messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "metadata" in msg and msg["metadata"]:
            st.caption(msg["metadata"])

# ── Chat Input ────────────────────────────────────────────────────────
if prompt := st.chat_input("Describe your issue or ask a question..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        # If it's not a greeting and no docs indexed, show warning
        from core.instant_responses import get_instant_response as _check_instant
        is_instant_query = _check_instant(prompt) is not None

        if not is_instant_query and not is_greeting(prompt) and store.is_empty(department):
            answer = (
                "⚠️ There are no documents indexed for **IT Support** yet. "
                "Please ask an Admin to upload documents first."
            )
            st.warning(answer)
            metadata_str = ""
        else:
            try:
                t0 = time.perf_counter()

                # ── Instant cache queries get no spinner (already sub-ms) ──
                if is_instant_query:
                    result = query_department(
                        question=prompt,
                        department=department,
                        model=model,
                        top_k=top_k,
                        num_ctx=context_window,
                        stream=False,
                        history=st.session_state.messages[:-1],
                    )
                else:
                    spinner_msg = (
                        "💬 Preparing a response..."
                        if is_greeting(prompt)
                        else "🔍 Searching the database..."
                    )
                    with st.spinner(spinner_msg):
                        result = query_department(
                            question=prompt,
                            department=department,
                            model=model,
                            top_k=top_k,
                            num_ctx=context_window,
                            stream=True,
                            history=st.session_state.messages[:-1],
                        )

                # ── Render answer ──────────────────────────────────────────
                if result.get("is_instant"):
                    answer = result["answer"]
                    st.markdown(answer)
                elif is_instant_query:
                    answer = result.get("answer", "")
                    st.markdown(answer)
                elif result.get("stream") is not None:
                    answer = st.write_stream(result["stream"])
                else:
                    answer = result.get("answer", "")
                    st.markdown(answer)

                total_latency_ms = int((time.perf_counter() - t0) * 1000)

                # ── Metadata bar ───────────────────────────────────────────
                chunks_count = len(result.get("chunks", []))
                if result.get("is_instant"):
                    chunks_label = "⚡ Instant"
                    model_label = "cache"
                elif chunks_count > 0:
                    chunks_label = f"📄 {chunks_count} chunks"
                    model_label = result["model"]
                else:
                    chunks_label = "💬 Conversational"
                    model_label = result["model"]

                metadata_str = (
                    f"⏱ {total_latency_ms}ms · "
                    f"🔒 IT SUPPORT · "
                    f"🤖 {model_label} · "
                    f"🧠 {context_window:,} ctx · "
                    f"{chunks_label}"
                )
                st.caption(metadata_str)

                # ── Source chunks (only for RAG answers) ──────────────────
                if result.get("chunks"):
                    with st.expander("🔍 View Source Chunks"):
                        for i, chunk in enumerate(result["chunks"], 1):
                            st.markdown(
                                f"**Chunk {i}** · `{chunk['source']}` · "
                                f"Score: `{chunk['score']:.3f}`"
                            )
                            st.markdown(
                                f"> {chunk['text'][:400]}{'...' if len(chunk['text']) > 400 else ''}"
                            )
                            if i < len(result["chunks"]):
                                st.divider()

            except ValueError as e:
                answer = f"⚠️ {str(e)}"
                st.warning(answer)
                metadata_str = ""
            except RuntimeError as e:
                answer = f"❌ {str(e)}"
                st.error(answer)
                metadata_str = ""

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "metadata": metadata_str if metadata_str else None,
        })
