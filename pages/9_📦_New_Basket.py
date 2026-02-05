"""
Quarterback - New Basket Transaction Page
=========================================
Create a new Cash & Carry or Reverse Cash & Carry basket.
Features:
- Strategy direction selector (Short Future/Long Stock vs Long Future/Short Stock)
- Date inputs for trade date, start date, and end date
- Notional-driven sizing that auto-calculates all legs
- Tabbed interface for each leg with counterparty selection
- Auto-generated basket ID
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import uuid
import sys
from pathlib import Path
import io

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import get_cached_data, get_basket_list
from components.theme import apply_theme, COLORS
from modules.calculations import (
    calculate_equity_trades_for_notional,
    calculate_futures_contracts_from_notional,
    SPX_FUTURES_MULTIPLIER,
)

# Page configuration
st.set_page_config(
    page_title="New Basket | Quarterback",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply theme
apply_theme()


def _ensure_trade_blotter():
    """Initialize the demo trade blotter in session state."""
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


def _get_next_basket_id(positions_df: pd.DataFrame) -> str:
    """Generate the next basket ID based on existing baskets."""
    existing_baskets = get_basket_list(positions_df)
    # Extract numbers from existing basket IDs like "Basket1", "Basket2", etc.
    max_num = 0
    for basket in existing_baskets:
        try:
            num = int(basket.replace("Basket", ""))
            max_num = max(max_num, num)
        except ValueError:
            continue
    return f"Basket{max_num + 1}"


# Initialize session state
_ensure_trade_blotter()

# Load data
positions_df = get_cached_data('positions')
market_data_df = get_cached_data('market_data')

# Get next basket ID
if 'new_basket_id' not in st.session_state:
    st.session_state['new_basket_id'] = _get_next_basket_id(positions_df)

new_basket_id = st.session_state['new_basket_id']


# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================
with st.sidebar:
    if st.button("← Back to Home", use_container_width=True):
        st.switch_page("app.py")
    
    st.markdown("---")
    st.markdown("### Navigation")
    
    if st.button("📊 Basket Detail", use_container_width=True):
        st.switch_page("pages/1_📊_Basket_Detail.py")
    if st.button("📅 Calendar", use_container_width=True):
        st.switch_page("pages/2_📅_Calendar.py")
    if st.button("🧾 Trade Blotter", use_container_width=True):
        st.switch_page("pages/4_🧾_Transactions_Menu.py")


# =============================================================================
# PAGE HEADER
# =============================================================================
st.markdown(f"""
    <h1 style="display: flex; align-items: center; gap: 1rem;">
        <span>📦</span>
        <span>Create New Basket</span>
    </h1>
    <p style="color: #808080; margin-bottom: 2rem;">
        New Basket ID: <strong style="color: #ff8c00;">{new_basket_id}</strong>
    </p>
""", unsafe_allow_html=True)


# =============================================================================
# SECTION 1: STRATEGY DIRECTION
# =============================================================================
st.markdown("### 1. Select Strategy Direction")

# Initialize strategy direction in session state
if 'strategy_direction' not in st.session_state:
    st.session_state['strategy_direction'] = None

col1, col2 = st.columns(2)

with col1:
    carry_selected = st.session_state.get('strategy_direction') == 'carry'
    carry_style = "background-color: #1a3a1a; border: 3px solid #00d26a;" if carry_selected else "background-color: #1e1e1e; border: 2px solid #333;"
    
    st.markdown(f"""
        <div style="{carry_style} border-radius: 8px; padding: 1.5rem; text-align: center; margin-bottom: 0.5rem;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">📉📈</div>
            <div style="color: #00d26a; font-size: 1.3rem; font-weight: 700;">Short Future / Long Stock</div>
            <div style="color: #808080; font-size: 0.9rem; margin-top: 0.5rem;">Cash & Carry Strategy</div>
            <div style="color: #606060; font-size: 0.8rem; margin-top: 0.25rem;">Borrow cash to buy stocks, hedge with short futures</div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Select Cash & Carry", key="btn_carry", use_container_width=True, type="primary" if carry_selected else "secondary"):
        st.session_state['strategy_direction'] = 'carry'
        st.rerun()

with col2:
    reverse_selected = st.session_state.get('strategy_direction') == 'reverse_carry'
    reverse_style = "background-color: #3a1a1a; border: 3px solid #ff4444;" if reverse_selected else "background-color: #1e1e1e; border: 2px solid #333;"
    
    st.markdown(f"""
        <div style="{reverse_style} border-radius: 8px; padding: 1.5rem; text-align: center; margin-bottom: 0.5rem;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">📈📉</div>
            <div style="color: #ff4444; font-size: 1.3rem; font-weight: 700;">Long Future / Short Stock</div>
            <div style="color: #808080; font-size: 0.9rem; margin-top: 0.5rem;">Reverse Cash & Carry Strategy</div>
            <div style="color: #606060; font-size: 0.8rem; margin-top: 0.25rem;">Short sell stocks, lend proceeds, hedge with long futures</div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Select Reverse Carry", key="btn_reverse", use_container_width=True, type="primary" if reverse_selected else "secondary"):
        st.session_state['strategy_direction'] = 'reverse_carry'
        st.rerun()


# Only show remaining sections if a direction is selected
if st.session_state.get('strategy_direction') is None:
    st.info("👆 Please select a strategy direction above to continue.")
    st.stop()

strategy = st.session_state['strategy_direction']
is_carry = strategy == 'carry'

st.markdown("---")


# =============================================================================
# SECTION 2: TRADE DATES
# =============================================================================
st.markdown("### 2. Trade Dates")

col1, col2, col3 = st.columns(3)

with col1:
    trade_date = st.date_input(
        "Trade Date",
        value=datetime.now().date(),
        help="Date the trade is executed"
    )

with col2:
    start_date = st.date_input(
        "Start Date",
        value=datetime.now().date(),
        help="Date the position starts accruing"
    )

with col3:
    # Default end date to ~3 months out (typical futures expiry)
    default_end = datetime.now().date() + timedelta(days=90)
    end_date = st.date_input(
        "End / Maturity Date",
        value=default_end,
        help="Target maturity or futures expiry date"
    )

st.markdown("---")


# =============================================================================
# SECTION 3: SIZING
# =============================================================================
st.markdown("### 3. Trade Sizing")

st.markdown("""
    <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem; margin-bottom: 1rem;">
        <span style="color: #ff8c00;">💡</span>
        <span style="color: #c0c0c0;">
            Enter the <strong>futures notional</strong> amount. All other legs (cash, equities, stock borrow) 
            will be automatically sized to match.
        </span>
    </div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    notional = st.number_input(
        "Futures Notional ($)",
        min_value=0.0,
        value=st.session_state.get('new_basket_notional', 100000000.0),
        step=10000000.0,
        format="%.0f",
        help="Total notional value for the basket"
    )
    st.session_state['new_basket_notional'] = notional

with col2:
    # Get current futures price from market data or use default
    futures_price = 6000.0  # Default SPX level
    if market_data_df is not None and not market_data_df.empty:
        # Calculate approximate index level from market caps/weights
        if 'INDEX_MARKET_CAP' in market_data_df.columns:
            total_cap = market_data_df['INDEX_MARKET_CAP'].sum()
            if total_cap > 0:
                futures_price = total_cap / 1e9  # Simplified approximation
    
    # Use a reasonable default
    futures_price = 6000.0
    
    contracts = calculate_futures_contracts_from_notional(notional, futures_price, SPX_FUTURES_MULTIPLIER)
    
    st.markdown(f"""
        <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; padding: 1rem; height: 100%;">
            <div style="color: #808080; font-size: 0.8rem; text-transform: uppercase;">Futures Contracts</div>
            <div style="color: #fff; font-size: 1.5rem; font-weight: 600;">{int(round(contracts)):,} contracts</div>
            <div style="color: #606060; font-size: 0.75rem;">@ SPX {futures_price:,.0f} × {SPX_FUTURES_MULTIPLIER} multiplier</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")


# =============================================================================
# SECTION 4: TABBED LEGS
# =============================================================================
st.markdown("### 4. Configure Trade Legs")

# Custom CSS for larger tabs
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

# Counterparty options
futures_exchanges = ["CME", "ICE", "EUREX", "SGX"]
cash_counterparties = ["Overnight Market", "Goldman Sachs", "Morgan Stanley", "JP Morgan", "Bank of America"]
stock_borrow_counterparties = ["Prime Broker A", "Prime Broker B", "Goldman Sachs", "Morgan Stanley"]
equity_venues = ["Exchange", "Dark Pool", "Algo - VWAP", "Algo - TWAP"]

# Build tabs based on strategy
if is_carry:
    # Carry: Futures + Cash Borrow + Physical Equities
    tabs = st.tabs(["📊 Futures (SHORT)", "💰 Cash Borrow", "📈 Physical Equities (LONG)"])
else:
    # Reverse Carry: Futures + Cash Lend + Stock Borrow + Physical Equities
    tabs = st.tabs(["📊 Futures (LONG)", "💰 Cash Lend", "📉 Stock Borrow", "📈 Physical Equities (SHORT)"])


# -----------------------------------------------------------------------------
# FUTURES TAB
# -----------------------------------------------------------------------------
with tabs[0]:
    futures_direction = "SHORT" if is_carry else "LONG"
    futures_color = "#ff4444" if is_carry else "#00d26a"
    
    st.markdown(f"""
        <div style="background-color: #252525; padding: 1rem; border-radius: 6px; border-left: 4px solid {futures_color}; margin-bottom: 1rem;">
            <span style="color: {futures_color}; font-weight: 700; font-size: 1.1rem;">{futures_direction} SPX AIR Futures</span>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Contracts", f"{int(round(contracts)):,}")
    with col2:
        st.metric("Notional", f"${notional:,.0f}")
    with col3:
        st.metric("Direction", futures_direction)
    
    st.markdown("")
    
    col1, col2 = st.columns(2)
    with col1:
        futures_exchange = st.selectbox(
            "Exchange",
            futures_exchanges,
            index=0,
            key="futures_exchange"
        )
    with col2:
        contract_month = st.text_input(
            "Contract Month",
            value=end_date.strftime("%y-%b").upper(),
            help="e.g., 26-MAR for March 2026"
        )


# -----------------------------------------------------------------------------
# CASH BORROW/LEND TAB
# -----------------------------------------------------------------------------
with tabs[1]:
    cash_type = "BORROW" if is_carry else "LEND"
    cash_color = "#ff8c00"
    cash_direction = "SHORT" if is_carry else "LONG"
    
    st.markdown(f"""
        <div style="background-color: #252525; padding: 1rem; border-radius: 6px; border-left: 4px solid {cash_color}; margin-bottom: 1rem;">
            <span style="color: {cash_color}; font-weight: 700; font-size: 1.1rem;">Cash {cash_type}</span>
            <span style="color: #808080; margin-left: 1rem;">
                {"Borrow cash to finance equity purchase" if is_carry else "Lend proceeds from short sale"}
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Amount", f"${notional:,.0f}")
    with col2:
        financing_rate = st.number_input(
            "Financing Rate (%)",
            min_value=0.0,
            max_value=20.0,
            value=5.3,
            step=0.1,
            format="%.2f",
            key="cash_rate"
        )
    with col3:
        st.metric("Direction", cash_direction)
    
    st.markdown("")
    
    cash_counterparty = st.selectbox(
        "Counterparty",
        cash_counterparties,
        index=0,
        key="cash_counterparty"
    )


# -----------------------------------------------------------------------------
# STOCK BORROW TAB (Reverse Carry only)
# -----------------------------------------------------------------------------
if not is_carry:
    with tabs[2]:
        st.markdown(f"""
            <div style="background-color: #252525; padding: 1rem; border-radius: 6px; border-left: 4px solid #a855f7; margin-bottom: 1rem;">
                <span style="color: #a855f7; font-weight: 700; font-size: 1.1rem;">Stock Borrow</span>
                <span style="color: #808080; margin-left: 1rem;">
                    Borrow shares to short sell
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Borrow Value", f"${notional:,.0f}")
        with col2:
            borrow_fee = st.number_input(
                "Borrow Fee (%)",
                min_value=0.0,
                max_value=20.0,
                value=0.5,
                step=0.1,
                format="%.2f",
                key="borrow_fee"
            )
        with col3:
            st.metric("Direction", "BORROW")
        
        st.markdown("")
        
        stock_borrow_counterparty = st.selectbox(
            "Prime Broker / Counterparty",
            stock_borrow_counterparties,
            index=0,
            key="stock_borrow_counterparty"
        )


# -----------------------------------------------------------------------------
# PHYSICAL EQUITIES TAB
# -----------------------------------------------------------------------------
equities_tab_idx = 2 if is_carry else 3

with tabs[equities_tab_idx]:
    equity_direction = "LONG" if is_carry else "SHORT"
    equity_action = "BUY" if is_carry else "SELL"
    equity_color = "#00d26a" if is_carry else "#ff4444"
    
    st.markdown(f"""
        <div style="background-color: #252525; padding: 1rem; border-radius: 6px; border-left: 4px solid {equity_color}; margin-bottom: 1rem;">
            <span style="color: {equity_color}; font-weight: 700; font-size: 1.1rem;">{equity_action} Physical Equities</span>
            <span style="color: #808080; margin-left: 1rem;">
                Index-weighted S&P 500 basket
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Market Value", f"${notional:,.0f}")
    with col2:
        # Count stocks in market data
        stock_count = len(market_data_df) if market_data_df is not None else 503
        st.metric("Stocks", f"{stock_count}")
    with col3:
        st.metric("Direction", equity_direction)
    
    st.markdown("")
    
    equity_venue = st.selectbox(
        "Execution Venue / Strategy",
        equity_venues,
        index=0,
        key="equity_venue"
    )
    
    # Calculate equity trades
    if notional > 0 and market_data_df is not None and not market_data_df.empty:
        # For new basket, there are no current positions, so we pass empty dataframes
        empty_positions = pd.DataFrame()
        
        # Calculate target allocation based on notional
        equity_trades = []
        
        for _, row in market_data_df.iterrows():
            ticker = row.get('BLOOMBERG_TICKER', '')
            company = row.get('COMPANY', '')
            price = row.get('LOCAL_PRICE', 0)
            index_weight = row.get('INDEX_WEIGHT', 0)
            
            if pd.isna(price) or price <= 0 or pd.isna(index_weight):
                continue
            
            # Calculate allocation
            allocation_value = notional * index_weight
            shares = allocation_value / price
            
            # For short (reverse carry), shares are negative
            if not is_carry:
                shares = -shares
                allocation_value = -allocation_value
            
            equity_trades.append({
                'TICKER': ticker,
                'COMPANY': company,
                'PRICE': price,
                'INDEX_WEIGHT': index_weight,
                'SHARES': int(round(shares)),
                'MARKET_VALUE': allocation_value,
            })
        
        equity_trades_df = pd.DataFrame(equity_trades)
        
        if not equity_trades_df.empty:
            # Show summary
            st.markdown("#### Equity Allocation Preview")
            
            display_df = equity_trades_df.copy()
            display_df['SHARES'] = display_df['SHARES'].round(0).astype(int)
            display_df['MARKET_VALUE'] = display_df['MARKET_VALUE'].round(2)
            display_df['INDEX_WEIGHT'] = (display_df['INDEX_WEIGHT'] * 100).round(4)
            
            st.dataframe(
                display_df.head(50),
                column_config={
                    "TICKER": "Ticker",
                    "COMPANY": st.column_config.TextColumn("Company", width="medium"),
                    "PRICE": st.column_config.NumberColumn("Price ($)", format="$%.2f"),
                    "INDEX_WEIGHT": st.column_config.NumberColumn("Weight (%)", format="%.4f%%"),
                    "SHARES": st.column_config.NumberColumn("Shares", format="%d"),
                    "MARKET_VALUE": st.column_config.NumberColumn("Market Value ($)", format="$%,.2f"),
                },
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            if len(equity_trades_df) > 50:
                st.caption(f"Showing 50 of {len(equity_trades_df)} positions")
            
            # Export button
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                equity_trades_df.to_excel(writer, index=False, sheet_name='Equity Trades')
            excel_data = excel_buffer.getvalue()
            
            st.download_button(
                label="📥 Export Equity Allocation to Excel",
                data=excel_data,
                file_name=f"new_basket_equities_{new_basket_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        equity_trades_df = pd.DataFrame()


st.markdown("---")


# =============================================================================
# SECTION 5: SUMMARY & SUBMIT
# =============================================================================
st.markdown("### 5. Summary & Submit")

# Summary panel
strategy_name = "Cash & Carry" if is_carry else "Reverse Cash & Carry"
futures_dir = "SHORT" if is_carry else "LONG"
equity_dir = "LONG (BUY)" if is_carry else "SHORT (SELL)"
cash_action = "BORROW" if is_carry else "LEND"

st.markdown(f"""
    <div style="background-color: #1a1a1a; border: 2px solid #ff8c00; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem;">
        <div style="color: #ff8c00; font-size: 1.3rem; font-weight: 700; margin-bottom: 1rem;">
            📦 {new_basket_id} - {strategy_name}
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div>
                <div style="color: #808080; font-size: 0.8rem;">FUTURES</div>
                <div style="color: #fff;">{futures_dir} {int(round(contracts)):,} SPX contracts @ {futures_exchange}</div>
            </div>
            <div>
                <div style="color: #808080; font-size: 0.8rem;">CASH</div>
                <div style="color: #fff;">{cash_action} ${notional:,.0f} @ {financing_rate}% via {cash_counterparty}</div>
            </div>
            <div>
                <div style="color: #808080; font-size: 0.8rem;">EQUITIES</div>
                <div style="color: #fff;">{equity_dir} ${notional:,.0f} via {equity_venue}</div>
            </div>
            <div>
                <div style="color: #808080; font-size: 0.8rem;">DATES</div>
                <div style="color: #fff;">{start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}</div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Stock borrow summary for reverse carry
if not is_carry:
    st.markdown(f"""
        <div style="background-color: #252525; border: 1px solid #333; border-radius: 6px; padding: 1rem; margin-bottom: 1rem;">
            <div style="color: #808080; font-size: 0.8rem;">STOCK BORROW</div>
            <div style="color: #fff;">BORROW ${notional:,.0f} @ {borrow_fee}% via {stock_borrow_counterparty}</div>
        </div>
    """, unsafe_allow_html=True)


# Submit button
col1, col2, col3 = st.columns([2, 2, 2])

with col2:
    if st.button("🚀 Create Basket & Generate Orders", type="primary", use_container_width=True):
        # Add all trades to blotter
        trades_added = 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Futures trade
        st.session_state["trade_blotter"].append({
            "id": uuid.uuid4().hex,
            "ticker": f"SPX AIR Futures {contract_month}",
            "side": futures_dir,
            "shares": int(round(contracts)),
            "contracts": int(round(contracts)),
            "price": futures_price,
            "estimated_value": float(notional),
            "basket_id": new_basket_id,
            "order_created_at": now_str,
            "execution_date": trade_date.strftime("%Y-%m-%d"),
            "status": "SUBMITTED",
            "route": futures_exchange,
            "instrument_type": "FUTURE",
        })
        trades_added += 1
        
        # Cash trade
        cash_position_type = "CASH_BORROW" if is_carry else "CASH_LEND"
        st.session_state["trade_blotter"].append({
            "id": uuid.uuid4().hex,
            "ticker": f"Cash {cash_action}",
            "side": cash_action,
            "shares": 0,
            "price": 0,
            "estimated_value": float(notional),
            "notional": float(notional) if is_carry else float(-notional),
            "rate": financing_rate,
            "basket_id": new_basket_id,
            "order_created_at": now_str,
            "execution_date": trade_date.strftime("%Y-%m-%d"),
            "status": "SUBMITTED",
            "route": cash_counterparty,
            "instrument_type": cash_position_type,
        })
        trades_added += 1
        
        # Stock borrow trade (reverse carry only)
        if not is_carry:
            st.session_state["trade_blotter"].append({
                "id": uuid.uuid4().hex,
                "ticker": "Stock Borrow",
                "side": "BORROW",
                "shares": 0,
                "price": 0,
                "estimated_value": float(notional),
                "notional": float(notional),
                "rate": borrow_fee,
                "basket_id": new_basket_id,
                "order_created_at": now_str,
                "execution_date": trade_date.strftime("%Y-%m-%d"),
                "status": "SUBMITTED",
                "route": stock_borrow_counterparty,
                "instrument_type": "STOCK_BORROW",
            })
            trades_added += 1
        
        # Equity trades
        if not equity_trades_df.empty:
            for _, row in equity_trades_df.iterrows():
                shares = row.get('SHARES', 0)
                if abs(shares) < 1:
                    continue
                
                action = 'BUY' if shares > 0 else 'SELL'
                
                st.session_state["trade_blotter"].append({
                    "id": uuid.uuid4().hex,
                    "ticker": row.get('TICKER', ''),
                    "side": action,
                    "shares": int(abs(shares)),
                    "price": float(row.get('PRICE', 0)),
                    "estimated_value": float(abs(row.get('MARKET_VALUE', 0))),
                    "basket_id": new_basket_id,
                    "order_created_at": now_str,
                    "execution_date": trade_date.strftime("%Y-%m-%d"),
                    "status": "SUBMITTED",
                    "route": equity_venue,
                    "instrument_type": "EQUITY",
                })
                trades_added += 1
        
        # Generate new basket ID for next time
        st.session_state['new_basket_id'] = f"Basket{int(new_basket_id.replace('Basket', '')) + 1}"
        
        # Clear strategy selection for fresh start
        st.session_state['strategy_direction'] = None
        st.session_state['new_basket_notional'] = 100000000.0
        
        st.balloons()
        st.success(f"✅ Created {new_basket_id} with {trades_added:,} orders added to Trade Blotter!")
        
        # Offer to go to blotter
        if st.button("📋 View Trade Blotter", use_container_width=True):
            st.switch_page("pages/4_🧾_Transactions_Menu.py")
