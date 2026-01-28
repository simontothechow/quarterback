"""
Analyze rebalancing requirements for Basket 1 and Basket 2

Rules:
- 2-share rebalancing threshold
- Use PRICE_OR_LEVEL from positions file for calculations
- SHORT positions have LONG_SHORT='SHORT' and negative QUANTITY
"""

import pandas as pd
import numpy as np

# Configuration
REBALANCE_THRESHOLD_SHARES = 2  # Generate warning if position differs by > 2 shares

# Load data
positions = pd.read_csv(r'C:\Users\simon\Desktop\Quarterback_v1\positions_physicalequities.csv')
market_data = pd.read_csv(r'C:\Users\simon\Desktop\Quarterback_v1\data\stockmarketdata.csv')

# Filter for EQUITY positions only
equity_positions = positions[positions['POSITION_TYPE'] == 'EQUITY'].copy()

# Get Basket 1 and Basket 2 equity positions
b1_equities = equity_positions[equity_positions['BASKET_ID'] == 'Basket1'].copy()
b2_equities = equity_positions[equity_positions['BASKET_ID'] == 'Basket2'].copy()

# Extract ticker from UNDERLYING column
b1_equities['TICKER'] = b1_equities['UNDERLYING'].str.strip()
b2_equities['TICKER'] = b2_equities['UNDERLYING'].str.strip()

# Get total portfolio value for each basket (use absolute value for shorts)
b1_total = b1_equities['MARKET_VALUE_USD'].sum()
b2_total = abs(b2_equities['MARKET_VALUE_USD'].sum())

print(f'Basket 1 Total Equity Value: ${b1_total:,.2f}')
print(f'Basket 2 Total Equity Value: ${b2_total:,.2f}')
print(f'Rebalancing Threshold: {REBALANCE_THRESHOLD_SHARES} shares')
print()

# Get market data ticker and index weight
market_data['TICKER'] = market_data['BLOOMBERG_TICKER'].str.strip()

# Merge to compare - using PRICE_OR_LEVEL from positions file
b1_merged = b1_equities.merge(market_data[['TICKER', 'INDEX_WEIGHT']], on='TICKER', how='left')
b2_merged = b2_equities.merge(market_data[['TICKER', 'INDEX_WEIGHT']], on='TICKER', how='left')

# Convert QUANTITY and PRICE to numeric
b1_merged['QUANTITY'] = pd.to_numeric(b1_merged['QUANTITY'], errors='coerce').fillna(0)
b2_merged['QUANTITY'] = pd.to_numeric(b2_merged['QUANTITY'], errors='coerce').fillna(0)
b1_merged['PRICE_OR_LEVEL'] = pd.to_numeric(b1_merged['PRICE_OR_LEVEL'], errors='coerce').fillna(0)
b2_merged['PRICE_OR_LEVEL'] = pd.to_numeric(b2_merged['PRICE_OR_LEVEL'], errors='coerce').fillna(0)

# Calculate current weight in portfolio
b1_merged['CURRENT_WEIGHT'] = b1_merged['MARKET_VALUE_USD'] / b1_total
b2_merged['CURRENT_WEIGHT'] = abs(b2_merged['MARKET_VALUE_USD']) / b2_total

# Calculate target value based on index weight
b1_merged['TARGET_VALUE'] = b1_merged['INDEX_WEIGHT'] * b1_total
b2_merged['TARGET_VALUE'] = b2_merged['INDEX_WEIGHT'] * b2_total

# Calculate target shares (using PRICE_OR_LEVEL from positions)
b1_merged['TARGET_SHARES'] = b1_merged['TARGET_VALUE'] / b1_merged['PRICE_OR_LEVEL']
b2_merged['TARGET_SHARES'] = b2_merged['TARGET_VALUE'] / b2_merged['PRICE_OR_LEVEL']

# Calculate shares difference
# For Basket 1 (LONG): SHARES_DIFF = TARGET - CURRENT (positive = need to buy)
# For Basket 2 (SHORT): SHARES_DIFF = TARGET - |CURRENT| (positive = need to short more)
b1_merged['SHARES_DIFF'] = b1_merged['TARGET_SHARES'] - b1_merged['QUANTITY']
b2_merged['SHARES_DIFF'] = b2_merged['TARGET_SHARES'] - abs(b2_merged['QUANTITY'])

# Calculate value difference using position price
b1_merged['VALUE_DIFF'] = b1_merged['SHARES_DIFF'] * b1_merged['PRICE_OR_LEVEL']
b2_merged['VALUE_DIFF'] = b2_merged['SHARES_DIFF'] * b2_merged['PRICE_OR_LEVEL']

# Find positions needing rebalancing (> threshold shares)
b1_rebal = b1_merged[abs(b1_merged['SHARES_DIFF']) > REBALANCE_THRESHOLD_SHARES].copy()
b2_rebal = b2_merged[abs(b2_merged['SHARES_DIFF']) > REBALANCE_THRESHOLD_SHARES].copy()

# Also check for zero/missing quantity positions that should have holdings
b1_zero = b1_merged[(b1_merged['QUANTITY'] == 0) & (b1_merged['INDEX_WEIGHT'] > 0)].copy()
b2_zero = b2_merged[(b2_merged['QUANTITY'] == 0) & (b2_merged['INDEX_WEIGHT'] > 0)].copy()

print('='*80)
print('BASKET 1 - REBALANCING ANALYSIS (Simple Carry: LONG Equities)')
print('='*80)
print(f'\nPositions with QUANTITY = 0 (missing positions that need to be BOUGHT):')
if not b1_zero.empty:
    for _, row in b1_zero.iterrows():
        shares = row['SHARES_DIFF']
        if pd.notna(shares) and shares > 0:
            print(f"  {row['TICKER']:12} - Need to BUY {shares:,.0f} shares (Index Weight: {row['INDEX_WEIGHT']*100:.4f}%)")
else:
    print("  None")

print('\n' + '-'*80)
print(f'Positions needing rebalancing (>{REBALANCE_THRESHOLD_SHARES} share diff, sorted by absolute share difference):')
print('-'*80)
b1_rebal_sorted = b1_rebal.reindex(b1_rebal['SHARES_DIFF'].abs().sort_values(ascending=False).index)
for _, row in b1_rebal_sorted.head(25).iterrows():
    shares = row['SHARES_DIFF']
    action = 'BUY' if shares > 0 else 'SELL'
    current_qty = int(row['QUANTITY'])
    target_qty = int(row['TARGET_SHARES'])
    price = row['PRICE_OR_LEVEL']
    value = abs(row['VALUE_DIFF'])
    print(f"  {row['TICKER']:12} - {action:4} {abs(shares):>8,.0f} shares | Current: {current_qty:>6,} | Target: {target_qty:>6,} | Price: ${price:>8.2f} | Value: ${value:>12,.2f}")

print('\n')
print('='*80)
print('BASKET 2 - REBALANCING ANALYSIS (Reverse Carry: SHORT Equities)')
print('='*80)
print(f'\nPositions with QUANTITY = 0 (missing positions that need to be SHORTED):')
if not b2_zero.empty:
    for _, row in b2_zero.iterrows():
        shares = row['SHARES_DIFF']
        if pd.notna(shares) and shares > 0:
            print(f"  {row['TICKER']:12} - Need to SHORT {shares:,.0f} shares (Index Weight: {row['INDEX_WEIGHT']*100:.4f}%)")
else:
    print("  None")

print('\n' + '-'*80)
print(f'Positions needing rebalancing (>{REBALANCE_THRESHOLD_SHARES} share diff, sorted by absolute share difference):')
print('-'*80)
b2_rebal_sorted = b2_rebal.reindex(b2_rebal['SHARES_DIFF'].abs().sort_values(ascending=False).index)
for _, row in b2_rebal_sorted.head(25).iterrows():
    shares = row['SHARES_DIFF']
    # For Basket 2 (short positions): positive means need to short more, negative means cover
    action = 'SHORT MORE' if shares > 0 else 'COVER'
    current_qty = int(abs(row['QUANTITY']))  # Show as positive for readability
    target_qty = int(row['TARGET_SHARES'])
    price = row['PRICE_OR_LEVEL']
    value = abs(row['VALUE_DIFF'])
    print(f"  {row['TICKER']:12} - {action:10} {abs(shares):>8,.0f} shares | Current: {current_qty:>6,} | Target: {target_qty:>6,} | Price: ${price:>8.2f} | Value: ${value:>12,.2f}")

# Summary statistics
print('\n')
print('='*80)
print('SUMMARY')
print('='*80)
print(f"\nBasket 1 (LONG equities):")
print(f"  Total positions in basket: {len(b1_merged)}")
print(f"  Positions needing rebalancing (>{REBALANCE_THRESHOLD_SHARES} shares): {len(b1_rebal)}")
print(f"  Positions with zero quantity: {len(b1_zero)}")
b1_buy = b1_rebal[b1_rebal['SHARES_DIFF'] > 0]['VALUE_DIFF'].sum()
b1_sell = abs(b1_rebal[b1_rebal['SHARES_DIFF'] < 0]['VALUE_DIFF'].sum())
print(f"  Total value to BUY: ${b1_buy:,.2f}")
print(f"  Total value to SELL: ${b1_sell:,.2f}")

print(f"\nBasket 2 (SHORT equities):")
print(f"  Total positions in basket: {len(b2_merged)}")
print(f"  Positions needing rebalancing (>{REBALANCE_THRESHOLD_SHARES} shares): {len(b2_rebal)}")
print(f"  Positions with zero quantity: {len(b2_zero)}")
b2_short = b2_rebal[b2_rebal['SHARES_DIFF'] > 0]['VALUE_DIFF'].sum()
b2_cover = abs(b2_rebal[b2_rebal['SHARES_DIFF'] < 0]['VALUE_DIFF'].sum())
print(f"  Total value to SHORT MORE: ${b2_short:,.2f}")
print(f"  Total value to COVER: ${b2_cover:,.2f}")
