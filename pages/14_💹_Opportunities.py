"""
Quarterback - Financing Opportunities Scanner
=============================================
Multi-strategy opportunity scanner for equity financing arbitrage.

Tabs:
1. Summary - Overview of best opportunities across all strategies
2. Calendar Spreads - Forward rate matrix and trade builder
3. Spot Cash & Carry - Futures vs box spread arbitrage
4. Forward Arbitrage - Calendar futures + calendar box

All key calculations are centralized in modules/calculations.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import (
    get_cached_data,
    get_combined_rate_data,
    generate_mock_box_spreads,
    generate_mock_futures_rates,
)
from modules.calculations import (
    calculate_forward_rate_matrix,
    calculate_carry_matrix,
    filter_opportunities_by_criteria,
    calculate_dv01_calendar_spread,
    calculate_notional_from_dv01_budget,
    calculate_spot_arb_metrics,
    calculate_forward_arb_metrics,
    generate_synthetic_historical_spreads,
    calculate_percentile_vs_history,
    get_best_opportunity_for_tenor,
    get_valuation_date,
    DEMO_MODE,
)
from modules.opportunities_config import (
    SOFR_RATE,
    TENOR_BUCKETS,
    STRATEGIES,
    DEFAULT_NOTIONAL,
    get_tenor_bucket,
    get_sofr_rate_pct,
)
from components.theme import COLORS


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def _ensure_session_state():
    """Initialize session state for Opportunities page."""
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []
    if "selected_opportunity" not in st.session_state:
        st.session_state["selected_opportunity"] = None
    if "selected_strategy" not in st.session_state:
        st.session_state["selected_strategy"] = None


# =============================================================================
# SHARED UI COMPONENTS
# =============================================================================

def _show_demo_banner():
    """Display demo mode banner with valuation date."""
    val_date = get_valuation_date()
    st.markdown(f"""
        <div style="background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%); 
                    padding: 10px 20px; border-radius: 8px; margin-bottom: 20px;
                    border-left: 4px solid #e94560;">
            <span style="color: #e94560; font-weight: bold;">📊 DEMO MODE</span>
            <span style="color: #a0a0a0; margin-left: 15px;">
                Valuation Date: {val_date.strftime('%B %d, %Y')} | 
                SOFR: {get_sofr_rate_pct():.2f}%
            </span>
        </div>
    """, unsafe_allow_html=True)


def _render_rate_cards(sofr_rate_pct: float, futures_rate_pct: float, spread_bps: float):
    """Render the rate summary cards at the top."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Box Spreads (SOFR)",
            value=f"{sofr_rate_pct:.2f}%",
            help="Risk-free rate proxy from box spreads"
        )
    
    with col2:
        st.metric(
            label="Equity Futures",
            value=f"{futures_rate_pct:.2f}%",
            help="Implied equity financing rate"
        )
    
    with col3:
        st.metric(
            label="Arb Spread",
            value=f"{spread_bps:.0f} bps",
            delta=f"{spread_bps - 25:.0f} vs avg" if spread_bps > 25 else None,
            delta_color="normal",
            help="Equity premium over risk-free"
        )
    
    with col4:
        st.metric(
            label="90-Day Avg",
            value="25 bps",
            help="Historical average spread"
        )


def _render_trade_builder(
    opportunity: dict,
    strategy_type: str,
    contracts_df: pd.DataFrame = None
):
    """
    Unified trade builder with Notional OR DV01 budget sizing.
    
    Args:
        opportunity: Opportunity dict with contract details
        strategy_type: One of 'calendar_spread', 'spot_arb', 'forward_arb'
        contracts_df: Optional contracts data for labels
    """
    st.markdown("### 🔧 Trade Builder")
    
    # Build contract lookup for labels
    contract_labels = {}
    if contracts_df is not None and not contracts_df.empty:
        for _, row in contracts_df.iterrows():
            code = row.get('Contract_Code', '')
            maturity = row.get('Maturity')
            if pd.notna(maturity):
                try:
                    mat_label = pd.to_datetime(maturity).strftime("%b %Y")
                    contract_labels[code] = mat_label
                except:
                    contract_labels[code] = code
    
    # Get period days
    period_days = opportunity.get('period_days', 90)
    
    # Sizing mode selection
    col1, col2 = st.columns(2)
    
    with col1:
        sizing_mode = st.radio(
            "Size by:",
            ["Notional", "DV01 Budget"],
            horizontal=True,
            key=f"sizing_mode_{strategy_type}"
        )
    
    with col2:
        if sizing_mode == "Notional":
            notional = st.number_input(
                "Notional ($)",
                min_value=1_000_000,
                max_value=1_000_000_000,
                value=DEFAULT_NOTIONAL,
                step=10_000_000,
                format="%d",
                key=f"notional_{strategy_type}"
            )
            dv01 = calculate_dv01_calendar_spread(notional, period_days)
        else:
            dv01_budget = st.number_input(
                "Max DV01 ($)",
                min_value=100,
                max_value=100_000,
                value=3000,
                step=500,
                key=f"dv01_budget_{strategy_type}"
            )
            notional = calculate_notional_from_dv01_budget(dv01_budget, period_days)
            dv01 = dv01_budget
    
    # Display calculated metrics
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Notional", f"${notional:,.0f}")
    
    with col2:
        st.metric("DV01", f"${dv01:,.0f}")
    
    with col3:
        # Calculate estimated P&L based on strategy
        spread_bps = opportunity.get('forward_rate', 0) - opportunity.get('box_rate_bps', SOFR_RATE * 10000)
        if strategy_type == 'calendar_spread':
            spread_bps = opportunity.get('annualized_carry', 0)
        
        # P&L = spread × notional × (days/360)
        time_factor = period_days / 360
        est_pnl = (spread_bps / 10000) * notional * time_factor
        st.metric("Est. Gross P&L", f"${est_pnl:,.0f}")
    
    # Trade details
    st.markdown("#### Trade Legs")
    
    if strategy_type == 'calendar_spread':
        from_code = opportunity.get('from_contract', '')
        to_code = opportunity.get('to_contract', '')
        from_label = contract_labels.get(from_code, from_code)
        to_label = contract_labels.get(to_code, to_code)
        
        leg_col1, leg_col2 = st.columns(2)
        with leg_col1:
            st.success(f"**LEG 1: LONG** {from_label} ({from_code})")
        with leg_col2:
            st.error(f"**LEG 2: SHORT** {to_label} ({to_code})")
    
    elif strategy_type == 'spot_arb':
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("**LEG 1:** Own S&P 500 Stocks")
        with col2:
            st.error("**LEG 2:** SELL Futures")
        with col3:
            st.warning("**LEG 3:** SHORT Box (Borrow)")
    
    elif strategy_type == 'forward_arb':
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Futures Calendar:**")
            st.success("LONG Near Futures")
            st.error("SHORT Far Futures")
        with col2:
            st.markdown("**Box Calendar:**")
            st.error("SHORT Near Box")
            st.success("LONG Far Box")
    
    # Execute button
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col2:
        if st.button("🚀 Add to Blotter", type="primary", use_container_width=True,
                     key=f"execute_{strategy_type}"):
            _add_trades_to_blotter(opportunity, notional, dv01, strategy_type, contract_labels)
            st.success("✅ Trade added to blotter!")
            st.balloons()


def _add_trades_to_blotter(
    opportunity: dict,
    notional: float,
    dv01: float,
    strategy_type: str,
    contract_labels: dict = None
):
    """Add trade(s) to the session state blotter."""
    if contract_labels is None:
        contract_labels = {}
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trade_id = str(uuid.uuid4())[:8]
    
    if strategy_type == 'calendar_spread':
        from_code = opportunity.get('from_contract', '')
        to_code = opportunity.get('to_contract', '')
        from_label = contract_labels.get(from_code, from_code)
        to_label = contract_labels.get(to_code, to_code)
        
        # Add two trades: long near, short far
        st.session_state["trade_blotter"].append({
            'trade_id': f"{trade_id}-L",
            'timestamp': timestamp,
            'strategy': 'Calendar Spread',
            'direction': 'LONG',
            'instrument': f"SPX Futures {from_label}",
            'contract': from_code,
            'notional': notional,
            'rate_bps': opportunity.get('forward_rate', 0),
            'dv01': dv01,
            'status': 'PENDING',
        })
        st.session_state["trade_blotter"].append({
            'trade_id': f"{trade_id}-S",
            'timestamp': timestamp,
            'strategy': 'Calendar Spread',
            'direction': 'SHORT',
            'instrument': f"SPX Futures {to_label}",
            'contract': to_code,
            'notional': -notional,
            'rate_bps': opportunity.get('forward_rate', 0),
            'dv01': dv01,
            'status': 'PENDING',
        })
    
    elif strategy_type == 'spot_arb':
        expiry = opportunity.get('expiry_label', 'N/A')
        
        st.session_state["trade_blotter"].append({
            'trade_id': f"{trade_id}-EQ",
            'timestamp': timestamp,
            'strategy': 'Spot Cash & Carry',
            'direction': 'LONG',
            'instrument': 'S&P 500 Basket',
            'contract': 'EQUITY',
            'notional': notional,
            'rate_bps': opportunity.get('futures_rate_bps', 0),
            'dv01': dv01,
            'status': 'PENDING',
        })
        st.session_state["trade_blotter"].append({
            'trade_id': f"{trade_id}-FUT",
            'timestamp': timestamp,
            'strategy': 'Spot Cash & Carry',
            'direction': 'SHORT',
            'instrument': f"SPX Futures {expiry}",
            'contract': opportunity.get('contract', ''),
            'notional': -notional,
            'rate_bps': opportunity.get('futures_rate_bps', 0),
            'dv01': dv01,
            'status': 'PENDING',
        })
        st.session_state["trade_blotter"].append({
            'trade_id': f"{trade_id}-BOX",
            'timestamp': timestamp,
            'strategy': 'Spot Cash & Carry',
            'direction': 'SHORT',
            'instrument': f"Box Spread {expiry}",
            'contract': 'BOX',
            'notional': -notional,
            'rate_bps': opportunity.get('box_rate_bps', 0),
            'dv01': 0,
            'status': 'PENDING',
        })
    
    elif strategy_type == 'forward_arb':
        from_label = opportunity.get('from_label', 'Near')
        to_label = opportunity.get('to_label', 'Far')
        
        # Futures calendar
        st.session_state["trade_blotter"].append({
            'trade_id': f"{trade_id}-FN",
            'timestamp': timestamp,
            'strategy': 'Forward Arbitrage',
            'direction': 'LONG',
            'instrument': f"SPX Futures {from_label}",
            'contract': opportunity.get('from_contract', ''),
            'notional': notional,
            'rate_bps': opportunity.get('fwd_futures_rate_bps', 0),
            'dv01': dv01,
            'status': 'PENDING',
        })
        st.session_state["trade_blotter"].append({
            'trade_id': f"{trade_id}-FF",
            'timestamp': timestamp,
            'strategy': 'Forward Arbitrage',
            'direction': 'SHORT',
            'instrument': f"SPX Futures {to_label}",
            'contract': opportunity.get('to_contract', ''),
            'notional': -notional,
            'rate_bps': opportunity.get('fwd_futures_rate_bps', 0),
            'dv01': dv01,
            'status': 'PENDING',
        })
        # Box calendar
        st.session_state["trade_blotter"].append({
            'trade_id': f"{trade_id}-BN",
            'timestamp': timestamp,
            'strategy': 'Forward Arbitrage',
            'direction': 'SHORT',
            'instrument': f"Box Spread {from_label}",
            'contract': 'BOX',
            'notional': -notional,
            'rate_bps': opportunity.get('fwd_box_rate_bps', 0),
            'dv01': 0,
            'status': 'PENDING',
        })
        st.session_state["trade_blotter"].append({
            'trade_id': f"{trade_id}-BF",
            'timestamp': timestamp,
            'strategy': 'Forward Arbitrage',
            'direction': 'LONG',
            'instrument': f"Box Spread {to_label}",
            'contract': 'BOX',
            'notional': notional,
            'rate_bps': opportunity.get('fwd_box_rate_bps', 0),
            'dv01': 0,
            'status': 'PENDING',
        })


# =============================================================================
# SUMMARY TAB
# =============================================================================

def _render_summary_tab(rate_data: dict, opportunities: list, contracts_df: pd.DataFrame):
    """Render the Summary tab with opportunity cards across strategies."""
    
    st.markdown("## 📊 Best Opportunities by Tenor")
    
    # Tenor bucket selector
    tenor_options = [b["name"] for b in TENOR_BUCKETS]
    selected_tenor = st.radio(
        "Select Tenor:",
        tenor_options,
        horizontal=True,
        index=1,  # Default to 3-6 Month
        key="tenor_selector"
    )
    
    # Get selected bucket
    selected_bucket = next(b for b in TENOR_BUCKETS if b["name"] == selected_tenor)
    
    st.markdown("---")
    
    # Strategy cards
    col1, col2, col3 = st.columns(3)
    
    # Calculate best opportunities for each strategy
    sofr_rate = rate_data['sofr_rate']
    box_spreads = rate_data['box_spreads']
    futures_rates = rate_data['futures_rates']
    
    # Calendar Spread - best from existing opportunities
    best_calendar = get_best_opportunity_for_tenor(
        opportunities,
        selected_bucket["min_days"],
        selected_bucket["max_days"],
        metric='annualized_carry'
    )
    
    # Spot Arb - best single expiry within tenor
    best_spot = None
    if not futures_rates.empty and not box_spreads.empty:
        merged = futures_rates.merge(
            box_spreads[['Days_to_Expiry', 'Box_Rate', 'Expiry_Label']],
            on='Days_to_Expiry',
            how='inner'
        )
        tenor_filtered = merged[
            (merged['Days_to_Expiry'] >= selected_bucket["min_days"]) &
            (merged['Days_to_Expiry'] <= selected_bucket["max_days"])
        ]
        if not tenor_filtered.empty:
            tenor_filtered = tenor_filtered.copy()
            tenor_filtered['spread_bps'] = (tenor_filtered['Futures_Rate'] - tenor_filtered['Box_Rate']) * 10000
            best_idx = tenor_filtered['spread_bps'].idxmax()
            best_row = tenor_filtered.loc[best_idx]
            best_spot = {
                'spread_bps': best_row['spread_bps'],
                'expiry_label': best_row['Expiry_Label_x'],
                'days': best_row['Days_to_Expiry'],
                'futures_rate': best_row['Futures_Rate'],
                'box_rate': best_row['Box_Rate'],
                'contract': best_row.get('Contract_Code', ''),
            }
    
    # Forward Arb (same as calendar but with reduced spread for boxes)
    best_forward = None
    if best_calendar:
        # Forward arb spread is smaller than calendar spread
        fwd_spread = best_calendar.get('annualized_carry', 0) * 0.25  # ~25% of futures spread
        best_forward = {
            'spread_bps': fwd_spread,
            'period_days': best_calendar.get('period_days', 90),
            'from_contract': best_calendar.get('from_contract', ''),
            'to_contract': best_calendar.get('to_contract', ''),
        }
    
    # Render cards
    with col1:
        _render_opportunity_card(
            "Calendar Spread",
            "📅",
            best_calendar.get('annualized_carry', 0) if best_calendar else 0,
            f"{best_calendar.get('from_contract', '')} → {best_calendar.get('to_contract', '')}" if best_calendar else "N/A",
            best_calendar.get('period_days', 0) if best_calendar else 0,
            "calendar_spread",
            best_calendar
        )
    
    with col2:
        _render_opportunity_card(
            "Spot Cash & Carry",
            "💰",
            best_spot['spread_bps'] if best_spot else 0,
            best_spot['expiry_label'] if best_spot else "N/A",
            best_spot['days'] if best_spot else 0,
            "spot_arb",
            best_spot
        )
    
    with col3:
        _render_opportunity_card(
            "Forward Arbitrage",
            "🔄",
            best_forward['spread_bps'] if best_forward else 0,
            f"{best_forward.get('from_contract', '')} → {best_forward.get('to_contract', '')}" if best_forward else "N/A",
            best_forward.get('period_days', 0) if best_forward else 0,
            "forward_arb",
            best_forward
        )
    
    # Historical spread chart
    st.markdown("---")
    st.markdown("### 📈 Spread vs History")
    
    current_spread = best_calendar.get('annualized_carry', 30) if best_calendar else 30
    history = generate_synthetic_historical_spreads(current_spread, 90)
    
    # Convert to DataFrame for chart
    history_df = pd.DataFrame(history)
    history_df['date'] = pd.to_datetime(history_df['date'])
    
    # Create chart
    st.line_chart(
        history_df.set_index('date')['spread_bps'],
        use_container_width=True
    )
    
    # Show percentile
    hist_values = [h['spread_bps'] for h in history]
    percentile = calculate_percentile_vs_history(current_spread, hist_values)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Current Percentile", f"{percentile:.0f}th")
    with col2:
        if percentile >= 75:
            st.success(f"Current spread ({current_spread:.0f} bps) is in the **upper quartile** - attractive entry point!")
        elif percentile >= 50:
            st.info(f"Current spread ({current_spread:.0f} bps) is **above median** - reasonable opportunity.")
        else:
            st.warning(f"Current spread ({current_spread:.0f} bps) is **below average** - consider waiting.")


def _render_opportunity_card(
    strategy_name: str,
    icon: str,
    spread_bps: float,
    period_label: str,
    period_days: int,
    strategy_key: str,
    opportunity: dict
):
    """Render a standardized opportunity card."""
    
    # Calculate P&L estimate
    pnl_estimate = (spread_bps / 10000) * DEFAULT_NOTIONAL * (period_days / 360) if period_days > 0 else 0
    dv01 = calculate_dv01_calendar_spread(DEFAULT_NOTIONAL, period_days) if period_days > 0 else 0
    
    # Card styling
    card_color = "#2d3436" if spread_bps > 0 else "#1a1a2e"
    border_color = "#00cec9" if spread_bps > 25 else "#636e72"
    
    st.markdown(f"""
        <div style="background: {card_color}; padding: 20px; border-radius: 12px; 
                    border: 2px solid {border_color}; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 1.5em;">{icon}</span>
                <span style="background: #636e72; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">
                    {period_days} days
                </span>
            </div>
            <h3 style="margin: 10px 0 5px 0; color: white;">{strategy_name}</h3>
            <div style="font-size: 2em; color: #00cec9; font-weight: bold;">
                {spread_bps:.0f} bps
            </div>
            <div style="color: #a0a0a0; font-size: 0.9em; margin-bottom: 10px;">
                {period_label}
            </div>
            <div style="display: flex; justify-content: space-between; color: #a0a0a0; font-size: 0.85em;">
                <span>P&L: ${pnl_estimate:,.0f}</span>
                <span>DV01: ${dv01:,.0f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if opportunity and st.button(f"Build Trade →", key=f"build_{strategy_key}", use_container_width=True):
        st.session_state["selected_opportunity"] = opportunity
        st.session_state["selected_strategy"] = strategy_key


# =============================================================================
# CALENDAR SPREADS TAB
# =============================================================================

def _render_calendar_spreads_tab(contracts_df: pd.DataFrame, opportunities: list):
    """Render the Calendar Spreads tab with matrix and trade builder."""
    
    st.markdown("## 📅 Calendar Spread Opportunities")
    st.markdown("*Long near contract / Short far contract - earn carry as spread converges*")
    
    # Calculate matrices
    as_of_date = get_valuation_date()
    fwd_matrix = calculate_forward_rate_matrix(contracts_df, as_of_date=as_of_date)
    carry_matrix = calculate_carry_matrix(contracts_df, as_of_date=as_of_date)
    
    # Build contract label lookup
    contract_labels = {}
    for _, row in contracts_df.iterrows():
        code = row.get('Contract_Code', '')
        maturity = row.get('Maturity')
        if pd.notna(maturity):
            try:
                mat_label = pd.to_datetime(maturity).strftime("%b %Y")
                contract_labels[code] = f"{mat_label}"
            except:
                contract_labels[code] = code
    
    # Filters
    st.markdown("### 🎯 Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        min_carry = st.number_input(
            "Min Carry (bps/yr)",
            min_value=0,
            value=0,
            step=5,
            key="cal_min_carry"
        )
    
    with col2:
        min_fwd_rate = st.number_input(
            "Min Fwd Rate (bps)",
            min_value=0,
            value=0,
            step=5,
            key="cal_min_fwd"
        )
    
    with col3:
        min_period = st.number_input(
            "Min Period (days)",
            min_value=0,
            value=0,
            step=30,
            key="cal_min_period"
        )
    
    with col4:
        max_period = st.number_input(
            "Max Period (days)",
            min_value=0,
            value=0,
            step=30,
            help="0 = no limit",
            key="cal_max_period"
        )
    
    # Filter opportunities
    filtered_opps = filter_opportunities_by_criteria(
        fwd_matrix, carry_matrix, contracts_df,
        min_forward_rate=min_fwd_rate if min_fwd_rate > 0 else None,
        min_annualized_carry=min_carry if min_carry > 0 else None,
        min_maturity_days=min_period if min_period > 0 else None,
        max_maturity_days=max_period if max_period > 0 else None,
        as_of_date=as_of_date
    )
    
    # Display matrix (simplified version)
    st.markdown("### 📊 Forward Rate Matrix")
    st.caption("Rows = LONG (buy near) | Columns = SHORT (sell far) | Values = Implied Forward Rate (bps)")
    
    # Relabel matrix with dates
    display_matrix = fwd_matrix.copy()
    display_matrix.index = [contract_labels.get(c, c) for c in display_matrix.index]
    display_matrix.columns = [contract_labels.get(c, c) for c in display_matrix.columns]
    
    st.dataframe(
        display_matrix.style.format("{:.1f}").background_gradient(cmap='RdYlGn', axis=None),
        use_container_width=True
    )
    
    # Top opportunities
    st.markdown("### 🏆 Top Opportunities")
    
    if filtered_opps:
        for i, opp in enumerate(filtered_opps[:5]):
            from_label = contract_labels.get(opp['from_contract'], opp['from_contract'])
            to_label = contract_labels.get(opp['to_contract'], opp['to_contract'])
            
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{from_label}** → **{to_label}**")
            with col2:
                st.markdown(f"Fwd Rate: **{opp['forward_rate']:.1f} bps**")
            with col3:
                st.markdown(f"Carry: **{opp['annualized_carry']:.0f}**")
            with col4:
                st.markdown(f"{opp['period_days']} days")
            with col5:
                if st.button("Select", key=f"select_cal_{i}"):
                    st.session_state["selected_opportunity"] = opp
                    st.session_state["selected_strategy"] = "calendar_spread"
            
            st.markdown("---")
    else:
        st.info("No opportunities match your filter criteria.")
    
    # Trade builder if opportunity selected
    if (st.session_state.get("selected_strategy") == "calendar_spread" and 
        st.session_state.get("selected_opportunity")):
        _render_trade_builder(
            st.session_state["selected_opportunity"],
            "calendar_spread",
            contracts_df
        )


# =============================================================================
# SPOT CASH & CARRY TAB
# =============================================================================

def _render_spot_arb_tab(rate_data: dict):
    """Render the Spot Cash & Carry tab."""
    
    st.markdown("## 💰 Spot Cash & Carry Arbitrage")
    st.markdown("*Own stocks + Sell futures + Borrow via box spread*")
    
    futures_rates = rate_data['futures_rates']
    box_spreads = rate_data['box_spreads']
    sofr_rate = rate_data['sofr_rate']
    
    if futures_rates.empty or box_spreads.empty:
        st.warning("Insufficient data to display spot arbitrage opportunities.")
        return
    
    # Term structure chart data
    st.markdown("### 📈 Term Structure: Futures vs Box Spreads")
    
    # Merge data for comparison
    merged = futures_rates.merge(
        box_spreads[['Days_to_Expiry', 'Box_Rate_Pct', 'Expiry_Label']],
        on='Days_to_Expiry',
        how='inner',
        suffixes=('', '_box')
    )
    
    if not merged.empty:
        chart_data = merged[['Expiry_Label', 'Futures_Rate_Pct', 'Box_Rate_Pct']].copy()
        chart_data = chart_data.set_index('Expiry_Label')
        chart_data.columns = ['Equity Futures Rate (%)', 'Box Spread Rate (%)']
        
        st.line_chart(chart_data)
        
        # Calculate spreads
        merged['Spread_Bps'] = (merged['Futures_Rate'] - merged['Box_Rate_Pct'] / 100) * 10000
    
    # Opportunity table
    st.markdown("### 🏆 Arbitrage Opportunities by Expiry")
    
    if not merged.empty:
        display_df = merged[['Expiry_Label', 'Days_to_Expiry', 'Futures_Rate_Pct', 'Box_Rate_Pct']].copy()
        display_df['Spread (bps)'] = ((merged['Futures_Rate'] - merged['Box_Rate_Pct'] / 100) * 10000).round(1)
        display_df['Est P&L ($100M)'] = (display_df['Spread (bps)'] / 10000 * 100_000_000 * display_df['Days_to_Expiry'] / 360).round(0)
        display_df.columns = ['Expiry', 'Days', 'Futures %', 'Box %', 'Spread (bps)', 'Est P&L ($100M)']
        
        st.dataframe(
            display_df.style.format({
                'Futures %': '{:.2f}',
                'Box %': '{:.2f}',
                'Spread (bps)': '{:.1f}',
                'Est P&L ($100M)': '${:,.0f}'
            }),
            use_container_width=True
        )
        
        # Select opportunity
        st.markdown("### 🔧 Build Trade")
        
        expiry_options = merged['Expiry_Label'].tolist()
        selected_expiry = st.selectbox("Select Expiry:", expiry_options, key="spot_expiry")
        
        if selected_expiry:
            row = merged[merged['Expiry_Label'] == selected_expiry].iloc[0]
            
            opportunity = {
                'expiry_label': selected_expiry,
                'days': row['Days_to_Expiry'],
                'futures_rate': row['Futures_Rate'],
                'futures_rate_bps': row['Futures_Rate'] * 10000,
                'box_rate': row['Box_Rate_Pct'] / 100,
                'box_rate_bps': row['Box_Rate_Pct'] * 100,
                'spread_bps': (row['Futures_Rate'] - row['Box_Rate_Pct'] / 100) * 10000,
                'period_days': row['Days_to_Expiry'],
                'contract': row.get('Contract_Code', ''),
            }
            
            _render_trade_builder(opportunity, "spot_arb")


# =============================================================================
# FORWARD ARBITRAGE TAB
# =============================================================================

def _render_forward_arb_tab(rate_data: dict, opportunities: list, contracts_df: pd.DataFrame):
    """Render the Forward Arbitrage tab."""
    
    st.markdown("## 🔄 Forward Arbitrage")
    st.markdown("*Calendar futures spread + Calendar box spread - capture forward equity premium*")
    
    st.info("""
        **Strategy:** Combine a calendar futures spread with a calendar box spread.
        - **Long** near futures / **Short** far futures = Receive forward equity rate
        - **Short** near box / **Long** far box = Pay forward SOFR
        - **Net:** Capture the forward equity premium (~8-15 bps typically)
    """)
    
    sofr_rate = rate_data['sofr_rate']
    
    # Build opportunities from calendar spread data
    st.markdown("### 🏆 Forward Arbitrage Opportunities")
    
    if opportunities:
        # Build contract labels
        contract_labels = {}
        for _, row in contracts_df.iterrows():
            code = row.get('Contract_Code', '')
            maturity = row.get('Maturity')
            if pd.notna(maturity):
                try:
                    contract_labels[code] = pd.to_datetime(maturity).strftime("%b %Y")
                except:
                    contract_labels[code] = code
        
        # Display top forward arb opportunities
        fwd_arb_opps = []
        for opp in opportunities[:10]:
            # Forward arb spread = futures forward rate - box forward rate
            # Box forward rate is approximately SOFR
            fwd_futures_rate = opp['forward_rate'] / 10000  # Convert from bps
            fwd_box_rate = sofr_rate - 0.0003  # SOFR minus ~3 bps friction
            
            fwd_spread = (fwd_futures_rate - fwd_box_rate) * 10000
            
            fwd_arb_opps.append({
                'from_contract': opp['from_contract'],
                'to_contract': opp['to_contract'],
                'from_label': contract_labels.get(opp['from_contract'], opp['from_contract']),
                'to_label': contract_labels.get(opp['to_contract'], opp['to_contract']),
                'period_days': opp['period_days'],
                'fwd_futures_rate_bps': opp['forward_rate'],
                'fwd_box_rate_bps': fwd_box_rate * 10000,
                'spread_bps': fwd_spread,
            })
        
        # Display table
        display_data = []
        for opp in fwd_arb_opps:
            pnl = (opp['spread_bps'] / 10000) * 100_000_000 * (opp['period_days'] / 360)
            display_data.append({
                'Period': f"{opp['from_label']} → {opp['to_label']}",
                'Days': opp['period_days'],
                'Futures Fwd (bps)': opp['fwd_futures_rate_bps'],
                'Box Fwd (bps)': round(opp['fwd_box_rate_bps'], 1),
                'Net Spread (bps)': round(opp['spread_bps'], 1),
                'Est P&L ($100M)': round(pnl, 0),
            })
        
        display_df = pd.DataFrame(display_data)
        st.dataframe(
            display_df.style.format({
                'Futures Fwd (bps)': '{:.1f}',
                'Box Fwd (bps)': '{:.1f}',
                'Net Spread (bps)': '{:.1f}',
                'Est P&L ($100M)': '${:,.0f}'
            }),
            use_container_width=True
        )
        
        # Select and build
        st.markdown("### 🔧 Build Trade")
        
        period_options = [f"{o['from_label']} → {o['to_label']}" for o in fwd_arb_opps]
        selected_period = st.selectbox("Select Forward Period:", period_options, key="fwd_period")
        
        if selected_period:
            idx = period_options.index(selected_period)
            selected_opp = fwd_arb_opps[idx]
            
            # Add annualized_carry for trade builder compatibility
            selected_opp['annualized_carry'] = selected_opp['spread_bps']
            selected_opp['forward_rate'] = selected_opp['fwd_futures_rate_bps']
            
            _render_trade_builder(selected_opp, "forward_arb", contracts_df)
    else:
        st.warning("No forward arbitrage opportunities available with current data.")


# =============================================================================
# BLOTTER TAB
# =============================================================================

def _render_blotter_tab():
    """Render the trade blotter showing all pending/executed trades."""
    
    st.markdown("## 📋 Trade Blotter")
    
    blotter = st.session_state.get("trade_blotter", [])
    
    if not blotter:
        st.info("No trades in blotter. Select an opportunity and build a trade to add entries.")
        return
    
    # Convert to DataFrame
    blotter_df = pd.DataFrame(blotter)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Trades", len(blotter))
    
    with col2:
        total_notional = blotter_df['notional'].abs().sum()
        st.metric("Gross Notional", f"${total_notional:,.0f}")
    
    with col3:
        total_dv01 = blotter_df['dv01'].sum()
        st.metric("Total DV01", f"${total_dv01:,.0f}")
    
    with col4:
        strategies = blotter_df['strategy'].nunique()
        st.metric("Strategies", strategies)
    
    st.markdown("---")
    
    # Display blotter
    display_cols = ['trade_id', 'timestamp', 'strategy', 'direction', 'instrument', 'notional', 'dv01', 'status']
    available_cols = [c for c in display_cols if c in blotter_df.columns]
    
    st.dataframe(
        blotter_df[available_cols].style.format({
            'notional': '${:,.0f}',
            'dv01': '${:,.0f}',
        }),
        use_container_width=True
    )
    
    # Actions
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Blotter", type="secondary"):
            st.session_state["trade_blotter"] = []
            st.rerun()
    
    with col2:
        if st.button("📤 Export to CSV"):
            csv = blotter_df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "trade_blotter.csv",
                "text/csv",
                key="download_blotter"
            )


# =============================================================================
# MAIN PAGE RENDERER
# =============================================================================

def render_opportunities_page():
    """Main page renderer for Financing Opportunities."""
    
    _ensure_session_state()
    
    st.title("💹 Financing Opportunities")
    
    _show_demo_banner()
    
    # Load data
    contracts_df = get_cached_data('futures_prices')
    rate_data = get_combined_rate_data()
    
    # Calculate calendar spread opportunities (used across tabs)
    as_of_date = get_valuation_date()
    fwd_matrix = calculate_forward_rate_matrix(contracts_df, as_of_date=as_of_date)
    carry_matrix = calculate_carry_matrix(contracts_df, as_of_date=as_of_date)
    
    opportunities = filter_opportunities_by_criteria(
        fwd_matrix, carry_matrix, contracts_df,
        as_of_date=as_of_date
    )
    
    # Rate summary cards
    if not rate_data['futures_rates'].empty:
        avg_futures_rate = rate_data['futures_rates']['Futures_Rate_Pct'].mean()
        spread_bps = (avg_futures_rate - rate_data['sofr_rate_pct']) * 100
        _render_rate_cards(rate_data['sofr_rate_pct'], avg_futures_rate, spread_bps)
    
    st.markdown("---")
    
    # Tabs
    tab_summary, tab_calendar, tab_spot, tab_forward, tab_blotter = st.tabs([
        "📊 Summary",
        "📅 Calendar Spreads",
        "💰 Spot Cash & Carry",
        "🔄 Forward Arb",
        "📋 Blotter"
    ])
    
    with tab_summary:
        _render_summary_tab(rate_data, opportunities, contracts_df)
    
    with tab_calendar:
        _render_calendar_spreads_tab(contracts_df, opportunities)
    
    with tab_spot:
        _render_spot_arb_tab(rate_data)
    
    with tab_forward:
        _render_forward_arb_tab(rate_data, opportunities, contracts_df)
    
    with tab_blotter:
        _render_blotter_tab()


# =============================================================================
# PAGE ENTRY POINT
# =============================================================================

render_opportunities_page()
