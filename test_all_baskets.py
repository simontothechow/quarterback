"""
Test rebalancing calculation for all baskets
"""
import pandas as pd
import sys
sys.path.insert(0, '.')
from modules.calculations import calculate_rebalancing_needs, REBALANCING_THRESHOLD_SHARES

positions = pd.read_csv('Positions_physicalequities.csv')
market_data = pd.read_csv('data/stockmarketdata.csv')

for basket_id in ['Basket1', 'Basket2', 'Basket3']:
    basket = positions[positions['BASKET_ID'] == basket_id]
    
    if basket.empty:
        continue
    
    print('=' * 70)
    print(f'{basket_id} ANALYSIS')
    print('=' * 70)
    
    # Get strategy info
    futures = basket[basket['POSITION_TYPE'] == 'FUTURE']
    equities = basket[basket['POSITION_TYPE'] == 'EQUITY']
    
    if not futures.empty:
        fut_direction = futures['LONG_SHORT'].iloc[0]
        fut_notional = futures['NOTIONAL_USD'].iloc[0]
        
        # Calculate net futures direction
        net_exposure = 0
        for _, f in futures.iterrows():
            if f['LONG_SHORT'] == 'LONG':
                net_exposure += abs(f['NOTIONAL_USD'])
            else:
                net_exposure -= abs(f['NOTIONAL_USD'])
        
        if net_exposure > 0:
            strategy = "Reverse Carry (LONG futures -> SHORT physical)"
            expected_physical = "NEGATIVE (short)"
        else:
            strategy = "Simple Carry (SHORT futures -> LONG physical)"
            expected_physical = "POSITIVE (long)"
        
        print(f"Strategy: {strategy}")
        print(f"Futures: {len(futures)} position(s)")
        for _, f in futures.iterrows():
            print(f"  - {f['LONG_SHORT']} ${abs(f['NOTIONAL_USD']):,.0f}")
        print(f"Net Futures Exposure: ${net_exposure:,.0f}")
        print(f"Expected Physical Direction: {expected_physical}")
    
    if not equities.empty:
        print(f"\nEquity Positions: {len(equities)}")
        sample = equities.head(3)
        for _, e in sample.iterrows():
            print(f"  - {e['UNDERLYING']}: {e['QUANTITY']:,.0f} shares ({e['LONG_SHORT']})")
    
    # Run rebalancing calculation
    rebal_df = calculate_rebalancing_needs(basket, market_data)
    
    if not rebal_df.empty:
        needs_rebal = rebal_df[rebal_df['NEEDS_REBALANCING'] == True]
        print(f"\nRebalancing Analysis (threshold: {REBALANCING_THRESHOLD_SHARES} shares):")
        print(f"  Positions needing rebalancing: {len(needs_rebal)}")
        
        if not needs_rebal.empty:
            print(f"\n  Sample positions flagged:")
            for i, (_, row) in enumerate(needs_rebal.head(5).iterrows()):
                print(f"    {row['TICKER']}: {row['ACTION']} {abs(int(row['SHARES_DIFF'])):,} shares")
                print(f"      Current: {int(row['CURRENT_SHARES']):,} | Target: {int(row['TARGET_SHARES']):,}")
        else:
            print("  ✓ All positions within threshold!")
    
    print()
