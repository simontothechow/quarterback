"""
Quarterback - Calendar View Page
================================
Calendar view of upcoming events, corporate actions, and trade lifecycle events.
Features both a visual monthly calendar and a list view with collapsible event groups.
Clicking on dates shows event details with navigation to basket detail pages.
"""

import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import (
    get_cached_data, get_basket_positions, get_basket_list,
    get_basket_underlying_index
)
from modules.calculations import (
    calculate_corp_action_impact,
    get_affected_baskets_for_ticker,
    calculate_event_trade_recommendations
)
from components.theme import apply_theme, COLORS

# Page configuration
st.set_page_config(
    page_title="Calendar | Quarterback",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply theme
apply_theme()

# Load data
positions_df = get_cached_data('positions')
corp_actions = get_cached_data('corp_actions')
market_data = get_cached_data('market_data')
earnings_df = get_cached_data('earnings')
market_events_df = get_cached_data('market_events')

# Get basket list
baskets = get_basket_list(positions_df)


def get_basket_events(basket_id: str, positions_df: pd.DataFrame) -> list:
    """Get lifecycle events for a basket (maturities, rolls, etc.)"""
    events = []
    basket_positions = get_basket_positions(positions_df, basket_id)
    
    for _, pos in basket_positions.iterrows():
        pos_type = pos.get('POSITION_TYPE', 'Position')
        instrument = pos.get('INSTRUMENT_NAME', pos_type)
        underlying = pos.get('UNDERLYING', '')
        counterparty = pos.get('EXCHANGE_OR_COUNTERPARTY', '')
        pnl = pos.get('PNL_USD', 0)
        if pd.isna(pnl):
            pnl = 0
        
        # End date / maturity events
        end_date = pos.get('END_DATE')
        if pd.notna(end_date):
            # Format end date for display
            end_date_str = pd.Timestamp(end_date).strftime('%b %d, %Y')
            
            # Create more descriptive event based on position type
            if pos_type == 'STOCK_BORROW':
                description = f"{underlying} Stock Loan Maturity - {end_date_str}"
                event_subtype = 'Stock Loan Maturity'
            elif pos_type == 'FUTURE':
                description = f"{instrument} {end_date_str}"
                event_subtype = 'Futures Maturity'
            elif pos_type == 'CASH_BORROW':
                description = f"Cash Borrow Maturity - {counterparty} - {end_date_str}"
                event_subtype = 'Cash Maturity'
            elif pos_type == 'CASH_LEND':
                description = f"Cash Lend Maturity - {counterparty} - {end_date_str}"
                event_subtype = 'Cash Maturity'
            else:
                description = f"{instrument} - Maturity - {end_date_str}"
                event_subtype = 'Other Maturity'
            
            events.append({
                'date': end_date,
                'type': 'Maturity',
                'subtype': event_subtype,
                'description': description,
                'basket': basket_id,
                'category': 'lifecycle',
                'ticker': underlying if underlying else instrument,
                'counterparty': counterparty,
                'position_type': pos_type,
                'pnl': pnl,
                'instrument': instrument
            })
            
            # Roll event if flagged
            if pos.get('ROLL_EVENT_FLAG') == 'TRUE' or pos.get('ROLL_EVENT_FLAG') == True:
                roll_date = end_date - timedelta(days=5)
                roll_date_str = pd.Timestamp(roll_date).strftime('%b %d, %Y')
                events.append({
                    'date': roll_date,
                    'type': 'Roll',
                    'subtype': 'Roll Window',
                    'description': f"{instrument} - Roll Window Opens ({roll_date_str})",
                    'basket': basket_id,
                    'category': 'lifecycle',
                    'ticker': underlying if underlying else instrument,
                    'counterparty': counterparty,
                    'position_type': pos_type,
                    'pnl': pnl,
                    'instrument': instrument
                })
    
    return events


def get_dividend_events_for_calendar(corp_actions_df: pd.DataFrame, 
                                     underlying: str = None) -> list:
    """Get dividend events formatted for calendar display."""
    events = []
    
    if corp_actions_df.empty:
        return events
    
    # Filter for dividends
    dividend_mask = corp_actions_df['ACTION_TYPE'] == 'Dividend'
    if 'ACTION_GROUP' in corp_actions_df.columns:
        dividend_mask = dividend_mask | (corp_actions_df['ACTION_GROUP'] == 'Distribution')
    
    div_df = corp_actions_df[dividend_mask].copy()
    
    # Filter by index if specified
    if underlying and 'INDEX_NAME' in div_df.columns:
        # Use flexible matching - check if underlying contains key index identifier
        # Match "S&P 500", "S&P500", "SP500", etc.
        if 'S&P' in underlying or 'SP' in underlying.upper():
            div_df = div_df[div_df['INDEX_NAME'].str.contains('S&P|SP500', case=False, na=False, regex=True)]
        elif 'TSX' in underlying.upper():
            div_df = div_df[div_df['INDEX_NAME'].str.contains('TSX', case=False, na=False)]
        else:
            div_df = div_df[div_df['INDEX_NAME'].str.contains(underlying, case=False, na=False)]
    
    for _, row in div_df.iterrows():
        eff_date = row.get('EFFECTIVE_DATE')
        if pd.notna(eff_date):
            # Use Bloomberg ticker format to match positions UNDERLYING field
            bloomberg_ticker = row.get('CURRENT_BLOOMBERG_TICKER', '')
            display_ticker = row.get('CURRENT_TICKER', bloomberg_ticker)
            
            if pd.isna(bloomberg_ticker) or not bloomberg_ticker:
                bloomberg_ticker = display_ticker
            if pd.isna(display_ticker) or not display_ticker:
                display_ticker = 'Unknown'
            
            dividend = row.get('DIVIDEND', 0)
            if pd.isna(dividend):
                dividend = 0
            
            events.append({
                'date': eff_date,
                'type': 'Dividend',
                'subtype': 'Cash Dividend',
                'description': f"{display_ticker} - Cash Div ${dividend:.4f}",
                'ticker': str(bloomberg_ticker),  # Use Bloomberg ticker for position matching
                'display_ticker': str(display_ticker),  # Short ticker for display
                'amount': dividend,
                'category': 'dividend',
                'counterparty': '',
                'basket': ''
            })
    
    return events


def get_corporate_action_events(corp_actions_df: pd.DataFrame) -> list:
    """Get non-dividend corporate action events."""
    events = []
    
    if corp_actions_df.empty:
        return events
    
    non_div_types = ['Merger/Acquisition', 'Spin-Off', 'Stock Profile Changes', 
                     'Index Rebalancing', 'Stock Split']
    
    for action_type in non_div_types:
        if 'ACTION_TYPE' in corp_actions_df.columns:
            mask = corp_actions_df['ACTION_TYPE'] == action_type
        elif 'ACTION_GROUP' in corp_actions_df.columns:
            mask = corp_actions_df['ACTION_GROUP'] == action_type
        else:
            continue
        
        action_df = corp_actions_df[mask]
        
        for _, row in action_df.iterrows():
            eff_date = row.get('EFFECTIVE_DATE')
            if pd.notna(eff_date):
                # Use Bloomberg ticker format to match positions UNDERLYING field
                bloomberg_ticker = row.get('CURRENT_BLOOMBERG_TICKER', '')
                display_ticker = row.get('CURRENT_TICKER', bloomberg_ticker)
                
                if pd.isna(bloomberg_ticker) or not bloomberg_ticker:
                    bloomberg_ticker = display_ticker
                if pd.isna(display_ticker) or not display_ticker:
                    display_ticker = 'Unknown'
                
                comments = row.get('COMMENTS', '')
                if pd.isna(comments) or not isinstance(comments, str):
                    comments = ''
                
                events.append({
                    'date': eff_date,
                    'type': action_type,
                    'subtype': action_type,
                    'description': f"{display_ticker} - {action_type}",
                    'ticker': str(bloomberg_ticker),  # Use Bloomberg ticker for position matching
                    'display_ticker': str(display_ticker),  # Short ticker for display
                    'comments': comments[:100] if comments else '',
                    'category': 'corporate_action',
                    'counterparty': '',
                    'basket': ''
                })
    
    return events


def get_earnings_events_for_calendar(
    earnings_df: pd.DataFrame,
    market_data_df: pd.DataFrame,
    allowed_bloomberg_tickers: list[str] | None = None,
) -> list:
    """Get earnings events formatted for calendar display."""
    events = []
    if earnings_df is None or earnings_df.empty:
        return events

    df = earnings_df.copy()
    if "EARNINGS_DATE" not in df.columns:
        return events

    df["EARNINGS_DATE"] = pd.to_datetime(df["EARNINGS_DATE"], errors="coerce")
    df = df[df["EARNINGS_DATE"].notna()]

    if allowed_bloomberg_tickers is not None:
        allowed = set([str(t).strip() for t in allowed_bloomberg_tickers if t])
        if allowed:
            if "BLOOMBERG_TICKER" in df.columns:
                df = df[df["BLOOMBERG_TICKER"].astype(str).isin(allowed)]

    # Company lookup (prefer market data, fallback to excel Company Name)
    company_lookup = {}
    if market_data_df is not None and not market_data_df.empty:
        if "BLOOMBERG_TICKER" in market_data_df.columns and "COMPANY" in market_data_df.columns:
            for _, r in market_data_df[["BLOOMBERG_TICKER", "COMPANY"]].dropna().iterrows():
                company_lookup[str(r["BLOOMBERG_TICKER"])] = str(r["COMPANY"])

    for _, row in df.iterrows():
        bloomberg_ticker = str(row.get("BLOOMBERG_TICKER", "")).strip()
        short_ticker = str(row.get("TICKER", bloomberg_ticker)).strip()
        company = company_lookup.get(bloomberg_ticker) or str(row.get("COMPANY_NAME", "")).strip()
        eff_date = row["EARNINGS_DATE"]

        if not bloomberg_ticker or pd.isna(eff_date):
            continue

        desc = f"{short_ticker} - Earnings"
        if company:
            desc = f"{short_ticker} - Earnings ({company})"

        events.append(
            {
                "date": eff_date,
                "type": "Earnings",
                "subtype": "Earnings",
                "description": desc,
                "ticker": bloomberg_ticker,
                "display_ticker": short_ticker,
                "company": company,
                "category": "earnings",
                "counterparty": "",
                "basket": "",
            }
        )

    return events


def get_market_events_for_calendar(market_events_df: pd.DataFrame) -> list:
    """Get market events (FOMC, holidays, early closes) formatted for calendar display."""
    events = []
    
    if market_events_df is None or market_events_df.empty:
        return events
    
    for _, row in market_events_df.iterrows():
        event_date = row.get('DATE')
        if pd.isna(event_date):
            continue
        
        event_type = str(row.get('EVENT_TYPE', '')).upper()
        event_name = str(row.get('EVENT_NAME', ''))
        description = str(row.get('DESCRIPTION', ''))
        market_closed = row.get('MARKET_CLOSED', False)
        
        # Determine subtype and category based on event type
        if event_type == 'FOMC':
            category = 'fomc'
            subtype = 'FOMC Announcement'
            icon_hint = '🏛️'
        elif event_type == 'HOLIDAY':
            category = 'holiday'
            subtype = 'Market Holiday'
            icon_hint = '🚫'
        elif event_type == 'EARLY_CLOSE':
            category = 'early_close'
            subtype = 'Early Close'
            icon_hint = '⏰'
        else:
            category = 'market_event'
            subtype = event_type
            icon_hint = '📅'
        
        events.append({
            'date': event_date,
            'type': event_type,
            'subtype': subtype,
            'description': f"{event_name} - {description}" if description else event_name,
            'ticker': '',
            'display_ticker': event_name,
            'category': category,
            'counterparty': '',
            'basket': '',
            'market_closed': market_closed,
        })
    
    return events


def get_event_color(category: str, event_type: str = None) -> str:
    """Get color for event category."""
    if category == 'dividend':
        return COLORS['accent_green']
    elif category == 'lifecycle':
        return COLORS['accent_orange']
    elif category == 'corporate_action':
        return COLORS['accent_blue']
    elif category == 'earnings':
        return "#a855f7"  # purple
    elif category == 'fomc':
        return "#ef4444"  # red
    elif category == 'holiday':
        return "#6b7280"  # gray
    elif category == 'early_close':
        return "#f59e0b"  # amber
    return COLORS['text_secondary']


def get_event_icon(category: str) -> str:
    """Get icon for event category."""
    if category == 'dividend':
        return "💵"
    elif category == 'lifecycle':
        return "⏰"
    elif category == 'corporate_action':
        return "📋"
    elif category == 'earnings':
        return "📣"
    elif category == 'fomc':
        return "🏛️"
    elif category == 'holiday':
        return "🚫"
    elif category == 'early_close':
        return "🕐"
    return "📌"


def render_event_detail_popup(selected_date, events: list):
    """Render the event detail popup for a selected date with trade recommendations."""
    
    # Filter events for the selected date
    date_events = [e for e in events 
                   if pd.Timestamp(e['date']).date() == selected_date]
    
    if not date_events:
        st.info(f"No events on {selected_date.strftime('%B %d, %Y')}")
        return
    
    # Header
    st.markdown(f"""
        <div style="background-color: #1a1a1a; padding: 1rem; border-radius: 6px; 
                    border: 2px solid #ff8c00; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #ff8c00; font-weight: 700; font-size: 1.25rem;">
                    📅 {selected_date.strftime('%A, %B %d, %Y')}
                </span>
                <span style="color: #808080;">
                    {len(date_events)} event{'s' if len(date_events) > 1 else ''}
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Group events by subtype
    by_subtype = {}
    for event in date_events:
        subtype = event.get('subtype', event.get('type', 'Other'))
        if subtype not in by_subtype:
            by_subtype[subtype] = []
        by_subtype[subtype].append(event)
    
    # Render each event type group
    for subtype, subtype_events in by_subtype.items():
        category = subtype_events[0].get('category', 'other')
        color = get_event_color(category)
        icon = get_event_icon(category)
        
        # Get unique tickers and baskets
        tickers = list(set([e.get('ticker', '') for e in subtype_events if e.get('ticker')]))
        baskets_affected = list(set([e.get('basket', '') for e in subtype_events if e.get('basket')]))
        counterparties = list(set([e.get('counterparty', '') for e in subtype_events if e.get('counterparty')]))
        
        # Event type header
        st.markdown(f"""
            <div style="background-color: #252525; padding: 0.75rem 1rem; border-radius: 4px; 
                        margin-bottom: 0.5rem; border-left: 4px solid {color};">
                <span style="font-size: 1.1rem;">{icon}</span>
                <span style="color: #fff; font-weight: 600; margin-left: 0.5rem; font-size: 1.1rem;">
                    {subtype}
                </span>
                <span style="color: #808080; margin-left: 1rem;">
                    ({len(subtype_events)} position{'s' if len(subtype_events) > 1 else ''})
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        # Check for trade recommendations for events with index weight changes
        all_recommendations = []
        events_with_impact = []
        
        for event in subtype_events:
            ticker = event.get('ticker', '')
            if ticker and ticker != 'Unknown':
                # Look up the full corp action event data from corp_actions df
                corp_event_data = get_corp_action_event_data(ticker, selected_date)
                if corp_event_data:
                    recommendations = calculate_event_trade_recommendations(
                        corp_event_data, positions_df, market_data
                    )
                    if recommendations:
                        all_recommendations.extend(recommendations)
                        events_with_impact.append({
                            'event': event,
                            'corp_data': corp_event_data,
                            'recommendations': recommendations
                        })
        
        # Determine affected baskets from recommendations
        if all_recommendations:
            rec_baskets = list(set([r['basket_id'] for r in all_recommendations]))
            if rec_baskets:
                baskets_affected = rec_baskets
        
        # Event details card
        with st.container():
            col1, col2 = st.columns(2)
            
            with col1:
                # For earnings, market events, and lifecycle events, show description instead of tickers
                if category in ['earnings', 'fomc', 'holiday', 'early_close', 'lifecycle']:
                    # Get descriptions from events
                    descriptions = [e.get('description', '') for e in subtype_events if e.get('description')]
                    st.markdown(f"""
                        <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; 
                                    padding: 0.75rem; margin-bottom: 0.5rem;">
                            <div style="color: #808080; font-size: 0.8rem; margin-bottom: 0.5rem;">
                                DESCRIPTION
                            </div>
                            <div style="color: #fff; font-size: 0.9rem;">
                                {'<br>'.join(descriptions[:5]) if descriptions else 'N/A'}
                                {'<br>... and ' + str(len(descriptions) - 5) + ' more' if len(descriptions) > 5 else ''}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    # Impacted Tickers for other event types (dividends, corporate actions)
                    st.markdown(f"""
                        <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; 
                                    padding: 0.75rem; margin-bottom: 0.5rem;">
                            <div style="color: #808080; font-size: 0.8rem; margin-bottom: 0.5rem;">
                                IMPACTED TICKERS
                            </div>
                            <div style="color: #fff; font-size: 0.9rem;">
                                {', '.join(tickers[:10]) if tickers else 'N/A'}
                                {'... and ' + str(len(tickers) - 10) + ' more' if len(tickers) > 10 else ''}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Counterparty if applicable
                if counterparties and counterparties[0]:
                    st.markdown(f"""
                        <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; 
                                    padding: 0.75rem; margin-bottom: 0.5rem;">
                            <div style="color: #808080; font-size: 0.8rem; margin-bottom: 0.5rem;">
                                COUNTERPARTY
                            </div>
                            <div style="color: #fff; font-size: 0.9rem;">
                                {', '.join(counterparties)}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                # Impacted Baskets with navigation buttons
                st.markdown(f"""
                    <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; 
                                padding: 0.75rem; margin-bottom: 0.5rem;">
                        <div style="color: #808080; font-size: 0.8rem; margin-bottom: 0.5rem;">
                            IMPACTED BASKETS
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                if baskets_affected:
                    for basket in baskets_affected:
                        if basket:
                            # For lifecycle events, show PNL alongside basket name
                            if category == 'lifecycle':
                                # Get PNL for this basket from the events
                                basket_pnl = sum([e.get('pnl', 0) for e in subtype_events if e.get('basket') == basket])
                                pnl_color = '#00d26a' if basket_pnl >= 0 else '#ff4444'
                                pnl_str = f"${basket_pnl:,.0f}" if basket_pnl >= 0 else f"-${abs(basket_pnl):,.0f}"
                                btn_label = f"📊 {basket} - Current PNL {pnl_str}"
                            else:
                                btn_label = f"📊 Go to {basket}"
                            
                            if st.button(btn_label, key=f"nav_{subtype}_{basket}_{selected_date}", use_container_width=True):
                                st.session_state['selected_basket'] = basket
                                st.switch_page("pages/1_📊_Basket_Detail.py")
                else:
                    # Check if we found any affected baskets via ticker lookup
                    found_baskets = set()
                    for ticker in tickers:
                        if ticker and ticker != 'Unknown':
                            affected = get_affected_baskets_for_ticker(ticker, positions_df)
                            found_baskets.update(affected)
                    
                    if found_baskets:
                        for basket in found_baskets:
                            if st.button(f"📊 Go to {basket}", key=f"nav_found_{subtype}_{basket}_{selected_date}", use_container_width=True):
                                st.session_state['selected_basket'] = basket
                                st.switch_page("pages/1_📊_Basket_Detail.py")
                    else:
                        st.markdown("<span style='color: #808080;'>No affected baskets found in positions</span>", unsafe_allow_html=True)
        
        # Trade Recommendations Section (if any)
        if all_recommendations:
            st.markdown(f"""
                <div style="background-color: #1a2a1a; border: 2px solid #00d26a; border-radius: 6px; 
                            padding: 1rem; margin: 0.5rem 0;">
                    <div style="color: #00d26a; font-weight: 700; font-size: 1.1rem; margin-bottom: 0.75rem;">
                        💹 TRADE RECOMMENDATIONS
                    </div>
            """, unsafe_allow_html=True)
            
            # Show impact summary for each event with recommendations
            for item in events_with_impact:
                corp_data = item['corp_data']
                recs = item['recommendations']
                ticker = corp_data.get('CURRENT_BLOOMBERG_TICKER', 'Unknown')
                
                # Calculate impact
                impact = calculate_corp_action_impact(corp_data, market_data)
                
                st.markdown(f"""
                    <div style="background-color: #252525; padding: 0.5rem 0.75rem; border-radius: 4px; margin-bottom: 0.5rem;">
                        <span style="color: #fff; font-weight: 600;">{ticker}</span>
                        <span style="color: #808080; margin-left: 1rem;">
                            Index Weight: {impact['current_index_weight']*100:.4f}% → {impact['new_index_weight']*100:.4f}%
                            ({impact['shares_change_pct']:+.2f}%)
                        </span>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Recommendations table
            rec_table_data = []
            for rec in all_recommendations:
                action_color = '#00d26a' if rec['action'] == 'BUY' else '#ff4444' if rec['action'] == 'SELL' else '#808080'
                rec_table_data.append({
                    'Basket': rec['basket_id'],
                    'Ticker': rec['ticker'],
                    'Strategy': rec['strategy_type'].replace('_', ' ').title(),
                    'Current': f"{rec['current_shares']:,}",
                    'Target': f"{rec['target_shares']:,}",
                    'Action': rec['action'],
                    'Shares': f"{rec['shares_diff']:,}",
                    'Value': f"${rec['trade_value']:,.0f}",
                    'Price': f"${rec['price']:.2f}"
                })
            
            if rec_table_data:
                rec_df = pd.DataFrame(rec_table_data)
                st.dataframe(
                    rec_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'Action': st.column_config.TextColumn(
                            'Action',
                            help='BUY or SELL recommendation'
                        )
                    }
                )
                
                # Transaction buttons for each recommendation
                st.markdown("**Execute Trades:**")
                rec_cols = st.columns(min(len(all_recommendations), 3))
                for idx, rec in enumerate(all_recommendations):
                    col_idx = idx % 3
                    with rec_cols[col_idx]:
                        if rec['action'] != 'NONE':
                            btn_label = f"{rec['action']} {rec['shares_diff']:,} {rec['ticker']} ({rec['basket_id']})"
                            if st.button(btn_label, key=f"trade_{rec['basket_id']}_{rec['ticker']}_{selected_date}", use_container_width=True):
                                # Store transaction details in session state
                                st.session_state['pending_transaction'] = {
                                    'ticker': rec['ticker'],
                                    'action': rec['action'],
                                    'shares': rec['shares_diff'],
                                    'price': rec['price'],
                                    'value': rec['trade_value'],
                                    'current_shares': rec['current_shares'],
                                    'target_shares': rec['target_shares'],
                                    'basket_id': rec['basket_id'],
                                    'source': 'calendar_event',
                                    'event_date': selected_date.strftime('%Y-%m-%d')
                                }
                                st.switch_page("pages/3_💱_Transaction.py")
        
        # Expandable details table for many events
        if len(subtype_events) > 3:
            with st.expander(f"View all {len(subtype_events)} {subtype} details", expanded=False):
                table_data = []
                for event in subtype_events:
                    table_data.append({
                        'Ticker': event.get('ticker', 'N/A'),
                        'Description': event.get('description', ''),
                        'Counterparty': event.get('counterparty', 'N/A') if event.get('counterparty') else '-',
                        'Basket': event.get('basket', '-') if event.get('basket') else '-'
                    })
                
                table_df = pd.DataFrame(table_data)
                st.dataframe(
                    table_df,
                    use_container_width=True,
                    hide_index=True,
                    height=min(400, 40 + len(table_data) * 35)
                )
        
        st.markdown("---")


def get_corp_action_event_data(ticker: str, event_date) -> dict:
    """Look up the full corporate action event data from the corp_actions dataframe."""
    if corp_actions.empty:
        return None
    
    # Convert event_date to comparable format
    if hasattr(event_date, 'date'):
        event_date = event_date
    
    # Find matching corp action
    for _, row in corp_actions.iterrows():
        row_ticker = row.get('CURRENT_BLOOMBERG_TICKER', row.get('CURRENT_TICKER', ''))
        row_date = row.get('EFFECTIVE_DATE')
        
        if pd.isna(row_ticker) or pd.isna(row_date):
            continue
        
        # Check ticker match
        if str(row_ticker) == str(ticker):
            # Check date match (convert row_date to date for comparison)
            try:
                row_date_obj = pd.Timestamp(row_date).date()
                if row_date_obj == event_date:
                    return row.to_dict()
            except:
                continue
    
    return None


def render_visual_calendar(events: list, year: int, month: int):
    """Render a visual monthly calendar grid with clickable dates."""
    
    # Get calendar data
    cal = calendar.Calendar(firstweekday=6)  # Sunday start
    month_days = cal.monthdayscalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Convert events to a dict keyed by day
    events_df = pd.DataFrame(events) if events else pd.DataFrame()
    events_by_day = {}
    
    if not events_df.empty:
        events_df['date'] = pd.to_datetime(events_df['date'])
        for _, event in events_df.iterrows():
            if event['date'].year == year and event['date'].month == month:
                day = event['date'].day
                if day not in events_by_day:
                    events_by_day[day] = []
                events_by_day[day].append(event.to_dict())
    
    # Calendar header
    st.markdown(f"""
        <div style="background-color: #1a1a1a; padding: 1rem; border-radius: 6px 6px 0 0; 
                    text-align: center; border: 1px solid #333;">
            <span style="color: #ff8c00; font-weight: 700; font-size: 1.5rem;">{month_name} {year}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Day headers using columns
    day_cols = st.columns(7)
    days_header = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    for i, day_name in enumerate(days_header):
        with day_cols[i]:
            st.markdown(f"""
                <div style="background-color: #252525; padding: 0.5rem; text-align: center; 
                            color: #ff8c00; font-weight: 600; border: 1px solid #333;">
                    {day_name}
                </div>
            """, unsafe_allow_html=True)
    
    # Calendar grid
    today = datetime.now().date()
    
    for week_idx, week in enumerate(month_days):
        week_cols = st.columns(7)
        
        for i, day in enumerate(week):
            with week_cols[i]:
                if day == 0:
                    # Empty cell for days outside the month
                    st.markdown("""
                        <div style="min-height: 80px; background-color: #1a1a1a; 
                                    border: 1px solid #333; padding: 0.25rem;">
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    # Check if this is today
                    is_today = (year == today.year and month == today.month and day == today.day)
                    day_events = events_by_day.get(day, [])
                    has_events = len(day_events) > 0
                    
                    # Check if this day is selected
                    selected_date_key = f"{year}-{month:02d}-{day:02d}"
                    is_selected = st.session_state.get('selected_calendar_date') == selected_date_key
                    
                    # Determine styling
                    if is_selected:
                        day_bg = '#3a3a00'
                        border_style = '2px solid #ffd700'
                    elif is_today:
                        day_bg = '#2a2a2a'
                        border_style = '2px solid #ff8c00'
                    else:
                        day_bg = '#1e1e1e'
                        border_style = '1px solid #333'
                    
                    day_color = '#ff8c00' if is_today else '#c0c0c0'
                    day_weight = '700' if is_today else '400'
                    
                    # Build event indicators
                    events_html = ''
                    if day_events:
                        by_category = {}
                        for e in day_events:
                            cat = e.get('category', 'other')
                            if cat not in by_category:
                                by_category[cat] = []
                            by_category[cat].append(e)
                        
                        for cat, cat_events in by_category.items():
                            color = get_event_color(cat)
                            count = len(cat_events)
                            if count <= 2:
                                for e in cat_events:
                                    # For market events, use display_ticker (event name) instead of ticker
                                    if cat in ['fomc', 'holiday', 'early_close']:
                                        label = str(e.get('display_ticker', ''))[:10]
                                    else:
                                        label = str(e.get('ticker', ''))[:8]
                                    events_html += f'<div style="background-color: {color}22; border-left: 2px solid {color}; padding: 2px 4px; margin: 2px 0; font-size: 0.6rem; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{label}</div>'
                            else:
                                # Map category to short display name
                                cat_name_map = {
                                    'dividend': 'Div',
                                    'lifecycle': 'Life',
                                    'corporate_action': 'Corp',
                                    'earnings': 'Earn',
                                    'fomc': 'FOMC',
                                    'holiday': 'Hol',
                                    'early_close': 'Early',
                                }
                                cat_name = cat_name_map.get(cat, 'Event')
                                events_html += f'<div style="background-color: {color}22; border-left: 2px solid {color}; padding: 2px 4px; margin: 2px 0; font-size: 0.6rem; color: #fff;">{count} {cat_name}</div>'
                    
                    # Show the day cell with HTML
                    st.markdown(f"""
                        <div style="min-height: 80px; background-color: {day_bg}; 
                                    border: {border_style}; padding: 0.25rem;">
                            <div style="color: {day_color}; font-weight: {day_weight}; 
                                        font-size: 0.85rem; margin-bottom: 0.25rem;">{day}</div>
                            {events_html}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Add clickable button if there are events
                    if has_events:
                        if st.button("View", key=f"day_{year}_{month}_{day}", use_container_width=True):
                            st.session_state['selected_calendar_date'] = selected_date_key
                            st.rerun()
    
    return events_by_day


def render_list_view(events: list, start_date, end_date):
    """Render the list view with collapsible event groups."""
    
    if not events:
        st.info("No events to display for the selected period and filters.")
        return
    
    # Convert to DataFrame
    events_df = pd.DataFrame(events)
    events_df['date'] = pd.to_datetime(events_df['date'])
    
    # Filter to date range
    events_df = events_df[
        (events_df['date'] >= pd.Timestamp(start_date)) & 
        (events_df['date'] <= pd.Timestamp(end_date))
    ]
    
    if events_df.empty:
        st.info("No events to display for the selected period and filters.")
        return
    
    # Group events by date
    events_by_date = events_df.groupby(events_df['date'].dt.date).apply(
        lambda x: x.to_dict('records')
    ).to_dict()
    
    st.markdown("""
        <div style="background-color: #1a1a1a; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;">
            <span style="color: #ff8c00; font-weight: 600; font-size: 1.1rem;">📅 Event Timeline</span>
        </div>
    """, unsafe_allow_html=True)
    
    sorted_dates = sorted(events_by_date.keys())
    
    for event_date in sorted_dates:
        date_events = events_by_date[event_date]
        date_str = event_date.strftime('%A, %B %d, %Y')
        
        # Date header with click to view details
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"""
                <div style="background-color: #252525; padding: 0.5rem 1rem; border-radius: 4px; 
                            margin: 0.5rem 0; border-left: 4px solid #ff8c00;">
                    <span style="color: #ff8c00; font-weight: 600;">{date_str}</span>
                    <span style="color: #808080; margin-left: 1rem;">({len(date_events)} event{'s' if len(date_events) > 1 else ''})</span>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            if st.button("View Details", key=f"list_view_{event_date}"):
                st.session_state['selected_calendar_date'] = event_date.strftime('%Y-%m-%d')
                st.rerun()
        
        # Group events by subtype for this date
        by_subtype = {}
        for event in date_events:
            subtype = event.get('subtype', event.get('type', 'Other'))
            if subtype not in by_subtype:
                by_subtype[subtype] = []
            by_subtype[subtype].append(event)
        
        # Show brief summary for each group
        for subtype, subtype_events in by_subtype.items():
            category = subtype_events[0].get('category', 'other')
            color = get_event_color(category)
            icon = get_event_icon(category)
            basket = subtype_events[0].get('basket', '')
            
            basket_badge = f'<span style="background-color: #333; padding: 0.1rem 0.5rem; border-radius: 3px; font-size: 0.75rem; margin-left: 0.5rem;">{basket}</span>' if basket else ''
            
            st.markdown(f"""
                <div style="background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; 
                            padding: 0.5rem 1rem; margin: 0.25rem 0 0.25rem 1rem;
                            border-left: 3px solid {color};">
                    <span style="font-size: 1rem;">{icon}</span>
                    <span style="color: #fff; margin-left: 0.5rem;">{len(subtype_events)} {subtype}</span>
                    {basket_badge}
                </div>
            """, unsafe_allow_html=True)


# Sidebar - Back button and filters
with st.sidebar:
    if st.button("← Back to Home", key="back_btn", use_container_width=True):
        st.switch_page("app.py")
    
    st.markdown("---")
    st.markdown("### Navigation")
    if st.button("📊 Basket Detail", use_container_width=True):
        st.switch_page("pages/1_📊_Basket_Detail.py")
    if st.button("🧾 Transactions", use_container_width=True):
        st.switch_page("pages/4_🧾_Transactions_Menu.py")
    
    st.markdown("---")
    st.markdown("### 🔍 Filters")
    
    # Basket filter
    st.markdown("**Baskets**")
    selected_baskets = st.multiselect(
        "Select baskets to display",
        baskets,
        default=baskets,
        key="basket_filter"
    )
    
    st.markdown("---")
    
    # Event type filter
    st.markdown("**Event Types**")
    show_dividends = st.checkbox("Dividends", value=True)
    show_lifecycle = st.checkbox("Trade Lifecycle", value=True)
    show_corp_actions = st.checkbox("Corporate Actions", value=True)
    show_earnings = st.checkbox("Earnings", value=True)
    show_market_events = st.checkbox("Market Events (FOMC/Holidays)", value=True)
    
    st.markdown("---")
    
    # Date range
    st.markdown("**Date Range**")
    today = datetime.now().date()
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From",
            value=today - timedelta(days=7),
            key="start_date"
        )
    with col2:
        end_date = st.date_input(
            "To",
            value=today + timedelta(days=60),
            key="end_date"
        )


# Main content
st.markdown("""
    <h1 style="display: flex; align-items: center; gap: 1rem;">
        <span>📅</span>
        <span>Calendar View</span>
    </h1>
""", unsafe_allow_html=True)

# Gather all events
all_events = []

# Get lifecycle events for selected baskets
if show_lifecycle:
    for basket_id in selected_baskets:
        basket_events = get_basket_events(basket_id, positions_df)
        all_events.extend(basket_events)

# Get dividend events for indices of selected baskets
if show_dividends:
    relevant_indices = set()
    for basket_id in selected_baskets:
        underlying = get_basket_underlying_index(positions_df, basket_id)
        relevant_indices.add(underlying)
    
    for index in relevant_indices:
        div_events = get_dividend_events_for_calendar(corp_actions, index)
        all_events.extend(div_events)

# Get corporate action events
if show_corp_actions:
    corp_events = get_corporate_action_events(corp_actions)
    all_events.extend(corp_events)

# Get earnings events (Top 50) for tickers held in selected baskets
if show_earnings:
    held_tickers = (
        positions_df[
            (positions_df["BASKET_ID"].isin(selected_baskets))
            & (positions_df["POSITION_TYPE"] == "EQUITY")
        ]["UNDERLYING"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    earn_events = get_earnings_events_for_calendar(earnings_df, market_data, allowed_bloomberg_tickers=held_tickers)
    all_events.extend(earn_events)

# Get market events (FOMC announcements, holidays, early closes)
if show_market_events:
    mkt_events = get_market_events_for_calendar(market_events_df)
    all_events.extend(mkt_events)

# Summary stats
if all_events:
    events_in_range = [e for e in all_events 
                       if pd.Timestamp(start_date) <= pd.Timestamp(e['date']) <= pd.Timestamp(end_date)]
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        dividend_count = len([e for e in events_in_range if e.get('category') == 'dividend'])
        st.metric("Dividend Events", dividend_count)
    
    with col2:
        lifecycle_count = len([e for e in events_in_range if e.get('category') == 'lifecycle'])
        st.metric("Lifecycle Events", lifecycle_count)
    
    with col3:
        corp_count = len([e for e in events_in_range if e.get('category') == 'corporate_action'])
        st.metric("Corporate Actions", corp_count)

    with col4:
        earnings_count = len([e for e in events_in_range if e.get('category') == 'earnings'])
        st.metric("Earnings", earnings_count)
    
    with col5:
        market_count = len([e for e in events_in_range if e.get('category') in ['fomc', 'holiday', 'early_close']])
        st.metric("Market Events", market_count)

    # Second row for total (keeps layout tidy)
    col1b, col2b, col3b, col4b, col5b = st.columns(5)
    with col1b:
        st.metric("Total Events", len(events_in_range))

st.markdown("---")

# Check if a date is selected - show event details popup
if 'selected_calendar_date' in st.session_state and st.session_state['selected_calendar_date']:
    selected_date_str = st.session_state['selected_calendar_date']
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        
        # Show close button
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("✕ Close", use_container_width=True):
                st.session_state['selected_calendar_date'] = None
                st.rerun()
        
        # Render the event detail popup
        render_event_detail_popup(selected_date, all_events)
        
    except ValueError:
        st.session_state['selected_calendar_date'] = None

# View toggle tabs
tab_calendar, tab_list = st.tabs(["📆 Calendar View", "📋 List View"])

with tab_calendar:
    # Month navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    
    # Initialize month/year in session state
    if 'calendar_month' not in st.session_state:
        st.session_state.calendar_month = today.month
    if 'calendar_year' not in st.session_state:
        st.session_state.calendar_year = today.year
    
    with col1:
        if st.button("◀ Previous Month", use_container_width=True):
            if st.session_state.calendar_month == 1:
                st.session_state.calendar_month = 12
                st.session_state.calendar_year -= 1
            else:
                st.session_state.calendar_month -= 1
            st.rerun()
    
    with col2:
        st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem;">
                <span style="color: #c0c0c0; font-size: 1rem;">
                    {calendar.month_name[st.session_state.calendar_month]} {st.session_state.calendar_year}
                </span>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        if st.button("Next Month ▶", use_container_width=True):
            if st.session_state.calendar_month == 12:
                st.session_state.calendar_month = 1
                st.session_state.calendar_year += 1
            else:
                st.session_state.calendar_month += 1
            st.rerun()
    
    st.markdown("")  # Spacer
    
    # Render the visual calendar
    render_visual_calendar(all_events, st.session_state.calendar_year, st.session_state.calendar_month)
    
    # Show today button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("📍 Go to Today", use_container_width=True):
            st.session_state.calendar_month = today.month
            st.session_state.calendar_year = today.year
            st.rerun()

with tab_list:
    render_list_view(all_events, start_date, end_date)

# Legend
st.markdown("---")
st.markdown("""
    <div style="background-color: #1e1e1e; padding: 1rem; border-radius: 6px;">
        <span style="color: #808080; font-weight: 600;">Legend:</span>
        <span style="margin-left: 1rem;">💵 <span style="color: #00d26a;">Dividend</span></span>
        <span style="margin-left: 1rem;">⏰ <span style="color: #ff8c00;">Trade Lifecycle</span></span>
        <span style="margin-left: 1rem;">📋 <span style="color: #0088ff;">Corporate Action</span></span>
        <span style="margin-left: 1rem;">📣 <span style="color: #a855f7;">Earnings</span></span>
        <span style="margin-left: 1rem;">🏛️ <span style="color: #ef4444;">FOMC</span></span>
        <span style="margin-left: 1rem;">🚫 <span style="color: #6b7280;">Holiday</span></span>
        <span style="margin-left: 1rem;">🕐 <span style="color: #f59e0b;">Early Close</span></span>
    </div>
""", unsafe_allow_html=True)
