"""
Analyze Basket 2 rebalancing needs.

Moved into tools/ to keep the app root clean.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.calculations import calculate_rebalancing_needs, REBALANCING_THRESHOLD_SHARES  # noqa: E402


positions = pd.read_csv(PROJECT_ROOT / "Positions_physicalequities.csv")
market_data = pd.read_csv(PROJECT_ROOT / "data" / "stockmarketdata.csv")

# Basket 2 analysis
basket2 = positions[positions["BASKET_ID"] == "Basket2"]
basket2_equities = basket2[basket2["POSITION_TYPE"] == "EQUITY"]
basket2_futures = basket2[basket2["POSITION_TYPE"] == "FUTURE"]
basket2_borrows = basket2[basket2["POSITION_TYPE"] == "STOCK_BORROW"]

print("=" * 60)
print("BASKET 2 ANALYSIS - Reverse Carry (Short Physical, Long Futures)")
print("=" * 60)

print("\nPosition counts:")
print(f"  Equity positions: {len(basket2_equities)}")
print(f"  Stock borrow positions: {len(basket2_borrows)}")
print(f"  Futures positions: {len(basket2_futures)}")

if not basket2_equities.empty:
    print("\nEquity summary:")
    print(f"  Total equity market value: ${basket2_equities['MARKET_VALUE_USD'].sum():,.0f}")

    # Check if SHORT or LONG
    if "LONG_SHORT" in basket2_equities.columns:
        long_count = (basket2_equities["LONG_SHORT"] == "LONG").sum()
        short_count = (basket2_equities["LONG_SHORT"] == "SHORT").sum()
        print(f"  Long positions: {long_count}")
        print(f"  Short positions: {short_count}")

if not basket2_futures.empty:
    notional = basket2_futures["NOTIONAL_USD"].iloc[0]
    direction = basket2_futures["LONG_SHORT"].iloc[0]
    print("\nFutures:")
    print(f"  Direction: {direction}")
    print(f"  Notional: ${abs(notional):,}")

# Run the fixed calculation
print("\n" + "=" * 60)
print("REBALANCING ANALYSIS")
print("=" * 60)

rebal_df = calculate_rebalancing_needs(basket2, market_data)

if rebal_df.empty:
    print("\nNo equity positions to analyze for rebalancing")
else:
    needs_rebal = rebal_df[rebal_df["NEEDS_REBALANCING"] == True]
    print(f"\nThreshold: {REBALANCING_THRESHOLD_SHARES} shares")
    print(f"Positions needing rebalancing: {len(needs_rebal)}")

    if not needs_rebal.empty:
        print("\nPositions flagged:")
        for _, row in needs_rebal.iterrows():
            action = row["ACTION"]
            diff = abs(int(row["SHARES_DIFF"]))
            ticker = row["TICKER"]
            current = int(row["CURRENT_SHARES"])
            target = int(row["TARGET_SHARES"])
            print(f"  {ticker}: {action} {diff:,} shares")
            print(f"    Current: {current:,} | Target: {target:,}")
    else:
        print("\nAll positions within threshold - no rebalancing needed!")

