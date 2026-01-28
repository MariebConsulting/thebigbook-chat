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
# Palette — LIGHT, readable, mobile-first
# ============================
PALETTE = {
    "page_bg": "#F4F5F2",
    "card_bg": "#FFFFFF",
    "text": "#000000",
    "muted": "rgba(0,0,0,0.55)",
    "border": "rgba(0,0,0,0.12)",
    "shadow": "0 10px 28px rgba(0,0,0,0.08)",

    "user_bg": "#EEF1F6",
    "asst_bg": "#FFFFFF",
}

# ============================
# LanceDB
# ============================
DB_DIR = "./db/lancedb"
CHAT_TABLE = "chat_messages"

def _db():
    os.makedirs(DB_DIR, exist_ok=True)
    return lancedb.connect(DB_DIR)

def _ensure_chat_table():
    db = _db()
    if CHAT_TABLE in set(db.table_names()):
        return db.open_table(CHAT_TABLE)

    schema = pa.schema([
        pa.field("session_id", pa.string()),
        pa.field("ts", pa.timestamp("ms")),
        pa.field("role", pa.string()),
        pa.field("content", pa.string()),
    ])

    dummy = [{
        "session_id": "init",
        "ts": datetime.now(timezone.utc),
        "role": "system",
        "content": "init",
    }]
    tbl = db.create_table(CHAT_TABLE, data=dummy, schema=schema)
    try:
        tbl.delete("session_id = 'init'")
    except Exception:
        pass
    return tbl

def _load_messages(session_id: str, limit: int = 400) -> List[Dict[str, str]]:
    df = _ensure_chat_table().to_pandas()
    if df.empty:
        return []
    df = df[df["session_id"] == session_id].sort_values("ts").tail(limit)
    return [{"role": r["role"], "content": r["content"]} for _, r in df.iterrows()]

def _append_message(session_id: str, role: str, content: str):
    _ensure_chat_table().add([{
        "session_id": session_id,
        "ts": datetime.now(timezone.utc),
        "role": role,
        "content": content,
    }])

# ============================
# Session state
# ============================
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = _load_messages(st.session_state.chat_session_id)

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if not st.session_state.messages:
    welcome = (
        "Hey — ask me anything about the Big Book or the Twelve & Twelve.\n\n"
        "I’ll keep it grounded in the text and list sources at the end."
    )
    st.session_state.messages = [{"role": "assistant", "content": welcome}]
    _append_message(st.session_state.chat_session_id, "assistant", welcome)

# ============================
# CSS
# ============================
CSS = f"""
<style>
#MainMenu, header, footer {{ visibility: hidden; }}

.stApp {{
  background: {PALETTE["page_bg"]};
  color: {PALETTE["text"]};
}}

.block-container {{
  max-width: 900px;
  padding-top: 20px;
  padding-bottom: 110px;
}}

.bb-title {{
  font-size: 38px;
  font-weight: 900;
  margin: 0;
}}

.bb-sub {{
  font-size: 14px;
  color: {PALETTE["muted"]};
  margin-top: 6px;
}}

.bb-pill {{
  margin-top: 10px;
  display: inline-block;
  padding: 8px 12px;
  border-radius: 999px;
  background: {PALETTE["card_bg"]};
  border: 1px solid {PALETTE["border"]};
  box-shadow: {PALETTE["shadow"]};
  font-size: 13px;
}}

.bb-bubble {{
  border-radius: 16px;
  padding: 14px;
  border: 1px solid {PALETTE["border"]};
  box-shadow: {PALETTE["shadow"]};
  background: {PALETTE["card_bg"]};
  white-space: pre-wrap;
}}

.bb-user {{
  background: {PALETTE["user_bg"]};
}}

.bb-assistant {{
  background: {PALETTE["asst_bg"]};
}}

.bb-sources-title {{
  margin-top: 12px;
  font-weight: 800;
}}

div[data-testid="stChatInput"] > div {{
  border-radius: 18px !important;
  border: 1px solid {PALETTE["border"]} !important;
  background: #FFFFFF !important;
  box-shadow: {PALETTE["shadow"]} !important;
}}

div[data-testid="stChatInput"] textarea {{
  font-size: 16px !important;
  color: #000000 !important;
}}

div[data-testid="stChatInput"] textarea::placeholder {{
  color: rgba(0,0,0,0.35) !important;
}}

/* ===== iOS POPOVER FIXES ===== */
.stPopover > button {{
  color: #FFFFFF !important;
  background: #1C1C1E !important;
  border: 1px solid rgba(255,255,255,0.25) !important;
}}

.stPopover > button span {{
  color: #FFFFFF !important;
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ============================
# Header + menu
# ============================
st.markdown(
    """
<div>
  <div class="bb-title">The Big Book .chat</div>
  <div class="bb-sub">Warm guidance, grounded in the text.</div>
  <div class="bb-pill">Sources are listed at the bottom of each answer.</div>
</div>
""",
    unsafe_allow_html=True,
)

with st.popover("⋯", help="Menu"):
    if st.button("Daily Reflection"):
        st.session_state.messages.append({"role": "user", "content": "Daily Reflection"})
        st.session_state.pending_prompt = (
            "Give me today's Daily Reflection style guidance grounded only in the Big Book "
            "and 12&12 excerpts you have. Keep it short, practical, and cite sources."
        )
        st.rerun()

    if st.button("New chat thread"):
        st.session_state.chat_session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    if st.button("Clear on-screen"):
        st.session_state.messages = []
        st.rerun()

# ============================
# Chat history
# ============================
for m in st.session_state.messages:
    if m["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(
                f'<div class="bb-bubble bb-user">{html.escape(m["content"])}</div>',
                unsafe_allow_html=True
            )
    else:
        raw = m["content"]
        body, *sources = raw.split("\nSources:")
        with st.chat_message("assistant", avatar="📖"):
            st.markdown(
                f'<div class="bb-bubble bb-assistant">{html.escape(body.strip())}</div>',
                unsafe_allow_html=True
            )
            if sources:
                lines = [l.strip("-• ") for l in sources[0].splitlines() if l.strip()]
                st.markdown('<div class="bb-sources-title">Sources:</div>', unsafe_allow_html=True)
                st.markdown(
                    "<ul>" + "".join(f"<li>{html.escape(l)}</li>" for l in lines) + "</ul>",
                    unsafe_allow_html=True
                )

# ============================
# Thinking + input
# ============================
if st.session_state.pending_prompt:
    with st.chat_message("assistant", avatar="📖"):
        st.markdown('<div class="bb-bubble bb-assistant">Thinking…</div>', unsafe_allow_html=True)
        reply = ask(st.session_state.pending_prompt, filters=None, top_k=10)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    _append_message(st.session_state.chat_session_id, "assistant", reply)
    st.session_state.pending_prompt = None
    st.rerun()

user_text = st.chat_input("Message…")

if user_text and user_text.strip():
    st.session_state.messages.append({"role": "user", "content": user_text})
    _append_message(st.session_state.chat_session_id, "user", user_text)
    st.session_state.pending_prompt = user_text
    st.rerun()
