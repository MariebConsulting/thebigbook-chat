import html
import streamlit as st
from scripts.smoke_ask import ask

st.set_page_config(page_title="The Big Book .chat", layout="wide")

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

/* Title row */
.bb-top {{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:16px;
  margin-bottom: 10px;
}}

.bb-title {{
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.05;
  margin: 0;
}}

.bb-sub {{
  margin-top: 8px;
  font-size: 14px;
  opacity: 0.78;
}}

/* Chat card */
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
  box-shadow: 0 18px 55px rgba(0,0,0,0.35);
}}

/* Input styling */
div[data-testid="stTextInput"] > div {{
  border-radius: 14px !important;
  background: rgba(255,255,255,0.82) !important;
  border: 1px solid {PALETTE["border"]} !important;
  box-shadow: none !important;
}}

body[data-dark="true"] div[data-testid="stTextInput"] > div {{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid {PALETTE["d_border"]} !important;
}}

div[data-testid="stTextInput"] input {{
  padding: 14px 14px !important;
  font-size: 16px !important;
}}

div[data-testid="stTextInput"] label {{
  font-weight: 700 !important;
  opacity: 0.85 !important;
  margin-bottom: 6px !important;
  display:block !important;
}}

/* Buttons */
div.stButton > button {{
  width: 100%;
  border-radius: 14px;
  padding: 12px 14px;
  border: 1px solid {PALETTE["border"]};
  background: rgba(255,255,255,0.75);
  font-weight: 800;
}}

div.stButton > button:hover {{
  border-color: rgba(0,0,0,0.22);
  transform: translateY(-1px);
}}

body[data-dark="true"] div.stButton > button {{
  border: 1px solid {PALETTE["d_border"]};
  background: rgba(255,255,255,0.06);
}}

body[data-dark="true"] div.stButton > button:hover {{
  border-color: rgba(255,255,255,0.24);
}}

/* Answer bubble */
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

/* Tighten checkbox so it doesn't look like a big bar */
div[data-testid="stCheckbox"] {{
  margin-top: -2px;
}}

div[data-testid="stCheckbox"] label {{
  display:flex;
  align-items:center;
  gap:10px;
  user-select:none;
  font-weight: 800;
}}

div[data-testid="stCheckbox"] input {{
  width: 46px !important;
  height: 26px !important;
  appearance: none !important;
  background: rgba(0,0,0,0.10);
  border: 1px solid {PALETTE["border"]};
  border-radius: 999px !important;
  position: relative !important;
  outline: none !important;
  cursor: pointer !important;
}}

div[data-testid="stCheckbox"] input:checked {{
  background: rgba(63,74,65,0.75);
  border-color: rgba(63,74,65,0.75);
}}

div[data-testid="stCheckbox"] input::before {{
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: rgba(255,255,255,0.92);
  transition: transform 0.18s ease;
}}

div[data-testid="stCheckbox"] input:checked::before {{
  transform: translateX(20px);
}}

body[data-dark="true"] div[data-testid="stCheckbox"] input {{
  background: rgba(255,255,255,0.08);
  border: 1px solid {PALETTE["d_border"]};
}}

body[data-dark="true"] div[data-testid="stCheckbox"] input:checked {{
  background: rgba(169,179,167,0.45);
  border-color: rgba(169,179,167,0.45);
}}

/* Make form spacing nice */
.bb-input-wrap {{
  margin-top: 6px;
}}

.bb-input-hint {{
  font-size: 13px;
  opacity: 0.75;
  margin-top: -4px;
  margin-bottom: 10px;
}}

.bb-divider {{
  height: 10px;
}}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# Header (clean)
st.markdown(
    """
<div class="bb-top">
  <div>
    <div class="bb-title">The Big Book .chat</div>
    <div class="bb-sub">Ask anything. Citations enforced.</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Clean “settings” (collapsible; keeps top uncluttered)
with st.expander("Preferences", expanded=False):
    st.checkbox("Dark mode", key="dark")

# Apply marker after checkbox render
st.markdown(
    f"<script>document.body.setAttribute('data-dark','{str(st.session_state.dark).lower()}');</script>",
    unsafe_allow_html=True,
)

# Main card
st.markdown('<div class="bb-card">', unsafe_allow_html=True)

st.markdown('<div class="bb-input-wrap">', unsafe_allow_html=True)
st.markdown('<div class="bb-input-hint">Type a message below, then press <b>Send</b>.</div>', unsafe_allow_html=True)

with st.form("ask_form", clear_on_submit=False):
    c1, c2 = st.columns([6, 2], gap="small")

    with c1:
        question = st.text_input(
            "Message",
            placeholder="Ask anything… (e.g., What does AA say about fear?)",
        )

    with c2:
        send_clicked = st.form_submit_button("Send", use_container_width=True)

    st.markdown('<div class="bb-divider"></div>', unsafe_allow_html=True)
    daily_clicked = st.form_submit_button("Daily Reflection", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Output
if send_clicked and question.strip():
    with st.spinner("Searching..."):
        result = ask(question, filters=None, top_k=10)
    safe = html.escape(result)
    st.markdown(f'<div class="bb-answer">{safe}</div>', unsafe_allow_html=True)

elif daily_clicked:
    daily_prompt = (
        "Give me today’s AA Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and cite sources."
    )
    with st.spinner("Searching..."):
        result = ask(daily_prompt, filters=None, top_k=10)
    safe = html.escape(result)
    st.markdown(f'<div class="bb-answer">{safe}</div>', unsafe_allow_html=True)
