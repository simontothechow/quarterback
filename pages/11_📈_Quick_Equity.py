"""
Quarterback - Quick Equity Package Trade Page
==============================================
Standalone page for executing equity package trades (index-weighted or custom).
Accessible via sidebar menu.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import uuid
import sys
from pathlib import Path
import io

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
EQUITY_COUNTERPARTIES = ["Goldman Sachs", "Morgan Stanley", "JP Morgan", "Citadel Securities", "Virtu Financial"]


def calculate_index_weighted_allocation(market_data: pd.DataFrame, notional: float, direction: str) -> pd.DataFrame:
    """
    Calculate share allocation based on S&P 500 index weights.
    
    Args:
        market_data: DataFrame with stock market data
        notional: Target notional value
        direction: 'LONG' (buy) or 'SHORT' (sell/borrow)
    
    Returns:
        DataFrame with allocation details
    """
    if market_data.empty:
        return pd.DataFrame()
    
    df = market_data.copy()
    
    # Map column names (handle both formats)
    if 'EXCHANGE_TICKER' in df.columns:
        df['TICKER'] = df['EXCHANGE_TICKER']
    if 'COMPANY' in df.columns:
        df['COMPANY_NAME'] = df['COMPANY']
    if 'LOCAL_PRICE' in df.columns:
        df['PRICE'] = df['LOCAL_PRICE']
    
    # Ensure numeric columns
    df['INDEX_WEIGHT'] = pd.to_numeric(df['INDEX_WEIGHT'], errors='coerce').fillna(0)
    df['PRICE'] = pd.to_numeric(df['PRICE'], errors='coerce').fillna(0)
    
    # Filter out zero-weight or zero-price stocks
    df = df[(df['INDEX_WEIGHT'] > 0) & (df['PRICE'] > 0)].copy()
    
    if df.empty:
        return pd.DataFrame()
    
    # Normalize weights to sum to 1
    total_weight = df['INDEX_WEIGHT'].sum()
    df['NORM_WEIGHT'] = df['INDEX_WEIGHT'] / total_weight
    
    # Calculate allocation
    df['ALLOCATION_VALUE'] = df['NORM_WEIGHT'] * abs(notional)
    df['SHARES'] = (df['ALLOCATION_VALUE'] / df['PRICE']).round(0).astype(int)
    df['ACTUAL_VALUE'] = df['SHARES'] * df['PRICE']
    
    # Apply direction sign
    if direction == 'SHORT':
        df['SHARES'] = -df['SHARES']
        df['ACTUAL_VALUE'] = -df['ACTUAL_VALUE']
    
    return df[['TICKER', 'COMPANY_NAME', 'PRICE', 'INDEX_WEIGHT', 'NORM_WEIGHT', 
               'SHARES', 'ACTUAL_VALUE']].copy()


def render_quick_equity_page():
    """Render the quick equity package trade page."""
    
    _ensure_trade_blotter()
    
    # Load data
    positions_df = get_cached_data('positions')
    market_data = get_cached_data('market_data')
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
            <span>📈</span>
            <span>Quick Equity Package Trade</span>
        </h1>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <p style="color: #808080; margin-bottom: 2rem;">
            Execute a standalone equity package trade (physical shares or stock borrow).
            Choose index-weighted allocation or customize your own weights.
        </p>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'qe_basket_option' not in st.session_state:
        st.session_state['qe_basket_option'] = "Standalone (No Basket)"
    if 'qe_notional' not in st.session_state:
        st.session_state['qe_notional'] = 10_000_000.0
    if 'qe_direction' not in st.session_state:
        st.session_state['qe_direction'] = "LONG"
    if 'qe_weight_mode' not in st.session_state:
        st.session_state['qe_weight_mode'] = "Index Weighted"
    
    # --- Trade Configuration ---
    st.markdown("### Trade Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Basket association
        basket_options = ["Standalone (No Basket)"] + baskets
        selected_basket_option = st.selectbox(
            "Basket Association",
            basket_options,
            index=basket_options.index(st.session_state.get('qe_basket_option', "Standalone (No Basket)")),
            key="qe_basket_select",
            help="Associate this trade with an existing basket or keep it standalone"
        )
        st.session_state['qe_basket_option'] = selected_basket_option
        basket_id = "" if selected_basket_option == "Standalone (No Basket)" else selected_basket_option
    
    with col2:
        # Trade direction
        direction = st.radio(
            "Direction",
            ["LONG", "SHORT"],
            horizontal=True,
            index=0 if st.session_state.get('qe_direction', 'LONG') == 'LONG' else 1,
            key="qe_direction_radio",
            help="LONG = Buy shares | SHORT = Sell/Borrow shares"
        )
        st.session_state['qe_direction'] = direction
    
    with col3:
        # Trade type
        trade_type = st.radio(
            "Trade Type",
            ["Physical Shares", "Stock Borrow"],
            horizontal=True,
            index=0,
            key="qe_trade_type",
            help="Physical shares or stock loan arrangement"
        )
    
    st.markdown("---")
    
    # --- Weight Mode Selection ---
    st.markdown("### Weighting Method")
    
    col1, col2 = st.columns(2)
    
    with col1:
        weight_mode = st.radio(
            "Allocation Method",
            ["Index Weighted", "Custom Weighted"],
            horizontal=True,
            index=0 if st.session_state.get('qe_weight_mode', 'Index Weighted') == 'Index Weighted' else 1,
            key="qe_weight_mode_radio",
            help="Index weighted uses S&P 500 constituent weights; Custom allows manual weight entry"
        )
        st.session_state['qe_weight_mode'] = weight_mode
    
    st.markdown("---")
    
    # --- Trade Details ---
    st.markdown("### Trade Details")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        trade_date = st.date_input(
            "Trade Date",
            value=datetime.now().date(),
            key="qe_trade_date"
        )
    
    with col2:
        counterparty = st.selectbox(
            "Counterparty",
            EQUITY_COUNTERPARTIES,
            index=0,
            key="qe_counterparty"
        )
    
    with col3:
        # Notional input
        notional = st.number_input(
            "Target Notional ($)",
            min_value=0.0,
            value=st.session_state.get('qe_notional', 10_000_000.0),
            step=1_000_000.0,
            format="%.0f",
            key="qe_notional_input",
            help="Enter the total notional exposure for the equity package"
        )
        st.session_state['qe_notional'] = notional
    
    st.markdown("---")
    
    # --- Allocation Preview ---
    st.markdown("### Equity Allocation Preview")
    
    if weight_mode == "Index Weighted":
        # Calculate index-weighted allocation
        allocation_df = calculate_index_weighted_allocation(market_data, notional, direction)
        
        if allocation_df.empty:
            st.warning("No market data available for allocation calculation.")
            return
        
        # Display summary
        total_shares = allocation_df['SHARES'].abs().sum()
        total_value = allocation_df['ACTUAL_VALUE'].abs().sum()
        position_count = len(allocation_df)
        
        st.info(f"**Allocation Summary:** {position_count} positions | {total_shares:,.0f} total shares | ${total_value:,.0f} total value")
        
        # Prepare display dataframe
        display_df = allocation_df.copy()
        display_df = display_df.rename(columns={
            'TICKER': 'Ticker',
            'COMPANY_NAME': 'Company',
            'PRICE': 'Price',
            'INDEX_WEIGHT': 'Index Weight',
            'SHARES': 'Shares',
            'ACTUAL_VALUE': 'Market Value'
        })
        
        # Format for display
        display_df['Shares'] = display_df['Shares'].apply(lambda x: f"{int(x):,}")
        display_df['Market Value'] = display_df['Market Value'].apply(lambda x: f"${x:,.2f}")
        display_df['Index Weight'] = display_df['Index Weight'].apply(lambda x: f"{x:.4f}")
        display_df['Price'] = display_df['Price'].apply(lambda x: f"${x:,.2f}")
        
        # Remove normalized weight from display
        display_df = display_df.drop(columns=['NORM_WEIGHT'], errors='ignore')
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # Export button
        col_exp1, col_exp2 = st.columns([1, 5])
        with col_exp1:
            # Create Excel download
            buffer = io.BytesIO()
            allocation_df.to_excel(buffer, index=False, sheet_name='Equity_Allocation')
            buffer.seek(0)
            
            st.download_button(
                label="📥 Export to Excel",
                data=buffer,
                file_name=f"equity_allocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    else:  # Custom Weighted
        st.info("**Custom Weighting Mode:** Enter your own ticker weights below.")
        
        # Custom weight input
        st.markdown("#### Enter Custom Weights")
        
        # Show available tickers from market data (handle both column name formats)
        ticker_col = 'EXCHANGE_TICKER' if 'EXCHANGE_TICKER' in market_data.columns else 'TICKER'
        available_tickers = market_data[ticker_col].tolist() if ticker_col in market_data.columns else []
        
        # Initialize custom weights in session state
        if 'qe_custom_weights' not in st.session_state:
            st.session_state['qe_custom_weights'] = {}
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            selected_ticker = st.selectbox(
                "Select Ticker",
                available_tickers,
                key="qe_custom_ticker"
            )
        with col2:
            custom_weight = st.number_input(
                "Weight (%)",
                min_value=0.0,
                max_value=100.0,
                value=5.0,
                step=0.5,
                key="qe_custom_weight_input"
            )
        with col3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Add", key="qe_add_weight"):
                st.session_state['qe_custom_weights'][selected_ticker] = custom_weight / 100.0
                st.rerun()
        
        # Show current custom weights
        if st.session_state['qe_custom_weights']:
            st.markdown("#### Current Custom Weights")
            
            custom_data = []
            # Handle both column name formats
            ticker_col = 'EXCHANGE_TICKER' if 'EXCHANGE_TICKER' in market_data.columns else 'TICKER'
            price_col = 'LOCAL_PRICE' if 'LOCAL_PRICE' in market_data.columns else 'PRICE'
            company_col = 'COMPANY' if 'COMPANY' in market_data.columns else 'COMPANY_NAME'
            
            for ticker, weight in st.session_state['qe_custom_weights'].items():
                ticker_data = market_data[market_data[ticker_col] == ticker]
                if not ticker_data.empty:
                    price = float(ticker_data[price_col].iloc[0])
                    company = ticker_data[company_col].iloc[0]
                    alloc_value = weight * abs(notional)
                    shares = int(alloc_value / price) if price > 0 else 0
                    if direction == 'SHORT':
                        shares = -shares
                    custom_data.append({
                        'Ticker': ticker,
                        'Company': company,
                        'Price': price,
                        'Weight': weight,
                        'Shares': shares,
                        'Market Value': shares * price
                    })
            
            if custom_data:
                custom_df = pd.DataFrame(custom_data)
                allocation_df = custom_df.copy()  # For submission
                
                # Display
                display_custom = custom_df.copy()
                display_custom['Weight'] = display_custom['Weight'].apply(lambda x: f"{x*100:.1f}%")
                display_custom['Price'] = display_custom['Price'].apply(lambda x: f"${x:,.2f}")
                display_custom['Shares'] = display_custom['Shares'].apply(lambda x: f"{int(x):,}")
                display_custom['Market Value'] = display_custom['Market Value'].apply(lambda x: f"${x:,.2f}")
                
                st.dataframe(display_custom, use_container_width=True, hide_index=True)
                
                total_weight = sum(st.session_state['qe_custom_weights'].values())
                st.metric("Total Weight", f"{total_weight*100:.1f}%")
                
                if st.button("🗑️ Clear All Weights", key="qe_clear_weights"):
                    st.session_state['qe_custom_weights'] = {}
                    st.rerun()
            else:
                allocation_df = pd.DataFrame()
        else:
            st.warning("No custom weights defined yet. Add tickers above.")
            allocation_df = pd.DataFrame()
    
    st.markdown("---")
    
    # --- Trade Summary ---
    st.markdown("### Trade Summary")
    
    direction_color = COLORS['accent_green'] if direction == 'LONG' else COLORS['accent_red']
    trade_type_label = "EQUITY" if trade_type == "Physical Shares" else "STOCK_BORROW"
    position_count = len(allocation_df) if not allocation_df.empty else 0
    total_value = allocation_df['ACTUAL_VALUE'].abs().sum() if not allocation_df.empty and 'ACTUAL_VALUE' in allocation_df.columns else (
        allocation_df['Market Value'].apply(lambda x: float(x.replace('$', '').replace(',', '')) if isinstance(x, str) else x).abs().sum() if not allocation_df.empty and 'Market Value' in allocation_df.columns else 0
    )
    
    st.markdown(f"""
        <div style="background-color: #1a1a1a; border: 2px solid {direction_color}; border-radius: 8px; 
                    padding: 1.5rem; margin: 1rem 0;">
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem;">
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Direction</div>
                    <div style="color: {direction_color}; font-size: 1.5rem; font-weight: 700;">{direction}</div>
                </div>
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Positions</div>
                    <div style="color: #fff; font-size: 1.5rem; font-weight: 700;">{position_count}</div>
                </div>
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Total Value</div>
                    <div style="color: #fff; font-size: 1.5rem; font-weight: 700;">${total_value:,.0f}</div>
                </div>
                <div>
                    <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Type</div>
                    <div style="color: #fff; font-size: 1.5rem; font-weight: 700;">{trade_type}</div>
                </div>
            </div>
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #333;">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
                    <div>
                        <span style="color: #808080;">Trade Date: </span>
                        <span style="color: #fff;">{trade_date.strftime('%Y-%m-%d')}</span>
                    </div>
                    <div>
                        <span style="color: #808080;">Counterparty: </span>
                        <span style="color: #fff;">{counterparty}</span>
                    </div>
                    <div>
                        <span style="color: #808080;">Weighting: </span>
                        <span style="color: #fff;">{weight_mode}</span>
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
        if st.button("🚀 Confirm & Generate Orders", use_container_width=True, type="primary"):
            if allocation_df.empty:
                st.error("No positions to submit. Please configure your allocation.")
            else:
                # Add each position to trade blotter
                trades_added = 0
                
                # Handle both index weighted and custom weighted dataframes
                if 'TICKER' in allocation_df.columns:
                    # Index weighted format
                    for _, row in allocation_df.iterrows():
                        shares = int(row['SHARES'])
                        if shares == 0:
                            continue
                        
                        trade = {
                            "id": uuid.uuid4().hex,
                            "trade_type": trade_type_label,
                            "ticker": row['TICKER'],
                            "instrument": row.get('COMPANY_NAME', row['TICKER']),
                            "side": "BUY" if shares > 0 else "SELL",
                            "contracts": None,
                            "shares": abs(shares),
                            "price": float(row['PRICE']),
                            "notional": float(row['ACTUAL_VALUE']),
                            "estimated_value": float(abs(row['ACTUAL_VALUE'])),
                            "basket_id": basket_id if basket_id else "STANDALONE",
                            "counterparty": counterparty,
                            "trade_date": trade_date.strftime("%Y-%m-%d"),
                            "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "execution_date": trade_date.strftime("%Y-%m-%d"),
                            "status": "SUBMITTED",
                            "route": counterparty,
                        }
                        st.session_state["trade_blotter"].append(trade)
                        trades_added += 1
                else:
                    # Custom weighted format
                    for _, row in allocation_df.iterrows():
                        shares = int(row['Shares'])
                        if shares == 0:
                            continue
                        
                        trade = {
                            "id": uuid.uuid4().hex,
                            "trade_type": trade_type_label,
                            "ticker": row['Ticker'],
                            "instrument": row.get('Company', row['Ticker']),
                            "side": "BUY" if shares > 0 else "SELL",
                            "contracts": None,
                            "shares": abs(shares),
                            "price": float(row['Price']),
                            "notional": float(row['Market Value']),
                            "estimated_value": float(abs(row['Market Value'])),
                            "basket_id": basket_id if basket_id else "STANDALONE",
                            "counterparty": counterparty,
                            "trade_date": trade_date.strftime("%Y-%m-%d"),
                            "order_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "execution_date": trade_date.strftime("%Y-%m-%d"),
                            "status": "SUBMITTED",
                            "route": counterparty,
                        }
                        st.session_state["trade_blotter"].append(trade)
                        trades_added += 1
                
                st.success(f"✅ Equity package submitted! {trades_added} positions added to blotter.")
                st.balloons()
    
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.switch_page("app.py")


# Main
render_quick_equity_page()
