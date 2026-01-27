import html
import streamlit as st
from scripts.smoke_ask import ask

st.set_page_config(page_title="The Big Book .chat", layout="wide")

# ----------------------------
# Palette
# ----------------------------
PALETTE = {
    "bg": "#E7E1D7",
    "bg2": "#DCD3C7",
    "card": "rgba(255,255,255,0.72)",
    "text": "#1F1F1D",
    "muted": "rgba(31,31,29,0.72)",
    "border": "rgba(31,31,29,0.14)",
    "shadow": "0 18px 55px rgba(0,0,0,0.10)",
    "accent": "#3F4A41",
    "accent2": "#5B5247",
    "d_bg": "#111312",
    "d_bg2": "#1A1F1C",
    "d_card": "rgba(255,255,255,0.06)",
    "d_text": "#F3F2EE",
    "d_muted": "rgba(243,242,238,0.70)",
    "d_border": "rgba(243,242,238,0.14)",
    "d_accent": "#A9B3A7",
}

if "dark" not in st.session_state:
    st.session_state.dark = False

# ----------------------------
# CSS
# ----------------------------
CSS = f"""
<style>
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

.block-container {{
  padding-top: 22px;
  max-width: 980px;
}}

.stApp {{
  background: radial-gradient(1200px 600px at 20% 0%,
    {PALETTE["bg2"]} 0%,
    {PALETTE["bg"]} 45%,
    {PALETTE["bg"]} 100%);
  color: {PALETTE["text"]};
}}

body[data-dark="true"] .stApp {{
  background: radial-gradient(1200px 600px at 20% 0%,
    {PALETTE["d_bg2"]} 0%,
    {PALETTE["d_bg"]} 55%,
    {PALETTE["d_bg"]} 100%);
  color: {PALETTE["d_text"]};
}}

h1, h2, h3, p, label, span, div {{ color: inherit; }}

.bb-top {{
  margin-bottom: 10px;
}}

.bb-title {{
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.05;
}}

.bb-sub {{
  margin-top: 6px;
  font-size: 14px;
  opacity: 0.78;
}}

.bb-card {{
  border: 1px solid {PALETTE["border"]};
  background: {PALETTE["card"]};
  border-radius: 18px;
  padding: 18px;
  box-shadow: {PALETTE["shadow"]};
}}

body[data-dark="true"] .bb-card {{
  border: 1px solid {PALETTE["d_border"]};
  background: {PALETTE["d_card"]};
}}

.bb-input-hint {{
  font-size: 13px;
  opacity: 0.75;
  margin-bottom: 8px;
}}

.bb-answer {{
  margin-top: 14px;
  border-radius: 18px;
  padding: 16px 18px;
  border: 1px solid {PALETTE["border"]};
  background: rgba(255,255,255,0.58);
  white-space: pre-wrap;
}}

body[data-dark="true"] .bb-answer {{
  border: 1px solid {PALETTE["d_border"]};
  background: rgba(255,255,255,0.04);
}}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------
# Header
# ----------------------------
st.markdown(
    """
<div class="bb-top">
  <div class="bb-title">The Big Book .chat</div>
  <div class="bb-sub">Ask anything. Citations enforced.</div>
</div>
""",
    unsafe_allow_html=True,
)

# Preferences (kept minimal)
with st.expander("Preferences", expanded=False):
    st.checkbox("Dark mode", key="dark")

st.markdown(
    f"<script>document.body.setAttribute('data-dark','{str(st.session_state.dark).lower()}');</script>",
    unsafe_allow_html=True,
)

# ----------------------------
# Input Area
# ----------------------------
st.markdown('<div class="bb-card">', unsafe_allow_html=True)
st.markdown(
    '<div class="bb-input-hint">Type a message below, then press <b>Send</b>.</div>',
    unsafe_allow_html=True,
)

with st.form("ask_form", clear_on_submit=False):
    col1, col2 = st.columns([6, 2], gap="small")

    with col1:
        question = st.text_input(
            "Message",
            placeholder="Ask anything… (e.g., What does AA say about fear?)",
        )

    with col2:
        send_clicked = st.form_submit_button("Send", use_container_width=True)

    daily_clicked = st.form_submit_button("Daily Reflection", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# Output
# ----------------------------
if send_clicked and question.strip():
    with st.spinner("Thinking…"):
        result = ask(question, filters=None, top_k=10)
    st.markdown(
        f'<div class="bb-answer">{html.escape(result)}</div>',
        unsafe_allow_html=True,
    )

elif daily_clicked:
    daily_prompt = (
        "Give me today’s AA Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and cite sources."
    )
    with st.spinner("Thinking…"):
        result = ask(daily_prompt, filters=None, top_k=10)
    st.markdown(
        f'<div class="bb-answer">{html.escape(result)}</div>',
        unsafe_allow_html=True,
    )
