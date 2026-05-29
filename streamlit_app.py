"""
FBOT Chatbot — Streamlit Frontend
Premium dark-themed chat interface for the FBOT financial assistant.
Connects to the FastAPI backend at http://localhost:8000.
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime

import os

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
APP_TITLE = "FBOT"
APP_SUBTITLE = "AI-Powered Financial Assistant"

# Intent → emoji + color mapping
INTENT_BADGES = {
    "MARKET_PRICE": ("💰", "#10b981"),
    "MARKET_TREND": ("📊", "#6366f1"),
    "STOCK_INFO": ("🏢", "#8b5cf6"),
    "STOCK_HISTORY": ("📈", "#f59e0b"),
    "STOCK_SCREEN": ("🔍", "#ec4899"),
    "TRADING_HOW_TO": ("📚", "#14b8a6"),
    "PORTFOLIO_QUERY": ("💼", "#f97316"),
    "NEWS_REQUEST": ("📰", "#3b82f6"),
    "EDUCATION": ("🎓", "#a855f7"),
    "GREETING": ("👋", "#22c55e"),
    "GENERAL": ("💬", "#64748b"),
    "ERROR": ("❌", "#ef4444"),
}


# ============================================================================
# PAGE CONFIG & CUSTOM CSS
# ============================================================================

st.set_page_config(
    page_title="FBOT — Financial Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ---- Import Google Font ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ---- Global Overrides ---- */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ---- Hide default Streamlit elements ---- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ---- Main container ---- */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
        max-width: 900px;
    }

    /* ---- Chat input styling ---- */
    .stChatInput > div {
        border-radius: 16px !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        background: rgba(15, 23, 42, 0.6) !important;
        backdrop-filter: blur(12px);
    }
    .stChatInput > div:focus-within {
        border-color: rgba(99, 102, 241, 0.7) !important;
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.15) !important;
    }

    /* ---- Chat messages ---- */
    .stChatMessage {
        border-radius: 16px !important;
        margin-bottom: 0.5rem !important;
        border: 1px solid rgba(255,255,255,0.04) !important;
    }

    /* ---- Sidebar styling ---- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.15);
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }

    /* ---- Hero header ---- */
    .hero-header {
        text-align: center;
        padding: 2rem 1rem 1rem;
        margin-bottom: 1rem;
    }
    .hero-header h1 {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
        letter-spacing: -0.5px;
    }
    .hero-header p {
        color: #94a3b8;
        font-size: 0.95rem;
        font-weight: 400;
    }

    /* ---- Sidebar logo area ---- */
    .sidebar-brand {
        text-align: center;
        padding: 1.2rem 0.5rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid rgba(99, 102, 241, 0.15);
    }
    .sidebar-brand h2 {
        background: linear-gradient(135deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.5rem;
        margin-bottom: 0.15rem;
        font-weight: 700;
    }
    .sidebar-brand p {
        color: #64748b;
        font-size: 0.75rem;
        margin: 0;
    }

    /* ---- Section headers in sidebar ---- */
    .sidebar-section {
        color: #94a3b8;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        padding: 0.6rem 0 0.3rem;
        margin-top: 0.5rem;
    }

    /* ---- Intent badge ---- */
    .intent-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-top: 4px;
        opacity: 0.85;
    }

    /* ---- Suggestion chips ---- */
    .suggestion-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 8px;
    }

    /* ---- Status indicator ---- */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse-glow 2s infinite;
    }
    @keyframes pulse-glow {
        0%, 100% { opacity: 1; box-shadow: 0 0 4px currentColor; }
        50% { opacity: 0.5; box-shadow: 0 0 8px currentColor; }
    }

    /* ---- Welcome cards ---- */
    .welcome-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-top: 1rem;
    }
    .welcome-card {
        background: rgba(99, 102, 241, 0.06);
        border: 1px solid rgba(99, 102, 241, 0.12);
        border-radius: 12px;
        padding: 14px 16px;
        transition: all 0.2s ease;
    }
    .welcome-card:hover {
        border-color: rgba(99, 102, 241, 0.3);
        background: rgba(99, 102, 241, 0.1);
    }
    .welcome-card .card-icon {
        font-size: 1.4rem;
        margin-bottom: 6px;
    }
    .welcome-card .card-title {
        color: #e2e8f0;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 3px;
    }
    .welcome-card .card-desc {
        color: #64748b;
        font-size: 0.72rem;
        line-height: 1.4;
    }

    /* ---- Divider ---- */
    .subtle-divider {
        border: none;
        border-top: 1px solid rgba(99, 102, 241, 0.1);
        margin: 0.8rem 0;
    }

    /* ---- Streamlit button overrides ---- */
    .stButton > button {
        border-radius: 10px !important;
        border: 1px solid rgba(99, 102, 241, 0.25) !important;
        background: rgba(99, 102, 241, 0.08) !important;
        color: #c7d2fe !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        padding: 0.35rem 0.9rem !important;
        transition: all 0.2s ease !important;
        width: 100%;
    }
    .stButton > button:hover {
        background: rgba(99, 102, 241, 0.2) !important;
        border-color: rgba(99, 102, 241, 0.5) !important;
        color: #fff !important;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_backend_health():
    """Check if the FastAPI backend is reachable."""
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def send_message(message: str, session_id: str = None) -> dict:
    """Send a message to the chatbot API and return the response."""
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
        
    r = requests.post(
        f"{API_BASE_URL}/chat",
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def render_intent_badge(intent: str):
    """Render a colored intent badge."""
    if not intent:
        return ""
    emoji, color = INTENT_BADGES.get(intent, ("💬", "#64748b"))
    return f'<span class="intent-badge" style="background: {color}22; color: {color}; border: 1px solid {color}44;">{emoji} {intent}</span>'


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "backend_online" not in st.session_state:
    st.session_state.backend_online = check_backend_health()

if "pending_suggestion" not in st.session_state:
    st.session_state.pending_suggestion = None


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # Brand
    st.markdown("""
    <div class="sidebar-brand">
        <h2>📊 FBOT</h2>
        <p>Intelligent Trading Companion</p>
    </div>
    """, unsafe_allow_html=True)

    # Status
    is_online = st.session_state.backend_online
    status_color = "#22c55e" if is_online else "#ef4444"
    status_text = "Backend Online" if is_online else "Backend Offline"
    st.markdown(
        f'<div style="display:flex;align-items:center;padding:0.3rem 0;margin-bottom:0.5rem;">'
        f'<span class="status-dot" style="color:{status_color};background:{status_color};"></span>'
        f'<span style="color:{status_color};font-size:0.78rem;font-weight:500;">{status_text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not is_online:
        if st.button("🔄 Retry Connection"):
            st.session_state.backend_online = check_backend_health()
            st.rerun()

    # Quick Actions
    st.markdown('<div class="sidebar-section">⚡ Quick Actions</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Market", key="qa_market"):
            st.session_state.pending_suggestion = "How is the market today?"
            st.rerun()
    with col2:
        if st.button("📰 News", key="qa_news"):
            st.session_state.pending_suggestion = "Show me latest market news"
            st.rerun()

    col3, col4 = st.columns(2)
    with col3:
        if st.button("🔍 Screener", key="qa_screener"):
            st.session_state.pending_suggestion = "Show me available stock screens"
            st.rerun()
    with col4:
        if st.button("📈 NIFTY", key="qa_nifty"):
            st.session_state.pending_suggestion = "What is Nifty 50 at right now?"
            st.rerun()

    st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)

    # Popular Stocks
    st.markdown('<div class="sidebar-section">🔥 Popular Stocks</div>', unsafe_allow_html=True)

    popular_stocks = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
    cols = st.columns(len(popular_stocks))
    for i, stock in enumerate(popular_stocks):
        with cols[i]:
            if st.button(stock, key=f"stock_{stock}"):
                st.session_state.pending_suggestion = f"What is the price of {stock}?"
                st.rerun()

    st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)

    # Sample Questions
    st.markdown('<div class="sidebar-section">💡 Try Asking</div>', unsafe_allow_html=True)

    sample_questions = [
        "Why is the market going down?",
        "Compare TCS and Infosys",
        "Explain stop-loss orders",
        "Analyze Reliance stock",
        "Last 5 day movement of TCS",
        "Show me undervalued stocks",
    ]
    for q in sample_questions:
        if st.button(f"→ {q}", key=f"sample_{q}"):
            st.session_state.pending_suggestion = q
            st.rerun()

    st.markdown('<hr class="subtle-divider">', unsafe_allow_html=True)

    # Session Info
    st.markdown('<div class="sidebar-section">🔧 Session</div>', unsafe_allow_html=True)

    sid_display = st.session_state.session_id
    if sid_display:
        st.markdown(
            f'<p style="color:#475569;font-size:0.7rem;word-break:break-all;">ID: {sid_display}</p>',
            unsafe_allow_html=True,
        )

    if st.button("🗑️ Clear Chat", key="clear_chat"):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.rerun()


# ============================================================================
# MAIN CHAT AREA
# ============================================================================

# Hero header (only when chat is empty)
if not st.session_state.messages:
    st.markdown("""
    <div class="hero-header">
        <h1>FBOT</h1>
        <p>Your AI-Powered Financial Assistant — Ask me anything about stocks, markets & trading</p>
    </div>
    """, unsafe_allow_html=True)

    # Welcome cards
    st.markdown("""
    <div class="welcome-grid">
        <div class="welcome-card">
            <div class="card-icon">💰</div>
            <div class="card-title">Stock Prices</div>
            <div class="card-desc">Get real-time prices for any NSE/BSE stock</div>
        </div>
        <div class="welcome-card">
            <div class="card-icon">📊</div>
            <div class="card-title">Market Trends</div>
            <div class="card-desc">NIFTY, SENSEX & sector-wise performance</div>
        </div>
        <div class="welcome-card">
            <div class="card-icon">📰</div>
            <div class="card-title">Financial News</div>
            <div class="card-desc">Latest headlines affecting your investments</div>
        </div>
        <div class="welcome-card">
            <div class="card-icon">🔍</div>
            <div class="card-title">Stock Screener</div>
            <div class="card-desc">Find undervalued, momentum & oversold stocks</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("", unsafe_allow_html=True)


# Render existing chat messages
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "📊"):
        st.markdown(msg["content"])

        # Show intent badge and suggestions for assistant messages
        if msg["role"] == "assistant":
            if msg.get("intent"):
                badge_html = render_intent_badge(msg["intent"])
                st.markdown(badge_html, unsafe_allow_html=True)
                
            if msg.get("elapsed"):
                st.caption(f"⚡ {msg['elapsed']}s")

        # Render suggestion chips for the LAST assistant message only
        if (
            msg["role"] == "assistant"
            and msg.get("suggestions")
            and i == len(st.session_state.messages) - 1
        ):
            suggestions = msg["suggestions"]
            cols = st.columns(min(len(suggestions), 4))
            for j, sugg in enumerate(suggestions):
                with cols[j % 4]:
                    if st.button(f"💡 {sugg}", key=f"sugg_{i}_{j}"):
                        st.session_state.pending_suggestion = sugg
                        st.rerun()


# ============================================================================
# HANDLE INPUT (from chat box or suggestion click)
# ============================================================================

# Check for pending suggestion
user_input = None
if st.session_state.pending_suggestion:
    user_input = st.session_state.pending_suggestion
    st.session_state.pending_suggestion = None

# Quick-question chips ABOVE input
st.markdown("**Try asking:**")
chip_cols = st.columns(4)
chips = [("📊","Nifty today"), ("💰","Reliance price"),
         ("🔍","Undervalued stocks"), ("📚","Explain RSI")]
for i, (icon, q) in enumerate(chips):
    if chip_cols[i].button(f"{icon} {q}", key=f"chip_{i}", use_container_width=True):
        st.session_state["prefill"] = q
        st.rerun()

prefill = st.session_state.pop("prefill", None)
chat_input = st.chat_input("Ask about stocks, markets, trading...") or prefill

if chat_input:
    user_input = chat_input

# Process the input
if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # Get bot response — streaming
    with st.chat_message("assistant", avatar="📊"):
        message_placeholder = st.empty()
        status_placeholder = st.empty()
        full_response = ""
        metadata = {}
        start_time = time.time()

        try:
            with requests.post(
                f"{API_BASE_URL}/stream",
                json={"message": user_input,
                      "session_id": st.session_state.session_id},
                stream=True,
                timeout=60,
            ) as r:
                if r.status_code == 429:
                    st.warning("Rate limit reached. Please wait before asking again.")
                    st.stop()
                elif r.status_code != 200:
                    st.error(f"Backend error {r.status_code}. Check server logs.")
                    st.stop()

                for line in r.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

                    if data["type"] == "token":
                        full_response += data["content"]
                        message_placeholder.markdown(full_response + "▌")
                    elif data["type"] == "status":
                        status_placeholder.caption(data["content"])
                    elif data["type"] == "done":
                        metadata = data

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Run: `uvicorn main:app --reload`")
            st.stop()
        except requests.exceptions.Timeout:
            st.error("Request timed out. Try again.")
            st.stop()
        except requests.exceptions.ChunkedEncodingError:
            # Server dropped connection (e.g. hot-reload) — show what we received so far
            if not full_response:
                st.error("Connection lost. Please try again.")
                st.stop()

        elapsed = round(time.time() - start_time, 1)

        # Clear status indicator and streaming cursor
        status_placeholder.empty()
        message_placeholder.markdown(full_response)

        intent = metadata.get("intent")
        suggestions = metadata.get("suggestions", [])
        session_id = metadata.get("session_id")

        # Update session ID
        if session_id:
            st.session_state.session_id = session_id

        # Intent badge
        if intent:
            badge_html = render_intent_badge(intent)
            st.markdown(badge_html, unsafe_allow_html=True)

        st.caption(f"⚡ {elapsed}s")

        # Store the message
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "intent": intent,
            "suggestions": suggestions,
            "elapsed": elapsed
        })

        # Render suggestion chips
        if suggestions:
            cols = st.columns(min(len(suggestions), 4))
            for j, sugg in enumerate(suggestions):
                with cols[j % 4]:
                    if st.button(f"💡 {sugg}", key=f"new_sugg_{j}"):
                        st.session_state.pending_suggestion = sugg
                        st.rerun()
