"""
Analyze corporate actions and calculate trade recommendations (research script).

Moved into tools/ to keep the app root clean.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load all data
corp_actions = pd.read_csv(PROJECT_ROOT / "data" / "corpactions.csv")
positions = pd.read_csv(PROJECT_ROOT / "Positions_physicalequities.csv")
market_data = pd.read_csv(PROJECT_ROOT / "data" / "stockmarketdata.csv")

print("=" * 70)
print("TRADE RECOMMENDATIONS FOR CORP ACTIONS WITH INDEX WEIGHT CHANGES")
print("=" * 70)

# Find events with actual numeric changes
corp_actions["PRIOR"] = pd.to_numeric(corp_actions["INDEX_SHARES_PRIOR_EVENTS"], errors="coerce")
corp_actions["POST"] = pd.to_numeric(corp_actions["INDEX_SHARES_POST_EVENTS"], errors="coerce")

# Filter for events with real changes (both values exist and are different)
weight_changes = corp_actions[
    (corp_actions["PRIOR"].notna())
    & (corp_actions["POST"].notna())
    & (corp_actions["PRIOR"] != corp_actions["POST"])
].copy()

print(f"Events with INDEX_SHARES changes: {len(weight_changes)}")
print()

# Get basket notional and direction (from futures)
basket_info: dict[str, dict] = {}
for basket_id in ["Basket1", "Basket2"]:
    basket = positions[positions["BASKET_ID"] == basket_id]
    futures = basket[basket["POSITION_TYPE"] == "FUTURE"]
    if not futures.empty:
        notional = abs(futures["NOTIONAL_USD"].iloc[0])
        fut_direction = futures["LONG_SHORT"].iloc[0]
        # Physical direction is opposite of futures
        if fut_direction == "LONG":
            phys_dir = -1  # Reverse Carry: SHORT physical
            strategy = "Reverse Carry (SHORT physical)"
        else:
            phys_dir = +1  # Simple Carry: LONG physical
            strategy = "Simple Carry (LONG physical)"
        basket_info[basket_id] = {"notional": notional, "direction": phys_dir, "strategy": strategy}

print("Basket Configuration:")
for basket_id, info in basket_info.items():
    print(f"  {basket_id}: ${info['notional']:,.0f} - {info['strategy']}")
print()

# Process each event with index share changes
for _, event in weight_changes.iterrows():
    ticker = event.get("CURRENT_BLOOMBERG_TICKER", "Unknown")
    if pd.isna(ticker):
        continue

    action_type = event.get("ACTION_TYPE", "Unknown")
    eff_date = event.get("EFFECTIVE_DATE", "Unknown")
    prior = event["PRIOR"]
    post = event["POST"]

    # Calculate % change in index shares
    pct_change = (post - prior) / prior

    # Get current price and weight from market data
    mkt = market_data[market_data["BLOOMBERG_TICKER"] == ticker]
    if mkt.empty:
        print(f"No market data for {ticker}")
        continue
    price = mkt.iloc[0]["LOCAL_PRICE"]
    current_weight = mkt.iloc[0]["INDEX_WEIGHT"]  # Already decimal

    # New weight after change
    new_weight = current_weight * (1 + pct_change)

    print("=" * 70)
    print(f"EVENT: {ticker} - {action_type}")
    print(f"Effective Date: {eff_date}")
    print(f"Index Shares: {prior:,.0f} -> {post:,.0f} ({pct_change*100:+.2f}%)")
    print(f"Current Index Weight: {current_weight*100:.4f}%")
    print(f"New Index Weight: {new_weight*100:.4f}%")
    print(f"Price: ${price:.2f}")
    print()

    # Find affected equity positions
    ticker_positions = positions[
        (positions["UNDERLYING"] == ticker) & (positions["POSITION_TYPE"] == "EQUITY")
    ]

    if ticker_positions.empty:
        print("No equity positions found for this ticker")
        continue

    print("TRADE RECOMMENDATIONS:")
    print("-" * 70)
    header = f"{'Basket':<10} {'Current':>10} {'New Target':>12} {'Trade':>18} {'Value':>15}"
    print(header)
    print("-" * 70)

    for _, pos in ticker_positions.iterrows():
        basket_id = pos["BASKET_ID"]
        current_qty = pos["QUANTITY"]

        if basket_id not in basket_info:
            continue

        info = basket_info[basket_id]
        notional = info["notional"]
        direction = info["direction"]

        # Calculate new target shares
        new_target_value = notional * new_weight
        new_target_shares = (new_target_value / price) * direction

        # Trade needed
        trade_shares = new_target_shares - current_qty
        trade_value = abs(trade_shares * price)

        if trade_shares > 10:
            action = f"BUY {abs(int(trade_shares)):,}"
        elif trade_shares < -10:
            action = f"SELL {abs(int(trade_shares)):,}"
        else:
            action = "NONE (within tolerance)"

        print(
            f"{basket_id:<10} {int(current_qty):>10,} {int(new_target_shares):>12,} {action:>18} ${trade_value:>13,.0f}"
        )

    print()

