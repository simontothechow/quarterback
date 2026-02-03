"""
Quarterback Widgets Module
==========================
Reusable UI widgets for basket display and management.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from modules.calculations import (
    calculate_basket_metrics, calculate_days_to_maturity,
    format_currency, format_bps, calculate_dv01,
    get_rebalancing_alerts, calculate_equity_basket_summary,
    calculate_rebalancing_needs,
    calculate_basket_calendar_trade_recommendations,
    calculate_basket_component_totals,
    calculate_unwind_trades_futures,
    calculate_unwind_trades_cash,
    calculate_unwind_trades_stock_borrow,
)
from components.theme import (
    COLORS, format_value_with_color, render_alert_badge, render_status_badge
)


def render_basket_summary_widget(basket_id: str, positions_df: pd.DataFrame) -> None:
    """
    Render a summary widget for a basket on the home dashboard.
    
    Args:
        basket_id: The basket identifier
        positions_df: DataFrame with all positions for this basket
    """
    metrics = calculate_basket_metrics(positions_df)
    strategy_type = positions_df['STRATEGY_TYPE'].iloc[0] if 'STRATEGY_TYPE' in positions_df.columns else "Unknown"
    underlying = positions_df['UNDERLYING'].iloc[0] if 'UNDERLYING' in positions_df.columns else "S&P 500"
    
    # Format dates
    start_str = metrics['start_date'].strftime('%Y-%m-%d') if metrics['start_date'] else 'N/A'
    end_str = metrics['end_date'].strftime('%Y-%m-%d') if metrics['end_date'] else 'N/A'
    
    # Check for alerts
    alerts = get_basket_alerts(basket_id, positions_df)
    
    # Render card
    with st.container():
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 6px; 
                        padding: 1rem; margin-bottom: 1rem; border-left: 4px solid #ff8c00;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <span style="color: #ff8c00; font-size: 1.25rem; font-weight: 600;">{basket_id}</span>
                    <span style="color: #808080; font-size: 0.85rem;">{strategy_type} | {underlying}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            pnl_color = "normal" if metrics['total_pnl_usd'] >= 0 else "inverse"
            st.metric(
                "P&L", 
                format_currency(metrics['total_pnl_usd']),
                f"{metrics['total_pnl_bps']:.1f} bps",
                delta_color=pnl_color
            )
        
        with col2:
            st.metric(
                "Net Equity Exposure",
                format_currency(metrics['net_equity_exposure'], include_sign=False),
                "⚠️ ALERT" if metrics['hedge_alert'] else "Hedged",
                delta_color="inverse" if metrics['hedge_alert'] else "off"
            )
        
        with col3:
            st.metric(
                "Total Notional",
                f"${metrics['total_notional']:,.0f}",
            )
        
        with col4:
            st.metric(
                "Daily Carry",
                format_currency(metrics['daily_carry']),
            )
        
        # Second row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Start Date", start_str)
        
        with col2:
            st.metric("End Date", end_str)
        
        with col3:
            st.metric("Accrued Carry", format_currency(metrics['accrued_carry']))
        
        with col4:
            st.metric("Carry to Maturity", format_currency(metrics['expected_carry_to_maturity']))
        
        # Alerts section
        if alerts:
            st.markdown("---")
            for alert in alerts:
                alert_color = "#ff4444" if alert['severity'] == 'high' else "#ffd700"
                st.markdown(f"""
                    <div style="background-color: rgba(255, 68, 68, 0.1); border-left: 3px solid {alert_color}; 
                                padding: 0.5rem 1rem; margin: 0.25rem 0; border-radius: 0 4px 4px 0;">
                        <span style="color: {alert_color}; font-weight: 600;">⚠ {alert['type']}</span>
                        <span style="color: #c0c0c0; margin-left: 1rem;">{alert['message']}</span>
                    </div>
                """, unsafe_allow_html=True)


def render_derivatives_widget(positions_df: pd.DataFrame, basket_id: str = "") -> None:
    """
    Render the derivatives (futures) widget for basket detail view.
    
    Args:
        positions_df: DataFrame with positions (will filter for futures)
        basket_id: The basket identifier for transaction routing
    """
    futures_df = positions_df[positions_df['POSITION_TYPE'] == 'FUTURE'].copy()
    
    if futures_df.empty:
        st.info("No futures positions in this basket")
        return
    
    # Header with Unwind/Resize buttons
    header_col, btn_col1, btn_col2 = st.columns([4, 1, 1])
    
    with header_col:
        st.markdown("""
            <div style="background-color: #252525; padding: 0.5rem 1rem; border-radius: 4px;">
                <span style="color: #ff8c00; font-weight: 600;">📊 DERIVATIVES</span>
            </div>
        """, unsafe_allow_html=True)
    
    with btn_col1:
        if st.button("Unwind", key=f"unwind_futures_{basket_id}", use_container_width=True):
            st.session_state['pending_futures_transaction'] = {
                'basket_id': basket_id,
                'mode': 'unwind',
                'positions_df': positions_df,
            }
            st.switch_page("pages/5_📊_Futures_Transaction.py")
    
    with btn_col2:
        if st.button("Resize", key=f"resize_futures_{basket_id}", use_container_width=True):
            st.session_state['pending_futures_transaction'] = {
                'basket_id': basket_id,
                'mode': 'resize',
                'positions_df': positions_df,
            }
            st.switch_page("pages/5_📊_Futures_Transaction.py")
    
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
    
    for _, pos in futures_df.iterrows():
        direction = pos.get('LONG_SHORT', 'N/A')
        direction_color = COLORS['accent_green'] if direction == 'LONG' else COLORS['accent_red']
        
        contract_month = pos.get('CONTRACT_MONTH', 'N/A')
        price = pos.get('PRICE_OR_LEVEL', 0)
        notional = pos.get('NOTIONAL_USD', 0)
        equity_exposure = pos.get('EQUITY_EXPOSURE_USD', 0)
        pnl = pos.get('PNL_USD', 0)
        financing_rate = pos.get('FINANCING_RATE_%', 0)
        
        # Calculate days to maturity
        end_date = pos.get('END_DATE')
        days_to_mat = calculate_days_to_maturity(end_date) if pd.notna(end_date) else 0
        
        # Calculate DV01
        dv01 = calculate_dv01(abs(notional), days_to_mat)
        
        # PNL color
        pnl_color = COLORS['accent_green'] if pnl >= 0 else COLORS['accent_red']
        
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; 
                        padding: 1rem; margin-bottom: 0.75rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                    <div>
                        <span style="color: {direction_color}; font-weight: 600; font-size: 1.1rem;">
                            {direction}
                        </span>
                        <span style="color: #fff; margin-left: 0.5rem;">{pos.get('INSTRUMENT_NAME', 'Future')}</span>
                        <span style="color: #808080; margin-left: 0.5rem;">({contract_month})</span>
                    </div>
                    <div>
                        <span style="color: #808080;">P&L: </span>
                        <span style="color: {pnl_color}; font-weight: 600;">{format_currency(pnl)}</span>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; font-size: 0.85rem;">
                    <div>
                        <div style="color: #808080;">Price</div>
                        <div style="color: #fff;">{price:,.2f}</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Notional</div>
                        <div style="color: #fff;">${abs(notional):,.0f}</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Days to Maturity</div>
                        <div style="color: #fff;">{days_to_mat}</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Implied Rate</div>
                        <div style="color: #fff;">{financing_rate:.2f}%</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Equity Delta</div>
                        <div style="color: #fff;">${equity_exposure:,.0f}</div>
                    </div>
                    <div>
                        <div style="color: #808080;">DV01</div>
                        <div style="color: #fff;">${dv01:,.0f}</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Exchange</div>
                        <div style="color: #fff;">{pos.get('EXCHANGE_OR_COUNTERPARTY', 'N/A')}</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Maturity</div>
                        <div style="color: #fff;">{end_date.strftime('%Y-%m-%d') if pd.notna(end_date) else 'N/A'}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)


def render_physical_shares_widget(positions_df: pd.DataFrame, 
                                  stock_data: pd.DataFrame,
                                  corp_actions: pd.DataFrame,
                                  basket_id: str = "",
                                  expanded: bool = False) -> None:
    """
    Render the enhanced physical shares widget for basket detail view.
    
    Shows:
    - Summary tab with total market value, PNL, position count
    - Unwind/Resize buttons for the entire equity basket
    - Rebalancing alerts as clickable buttons
    - Expanded view with full positions table
    
    Args:
        positions_df: DataFrame with positions for the basket
        stock_data: DataFrame with S&P 500 constituent data
        corp_actions: DataFrame with corporate actions
        basket_id: The basket identifier
        expanded: Whether to show expanded view by default
    """
    # Filter for EQUITY positions (for display)
    equity_df = positions_df[positions_df['POSITION_TYPE'] == 'EQUITY'].copy()
    
    if equity_df.empty:
        st.info("No physical equity positions in this basket")
        return
    
    # Calculate summary and alerts using FULL positions_df (needs futures for direction)
    summary = calculate_equity_basket_summary(positions_df, stock_data)
    
    # Get rebalancing alerts (pass full positions to detect futures direction)
    alerts = get_rebalancing_alerts(positions_df, stock_data)
    
    # Determine direction
    direction = summary['long_short']
    direction_color = COLORS['accent_green'] if direction == 'LONG' else COLORS['accent_red']
    pnl = summary['total_pnl']
    pnl_color = COLORS['accent_green'] if pnl >= 0 else COLORS['accent_red']
    
    # Header with Unwind/Resize buttons
    eq_header_col, eq_btn1, eq_btn2 = st.columns([4, 1, 1])
    
    with eq_header_col:
        st.markdown("""
            <div style="background-color: #252525; padding: 0.5rem 1rem; border-radius: 4px;">
                <span style="color: #ff8c00; font-weight: 600;">📈 PHYSICAL EQUITIES</span>
            </div>
        """, unsafe_allow_html=True)
    
    with eq_btn1:
        if st.button("Unwind", key=f"unwind_equities_{basket_id}", use_container_width=True):
            st.session_state['pending_equity_transaction'] = {
                'basket_id': basket_id,
                'mode': 'unwind',
                'position_type': 'EQUITY',
                'positions_df': positions_df,
            }
            st.switch_page("pages/7_📈_Equity_Transaction.py")
    
    with eq_btn2:
        if st.button("Resize", key=f"resize_equities_{basket_id}", use_container_width=True):
            st.session_state['pending_equity_transaction'] = {
                'basket_id': basket_id,
                'mode': 'resize',
                'position_type': 'EQUITY',
                'positions_df': positions_df,
            }
            st.switch_page("pages/7_📈_Equity_Transaction.py")
    
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
    
    # Summary card
    st.markdown(f"""
        <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; 
                    padding: 1rem; margin-bottom: 0.75rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                <div>
                    <span style="color: {direction_color}; font-weight: 600; font-size: 1.1rem;">
                        {direction}
                    </span>
                    <span style="color: #fff; margin-left: 0.5rem;">S&P 500 Basket</span>
                    <span style="color: #808080; margin-left: 0.5rem;">({summary['position_count']} positions)</span>
                </div>
                <div>
                    <span style="color: #808080;">P&L: </span>
                    <span style="color: {pnl_color}; font-weight: 600;">{format_currency(pnl)}</span>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; font-size: 0.85rem;">
                <div>
                    <div style="color: #808080;">Total Market Value</div>
                    <div style="color: #fff;">${abs(summary['total_market_value']):,.0f}</div>
                </div>
                <div>
                    <div style="color: #808080;">Position Count</div>
                    <div style="color: #fff;">{summary['position_count']}</div>
                </div>
                <div>
                    <div style="color: #808080;">Total P&L</div>
                    <div style="color: {pnl_color};">{format_currency(pnl)}</div>
                </div>
                <div>
                    <div style="color: #808080;">Rebalancing Alerts</div>
                    <div style="color: {'#ff4444' if summary['alerts_count'] > 0 else '#00d26a'};">
                        {summary['alerts_count']} {'⚠️' if summary['alerts_count'] > 0 else '✓'}
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Rebalancing Alerts Section - Clickable buttons
    if alerts:
        st.markdown("""
            <div style="background-color: rgba(255, 68, 68, 0.1); border: 1px solid #ff4444; 
                        border-radius: 4px; padding: 0.75rem; margin: 1rem 0;">
                <div style="color: #ff4444; font-weight: 600; margin-bottom: 0.5rem;">
                    ⚠️ REBALANCING REQUIRED ({} positions)
                </div>
            </div>
        """.format(len(alerts)), unsafe_allow_html=True)
        
        # Display alerts as clickable buttons
        for i, alert in enumerate(alerts):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # Create clickable button for each alert
                action_color = COLORS['accent_green'] if alert['action'] in ['BUY', 'SHORT'] else COLORS['accent_red']
                
                if st.button(
                    f"🔔 {alert['message']}", 
                    key=f"alert_{basket_id}_{i}",
                    use_container_width=True
                ):
                    # Store transaction details in session state and navigate
                    st.session_state['pending_transaction'] = {
                        'ticker': alert['ticker'],
                        'action': alert['action'],
                        'shares': alert['shares'],
                        'price': alert['price'],
                        'value': alert['value'],
                        'current_shares': alert['current_shares'],
                        'target_shares': alert['target_shares'],
                        'basket_id': basket_id,
                        'position_id': alert['position_id']
                    }
                    st.switch_page("pages/3_💱_Transaction.py")
            
            with col2:
                st.markdown(f"""
                    <div style="text-align: center; padding: 0.5rem;">
                        <span style="color: {action_color}; font-weight: 600;">{alert['action']}</span>
                    </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                    <div style="text-align: right; padding: 0.5rem;">
                        <span style="color: #808080;">${alert['value']:,.0f}</span>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background-color: rgba(0, 210, 106, 0.1); border: 1px solid #00d26a; 
                        border-radius: 4px; padding: 0.75rem; margin: 1rem 0; text-align: center;">
                <span style="color: #00d26a; font-weight: 600;">
                    ✓ Portfolio is properly balanced - no rebalancing required
                </span>
            </div>
        """, unsafe_allow_html=True)
    
    # Expanded view - show all positions table
    with st.expander("View All Equity Positions", expanded=expanded):
        # Calculate full rebalancing data for table (pass full positions for futures direction)
        rebal_df = calculate_rebalancing_needs(positions_df, stock_data)
        
        if not rebal_df.empty:
            # Prepare display dataframe
            display_df = rebal_df[[
                'TICKER', 'CURRENT_SHARES', 'TARGET_SHARES', 'SHARES_DIFF',
                'PRICE', 'MARKET_VALUE_USD', 'PNL_USD', 'ACTION'
            ]].copy()
            
            display_df.columns = [
                'Ticker', 'Current Qty', 'Target Qty', 'Difference',
                'Price', 'Market Value', 'P&L', 'Action'
            ]
            
            # Format numeric columns
            display_df['Current Qty'] = display_df['Current Qty'].apply(lambda x: f"{int(x):,}")
            display_df['Target Qty'] = display_df['Target Qty'].apply(lambda x: f"{int(x):,}")
            display_df['Difference'] = display_df['Difference'].apply(lambda x: f"{int(x):+,}")
            display_df['Price'] = display_df['Price'].apply(lambda x: f"${x:,.2f}")
            display_df['Market Value'] = display_df['Market Value'].apply(lambda x: f"${x:,.0f}")
            display_df['P&L'] = display_df['P&L'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")
            display_df['Action'] = display_df['Action'].fillna('-')
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=400
            )
        else:
            st.info("No position data available")


def render_calendar_events_widget(
    all_positions_df: pd.DataFrame,
    stock_data: pd.DataFrame,
    corp_actions: pd.DataFrame,
    basket_id: str,
) -> None:
    """
    Render a Basket Detail widget that unifies calendar events and trade recommendations.
    
    For demo purposes, all trades scheduled from this widget are forward-starting and use
    the event effective date as the execution date.
    """
    st.markdown("""
        <div style="background-color: #252525; padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 1rem;">
            <span style="color: #ff8c00; font-weight: 600;">🗓 CALENDAR EVENTS</span>
        </div>
    """, unsafe_allow_html=True)

    recs = calculate_basket_calendar_trade_recommendations(
        basket_id=basket_id,
        positions_df=all_positions_df,
        corp_actions_df=corp_actions,
        market_data_df=stock_data,
    )

    if not recs:
        st.info("No actionable calendar events found for this basket.")
        return

    # Header row
    header_cols = st.columns([2, 2, 2, 3, 2])
    headers = ["Ticker / Company", "Event Type", "Effective Date", "Recommendation", "Action"]
    for col, label in zip(header_cols, headers):
        with col:
            st.markdown(
                f"<div style='color:#808080; font-size:0.8rem; text-transform:uppercase; font-weight:600; padding:0.25rem 0;'>{label}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<div style='border-bottom: 1px solid #333; margin: 0.25rem 0 0.75rem 0;'></div>", unsafe_allow_html=True)

    for i, r in enumerate(recs):
        action = str(r.get("action", "NONE"))
        if action not in ("BUY", "SELL"):
            continue

        btn_label = "Schedule Buy" if action == "BUY" else "Schedule Sell"
        shares = int(r.get("shares", 0) or 0)
        ticker = r.get("ticker", "N/A")
        company = r.get("company", "")
        event_type = r.get("event_type", "Corporate Action")
        eff_date = r.get("effective_date", "")
        price = float(r.get("price", 0) or 0)
        value = float(r.get("value", 0) or 0)
        current_shares = int(r.get("current_shares", 0) or 0)
        target_shares = int(r.get("target_shares", 0) or 0)

        rec_text = f"{action} {shares:,} shares on {eff_date} @ ${price:,.2f} (≈ ${value:,.0f})"

        cols = st.columns([2, 2, 2, 3, 2])
        with cols[0]:
            st.markdown(f"**{ticker}**")
            if company:
                st.caption(company)
        with cols[1]:
            st.markdown(event_type)
        with cols[2]:
            st.markdown(eff_date)
        with cols[3]:
            st.markdown(rec_text)
            comments = str(r.get("comments", "") or "").strip()
            if comments:
                st.caption(comments)
        with cols[4]:
            if st.button(btn_label, key=f"cal_evt_{basket_id}_{ticker}_{i}", use_container_width=True):
                # Store transaction details (forward-start execution_date from event)
                st.session_state["pending_transaction"] = {
                    "ticker": ticker,
                    "action": action,
                    "shares": shares,
                    "price": price,
                    "value": value,
                    "current_shares": current_shares,
                    "target_shares": target_shares,
                    "basket_id": basket_id,
                    "execution_date": eff_date,
                    "event_date": eff_date,
                    "source": "basket_calendar_widget",
                }
                st.switch_page("pages/3_💱_Transaction.py")

        st.markdown("<div style='margin: 0.5rem 0; border-bottom: 1px solid #333;'></div>", unsafe_allow_html=True)


def render_borrowing_lending_widget(positions_df: pd.DataFrame, basket_id: str = "") -> None:
    """
    Render the borrowing/lending widget for basket detail view.
    
    Shows:
    - Cash Borrow/Lend as individual entries with Unwind/Resize buttons
    - Stock Borrows aggregated into a summary with expandable table and Unwind/Resize buttons
    
    Args:
        positions_df: DataFrame with positions
        basket_id: The basket identifier for transaction routing
    """
    # Filter for cash borrow/lend and stock borrow
    borrow_lend_types = ['CASH_BORROW', 'CASH_LEND', 'STOCK_BORROW']
    bl_df = positions_df[positions_df['POSITION_TYPE'].isin(borrow_lend_types)].copy()
    
    if bl_df.empty:
        return  # Don't show widget if no borrowing/lending
    
    st.markdown("""
        <div style="background-color: #252525; padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 1rem;">
            <span style="color: #ff8c00; font-weight: 600;">💰 BORROWING / LENDING</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Separate cash positions from stock borrows
    cash_positions = bl_df[bl_df['POSITION_TYPE'].isin(['CASH_BORROW', 'CASH_LEND'])]
    stock_borrows = bl_df[bl_df['POSITION_TYPE'] == 'STOCK_BORROW'].copy()
    
    # Render Cash Borrow/Lend positions individually with Unwind/Resize buttons
    for idx, pos in cash_positions.iterrows():
        pos_type = pos.get('POSITION_TYPE', 'N/A')
        
        if pos_type == 'CASH_BORROW':
            label = "Cash Borrowing"
            icon = "🔻"
        else:
            label = "Cash Lending"
            icon = "🔺"
        
        notional = pos.get('NOTIONAL_USD', 0)
        market_value = pos.get('MARKET_VALUE_USD', 0)
        rate = pos.get('FINANCING_RATE_%', 0)
        rate_type = pos.get('FINANCING_RATE_TYPE', 'N/A')
        counterparty = pos.get('EXCHANGE_OR_COUNTERPARTY', 'N/A')
        pnl = pos.get('PNL_USD', 0)
        
        pnl_color = COLORS['accent_green'] if pnl >= 0 else COLORS['accent_red']
        
        # Header row with Unwind/Resize buttons
        cash_header_col, cash_btn1, cash_btn2 = st.columns([4, 1, 1])
        
        with cash_header_col:
            st.markdown(f"""
                <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px 4px 0 0; 
                            padding: 0.75rem 1rem; display: flex; justify-content: space-between;">
                    <div>
                        <span style="font-size: 1.1rem;">{icon}</span>
                        <span style="color: #fff; margin-left: 0.5rem; font-weight: 600;">{label}</span>
                    </div>
                    <div>
                        <span style="color: #808080;">P&L: </span>
                        <span style="color: {pnl_color}; font-weight: 600;">{format_currency(pnl)}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        with cash_btn1:
            if st.button("Unwind", key=f"unwind_cash_{basket_id}_{pos_type}_{idx}", use_container_width=True):
                st.session_state['pending_cash_transaction'] = {
                    'basket_id': basket_id,
                    'mode': 'unwind',
                    'position_type': pos_type,
                    'positions_df': positions_df,
                }
                st.switch_page("pages/6_💰_Cash_Transaction.py")
        
        with cash_btn2:
            if st.button("Resize", key=f"resize_cash_{basket_id}_{pos_type}_{idx}", use_container_width=True):
                st.session_state['pending_cash_transaction'] = {
                    'basket_id': basket_id,
                    'mode': 'resize',
                    'position_type': pos_type,
                    'positions_df': positions_df,
                }
                st.switch_page("pages/6_💰_Cash_Transaction.py")
        
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-top: none; border-radius: 0 0 4px 4px; 
                        padding: 1rem; margin-bottom: 0.75rem;">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; font-size: 0.85rem;">
                    <div>
                        <div style="color: #808080;">Notional</div>
                        <div style="color: #fff;">${abs(notional):,.0f}</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Market Value</div>
                        <div style="color: #fff;">${abs(market_value):,.0f}</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Rate ({rate_type})</div>
                        <div style="color: #fff;">{rate:.2f}%</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Counterparty</div>
                        <div style="color: #fff;">{counterparty}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Render Stock Borrows as aggregated summary with expandable table and Unwind/Resize buttons
    if not stock_borrows.empty:
        # Convert numeric columns
        stock_borrows['QUANTITY'] = pd.to_numeric(stock_borrows['QUANTITY'], errors='coerce').fillna(0)
        stock_borrows['MARKET_VALUE_USD'] = pd.to_numeric(stock_borrows['MARKET_VALUE_USD'], errors='coerce').fillna(0)
        stock_borrows['PNL_USD'] = pd.to_numeric(stock_borrows['PNL_USD'], errors='coerce').fillna(0)
        
        # Calculate summary statistics
        total_market_value = stock_borrows['MARKET_VALUE_USD'].sum()
        total_pnl = stock_borrows['PNL_USD'].sum()
        position_count = len(stock_borrows)
        
        # Get rate info from first row (should be same for all)
        rate = stock_borrows['FINANCING_RATE_%'].iloc[0] if 'FINANCING_RATE_%' in stock_borrows.columns else 0
        rate_type = stock_borrows['FINANCING_RATE_TYPE'].iloc[0] if 'FINANCING_RATE_TYPE' in stock_borrows.columns else 'N/A'
        counterparty = stock_borrows['EXCHANGE_OR_COUNTERPARTY'].iloc[0] if 'EXCHANGE_OR_COUNTERPARTY' in stock_borrows.columns else 'N/A'
        
        pnl_color = COLORS['accent_green'] if total_pnl >= 0 else COLORS['accent_red']
        
        # Header row with Unwind/Resize buttons for Stock Borrow
        sb_header_col, sb_btn1, sb_btn2 = st.columns([4, 1, 1])
        
        with sb_header_col:
            st.markdown(f"""
                <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px 4px 0 0; 
                            padding: 0.75rem 1rem; display: flex; justify-content: space-between;">
                    <div>
                        <span style="font-size: 1.1rem;">📊</span>
                        <span style="color: #fff; margin-left: 0.5rem; font-weight: 600;">Stock Borrowing</span>
                        <span style="color: #808080; margin-left: 0.5rem;">({position_count} positions)</span>
                    </div>
                    <div>
                        <span style="color: #808080;">P&L: </span>
                        <span style="color: {pnl_color}; font-weight: 600;">{format_currency(total_pnl)}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        with sb_btn1:
            if st.button("Unwind", key=f"unwind_stock_borrow_{basket_id}", use_container_width=True):
                st.session_state['pending_equity_transaction'] = {
                    'basket_id': basket_id,
                    'mode': 'unwind',
                    'position_type': 'STOCK_BORROW',
                    'positions_df': positions_df,
                }
                st.switch_page("pages/7_📈_Equity_Transaction.py")
        
        with sb_btn2:
            if st.button("Resize", key=f"resize_stock_borrow_{basket_id}", use_container_width=True):
                st.session_state['pending_equity_transaction'] = {
                    'basket_id': basket_id,
                    'mode': 'resize',
                    'position_type': 'STOCK_BORROW',
                    'positions_df': positions_df,
                }
                st.switch_page("pages/7_📈_Equity_Transaction.py")
        
        # Summary card for stock borrows (body)
        st.markdown(f"""
            <div style="background-color: #1e1e1e; border: 1px solid #333; border-top: none; border-radius: 0 0 4px 4px; 
                        padding: 1rem; margin-bottom: 0.75rem;">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; font-size: 0.85rem;">
                    <div>
                        <div style="color: #808080;">Total Market Value</div>
                        <div style="color: #fff;">${abs(total_market_value):,.0f}</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Positions</div>
                        <div style="color: #fff;">{position_count}</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Rate ({rate_type})</div>
                        <div style="color: #fff;">{rate:.2f}%</div>
                    </div>
                    <div>
                        <div style="color: #808080;">Counterparty</div>
                        <div style="color: #fff;">{counterparty}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Expandable table with individual stock borrow details
        with st.expander("View All Stock Borrow Positions", expanded=False):
            # Prepare display dataframe
            display_df = stock_borrows[[
                'UNDERLYING', 'QUANTITY', 'PRICE_OR_LEVEL', 'MARKET_VALUE_USD', 'PNL_USD'
            ]].copy()
            
            display_df.columns = ['Ticker', 'Quantity', 'Price', 'Market Value', 'P&L']
            
            # Format columns
            display_df['Ticker'] = display_df['Ticker'].str.strip()
            display_df['Quantity'] = display_df['Quantity'].apply(lambda x: f"{int(x):,}")
            display_df['Price'] = pd.to_numeric(display_df['Price'], errors='coerce').apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A")
            display_df['Market Value'] = display_df['Market Value'].apply(lambda x: f"${x:,.0f}")
            display_df['P&L'] = display_df['P&L'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=400
            )


def render_whole_basket_summary(basket_id: str, positions_df: pd.DataFrame) -> None:
    """
    Render the whole basket summary widget showing aggregated KPIs.
    
    Includes "Unwind All" and "Resize All" buttons for full basket operations.
    
    Args:
        basket_id: The basket identifier
        positions_df: DataFrame with all positions for this basket
    """
    metrics = calculate_basket_metrics(positions_df)
    strategy_type = positions_df['STRATEGY_TYPE'].iloc[0] if 'STRATEGY_TYPE' in positions_df.columns else "Unknown"
    
    # Header row with basket info and action buttons
    header_col, btn_col1, btn_col2 = st.columns([4, 1, 1])
    
    with header_col:
        st.markdown(f"""
            <div style="background-color: #1a1a1a; border: 2px solid #ff8c00; border-radius: 6px; 
                        padding: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="color: #ff8c00; font-size: 1.5rem; font-weight: 700;">{basket_id}</span>
                        <span style="color: #808080; margin-left: 1rem; font-size: 1rem;">{strategy_type}</span>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: #808080;">Total Notional: </span>
                        <span style="color: #fff; font-size: 1.25rem; font-weight: 600;">${metrics['total_notional']:,.0f}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with btn_col1:
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Unwind All", key=f"unwind_all_{basket_id}", use_container_width=True, type="primary"):
            st.session_state['pending_basket_transaction'] = {
                'basket_id': basket_id,
                'mode': 'unwind',
                'positions_df': positions_df,
            }
            st.switch_page("pages/8_🎯_Basket_Transaction.py")
    
    with btn_col2:
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("📐 Resize All", key=f"resize_all_{basket_id}", use_container_width=True, type="secondary"):
            st.session_state['pending_basket_transaction'] = {
                'basket_id': basket_id,
                'mode': 'resize',
                'positions_df': positions_df,
            }
            st.switch_page("pages/8_🎯_Basket_Transaction.py")
    
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
    
    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pnl_delta = "normal" if metrics['total_pnl_usd'] >= 0 else "inverse"
        st.metric(
            "Total P&L",
            format_currency(metrics['total_pnl_usd']),
            format_bps(metrics['total_pnl_bps']),
            delta_color=pnl_delta
        )
    
    with col2:
        exposure_status = "⚠️ UNHEDGED" if metrics['hedge_alert'] else "✓ Hedged"
        st.metric(
            "Net Equity Exposure",
            format_currency(metrics['net_equity_exposure'], include_sign=False),
            exposure_status,
            delta_color="inverse" if metrics['hedge_alert'] else "off"
        )
    
    with col3:
        st.metric(
            "Total DV01",
            f"${metrics['total_dv01']:,.0f}",
        )
    
    with col4:
        st.metric(
            "Daily Carry",
            format_currency(metrics['daily_carry']),
        )
    
    # Second row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Accrued Carry", format_currency(metrics['accrued_carry']))
    
    with col2:
        st.metric("Expected Carry to Maturity", format_currency(metrics['expected_carry_to_maturity']))
    
    with col3:
        st.metric("Long Futures", f"${metrics['long_futures_notional']:,.0f}")
    
    with col4:
        st.metric("Short Futures", f"${metrics['short_futures_notional']:,.0f}")


def get_basket_alerts(basket_id: str, positions_df: pd.DataFrame) -> list:
    """
    Get alerts for a basket based on positions and upcoming events.
    
    Args:
        basket_id: The basket identifier
        positions_df: DataFrame with basket positions
    
    Returns:
        List of alert dictionaries with type, message, and severity
    """
    alerts = []
    metrics = calculate_basket_metrics(positions_df)
    today = datetime.now().date()
    
    # Check for hedge alert
    if metrics['hedge_alert']:
        alerts.append({
            'type': 'Physical Share Transaction Required',
            'message': f"Net equity exposure ${metrics['net_equity_exposure']:,.0f} exceeds threshold",
            'severity': 'high'
        })
    
    # Check for upcoming maturities
    if 'END_DATE' in positions_df.columns:
        for _, pos in positions_df.iterrows():
            end_date = pos.get('END_DATE')
            if pd.notna(end_date):
                if isinstance(end_date, str):
                    end_date = pd.to_datetime(end_date).date()
                elif hasattr(end_date, 'date'):
                    end_date = end_date.date()
                
                days_to_end = (end_date - today).days
                
                if 0 <= days_to_end <= 3:
                    pos_type = pos.get('POSITION_TYPE', 'Position')
                    alerts.append({
                        'type': 'Maturity Upcoming',
                        'message': f"{pos_type} matures in {days_to_end} day(s)",
                        'severity': 'high'
                    })
                elif 3 < days_to_end <= 7:
                    pos_type = pos.get('POSITION_TYPE', 'Position')
                    if pos.get('ROLL_EVENT_FLAG') == 'TRUE' or pos.get('ROLL_EVENT_FLAG') == True:
                        alerts.append({
                            'type': 'Roll Upcoming',
                            'message': f"{pos_type} roll in {days_to_end} day(s)",
                            'severity': 'medium'
                        })
    
    return alerts


def get_upcoming_stock_actions(corp_actions: pd.DataFrame, 
                               days_ahead: int = 5) -> pd.DataFrame:
    """
    Get corporate actions for stocks in the next N days.
    
    Args:
        corp_actions: Corporate actions DataFrame
        days_ahead: Number of days to look ahead
    
    Returns:
        Filtered DataFrame with upcoming actions
    """
    if corp_actions.empty or 'EFFECTIVE_DATE' not in corp_actions.columns:
        return pd.DataFrame()
    
    today = pd.Timestamp.now().normalize()
    end_date = today + pd.Timedelta(days=days_ahead)
    
    mask = (corp_actions['EFFECTIVE_DATE'] >= today) & \
           (corp_actions['EFFECTIVE_DATE'] <= end_date)
    
    return corp_actions[mask].sort_values('EFFECTIVE_DATE')
