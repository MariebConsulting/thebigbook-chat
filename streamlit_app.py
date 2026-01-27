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
# Modern DARK palette (non-blue)
# ============================
PALETTE = {
    # Backgrounds
    "bg": "#0E0F11",          # near-black
    "bg2": "#121418",         # soft charcoal
    "card": "rgba(255,255,255,0.06)",

    # Text
    "text": "#ECE9E2",        # warm off-white
    "muted": "rgba(236,233,226,0.70)",

    # Lines + shadows
    "border": "rgba(236,233,226,0.12)",
    "shadow": "0 18px 55px rgba(0,0,0,0.45)",

    # Accents (no blue)
    "accent": "#C46A4A",      # warm clay
    "accent2": "#7E8B7A",     # muted sage

    # Chat bubbles
    "user_bg": "rgba(196,106,74,0.14)",
    "asst_bg": "rgba(255,255,255,0.08)",

    # Inputs
    "input_bg": "rgba(255,255,255,0.06)",
    "input_border": "rgba(236,233,226,0.16)",
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

    # Some LanceDB versions choke on create_table(data=[]) even with schema.
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
    # Clears current UI memory, keeps DB history intact
    st.session_state.messages = []


def _new_chat_session():
    # New session id = new persistent thread
    st.session_state.chat_session_id = str(uuid.uuid4())
    st.session_state.messages = []


# ============================
# Session state init (BEFORE any access)
# ============================
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = _load_messages(st.session_state.chat_session_id, limit=400)

# Seed welcome once per empty session
if not st.session_state.messages:
    welcome = (
        "Hey — I’m here with you.\n\n"
        "Ask me anything about the Big Book or the Twelve & Twelve. "
        "I’ll stay grounded in the text and list sources at the end."
    )
    st.session_state.messages = [{"role": "assistant", "content": welcome}]
    _append_message(st.session_state.chat_session_id, "assistant", welcome)

# ============================
# CSS (mobile-first, dark, clean)
# ============================
CSS = f"""
<style>
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

/* make the page feel like an app */
.stApp {{
  background: radial-gradient(1200px 700px at 20% 0%,
    {PALETTE["bg2"]} 0%,
    {PALETTE["bg"]} 55%,
    {PALETTE["bg"]} 100%);
  color: {PALETTE["text"]};
}}

/* tighter container for mobile readability */
.block-container {{
  padding-top: 16px;
  padding-bottom: 10px;
  max-width: 860px;
}}

/* header */
.bb-top {{
  margin-bottom: 10px;
}}
.bb-title {{
  font-size: 40px;
  font-weight: 850;
  letter-spacing: -0.02em;
  line-height: 1.05;
  margin: 0;
}}
.bb-sub {{
  margin-top: 6px;
  font-size: 14px;
  opacity: 0.78;
}}

/* tagline bubble (your “streamlit universe” bubble, but styled) */
.bb-tagline {{
  display:inline-block;
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid {PALETTE["border"]};
  background: rgba(255,255,255,0.05);
  color: {PALETTE["muted"]};
  font-size: 13px;
}}

/* chat card */
.bb-card {{
  margin-top: 14px;
  border: 1px solid {PALETTE["border"]};
  background: {PALETTE["card"]};
  border-radius: 18px;
  padding: 12px;
  box-shadow: {PALETTE["shadow"]};
}}

/* chat area spacing */
.bb-chat {{
  margin-top: 6px;
  padding: 2px 2px 10px 2px;
}}

/* bubble base */
.bb-bubble {{
  border-radius: 16px;
  padding: 14px 14px;
  line-height: 1.55;
  border: 1px solid {PALETTE["border"]};
  white-space: pre-wrap;
}}

/* user bubble */
.bb-user {{
  background: {PALETTE["user_bg"]};
}}

/* assistant bubble */
.bb-assistant {{
  background: {PALETTE["asst_bg"]};
}}

/* Sources section */
.bb-sources-title {{
  margin-top: 12px;
  font-weight: 850;
  color: {PALETTE["text"]};
}}
.bb-sources ul {{
  margin: 8px 0 0 18px;
}}
.bb-sources li {{
  margin: 6px 0;
  color: {PALETTE["muted"]};
}}

/* composer card */
.bb-compose {{
  margin-top: 10px;
  border: 1px solid {PALETTE["border"]};
  background: rgba(255,255,255,0.04);
  border-radius: 18px;
  padding: 12px;
}}

/* input style */
div[data-testid="stTextInput"] > div {{
  border-radius: 14px !important;
  background: {PALETTE["input_bg"]} !important;
  border: 1px solid {PALETTE["input_border"]} !important;
  box-shadow: none !important;
}}
div[data-testid="stTextInput"] input {{
  padding: 14px 14px !important;
  font-size: 16px !important;
  color: {PALETTE["text"]} !important;
}}
div[data-testid="stTextInput"] label {{
  display:none !important;
}}

/* buttons */
div.stButton > button {{
  width: 100%;
  border-radius: 14px;
  padding: 11px 12px;
  border: 1px solid {PALETTE["border"]};
  background: rgba(255,255,255,0.06);
  font-weight: 850;
  color: {PALETTE["text"]};
}}
div.stButton > button:hover {{
  border-color: rgba(255,255,255,0.20);
  transform: translateY(-1px);
}}
/* primary button variant */
.bb-primary div.stButton > button {{
  border-color: rgba(196,106,74,0.45);
  background: rgba(196,106,74,0.16);
}}

/* make streamlit chat message containers less “bubbly” */
div[data-testid="stChatMessage"] {{
  padding-top: 0.25rem;
  padding-bottom: 0.25rem;
}}

/* mobile tweaks */
@media (max-width: 520px) {{
  .bb-title {{ font-size: 34px; }}
  .block-container {{ padding-top: 12px; }}
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ============================
# Header
# ============================
st.markdown(
    """
<div class="bb-top">
  <div class="bb-title">The Big Book .chat</div>
  <div class="bb-sub">Warm guidance, grounded in the text.</div>
  <div class="bb-tagline">Sources are listed at the bottom of each answer.</div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================
# Chat history
# ============================
st.markdown('<div class="bb-card">', unsafe_allow_html=True)
st.markdown('<div class="bb-chat">', unsafe_allow_html=True)

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
        raw = content.strip()
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
                    '<div class="bb-sources"><ul>' +
                    "".join(f"<li>{html.escape(x)}</li>" for x in cleaned) +
                    "</ul></div>",
                    unsafe_allow_html=True
                )

st.markdown("</div>", unsafe_allow_html=True)  # bb-chat
st.markdown("</div>", unsafe_allow_html=True)  # bb-card

# ============================
# Composer (INPUT ABOVE BUTTONS)
# ============================
st.markdown('<div class="bb-compose">', unsafe_allow_html=True)

with st.form("composer", clear_on_submit=True):
    c1, c2 = st.columns([6, 2], gap="small")
    with c1:
        prompt = st.text_input("Message", placeholder="Type your message…")
    with c2:
        send_clicked = st.form_submit_button("Send", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)  # bb-compose

# Buttons BELOW input
b1, b2, b3 = st.columns([1, 1, 1], gap="small")
with b1:
    daily_clicked = st.button("Daily Reflection", use_container_width=True)
with b2:
    new_thread = st.button("New chat thread", use_container_width=True)
with b3:
    clear_clicked = st.button("Clear on-screen", use_container_width=True)

if clear_clicked:
    _reset_screen_only()
    st.rerun()

if new_thread:
    _new_chat_session()
    st.rerun()

def _run_query(q: str):
    q = (q or "").strip()
    if not q:
        return

    st.session_state.messages.append({"role": "user", "content": q})
    _append_message(st.session_state.chat_session_id, "user", q)

    with st.spinner("Thinking…"):
        reply = ask(q, filters=None, top_k=10)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    _append_message(st.session_state.chat_session_id, "assistant", reply)
    st.rerun()

if send_clicked and prompt and prompt.strip():
    _run_query(prompt.strip())

if daily_clicked:
    daily_prompt = (
        "Give me today's AA Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and cite sources."
    )
    _run_query(daily_prompt)
