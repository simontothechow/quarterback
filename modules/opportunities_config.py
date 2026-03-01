"""
Opportunities Section Configuration
====================================
Centralized configuration for the Financing Opportunities scanner.

This file contains all configurable parameters that may need adjustment
for demo presentations or when transitioning to live market data.

To change the SOFR rate: Simply update SOFR_RATE below.
"""

from datetime import date

# =============================================================================
# REFERENCE RATES
# =============================================================================
# Current SOFR rate (as of Feb 2026 demo)
# This is the risk-free benchmark for box spread pricing
SOFR_RATE = 0.0367  # 3.67% annualized

# Historical average equity financing premium over SOFR
EQUITY_PREMIUM_AVG_BPS = 25  # ~25 bps typical spread


# =============================================================================
# TENOR BUCKETS
# =============================================================================
# Standard periods for grouping opportunities
TENOR_BUCKETS = [
    {"name": "1-3 Month", "min_days": 0, "max_days": 90, "key": "1-3M"},
    {"name": "3-6 Month", "min_days": 91, "max_days": 180, "key": "3-6M"},
    {"name": "6-12 Month", "min_days": 181, "max_days": 365, "key": "6-12M"},
    {"name": "12M+", "min_days": 366, "max_days": 9999, "key": "12M+"},
]


# =============================================================================
# MOCK DATA GENERATION PARAMETERS
# =============================================================================
# Box spread discount from SOFR (reflects market friction/bid-ask)
# Box spreads typically trade 2-5 bps below theoretical SOFR
BOX_SPREAD_DISCOUNT_MIN_BPS = 2
BOX_SPREAD_DISCOUNT_MAX_BPS = 5

# Futures premium over SOFR (reflects equity balance sheet premium)
# Futures typically imply rates 20-40 bps above SOFR
FUTURES_PREMIUM_MIN_BPS = 20
FUTURES_PREMIUM_MAX_BPS = 40

# Historical data generation
HISTORICAL_DAYS = 90  # Days of synthetic history to generate
HISTORICAL_VOLATILITY_BPS = 5  # Daily volatility in the spread (bps)


# =============================================================================
# DISPLAY FORMATTING
# =============================================================================
# Default notional for P&L estimates
DEFAULT_NOTIONAL = 100_000_000  # $100M

# Currency formatting
CURRENCY_PRECISION = 0  # Decimal places for currency display


# =============================================================================
# STRATEGY CONFIGURATIONS
# =============================================================================
STRATEGIES = {
    "spot_arb": {
        "name": "Spot Cash & Carry",
        "description": "Hold stocks + Sell futures + Borrow via box",
        "legs": 3,
        "complexity": "Medium",
        "capital_required": "100%",
        "icon": "💰",
    },
    "calendar_spread": {
        "name": "Calendar Spread",
        "description": "Long near / Short far futures",
        "legs": 2,
        "complexity": "Low",
        "capital_required": "~5%",
        "icon": "📅",
    },
    "forward_arb": {
        "name": "Forward Arbitrage",
        "description": "Calendar futures + Calendar box",
        "legs": 4,
        "complexity": "High",
        "capital_required": "~10%",
        "icon": "🔄",
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_tenor_bucket(days: int) -> dict:
    """Get the tenor bucket for a given number of days."""
    for bucket in TENOR_BUCKETS:
        if bucket["min_days"] <= days <= bucket["max_days"]:
            return bucket
    return TENOR_BUCKETS[-1]  # Default to longest bucket


def get_sofr_rate() -> float:
    """Get current SOFR rate. Can be modified later for live data."""
    return SOFR_RATE


def get_sofr_rate_pct() -> float:
    """Get SOFR rate as percentage (e.g., 3.67)."""
    return SOFR_RATE * 100
