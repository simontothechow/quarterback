"""
Quarterback - Transactions Menu
===============================
Demo Transactions hub page:
- Trade Blotter (persistent in session until deleted)
- New Transaction (placeholder)

Supports two trade formats:
1. Legacy format: ticker, side, shares, estimated_value (from equity/futures trades)
2. Opportunities format: instrument, direction, notional, strategy (from arb trades)
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def _ensure_trade_blotter():
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


def _get_trade_id(trade: dict) -> str:
    """Get unique ID from either format."""
    return trade.get("id") or trade.get("trade_id") or str(id(trade))


def _get_trade_display(trade: dict) -> dict:
    """Normalize trade data for display, handling both formats."""
    
    # Check if this is an Opportunities-style trade (has 'strategy' and 'instrument')
    is_opportunities_trade = 'strategy' in trade and 'instrument' in trade
    
    if is_opportunities_trade:
        return {
            'ticker': trade.get('instrument', 'N/A'),
            'side': trade.get('direction', 'N/A'),
            'quantity': f"${abs(trade.get('notional', 0)):,.0f}",
            'quantity_label': 'Notional',
            'created': trade.get('timestamp', ''),
            'execution': trade.get('status', 'PENDING'),
            'value': f"DV01: ${trade.get('dv01', 0):,.0f}",
            'route': trade.get('strategy', ''),
            'id': _get_trade_id(trade),
            'is_arb': True,
        }
    else:
        # Legacy format
        return {
            'ticker': trade.get('ticker', 'N/A'),
            'side': trade.get('side', 'N/A'),
            'quantity': f"{int(trade.get('shares', 0) or 0):,}",
            'quantity_label': 'Shares',
            'created': trade.get('order_created_at', ''),
            'execution': trade.get('execution_date', 'CURRENT'),
            'value': f"${float(trade.get('estimated_value', 0) or 0):,.2f}",
            'route': trade.get('route', ''),
            'id': _get_trade_id(trade),
            'is_arb': False,
            'basket_id': trade.get('basket_id', ''),
        }


_ensure_trade_blotter()


st.markdown("""
    <h1 style="display: flex; align-items: center; gap: 1rem;">
        <span>🧾</span>
        <span>Transactions</span>
    </h1>
""", unsafe_allow_html=True)


tab_blotter, tab_arb, tab_new = st.tabs(["All Trades", "Arb Trades", "New Transaction"])

with tab_blotter:
    st.markdown("### Trade Blotter - All Trades")

    blotter = st.session_state.get("trade_blotter", [])
    
    # Clear All Transactions button
    if blotter:
        col_clear, col_count, col_spacer = st.columns([2, 2, 4])
        with col_clear:
            if st.session_state.get("confirm_clear_all", False):
                st.warning("Delete ALL transactions?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Yes, Clear All", type="primary", use_container_width=True):
                        st.session_state["trade_blotter"] = []
                        st.session_state["confirm_clear_all"] = False
                        st.balloons()
                        st.rerun()
                with c2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state["confirm_clear_all"] = False
                        st.rerun()
            else:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.session_state["confirm_clear_all"] = True
                    st.rerun()
        with col_count:
            st.metric("Total Trades", len(blotter))
        st.markdown("---")
    
    if not blotter:
        st.info("No trades yet. Submit a trade from Transactions, Quick Trades, or Opportunities pages.")
    else:
        # Header row
        header_cols = st.columns([2, 1, 1.5, 2, 1.5, 2, 0.5])
        headers = ["Instrument", "Side", "Size", "Created", "Status", "Value / Strategy", ""]
        for col, label in zip(header_cols, headers):
            with col:
                st.markdown(
                    f"<div style='color:#808080; font-size:0.75rem; text-transform:uppercase; font-weight:600;'>{label}</div>",
                    unsafe_allow_html=True,
                )
        st.markdown("<div style='border-bottom: 1px solid #333; margin: 0.25rem 0 0.5rem 0;'></div>", unsafe_allow_html=True)

        # Delete confirmation
        pending_delete_id = st.session_state.get("pending_delete_trade_id", None)
        if pending_delete_id:
            match = next((t for t in blotter if _get_trade_id(t) == pending_delete_id), None)
            if match:
                display = _get_trade_display(match)
                st.warning(f"Delete trade `{display['ticker']}` ({display['side']})?")
                c1, c2, c3 = st.columns([1, 1, 6])
                with c1:
                    if st.button("Yes", type="primary", use_container_width=True):
                        st.session_state["trade_blotter"] = [
                            t for t in blotter if _get_trade_id(t) != pending_delete_id
                        ]
                        st.session_state["pending_delete_trade_id"] = None
                        st.rerun()
                with c2:
                    if st.button("No", use_container_width=True):
                        st.session_state["pending_delete_trade_id"] = None
                        st.rerun()
                st.markdown("---")

        # Render trades (newest first)
        for trade in reversed(st.session_state["trade_blotter"]):
            display = _get_trade_display(trade)
            cols = st.columns([2, 1, 1.5, 2, 1.5, 2, 0.5])
            
            with cols[0]:
                st.markdown(f"**{display['ticker']}**")
                if display.get('basket_id'):
                    st.caption(f"Basket: {display['basket_id']}")
            with cols[1]:
                side_color = "#00b894" if display['side'] == "LONG" else "#d63031" if display['side'] in ["SHORT", "SELL"] else "#636e72"
                st.markdown(f"<span style='color:{side_color};font-weight:600;'>{display['side']}</span>", unsafe_allow_html=True)
            with cols[2]:
                st.markdown(display['quantity'])
            with cols[3]:
                st.markdown(display['created'][:16] if display['created'] else "-")
            with cols[4]:
                status = display['execution']
                status_color = "#fdcb6e" if status == "PENDING" else "#00b894" if status == "FILLED" else "#636e72"
                st.markdown(f"<span style='color:{status_color};'>{status}</span>", unsafe_allow_html=True)
            with cols[5]:
                st.markdown(display['value'])
                if display['route']:
                    st.caption(display['route'])
            with cols[6]:
                if st.button("✕", key=f"del_{display['id']}", use_container_width=True):
                    st.session_state["pending_delete_trade_id"] = display['id']
                    st.rerun()

            st.markdown("<div style='margin: 0.3rem 0; border-bottom: 1px solid #222;'></div>", unsafe_allow_html=True)


with tab_arb:
    st.markdown("### Arbitrage Trades")
    st.caption("Trades from the Opportunities page (Calendar Spreads, Spot Arb, Forward Arb)")
    
    blotter = st.session_state.get("trade_blotter", [])
    arb_trades = [t for t in blotter if 'strategy' in t and 'instrument' in t]
    
    if not arb_trades:
        st.info("No arbitrage trades yet. Visit the **Opportunities** page to find and execute arb strategies.")
    else:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Arb Trades", len(arb_trades))
        with col2:
            total_notional = sum(abs(t.get('notional', 0)) for t in arb_trades)
            st.metric("Gross Notional", f"${total_notional:,.0f}")
        with col3:
            total_dv01 = sum(t.get('dv01', 0) for t in arb_trades)
            st.metric("Total DV01", f"${total_dv01:,.0f}")
        with col4:
            strategies = set(t.get('strategy', '') for t in arb_trades)
            st.metric("Strategies", len(strategies))
        
        st.markdown("---")
        
        # Group by strategy
        by_strategy = {}
        for trade in arb_trades:
            strat = trade.get('strategy', 'Unknown')
            if strat not in by_strategy:
                by_strategy[strat] = []
            by_strategy[strat].append(trade)
        
        for strategy, trades in by_strategy.items():
            with st.expander(f"**{strategy}** ({len(trades)} legs)", expanded=True):
                for trade in trades:
                    col1, col2, col3, col4 = st.columns([3, 1, 2, 2])
                    with col1:
                        st.markdown(f"**{trade.get('instrument', 'N/A')}**")
                    with col2:
                        direction = trade.get('direction', '')
                        color = "#00b894" if direction == "LONG" else "#d63031"
                        st.markdown(f"<span style='color:{color};font-weight:bold;'>{direction}</span>", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"${abs(trade.get('notional', 0)):,.0f}")
                    with col4:
                        st.markdown(f"DV01: ${trade.get('dv01', 0):,.0f}")


with tab_new:
    st.markdown("### New Transaction")
    st.info("💡 **Tip:** Use the **Opportunities** page to find financing arbitrage trades, or **Quick Trades** for single-leg transactions.")

