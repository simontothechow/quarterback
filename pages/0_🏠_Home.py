"""
Quarterback Home Dashboard
==========================
Overview of all baskets with key metrics and alerts.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import (
    load_positions, load_stock_market_data, load_corporate_actions,
    get_cached_data, get_basket_list, get_basket_positions
)
from modules.calculations import calculate_basket_metrics, format_currency, format_bps
from components.widgets import render_basket_summary_widget, get_basket_alerts


def render_home_page():
    """Render the home dashboard page."""
    
    # Load data
    positions_df = get_cached_data('positions')
    if positions_df is None:
        positions_df = load_positions()
    
    market_data = get_cached_data('market_data')
    if market_data is None:
        market_data = load_stock_market_data()
    
    baskets = get_basket_list(positions_df)
    
    # Header
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
    
    # Portfolio Summary
    render_portfolio_summary(positions_df, baskets)
    
    # Alerts
    render_all_alerts(positions_df, baskets)
    
    # Baskets Grid
    render_baskets_grid(positions_df, baskets)
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #808080; font-size: 0.85rem; padding: 1rem;">
            <strong>Quarterback</strong> - Cash & Carry Strategy Management System | 
            Underlying: S&P 500 AIR Futures | 
            Data as of: {}
        </div>
    """.format(datetime.now().strftime('%Y-%m-%d')), unsafe_allow_html=True)


def render_portfolio_summary(positions_df, baskets):
    """Render the portfolio-wide summary metrics."""
    
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
        st.metric("Total P&L", format_currency(total_pnl), format_bps(avg_pnl_bps), delta_color=pnl_color)
    
    with col2:
        st.metric("Total Notional", f"${total_notional:,.0f}")
    
    with col3:
        st.metric("Net Equity Exposure", format_currency(total_net_exposure, include_sign=False))
    
    with col4:
        st.metric("Daily Carry", format_currency(total_daily_carry))
    
    with col5:
        st.metric(
            "Active Baskets",
            len(baskets),
            f"{alert_count} alerts" if alert_count > 0 else "No alerts",
            delta_color="inverse" if alert_count > 0 else "off"
        )


def render_all_alerts(positions_df, baskets):
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
            
            col1, col2 = st.columns([1, 6])
            
            with col1:
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


def render_baskets_grid(positions_df, baskets):
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
            
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button(f"View Details", key=f"view_{basket_id}"):
                    st.session_state['selected_basket'] = basket_id
                    st.switch_page("pages/1_📊_Basket_Detail.py")
        
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)


# Run the page
render_home_page()
