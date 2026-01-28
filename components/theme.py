"""
Quarterback Theme Module
========================
Bloomberg Terminal-inspired dark theme styling for Streamlit.
"""

import streamlit as st

# Color palette - Bloomberg Terminal inspired
COLORS = {
    # Primary backgrounds
    'bg_primary': '#0a0a0a',        # Near black
    'bg_secondary': '#1a1a1a',      # Dark gray
    'bg_card': '#1e1e1e',           # Card background
    'bg_highlight': '#252525',       # Highlighted areas
    
    # Text colors
    'text_primary': '#ff8c00',       # Bloomberg orange
    'text_secondary': '#c0c0c0',     # Light gray
    'text_muted': '#808080',         # Muted gray
    'text_white': '#ffffff',         # Pure white
    
    # Accent colors
    'accent_orange': '#ff8c00',      # Primary orange
    'accent_green': '#00d26a',       # Positive/profit green
    'accent_red': '#ff4444',         # Negative/loss red
    'accent_blue': '#0088ff',        # Info blue
    'accent_yellow': '#ffd700',      # Warning yellow
    
    # Border colors
    'border_dark': '#333333',
    'border_light': '#444444',
}

# Custom CSS for Bloomberg-style appearance
CUSTOM_CSS = """
<style>
    /* Import fonts including Material Icons for proper icon rendering */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=Material+Icons&family=Material+Icons+Outlined&display=swap');
    
    /* Main app background */
    .stApp {
        background-color: #0a0a0a;
    }
    
    /* Main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        color: #ff8c00 !important;
        font-weight: 600 !important;
    }
    
    h1 {
        font-size: 2.2rem !important;
        border-bottom: 2px solid #ff8c00;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem !important;
    }
    
    /* Regular text */
    p, span, div, label {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Metric containers */
    [data-testid="stMetric"] {
        background-color: #1e1e1e;
        border: 1px solid #333333;
        border-radius: 4px;
        padding: 1rem;
    }
    
    [data-testid="stMetricLabel"] {
        color: #808080 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stMetricDelta"] > div {
        font-size: 0.85rem !important;
    }
    
    /* Data frames / tables */
    .stDataFrame {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    [data-testid="stDataFrame"] > div {
        background-color: #1e1e1e;
        border: 1px solid #333333;
        border-radius: 4px;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #1e1e1e;
        color: #ff8c00;
        border: 1px solid #ff8c00;
        border-radius: 4px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #ff8c00;
        color: #0a0a0a;
        border-color: #ff8c00;
    }
    
    /* Primary action buttons */
    .stButton > button[kind="primary"] {
        background-color: #ff8c00;
        color: #0a0a0a;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a;
        border-right: 1px solid #333333;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ff8c00 !important;
    }
    
    /* Select boxes */
    .stSelectbox > div > div {
        background-color: #1e1e1e;
        border-color: #333333;
    }
    
    /* Multi-select */
    .stMultiSelect > div > div {
        background-color: #1e1e1e;
        border-color: #333333;
    }
    
    /* Expander - Updated for newer Streamlit versions */
    [data-testid="stExpander"] {
        background-color: #1e1e1e;
        border: 1px solid #333333;
        border-radius: 4px;
    }
    
    [data-testid="stExpander"] summary {
        background-color: #1e1e1e;
        color: #ff8c00 !important;
        font-family: 'Inter', sans-serif !important;
        padding: 0.75rem 1rem;
    }
    
    [data-testid="stExpander"] summary:hover {
        background-color: #252525;
    }
    
    [data-testid="stExpander"] summary span {
        color: #ff8c00 !important;
    }
    
    /* Fix icon rendering in expander */
    [data-testid="stExpander"] summary svg {
        display: inline-block;
        vertical-align: middle;
        margin-right: 0.5rem;
    }
    
    /* Hide any text-based icon fallbacks and fix text overlap */
    [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p {
        display: inline;
    }
    
    /* Ensure expander toggle icon renders correctly */
    [data-testid="stExpander"] details summary::before,
    [data-testid="stExpander"] details summary::marker {
        font-family: 'Material Icons', sans-serif !important;
    }
    
    /* Fix for icon text fallback showing as "arrow_right" */
    [data-testid="stExpander"] summary .material-icons,
    [data-testid="stExpander"] summary [class*="icon"] {
        font-family: 'Material Icons' !important;
        font-size: 1.2rem;
        vertical-align: middle;
    }
    
    [data-testid="stExpanderDetails"] {
        background-color: #1a1a1a;
        border-top: 1px solid #333333;
        padding: 1rem;
    }
    
    /* Legacy expander classes for compatibility */
    .streamlit-expanderHeader {
        background-color: #1e1e1e;
        border: 1px solid #333333;
        border-radius: 4px;
        color: #ff8c00 !important;
    }
    
    .streamlit-expanderContent {
        background-color: #1a1a1a;
        border: 1px solid #333333;
        border-top: none;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1a1a1a;
        border-bottom: 1px solid #333333;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #808080;
        font-family: 'Inter', sans-serif;
    }
    
    .stTabs [aria-selected="true"] {
        color: #ff8c00 !important;
        border-bottom-color: #ff8c00 !important;
    }
    
    /* Alert boxes */
    .stAlert {
        background-color: #1e1e1e;
        border: 1px solid #333333;
        border-radius: 4px;
    }
    
    /* Success message */
    .stSuccess {
        background-color: rgba(0, 210, 106, 0.1);
        border-color: #00d26a;
    }
    
    /* Warning message */
    .stWarning {
        background-color: rgba(255, 215, 0, 0.1);
        border-color: #ffd700;
    }
    
    /* Error message */
    .stError {
        background-color: rgba(255, 68, 68, 0.1);
        border-color: #ff4444;
    }
    
    /* Custom card class */
    .qb-card {
        background-color: #1e1e1e;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    
    .qb-card-header {
        color: #ff8c00;
        font-size: 1rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #333333;
    }
    
    /* Positive/negative value colors */
    .positive {
        color: #00d26a !important;
    }
    
    .negative {
        color: #ff4444 !important;
    }
    
    .neutral {
        color: #c0c0c0 !important;
    }
    
    /* Alert badge */
    .alert-badge {
        background-color: #ff4444;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* Active status badge */
    .status-active {
        background-color: #00d26a;
        color: #0a0a0a;
        padding: 0.2rem 0.5rem;
        border-radius: 3px;
        font-size: 0.7rem;
        font-weight: 600;
    }
    
    .status-pending {
        background-color: #ffd700;
        color: #0a0a0a;
        padding: 0.2rem 0.5rem;
        border-radius: 3px;
        font-size: 0.7rem;
        font-weight: 600;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a1a1a;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #444444;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #555555;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""


def apply_theme():
    """Apply the Bloomberg-inspired dark theme to the Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, delta: str = None, 
                       delta_color: str = "normal") -> None:
    """
    Render a styled metric card.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta/change value
        delta_color: Color for delta ("normal", "inverse", or "off")
    """
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def render_card(title: str, content_func) -> None:
    """
    Render a styled card container.
    
    Args:
        title: Card title
        content_func: Function that renders the card content
    """
    st.markdown(f"""
        <div class="qb-card">
            <div class="qb-card-header">{title}</div>
        </div>
    """, unsafe_allow_html=True)
    content_func()


def format_value_with_color(value: float, is_currency: bool = True, 
                            invert: bool = False) -> str:
    """
    Format a value with appropriate color class.
    
    Args:
        value: Numeric value
        is_currency: Whether to format as currency
        invert: Whether to invert positive/negative colors
    
    Returns:
        HTML string with colored value
    """
    if value > 0:
        color_class = "negative" if invert else "positive"
        sign = "+"
    elif value < 0:
        color_class = "positive" if invert else "negative"
        sign = ""
    else:
        color_class = "neutral"
        sign = ""
    
    if is_currency:
        formatted = f"{sign}${abs(value):,.0f}"
    else:
        formatted = f"{sign}{value:,.2f}"
    
    return f'<span class="{color_class}">{formatted}</span>'


def render_alert_badge(text: str) -> str:
    """
    Render an alert badge.
    
    Args:
        text: Badge text
    
    Returns:
        HTML string for alert badge
    """
    return f'<span class="alert-badge">{text}</span>'


def render_status_badge(status: str) -> str:
    """
    Render a status badge.
    
    Args:
        status: Status text (ACTIVE, PENDING, etc.)
    
    Returns:
        HTML string for status badge
    """
    status_lower = status.lower()
    if status_lower == 'active':
        return f'<span class="status-active">{status}</span>'
    elif status_lower == 'pending':
        return f'<span class="status-pending">{status}</span>'
    return status


def get_pnl_color(value: float) -> str:
    """Get color for P&L value."""
    if value > 0:
        return COLORS['accent_green']
    elif value < 0:
        return COLORS['accent_red']
    return COLORS['text_secondary']
