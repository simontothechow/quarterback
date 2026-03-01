# Implied Forward Rate Calculator - Documentation

## Overview

This document describes the **Implied Forward Rate Spreadsheet** used for analyzing calendar spread arbitrage opportunities in S&P 500 futures (AIR futures). The spreadsheet calculates what interest rate the market is implying for future time periods, based on current futures prices.

---

## Purpose

The spreadsheet helps traders answer:

> "If I go LONG one futures contract and SHORT another, what implied forward rate am I locking in for that period?"

This enables:
- **Carry trades** - Harvesting the time premium between contracts
- **Arbitrage opportunities** - Finding mispriced spreads
- **Term structure analysis** - Understanding market rate expectations

---

## Spreadsheet Structure

### Data Layout

```
        │  A      │  B        │  C          │  D              │  E     │  F     │  G     │ ...
────────┼─────────┼───────────┼─────────────┼─────────────────┼────────┼────────┼────────┼─────
Row 2   │         │           │             │                 │ -42    │ -7     │ 21     │  Days to expiry (columns)
Row 3   │         │           │             │ End             │ AXWF6  │ AXWG6  │ AXWH6  │  Contract codes (columns)
Row 4   │         │           │             │                 │ 44.5   │ 72     │ 95     │  Contract PRICES (columns)
Row 5   │ Start   │           │ last_price  │ FUT_DLV_DT_FIRST│1/16/26 │2/20/26 │3/20/26 │  Delivery dates (columns)
────────┼─────────┼───────────┼─────────────┼─────────────────┼────────┼────────┼────────┼─────
Row 6   │ -70     │ AXWZ5     │ 65          │ 12/19/2025      │ CALC   │ CALC   │ CALC   │  Forward rates
Row 7   │ -42     │ AXWF6     │ VALUEERROR  │ 1/16/2026       │ DARK   │ DARK   │ DARK   │  (no valid price)
Row 8   │ -7      │ AXWG6     │ VALUEERROR  │ 2/20/2026       │ DARK   │ DARK   │ DARK   │  (no valid price)
Row 9   │ 21      │ AXWH6     │ 44.5        │ 3/20/2026       │ DARK   │ DARK   │ DARK   │  Forward rates
Row 10  │ 49      │ AXWJ6     │ 72          │ 4/17/2026       │ DARK   │ DARK   │ DARK   │  Forward rates
...     │         │           │             │                 │        │        │        │
```

### Key Columns/Rows

| Location | Description |
|----------|-------------|
| **Column A** | "Start" - Days to expiry for the FROM contract (row) |
| **Column B** | Contract code for the FROM contract (row) |
| **Column C** | "last_price" - Price for the FROM contract (row) |
| **Column D** | "FUT_DLV_DT_FIRST" - Delivery date for the FROM contract (row) |
| **Row 2** | Days to expiry for each TO contract (column) |
| **Row 3** | Contract codes for each TO contract (column) |
| **Row 4** | Prices for each TO contract (column) - **MUST match Column C for same contract** |
| **Row 5** | Delivery dates for each TO contract (column) |
| **Grid (E6:P29)** | Calculated implied forward rates |

---

## The Formula

### Excel Formula (for cell J9 as example)

```excel
=(J4-($C$9*(($D$9-(TODAY()))/($J5-(TODAY())))))/(($J2-$A$9)/J2)
```

### Formula in Plain English

```
Implied Forward Rate = 
    (TO_Contract_Price - (FROM_Contract_Price × Time_Ratio))
    ÷
    Day_Count_Fraction

Where:
    Time_Ratio = Days_to_FROM_Contract ÷ Days_to_TO_Contract
    Day_Count_Fraction = (Days_to_TO - Days_to_FROM) ÷ Days_to_TO
```

### Formula Components Explained

| Component | Cell Reference | Description |
|-----------|---------------|-------------|
| `J4` | TO contract price | Price of the contract you're rolling TO |
| `$C$9` | FROM contract price | Price of the contract you're rolling FROM |
| `$D$9` | FROM delivery date | When the FROM contract expires |
| `$J5` | TO delivery date | When the TO contract expires |
| `$J2` | TO days to expiry | Days until TO contract expires |
| `$A$9` | FROM days to expiry | Days until FROM contract expires |
| `TODAY()` | Current date | Used to calculate remaining days |

### Visual Representation

```
TODAY ─────────── FROM Contract ─────────── TO Contract
  │                    │                        │
  │◄── Days to FROM ──►│                        │
  │                                             │
  │◄────────────── Days to TO ─────────────────►│
                       │                        │
                       │◄── Forward Period ────►│
                       │                        │
                    RESULT: Implied rate for this period
```

---

## Understanding Implied Forward Rates

### What Is an Implied Forward Rate?

The market prices futures contracts for different expiration dates. From these prices, we can **back-calculate** what interest rate the market is "implying" for future time periods.

**Example:**
- March 2026 futures price implies a certain rate from now until March
- June 2026 futures price implies a certain rate from now until June
- The **implied forward rate** (March→June) is what's left over for the March-to-June period

### Why This Matters

If you believe the ACTUAL rate from March to June will be different from what the market implies:

| Your View | Market Implies | Action |
|-----------|---------------|--------|
| Rates will be HIGHER | Lower rate | SELL the spread (short near, long far) |
| Rates will be LOWER | Higher rate | BUY the spread (long near, short far) |

---

## The Trading Strategy: Calendar Spread Arbitrage

### Basic Concept

1. **Go LONG** one futures contract (the "FROM" or near-dated contract)
2. **Go SHORT** another futures contract (the "TO" or far-dated contract)
3. **Hold** until the near contract expires
4. **Profit** from the spread convergence

### Example Trade

```
Trade Date: February 27, 2026
Action: Buy March futures (AXWH6) at 44.5, Sell June futures (AXWM6) at 51.5
Spread locked in: 7.0 basis points

Matrix shows: Implied forward rate (Mar→Jun) = 111.72 bps

Interpretation: The market is pricing in a 111.72 bps annualized forward rate
               for the March-to-June period.

If you think the actual rate will be LOWER, this spread is attractive.
```

### Risk/Reward

| Factor | Description |
|--------|-------------|
| **Profit source** | Carry (time premium) + Rate view |
| **Max profit** | Spread converges favorably |
| **Max loss** | Spread moves against you |
| **Key risk** | Interest rate moves opposite to your view |

---

## Dark Cells Explanation

Cells in the matrix are **dark/empty** when:

1. **FROM contract expires AFTER TO contract** - Can't have a forward period that goes backwards in time
2. **Either contract has no valid price** - VALUEERROR in the price data

---

## Critical Data Integrity Rule

### Row 4 MUST Equal Column C for the Same Contract

The formula assumes:
- **Row 4** = Price when that contract is the END of the forward period
- **Column C** = Price when that contract is the START of the forward period

**These must be the same value** because it's the same contract at the same price.

| Contract | Row 4 (Column Header) | Column C (Row Data) | Must Match? |
|----------|----------------------|---------------------|-------------|
| AXWH6 | G4 = 44.5 | C9 = 44.5 | ✓ YES |
| AXWM6 | J4 = 51.5 | C12 = 51.5 | ✓ YES |

If these don't match, the implied forward rate calculation will be incorrect.

---

## Contract Naming Convention

The futures contracts follow this pattern: `AXW` + `Month Code` + `Year`

### Month Codes

| Code | Month | Typical Expiry |
|------|-------|----------------|
| F | January | 3rd Friday |
| G | February | 3rd Friday |
| H | March | 3rd Friday |
| J | April | 3rd Friday |
| K | May | 3rd Friday |
| M | June | 3rd Friday |
| U | September | 3rd Friday |
| Z | December | 3rd Friday |

### Examples

| Contract | Meaning |
|----------|---------|
| AXWH6 | March 2026 futures |
| AXWM6 | June 2026 futures |
| AXWZ7 | December 2027 futures |
| AXWH8 | March 2028 futures |

---

## Files Reference

| File | Description |
|------|-------------|
| `Mid_Spreads_Reconstructed.xlsx` | Original values (static, no formulas) |
| `Mid_Spreads_With_Formulas.xlsx` | With formulas but original (potentially incorrect) Row 4 |
| `Mid_Spreads_Corrected.xlsx` | **CORRECT VERSION** - Row 4 matches Column C, proper formulas |
| `create_spreadsheet.py` | Script to generate static version |
| `create_spreadsheet_with_formulas.py` | Script to generate formula version |
| `create_spreadsheet_corrected.py` | Script to generate corrected version |

---

## Future App Implementation Notes

When building this feature into the Quarterback app:

### Data Requirements

1. **Live futures prices** for all contracts (Column C / Row 4)
2. **Delivery dates** for all contracts (Column D / Row 5)
3. **Days to expiry** calculation (can be derived from delivery dates and current date)

### Calculation Steps

```python
def calculate_implied_forward_rate(from_price, to_price, days_to_from, days_to_to):
    """
    Calculate implied forward rate between two contracts.
    
    Args:
        from_price: Price of the near-dated (FROM) contract
        to_price: Price of the far-dated (TO) contract
        days_to_from: Days until FROM contract delivery
        days_to_to: Days until TO contract delivery
    
    Returns:
        Implied forward rate in basis points
    """
    if days_to_from >= days_to_to:
        return None  # Invalid: FROM must expire before TO
    
    time_ratio = days_to_from / days_to_to
    day_count_fraction = (days_to_to - days_to_from) / days_to_to
    
    numerator = to_price - (from_price * time_ratio)
    forward_rate = numerator / day_count_fraction
    
    return forward_rate
```

### UI Considerations

1. **Matrix view** - Show all combinations of FROM/TO contracts
2. **Color coding** - Highlight attractive spreads (cheap vs rich)
3. **Filtering** - Allow users to filter by time period (e.g., only 3-month forwards)
4. **Trade generator** - Click a cell to generate the spread trade orders

---

## Glossary

| Term | Definition |
|------|------------|
| **Calendar Spread** | Trading two futures contracts with different expiration dates |
| **Carry** | The cost or benefit of holding a position over time |
| **Forward Rate** | An interest rate for a future time period, derived from current prices |
| **Implied** | Calculated/derived from market prices, not directly quoted |
| **Roll** | Moving a futures position from one expiration to another |
| **Basis Points (bps)** | 1/100th of a percent (100 bps = 1%) |
| **Long** | Buying / owning a position |
| **Short** | Selling / owing a position |
| **Arbitrage** | Profiting from price differences in related instruments |

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| Feb 27, 2026 | AI Assistant | Initial documentation based on spreadsheet analysis |

---

*This documentation was created to support the Quarterback v1 application futures trading feature.*
