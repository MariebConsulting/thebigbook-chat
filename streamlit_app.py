
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
# Modern dark palette (charcoal + foggy dew) — NO blue, NO AA vibes
# ============================
PALETTE = {
    # App background (charcoal)
    "bg": "#121416",
    "bg2": "#1A1D20",

    # Cards / panels (foggy dew)
    "card": "#DDE3DB",
    "card2": "#F1F4EE",

    # Text
    "text": "#0E0F10",          # on foggy dew
    "text_on_dark": "#ECEFF1",  # on charcoal
    "muted_on_dark": "rgba(236,239,241,0.70)",
    "muted_on_card": "rgba(14,15,16,0.62)",

    # Borders / shadows
    "border_on_card": "rgba(0,0,0,0.10)",
    "border_on_dark": "rgba(236,239,241,0.10)",
    "shadow": "0 12px 40px rgba(0,0,0,0.35)",

    # Accents (subtle, no blue)
    "accent": "#8E9A91",   # sage gray
    "accent2": "#B08A6A",  # warm clay

    # Chat bubbles
    "user_bg": "#E6EBE3",
    "asst_bg": "#F1F4EE",

    # Tagline pill
    "pill_bg": "#1E2125",
    "pill_text": "#ECEFF1",
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
        pa.field("role", pa.string()),  # "user" | "assistant"
        pa.field("content", pa.string()),
    ])

    # Some LanceDB versions choke on create_table(data=[], schema=...).
    # Create with a dummy row, then delete it if supported.
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
    # Clears current UI memory, keeps DB history intact.
    st.session_state.messages = []


def _new_chat_session():
    # New session id = new persistent thread
    st.session_state.chat_session_id = str(uuid.uuid4())
    st.session_state.messages = []


# ============================
# Session state init (MUST come before any access)
# ============================
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = _load_messages(st.session_state.chat_session_id, limit=400)

# Seed a warm welcome if this is a new session
if not st.session_state.messages:
    welcome = (
        "Hey — I’m here with you.\n\n"
        "Ask me anything about the Big Book or the Twelve & Twelve. "
        "I’ll stay grounded in the text and list sources at the end."
    )
    st.session_state.messages = [{"role": "assistant", "content": welcome}]
    _append_message(st.session_state.chat_session_id, "assistant", welcome)

# ============================
# CSS (mobile-first, darker, readable)
# ============================
CSS = f"""
<style>
/* Hide Streamlit chrome */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

/* Layout */
.block-container {{
  padding-top: 18px;
  max-width: 980px;
}}

/* App background */
.stApp {{
  background: radial-gradient(1200px 600px at 20% 0%,
    {PALETTE["bg2"]} 0%,
    {PALETTE["bg"]} 60%,
    #0D0F11 100%);
  color: {PALETTE["text_on_dark"]};
}}

/* Header */
.bb-top {{
  margin-bottom: 10px;
}}
.bb-title {{
  font-size: 40px;
  font-weight: 900;
  letter-spacing: -0.02em;
  line-height: 1.05;
  margin: 0;
}}
.bb-sub {{
  margin-top: 6px;
  font-size: 14px;
  color: {PALETTE["muted_on_dark"]};
}}

/* Tagline pill */
.bb-pill {{
  display:inline-block;
  background: {PALETTE["pill_bg"]};
  color: {PALETTE["pill_text"]};
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
  margin-top: 10px;
  margin-bottom: 12px;
  border: 1px solid {PALETTE["border_on_dark"]};
}}

/* Chat card/panel */
.bb-card {{
  border: 1px solid {PALETTE["border_on_dark"]};
  background: rgba(0,0,0,0.18);
  border-radius: 18px;
  padding: 12px;
  box-shadow: {PALETTE["shadow"]};
}}

/* Chat scroll area */
.bb-chat {{
  margin-top: 6px;
  padding: 2px 2px 10px 2px;
}}

/* Bubbles (we render inside st.chat_message containers) */
.bb-bubble {{
  border-radius: 16px;
  padding: 14px 14px;
  line-height: 1.55;
  border: 1px solid {PALETTE["border_on_card"]};
  white-space: pre-wrap;
  color: {PALETTE["text"]};
}}
.bb-user {{
  background: {PALETTE["user_bg"]};
}}
.bb-assistant {{
  background: {PALETTE["asst_bg"]};
}}

/* Sources */
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

/* Input strip (above buttons) */
.bb-composer {{
  background: {PALETTE["card"]};
  border: 1px solid {PALETTE["border_on_card"]};
  border-radius: 16px;
  padding: 12px;
  margin-top: 10px;
}}
.bb-hint {{
  font-size: 13px;
  color: {PALETTE["muted_on_card"]};
  margin: 0 0 10px 2px;
}}

/* Text input styling */
div[data-testid="stTextInput"] > div {{
  border-radius: 14px !important;
  background: {PALETTE["card2"]} !important;
  border: 1px solid {PALETTE["border_on_card"]} !important;
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

/* Buttons */
div.stButton > button {{
  width: 100%;
  border-radius: 14px;
  padding: 12px 14px;
  border: 1px solid {PALETTE["border_on_card"]};
  background: {PALETTE["card2"]};
  font-weight: 900;
  color: {PALETTE["text"]};
}}
div.stButton > button:hover {{
  transform: translateY(-1px);
}}

/* Make chat message containers less "Streamlit-y" */
section[data-testid="stChatMessage"] {{
  padding: 0.25rem 0 !important;
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
  <div class="bb-pill">Sources are listed at the bottom of each answer.</div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================
# Main panel: chat + composer + actions
# ============================
st.markdown('<div class="bb-card">', unsafe_allow_html=True)

# --- Render chat history ---
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

        # Split answer vs Sources section (prevents nested bullet weirdness)
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

st.markdown("</div>", unsafe_allow_html=True)  # bb-chat

# --- Composer (INPUT ABOVE BUTTONS) ---
st.markdown('<div class="bb-composer">', unsafe_allow_html=True)
st.markdown('<div class="bb-hint">Type your message and press <b>Send</b>.</div>', unsafe_allow_html=True)

with st.form("composer_form", clear_on_submit=True):
    c1, c2 = st.columns([5, 2], gap="small")
    with c1:
        user_text = st.text_input("Message", placeholder="Ask about fear, resentment, Step One…")
    with c2:
        send_clicked = st.form_submit_button("Send", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)  # bb-composer

# --- Actions row (below input) ---
b1, b2, b3 = st.columns(3, gap="small")
with b1:
    daily_clicked = st.button("Daily Reflection", use_container_width=True)
with b2:
    new_thread = st.button("New chat thread", use_container_width=True)
with b3:
    clear_clicked = st.button("Clear on-screen", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)  # bb-card


def _run_query(prompt: str):
    # persist user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    _append_message(st.session_state.chat_session_id, "user", prompt)

    # assistant response (with thinking)
    with st.spinner("Thinking…"):
        reply = ask(prompt, filters=None, top_k=10)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    _append_message(st.session_state.chat_session_id, "assistant", reply)
    st.rerun()


# Buttons / actions
if clear_clicked:
    _reset_screen_only()
    st.rerun()

if new_thread:
    _new_chat_session()
    st.rerun()

if daily_clicked:
    daily_prompt = (
        "Give me today's Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and cite sources."
    )
    _run_query(daily_prompt)

# Send
if send_clicked and user_text and user_text.strip():
    _run_query(user_text.strip())
