"""
Quarterback - Quick Cash Trade Page
====================================
Standalone page for executing cash borrow/lend trades.
Accessible via sidebar menu.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import uuid
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import get_cached_data, get_basket_list
from components.theme import COLORS


def _ensure_trade_blotter():
    """Initialize the demo trade blotter in session state."""
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


# Demo counterparties
CASH_COUNTERPARTIES = ["Goldman Sachs", "JP Morgan", "Bank of America", "Citigroup", "Wells Fargo", "State Street"]

# Rate types
RATE_TYPES = ["SOFR", "Fed Funds", "LIBOR", "Fixed"]


def render_quick_cash_page():
    """Render the quick cash borrow/lend trade page."""
    
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
            <span>💰</span>
            <span>Quick Cash Trade</span>
        </h1>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <p style="color: #808080; margin-bottom: 2rem;">
            Execute a standalone cash borrowing or lending transaction.
        </p>
    """, unsafe_allow_html=True)
    
    # Initialize session state for form
    if 'qc_basket_option' not in st.session_state:
        st.session_state['qc_basket_option'] = "Standalone (No Basket)"
    if 'qc_notional' not in st.session_state:
        st.session_state['qc_notional'] = 10_000_000.0
    if 'qc_trade_type' not in st.session_state:
        st.session_state['qc_trade_type'] = "Cash Borrowing"
    
    # --- Trade Configuration ---
    st.markdown("### Trade Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Basket association
        basket_options = ["Standalone (No Basket)"] + baskets
        selected_basket_option = st.selectbox(
            "Basket Association",
            basket_options,
            index=basket_options.index(st.session_state.get('qc_basket_option', "Standalone (No Basket)")),
            key="qc_basket_select",
            help="Associate this trade with an existing basket or keep it standalone"
        )
        st.session_state['qc_basket_option'] = selected_basket_option
        basket_id = "" if selected_basket_option == "Standalone (No Basket)" else selected_basket_option
    
    with col2:
        # Trade type
        trade_type = st.radio(
            "Transaction Type",
            ["Cash Borrowing", "Cash Lending"],
            horizontal=True,
            index=0 if st.session_state.get('qc_trade_type', 'Cash Borrowing') == 'Cash Borrowing' else 1,
            key="qc_trade_type_radio",
            help="Borrowing = You receive cash (pay interest) | Lending = You provide cash (receive interest)"
        )
        st.session_state['qc_trade_type'] = trade_type
    
    # Visual indicator for cash flow direction
    if trade_type == "Cash Borrowing":
        st.markdown("""
            <div style="background-color: rgba(255, 68, 68, 0.1); border-left: 4px solid #ff4444; 
                        padding: 0.75rem 1rem; margin: 1rem 0; border-radius: 0 4px 4px 0;">
                <span style="color: #ff4444; font-weight: 600;">🔻 Cash Borrowing:</span>
                <span style="color: #c0c0c0;"> You receive cash now and pay it back with interest at maturity.</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background-color: rgba(0, 210, 106, 0.1); border-left: 4px solid #00d26a; 
                        padding: 0.75rem 1rem; margin: 1rem 0; border-radius: 0 4px 4px 0;">
                <span style="color: #00d26a; font-weight: 600;">🔺 Cash Lending:</span>
                <span style="color: #c0c0c0;"> You provide cash now and receive it back with interest at maturity.</span>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- Trade Details ---
    st.markdown("### Trade Details")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        trade_date = st.date_input(
            "Trade Date",
            value=datetime.now().date(),
            key="qc_trade_date"
        )
    
    with col2:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now().date(),
            key="qc_start_date"
        )
    
    with col3:
        maturity_date = st.date_input(
            "Maturity Date",
            value=datetime.now().date() + timedelta(days=90),
            key="qc_maturity_date"
        )
    
    # Calculate term
    term_days = (maturity_date - start_date).days
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        counterparty = st.selectbox(
            "Counterparty",
            CASH_COUNTERPARTIES,
            index=0,
            key="qc_counterparty"
        )
    
    with col2:
        rate_type = st.selectbox(
            "Rate Type",
            RATE_TYPES,
            index=0,
            key="qc_rate_type"
        )
    
    with col3:
        rate = st.number_input(
            "Rate (%)",
            min_value=0.0,
            max_value=20.0,
            value=5.25,
            step=0.01,
            format="%.2f",
            key="qc_rate",
            help="Annual interest rate"
        )
    
    st.markdown("---")
    
    # --- Sizing ---
    st.markdown("### Sizing")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        notional = st.number_input(
            "Principal Amount ($)",
            min_value=0.0,
            value=st.session_state.get('qc_notional', 10_000_000.0),
            step=1_000_000.0,
            format="%.0f",
            key="qc_notional_input",
            help="The principal amount to borrow or lend"
        )
        st.session_state['qc_notional'] = notional
    
    with col2:
        # Calculate estimated interest
        interest = notional * (rate / 100) * (term_days / 365)
        st.metric(
            "Estimated Interest",
            f"${interest:,.2f}",
            help=f"Based on {term_days} day term at {rate}% annual rate"
        )
    
    with col3:
        # Calculate maturity value
        if trade_type == "Cash Borrowing":
            maturity_value = notional + interest  # You pay back principal + interest
            st.metric(
                "Repayment at Maturity",
                f"${maturity_value:,.2f}",
                delta=f"-${interest:,.2f}",
                delta_color="inverse"
            )
        else:
            maturity_value = notional + interest  # You receive principal + interest
            st.metric(
                "Receive at Maturity",
                f"${maturity_value:,.2f}",
                delta=f"+${interest:,.2f}",
                delta_color="normal"
            )
    
    st.markdown("---")
    
    # --- Trade Summary ---
    st.markdown("### Trade Summary")
    
    if trade_type == "Cash Borrowing":
        direction_color = COLORS['accent_red']
        icon = "🔻"
        position_type = "CASH_BORROW"
    else:
        direction_color = COLORS['accent_green']
        icon = "🔺"
        position_type = "CASH_LEND"
    
    st.markdown(f"""
        <div style="background-color: #1a1a1a; border: 2px solid {direction_color}; border-radius: 8px; 
                    padding: 1.5rem; margin: 1rem 0;">
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem;">
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Type</div>
                    <div style="color: {direction_color}; font-size: 1.5rem; font-weight: 700;">{icon} {trade_type}</div>
                </div>
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Principal</div>
                    <div style="color: #fff; font-size: 1.5rem; font-weight: 700;">${notional:,.0f}</div>
                </div>
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Rate ({rate_type})</div>
                    <div style="color: #fff; font-size: 1.5rem; font-weight: 700;">{rate:.2f}%</div>
                </div>
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Term</div>
                    <div style="color: #fff; font-size: 1.5rem; font-weight: 700;">{term_days} days</div>
                </div>
            </div>
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #333;">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
                    <div>
                        <span style="color: #808080;">Trade Date: </span>
                        <span style="color: #fff;">{trade_date.strftime('%Y-%m-%d')}</span>
                    </div>
                    <div>
                        <span style="color: #808080;">Start Date: </span>
                        <span style="color: #fff;">{start_date.strftime('%Y-%m-%d')}</span>
                    </div>
                    <div>
                        <span style="color: #808080;">Maturity: </span>
                        <span style="color: #fff;">{maturity_date.strftime('%Y-%m-%d')}</span>
                    </div>
                    <div>
                        <span style="color: #808080;">Basket: </span>
                        <span style="color: #ff8c00;">{basket_id if basket_id else 'Standalone'}</span>
                    </div>
                </div>
            </div>
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #333;">
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                    <div>
                        <span style="color: #808080;">Counterparty: </span>
                        <span style="color: #fff;">{counterparty}</span>
                    </div>
                    <div>
                        <span style="color: #808080;">Est. Interest: </span>
                        <span style="color: {direction_color};">${interest:,.2f}</span>
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
            if notional <= 0:
                st.error("Please enter a valid principal amount.")
            elif term_days <= 0:
                st.error("Maturity date must be after start date.")
            else:
                # Add to trade blotter
                # For cash borrow: notional is negative (you owe)
                # For cash lend: notional is positive (you're owed)
                signed_notional = -notional if trade_type == "Cash Borrowing" else notional
                
                trade = {
                    "id": uuid.uuid4().hex,
                    "trade_type": position_type,
                    "ticker": f"{trade_type.upper().replace(' ', '_')}",
                    "instrument": f"{trade_type} @ {rate:.2f}% {rate_type}",
                    "side": "BORROW" if trade_type == "Cash Borrowing" else "LEND",
                    "contracts": None,
                    "shares": None,
                    "price": float(rate),
                    "notional": float(signed_notional),
                    "estimated_value": float(abs(notional)),
                    "interest": float(interest),
                    "basket_id": basket_id if basket_id else "STANDALONE",
                    "counterparty": counterparty,
                    "trade_date": trade_date.strftime("%Y-%m-%d"),
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "maturity_date": maturity_date.strftime("%Y-%m-%d"),
                    "rate": float(rate),
                    "rate_type": rate_type,
                    "term_days": term_days,
                    "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "execution_date": start_date.strftime("%Y-%m-%d"),
                    "status": "SUBMITTED",
                    "route": counterparty,
                }
                st.session_state["trade_blotter"].append(trade)
                
                st.success(f"✅ Cash trade submitted! {trade_type} ${notional:,.0f} @ {rate:.2f}% for {term_days} days")
                st.balloons()
    
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.switch_page("app.py")


# Main
render_quick_cash_page()
