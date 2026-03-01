"""
Implied Forward Rate Calculator

This script demonstrates that the entire forward rate matrix can be 
recreated from simple market data (contract, days to maturity, price, maturity date).

Input: SP500 AIR futures prices.xlsx
Output: Forward rate matrix printed to console + exported to Excel
"""

import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================
# STEP 1: Load the source data
# ============================================================
print("="*70)
print("STEP 1: Loading source data")
print("="*70)

# Load from Excel
source_file = r"C:\Users\simon\OneDrive\Desktop\Quarterback_v1\data\Futures data B\SP500 AIR futures prices.xlsx"
df = pd.read_excel(source_file)

# Calculate days to maturity dynamically from today's date
TODAY = datetime.now().date()
print(f"\nToday's date: {TODAY}")

# Convert Maturity column to date and calculate days
df['Maturity'] = pd.to_datetime(df['Maturity']).dt.date
df['Days_Calculated'] = df['Maturity'].apply(lambda x: (x - TODAY).days)

print(f"\nLoaded {len(df)} contracts:\n")
print(df[['Contract_Code', 'Days_to_maturity', 'Days_Calculated', 'last_price', 'Maturity']].to_string(index=False))
print("\nNote: Days_to_maturity = static (from file), Days_Calculated = dynamic (from today)")

# ============================================================
# STEP 2: Define the forward rate calculation function
# ============================================================
print("\n" + "="*70)
print("STEP 2: Forward Rate Formula")
print("="*70)

def calculate_implied_forward_rate(from_price, to_price, days_to_from_dynamic, days_to_to_dynamic,
                                    days_to_from_static=None, days_to_to_static=None):
    """
    Calculate the implied forward rate between two contracts.
    
    The spreadsheet formula uses a HYBRID approach:
    - Numerator: uses DYNAMIC days (calculated from dates - TODAY())
    - Denominator: uses STATIC days (from Row 2 and Column A)
    
    Formula:
    Forward Rate = (TO_Price - (FROM_Price × (Dynamic_Days_FROM / Dynamic_Days_TO))) 
                   ÷ 
                   ((Static_Days_TO - Static_Days_FROM) / Static_Days_TO)
    
    Args:
        from_price: Price of the near-dated (FROM) contract
        to_price: Price of the far-dated (TO) contract
        days_to_from_dynamic: Days until FROM contract (calculated from date)
        days_to_to_dynamic: Days until TO contract (calculated from date)
        days_to_from_static: Static days for FROM (from original data, optional)
        days_to_to_static: Static days for TO (from original data, optional)
    
    Returns:
        Implied forward rate, or None if invalid
    """
    # Use static days for denominator if provided, otherwise use dynamic
    if days_to_from_static is None:
        days_to_from_static = days_to_from_dynamic
    if days_to_to_static is None:
        days_to_to_static = days_to_to_dynamic
    
    # Validation: FROM must expire BEFORE TO
    if days_to_from_dynamic >= days_to_to_dynamic:
        return None
    
    # Time ratio for numerator: uses DYNAMIC days
    time_ratio = days_to_from_dynamic / days_to_to_dynamic
    
    # Day count fraction for denominator: uses STATIC days
    day_count_fraction = (days_to_to_static - days_to_from_static) / days_to_to_static
    
    # Numerator: TO price minus time-adjusted FROM price
    numerator = to_price - (from_price * time_ratio)
    
    # Final calculation
    forward_rate = numerator / day_count_fraction
    
    return forward_rate

print("""
Formula:
  Forward Rate = (TO_Price - (FROM_Price × Time_Ratio)) ÷ Day_Count_Fraction

Where:
  Time_Ratio = Days_to_FROM ÷ Days_to_TO
  Day_Count_Fraction = (Days_to_TO - Days_to_FROM) ÷ Days_to_TO
""")

# ============================================================
# STEP 3: Create the forward rate matrix
# ============================================================
print("="*70)
print("STEP 3: Building Forward Rate Matrix")
print("="*70)

# Get list of contracts
contracts = df['Contract_Code'].tolist()
n = len(contracts)

# Create empty matrix
matrix = pd.DataFrame(index=contracts, columns=contracts, dtype=float)

# Fill the matrix
# Note: We use DYNAMIC days (Days_Calculated) for the time ratio in numerator
#       and STATIC days (original Days_to_maturity from file) for denominator
#       This matches the spreadsheet's hybrid approach

for from_contract in contracts:
    from_row = df[df['Contract_Code'] == from_contract].iloc[0]
    from_price = from_row['last_price']
    days_to_from_dynamic = from_row['Days_Calculated']
    days_to_from_static = from_row['Days_to_maturity']  # Original static value
    
    for to_contract in contracts:
        to_row = df[df['Contract_Code'] == to_contract].iloc[0]
        to_price = to_row['last_price']
        days_to_to_dynamic = to_row['Days_Calculated']
        days_to_to_static = to_row['Days_to_maturity']  # Original static value
        
        # Calculate forward rate using hybrid approach
        fwd_rate = calculate_implied_forward_rate(
            from_price, to_price,
            days_to_from_dynamic, days_to_to_dynamic,
            days_to_from_static, days_to_to_static
        )
        
        matrix.loc[from_contract, to_contract] = fwd_rate

print(f"\nMatrix dimensions: {n} x {n} = {n*n} cells")
print(f"Valid forward rates: {matrix.notna().sum().sum()} cells")
print(f"Invalid (dark) cells: {matrix.isna().sum().sum()} cells")

# ============================================================
# STEP 4: Display the matrix
# ============================================================
print("\n" + "="*70)
print("STEP 4: Implied Forward Rate Matrix")
print("="*70)

# Format for display (round to 2 decimals, show '-' for NaN)
display_matrix = matrix.round(2).fillna('-')

# Show first 10x10 for readability
print("\nFirst 10 contracts (FROM rows -> TO columns):\n")
print(display_matrix.iloc[:10, :10].to_string())

# ============================================================
# STEP 5: Verify against known values
# ============================================================
print("\n" + "="*70)
print("STEP 5: Verification Against Original Spreadsheet")
print("="*70)

# Check specific cells against the CORRECTED spreadsheet (Mid_Spreads_Corrected_shortened.xlsx)
test_cases = [
    ('AXWH6', 'AXWJ6', 93.55),   # F6 - March to April
    ('AXWH6', 'AXWK6', 114.52),  # G6 - March to May
    ('AXWH6', 'AXWM6', 53.54),   # H6 - March to June
    ('AXWH6', 'AXWU6', 55.87),   # I6 - March to September
    ('AXWH6', 'AXWZ6', 57.04),   # J6 - March to December
]

print("\nComparing calculated values to original spreadsheet:")
print("-" * 60)
print(f"{'FROM':<10} {'TO':<10} {'Expected':<12} {'Calculated':<12} {'Match?'}")
print("-" * 60)

for from_c, to_c, expected in test_cases:
    calculated = matrix.loc[from_c, to_c]
    match = "YES" if abs(calculated - expected) < 0.1 else "NO"
    print(f"{from_c:<10} {to_c:<10} {expected:<12.2f} {calculated:<12.2f} {match}")

# ============================================================
# STEP 6: Export to Excel
# ============================================================
print("\n" + "="*70)
print("STEP 6: Exporting to Excel")
print("="*70)

output_file = r"C:\Users\simon\OneDrive\Desktop\Quarterback_v1\data\Futures data B\Forward_Rate_Matrix_Calculated.xlsx"

# Create Excel writer
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Sheet 1: Source data
    df.to_excel(writer, sheet_name='Source Data', index=False)
    
    # Sheet 2: Forward rate matrix
    matrix.to_excel(writer, sheet_name='Forward Rate Matrix')
    
    # Sheet 3: Summary info
    summary = pd.DataFrame({
        'Metric': ['Calculation Date', 'Number of Contracts', 'Valid Forward Rates', 'Formula'],
        'Value': [
            datetime.now().strftime('%Y-%m-%d'),
            len(contracts),
            int(matrix.notna().sum().sum()),
            '(TO_Price - FROM_Price × Time_Ratio) ÷ Day_Count_Fraction'
        ]
    })
    summary.to_excel(writer, sheet_name='Summary', index=False)

print(f"\nExported to: {output_file}")
print("\nSheets created:")
print("  1. Source Data - Original market data")
print("  2. Forward Rate Matrix - Calculated implied forward rates")
print("  3. Summary - Calculation metadata")

# ============================================================
# STEP 7: Example trade interpretation
# ============================================================
print("\n" + "="*70)
print("STEP 7: Example Trade Interpretation")
print("="*70)

# Find the highest and lowest forward rates
valid_rates = matrix.stack().dropna()
max_rate = valid_rates.max()
min_rate = valid_rates.min()
max_idx = valid_rates.idxmax()
min_idx = valid_rates.idxmin()

print(f"""
HIGHEST Implied Forward Rate: {max_rate:.2f} bps
  Period: {max_idx[0]} -> {max_idx[1]}
  Trade: If you think rates will be LOWER than {max_rate:.0f} bps, 
         BUY this spread (long {max_idx[0]}, short {max_idx[1]})

LOWEST Implied Forward Rate: {min_rate:.2f} bps  
  Period: {min_idx[0]} -> {min_idx[1]}
  Trade: If you think rates will be HIGHER than {min_rate:.0f} bps,
         SELL this spread (short {min_idx[0]}, long {min_idx[1]})
""")

print("="*70)
print("COMPLETE! Forward rate matrix successfully recreated from source data.")
print("="*70)
