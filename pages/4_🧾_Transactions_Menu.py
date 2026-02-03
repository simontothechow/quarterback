"""
Quarterback - Transactions Menu
===============================
Demo Transactions hub page:
- Trade Blotter (persistent in session until deleted)
- New Transaction (placeholder)
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.theme import apply_theme


def _ensure_trade_blotter():
    if "trade_blotter" not in st.session_state:
        st.session_state["trade_blotter"] = []


st.set_page_config(
    page_title="Transactions | Quarterback",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
_ensure_trade_blotter()


# Sidebar navigation
with st.sidebar:
    if st.button("← Back to Home", key="back_home", use_container_width=True):
        st.switch_page("app.py")

    st.markdown("---")
    st.markdown("### Navigation")

    if st.button("📊 Basket Detail", use_container_width=True):
        st.switch_page("pages/1_📊_Basket_Detail.py")

    if st.button("📅 Calendar View", use_container_width=True):
        st.switch_page("pages/2_📅_Calendar.py")

    if st.button("🧾 Transactions", use_container_width=True, disabled=True):
        pass


st.markdown("""
    <h1 style="display: flex; align-items: center; gap: 1rem;">
        <span>🧾</span>
        <span>Transactions</span>
    </h1>
""", unsafe_allow_html=True)


tab_blotter, tab_new = st.tabs(["Trade Blotter", "New Transaction"])

with tab_blotter:
    st.markdown("### Trade Blotter")

    blotter = st.session_state.get("trade_blotter", [])
    
    # Clear All Transactions button
    if blotter:
        col_clear, col_spacer = st.columns([2, 6])
        with col_clear:
            if st.session_state.get("confirm_clear_all", False):
                st.warning("Are you sure you want to delete ALL transactions?")
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
                if st.button("🗑️ Clear All Transactions", use_container_width=True):
                    st.session_state["confirm_clear_all"] = True
                    st.rerun()
        st.markdown("---")
    
    if not blotter:
        st.info("No trades yet. Submit or schedule a trade from the Transaction page to see it here.")
    else:
        # Header row
        header_cols = st.columns([2, 1, 1, 2, 2, 2, 1])
        headers = [
            "Ticker / Basket",
            "Side",
            "Shares",
            "Order Created",
            "Execution Date",
            "Est. Value / Route",
            "Delete",
        ]
        for col, label in zip(header_cols, headers):
            with col:
                st.markdown(
                    f"<div style='color:#808080; font-size:0.8rem; text-transform:uppercase; font-weight:600; padding:0.25rem 0;'>{label}</div>",
                    unsafe_allow_html=True,
                )
        st.markdown("<div style='border-bottom: 1px solid #333; margin: 0.25rem 0 0.75rem 0;'></div>", unsafe_allow_html=True)

        # Delete confirmation (inline)
        pending_delete_id = st.session_state.get("pending_delete_trade_id", None)
        if pending_delete_id:
            match = next((t for t in blotter if t.get("id") == pending_delete_id), None)
            if match:
                st.warning(
                    f"Are you sure you want to delete trade `{match.get('ticker','')}` "
                    f"({match.get('side','') } {match.get('shares','')} shares)?"
                )
                c1, c2, c3 = st.columns([1, 1, 6])
                with c1:
                    if st.button("Yes, delete", type="primary", use_container_width=True):
                        st.session_state["trade_blotter"] = [t for t in blotter if t.get("id") != pending_delete_id]
                        st.session_state["pending_delete_trade_id"] = None
                        st.rerun()
                with c2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state["pending_delete_trade_id"] = None
                        st.rerun()

            st.markdown("---")

        # Render trades (newest first)
        for trade in reversed(st.session_state["trade_blotter"]):
            cols = st.columns([2, 1, 1, 2, 2, 2, 1])
            with cols[0]:
                st.markdown(f"**{trade.get('ticker', 'N/A')}**")
                basket_id = trade.get("basket_id", "")
                if basket_id:
                    st.caption(f"Basket: {basket_id}")
            with cols[1]:
                st.markdown(trade.get("side", "N/A"))
            with cols[2]:
                st.markdown(f"{int(trade.get('shares', 0) or 0):,}")
            with cols[3]:
                st.markdown(trade.get("order_created_at", ""))
            with cols[4]:
                st.markdown(trade.get("execution_date", "CURRENT"))
            with cols[5]:
                st.markdown(f"${float(trade.get('estimated_value', 0) or 0):,.2f}")
                st.caption(trade.get("route", ""))
            with cols[6]:
                if st.button("✕", key=f"delete_{trade.get('id')}", use_container_width=True):
                    st.session_state["pending_delete_trade_id"] = trade.get("id")
                    st.rerun()

            st.markdown("<div style='margin: 0.5rem 0; border-bottom: 1px solid #333;'></div>", unsafe_allow_html=True)

with tab_new:
    st.markdown("### New Transaction")
    st.info("Coming next: create a new transaction directly from this page.")

