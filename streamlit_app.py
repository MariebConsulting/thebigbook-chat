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
    page_title="The Big Book Chat",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================
# CLEAN, MODERN PALETTE
# Ultra-readable with excellent contrast
# ============================
PALETTE = {
    # Backgrounds
    "bg": "#1A1D23",              # Deep navy (not black, easier on eyes)
    "surface": "#252932",          # Lighter surface for cards
    "elevated": "#2D323E",         # Elevated surfaces
    
    # Text - MAXIMUM readability
    "text": "#FFFFFF",             # Pure white text
    "text_secondary": "#B8BCC8",   # Light gray for secondary
    
    # Accent - Calm but uplifting
    "accent": "#64B5F6",           # Soft sky blue (calming, hopeful)
    "accent_hover": "#90CAF9",     # Lighter blue
    "accent_bg": "#1E3A52",        # Dark blue background
    
    # Input/Interactive
    "input_bg": "#2D323E",         # Clear input background
    "input_border": "#3D4350",     # Subtle border
    "input_focus": "#64B5F6",      # Blue when focused
    
    # Messages
    "user_msg": "#2C5F7F",         # User message (blue-tinted)
    "assistant_msg": "#2D323E",    # Assistant message
    
    # Borders
    "border": "#3D4350",           # Subtle borders
    "border_light": "#4A5060",     # Lighter borders
}

# ============================
# Database Functions
# ============================
DB_DIR = "./db/lancedb"
CHAT_TABLE = "chat_messages"

def _db():
    os.makedirs(DB_DIR, exist_ok=True)
    return lancedb.connect(DB_DIR)

def _ensure_chat_table():
    db = _db()
    if CHAT_TABLE in db.table_names():
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
    except:
        pass
    return tbl

def _load_messages(session_id: str, limit: int = 400) -> List[Dict[str, str]]:
    tbl = _ensure_chat_table()
    df = tbl.to_pandas()
    if df.empty:
        return []
    df = df[df["session_id"] == session_id].sort_values("ts").tail(limit)
    return [{"role": str(r["role"]), "content": str(r["content"])} for _, r in df.iterrows()]

def _append_message(session_id: str, role: str, content: str) -> None:
    tbl = _ensure_chat_table()
    tbl.add([{
        "session_id": session_id,
        "ts": datetime.now(timezone.utc),
        "role": role,
        "content": content,
    }])

def _new_chat():
    st.session_state.chat_session_id = str(uuid.uuid4())
    st.session_state.messages = []

# ============================
# Session State
# ============================
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = _load_messages(st.session_state.chat_session_id, limit=400)
    if not st.session_state.messages:
        welcome = "Hey there. 👋\n\nI'm here to help with anything from the Big Book or Twelve & Twelve. Ask me anything, and I'll stay grounded in the text with sources to back it up."
        st.session_state.messages = [{"role": "assistant", "content": welcome}]

# ============================
# CSS - MODERN, CLEAN, READABLE
# ============================
CSS = f"""
<style>
/* Hide Streamlit branding */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}
.stDeployButton {{display: none;}}

/* Main app styling */
.stApp {{
    background: {PALETTE["bg"]};
    color: {PALETTE["text"]};
}}

/* Container - mobile first */
.block-container {{
    padding: 0;
    max-width: 100%;
}}

/* HEADER - Fixed at top */
.chat-header {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: {PALETTE["surface"]};
    border-bottom: 2px solid {PALETTE["accent"]};
    padding: 16px 20px;
    z-index: 1000;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}}

.chat-title {{
    font-size: 24px;
    font-weight: 800;
    color: {PALETTE["text"]};
    margin: 0;
    text-align: center;
}}

.chat-subtitle {{
    font-size: 13px;
    color: {PALETTE["text_secondary"]};
    text-align: center;
    margin-top: 4px;
}}

/* MESSAGES AREA - Scrollable middle section */
.messages-container {{
    margin-top: 100px;
    margin-bottom: 180px;
    padding: 16px;
    min-height: 50vh;
}}

/* Message bubbles - SUPER readable */
div[data-testid="stChatMessage"] {{
    background: transparent !important;
    padding: 8px 0 !important;
    margin: 12px 0 !important;
}}

.msg-bubble {{
    padding: 16px 20px;
    border-radius: 16px;
    line-height: 1.7;
    font-size: 16px;
    max-width: 85%;
    word-wrap: break-word;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}}

.msg-user {{
    background: {PALETTE["user_msg"]};
    margin-left: auto;
    color: {PALETTE["text"]};
    border: 1px solid {PALETTE["border_light"]};
}}

.msg-assistant {{
    background: {PALETTE["assistant_msg"]};
    margin-right: auto;
    color: {PALETTE["text"]};
    border: 1px solid {PALETTE["border"]};
}}

/* Sources styling */
.sources-box {{
    margin-top: 12px;
    padding: 12px 16px;
    background: {PALETTE["accent_bg"]};
    border-left: 3px solid {PALETTE["accent"]};
    border-radius: 8px;
}}

.sources-title {{
    font-size: 12px;
    font-weight: 700;
    color: {PALETTE["accent"]};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}}

.sources-box ul {{
    margin: 0;
    padding-left: 18px;
    list-style: none;
}}

.sources-box li {{
    color: {PALETTE["text_secondary"]};
    font-size: 13px;
    margin: 4px 0;
    padding-left: 8px;
    position: relative;
}}

.sources-box li:before {{
    content: "›";
    position: absolute;
    left: -8px;
    color: {PALETTE["accent"]};
    font-weight: bold;
}}

/* INPUT AREA - Fixed at bottom */
.input-container {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: {PALETTE["surface"]};
    border-top: 2px solid {PALETTE["border_light"]};
    padding: 16px;
    z-index: 1000;
    box-shadow: 0 -2px 12px rgba(0,0,0,0.3);
}}

/* Streamlit chat input styling */
div[data-testid="stChatInput"] {{
    background: transparent;
    padding: 0;
}}

div[data-testid="stChatInput"] > div {{
    background: {PALETTE["input_bg"]} !important;
    border: 2px solid {PALETTE["input_border"]} !important;
    border-radius: 24px !important;
    transition: all 0.2s ease;
}}

div[data-testid="stChatInput"] > div:focus-within {{
    border-color: {PALETTE["accent"]} !important;
    box-shadow: 0 0 0 3px {PALETTE["accent_bg"]} !important;
}}

div[data-testid="stChatInput"] textarea {{
    font-size: 16px !important;
    color: {PALETTE["text"]} !important;
    padding: 14px 20px !important;
}}

div[data-testid="stChatInput"] textarea::placeholder {{
    color: {PALETTE["text_secondary"]} !important;
}}

div[data-testid="stChatInput"] button {{
    background: {PALETTE["accent"]} !important;
    color: white !important;
    border-radius: 50% !important;
    width: 44px !important;
    height: 44px !important;
    min-width: 44px !important;
    padding: 0 !important;
    margin-right: 4px !important;
    transition: all 0.2s ease !important;
}}

div[data-testid="stChatInput"] button:hover {{
    background: {PALETTE["accent_hover"]} !important;
    transform: scale(1.05);
}}

/* Action buttons */
.action-buttons {{
    display: flex;
    gap: 8px;
    margin-top: 12px;
    justify-content: center;
}}

.stButton button {{
    background: {PALETTE["elevated"]} !important;
    color: {PALETTE["text"]} !important;
    border: 1px solid {PALETTE["border"]} !important;
    border-radius: 20px !important;
    padding: 10px 20px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}}

.stButton button:hover {{
    background: {PALETTE["accent_bg"]} !important;
    border-color: {PALETTE["accent"]} !important;
    color: {PALETTE["accent"]} !important;
    transform: translateY(-2px);
}}

/* Mobile responsive */
@media (max-width: 768px) {{
    .chat-title {{
        font-size: 20px;
    }}
    
    .msg-bubble {{
        max-width: 90%;
        font-size: 15px;
    }}
    
    .messages-container {{
        margin-bottom: 200px;
    }}
}}

/* Smooth scrolling */
html {{
    scroll-behavior: smooth;
}}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ============================
# HEADER
# ============================
st.markdown("""
<div class="chat-header">
    <div class="chat-title">The Big Book Chat</div>
    <div class="chat-subtitle">Grounded guidance from the text, sources included</div>
</div>
""", unsafe_allow_html=True)

# ============================
# MESSAGES
# ============================
st.markdown('<div class="messages-container">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    
    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(f'<div class="msg-bubble msg-user">{html.escape(content)}</div>', unsafe_allow_html=True)
    else:
        # Parse out sources
        if "\nSources:" in content:
            body, sources = content.split("\nSources:", 1)
            source_lines = [s.strip().lstrip("-•") for s in sources.strip().split("\n") if s.strip()]
        else:
            body = content
            source_lines = []
        
        with st.chat_message("assistant", avatar="💬"):
            st.markdown(f'<div class="msg-bubble msg-assistant">{html.escape(body.strip())}</div>', unsafe_allow_html=True)
            
            if source_lines:
                sources_html = '<div class="sources-box"><div class="sources-title">Sources</div><ul>'
                sources_html += ''.join(f'<li>{html.escape(s)}</li>' for s in source_lines if s)
                sources_html += '</ul></div>'
                st.markdown(sources_html, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ============================
# INPUT AREA (Fixed at bottom)
# ============================
st.markdown('<div class="input-container">', unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Type your message here...")

# Action buttons
st.markdown('<div class="action-buttons">', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    daily_btn = st.button("📖 Daily Reflection")
with col2:
    new_chat_btn = st.button("✨ New Chat")
with col3:
    # Placeholder for future feature
    pass
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ============================
# HANDLE INPUT
# ============================
def _process_message(text: str):
    if not text or not text.strip():
        return
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": text})
    _append_message(st.session_state.chat_session_id, "user", text)
    
    # Get response
    with st.spinner("Thinking..."):
        reply = ask(text, filters=None, top_k=10)
    
    # Add assistant message
    st.session_state.messages.append({"role": "assistant", "content": reply})
    _append_message(st.session_state.chat_session_id, "assistant", reply)
    st.rerun()

if user_input:
    _process_message(user_input)

if daily_btn:
    _process_message("Give me today's Daily Reflection style guidance from the Big Book and 12&12. Keep it short and practical.")

if new_chat_btn:
    _new_chat()
    st.rerun()