import pandas as pd

THRESHOLD = 1000

positions = pd.read_csv(r'C:\Users\simon\Desktop\Quarterback_v1\positions_physicalequities.csv')
market_data = pd.read_csv(r'C:\Users\simon\Desktop\Quarterback_v1\data\stockmarketdata.csv')

equity_positions = positions[positions['POSITION_TYPE'] == 'EQUITY'].copy()
b1 = equity_positions[equity_positions['BASKET_ID'] == 'Basket1'].copy()
b2 = equity_positions[equity_positions['BASKET_ID'] == 'Basket2'].copy()

b1['TICKER'] = b1['UNDERLYING'].str.strip()
b2['TICKER'] = b2['UNDERLYING'].str.strip()

b1_total = b1['MARKET_VALUE_USD'].sum()
b2_total = abs(b2['MARKET_VALUE_USD'].sum())

market_data['TICKER'] = market_data['BLOOMBERG_TICKER'].str.strip()

b1 = b1.merge(market_data[['TICKER', 'INDEX_WEIGHT']], on='TICKER', how='left')
b2 = b2.merge(market_data[['TICKER', 'INDEX_WEIGHT']], on='TICKER', how='left')

b1['QUANTITY'] = pd.to_numeric(b1['QUANTITY'], errors='coerce').fillna(0)
b2['QUANTITY'] = pd.to_numeric(b2['QUANTITY'], errors='coerce').fillna(0)
b1['PRICE_OR_LEVEL'] = pd.to_numeric(b1['PRICE_OR_LEVEL'], errors='coerce').fillna(0)
b2['PRICE_OR_LEVEL'] = pd.to_numeric(b2['PRICE_OR_LEVEL'], errors='coerce').fillna(0)

b1['TARGET_SHARES'] = (b1['INDEX_WEIGHT'] * b1_total) / b1['PRICE_OR_LEVEL']
b2['TARGET_SHARES'] = (b2['INDEX_WEIGHT'] * b2_total) / b2['PRICE_OR_LEVEL']

b1['SHARES_DIFF'] = b1['TARGET_SHARES'] - b1['QUANTITY']
b2['SHARES_DIFF'] = b2['TARGET_SHARES'] - abs(b2['QUANTITY'])

b1_rebal = b1[abs(b1['SHARES_DIFF']) > THRESHOLD]
b2_rebal = b2[abs(b2['SHARES_DIFF']) > THRESHOLD]

print(f'=== With {THRESHOLD}-share threshold ===')
print()
print(f'BASKET 1: {len(b1_rebal)} positions need rebalancing')
print('-'*70)
for _, row in b1_rebal.sort_values('SHARES_DIFF', key=abs, ascending=False).iterrows():
    action = 'BUY' if row['SHARES_DIFF'] > 0 else 'SELL'
    curr = int(row['QUANTITY'])
    tgt = int(row['TARGET_SHARES'])
    diff = int(abs(row['SHARES_DIFF']))
    print(f"  {row['TICKER']:12} - {action:4} {diff:>6,} shares | Current: {curr:>6,} | Target: {tgt:>6,}")

print()
print(f'BASKET 2: {len(b2_rebal)} positions need rebalancing')
print('-'*70)
for _, row in b2_rebal.sort_values('SHARES_DIFF', key=abs, ascending=False).iterrows():
    action = 'SHORT' if row['SHARES_DIFF'] > 0 else 'COVER'
    curr = int(abs(row['QUANTITY']))
    tgt = int(row['TARGET_SHARES'])
    diff = int(abs(row['SHARES_DIFF']))
    print(f"  {row['TICKER']:12} - {action:5} {diff:>6,} shares | Current: {curr:>6,} | Target: {tgt:>6,}")
