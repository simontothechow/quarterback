"""
Quarterback - Quick Futures Trade Page
======================================
Standalone page for executing futures trades without full basket context.
Accessible via sidebar menu.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import uuid
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import get_cached_data, get_basket_list
from components.theme import COLORS
from modules.calculations import (
    calculate_futures_contracts_from_notional,
    SPX_FUTURES_MULTIPLIER,
)


def _ensure_trade_blotter():
    """Initialize the demo trade blotter in session state."""
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


# Demo counterparties
FUTURES_COUNTERPARTIES = ["CME Globex", "ICE Futures", "Eurex", "Bloomberg EMSX"]


def render_quick_futures_page():
    """Render the quick futures trade page."""
    
    _ensure_trade_blotter()
    
    # Load data for basket selection
    positions_df = get_cached_data('positions')
    baskets = get_basket_list(positions_df)
    
    # Header
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.switch_page("app.py")
    with col3:
        if st.button("🧾 Blotter", use_container_width=True):
            st.switch_page("pages/4_🧾_Transactions_Menu.py")
    
    st.markdown("""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>📊</span>
            <span>Quick Futures Trade</span>
        </h1>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <p style="color: #808080; margin-bottom: 2rem;">
            Execute a standalone futures trade or associate with an existing basket.
        </p>
    """, unsafe_allow_html=True)
    
    # Initialize session state for form
    if 'qf_basket_option' not in st.session_state:
        st.session_state['qf_basket_option'] = "Standalone (No Basket)"
    if 'qf_notional' not in st.session_state:
        st.session_state['qf_notional'] = 10_000_000.0
    if 'qf_direction' not in st.session_state:
        st.session_state['qf_direction'] = "LONG"
    
    # --- Trade Configuration ---
    st.markdown("### Trade Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Basket association
        basket_options = ["Standalone (No Basket)"] + baskets
        selected_basket_option = st.selectbox(
            "Basket Association",
            basket_options,
            index=basket_options.index(st.session_state.get('qf_basket_option', "Standalone (No Basket)")),
            key="qf_basket_select",
            help="Associate this trade with an existing basket or keep it standalone"
        )
        st.session_state['qf_basket_option'] = selected_basket_option
        
        basket_id = "" if selected_basket_option == "Standalone (No Basket)" else selected_basket_option
    
    with col2:
        # Trade direction
        direction = st.radio(
            "Direction",
            ["LONG", "SHORT"],
            horizontal=True,
            index=0 if st.session_state.get('qf_direction', 'LONG') == 'LONG' else 1,
            key="qf_direction_radio"
        )
        st.session_state['qf_direction'] = direction
    
    st.markdown("---")
    
    # --- Contract Details ---
    st.markdown("### Contract Details")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Trade date
        trade_date = st.date_input(
            "Trade Date",
            value=datetime.now().date(),
            key="qf_trade_date"
        )
    
    with col2:
        # Contract month (demo - simplified)
        contract_months = ["Mar 2026", "Jun 2026", "Sep 2026", "Dec 2026"]
        contract_month = st.selectbox(
            "Contract Month",
            contract_months,
            index=0,
            key="qf_contract_month"
        )
    
    with col3:
        # Counterparty
        counterparty = st.selectbox(
            "Exchange / Counterparty",
            FUTURES_COUNTERPARTIES,
            index=0,
            key="qf_counterparty"
        )
    
    st.markdown("---")
    
    # --- Sizing ---
    st.markdown("### Sizing")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Futures price (demo)
        futures_price = st.number_input(
            "Futures Price",
            min_value=1000.0,
            max_value=10000.0,
            value=6050.0,
            step=1.0,
            format="%.2f",
            key="qf_futures_price"
        )
    
    with col2:
        # Notional input
        notional = st.number_input(
            "Notional ($)",
            min_value=0.0,
            value=st.session_state.get('qf_notional', 10_000_000.0),
            step=1_000_000.0,
            format="%.0f",
            key="qf_notional_input",
            help="Enter the desired notional exposure"
        )
        st.session_state['qf_notional'] = notional
    
    with col3:
        # Calculate equivalent contracts
        contracts = calculate_futures_contracts_from_notional(notional, futures_price)
        st.metric(
            "Equivalent Contracts",
            f"{contracts:,}",
            help=f"Based on ${SPX_FUTURES_MULTIPLIER:,} multiplier"
        )
    
    # Display calculated notional from contracts
    actual_notional = contracts * futures_price * SPX_FUTURES_MULTIPLIER
    st.info(f"**Actual Notional (rounded):** ${actual_notional:,.0f}")
    
    st.markdown("---")
    
    # --- Trade Summary ---
    st.markdown("### Trade Summary")
    
    direction_color = COLORS['accent_green'] if direction == 'LONG' else COLORS['accent_red']
    
    st.markdown(f"""
        <div style="background-color: #1a1a1a; border: 2px solid {direction_color}; border-radius: 8px; 
                    padding: 1.5rem; margin: 1rem 0;">
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem;">
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Direction</div>
                    <div style="color: {direction_color}; font-size: 1.5rem; font-weight: 700;">{direction}</div>
                </div>
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Contracts</div>
                    <div style="color: #fff; font-size: 1.5rem; font-weight: 700;">{contracts:,}</div>
                </div>
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Notional</div>
                    <div style="color: #fff; font-size: 1.5rem; font-weight: 700;">${actual_notional:,.0f}</div>
                </div>
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Contract</div>
                    <div style="color: #fff; font-size: 1.5rem; font-weight: 700;">ES {contract_month}</div>
                </div>
            </div>
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #333;">
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
                    <div>
                        <span style="color: #808080;">Trade Date: </span>
                        <span style="color: #fff;">{trade_date.strftime('%Y-%m-%d')}</span>
                    </div>
                    <div>
                        <span style="color: #808080;">Counterparty: </span>
                        <span style="color: #fff;">{counterparty}</span>
                    </div>
                    <div>
                        <span style="color: #808080;">Basket: </span>
                        <span style="color: #ff8c00;">{basket_id if basket_id else 'Standalone'}</span>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- Action Buttons ---
    col1, col2, col3 = st.columns([2, 2, 4])
    
    with col1:
        if st.button("🚀 Confirm & Generate Order", use_container_width=True, type="primary"):
            if contracts <= 0:
                st.error("Please enter a valid notional amount.")
            else:
                # Add to trade blotter
                signed_contracts = contracts if direction == "LONG" else -contracts
                signed_notional = actual_notional if direction == "LONG" else -actual_notional
                
                trade = {
                    "id": uuid.uuid4().hex,
                    "trade_type": "FUTURES",
                    "ticker": f"ES {contract_month}",
                    "instrument": "S&P 500 E-mini Future",
                    "side": "BUY" if direction == "LONG" else "SELL",
                    "contracts": signed_contracts,
                    "shares": None,
                    "price": float(futures_price),
                    "notional": float(signed_notional),
                    "estimated_value": float(abs(signed_notional)),
                    "basket_id": basket_id if basket_id else "STANDALONE",
                    "counterparty": counterparty,
                    "trade_date": trade_date.strftime("%Y-%m-%d"),
                    "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "execution_date": trade_date.strftime("%Y-%m-%d"),
                    "status": "SUBMITTED",
                    "route": counterparty,
                }
                st.session_state["trade_blotter"].append(trade)
                
                st.success(f"✅ Futures trade submitted! {direction} {contracts:,} contracts @ {futures_price:,.2f}")
                st.balloons()
    
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.switch_page("app.py")


# Main
render_quick_futures_page()
