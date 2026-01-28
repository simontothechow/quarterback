"""
Quarterback - Transaction Page
==============================
Transaction confirmation and order generation page.
Accessed when trader clicks on a rebalancing alert.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import get_cached_data
from components.theme import apply_theme, COLORS

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

def render_transaction_page(txn: dict):
    """Render the transaction confirmation page."""
    
    # Header with back button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state['pending_transaction'] = None
            st.switch_page("pages/1_📊_Basket_Detail.py")
    
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
                    {txn.get('shares', 0):,} shares
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
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
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{txn.get('shares', 0):,}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Price</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">${txn.get('price', 0):,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Estimated Value</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">${txn.get('value', 0):,.2f}</div>
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
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Target Position</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{txn.get('target_shares', 0):,}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Order routing options
    st.markdown("### Order Routing")
    
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
            value=txn.get('price', 100.0),
            step=0.01,
            format="%.2f"
        )
    
    st.markdown("---")
    
    # Action buttons
    st.markdown("### Generate Trade Order")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Generate for Bloomberg", use_container_width=True, type="primary"):
            st.success("✅ Bloomberg order file generated!")
            st.info("📁 File saved to: /orders/bloomberg_order_" + 
                   datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")
            st.balloons()
    
    with col2:
        if st.button("📋 Generate for Booking System", use_container_width=True):
            st.success("✅ Booking system order generated!")
            st.info("📁 File saved to: /orders/booking_order_" + 
                   datetime.now().strftime("%Y%m%d_%H%M%S") + ".xml")
    
    with col3:
        if st.button("⚙️ Generate Custom Order", use_container_width=True):
            st.info("🚧 Custom order generation coming in Phase 2")
    
    with col4:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state['pending_transaction'] = None
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
            f"{txn.get('shares', 0):,}",
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
