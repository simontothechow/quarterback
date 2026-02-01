"""
Temporary script to analyze basket rebalancing calculation logic.

Moved into tools/ to keep the app root clean.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

# Ensure imports work when run from tools/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.calculations import calculate_rebalancing_needs, REBALANCING_THRESHOLD_SHARES  # noqa: E402


positions = pd.read_csv(PROJECT_ROOT / "Positions_physicalequities.csv")
market_data = pd.read_csv(PROJECT_ROOT / "data" / "stockmarketdata.csv")

print("=" * 60)
print("BASKET 1 ANALYSIS - Physical Equity Rebalancing")
print("=" * 60)

# Get Basket 1 data
basket1_equities = positions[
    (positions["BASKET_ID"] == "Basket1") & (positions["POSITION_TYPE"] == "EQUITY")
]
basket1_futures = positions[
    (positions["BASKET_ID"] == "Basket1") & (positions["POSITION_TYPE"] == "FUTURE")
]

# Key values
basket_notional = 100_000_000  # From futures position (demo assumption)
total_basket_mv = basket1_equities["MARKET_VALUE_USD"].sum()

print(f"\nBasket 1 Futures Notional: ${basket_notional:,}")
print(f"Basket 1 Total Equity MV:  ${total_basket_mv:,.0f}")
print(f"Number of equity positions: {len(basket1_equities)}")

print("\n" + "=" * 60)
print("THE CALCULATION LOGIC:")
print("=" * 60)
print(
    """
For each stock in the basket:
1. Get INDEX_WEIGHT from stockmarketdata.csv
2. TARGET_VALUE = BASKET_NOTIONAL × INDEX_WEIGHT
3. TARGET_SHARES = TARGET_VALUE / CURRENT_PRICE
4. SHARES_DIFF = TARGET_SHARES - CURRENT_SHARES
5. If |SHARES_DIFF| > threshold, flag for rebalancing
"""
)

print("=" * 60)
print("POSITIONS NEEDING REBALANCING (diff > 100 shares)")
print("=" * 60)

results: list[dict] = []
for _, pos in basket1_equities.iterrows():
    ticker = pos["UNDERLYING"]
    qty = pos["QUANTITY"]
    price = pos["PRICE_OR_LEVEL"]
    mv = pos["MARKET_VALUE_USD"]

    # Join to market data
    idx = market_data[market_data["BLOOMBERG_TICKER"] == ticker]
    if idx.empty:
        continue

    index_weight = idx["INDEX_WEIGHT"].iloc[0]

    # Calculate current weight
    current_weight = mv / total_basket_mv

    # Calculate target shares using BASKET NOTIONAL
    target_value = basket_notional * index_weight
    target_shares = target_value / price
    shares_diff = target_shares - qty

    if abs(shares_diff) >= 100:
        action = "BUY" if shares_diff > 0 else "SELL"
        results.append(
            {
                "ticker": ticker,
                "qty": qty,
                "target": target_shares,
                "diff": shares_diff,
                "action": action,
                "current_wt": current_weight * 100,
                "index_wt": index_weight * 100,
            }
        )

# Sort by absolute difference
results.sort(key=lambda x: abs(x["diff"]), reverse=True)

print(f"\nFound {len(results)} positions needing rebalancing:\n")
for r in results[:20]:
    print(
        f"{r['ticker']:12} | Current: {int(r['qty']):>8,} | Target: {int(r['target']):>8,} | {r['action']:4} {abs(int(r['diff'])):>6,} shares"
    )
    print(f"{'':12} | Current Wt: {r['current_wt']:.4f}% | Index Wt: {r['index_wt']:.4f}%")
    print()

print("=" * 60)
print("WHAT MY CURRENT CODE IS DOING (POTENTIALLY WRONG)")
print("=" * 60)
print(
    """
Current code uses:
  total_portfolio_value = sum of all EQUITY MARKET_VALUE_USD
  target_value = total_portfolio_value × index_weight

This is WRONG if total_portfolio_value != basket_notional

The CORRECT approach:
  basket_notional = from FUTURE or CASH position (e.g., $100M)
  target_value = basket_notional × index_weight
"""
)

print(f"\nIn this case:")
print(f"  total_portfolio_value = ${total_basket_mv:,.0f}")
print(f"  basket_notional       = ${basket_notional:,}")
print(f"  Difference            = ${abs(total_basket_mv - basket_notional):,.0f}")

if abs(total_basket_mv - basket_notional) > 1_000_000:
    print("\n[!] SIGNIFICANT DIFFERENCE - this would cause incorrect calculations!")
else:
    print("\n[OK] Values are close, so current calculation should be approximately correct")

# Now let's compare my code's logic vs correct logic
print("\n" + "=" * 60)
print("COMPARING: My Code vs Correct Calculation")
print("=" * 60)

# Rebalancing with 1000 share threshold (what my code uses)
my_code_results: list[str] = []
correct_results: list[str] = []

for _, pos in basket1_equities.iterrows():
    ticker = pos["UNDERLYING"]
    qty = pos["QUANTITY"]
    price = pos["PRICE_OR_LEVEL"]
    mv = pos["MARKET_VALUE_USD"]

    idx = market_data[market_data["BLOOMBERG_TICKER"] == ticker]
    if idx.empty:
        continue

    index_weight = idx["INDEX_WEIGHT"].iloc[0]

    # MY CODE'S CALCULATION (using total equity MV)
    my_target_value = total_basket_mv * index_weight
    my_target_shares = my_target_value / price
    my_shares_diff = my_target_shares - qty

    # CORRECT CALCULATION (using basket notional)
    correct_target_value = basket_notional * index_weight
    correct_target_shares = correct_target_value / price
    correct_shares_diff = correct_target_shares - qty

    # Check with 1000 share threshold
    if abs(my_shares_diff) >= 1000:
        my_code_results.append(ticker)
    if abs(correct_shares_diff) >= 1000:
        correct_results.append(ticker)

print(f"\nUsing 1000 share threshold:")
print(f"  My code finds {len(my_code_results)} positions needing rebalancing")
print(f"  Correct logic finds {len(correct_results)} positions needing rebalancing")

print(f"\nMy code flagged: {my_code_results[:10]}...")
print(f"Correct flagged: {correct_results[:10]}...")

# Check matching issues
print("\n" + "=" * 60)
print("CHECKING: How many positions DON'T match to market data?")
print("=" * 60)

matched = 0
not_matched: list[str] = []
for _, pos in basket1_equities.iterrows():
    ticker = pos["UNDERLYING"]

    # Exact match
    idx = market_data[market_data["BLOOMBERG_TICKER"] == ticker]
    if idx.empty:
        not_matched.append(ticker)
    else:
        matched += 1

print(f"\nMatched to market data: {matched}")
print(f"NOT matched: {len(not_matched)}")
if not_matched:
    print(f"\nSample unmatched tickers: {not_matched[:20]}")

# Check what happens when there's no match
print("\n" + "=" * 60)
print("WHAT HAPPENS WITH UNMATCHED TICKERS IN MY CODE?")
print("=" * 60)
print(
    """
If a position's ticker doesn't match market data:
  - My code sets index_weight = 0
  - target_shares = 0 (since target_value = 0)
  - shares_diff = 0 - current_qty = -current_qty
  - This flags ALL unmatched positions for SELL!

THIS IS THE BUG! If there are 141 unmatched tickers,
they all get flagged as needing to SELL all their shares.
"""
)

# Check what my code's .str.contains() is doing
print("\n" + "=" * 60)
print("CHECKING: Is .str.contains() causing wrong matches?")
print("=" * 60)

bad_matches: list[dict] = []
for _, pos in basket1_equities.iterrows():
    ticker = pos["UNDERLYING"]

    # My code's approach - uses .str.contains()
    ticker_clean = (
        str(ticker).replace(" UN", "").replace(" UQ", "").replace(" US", "").strip()
    )
    matches = market_data[
        market_data["BLOOMBERG_TICKER"].str.contains(ticker_clean, case=False, na=False)
    ]

    if len(matches) != 1:
        bad_matches.append(
            {
                "ticker": ticker,
                "clean": ticker_clean,
                "matches": len(matches),
                "matched_to": list(matches["BLOOMBERG_TICKER"].head(3)),
            }
        )

print(f"\nPositions with wrong number of matches: {len(bad_matches)}")
if bad_matches:
    print("\nExamples of bad matches:")
    for b in bad_matches[:10]:
        print(
            f"  {b['ticker']} (clean: '{b['clean']}') -> {b['matches']} matches: {b['matched_to']}"
        )

# The REAL calculation check - simulate exactly what my code does
print("\n" + "=" * 60)
print("SIMULATING MY CODE'S EXACT BEHAVIOR")
print("=" * 60)

flagged_rebal: list[dict] = []
for _, pos in basket1_equities.iterrows():
    ticker = pos["UNDERLYING"]
    qty = pos["QUANTITY"]
    price = pos["PRICE_OR_LEVEL"]

    # My code's matching logic
    ticker_clean = (
        str(ticker).replace(" UN", "").replace(" UQ", "").replace(" US", "").strip()
    )
    matches = market_data[
        market_data["BLOOMBERG_TICKER"].str.contains(ticker_clean, case=False, na=False)
    ]

    if matches.empty:
        index_weight = 0
    else:
        index_weight = matches.iloc[0]["INDEX_WEIGHT"]
        if pd.isna(index_weight):
            index_weight = 0
        index_weight = float(index_weight) / 100  # Convert from percentage

    # My code's calculation
    target_value = total_basket_mv * index_weight
    target_shares = target_value / price if price > 0 else qty
    shares_diff = target_shares - qty

    if abs(shares_diff) >= 1000:
        flagged_rebal.append({"ticker": ticker, "diff": shares_diff})

print(f"\nMy code would flag {len(flagged_rebal)} positions for rebalancing")
if flagged_rebal:
    print("Flagged tickers:")
    for f in flagged_rebal[:20]:
        action = "BUY" if f["diff"] > 0 else "SELL"
        print(f"  {f['ticker']}: {action} {abs(int(f['diff'])):,} shares")

# TEST THE FIXED CALCULATION MODULE
print("\n" + "=" * 60)
print("TESTING FIXED CALCULATION MODULE")
print("=" * 60)

basket1_all = positions[positions["BASKET_ID"] == "Basket1"]
rebal_df = calculate_rebalancing_needs(basket1_all, market_data)
needs_rebal = rebal_df[rebal_df["NEEDS_REBALANCING"] == True]

print(f"\nThreshold: {REBALANCING_THRESHOLD_SHARES} shares")
print(f"Positions needing rebalancing: {len(needs_rebal)}")

if not needs_rebal.empty:
    print("\nPositions flagged:")
    for _, row in needs_rebal.iterrows():
        print(
            f"  {row['TICKER']}: {row['ACTION']} {abs(int(row['SHARES_DIFF'])):,} shares"
        )
        print(
            f"    Current: {int(row['CURRENT_SHARES']):,} | Target: {int(row['TARGET_SHARES']):,}"
        )
else:
    print("\nNo positions need rebalancing (all within threshold)")

