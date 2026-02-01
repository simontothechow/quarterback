"""
Quarterback Trading Application
===============================
Main entry point for the Cash and Carry / Reverse Cash and Carry 
strategy management application.

Home Dashboard - Overview of all baskets with key metrics and alerts.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from modules.data_loader import (
    load_positions, load_stock_market_data, load_corporate_actions,
    get_cached_data, get_basket_list, get_basket_positions
)
from modules.calculations import calculate_basket_metrics, format_currency, format_bps
from components.theme import apply_theme, COLORS
from components.widgets import render_basket_summary_widget, get_basket_alerts

# Page configuration
st.set_page_config(
    page_title="Quarterback | Trading Dashboard",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom theme
apply_theme()

# Load all data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_all_data():
    positions = load_positions()
    market_data = load_stock_market_data()
    corp_actions = load_corporate_actions()
    return positions, market_data, corp_actions

positions_df, market_data, corp_actions = load_all_data()

# Get list of baskets
baskets = get_basket_list(positions_df)


def render_header():
    """Render the application header."""
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; 
                    padding: 0.5rem 0; margin-bottom: 1rem;">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <span style="font-size: 2.5rem;">🏈</span>
                <div>
                    <h1 style="margin: 0; padding: 0; border: none; font-size: 2rem;">QUARTERBACK</h1>
                    <span style="color: #808080; font-size: 0.9rem;">Cash & Carry Strategy Management</span>
                </div>
            </div>
            <div style="text-align: right; color: #808080;">
                <div style="font-size: 0.85rem;">Last Updated</div>
                <div style="color: #ff8c00; font-size: 1.1rem;">{}</div>
            </div>
        </div>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')), unsafe_allow_html=True)


def render_portfolio_summary():
    """Render the portfolio-wide summary metrics."""
    
    # Aggregate metrics across all baskets
    total_pnl = 0
    total_notional = 0
    total_net_exposure = 0
    total_daily_carry = 0
    alert_count = 0
    
    for basket_id in baskets:
        basket_positions = get_basket_positions(positions_df, basket_id)
        metrics = calculate_basket_metrics(basket_positions)
        
        total_pnl += metrics['total_pnl_usd']
        total_notional += metrics['total_notional']
        total_net_exposure += metrics['net_equity_exposure']
        total_daily_carry += metrics['daily_carry']
        
        if metrics['hedge_alert']:
            alert_count += 1
    
    # Calculate average PNL in BPS
    avg_pnl_bps = (total_pnl / total_notional * 10000) if total_notional > 0 else 0
    
    st.markdown("""
        <div style="background-color: #1a1a1a; border: 1px solid #333; border-radius: 6px; 
                    padding: 1.25rem; margin-bottom: 1.5rem;">
            <div style="color: #ff8c00; font-weight: 600; margin-bottom: 1rem; font-size: 1rem;
                        text-transform: uppercase; letter-spacing: 0.5px;">
                Portfolio Overview
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        pnl_color = "normal" if total_pnl >= 0 else "inverse"
        st.metric(
            "Total P&L",
            format_currency(total_pnl),
            format_bps(avg_pnl_bps),
            delta_color=pnl_color
        )
    
    with col2:
        st.metric(
            "Total Notional",
            f"${total_notional:,.0f}"
        )
    
    with col3:
        st.metric(
            "Net Equity Exposure",
            format_currency(total_net_exposure, include_sign=False)
        )
    
    with col4:
        st.metric(
            "Daily Carry",
            format_currency(total_daily_carry)
        )
    
    with col5:
        st.metric(
            "Active Baskets",
            len(baskets),
            f"{alert_count} alerts" if alert_count > 0 else "No alerts",
            delta_color="inverse" if alert_count > 0 else "off"
        )


def render_all_alerts():
    """Render a consolidated view of all alerts across baskets."""
    
    all_alerts = []
    for basket_id in baskets:
        basket_positions = get_basket_positions(positions_df, basket_id)
        alerts = get_basket_alerts(basket_id, basket_positions)
        for alert in alerts:
            alert['basket'] = basket_id
            all_alerts.append(alert)
    
    if all_alerts:
        st.markdown("""
            <div style="background-color: rgba(255, 68, 68, 0.1); border: 1px solid #ff4444; 
                        border-radius: 6px; padding: 1rem; margin-bottom: 1.5rem;">
                <div style="color: #ff4444; font-weight: 600; margin-bottom: 0.75rem; font-size: 1rem;">
                    ⚠️ ACTIVE ALERTS ({})
                </div>
        """.format(len(all_alerts)), unsafe_allow_html=True)
        
        for i, alert in enumerate(all_alerts):
            severity_color = "#ff4444" if alert['severity'] == 'high' else "#ffd700"
            
            # Create columns for clickable basket badge and alert message
            col1, col2 = st.columns([1, 6])
            
            with col1:
                # Clickable basket button
                if st.button(
                    alert['basket'], 
                    key=f"alert_basket_{i}",
                    help=f"Click to view {alert['basket']} details"
                ):
                    st.session_state['selected_basket'] = alert['basket']
                    st.switch_page("pages/1_📊_Basket_Detail.py")
            
            with col2:
                st.markdown(f"""
                    <div style="display: flex; align-items: center; padding: 0.3rem 0;">
                        <span style="color: {severity_color}; font-weight: 600; margin-right: 0.5rem;">
                            {alert['type']}:
                        </span>
                        <span style="color: #c0c0c0;">{alert['message']}</span>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)


def render_baskets_grid():
    """Render the grid of basket summaries."""
    
    st.markdown("""
        <div style="color: #ff8c00; font-weight: 600; margin: 1.5rem 0 1rem 0; font-size: 1.1rem;
                    text-transform: uppercase; letter-spacing: 0.5px;">
            Active Baskets
        </div>
    """, unsafe_allow_html=True)
    
    for basket_id in baskets:
        basket_positions = get_basket_positions(positions_df, basket_id)
        
        with st.container():
            render_basket_summary_widget(basket_id, basket_positions)
            
            # Add view details button
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button(f"View Details", key=f"view_{basket_id}"):
                    st.session_state['selected_basket'] = basket_id
                    st.switch_page("pages/1_📊_Basket_Detail.py")
        
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)


# Sidebar
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <span style="font-size: 3rem;">🏈</span>
            <h2 style="color: #ff8c00; margin: 0.5rem 0;">QUARTERBACK</h2>
            <p style="color: #808080; font-size: 0.85rem;">v1.0 Demo</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### Navigation")
    
    if st.button("🏠 Home Dashboard", use_container_width=True):
        pass  # Already on home
    
    if st.button("📅 Calendar View", use_container_width=True):
        st.switch_page("pages/2_📅_Calendar.py")

    if st.button("🧾 Transactions", use_container_width=True):
        st.switch_page("pages/4_🧾_Transactions_Menu.py")
    
    st.markdown("---")
    
    st.markdown("### Quick Actions")
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    st.markdown("### Data Status")
    st.markdown(f"""
        <div style="font-size: 0.85rem; color: #808080;">
            <div style="margin-bottom: 0.5rem;">
                <span style="color: #00d26a;">●</span> Positions: {len(positions_df)} records
            </div>
            <div style="margin-bottom: 0.5rem;">
                <span style="color: #00d26a;">●</span> Market Data: {len(market_data)} stocks
            </div>
            <div style="margin-bottom: 0.5rem;">
                <span style="color: #00d26a;">●</span> Corp Actions: {len(corp_actions)} events
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
        <div style="color: #808080; font-size: 0.75rem; text-align: center;">
            © 2026 Quarterback Trading Systems<br>
            Demo Version
        </div>
    """, unsafe_allow_html=True)


# Main content
render_header()
render_portfolio_summary()
render_all_alerts()
render_baskets_grid()

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #808080; font-size: 0.85rem; padding: 1rem;">
        <strong>Quarterback</strong> - Cash & Carry Strategy Management System | 
        Underlying: S&P 500 AIR Futures | 
        Data as of: {}
    </div>
""".format(datetime.now().strftime('%Y-%m-%d')), unsafe_allow_html=True)
