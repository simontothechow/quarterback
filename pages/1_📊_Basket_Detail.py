"""
Quarterback - Basket Detail Page
================================
Detailed view of a specific basket with all component widgets.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import (
    get_cached_data, get_basket_positions, get_basket_list
)
from components.theme import apply_theme, COLORS
from components.widgets import (
    render_whole_basket_summary, render_derivatives_widget,
    render_physical_shares_widget, render_borrowing_lending_widget
)

# Page configuration
st.set_page_config(
    page_title="Basket Detail | Quarterback",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply theme
apply_theme()

# Load data
positions_df = get_cached_data('positions')
stock_data = get_cached_data('market_data')
corp_actions = get_cached_data('corp_actions')

# Get basket list
baskets = get_basket_list(positions_df)

# Sidebar - Back button and basket selection
with st.sidebar:
    if st.button("← Back to Home", key="back_btn", use_container_width=True):
        st.switch_page("app.py")
    
    st.markdown("---")
    st.markdown("### Select Basket")
    
    # Get selected basket from session state or default to first
    default_basket = st.session_state.get('selected_basket', baskets[0] if baskets else None)
    
    selected_basket = st.selectbox(
        "Basket",
        baskets,
        index=baskets.index(default_basket) if default_basket in baskets else 0,
        key="basket_selector"
    )
    
    # Store selection in session state
    st.session_state['selected_basket'] = selected_basket
    
    st.markdown("---")
    st.markdown("### Display Options")
    show_expanded = st.checkbox("Expanded Shares View", value=False)

    st.markdown("---")
    st.markdown("### Navigation")
    if st.button("📅 Calendar View", use_container_width=True):
        st.switch_page("pages/2_📅_Calendar.py")
    if st.button("🧾 Transactions", use_container_width=True):
        st.switch_page("pages/4_🧾_Transactions_Menu.py")

# Main content
if selected_basket:
    basket_positions = get_basket_positions(positions_df, selected_basket)
    
    if not basket_positions.empty:
        # Page header
        st.markdown(f"""
            <h1 style="display: flex; align-items: center; gap: 1rem;">
                <span>📊</span>
                <span>Basket Detail</span>
            </h1>
        """, unsafe_allow_html=True)
        
        # Whole basket summary
        render_whole_basket_summary(selected_basket, basket_positions)
        
        st.markdown("---")
        
        # Widgets section
        col1, col2 = st.columns(2)
        
        with col1:
            # Derivatives widget
            render_derivatives_widget(basket_positions)
        
        with col2:
            # Borrowing/Lending widget
            render_borrowing_lending_widget(basket_positions)
        
        # Physical shares widget (full width)
        st.markdown("---")
        render_physical_shares_widget(
            basket_positions, 
            stock_data, 
            corp_actions,
            basket_id=selected_basket,
            expanded=show_expanded
        )
        
    else:
        st.warning(f"No positions found for basket: {selected_basket}")
else:
    st.info("Please select a basket from the sidebar to view details.")
