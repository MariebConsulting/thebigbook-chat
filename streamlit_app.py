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

st.set_page_config(
    page_title="The Big Book .chat",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================
# Dark modern palette
# ============================
PALETTE = {
    "bg": "#0A0A0A",           # deep black
    "bg2": "#121212",          # slightly lighter
    "card": "#1A1A1A",         # dark card
    "text": "#E8E8E8",         # bright text
    "muted": "#999999",        # muted text
    "border": "#2A2A2A",       # subtle border
    "accent": "#FF6B35",       # warm orange accent
    "accent_hover": "#FF8C61", # lighter orange
    "input_bg": "#242424",     # input background
    "user_bubble": "#2A2A2A",  # user message
    "asst_bubble": "#1A1A1A",  # assistant message
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


def _new_chat_session():
    st.session_state.chat_session_id = str(uuid.uuid4())
    st.session_state.messages = []


# ============================
# Session state initialization
# ============================
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = _load_messages(
        st.session_state.chat_session_id,
        limit=400
    )

    if not st.session_state.messages:
        welcome = (
            "Hey.\n\n"
            "Ask me anything about the Big Book or the Twelve & Twelve. "
            "I'll stay grounded in the text and cite sources."
        )
        st.session_state.messages = [
            {"role": "assistant", "content": welcome}
        ]


# ============================
# CSS - Dark, mobile-first
# ============================
CSS = f"""
<style>
/* Hide Streamlit UI elements */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}
.stDeployButton {{display: none;}}

/* Container */
.block-container {{
  padding: 12px 16px 80px 16px;
  max-width: 100%;
}}

/* Dark background */
.stApp {{
  background: {PALETTE["bg"]};
  color: {PALETTE["text"]};
}}

/* All text white */
h1, h2, h3, p, label, span, div {{
  color: {PALETTE["text"]} !important;
}}

/* Header */
.bb-header {{
  text-align: center;
  padding: 20px 0 12px 0;
  border-bottom: 1px solid {PALETTE["border"]};
  margin-bottom: 16px;
}}

.bb-title {{
  font-size: 32px;
  font-weight: 900;
  letter-spacing: -0.01em;
  margin: 0;
  color: {PALETTE["text"]};
}}

/* Tagline card */
.bb-tagline {{
  background: {PALETTE["card"]};
  border: 1px solid {PALETTE["border"]};
  border-radius: 12px;
  padding: 12px 16px;
  margin: 12px 0 16px 0;
  font-size: 14px;
  color: {PALETTE["muted"]};
  text-align: center;
}}

/* Chat input at top - make it look good */
div[data-testid="stChatInput"] {{
  position: fixed;
  top: 140px;
  left: 0;
  right: 0;
  z-index: 999;
  padding: 0 16px 12px 16px;
  background: {PALETTE["bg"]};
  border-bottom: 1px solid {PALETTE["border"]};
}}

div[data-testid="stChatInput"] > div {{
  border-radius: 12px !important;
  border: 1px solid {PALETTE["border"]} !important;
  background: {PALETTE["input_bg"]} !important;
}}

div[data-testid="stChatInput"] textarea {{
  color: {PALETTE["text"]} !important;
  font-size: 16px !important;
  border-radius: 12px !important;
}}

div[data-testid="stChatInput"] textarea::placeholder {{
  color: {PALETTE["muted"]} !important;
}}

/* Buttons below input */
.bb-controls {{
  position: fixed;
  top: 200px;
  left: 0;
  right: 0;
  z-index: 998;
  display: flex;
  gap: 8px;
  padding: 0 16px 12px 16px;
  background: {PALETTE["bg"]};
  border-bottom: 1px solid {PALETTE["border"]};
}}

.bb-controls .stButton > button {{
  width: 100%;
  background: {PALETTE["card"]} !important;
  border: 1px solid {PALETTE["border"]} !important;
  border-radius: 10px !important;
  color: {PALETTE["text"]} !important;
  font-weight: 700 !important;
  font-size: 14px !important;
  padding: 10px 12px !important;
  transition: all 0.2s !important;
}}

.bb-controls .stButton > button:hover {{
  background: {PALETTE["accent"]} !important;
  border-color: {PALETTE["accent"]} !important;
}}

/* Chat area - add top padding for fixed elements */
.bb-chat {{
  margin-top: 120px;
  padding-bottom: 20px;
}}

/* Chat messages */
div[data-testid="stChatMessage"] {{
  background: transparent !important;
  border: none !important;
  padding: 8px 0 !important;
}}

/* Message bubbles */
.bb-bubble {{
  border-radius: 16px;
  padding: 14px 16px;
  line-height: 1.6;
  font-size: 15px;
  margin: 4px 0;
  word-wrap: break-word;
}}

.bb-user {{
  background: {PALETTE["user_bubble"]};
  border: 1px solid {PALETTE["border"]};
  margin-left: 20px;
}}

.bb-assistant {{
  background: {PALETTE["asst_bubble"]};
  border: 1px solid {PALETTE["border"]};
  margin-right: 20px;
}}

/* Sources */
.bb-sources {{
  margin-top: 12px;
  padding: 12px;
  background: {PALETTE["bg2"]};
  border-radius: 10px;
  border: 1px solid {PALETTE["border"]};
}}

.bb-sources-title {{
  font-weight: 700;
  font-size: 13px;
  color: {PALETTE["accent"]};
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}

.bb-sources ul {{
  margin: 0;
  padding-left: 20px;
  list-style: none;
}}

.bb-sources li {{
  font-size: 13px;
  color: {PALETTE["muted"]};
  margin: 6px 0;
  position: relative;
  padding-left: 12px;
}}

.bb-sources li:before {{
  content: "→";
  position: absolute;
  left: 0;
  color: {PALETTE["accent"]};
}}

/* Spinner */
div[data-testid="stSpinner"] > div {{
  border-color: {PALETTE["accent"]} transparent transparent transparent !important;
}}

/* Mobile optimizations */
@media (max-width: 768px) {{
  .bb-title {{
    font-size: 28px;
  }}
  
  .bb-controls {{
    flex-direction: column;
  }}
  
  div[data-testid="stChatInput"] {{
    top: 120px;
  }}
  
  .bb-controls {{
    top: 175px;
  }}
  
  .bb-chat {{
    margin-top: 100px;
  }}
}}

/* Very small screens */
@media (max-width: 400px) {{
  .bb-title {{
    font-size: 24px;
  }}
  
  .bb-bubble {{
    font-size: 14px;
    padding: 12px 14px;
  }}
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
</div>
""",
    unsafe_allow_html=True,
)

# Tagline in bubble
st.markdown(
    '<div class="bb-tagline">Warm guidance, grounded in the text. Sources at the bottom.</div>',
    unsafe_allow_html=True,
)

# ============================
# Chat input at TOP
# ============================
user_text = st.chat_input("Message…")

# ============================
# Control buttons below input
# ============================
st.markdown('<div class="bb-controls">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    daily_clicked = st.button("📖 Daily Reflection", use_container_width=True)
with col2:
    new_thread = st.button("✨ New Chat", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

if new_thread:
    _new_chat_session()
    st.rerun()

# ============================
# Chat history
# ============================
st.markdown('<div class="bb-chat">', unsafe_allow_html=True)

for m in st.session_state.messages:
    role = m.get("role", "assistant")
    content = m.get("content", "")

    if role == "user":
        with st.chat_message("user", avatar="💭"):
            st.markdown(
                f'<div class="bb-bubble bb-user">{html.escape(content)}</div>',
                unsafe_allow_html=True
            )
    else:
        # Split answer vs Sources
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
            if body:
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

                sources_html = '<div class="bb-sources">'
                sources_html += '<div class="bb-sources-title">Sources</div>'
                sources_html += '<ul>' + "".join(
                    f"<li>{html.escape(x)}</li>" for x in cleaned
                ) + '</ul></div>'
                st.markdown(sources_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ============================
# Handle input
# ============================
def _run_query(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    _append_message(st.session_state.chat_session_id, "user", prompt)

    with st.spinner("Thinking…"):
        reply = ask(prompt, filters=None, top_k=10)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    _append_message(st.session_state.chat_session_id, "assistant", reply)
    st.rerun()

if daily_clicked:
    daily_prompt = (
        "Give me today's AA Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and cite sources."
    )
    _run_query(daily_prompt)

if user_text and user_text.strip():
    _run_query(user_text.strip())
