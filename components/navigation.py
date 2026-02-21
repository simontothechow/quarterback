"""
Quarterback Navigation Module
=============================
Centralized navigation and sidebar components for consistent UI across all pages.
"""

import streamlit as st
from datetime import datetime


def render_sidebar_header():
    """Render the Quarterback logo and branding in sidebar."""
    st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <span style="font-size: 3rem;">🏈</span>
            <h2 style="color: #ff8c00; margin: 0.5rem 0;">QUARTERBACK</h2>
            <p style="color: #808080; font-size: 0.85rem;">v1.0 Demo</p>
        </div>
    """, unsafe_allow_html=True)


def render_sidebar_data_status(positions_count: int, market_data_count: int, corp_actions_count: int):
    """Render data status section in sidebar."""
    st.markdown("---")
    st.markdown("### Data Status")
    st.markdown(f"""
        <div style="font-size: 0.85rem; color: #808080;">
            <div style="margin-bottom: 0.5rem;">
                <span style="color: #00d26a;">●</span> Positions: {positions_count} records
            </div>
            <div style="margin-bottom: 0.5rem;">
                <span style="color: #00d26a;">●</span> Market Data: {market_data_count} stocks
            </div>
            <div style="margin-bottom: 0.5rem;">
                <span style="color: #00d26a;">●</span> Corp Actions: {corp_actions_count} events
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_sidebar_footer():
    """Render footer in sidebar."""
    st.markdown("---")
    st.markdown("""
        <div style="color: #808080; font-size: 0.75rem; text-align: center;">
            © 2026 Quarterback Trading Systems<br>
            Demo Version
        </div>
    """, unsafe_allow_html=True)


def render_refresh_button():
    """Render refresh data button."""
    st.markdown("---")
    st.markdown("### Quick Actions")
    if st.button("🔄 Refresh Data", use_container_width=True, key="nav_refresh"):
        st.cache_data.clear()
        st.rerun()


def render_back_button(destination: str = "Home"):
    """Render a back button that returns to Home."""
    if st.button(f"← Back to {destination}", use_container_width=True, key="nav_back"):
        st.switch_page("app.py")


def render_full_sidebar(positions_count: int = 0, market_data_count: int = 0, corp_actions_count: int = 0):
    """
    Render the complete sidebar with all components.
    Use this for pages that need the full sidebar experience.
    """
    render_sidebar_header()
    render_refresh_button()
    render_sidebar_data_status(positions_count, market_data_count, corp_actions_count)
    render_sidebar_footer()


def render_minimal_sidebar():
    """
    Render a minimal sidebar with just branding and back button.
    Use this for transaction/detail pages.
    """
    render_sidebar_header()
    st.markdown("---")
    render_back_button()
    render_sidebar_footer()
