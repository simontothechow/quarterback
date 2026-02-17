"""
Quarterback - Futures Transaction Page
======================================
Transaction page for unwinding or resizing futures positions.
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
    calculate_unwind_trades_futures,
    calculate_resize_trades_futures,
    calculate_futures_contracts_from_notional,
    calculate_basket_component_totals,
    SPX_FUTURES_MULTIPLIER,
)

# Page configuration
st.set_page_config(
    page_title="Futures Transaction | Quarterback",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply theme
apply_theme()


def _ensure_trade_blotter():
    """Initialize the demo trade blotter in session state."""
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


def render_futures_transaction_page(txn_data: dict):
    """Render the futures transaction page."""
    
    _ensure_trade_blotter()
    
    basket_id = txn_data.get('basket_id', '')
    mode = txn_data.get('mode', 'resize')
    positions_df = txn_data.get('positions_df')
    
    if positions_df is None:
        positions_df = get_cached_data('positions')
    
    # Get current futures position info
    totals = calculate_basket_component_totals(positions_df, basket_id)
    
    # Get futures details
    futures_mask = (positions_df['BASKET_ID'] == basket_id) & \
                   (positions_df['POSITION_TYPE'] == 'FUTURE')
    futures_positions = positions_df[futures_mask]
    
    if futures_positions.empty:
        st.warning("No futures positions found in this basket.")
        if st.button("← Back to Basket Detail"):
            st.switch_page("pages/1_📊_Basket_Detail.py")
        return
    
    # Get primary futures position info
    primary_future = futures_positions.iloc[0]
    current_notional = totals['futures_notional']
    current_contracts = totals['futures_contracts']
    futures_price = primary_future.get('PRICE_OR_LEVEL', 0) or 0
    contract_month = primary_future.get('CONTRACT_MONTH', '')
    direction = primary_future.get('LONG_SHORT', '')
    
    # Initialize session state for this transaction
    txn_key = f"futures_txn_{basket_id}_{mode}"
    if st.session_state.get('futures_txn_key') != txn_key:
        st.session_state['futures_txn_key'] = txn_key
        if mode == 'unwind':
            # Pre-populate with full unwind
            st.session_state['futures_txn_notional'] = -1 * current_notional
        else:
            st.session_state['futures_txn_notional'] = 0.0
    
    # Header with back button
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.pop('pending_futures_transaction', None)
            st.session_state.pop('futures_txn_key', None)
            st.session_state.pop('futures_txn_notional', None)
            st.switch_page("pages/1_📊_Basket_Detail.py")
    with col3:
        if st.button("🧾 Blotter", use_container_width=True):
            st.switch_page("pages/4_🧾_Transactions_Menu.py")
    
    # Page title
    mode_label = "Unwind" if mode == 'unwind' else "Resize"
    st.markdown(f"""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>📊</span>
            <span>Futures Transaction - {mode_label}</span>
        </h1>
    """, unsafe_allow_html=True)
    
    # Current Position Summary
    st.markdown("### Current Position")
    
    direction_color = COLORS['accent_green'] if direction == 'LONG' else COLORS['accent_red']
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Direction</div>
                <div style="color: {direction_color}; font-size: 1.5rem; font-weight: 600;">{direction}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Contracts</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{current_contracts:,}</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Notional</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">${current_notional:,.0f}</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Contract Month</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{contract_month}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Transaction Input
    st.markdown("### Transaction Details")
    
    if mode == 'unwind':
        st.info("**Unwind Mode:** This will fully close your futures position.")
        transaction_notional = -1 * current_notional
        st.session_state['futures_txn_notional'] = transaction_notional
    else:
        st.markdown("Enter the notional amount to transact:")
        st.markdown("- **Positive** = Buy (go more long / reduce short)")
        st.markdown("- **Negative** = Sell (go more short / reduce long)")
        
        transaction_notional = st.number_input(
            "Transaction Notional ($)",
            value=float(st.session_state.get('futures_txn_notional', 0)),
            step=1000000.0,
            format="%.0f",
            key="futures_notional_input",
            help="Enter the notional change. Positive = buy, Negative = sell."
        )
        st.session_state['futures_txn_notional'] = transaction_notional
    
    # Calculate derived values
    if futures_price > 0:
        transaction_contracts = calculate_futures_contracts_from_notional(transaction_notional, futures_price)
    else:
        transaction_contracts = 0
    
    new_notional = current_notional + transaction_notional
    new_contracts = current_contracts + transaction_contracts
    
    # Determine action
    if transaction_notional > 0:
        action = 'BUY'
        action_color = COLORS['accent_green']
    elif transaction_notional < 0:
        action = 'SELL'
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
                    SPX Futures {contract_month}
                </span>
            </div>
            <div style="text-align: center;">
                <span style="color: #fff; font-size: 3rem; font-weight: 700;">
                    {int(round(abs(transaction_contracts))):,} contracts
                </span>
            </div>
            <div style="text-align: center; margin-top: 0.5rem;">
                <span style="color: #808080; font-size: 1.2rem;">
                    (${abs(transaction_notional):,.0f} notional)
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Post-Transaction State
    st.markdown("### Position After Transaction")
    
    new_direction = 'LONG' if new_notional > 0 else 'SHORT' if new_notional < 0 else 'FLAT'
    new_direction_color = COLORS['accent_green'] if new_direction == 'LONG' else COLORS['accent_red'] if new_direction == 'SHORT' else '#808080'
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">New Direction</div>
                <div style="color: {new_direction_color}; font-size: 1.5rem; font-weight: 600;">{new_direction}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">New Contracts</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{int(round(new_contracts)):,}</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">New Notional</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">${new_notional:,.0f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Order Routing
    st.markdown("### Order Routing")
    
    col1, col2 = st.columns(2)
    with col1:
        order_type = st.selectbox(
            "Order Type",
            ["Market", "Limit", "VWAP", "TWAP"],
            index=0,
            key="futures_order_type"
        )
    with col2:
        destination = st.selectbox(
            "Destination",
            ["CME GLOBEX", "CME FLOOR", "SMART"],
            index=0,
            key="futures_destination"
        )
    
    if order_type == "Limit":
        limit_price = st.number_input(
            "Limit Price",
            min_value=0.01,
            value=float(futures_price) if futures_price > 0 else 5300.0,
            step=0.25,
            format="%.2f",
            key="futures_limit_price"
        )
    
    st.markdown("---")
    
    # Submit buttons
    st.markdown("### Submit Order")
    
    def _submit_futures_trade(route: str):
        """Submit futures trade to blotter."""
        st.session_state["trade_blotter"].append({
            "id": uuid.uuid4().hex,
            "ticker": f"SPX {contract_month}",
            "side": action,
            "shares": int(round(abs(transaction_contracts))),
            "contracts": int(round(abs(transaction_contracts))),
            "price": float(futures_price),
            "estimated_value": float(abs(transaction_notional)),
            "basket_id": basket_id,
            "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "execution_date": "CURRENT",
            "status": "SUBMITTED",
            "route": route,
            "instrument_type": "FUTURE",
        })
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Generate for Bloomberg", use_container_width=True, type="primary"):
            if action != 'NONE':
                _submit_futures_trade(route="Bloomberg")
                st.success("✅ Bloomberg order generated!")
                st.balloons()
            else:
                st.warning("No transaction to submit.")
    
    with col2:
        if st.button("📋 Submit to Blotter", use_container_width=True):
            if action != 'NONE':
                _submit_futures_trade(route=f"{order_type} / {destination}")
                st.success("✅ Trade submitted to blotter!")
                st.balloons()
            else:
                st.warning("No transaction to submit.")
    
    with col3:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.pop('pending_futures_transaction', None)
            st.session_state.pop('futures_txn_key', None)
            st.session_state.pop('futures_txn_notional', None)
            st.switch_page("pages/1_📊_Basket_Detail.py")


# Main content
txn_data = st.session_state.get('pending_futures_transaction', None)

if txn_data:
    render_futures_transaction_page(txn_data)
else:
    st.markdown("""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>📊</span>
            <span>Futures Transaction</span>
        </h1>
    """, unsafe_allow_html=True)
    
    st.warning("No futures transaction selected. Please click Unwind or Resize from the Basket Detail page.")
    
    if st.button("← Back to Home"):
        st.switch_page("app.py")
