"""
Quarterback Trading Application
===============================
Main entry point with centralized navigation control.
Uses st.navigation() API to manage sidebar page visibility.
"""

import streamlit as st
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from modules.data_loader import load_positions, load_stock_market_data, load_corporate_actions
from components.theme import apply_theme
from components.navigation import render_sidebar_header, render_sidebar_footer, render_sidebar_data_status

# =============================================================================
# PAGE CONFIGURATION - Must be first Streamlit command
# =============================================================================
st.set_page_config(
    page_title="Quarterback | Trading Dashboard",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom theme
apply_theme()

# =============================================================================
# LOAD DATA FOR SIDEBAR STATS
# =============================================================================
@st.cache_data(ttl=300)
def load_all_data():
    positions = load_positions()
    market_data = load_stock_market_data()
    corp_actions = load_corporate_actions()
    return positions, market_data, corp_actions

positions_df, market_data, corp_actions = load_all_data()

# =============================================================================
# DEFINE ALL PAGES
# =============================================================================

# Main navigation pages (visible in sidebar)
home_page = st.Page("pages/0_🏠_Home.py", title="Home", icon="🏠", default=True)
basket_detail_page = st.Page("pages/1_📊_Basket_Detail.py", title="Basket Detail", icon="📊")
calendar_page = st.Page("pages/2_📅_Calendar.py", title="Calendar", icon="📅")
transactions_page = st.Page("pages/4_🧾_Transactions_Menu.py", title="Transactions", icon="🧾")
new_basket_page = st.Page("pages/9_📦_New_Basket.py", title="New Basket", icon="📦")

# Quick trade pages (visible in sidebar under separate section)
quick_futures_page = st.Page("pages/10_📊_Quick_Futures.py", title="Quick Futures", icon="📊")
quick_equity_page = st.Page("pages/11_📈_Quick_Equity.py", title="Quick Equity", icon="📈")
quick_cash_page = st.Page("pages/12_💰_Quick_Cash.py", title="Quick Cash", icon="💰")

# Markets page (calendar spread opportunity scanner)
markets_page = st.Page("pages/13_🌐_Markets.py", title="Markets", icon="🌐")

# Opportunities page (multi-strategy financing arbitrage scanner)
opportunities_page = st.Page("pages/14_💹_Opportunities.py", title="Opportunities", icon="💹")

# Hidden pages (accessible via st.switch_page but NOT shown in sidebar)
hidden_basket_txn = st.Page("pages/__Basket_Transaction.py", title="Basket Transaction")
hidden_futures_txn = st.Page("pages/__Futures_Transaction.py", title="Futures Transaction")
hidden_cash_txn = st.Page("pages/__Cash_Transaction.py", title="Cash Transaction")
hidden_equity_txn = st.Page("pages/__Equity_Transaction.py", title="Equity Transaction")
hidden_transaction = st.Page("pages/__Transaction.py", title="Transaction")

# =============================================================================
# NAVIGATION SETUP
# =============================================================================

# CSS to hide the "Hidden" section from the sidebar
# This section contains pages accessible via st.switch_page() but not shown in nav
st.markdown("""
<style>
    /* Hide the "Hidden" section from sidebar navigation */
    [data-testid="stSidebarNav"] > ul > li:last-child {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Create navigation with organized sections
# Hidden pages MUST be included for st.switch_page() to work
pg = st.navigation(
    {
        "Main": [home_page, basket_detail_page, calendar_page, transactions_page, new_basket_page],
        "Quick Trades": [quick_futures_page, quick_equity_page, quick_cash_page],
        "Markets": [markets_page],
        "Opportunities": [opportunities_page],
        "Hidden": [hidden_basket_txn, hidden_futures_txn, hidden_cash_txn, hidden_equity_txn, hidden_transaction],
    },
    position="sidebar"
)

# =============================================================================
# SIDEBAR CONTENT (below navigation)
# =============================================================================
with st.sidebar:
    st.markdown("---")
    
    # Quick Actions
    st.markdown("### Quick Actions")
    if st.button("🔄 Refresh Data", use_container_width=True, key="main_refresh"):
        st.cache_data.clear()
        st.rerun()
    
    # Data Status
    render_sidebar_data_status(len(positions_df), len(market_data), len(corp_actions))
    
    # Footer
    render_sidebar_footer()

# =============================================================================
# RUN THE SELECTED PAGE
# =============================================================================
pg.run()
