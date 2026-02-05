"""
Quarterback - Total Basket Transaction Page
============================================
Transaction page for unwinding or resizing an entire basket.
Features:
- Tabbed interface showing each component type present in the basket
- Linked notional sizing across tabs (for resize mode)
- Pre-populated unwind trades when Unwind All is clicked
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
    calculate_basket_component_totals,
    calculate_basket_unwind_all,
    calculate_basket_resize_all,
    calculate_unwind_trades_futures,
    calculate_resize_trades_futures,
    calculate_unwind_trades_cash,
    calculate_resize_trades_cash,
    calculate_unwind_trades_stock_borrow,
    calculate_resize_trades_stock_borrow,
    calculate_unwind_trades_equities,
    calculate_equity_trades_for_notional,
    calculate_equivalent_futures_contracts,
    calculate_futures_contracts_from_notional,
    SPX_FUTURES_MULTIPLIER,
)

# Page configuration
st.set_page_config(
    page_title="Basket Transaction | Quarterback",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply theme
apply_theme()


def _ensure_trade_blotter():
    """Initialize the demo trade blotter in session state."""
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


def render_basket_transaction_page(txn_data: dict):
    """Render the total basket transaction page with tabs."""
    
    _ensure_trade_blotter()
    
    basket_id = txn_data.get('basket_id', '')
    mode = txn_data.get('mode', 'resize')
    positions_df = txn_data.get('positions_df')
    
    if positions_df is None:
        positions_df = get_cached_data('positions')
    
    market_data_df = get_cached_data('market_data')
    
    # Get basket component totals
    totals = calculate_basket_component_totals(positions_df, basket_id)
    
    # Initialize session state for this transaction
    txn_key = f"basket_txn_{basket_id}_{mode}"
    if st.session_state.get('basket_txn_key') != txn_key:
        st.session_state['basket_txn_key'] = txn_key
        st.session_state['basket_txn_notional'] = 0.0
        st.session_state['basket_trades_calculated'] = False
    
    # Header with back button
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            _clear_basket_session_state()
            st.switch_page("pages/1_📊_Basket_Detail.py")
    with col3:
        if st.button("🧾 Blotter", use_container_width=True):
            st.switch_page("pages/4_🧾_Transactions_Menu.py")
    
    # Page title
    mode_label = "Unwind All" if mode == 'unwind' else "Resize All"
    st.markdown(f"""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>🎯</span>
            <span>Total Basket Transaction - {mode_label}</span>
        </h1>
    """, unsafe_allow_html=True)
    
    # Basket summary header
    strategy_type = "Unknown"
    basket_positions = positions_df[positions_df['BASKET_ID'] == basket_id]
    if not basket_positions.empty and 'STRATEGY_TYPE' in basket_positions.columns:
        strategy_type = basket_positions['STRATEGY_TYPE'].iloc[0]
    
    total_basket_notional = abs(totals['futures_notional']) + abs(totals['cash_borrow_notional']) + \
                            abs(totals['cash_lend_notional']) + abs(totals['equity_market_value'])
    
    st.markdown(f"""
        <div style="background-color: #1a1a1a; border: 2px solid #ff8c00; border-radius: 6px; 
                    padding: 1.25rem; margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #ff8c00; font-size: 1.5rem; font-weight: 700;">{basket_id}</span>
                    <span style="color: #808080; margin-left: 1rem; font-size: 1rem;">{strategy_type}</span>
                </div>
                <div style="text-align: right;">
                    <span style="color: #808080;">Total Basket Size: </span>
                    <span style="color: #fff; font-size: 1.25rem; font-weight: 600;">${total_basket_notional:,.0f}</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # ==========================================================================
    # MODE-SPECIFIC HEADER
    # ==========================================================================
    if mode == 'unwind':
        st.info("**Unwind All Mode:** All positions will be fully reversed to close the basket.")
        transaction_notional = None  # Each component uses its own unwind logic
    else:
        st.markdown("### Transaction Sizing")
        st.markdown("Enter the notional amount to resize the entire basket. This notional will be applied to all components proportionally.")
        st.markdown("- **Positive** = Increase position sizes (buy more long / increase short)")
        st.markdown("- **Negative** = Decrease position sizes (reduce long / cover short)")
        
        col1, col2 = st.columns(2)
        with col1:
            transaction_notional = st.number_input(
                "Transaction Notional ($)",
                value=float(st.session_state.get('basket_txn_notional', 0)),
                step=1000000.0,
                format="%.0f",
                key="basket_notional_input",
                help="This notional change will be applied to all basket components."
            )
            st.session_state['basket_txn_notional'] = transaction_notional
        
        with col2:
            equiv_contracts = calculate_equivalent_futures_contracts(
                abs(transaction_notional), positions_df, basket_id
            )
            st.markdown(f"""
                <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem; margin-top: 1.5rem;">
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Equivalent Futures Contracts</div>
                    <div style="color: #808080; font-size: 1.3rem; font-weight: 600;">{int(round(equiv_contracts)):,} contracts</div>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==========================================================================
    # TABBED INTERFACE
    # ==========================================================================
    
    # Custom CSS to make tab headers larger
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 60px;
            padding: 12px 24px;
            font-size: 1.1rem;
            font-weight: 600;
        }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 1.1rem;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Determine which tabs to show based on what's in the basket
    tab_list = []
    tab_labels = []
    
    if totals['has_futures']:
        tab_list.append('futures')
        tab_labels.append("📊 Futures")
    
    if totals['has_cash_borrow'] or totals['has_cash_lend']:
        tab_list.append('cash')
        tab_labels.append("💰 Cash Borrow/Lend")
    
    if totals['has_stock_borrow']:
        tab_list.append('stock_borrow')
        tab_labels.append("📊 Stock Borrow")
    
    if totals['has_equities']:
        tab_list.append('equities')
        tab_labels.append("📈 Physical Equities")
    
    if not tab_list:
        st.warning("No positions found in this basket.")
        return
    
    tabs = st.tabs(tab_labels)
    
    # Track all trades across tabs
    all_trades = {
        'futures': [],
        'cash': [],
        'stock_borrow': [],
        'equities': pd.DataFrame()
    }
    
    # ==========================================================================
    # FUTURES TAB
    # ==========================================================================
    if 'futures' in tab_list:
        tab_idx = tab_list.index('futures')
        with tabs[tab_idx]:
            st.markdown("### Futures Position")
            
            # Current position info
            futures_mask = (positions_df['BASKET_ID'] == basket_id) & \
                           (positions_df['POSITION_TYPE'] == 'FUTURE')
            futures_positions = positions_df[futures_mask]
            
            if not futures_positions.empty:
                primary_future = futures_positions.iloc[0]
                current_notional = totals['futures_notional']
                current_contracts = totals['futures_contracts']
                futures_price = primary_future.get('PRICE_OR_LEVEL', 0) or 0
                contract_month = primary_future.get('CONTRACT_MONTH', '')
                direction = primary_future.get('LONG_SHORT', '')
                
                direction_color = COLORS['accent_green'] if direction == 'LONG' else COLORS['accent_red']
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Direction", direction)
                with col2:
                    st.metric("Current Contracts", f"{current_contracts:,}")
                with col3:
                    st.metric("Current Notional", f"${current_notional:,.0f}")
                with col4:
                    st.metric("Contract Month", contract_month)
                
                # Calculate trades
                if mode == 'unwind':
                    futures_trades = calculate_unwind_trades_futures(positions_df, basket_id)
                else:
                    futures_trades = calculate_resize_trades_futures(positions_df, basket_id, transaction_notional)
                
                all_trades['futures'] = futures_trades
                
                if futures_trades:
                    trade = futures_trades[0]
                    txn_notional = trade.get('notional', 0)
                    txn_contracts = trade.get('contracts_signed', 0)
                    action = trade.get('action', 'NONE')
                    new_notional = trade.get('new_notional', current_notional + txn_notional) if mode == 'resize' else 0
                    new_contracts = trade.get('new_contracts', current_contracts + txn_contracts) if mode == 'resize' else 0
                    
                    action_color = COLORS['accent_green'] if action == 'BUY' else COLORS['accent_red'] if action == 'SELL' else '#808080'
                    
                    st.markdown("#### Transaction")
                    st.markdown(f"""
                        <div style="background-color: #1a1a1a; border: 2px solid {action_color}; border-radius: 8px; 
                                    padding: 1.5rem; margin: 1rem 0; text-align: center;">
                            <span style="color: {action_color}; font-size: 1.5rem; font-weight: 700;">{action}</span>
                            <span style="color: #fff; font-size: 1.5rem; margin-left: 1rem;">
                                {int(round(abs(txn_contracts))):,} contracts
                            </span>
                            <span style="color: #808080; margin-left: 1rem;">
                                (${abs(txn_notional):,.0f})
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("New Contracts", f"{int(round(new_contracts)):,}")
                    with col2:
                        st.metric("New Notional", f"${new_notional:,.0f}")
    
    # ==========================================================================
    # CASH BORROW/LEND TAB
    # ==========================================================================
    if 'cash' in tab_list:
        tab_idx = tab_list.index('cash')
        with tabs[tab_idx]:
            st.markdown("### Cash Borrow/Lend Positions")
            
            if mode == 'unwind':
                cash_trades = calculate_unwind_trades_cash(positions_df, basket_id)
            else:
                cash_trades = calculate_resize_trades_cash(positions_df, basket_id, transaction_notional)
            
            all_trades['cash'] = cash_trades
            
            for trade in cash_trades:
                pos_type = trade.get('position_type', '')
                current_notional = trade.get('current_notional', 0)
                txn_notional = trade.get('notional', 0)
                new_notional = trade.get('new_notional', 0)
                action = trade.get('action', 'NONE')
                rate = trade.get('rate', 0)
                counterparty = trade.get('counterparty', 'N/A')
                
                label = "Cash Borrowing" if pos_type == 'CASH_BORROW' else "Cash Lending"
                icon = "🔻" if pos_type == 'CASH_BORROW' else "🔺"
                action_color = COLORS['accent_green'] if action in ['REPAY', 'LEND'] else COLORS['accent_red']
                
                st.markdown(f"#### {icon} {label}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Notional", f"${current_notional:,.0f}")
                with col2:
                    st.metric("Rate", f"{rate:.2f}%")
                with col3:
                    st.metric("Counterparty", counterparty)
                
                st.markdown(f"""
                    <div style="background-color: #1a1a1a; border: 2px solid {action_color}; border-radius: 8px; 
                                padding: 1.5rem; margin: 1rem 0; text-align: center;">
                        <span style="color: {action_color}; font-size: 1.5rem; font-weight: 700;">{action}</span>
                        <span style="color: #fff; font-size: 1.5rem; margin-left: 1rem;">
                            ${abs(txn_notional):,.0f}
                        </span>
                    </div>
                """, unsafe_allow_html=True)
                
                st.metric("New Notional", f"${new_notional:,.0f}")
                st.markdown("---")
    
    # ==========================================================================
    # STOCK BORROW TAB
    # ==========================================================================
    if 'stock_borrow' in tab_list:
        tab_idx = tab_list.index('stock_borrow')
        with tabs[tab_idx]:
            st.markdown("### Stock Borrow Positions")
            
            current_sb_notional = totals['stock_borrow_notional']
            
            if mode == 'unwind':
                sb_trades = calculate_unwind_trades_stock_borrow(positions_df, basket_id)
            else:
                sb_trades = calculate_resize_trades_stock_borrow(positions_df, basket_id, transaction_notional)
            
            all_trades['stock_borrow'] = sb_trades
            
            for trade in sb_trades:
                txn_notional = trade.get('notional', 0)
                new_notional = trade.get('new_notional', 0)
                action = trade.get('action', 'NONE')
                rate = trade.get('rate', 0)
                counterparty = trade.get('counterparty', 'N/A')
                position_count = trade.get('position_count', 0)
                
                action_color = COLORS['accent_green'] if action == 'RETURN' else COLORS['accent_red']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Market Value", f"${current_sb_notional:,.0f}")
                with col2:
                    st.metric("Positions", f"{position_count:,}")
                with col3:
                    st.metric("Borrow Rate", f"{rate:.2f}%")
                
                st.markdown(f"""
                    <div style="background-color: #1a1a1a; border: 2px solid {action_color}; border-radius: 8px; 
                                padding: 1.5rem; margin: 1rem 0; text-align: center;">
                        <span style="color: {action_color}; font-size: 1.5rem; font-weight: 700;">{action}</span>
                        <span style="color: #fff; font-size: 1.5rem; margin-left: 1rem;">
                            ${abs(txn_notional):,.0f}
                        </span>
                    </div>
                """, unsafe_allow_html=True)
                
                st.metric("New Market Value", f"${new_notional:,.0f}")
    
    # ==========================================================================
    # PHYSICAL EQUITIES TAB
    # ==========================================================================
    if 'equities' in tab_list:
        tab_idx = tab_list.index('equities')
        with tabs[tab_idx]:
            st.markdown("### Physical Equity Positions")
            
            current_eq_mv = totals['equity_market_value']
            position_count = totals['equity_position_count']
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Current Total Market Value", f"${current_eq_mv:,.0f}")
            with col2:
                st.metric("Position Count", f"{position_count:,}")
            
            # Calculate trades
            if mode == 'unwind':
                equity_trades_df = calculate_unwind_trades_equities(positions_df, market_data_df, basket_id)
                txn_notional_eq = -1 * current_eq_mv
            else:
                equity_trades_df = calculate_equity_trades_for_notional(
                    positions_df, market_data_df, basket_id, transaction_notional
                )
                txn_notional_eq = transaction_notional
            
            all_trades['equities'] = equity_trades_df
            
            if not equity_trades_df.empty:
                new_mv = current_eq_mv + txn_notional_eq
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Transaction Notional", f"${txn_notional_eq:,.0f}")
                with col2:
                    equiv = calculate_equivalent_futures_contracts(abs(txn_notional_eq), positions_df, basket_id)
                    st.metric("Equiv. Futures", f"{int(round(equiv)):,} contracts")
                with col3:
                    st.metric("New Market Value", f"${new_mv:,.0f}")
                
                # Display summary table
                st.markdown("#### Equity Trades Summary")
                
                display_df = equity_trades_df[[
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
                
                # Show first 50 rows with option to expand
                st.dataframe(
                    display_df.head(50),
                    column_config={
                        "TICKER": "Ticker",
                        "COMPANY": "Company",
                        "CURRENT_SHARES": st.column_config.NumberColumn("Current Shares", format="%d"),
                        "CURRENT_MARKET_VALUE": st.column_config.NumberColumn("Current MV ($)", format="$%,.2f"),
                        "TRANSACTION_VALUE": st.column_config.NumberColumn("Txn Value ($)", format="$%,.2f"),
                        "SHARES_TRANSACTED": st.column_config.NumberColumn("Shares Txn", format="%d"),
                        "SHARES_AFTER": st.column_config.NumberColumn("Shares After", format="%d"),
                        "MARKET_VALUE_AFTER": st.column_config.NumberColumn("MV After ($)", format="$%,.2f"),
                    },
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
                
                # Summary stats
                total_txn_value = equity_trades_df['TRANSACTION_VALUE'].sum()
                buy_count = len(equity_trades_df[equity_trades_df['SHARES_TRANSACTED'] > 0])
                sell_count = len(equity_trades_df[equity_trades_df['SHARES_TRANSACTED'] < 0])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Transaction Value", f"${total_txn_value:,.0f}")
                with col2:
                    st.metric("Buy Orders", f"{buy_count:,}")
                with col3:
                    st.metric("Sell Orders", f"{sell_count:,}")
                
                # Export button
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    equity_trades_df.to_excel(writer, index=False, sheet_name='Equity Trades')
                excel_data = excel_buffer.getvalue()
                
                st.download_button(
                    label="📥 Export Equity Trades to Excel",
                    data=excel_data,
                    file_name=f"basket_equity_trades_{basket_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    st.markdown("---")
    
    # ==========================================================================
    # CONFIRM AND SUBMIT ALL
    # ==========================================================================
    st.markdown("### Confirm and Submit All Orders")
    
    def _submit_all_basket_trades(route: str):
        """Submit all basket trades to blotter."""
        trades_added = 0
        
        # Futures trades
        for trade in all_trades.get('futures', []):
            if trade.get('action', 'NONE') == 'NONE':
                continue
            st.session_state["trade_blotter"].append({
                "id": uuid.uuid4().hex,
                "ticker": trade.get('ticker', 'SPX Futures'),
                "side": trade.get('action'),
                "shares": int(round(abs(trade.get('contracts_signed', 0)))),
                "contracts": int(round(abs(trade.get('contracts_signed', 0)))),
                "price": float(trade.get('price', 0)),
                "estimated_value": float(abs(trade.get('notional', 0))),
                "basket_id": basket_id,
                "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "execution_date": "CURRENT",
                "status": "SUBMITTED",
                "route": route,
                "instrument_type": "FUTURE",
            })
            trades_added += 1
        
        # Cash trades
        for trade in all_trades.get('cash', []):
            if trade.get('action', 'NONE') == 'NONE':
                continue
            st.session_state["trade_blotter"].append({
                "id": uuid.uuid4().hex,
                "ticker": "Cash",
                "side": trade.get('action'),
                "shares": 0,
                "price": 0,
                "estimated_value": float(abs(trade.get('notional', 0))),
                "notional": float(trade.get('notional', 0)),
                "basket_id": basket_id,
                "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "execution_date": "CURRENT",
                "status": "SUBMITTED",
                "route": route,
                "instrument_type": trade.get('position_type', 'CASH'),
            })
            trades_added += 1
        
        # Stock borrow trades
        for trade in all_trades.get('stock_borrow', []):
            if trade.get('action', 'NONE') == 'NONE':
                continue
            st.session_state["trade_blotter"].append({
                "id": uuid.uuid4().hex,
                "ticker": "Stock Borrow",
                "side": trade.get('action'),
                "shares": 0,
                "price": 0,
                "estimated_value": float(abs(trade.get('notional', 0))),
                "notional": float(trade.get('notional', 0)),
                "basket_id": basket_id,
                "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "execution_date": "CURRENT",
                "status": "SUBMITTED",
                "route": route,
                "instrument_type": "STOCK_BORROW",
            })
            trades_added += 1
        
        # Equity trades
        equity_df = all_trades.get('equities')
        if equity_df is not None and not equity_df.empty:
            for _, row in equity_df.iterrows():
                shares_transacted = row.get('SHARES_TRANSACTED', 0)
                if abs(shares_transacted) < 1:
                    continue
                
                action = 'BUY' if shares_transacted > 0 else 'SELL'
                price = row.get('PRICE', 0) or (row.get('CURRENT_MARKET_VALUE', 0) / row.get('CURRENT_SHARES', 1) if row.get('CURRENT_SHARES', 0) != 0 else 0)
                
                st.session_state["trade_blotter"].append({
                    "id": uuid.uuid4().hex,
                    "ticker": row.get('TICKER', ''),
                    "side": action,
                    "shares": int(round(abs(shares_transacted))),
                    "price": float(price),
                    "estimated_value": float(abs(row.get('TRANSACTION_VALUE', 0))),
                    "basket_id": basket_id,
                    "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "execution_date": "CURRENT",
                    "status": "SUBMITTED",
                    "route": route,
                    "instrument_type": "EQUITY",
                })
                trades_added += 1
        
        return trades_added
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎯 CONFIRM AND SUBMIT ALL", use_container_width=True, type="primary"):
            has_trades = (
                len(all_trades.get('futures', [])) > 0 or
                len(all_trades.get('cash', [])) > 0 or
                len(all_trades.get('stock_borrow', [])) > 0 or
                (all_trades.get('equities') is not None and not all_trades['equities'].empty)
            )
            
            if has_trades:
                trades_added = _submit_all_basket_trades(route="Bloomberg")
                st.success(f"✅ {trades_added} trade orders generated and submitted to blotter!")
                st.balloons()
            else:
                st.warning("No trades to submit. Enter a notional amount first.")
    
    with col2:
        if st.button("📋 Submit to Blotter Only", use_container_width=True):
            has_trades = (
                len(all_trades.get('futures', [])) > 0 or
                len(all_trades.get('cash', [])) > 0 or
                len(all_trades.get('stock_borrow', [])) > 0 or
                (all_trades.get('equities') is not None and not all_trades['equities'].empty)
            )
            
            if has_trades:
                trades_added = _submit_all_basket_trades(route="Manual")
                st.success(f"✅ {trades_added} trades submitted to blotter!")
                st.balloons()
            else:
                st.warning("No trades to submit.")
    
    with col3:
        if st.button("❌ Cancel", use_container_width=True):
            _clear_basket_session_state()
            st.switch_page("pages/1_📊_Basket_Detail.py")


def _clear_basket_session_state():
    """Clear all basket transaction session state."""
    st.session_state.pop('pending_basket_transaction', None)
    st.session_state.pop('basket_txn_key', None)
    st.session_state.pop('basket_txn_notional', None)
    st.session_state.pop('basket_trades_calculated', None)


# Main content
txn_data = st.session_state.get('pending_basket_transaction', None)

if txn_data:
    render_basket_transaction_page(txn_data)
else:
    st.markdown("""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>🎯</span>
            <span>Basket Transaction</span>
        </h1>
    """, unsafe_allow_html=True)
    
    st.warning("No basket transaction selected. Please click 'Unwind All' or 'Resize All' from the Basket Detail page.")
    
    if st.button("← Back to Home"):
        st.switch_page("app.py")
