"""
Quarterback - Cash Borrow/Lend Transaction Page
================================================
Transaction page for unwinding or resizing cash borrowing/lending positions.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import get_cached_data
from components.theme import apply_theme, COLORS
from modules.calculations import (
    calculate_unwind_trades_cash,
    calculate_resize_trades_cash,
    calculate_basket_component_totals,
)

# Page configuration
st.set_page_config(
    page_title="Cash Transaction | Quarterback",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply theme
apply_theme()


def _ensure_trade_blotter():
    """Initialize the demo trade blotter in session state."""
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


def render_cash_transaction_page(txn_data: dict):
    """Render the cash borrow/lend transaction page."""
    
    _ensure_trade_blotter()
    
    basket_id = txn_data.get('basket_id', '')
    mode = txn_data.get('mode', 'resize')
    position_type = txn_data.get('position_type', 'CASH_BORROW')
    positions_df = txn_data.get('positions_df')
    
    if positions_df is None:
        positions_df = get_cached_data('positions')
    
    # Get current cash position info
    cash_mask = (positions_df['BASKET_ID'] == basket_id) & \
                (positions_df['POSITION_TYPE'] == position_type)
    cash_positions = positions_df[cash_mask]
    
    if cash_positions.empty:
        st.warning(f"No {position_type.replace('_', ' ').lower()} positions found in this basket.")
        if st.button("← Back to Basket Detail"):
            st.switch_page("pages/1_📊_Basket_Detail.py")
        return
    
    # Get position details
    cash_position = cash_positions.iloc[0]
    current_notional = cash_position.get('NOTIONAL_USD', 0) or 0
    current_market_value = cash_position.get('MARKET_VALUE_USD', 0) or 0
    rate = cash_position.get('FINANCING_RATE_%', 0) or 0
    rate_type = cash_position.get('FINANCING_RATE_TYPE', 'N/A')
    counterparty = cash_position.get('EXCHANGE_OR_COUNTERPARTY', 'N/A')
    
    # Determine labels based on position type
    if position_type == 'CASH_BORROW':
        position_label = "Cash Borrowing"
        icon = "🔻"
        # Cash borrow has negative notional (you owe money)
    else:
        position_label = "Cash Lending"
        icon = "🔺"
        # Cash lend has positive notional (you're owed money)
    
    # Initialize session state for this transaction
    txn_key = f"cash_txn_{basket_id}_{position_type}_{mode}"
    if st.session_state.get('cash_txn_key') != txn_key:
        st.session_state['cash_txn_key'] = txn_key
        if mode == 'unwind':
            # Pre-populate with full unwind (flip the sign)
            st.session_state['cash_txn_notional'] = -1 * current_notional
        else:
            st.session_state['cash_txn_notional'] = 0.0
    
    # Header with back button
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.pop('pending_cash_transaction', None)
            st.session_state.pop('cash_txn_key', None)
            st.session_state.pop('cash_txn_notional', None)
            st.switch_page("pages/1_📊_Basket_Detail.py")
    with col3:
        if st.button("🧾 Blotter", use_container_width=True):
            st.switch_page("pages/4_🧾_Transactions_Menu.py")
    
    # Page title
    mode_label = "Unwind" if mode == 'unwind' else "Resize"
    st.markdown(f"""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>💰</span>
            <span>{position_label} - {mode_label}</span>
        </h1>
    """, unsafe_allow_html=True)
    
    # Current Position Summary
    st.markdown("### Current Position")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Type</div>
                <div style="color: #fff; font-size: 1.3rem; font-weight: 600;">{icon} {position_label}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Current Notional</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">${current_notional:,.0f}</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Rate ({rate_type})</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{rate:.2f}%</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Counterparty</div>
                <div style="color: #fff; font-size: 1.3rem; font-weight: 600;">{counterparty}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Transaction Input
    st.markdown("### Transaction Details")
    
    if mode == 'unwind':
        st.info(f"**Unwind Mode:** This will fully close your {position_label.lower()} position.")
        transaction_notional = -1 * current_notional
        st.session_state['cash_txn_notional'] = transaction_notional
    else:
        if position_type == 'CASH_BORROW':
            st.markdown("Enter the notional amount to transact:")
            st.markdown("- **Positive** = Repay borrowed cash (reduce debt)")
            st.markdown("- **Negative** = Borrow more cash (increase debt)")
        else:
            st.markdown("Enter the notional amount to transact:")
            st.markdown("- **Positive** = Lend more cash")
            st.markdown("- **Negative** = Recall lent cash")
        
        transaction_notional = st.number_input(
            "Transaction Notional ($)",
            value=float(st.session_state.get('cash_txn_notional', 0)),
            step=1000000.0,
            format="%.0f",
            key="cash_notional_input",
            help="Enter the notional change amount."
        )
        st.session_state['cash_txn_notional'] = transaction_notional
    
    # Calculate new position
    new_notional = current_notional + transaction_notional
    
    # Determine action
    if position_type == 'CASH_BORROW':
        if transaction_notional > 0:
            action = 'REPAY'
            action_color = COLORS['accent_green']
        elif transaction_notional < 0:
            action = 'BORROW'
            action_color = COLORS['accent_red']
        else:
            action = 'NONE'
            action_color = '#808080'
    else:  # CASH_LEND
        if transaction_notional > 0:
            action = 'LEND'
            action_color = COLORS['accent_green']
        elif transaction_notional < 0:
            action = 'RECALL'
            action_color = COLORS['accent_red']
        else:
            action = 'NONE'
            action_color = '#808080'
    
    # Transaction Summary Card
    st.markdown(f"""
        <div style="background-color: #1a1a1a; border: 2px solid {action_color}; border-radius: 8px; 
                    padding: 2rem; margin: 1.5rem 0;">
            <div style="text-align: center; margin-bottom: 1.5rem;">
                <span style="color: {action_color}; font-size: 2.5rem; font-weight: 700;">
                    {action}
                </span>
            </div>
            <div style="text-align: center; margin-bottom: 1rem;">
                <span style="color: #ff8c00; font-size: 2rem; font-weight: 600;">
                    {position_label}
                </span>
            </div>
            <div style="text-align: center;">
                <span style="color: #fff; font-size: 3rem; font-weight: 700;">
                    ${abs(transaction_notional):,.0f}
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Post-Transaction State
    st.markdown("### Position After Transaction")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">New Notional</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">${new_notional:,.0f}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        status = "CLOSED" if new_notional == 0 else "OPEN"
        status_color = '#808080' if status == "CLOSED" else COLORS['accent_green']
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Status</div>
                <div style="color: {status_color}; font-size: 1.5rem; font-weight: 600;">{status}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Submit buttons
    st.markdown("### Submit Order")
    
    def _submit_cash_trade(route: str):
        """Submit cash trade to blotter."""
        st.session_state["trade_blotter"].append({
            "id": uuid.uuid4().hex,
            "ticker": "Cash",
            "side": action,
            "shares": 0,
            "price": 0,
            "estimated_value": float(abs(transaction_notional)),
            "notional": float(transaction_notional),
            "basket_id": basket_id,
            "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "execution_date": "CURRENT",
            "status": "SUBMITTED",
            "route": route,
            "instrument_type": position_type,
            "rate": rate,
            "counterparty": counterparty,
        })
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Generate for Bloomberg", use_container_width=True, type="primary"):
            if action != 'NONE':
                _submit_cash_trade(route="Bloomberg")
                st.success("✅ Bloomberg order generated!")
                st.balloons()
            else:
                st.warning("No transaction to submit.")
    
    with col2:
        if st.button("📋 Submit to Blotter", use_container_width=True):
            if action != 'NONE':
                _submit_cash_trade(route="Treasury")
                st.success("✅ Trade submitted to blotter!")
                st.balloons()
            else:
                st.warning("No transaction to submit.")
    
    with col3:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.pop('pending_cash_transaction', None)
            st.session_state.pop('cash_txn_key', None)
            st.session_state.pop('cash_txn_notional', None)
            st.switch_page("pages/1_📊_Basket_Detail.py")


# Main content
txn_data = st.session_state.get('pending_cash_transaction', None)

if txn_data:
    render_cash_transaction_page(txn_data)
else:
    st.markdown("""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>💰</span>
            <span>Cash Transaction</span>
        </h1>
    """, unsafe_allow_html=True)
    
    st.warning("No cash transaction selected. Please click Unwind or Resize from the Basket Detail page.")
    
    if st.button("← Back to Home"):
        st.switch_page("app.py")
