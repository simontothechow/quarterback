# Equity Financing Strategies Guide

A comprehensive reference for understanding and capturing equity financing spreads through various market instruments.

---

## Table of Contents

1. [Core Concept: The Equity Financing Premium](#core-concept-the-equity-financing-premium)
2. [The Rate Hierarchy](#the-rate-hierarchy)
3. [Instruments for Accessing Equity Financing Rates](#instruments-for-accessing-equity-financing-rates)
4. [Strategy 1: Spot Cash & Carry (Direct Balance Sheet)](#strategy-1-spot-cash--carry-direct-balance-sheet)
5. [Strategy 2: Futures Calendar Spreads (Forward Rate Exposure)](#strategy-2-futures-calendar-spreads-forward-rate-exposure)
6. [Strategy 3: Box Spreads (Risk-Free Rate)](#strategy-3-box-spreads-risk-free-rate)
7. [Strategy 4: The Complete Arbitrage](#strategy-4-the-complete-arbitrage)
8. [Forward-Starting Strategies](#forward-starting-strategies)
9. [Risk Management: DV01 and Interest Rate Exposure](#risk-management-dv01-and-interest-rate-exposure)
10. [Hedging Interest Rate Risk](#hedging-interest-rate-risk)
11. [Decision Framework: Which Strategy When](#decision-framework-which-strategy-when)
12. [Summary Tables](#summary-tables)

---

## Core Concept: The Equity Financing Premium

### What Is It?

The market pays a **premium** (~20-40 basis points over risk-free rates) to those willing to hold equities on their balance sheet. This premium exists because:

| Risk Factor | Why It Demands Premium |
|-------------|------------------------|
| **Volatility** | Equities can gap down significantly overnight |
| **Correlation** | Stocks often fall when liquidity is most needed |
| **Capital charges** | Regulators require more capital for equity holdings |
| **Haircuts** | Equity collateral gets 15-25% haircut vs 2% for Treasuries |
| **Operational complexity** | Dividends, corporate actions, settlements |

### The Economic Essence

> **If you're willing to hold equities on your balance sheet, you get paid ~30 bps extra over risk-free rates.**

All the complexity of futures, options, calendar spreads, and boxes ultimately connects to this simple economic reality.

---

## The Rate Hierarchy

### From Cheapest to Most Expensive Financing

```
Box spreads (risk-free)      ~5.30%  (SOFR)
Treasury repo                ~5.30%  (SOFR)
Equity index futures         ~5.50%  (SOFR + 20 bps)
Equity repo (GC)             ~5.55%  (SOFR + 25 bps)
Total Return Swaps           ~5.60%  (SOFR + 30 bps)
Prime brokerage              ~5.75%  (SOFR + 45 bps)
Margin lending (retail)      ~7.00%+ (Prime + spread)
```

### The Key Spread

```
Equity Financing Rate  =  SOFR + ~30 bps
Risk-Free Rate         =  SOFR
────────────────────────────────────────
Equity Premium         =  ~30 bps
```

This ~30 bps is the compensation for holding equity risk on your balance sheet.

---

## Instruments for Accessing Equity Financing Rates

### 1. Equity Index Futures

- **What they are**: Standardized contracts to buy/sell an index at a future date
- **Implied rate**: Embedded in the futures-spot basis
- **Formula**: `Futures = Spot × (1 + r × days/360) - Dividends`
- **Rate captured**: Equity financing rate (~SOFR + 20-30 bps)

### 2. Total Return Swaps (TRS)

- **What they are**: OTC contracts where you receive total return, pay financing
- **Rate paid/received**: Typically SOFR + 20-40 bps
- **Use case**: Synthetic equity exposure without ownership

### 3. Box Spreads

- **What they are**: Four-legged options structure creating synthetic zero-coupon bond
- **Rate captured**: Risk-free rate (~SOFR)
- **Use case**: Cheapest borrowing, purest lending

### 4. Equity Repo

- **What it is**: Pledge stocks as collateral, receive/deliver cash
- **Rate**: SOFR + 20-50 bps (varies by collateral quality)
- **Use case**: Direct balance sheet transactions

### 5. Securities Lending

- **What it is**: Lend out stocks, receive cash collateral
- **Rate earned**: Rebate rate (close to SOFR for GC stocks)
- **Use case**: Monetize long stock positions

---

## Strategy 1: Spot Cash & Carry (Direct Balance Sheet)

### The Setup

You already own (or buy) stocks and want to earn the equity financing rate.

### The Trade

```
Own $100M S&P 500 stocks
+ Sell $100M S&P 500 futures (any expiration)
────────────────────────────────────────────
= Locked in equity financing rate until expiry
```

### Economics

| Component | Value |
|-----------|-------|
| Equity exposure | Zero (hedged by futures) |
| Rate earned | ~5.50% (implied futures rate) |
| Risk | Minimal (dividend estimation, basis) |
| Capital required | Full stock ownership |

### Enhanced Version: Add Box Spread Borrowing

```
Own $100M stocks
+ Sell $100M futures         → Earn 5.50%
+ Short $100M box spread     → Pay 5.30%
────────────────────────────────────────────
= Net profit: ~20 bps (the equity premium)
```

On $100M for 90 days:
```
Profit = $100M × 0.20% × (90/360) = $50,000
```

### Who Should Use This

- Long-only asset managers (already hold stocks)
- Insurance companies (balance sheet capacity)
- Pension funds (natural equity holders)
- Anyone with stocks seeking yield enhancement

---

## Strategy 2: Futures Calendar Spreads (Forward Rate Exposure)

### The Setup

Trade two futures of different maturities to capture forward financing rates.

### The Trade

```
Long  $100M Apr 2026 S&P futures (near leg)
Short $100M Jun 2026 S&P futures (far leg)
────────────────────────────────────────────
= Exposure to Apr→Jun forward equity financing rate
```

### Economics

| Component | Value |
|-----------|-------|
| Equity exposure | Minimal (mostly hedged) |
| Rate exposure | Forward rate for the period between maturities |
| P&L driver | Changes in forward rate expectations |
| Capital required | Futures margin only (~5%) |

### Important Distinction

**This is NOT the same as direct balance sheet rental.**

- You don't hold stocks
- You capture forward RATE EXPECTATIONS
- Profit comes from rate CHANGES, not direct carry
- More leveraged, more volatile

### P&L Scenarios

| Scenario | Your P&L |
|----------|----------|
| Forward rate stays high | Collect "carry" as spread rolls |
| Forward rate rises | Profit |
| Forward rate falls | Loss |
| Rates shift parallel | Mostly neutral (DV01 exposure) |

### Who Should Use This

- Traders with views on forward financing rates
- Those wanting leveraged exposure without holding stocks
- Rate speculators

---

## Strategy 3: Box Spreads (Risk-Free Rate)

### What Is a Box Spread?

A combination of 4 options that creates a synthetic zero-coupon bond with guaranteed payoff at expiration.

### Construction

**Long Box (You LEND money):**
```
At strikes K1=5000 and K2=5100:

Buy  5000 Call  ┐
Sell 5000 Put   ┤ = Synthetic Long at 5000
                │
Sell 5100 Call  ┤
Buy  5100 Put   ┘ = Synthetic Short at 5100

Guaranteed payoff at expiration: $100 (K2 - K1)
```

### Example Pricing

```
Box pays $100 at expiration (90 days out)
Box costs $98.75 today
Return: $1.25 / $98.75 = 1.27%
Annualized: 1.27% × (365/90) = 5.13%
```

### Short Box (You BORROW money)

- Flip all trades
- Receive $98.75 today
- Owe $100 at expiration
- Borrowing rate: 5.13%

### Why Use Box Spreads?

| Advantage | Detail |
|-----------|--------|
| Cheapest borrowing | Often beats broker rates |
| No counterparty approval | Just trade options |
| Locked-in rate | No floating rate risk |
| Pure rate exposure | Zero equity beta |

### Limitations

| Disadvantage | Detail |
|--------------|--------|
| 4 legs | Higher transaction costs |
| Wider bid/ask | Especially for odd dates |
| Complexity | Harder to execute |
| Lower rate | SOFR, not equity rate |

---

## Strategy 4: The Complete Arbitrage

### The Insight

**Borrow where it's cheap, lend where it's rich.**

```
Borrow via box spread:  Pay ~5.30% (SOFR)
Lend via futures:       Earn ~5.60% (equity rate)
────────────────────────────────────────────────
Net spread:             ~30 bps
```

### The Trade

```
1. Buy $100M S&P 500 stocks
2. Sell $100M S&P 500 futures (earn equity financing)
3. Short $100M box spread (borrow at SOFR)
4. Net equity exposure: Zero
5. Net P&L: ~30 bps annualized
```

### On $100M for 90 days:

```
Gross spread: $100M × 0.30% × (90/360) = $75,000
Transaction costs: ~$10,000-20,000
Net profit: ~$55,000-65,000
```

### Why Does This Spread Exist?

| Reason | Explanation |
|--------|-------------|
| Different collateral | Equities vs Treasuries |
| Market segmentation | Futures traders ≠ options traders |
| Capital treatment | Different regulatory charges |
| Operational barriers | Not everyone can execute both |

---

## Forward-Starting Strategies

### Can You Create Forward-Starting Box Spreads?

**Yes!** Called "Calendar Box" or "Jelly Roll."

### Forward Box Construction

```
Short Apr 2026 box  → Borrow until Apr at SOFR
Long  Jun 2026 box  → Lend until Jun at SOFR
────────────────────────────────────────────────
= Locked in FORWARD SOFR for Apr→Jun period
```

### Forward Arbitrage Trade

Combine calendar futures with calendar box:

```
Calendar Futures:
  Long Apr futures / Short Jun futures
  → RECEIVE forward equity financing rate (~55 bps)

Calendar Box:
  Short Apr box / Long Jun box
  → PAY forward SOFR (~52 bps)

Net: Pocket ~3 bps forward equity premium
```

### Why Is Forward Premium Smaller?

- Less balance sheet actually used
- Markets more efficient in forward space
- Harder to execute = smaller premium persists

### Comparison: Spot vs Forward

| Aspect | Spot Strategy | Forward Strategy |
|--------|---------------|------------------|
| Premium captured | ~30 bps | ~3-10 bps (varies) |
| Balance sheet required | Yes (hold stocks) | No |
| Complexity | Moderate | Higher |
| Risk profile | Lower | Higher |
| What you're earning | Balance sheet rental | Forward rate exposure |

---

## Risk Management: DV01 and Interest Rate Exposure

### What Is DV01?

**Dollar Value of 01** = P&L change for 1 basis point move in rates.

### Calendar Spread DV01

For a calendar spread, DV01 depends on the **period between contracts**:

```
DV01 ≈ Notional × (Days between contracts / 360) × 0.0001
```

**Example: $100M, 90-day period**
```
DV01 = $100,000,000 × (90/360) × 0.0001 = $2,500 per bp
```

### Directional Exposure

| Position | Rate Sensitivity |
|----------|------------------|
| Long near / Short far | **Short duration** (benefit when rates rise) |
| Short near / Long far | **Long duration** (benefit when rates fall) |

### Key Property: DV01 Is Stable Over Time

Unlike a single bond/future, calendar spread DV01 stays **relatively constant** because it depends on the period (which is fixed), not absolute days to maturity.

| Date | Near DV01 | Far DV01 | Spread DV01 |
|------|-----------|----------|-------------|
| Feb 27 | $1,444 | $3,944 | $2,500 |
| Mar 27 | $667 | $3,167 | $2,500 |
| Apr 15 | $139 | $2,639 | $2,500 |

---

## Hedging Interest Rate Risk

### The Problem

Calendar spreads have DV01 exposure. If rates move against you, you lose money even if your carry thesis is correct.

### The Solution: Hedge with Interest Rate Futures

**Best instruments:**
- **SOFR futures** (3-month) - closest match to equity financing
- **Fed Funds futures** - very short-term
- **Treasury futures** - for longer duration hedges

### Hedge Calculation

```
Your spread DV01: $2,500 per bp
SOFR futures DV01: $25 per contract per bp
Hedge ratio: $2,500 / $25 = 100 contracts
Action: BUY 100 SOFR futures (to offset short duration)
```

### After Hedging

| Scenario | Spread P&L | Hedge P&L | Net |
|----------|------------|-----------|-----|
| Rates +10bp | +$25,000 | -$25,000 | ~$0 |
| Rates -10bp | -$25,000 | +$25,000 | ~$0 |
| Rates flat | Earn carry | Small cost | Carry profit |

### Caveat: Basis Risk

SOFR and equity financing rates don't move exactly 1:1. The hedge captures ~80-90% of the rate risk. The remaining ~10-20% is "basis risk."

---

## Decision Framework: Which Strategy When

### Based on What You Have

| Your Situation | Best Strategy |
|----------------|---------------|
| Already own stocks | Cash & Carry + Box (full arb) |
| Have cash, want to lend | Buy stocks + sell futures |
| Need to borrow cash | Box spreads (cheapest) |
| Want leveraged rate exposure | Calendar futures |
| Want pure rate bet, no equity risk | Box spreads only |

### Based on Your View

| Your View | Strategy |
|-----------|----------|
| Rates will rise | Long near / Short far futures |
| Rates will fall | Short near / Long far futures |
| Rates stable, earn carry | Calendar spread (either direction based on curve) |
| No view, just want premium | Full arb (futures + box) |

### Based on Operational Capacity

| Capability | Recommended |
|------------|-------------|
| Can hold stocks + trade futures | Full Cash & Carry arb |
| Futures only | Calendar spreads |
| Options only | Box spreads |
| All instruments | Full forward arb |

---

## Summary Tables

### Strategy Comparison

| Strategy | Instruments | Rate Captured | Equity Exposure | Complexity | Capital |
|----------|-------------|---------------|-----------------|------------|---------|
| Cash & Carry | Stocks + Futures | SOFR + 30 bps | Hedged | Low | High |
| Calendar Spread | 2 Futures | Forward rate | Minimal | Low | Low |
| Box Spread | 4 Options | SOFR | Zero | Medium | Medium |
| Full Arb | All | 30 bps spread | Zero | High | High |
| Forward Arb | Cal Futures + Cal Box | Fwd spread | Zero | High | Medium |

### Rate Comparison

| Instrument | Rate | Best For |
|------------|------|----------|
| Box Spread | SOFR (~5.30%) | Borrowing |
| Equity Futures | SOFR + 20-30 bps | Lending |
| Direct Repo | SOFR + 30-50 bps | Large institutional |
| Margin | Prime + spread | Last resort |

### Risk Comparison

| Strategy | Rate Risk (DV01) | Equity Risk | Basis Risk | Operational Risk |
|----------|------------------|-------------|------------|------------------|
| Cash & Carry | Low | Hedged | Low | Medium |
| Calendar Spread | Medium | Low | Medium | Low |
| Box Spread | Low | Zero | Zero | Medium |
| Full Arb | Low | Zero | Medium | High |

---

## Quick Reference Formulas

### Implied Futures Rate
```
Rate = (Futures - Spot + Dividends) / Spot × (360 / Days)
```

### Calendar Spread Forward Rate
```
Forward Rate = (Far_Price - Near_Price × Time_Ratio) / Day_Count_Fraction
```

### DV01 of Calendar Spread
```
DV01 = Notional × (Period_Days / 360) × 0.0001
```

### Box Spread Implied Rate
```
Rate = ((Strike_Diff - Box_Price) / Box_Price) × (365 / Days_to_Expiry)
```

### Hedge Ratio
```
Contracts = Spread_DV01 / Hedge_Instrument_DV01
```

---

## Key Takeaways

1. **The equity premium (~30 bps) exists** because holding equities on your balance sheet carries risk that Treasuries don't.

2. **You can capture this premium** multiple ways: direct (hold stocks + sell futures) or synthetic (calendar spreads).

3. **Borrow cheap, lend rich**: Use box spreads to borrow (SOFR), use futures to lend (SOFR + spread).

4. **Calendar spreads are forward rate bets**, not direct balance sheet rental. You're paid for taking rate risk, not holding stocks.

5. **DV01 is your friend and enemy**: Understand it, measure it, hedge it if you want pure carry.

6. **Forward-starting versions exist** for both futures (calendar spreads) and boxes (jelly rolls).

7. **The full arb** combines all instruments to isolate the pure equity-SOFR spread.

---

*Document created: January 2026*
*For reference in Quarterback Trading Application*
