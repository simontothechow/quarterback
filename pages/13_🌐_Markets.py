"""
Quarterback - Markets Page
==========================
Calendar spread opportunity scanner for S&P 500 AIR futures.

Features:
- Filter by minimum carry, forward rate, and maturity period
- Heatmap visualization of implied forward rates
- Heatmap visualization of annualized carry
- Trade execution for calendar spreads
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_loader import get_cached_data
from modules.calculations import (
    calculate_forward_rate_matrix,
    calculate_carry_matrix,
    filter_opportunities_by_criteria,
    calculate_futures_contracts_from_notional,
    get_valuation_date,
    DEMO_MODE,
    SPX_FUTURES_MULTIPLIER,
)
from components.theme import COLORS


def _ensure_trade_blotter():
    """Initialize the demo trade blotter in session state."""
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


def _build_combined_matrix(fwd_matrix: pd.DataFrame, carry_matrix: pd.DataFrame) -> tuple:
    """
    Combine forward rate and carry matrices into one display matrix.
    Returns (combined_display_df, sum_matrix_for_coloring)
    """
    if fwd_matrix.empty or carry_matrix.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    combined = pd.DataFrame(index=fwd_matrix.index, columns=fwd_matrix.columns, dtype=object)
    sum_matrix = pd.DataFrame(index=fwd_matrix.index, columns=fwd_matrix.columns, dtype=float)
    
    for row in fwd_matrix.index:
        for col in fwd_matrix.columns:
            fwd_val = fwd_matrix.loc[row, col]
            carry_val = carry_matrix.loc[row, col]
            
            if pd.isna(fwd_val) or pd.isna(carry_val):
                combined.loc[row, col] = "-"
                sum_matrix.loc[row, col] = float('nan')
            else:
                combined.loc[row, col] = f"{fwd_val:.0f} | {carry_val:.0f}"
                sum_matrix.loc[row, col] = fwd_val + carry_val
    
    return combined, sum_matrix


def _style_combined_heatmap(display_df: pd.DataFrame, sum_df: pd.DataFrame, 
                            fwd_df: pd.DataFrame = None, carry_df: pd.DataFrame = None,
                            filter_mask: pd.DataFrame = None):
    """Apply color gradient styling based on sum values, with optional filter highlighting."""
    if display_df.empty:
        return display_df.style
    
    numeric_vals = sum_df.values.flatten()
    numeric_vals = [v for v in numeric_vals if pd.notna(v)]
    
    if not numeric_vals:
        return display_df.style
    
    min_val = min(numeric_vals)
    max_val = max(numeric_vals)
    
    has_filter = filter_mask is not None and filter_mask.any().any()
    
    def color_cell(row_idx, col_idx):
        sum_val = sum_df.iloc[row_idx, col_idx]
        
        if pd.isna(sum_val):
            return 'background-color: #1a1a1a; color: #404040; border: 1px solid #333;'
        
        # Check if this cell passes the filter
        passes_filter = True
        if has_filter:
            row_label = sum_df.index[row_idx]
            col_label = sum_df.columns[col_idx]
            passes_filter = filter_mask.loc[row_label, col_label] if (row_label in filter_mask.index and col_label in filter_mask.columns) else False
        
        if max_val == min_val:
            norm = 0.5
        else:
            norm = (sum_val - min_val) / (max_val - min_val)
        
        if has_filter and not passes_filter:
            # Blue gradient for cells not matching filter
            # Low values = dark blue, High values = very light blue (almost white)
            r = int(25 + norm * 200)
            g = int(35 + norm * 200)
            b = int(60 + norm * 180)
            # Text color: dark for light backgrounds, light for dark backgrounds
            text_color = '#303040' if norm > 0.6 else '#90a0b0'
            return f'background-color: rgb({r},{g},{b}); color: {text_color}; font-weight: 400; border: 1px solid #3a4a5a;'
        
        if has_filter:
            # Purple/magenta gradient for cells matching filter criteria
            # Low values = darker purple, High values = bright magenta/pink
            r = int(80 + norm * 175)
            g = int(30 + norm * 70)
            b = int(120 + norm * 100)
            return f'background-color: rgb({r},{g},{b}); color: white; font-weight: 600; border: 2px solid #ff8c00;'
        else:
            # Green-to-red gradient when no filter is active
            if norm < 0.5:
                r = int(50 + norm * 2 * 50)
                g = int(50 + norm * 2 * 150)
                b = int(80 + norm * 2 * 20)
            else:
                r = int(100 + (norm - 0.5) * 2 * 155)
                g = int(200 - (norm - 0.5) * 2 * 100)
                b = int(100 - (norm - 0.5) * 2 * 50)
            
            return f'background-color: rgb({r},{g},{b}); color: white; font-weight: 500; border: 1px solid #222;'
    
    def apply_colors(df):
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        for i, row in enumerate(df.index):
            for j, col in enumerate(df.columns):
                styles.loc[row, col] = color_cell(i, j)
        return styles
    
    return display_df.style.apply(lambda _: apply_colors(display_df), axis=None)


def _build_filter_mask(fwd_matrix: pd.DataFrame, carry_matrix: pd.DataFrame,
                       contracts_df: pd.DataFrame, contract_to_label: dict,
                       min_fwd_rate: float = None, min_carry: float = None,
                       min_period: int = None, max_period: int = None,
                       as_of_date = None) -> pd.DataFrame:
    """Build a boolean mask indicating which cells pass the filter criteria."""
    if fwd_matrix.empty:
        return pd.DataFrame()
    
    # Build contract days lookup (contract code -> days to maturity)
    contract_days = {}
    for _, row in contracts_df.iterrows():
        code = row['Contract_Code']
        maturity = row.get('Maturity')
        if pd.notna(maturity):
            mat_date = pd.to_datetime(maturity)
            if as_of_date:
                contract_days[code] = (mat_date.date() - as_of_date).days
            else:
                contract_days[code] = row.get('Days_to_maturity', 0)
    
    # Create mask with relabeled index/columns to match the display matrix
    labels = [contract_to_label.get(c, c) for c in fwd_matrix.index]
    mask = pd.DataFrame(False, index=labels, columns=labels)
    
    for from_code in fwd_matrix.index:
        for to_code in fwd_matrix.columns:
            from_label = contract_to_label.get(from_code, from_code)
            to_label = contract_to_label.get(to_code, to_code)
            
            fwd_val = fwd_matrix.loc[from_code, to_code]
            carry_val = carry_matrix.loc[from_code, to_code]
            
            # Invalid cells don't pass
            if pd.isna(fwd_val) or pd.isna(carry_val):
                continue
            
            # Calculate period between contracts
            from_days = contract_days.get(from_code, 0)
            to_days = contract_days.get(to_code, 0)
            period = to_days - from_days
            
            # Skip invalid periods (must be positive - TO must be after FROM)
            if period <= 0:
                continue
            
            # Apply all filters - cell must pass ALL criteria
            if min_fwd_rate and fwd_val < min_fwd_rate:
                continue
            
            if min_carry and carry_val < min_carry:
                continue
            
            if min_period and period < min_period:
                continue
            
            if max_period and period > max_period:
                continue
            
            # Passed all filters
            mask.loc[from_label, to_label] = True
    
    return mask


def _relabel_matrix(matrix: pd.DataFrame, label_map: dict) -> pd.DataFrame:
    """Relabel matrix index and columns using the label map."""
    if matrix.empty:
        return matrix
    
    new_index = [label_map.get(idx, idx) for idx in matrix.index]
    new_columns = [label_map.get(col, col) for col in matrix.columns]
    
    relabeled = matrix.copy()
    relabeled.index = new_index
    relabeled.columns = new_columns
    
    return relabeled


def render_markets_page():
    """Render the Markets page."""
    
    _ensure_trade_blotter()
    
    val_date = get_valuation_date()
    
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.switch_page("app.py")
    with col3:
        if st.button("🧾 Blotter", use_container_width=True):
            st.switch_page("pages/4_🧾_Transactions_Menu.py")
    
    st.markdown("""
        <h1 style="display: flex; align-items: center; gap: 1rem;">
            <span>🌐</span>
            <span>Markets - Calendar Spread Scanner</span>
        </h1>
    """, unsafe_allow_html=True)
    
    mode_label = "DEMO MODE" if DEMO_MODE else "LIVE"
    mode_color = "#ff8c00" if DEMO_MODE else "#00d26a"
    st.markdown(f"""
        <p style="color: #808080; margin-bottom: 1rem;">
            Scan for calendar spread opportunities across S&P 500 AIR futures contracts.
            <span style="background-color: {mode_color}; color: #000; padding: 2px 8px; border-radius: 4px; 
                         font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">{mode_label}</span>
            <span style="color: #606060; margin-left: 0.5rem;">Valuation Date: {val_date.strftime('%b %d, %Y')}</span>
        </p>
    """, unsafe_allow_html=True)
    
    futures_df = get_cached_data('futures_prices')
    
    if futures_df.empty:
        st.error("No futures price data available. Please ensure data/futures_prices.xlsx exists.")
        st.stop()
    
    # Build mapping from contract code to maturity date for display
    contract_to_date = {}
    contract_to_label = {}
    for _, row in futures_df.iterrows():
        code = row['Contract_Code']
        maturity = row.get('Maturity')
        if pd.notna(maturity):
            mat_date = pd.to_datetime(maturity)
            contract_to_date[code] = mat_date.strftime('%b %d, %Y')
            contract_to_label[code] = mat_date.strftime('%b %Y')
        else:
            contract_to_date[code] = code
            contract_to_label[code] = code
    
    st.markdown("### Filter Criteria")
    
    # Handle clear filters flag (set before widgets are instantiated)
    if st.session_state.get('_clear_filters', False):
        st.session_state['_clear_filters'] = False
        default_carry = 0.0
        default_fwd = 0.0
        default_min_period = 0
        default_max_period = 0
    else:
        default_carry = st.session_state.get('filter_min_carry', 0.0)
        default_fwd = st.session_state.get('filter_min_fwd', 0.0)
        default_min_period = st.session_state.get('filter_min_period', 0)
        default_max_period = st.session_state.get('filter_max_period', 0)
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 0.6])
    
    with col1:
        min_carry = st.number_input(
            "Min Annualized Carry (bps)",
            min_value=0.0,
            max_value=500.0,
            value=default_carry,
            step=5.0,
            key="filter_min_carry",
            help="Minimum annualized carry in basis points per year"
        )
    
    with col2:
        min_fwd_rate = st.number_input(
            "Min Implied Fwd Rate (bps)",
            min_value=0.0,
            max_value=500.0,
            value=default_fwd,
            step=5.0,
            key="filter_min_fwd",
            help="Minimum implied forward rate in basis points"
        )
    
    with col3:
        min_maturity = st.number_input(
            "Min Period (days)",
            min_value=0,
            max_value=365,
            value=default_min_period,
            step=30,
            key="filter_min_period",
            help="Minimum days for the forward period"
        )
    
    with col4:
        max_maturity = st.number_input(
            "Max Period (days)",
            min_value=0,
            value=default_max_period,
            step=30,
            key="filter_max_period",
            help="Maximum days for the forward period (0 = no limit)"
        )
    
    with col5:
        st.markdown("<div style='height: 1.6rem;'></div>", unsafe_allow_html=True)
        if st.button("Clear Filters", use_container_width=True):
            st.session_state['_clear_filters'] = True
            st.rerun()
    
    if max_maturity == 0:
        max_maturity = None
    
    # Check if any filters are active
    filters_active = (min_carry > 0 or min_fwd_rate > 0 or min_maturity > 0 or 
                      (max_maturity is not None and max_maturity > 0))
    
    st.markdown("---")
    
    fwd_matrix = calculate_forward_rate_matrix(
        futures_df,
        price_column='last_price',
        days_column='Days_to_maturity',
        contract_column='Contract_Code',
        maturity_column='Maturity',
        as_of_date=val_date
    )
    
    carry_matrix = calculate_carry_matrix(
        futures_df,
        price_column='last_price',
        days_column='Days_to_maturity',
        contract_column='Contract_Code',
        maturity_column='Maturity',
        as_of_date=val_date
    )
    
    opportunities = filter_opportunities_by_criteria(
        forward_rate_matrix=fwd_matrix,
        carry_matrix=carry_matrix,
        contracts_df=futures_df,
        min_forward_rate=min_fwd_rate if min_fwd_rate > 0 else None,
        min_annualized_carry=min_carry if min_carry > 0 else None,
        min_maturity_days=min_maturity if min_maturity > 0 else None,
        max_maturity_days=max_maturity,
        as_of_date=val_date
    )
    
    st.markdown("### Forward Rate & Carry Matrix")
    st.markdown("""
        <p style="color: #808080; font-size: 0.85rem; margin-bottom: 0.5rem;">
            Each cell shows: <strong>Implied Forward Rate (bps) | Annualized Carry (bps/yr)</strong><br>
            <span style="color: #4ade80;">Green = lower combined value</span> | 
            <span style="color: #f87171;">Red = higher combined value (better opportunity)</span>
        </p>
    """, unsafe_allow_html=True)
    
    if not fwd_matrix.empty and not carry_matrix.empty:
        combined_display, sum_matrix = _build_combined_matrix(fwd_matrix, carry_matrix)
        combined_display = _relabel_matrix(combined_display, contract_to_label)
        sum_matrix_relabeled = _relabel_matrix(sum_matrix, contract_to_label)
        
        # Build filter mask if filters are active
        filter_mask = None
        if filters_active:
            filter_mask = _build_filter_mask(
                fwd_matrix, carry_matrix, futures_df, contract_to_label,
                min_fwd_rate=min_fwd_rate if min_fwd_rate > 0 else None,
                min_carry=min_carry if min_carry > 0 else None,
                min_period=min_maturity if min_maturity > 0 else None,
                max_period=max_maturity,
                as_of_date=val_date
            )
        
        styled_combined = _style_combined_heatmap(
            combined_display, sum_matrix_relabeled, 
            fwd_matrix, carry_matrix, filter_mask
        )
        
        # Add axis label for Short Contract (horizontal)
        filter_indicator = ""
        if filters_active:
            filter_indicator = '<span style="background-color: #ff8c00; color: #000; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; margin-left: 1rem;">FILTERED</span>'
        
        st.markdown(f"""
            <div style="text-align: center; color: #ff4444; font-weight: 600; font-size: 0.9rem; 
                        margin-bottom: 0.25rem; letter-spacing: 0.5px;">
                SHORT CONTRACT (Sell) → {filter_indicator}
            </div>
        """, unsafe_allow_html=True)
        
        # Create layout with vertical label on left
        label_col, matrix_col = st.columns([0.03, 0.97])
        
        with label_col:
            st.markdown("""
                <div style="writing-mode: vertical-rl; text-orientation: mixed; transform: rotate(180deg);
                            color: #00d26a; font-weight: 600; font-size: 0.9rem; 
                            height: 300px; display: flex; align-items: center; justify-content: center;
                            letter-spacing: 0.5px;">
                    LONG CONTRACT (Buy) ↓
                </div>
            """, unsafe_allow_html=True)
        
        with matrix_col:
            st.dataframe(styled_combined, use_container_width=True, height=350)
    else:
        st.info("No matrix data available.")
    
    st.markdown("---")
    
    st.markdown("### Top Opportunities")
    
    if opportunities:
        st.markdown(f"""
            <p style="color: #808080; font-size: 0.85rem; margin-bottom: 1rem;">
                Found <strong style="color: #ff8c00;">{len(opportunities)}</strong> opportunities matching your criteria.
                Click a row to select it for trading.
            </p>
        """, unsafe_allow_html=True)
        
        opp_df = pd.DataFrame(opportunities)
        opp_df = opp_df.rename(columns={
            'from_contract': 'FROM (Buy)',
            'to_contract': 'TO (Sell)',
            'forward_rate': 'Fwd Rate (bps)',
            'annualized_carry': 'Ann. Carry (bps/yr)',
            'period_days': 'Period (days)',
            'from_days': 'Days to FROM',
            'to_days': 'Days to TO',
        })
        
        if 'selected_opportunity' not in st.session_state:
            st.session_state['selected_opportunity'] = None
        
        for i, opp in enumerate(opportunities[:10]):
            is_selected = st.session_state.get('selected_opportunity') == i
            border_color = "#ff8c00" if is_selected else "#333"
            bg_color = "#2a2a1a" if is_selected else "#1a1a1a"
            
            from_date = contract_to_date.get(opp['from_contract'], opp['from_contract'])
            to_date = contract_to_date.get(opp['to_contract'], opp['to_contract'])
            
            col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 1.5, 1.5, 1.5, 1])
            
            with col1:
                st.markdown(f"""
                    <div style="background-color: {bg_color}; border: 1px solid {border_color}; 
                                border-radius: 4px; padding: 0.5rem; text-align: center;">
                        <div style="color: #00d26a; font-weight: 600; font-size: 0.8rem;">BUY</div>
                        <div style="color: #fff; font-size: 1.1rem; font-weight: 600;">{from_date}</div>
                        <div style="color: #606060; font-size: 0.75rem;">{opp['from_contract']}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                    <div style="background-color: {bg_color}; border: 1px solid {border_color}; 
                                border-radius: 4px; padding: 0.5rem; text-align: center;">
                        <div style="color: #ff4444; font-weight: 600; font-size: 0.8rem;">SELL</div>
                        <div style="color: #fff; font-size: 1.1rem; font-weight: 600;">{to_date}</div>
                        <div style="color: #606060; font-size: 0.75rem;">{opp['to_contract']}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.metric("Fwd Rate", f"{opp['forward_rate']:.1f} bps")
            
            with col4:
                st.metric("Carry", f"{opp['annualized_carry']:.1f} bps/yr")
            
            with col5:
                st.metric("Period", f"{opp['period_days']} days")
            
            with col6:
                if st.button("Select", key=f"select_opp_{i}", use_container_width=True):
                    st.session_state['selected_opportunity'] = i
                    st.session_state['selected_from'] = opp['from_contract']
                    st.session_state['selected_to'] = opp['to_contract']
                    st.rerun()
            
            st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        
        if len(opportunities) > 10:
            st.caption(f"Showing top 10 of {len(opportunities)} opportunities")
    
    else:
        st.info("No opportunities found matching your criteria. Try adjusting the filters.")
    
    st.markdown("---")
    
    st.markdown("### Execute Calendar Spread")
    
    selected_idx = st.session_state.get('selected_opportunity')
    
    if selected_idx is not None and selected_idx < len(opportunities):
        selected = opportunities[selected_idx]
        from_contract = selected['from_contract']
        to_contract = selected['to_contract']
        
        from_row = futures_df[futures_df['Contract_Code'] == from_contract].iloc[0]
        to_row = futures_df[futures_df['Contract_Code'] == to_contract].iloc[0]
        
        from_price = from_row['last_price']
        to_price = to_row['last_price']
        
        from_date = contract_to_date.get(from_contract, from_contract)
        to_date = contract_to_date.get(to_contract, to_contract)
        
        st.markdown(f"""
            <div style="background-color: #1a1a1a; border: 2px solid #ff8c00; border-radius: 8px; 
                        padding: 1.5rem; margin-bottom: 1rem;">
                <div style="color: #ff8c00; font-size: 1.2rem; font-weight: 700; margin-bottom: 1rem;">
                    Selected: {from_date} → {to_date}
                    <span style="color: #606060; font-size: 0.85rem; font-weight: 400; margin-left: 0.5rem;">
                        ({from_contract} → {to_contract})
                    </span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
                    <div>
                        <div style="color: #808080; font-size: 0.8rem;">BUY LEG</div>
                        <div style="color: #00d26a; font-size: 1.2rem;">{from_date}</div>
                        <div style="color: #00d26a; font-size: 0.9rem;">{from_contract} @ {from_price:.1f} bps</div>
                    </div>
                    <div>
                        <div style="color: #808080; font-size: 0.8rem;">SELL LEG</div>
                        <div style="color: #ff4444; font-size: 1.2rem;">{to_date}</div>
                        <div style="color: #ff4444; font-size: 0.9rem;">{to_contract} @ {to_price:.1f} bps</div>
                    </div>
                    <div>
                        <div style="color: #808080; font-size: 0.8rem;">IMPLIED FWD RATE</div>
                        <div style="color: #fff; font-size: 1.2rem;">{selected['forward_rate']:.1f} bps</div>
                    </div>
                    <div>
                        <div style="color: #808080; font-size: 0.8rem;">ANNUALIZED CARRY</div>
                        <div style="color: #fff; font-size: 1.2rem;">{selected['annualized_carry']:.1f} bps/yr</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            notional = st.number_input(
                "Notional ($)",
                min_value=0.0,
                value=st.session_state.get('spread_notional', 100_000_000.0),
                step=10_000_000.0,
                format="%.0f",
                key="spread_notional_input"
            )
            st.session_state['spread_notional'] = notional
        
        with col2:
            futures_price = 6000.0
            contracts = calculate_futures_contracts_from_notional(notional, futures_price)
            st.metric("Contracts (each leg)", f"{contracts:,}")
        
        with col3:
            trade_date = st.date_input(
                "Trade Date",
                value=val_date,
                key="spread_trade_date"
            )
        
        actual_notional = contracts * futures_price * SPX_FUTURES_MULTIPLIER
        
        st.markdown(f"""
            <div style="background-color: #252525; border: 1px solid #333; border-radius: 6px; 
                        padding: 1rem; margin: 1rem 0;">
                <div style="color: #808080; font-size: 0.85rem; margin-bottom: 0.5rem;">TRADE PREVIEW</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div style="background-color: #1a3a1a; border: 1px solid #00d26a; border-radius: 4px; padding: 0.75rem;">
                        <span style="color: #00d26a; font-weight: 600;">BUY</span>
                        <span style="color: #fff; margin-left: 0.5rem;">{contracts:,} × {from_date}</span>
                        <span style="color: #606060; margin-left: 0.25rem; font-size: 0.85rem;">({from_contract})</span>
                        <span style="color: #808080; margin-left: 0.5rem;">@ {from_price:.1f} bps</span>
                    </div>
                    <div style="background-color: #3a1a1a; border: 1px solid #ff4444; border-radius: 4px; padding: 0.75rem;">
                        <span style="color: #ff4444; font-weight: 600;">SELL</span>
                        <span style="color: #fff; margin-left: 0.5rem;">{contracts:,} × {to_date}</span>
                        <span style="color: #606060; margin-left: 0.25rem; font-size: 0.85rem;">({to_contract})</span>
                        <span style="color: #808080; margin-left: 0.5rem;">@ {to_price:.1f} bps</span>
                    </div>
                </div>
                <div style="color: #606060; font-size: 0.8rem; margin-top: 0.75rem;">
                    Notional per leg: ${actual_notional:,.0f} | Period: {selected['period_days']} days
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2, 2, 4])
        
        with col1:
            if st.button("🚀 Execute Spread", use_container_width=True, type="primary"):
                if contracts <= 0:
                    st.error("Please enter a valid notional amount.")
                else:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    spread_id = f"SPREAD-{uuid.uuid4().hex[:6].upper()}"
                    
                    st.session_state["trade_blotter"].append({
                        "id": uuid.uuid4().hex,
                        "trade_type": "CALENDAR_SPREAD",
                        "ticker": f"{from_date} ({from_contract})",
                        "instrument": "S&P 500 AIR Future",
                        "side": "BUY",
                        "contracts": int(contracts),
                        "shares": int(contracts),
                        "price": float(from_price),
                        "notional": float(actual_notional),
                        "estimated_value": float(actual_notional),
                        "basket_id": spread_id,
                        "counterparty": "CME Globex",
                        "trade_date": trade_date.strftime("%Y-%m-%d"),
                        "order_created_at": now_str,
                        "execution_date": trade_date.strftime("%Y-%m-%d"),
                        "status": "SUBMITTED",
                        "route": "CME Globex",
                        "spread_leg": "NEAR",
                    })
                    
                    st.session_state["trade_blotter"].append({
                        "id": uuid.uuid4().hex,
                        "trade_type": "CALENDAR_SPREAD",
                        "ticker": f"{to_date} ({to_contract})",
                        "instrument": "S&P 500 AIR Future",
                        "side": "SELL",
                        "contracts": int(-contracts),
                        "shares": int(-contracts),
                        "price": float(to_price),
                        "notional": float(-actual_notional),
                        "estimated_value": float(actual_notional),
                        "basket_id": spread_id,
                        "counterparty": "CME Globex",
                        "trade_date": trade_date.strftime("%Y-%m-%d"),
                        "order_created_at": now_str,
                        "execution_date": trade_date.strftime("%Y-%m-%d"),
                        "status": "SUBMITTED",
                        "route": "CME Globex",
                        "spread_leg": "FAR",
                    })
                    
                    st.success(f"Calendar spread submitted! {spread_id}: BUY {from_date} / SELL {to_date}")
                    st.balloons()
        
        with col2:
            if st.button("❌ Clear Selection", use_container_width=True):
                st.session_state['selected_opportunity'] = None
                st.rerun()
    
    else:
        st.info("👆 Select an opportunity from the list above to configure a trade.")
    
    st.markdown("---")
    st.markdown("### Contract Reference")
    
    with st.expander("View All Contracts"):
        display_df = futures_df.copy()
        if 'Maturity' in display_df.columns:
            display_df['Maturity'] = pd.to_datetime(display_df['Maturity']).dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            display_df,
            column_config={
                "Contract_Code": "Contract",
                "Days_to_maturity": st.column_config.NumberColumn("Days to Maturity", format="%d"),
                "last_price": st.column_config.NumberColumn("Price (bps)", format="%.2f"),
                "Maturity": "Maturity Date",
            },
            use_container_width=True,
            hide_index=True
        )


render_markets_page()
