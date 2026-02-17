"""
Quarterback - Equity / Stock Borrow Transaction Page
=====================================================
Transaction page for unwinding or resizing equity or stock borrow positions.
Features:
- Sizing section with notional input and equivalent futures contracts reference
- Current total market value display
- Editable trades table per stock
- Excel export functionality
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import sys
from pathlib import Path
import io

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import get_cached_data
from components.theme import apply_theme, COLORS
from modules.calculations import (
    calculate_unwind_trades_equities,
    calculate_equity_trades_for_notional,
    calculate_unwind_trades_stock_borrow,
    calculate_resize_trades_stock_borrow,
    calculate_basket_component_totals,
    calculate_equivalent_futures_contracts,
    SPX_FUTURES_MULTIPLIER,
)

# Page configuration
st.set_page_config(
    page_title="Equity Transaction | Quarterback",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply theme
apply_theme()


def _ensure_trade_blotter():
    """Initialize the demo trade blotter in session state."""
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


def render_equity_transaction_page(txn_data: dict):
    """Render the equity/stock borrow transaction page."""
    
    _ensure_trade_blotter()
    
    basket_id = txn_data.get('basket_id', '')
    mode = txn_data.get('mode', 'resize')
    position_type = txn_data.get('position_type', 'EQUITY')  # EQUITY or STOCK_BORROW
    positions_df = txn_data.get('positions_df')
    
    if positions_df is None:
        positions_df = get_cached_data('positions')
    
    market_data_df = get_cached_data('market_data')
    
    # Get current position totals
    totals = calculate_basket_component_totals(positions_df, basket_id)
    
    if position_type == 'EQUITY':
        current_market_value = totals['equity_market_value']
        position_count = totals['equity_position_count']
        position_label = "Physical Equities"
        icon = "📈"
    else:  # STOCK_BORROW
        current_market_value = totals['stock_borrow_notional']
        # Count stock borrow positions
        sb_mask = (positions_df['BASKET_ID'] == basket_id) & \
                  (positions_df['POSITION_TYPE'] == 'STOCK_BORROW')
        position_count = len(positions_df[sb_mask])
        position_label = "Stock Borrowing"
        icon = "📊"
    
    # Initialize session state for this transaction
    txn_key = f"equity_txn_{basket_id}_{position_type}_{mode}"
    if st.session_state.get('equity_txn_key') != txn_key:
        st.session_state['equity_txn_key'] = txn_key
        if mode == 'unwind':
            # For unwind, the notional to transact is opposite of current
            # If long equities (+100mm), unwind with -100mm (sell all)
            # If stock borrow (+100mm), unwind with -100mm (return all)
            st.session_state['equity_txn_notional'] = -1 * current_market_value
        else:
            st.session_state['equity_txn_notional'] = 0.0
        st.session_state['equity_trades_df'] = None
    
    # Header with back button
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.pop('pending_equity_transaction', None)
            st.session_state.pop('equity_txn_key', None)
            st.session_state.pop('equity_txn_notional', None)
            st.session_state.pop('equity_trades_df', None)
            st.switch_page("pages/1_📊_Basket_Detail.py")
    with col3:
        if st.button("🧾 Blotter", use_container_width=True):
            st.switch_page("pages/4_🧾_Transactions_Menu.py")
    
    # Page title
    mode_label = "Unwind" if mode == 'unwind' else "Resize"
    st.markdown(f"""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>{icon}</span>
            <span>{position_label} Transaction - {mode_label}</span>
        </h1>
    """, unsafe_allow_html=True)
    
    # ==========================================================================
    # SIZING SECTION
    # ==========================================================================
    st.markdown("### Sizing")
    
    # Current position summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Current Total Market Value</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">${current_market_value:,.0f}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Position Count</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{position_count:,}</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Position Type</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{position_label}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("")
    
    # Transaction notional input
    if mode == 'unwind':
        st.info(f"**Unwind Mode:** This will fully close all {position_label.lower()} positions.")
        transaction_notional = -1 * current_market_value
        st.session_state['equity_txn_notional'] = transaction_notional
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
                <div style="background-color: #1e1e1e; border: 2px solid #ff8c00; border-radius: 6px; padding: 1rem;">
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Transaction Notional</div>
                    <div style="color: #ff8c00; font-size: 1.5rem; font-weight: 600;">${transaction_notional:,.0f}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("Enter the notional amount to transact:")
        if position_type == 'EQUITY':
            st.markdown("- **Positive** = Buy shares (go more long / reduce short)")
            st.markdown("- **Negative** = Sell shares (go more short / reduce long)")
        else:
            st.markdown("- **Positive** = Borrow more shares")
            st.markdown("- **Negative** = Return borrowed shares")
        
        col1, col2 = st.columns(2)
        with col1:
            transaction_notional = st.number_input(
                "Transaction Notional ($)",
                value=float(st.session_state.get('equity_txn_notional', 0)),
                step=1000000.0,
                format="%.0f",
                key="equity_notional_input",
                help="Enter the total notional change. This will be allocated across all positions by index weight."
            )
            st.session_state['equity_txn_notional'] = transaction_notional
    
    # Equivalent futures contracts reference
    with col2:
        equiv_contracts = calculate_equivalent_futures_contracts(
            abs(transaction_notional), positions_df, basket_id
        )
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Equivalent Futures Contracts</div>
                <div style="color: #808080; font-size: 1.3rem; font-weight: 600;">{int(round(equiv_contracts)):,} contracts</div>
                <div style="color: #606060; font-size: 0.75rem;">(Reference only - SPX × {SPX_FUTURES_MULTIPLIER} multiplier)</div>
            </div>
        """, unsafe_allow_html=True)
    
    # New position after transaction
    new_market_value = current_market_value + transaction_notional
    
    st.markdown("")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Market Value After Transaction</div>
                <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">${new_market_value:,.0f}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        status = "CLOSED" if abs(new_market_value) < 1000 else "OPEN"
        status_color = '#808080' if status == "CLOSED" else COLORS['accent_green']
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem;">
                <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Position Status After</div>
                <div style="color: {status_color}; font-size: 1.5rem; font-weight: 600;">{status}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==========================================================================
    # EQUITY TRADES SECTION
    # ==========================================================================
    st.markdown("### Equity Trades")
    
    # Calculate trades based on notional
    if transaction_notional != 0:
        if mode == 'unwind' and position_type == 'EQUITY':
            trades_df = calculate_unwind_trades_equities(positions_df, market_data_df, basket_id)
        elif position_type == 'EQUITY':
            trades_df = calculate_equity_trades_for_notional(
                positions_df, market_data_df, basket_id, transaction_notional
            )
        else:
            # For stock borrow, create a similar DataFrame structure
            # (In practice, stock borrow would follow similar logic)
            trades_df = calculate_equity_trades_for_notional(
                positions_df, market_data_df, basket_id, transaction_notional
            )
        
        if trades_df.empty:
            st.warning("No equity positions found to trade.")
        else:
            # Prepare display DataFrame
            display_df = trades_df[[
                'TICKER', 'COMPANY', 'CURRENT_SHARES', 'CURRENT_MARKET_VALUE',
                'TRANSACTION_VALUE', 'SHARES_TRANSACTED', 'SHARES_AFTER', 'MARKET_VALUE_AFTER'
            ]].copy()
            
            # Round numeric columns for clean display
            display_df['CURRENT_SHARES'] = display_df['CURRENT_SHARES'].round(0).astype(int)
            display_df['CURRENT_MARKET_VALUE'] = display_df['CURRENT_MARKET_VALUE'].round(2)
            display_df['TRANSACTION_VALUE'] = display_df['TRANSACTION_VALUE'].round(2)
            display_df['SHARES_TRANSACTED'] = display_df['SHARES_TRANSACTED'].round(0).astype(int)
            display_df['SHARES_AFTER'] = display_df['SHARES_AFTER'].round(0).astype(int)
            display_df['MARKET_VALUE_AFTER'] = display_df['MARKET_VALUE_AFTER'].round(2)
            
            # Make it editable
            st.markdown("**Edit Transaction Value or Shares as needed.** Press Enter to confirm edits.")
            
            edited_df = st.data_editor(
                display_df,
                column_config={
                    "TICKER": st.column_config.TextColumn("Ticker", disabled=True),
                    "COMPANY": st.column_config.TextColumn("Company", disabled=True, width="large"),
                    "CURRENT_SHARES": st.column_config.NumberColumn("Current Shares", format="%d", disabled=True),
                    "CURRENT_MARKET_VALUE": st.column_config.NumberColumn("Current MV ($)", format="$%,.2f", disabled=True),
                    "TRANSACTION_VALUE": st.column_config.NumberColumn("Transaction Value ($)", format="$%,.2f"),
                    "SHARES_TRANSACTED": st.column_config.NumberColumn("Shares Bought(Sold)", format="%d"),
                    "SHARES_AFTER": st.column_config.NumberColumn("Shares After", format="%d", disabled=True),
                    "MARKET_VALUE_AFTER": st.column_config.NumberColumn("MV After ($)", format="$%,.2f", disabled=True),
                },
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key="equity_trades_editor"
            )
            
            # Store edited trades
            st.session_state['equity_trades_df'] = edited_df
            
            # Summary stats
            total_transaction_value = edited_df['TRANSACTION_VALUE'].sum()
            buy_count = len(edited_df[edited_df['SHARES_TRANSACTED'] > 0])
            sell_count = len(edited_df[edited_df['SHARES_TRANSACTED'] < 0])
            
            st.markdown("")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Transaction Value", f"${total_transaction_value:,.0f}")
            with col2:
                st.metric("Buy Orders", f"{buy_count:,}")
            with col3:
                st.metric("Sell Orders", f"{sell_count:,}")
            
            # Export to Excel button
            st.markdown("---")
            
            # Create Excel file in memory
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                edited_df.to_excel(writer, index=False, sheet_name='Equity Trades')
            excel_data = excel_buffer.getvalue()
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.download_button(
                    label="📥 Export to Excel",
                    data=excel_data,
                    file_name=f"equity_trades_{basket_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    else:
        st.info("Enter a transaction notional above to see the calculated trades.")
    
    st.markdown("---")
    
    # ==========================================================================
    # SUBMIT SECTION
    # ==========================================================================
    st.markdown("### Submit Orders")
    
    def _submit_equity_trades(route: str):
        """Submit all equity trades to blotter."""
        if st.session_state.get('equity_trades_df') is None:
            return False
        
        df = st.session_state['equity_trades_df']
        trades_added = 0
        
        for _, row in df.iterrows():
            shares_transacted = row.get('SHARES_TRANSACTED', 0)
            if abs(shares_transacted) < 1:
                continue  # Skip negligible trades
            
            action = 'BUY' if shares_transacted > 0 else 'SELL'
            
            st.session_state["trade_blotter"].append({
                "id": uuid.uuid4().hex,
                "ticker": row.get('TICKER', ''),
                "side": action,
                "shares": int(round(abs(shares_transacted))),
                "price": row.get('CURRENT_MARKET_VALUE', 0) / row.get('CURRENT_SHARES', 1) if row.get('CURRENT_SHARES', 0) != 0 else 0,
                "estimated_value": float(abs(row.get('TRANSACTION_VALUE', 0))),
                "basket_id": basket_id,
                "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "execution_date": "CURRENT",
                "status": "SUBMITTED",
                "route": route,
                "instrument_type": position_type,
            })
            trades_added += 1
        
        return trades_added > 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎯 Confirm and Generate Trade Orders", use_container_width=True, type="primary"):
            if transaction_notional != 0 and st.session_state.get('equity_trades_df') is not None:
                if _submit_equity_trades(route="Bloomberg"):
                    st.success("✅ Trade orders generated and submitted to blotter!")
                    st.balloons()
                else:
                    st.warning("No trades to submit.")
            else:
                st.warning("Please calculate trades first by entering a notional amount.")
    
    with col2:
        if st.button("📋 Submit to Blotter Only", use_container_width=True):
            if transaction_notional != 0 and st.session_state.get('equity_trades_df') is not None:
                if _submit_equity_trades(route="Manual"):
                    st.success("✅ Trades submitted to blotter!")
                    st.balloons()
                else:
                    st.warning("No trades to submit.")
            else:
                st.warning("Please calculate trades first.")
    
    with col3:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.pop('pending_equity_transaction', None)
            st.session_state.pop('equity_txn_key', None)
            st.session_state.pop('equity_txn_notional', None)
            st.session_state.pop('equity_trades_df', None)
            st.switch_page("pages/1_📊_Basket_Detail.py")


# Main content
txn_data = st.session_state.get('pending_equity_transaction', None)

if txn_data:
    render_equity_transaction_page(txn_data)
else:
    st.markdown("""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>📈</span>
            <span>Equity Transaction</span>
        </h1>
    """, unsafe_allow_html=True)
    
    st.warning("No equity transaction selected. Please click Unwind or Resize from the Basket Detail page.")
    
    if st.button("← Back to Home"):
        st.switch_page("app.py")
