"""
Quarterback - Transaction Page
==============================
Transaction confirmation and order generation page.
Accessed when trader clicks on a rebalancing alert.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import uuid
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import get_cached_data
from components.theme import apply_theme, COLORS
from modules.calculations import calculate_trade_value

# Page configuration
st.set_page_config(
    page_title="Transaction | Quarterback",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply theme
apply_theme()

# Get transaction details from session state
transaction = st.session_state.get('pending_transaction', None)

def _ensure_trade_blotter():
    """Initialize the demo trade blotter in session state."""
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


def render_transaction_page(txn: dict):
    """Render the transaction confirmation page."""

    _ensure_trade_blotter()

    # Initialize editable fields when a new transaction is opened
    txn_context_key = "|".join([
        str(txn.get("basket_id", "")),
        str(txn.get("ticker", "")),
        str(txn.get("action", "")),
        str(txn.get("event_date", "")),
        str(txn.get("position_id", "")),
        str(txn.get("source", "")),
    ])
    if st.session_state.get("txn_context_key") != txn_context_key:
        st.session_state["txn_context_key"] = txn_context_key
        try:
            st.session_state["txn_shares"] = int(round(float(txn.get("shares", 0) or 0)))
        except (TypeError, ValueError):
            st.session_state["txn_shares"] = 0
        # Scheduling state
        st.session_state["show_schedule_picker"] = False
        st.session_state["txn_execution_date"] = txn.get("execution_date", None)
    
    # Header with back button
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state['pending_transaction'] = None
            st.session_state.pop("txn_context_key", None)
            st.session_state.pop("txn_shares", None)
            st.session_state.pop("txn_execution_date", None)
            st.session_state.pop("show_schedule_picker", None)
            st.switch_page("pages/1_📊_Basket_Detail.py")
    with col3:
        if st.button("🧾 Blotter", use_container_width=True):
            st.switch_page("pages/4_🧾_Transactions_Menu.py")
    
    st.markdown(f"""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>💱</span>
            <span>Transaction Confirmation</span>
        </h1>
    """, unsafe_allow_html=True)
    
    # Determine colors based on action
    action = txn.get('action', 'BUY')
    if action in ['BUY', 'SHORT']:
        action_color = COLORS['accent_green']
    else:
        action_color = COLORS['accent_red']
    
    # Transaction summary card
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
                    {txn.get('ticker', 'N/A')}
                </span>
            </div>
            <div style="text-align: center;">
                <span style="color: #fff; font-size: 3rem; font-weight: 700;">
                    {int(st.session_state.get('txn_shares', 0) or 0):,} shares
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Pull current editable values and recompute derived fields
    try:
        price = float(txn.get("price", 0) or 0)
    except (TypeError, ValueError):
        price = 0.0
    shares = int(st.session_state.get("txn_shares", 0) or 0)
    value = calculate_trade_value(shares, price)

    # Keep pending_transaction in sync so downstream UI uses edited values
    txn["shares"] = shares
    txn["value"] = value
    txn["execution_date"] = st.session_state.get("txn_execution_date", None)
    st.session_state["pending_transaction"] = txn
    
    # Transaction details
    st.markdown("### Order Details")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Symbol</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{txn.get('ticker', 'N/A')}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Quantity</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{shares:,}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Price</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">${price:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Estimated Value</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">${value:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Current Position</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{txn.get('current_shares', 0):,}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Keep display clean (avoid long float strings)
        try:
            target_pos_display = int(round(float(txn.get("target_shares", 0) or 0)))
        except (TypeError, ValueError):
            target_pos_display = 0
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Target Position</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{target_pos_display:,}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Order routing options
    st.markdown("### Order Routing")

    st.number_input(
        "Quantity (shares)",
        min_value=0,
        step=1,
        value=shares,
        key="txn_shares",
        help="Edit shares and press Enter to update Estimated Value.",
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        order_type = st.selectbox(
            "Order Type",
            ["Market", "Limit", "VWAP", "TWAP"],
            index=0
        )
    
    with col2:
        destination = st.selectbox(
            "Destination",
            ["SMART", "NYSE", "NASDAQ", "ARCA", "BATS"],
            index=0
        )
    
    if order_type == "Limit":
        limit_price = st.number_input(
            "Limit Price",
            min_value=0.01,
            value=price if price > 0 else 100.0,
            step=0.01,
            format="%.2f"
        )
    
    st.markdown("---")

    # Execution & Scheduling (demo)
    st.markdown("### Execution & Scheduling")

    execution_date = st.session_state.get("txn_execution_date", None)
    execution_label = execution_date if execution_date else "CURRENT"
    st.markdown(f"**Trade Execution Date:** `{execution_label}`")

    sched_col1, sched_col2, sched_col3 = st.columns([2, 2, 4])
    with sched_col1:
        if st.button("Schedule Fwd Start", use_container_width=True):
            st.session_state["show_schedule_picker"] = True
    with sched_col2:
        if st.button("Clear Schedule", use_container_width=True):
            st.session_state["txn_execution_date"] = None
            st.session_state["show_schedule_picker"] = False

    if st.session_state.get("show_schedule_picker", False):
        picked = st.date_input(
            "Select execution date",
            value=datetime.now().date(),
            key="txn_execution_date_picker",
            help="Demo mode: any date allowed.",
        )
        # Store as ISO string for easy display/serialization
        if isinstance(picked, date):
            st.session_state["txn_execution_date"] = picked.strftime("%Y-%m-%d")

    def _append_trade_to_blotter(route: str):
        """Append current transaction to blotter (demo persistence)."""
        execution_date_local = st.session_state.get("txn_execution_date", None)
        status = "SCHEDULED" if execution_date_local else "SUBMITTED"
        st.session_state["trade_blotter"].append({
            "id": uuid.uuid4().hex,
            "ticker": txn.get("ticker", "N/A"),
            "side": action,
            "shares": int(shares),
            "price": float(price),
            "estimated_value": float(value),
            "basket_id": txn.get("basket_id", ""),
            "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "execution_date": execution_date_local if execution_date_local else "CURRENT",
            "status": status,
            "route": route,
        })

    # Submit button (records trade in blotter)
    if st.button("Submit Trade", use_container_width=True, type="primary"):
        _append_trade_to_blotter(route=f"{order_type} / {destination}")
        st.success("✅ Trade submitted to blotter.")
    
    # Action buttons
    st.markdown("### Generate Trade Order")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Generate for Bloomberg", use_container_width=True, type="primary"):
            _append_trade_to_blotter(route="Bloomberg")
            st.success("✅ Bloomberg order file generated!")
            st.info("📁 File saved to: /orders/bloomberg_order_" + 
                   datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")
            st.balloons()
    
    with col2:
        if st.button("📋 Generate for Booking System", use_container_width=True):
            _append_trade_to_blotter(route="Booking System")
            st.success("✅ Booking system order generated!")
            st.info("📁 File saved to: /orders/booking_order_" + 
                   datetime.now().strftime("%Y%m%d_%H%M%S") + ".xml")
    
    with col3:
        if st.button("⚙️ Generate Custom Order", use_container_width=True):
            st.info("🚧 Custom order generation coming in Phase 2")
    
    with col4:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state['pending_transaction'] = None
            st.session_state.pop("txn_context_key", None)
            st.session_state.pop("txn_shares", None)
            st.session_state.pop("txn_execution_date", None)
            st.session_state.pop("show_schedule_picker", None)
            st.switch_page("pages/1_📊_Basket_Detail.py")
    
    # Order preview
    st.markdown("---")
    st.markdown("### Order Preview")
    
    order_data = {
        'Field': ['Symbol', 'Side', 'Quantity', 'Order Type', 'Price', 'Destination', 
                  'Account', 'Basket ID', 'Timestamp'],
        'Value': [
            txn.get('ticker', 'N/A'),
            action,
            f"{shares:,}",
            order_type,
            f"${txn.get('price', 0):,.2f}" if order_type == "Market" else f"${limit_price:,.2f}" if order_type == "Limit" else "N/A",
            destination,
            txn.get('basket_id', 'N/A'),
            txn.get('basket_id', 'N/A'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
    }
    
    st.dataframe(
        pd.DataFrame(order_data),
        use_container_width=True,
        hide_index=True
    )


# Main content
if transaction:
    render_transaction_page(transaction)
else:
    st.markdown("""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>💱</span>
            <span>Transaction</span>
        </h1>
    """, unsafe_allow_html=True)
    
    st.warning("No transaction selected. Please click on a rebalancing alert from the Basket Detail page.")
    
    if st.button("← Back to Home"):
        st.switch_page("app.py")
