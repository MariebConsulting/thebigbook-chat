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
# Light background + BLACK text (mobile-first)
# ============================
PALETTE = {
    "page_bg": "#F4F5F2",
    "card_bg": "#FFFFFF",
    "text": "#000000",
    "muted": "rgba(0,0,0,0.58)",
    "border": "rgba(0,0,0,0.12)",
    "shadow": "0 12px 38px rgba(0,0,0,0.08)",

    # bubbles
    "user_bg": "#F3F1FF",
    "asst_bg": "#FFFFFF",

    # controls
    "btn_bg": "#FFFFFF",
    "btn_text": "#000000",
    "btn_border": "rgba(0,0,0,0.16)",
    "btn_hover": "#F2F2F2",
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
        pa.field("role", pa.string()),
        pa.field("content", pa.string()),
    ])

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


def _reset_screen_only():
    st.session_state.messages = []


def _new_chat_session():
    st.session_state.chat_session_id = str(uuid.uuid4())
    st.session_state.messages = []


# ============================
# Session state (init FIRST)
# ============================
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = _load_messages(st.session_state.chat_session_id, limit=400)

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if not st.session_state.messages:
    welcome = (
        "Hey — ask me anything about the Big Book or the Twelve & Twelve.\n\n"
        "I’ll keep it grounded in your text and list sources at the end."
    )
    st.session_state.messages = [{"role": "assistant", "content": welcome}]
    _append_message(st.session_state.chat_session_id, "assistant", welcome)

# ============================
# CSS (iOS-safe composer + force white buttons)
# ============================
CSS = f"""
<style>
#MainMenu {{visibility:hidden;}}
footer {{visibility:hidden;}}
header {{visibility:hidden;}}

.stApp {{
  background: {PALETTE["page_bg"]};
  color: {PALETTE["text"]};
}}

.block-container {{
  padding-top: 14px;
  /* MORE room for iOS Safari bottom bar + Streamlit pinned composer */
  padding-bottom: calc(220px + env(safe-area-inset-bottom));
  max-width: 980px;
}}

.bb-header {{
  margin-bottom: 8px;
}}

.bb-title {{
  font-size: 40px;
  font-weight: 900;
  letter-spacing: -0.02em;
  margin: 0;
  color: {PALETTE["text"]};
}}

.bb-sub {{
  margin-top: 6px;
  font-size: 14px;
  color: {PALETTE["muted"]};
}}

/* pill + menu aligned on one row */
.bb-pillrow {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:10px;
  margin-top: 10px;
}}

.bb-pill {{
  flex: 1;
  padding: 8px 12px;
  border-radius: 999px;
  background: {PALETTE["card_bg"]};
  border: 1px solid {PALETTE["border"]};
  box-shadow: {PALETTE["shadow"]};
  color: {PALETTE["muted"]};
  font-size: 13px;
}}

/* menu button area */
.bb-menu {{
  flex: 0 0 auto;
}}

/* FORCE Streamlit buttons to be white w/ black text (strong selectors) */
.stButton > button,
.stButton > button:focus,
.stButton > button:active,
.stPopover > button,
.stPopover > button:focus,
.stPopover > button:active {{
  background: {PALETTE["btn_bg"]} !important;
  color: {PALETTE["btn_text"]} !important;
  border: 1px solid {PALETTE["btn_border"]} !important;
  border-radius: 14px !important;
  font-weight: 900 !important;
  box-shadow: {PALETTE["shadow"]} !important;
}}

.stButton > button:hover,
.stPopover > button:hover {{
  background: {PALETTE["btn_hover"]} !important;
}}

/* Chat bubbles */
.bb-chatwrap {{
  padding-top: 10px;
}}

.bb-bubble {{
  border-radius: 16px;
  padding: 14px 14px;
  border: 1px solid {PALETTE["border"]};
  background: {PALETTE["card_bg"]};
  box-shadow: 0 10px 28px rgba(0,0,0,0.06);
  white-space: pre-wrap;
  line-height: 1.55;
  color: {PALETTE["text"]};
}}

.bb-user {{
  background: {PALETTE["user_bg"]};
}}

.bb-assistant {{
  background: {PALETTE["asst_bg"]};
}}

.bb-sources-title {{
  margin-top: 12px;
  font-weight: 900;
  color: {PALETTE["text"]};
}}

.bb-sources ul {{
  margin: 8px 0 0 18px;
}}

.bb-sources li {{
  margin: 6px 0;
  color: {PALETTE["text"]};
}}

/* Composer */
div[data-testid="stChatInput"] > div {{
  border-radius: 16px !important;
  border: 1px solid {PALETTE["border"]} !important;
  background: {PALETTE["card_bg"]} !important;
  box-shadow: {PALETTE["shadow"]} !important;
}}

div[data-testid="stChatInput"] textarea {{
  color: {PALETTE["text"]} !important;
  font-size: 16px !important;
}}

div[data-testid="stChatInput"] textarea::placeholder {{
  color: rgba(0,0,0,0.35) !important;
}}

@media (max-width: 480px) {{
  .bb-title {{ font-size: 34px; }}
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ============================
# Header + pill + menu (top-right)
# ============================
st.markdown(
    """
<div class="bb-header">
  <div class="bb-title">The Big Book .chat</div>
  <div class="bb-sub">Conversation grounded in text</div>
  <div class="bb-pillrow">
    <div class="bb-pill">Sources are listed at the bottom of each answer.</div>
    <div class="bb-menu"></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Put ALL actions into one menu (top-right)
with st.popover("⋯", use_container_width=False):
    daily_clicked = st.button("Daily Reflection", use_container_width=True)
    new_thread = st.button("New chat thread", use_container_width=True)
    clear_clicked = st.button("Clear on-screen", use_container_width=True)

if clear_clicked:
    _reset_screen_only()
    st.rerun()

if new_thread:
    _new_chat_session()
    st.rerun()

# ============================
# Render chat history
# ============================
st.markdown('<div class="bb-chatwrap">', unsafe_allow_html=True)


def _render_assistant(content: str):
    raw = (content or "").strip()

    if "\nSources:" in raw:
        body, sources = raw.split("\nSources:", 1)
        sources_lines = [s.strip() for s in sources.splitlines() if s.strip()]
    elif raw.startswith("Sources:"):
        body = ""
        sources_lines = [s.strip() for s in raw[len("Sources:"):].splitlines() if s.strip()]
    else:
        body = raw
        sources_lines = []

    with st.chat_message("assistant", avatar="🍂"):
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
        with st.chat_message("user", avatar="🧑"):
            st.markdown(
                f'<div class="bb-bubble bb-user">{html.escape(content)}</div>',
                unsafe_allow_html=True
            )
    else:
        _render_assistant(content)

# Pending prompt: show Thinking… bubble then run ask()
if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt

    with st.chat_message("assistant", avatar="🍂"):
        placeholder = st.empty()
        placeholder.markdown(
            '<div class="bb-bubble bb-assistant">Thinking…</div>',
            unsafe_allow_html=True
        )
        with st.spinner(""):
            reply = ask(prompt, filters=None, top_k=10)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    _append_message(st.session_state.chat_session_id, "assistant", reply)

    st.session_state.pending_prompt = None
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ============================
# Input (paper-airplane) — only entry
# ============================
user_text = st.chat_input("Message…")


def _queue_prompt(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    _append_message(st.session_state.chat_session_id, "user", prompt)
    st.session_state.pending_prompt = prompt
    st.rerun()


if daily_clicked:
    st.session_state.messages.append({"role": "user", "content": "Daily Reflection"})
    _append_message(st.session_state.chat_session_id, "user", "Daily Reflection")

    daily_prompt = (
        "Give me today's Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and cite sources."
    )
    st.session_state.pending_prompt = daily_prompt
    st.rerun()

if user_text and user_text.strip():
    _queue_prompt(user_text.strip())


