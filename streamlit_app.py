# streamlit_app.py
import html
import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict

import streamlit as st
import lancedb
import pyarrow as pa

from scripts.smoke_ask import ask

st.set_page_config(page_title="The Big Book .chat", layout="wide")

# ============================
# Look: light background, BLACK text (mobile-first)
# ============================
PALETTE = {
    "page_bg": "#F4F5F2",   # soft light
    "card_bg": "#FFFFFF",
    "text": "#000000",
    "muted": "rgba(0,0,0,0.58)",
    "border": "rgba(0,0,0,0.12)",
    "shadow": "0 12px 38px rgba(0,0,0,0.08)",

    # bubbles
    "user_bg": "#F1F1F1",   # neutral (not blue)
    "asst_bg": "#FFFFFF",

    # input
    "input_bg": "#FFFFFF",
}

# ============================
# LanceDB chat storage
# ============================
DB_DIR = "./db/lancedb"
CHAT_TABLE = "chat_messages"


def _db():
    os.makedirs(DB_DIR, exist_ok=True)
    return lancedb.connect(DB_DIR)


def _ensure_chat_table():
    db = _db()
    names = set(db.table_names())
    if CHAT_TABLE in names:
        return db.open_table(CHAT_TABLE)

    schema = pa.schema([
        pa.field("session_id", pa.string()),
        pa.field("ts", pa.timestamp("ms")),
        pa.field("role", pa.string()),     # "user" | "assistant"
        pa.field("content", pa.string()),
    ])

    # Some LanceDB versions choke on create_table(data=[], schema=...)
    dummy = [{
        "session_id": "init",
        "ts": datetime.now(timezone.utc),
        "role": "system",
        "content": "initialization",
    }]
    tbl = db.create_table(CHAT_TABLE, data=dummy, schema=schema)
    try:
        tbl.delete("session_id = 'init'")
    except Exception:
        pass
    return tbl


def _load_messages(session_id: str, limit: int = 400) -> List[Dict[str, str]]:
    tbl = _ensure_chat_table()
    df = tbl.to_pandas()
    if df.empty:
        return []
    df = df[df["session_id"] == session_id].sort_values("ts").tail(limit)
    out: List[Dict[str, str]] = []
    for _, r in df.iterrows():
        out.append({"role": str(r["role"]), "content": str(r["content"])})
    return out


def _append_message(session_id: str, role: str, content: str) -> None:
    tbl = _ensure_chat_table()
    tbl.add([{
        "session_id": session_id,
        "ts": datetime.now(timezone.utc),
        "role": role,
        "content": content,
    }])


# ============================
# Session state (init FIRST)
# ============================
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = _load_messages(st.session_state.chat_session_id, limit=400)

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None  # when set, render Thinking… then run ask()

# Seed welcome once per thread
if not st.session_state.messages:
    welcome = (
        "Hey — ask me anything about the Big Book or the Twelve & Twelve.\n\n"
        "I’ll keep it grounded in your text and list sources at the end."
    )
    st.session_state.messages = [{"role": "assistant", "content": welcome}]
    _append_message(st.session_state.chat_session_id, "assistant", welcome)

# ============================
# CSS (force BLACK text + fix “washed out”)
# ============================
CSS = f"""
<style>
/* hide streamlit chrome */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

/* page */
.stApp {{
  background: {PALETTE["page_bg"]} !important;
  color: {PALETTE["text"]} !important;
}}

.block-container {{
  padding-top: 18px;
  padding-bottom: 84px; /* room above chat input on mobile */
  max-width: 980px;
}}

/* FORCE readable text everywhere (kills the faint/opacity issue) */
html, body, p, span, div, label, li {{
  color: {PALETTE["text"]} !important;
  opacity: 1 !important;
}}

/* header */
.bb-header {{
  margin-bottom: 12px;
}}
.bb-title {{
  font-size: 40px;
  font-weight: 900;
  letter-spacing: -0.02em;
  margin: 0;
}}
.bb-sub {{
  margin-top: 6px;
  font-size: 14px;
  color: {PALETTE["muted"]} !important;
}}
.bb-pill {{
  display:inline-block;
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 999px;
  background: {PALETTE["card_bg"]};
  border: 1px solid {PALETTE["border"]};
  box-shadow: {PALETTE["shadow"]};
  color: {PALETTE["muted"]} !important;
  font-size: 13px;
}}

/* chat area wrapper */
.bb-chatwrap {{
  padding: 6px 0 0 0;
}}

/* bubbles */
.bb-bubble {{
  border-radius: 16px;
  padding: 14px 14px;
  border: 1px solid {PALETTE["border"]};
  box-shadow: 0 10px 28px rgba(0,0,0,0.06);
  white-space: pre-wrap;
  line-height: 1.55;
  color: {PALETTE["text"]} !important;
  opacity: 1 !important;
}}

.bb-user {{
  background: {PALETTE["user_bg"]};
}}

.bb-assistant {{
  background: {PALETTE["asst_bg"]};
}}

/* sources */
.bb-sources-title {{
  margin-top: 12px;
  font-weight: 900;
}}
.bb-sources ul {{
  margin: 8px 0 0 18px;
}}
.bb-sources li {{
  margin: 6px 0;
}}

/* chat input — keep it light + visible on iOS */
div[data-testid="stChatInput"] {{
  position: sticky;
  bottom: 0;
  z-index: 9999;
}}

div[data-testid="stChatInput"] > div {{
  border-radius: 16px !important;
  border: 1px solid {PALETTE["border"]} !important;
  background: {PALETTE["input_bg"]} !important;
  box-shadow: {PALETTE["shadow"]} !important;
}}

div[data-testid="stChatInput"] textarea {{
  color: {PALETTE["text"]} !important;
  opacity: 1 !important;
  font-size: 16px !important;
}}

div[data-testid="stChatInput"] textarea::placeholder {{
  color: rgba(0,0,0,0.35) !important;
  opacity: 1 !important;
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ============================
# Header
# ============================
st.markdown(
    """
<div class="bb-header">
  <div class="bb-title">The Big Book .chat</div>
  <div class="bb-sub">Warm guidance, grounded in the text.</div>
  <div class="bb-pill">Sources are listed at the bottom of each answer.</div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================
# Render chat history
# ============================
st.markdown('<div class="bb-chatwrap">', unsafe_allow_html=True)


def _render_assistant(content: str):
    raw = (content or "").strip()

    # Split body vs Sources (flat list; avoids nested bullet mess)
    if "\nSources:" in raw:
        body, sources = raw.split("\nSources:", 1)
        sources_lines = [s.strip() for s in sources.splitlines() if s.strip()]
    elif raw.startswith("Sources:"):
        body = ""
        sources_lines = [s.strip() for s in raw[len("Sources:"):].splitlines() if s.strip()]
    else:
        body = raw
        sources_lines = []

    with st.chat_message("assistant", avatar="📖"):
        st.markdown(
            f'<div class="bb-bubble bb-assistant">{html.escape(body.strip())}</div>',
            unsafe_allow_html=True
        )

        if sources_lines:
            cleaned = []
            for line in sources_lines:
                line = line.lstrip("-•").strip()
                if line:
                    cleaned.append(line)

            st.markdown('<div class="bb-sources-title">Sources:</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="bb-sources"><ul>'
                + "".join(f"<li>{html.escape(x)}</li>" for x in cleaned)
                + "</ul></div>",
                unsafe_allow_html=True
            )


for m in st.session_state.messages:
    role = m.get("role", "assistant")
    content = m.get("content", "")

    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(
                f'<div class="bb-bubble bb-user">{html.escape(content)}</div>',
                unsafe_allow_html=True
            )
    else:
        _render_assistant(content)

# If there's a pending prompt, show "Thinking…" then process it now
if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt

    with st.chat_message("assistant", avatar="📖"):
        st.markdown('<div class="bb-bubble bb-assistant">Thinking…</div>', unsafe_allow_html=True)
        with st.spinner(""):
            reply = ask(prompt, filters=None, top_k=10)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    _append_message(st.session_state.chat_session_id, "assistant", reply)

    st.session_state.pending_prompt = None
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ============================
# Input (paper-airplane send)
# ============================
user_text = st.chat_input("Message…")


def _queue_prompt(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    _append_message(st.session_state.chat_session_id, "user", prompt)
    st.session_state.pending_prompt = prompt
    st.rerun()


if user_text and user_text.strip():
    _queue_prompt(user_text.strip())

