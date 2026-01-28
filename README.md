# 🏈 Quarterback Trading Application

**Cash & Carry / Reverse Cash & Carry Strategy Management System**

A Streamlit-based web application for managing S&P 500 AIR (Adjustable Interest Rate) Futures trading strategies.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.53-red)
![License](https://img.shields.io/badge/License-Proprietary-yellow)

---

## 📋 Overview

Quarterback is a trading strategy management tool designed to help traders monitor and manage:

- **Simple Carry**: Short rich futures + Long physical stocks + Borrow cash
- **Reverse Carry**: Long cheap futures + Short physical stocks + Lend cash
- **Calendar Spread**: Trade mispricing between two futures maturities

The application provides real-time tracking of:
- Basket P&L and performance
- Net equity exposure (hedge monitoring)
- Daily and accrued carry
- Corporate actions calendar
- Dividend events
- Trade lifecycle alerts

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ installed
- Fresh installation works with `py` launcher on Windows

### Installation

1. **Clone/download the project folder**

2. **Install dependencies:**
   ```bash
   py -m pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   py -m streamlit run app.py
   ```

4. **Open browser:**
   Navigate to `http://localhost:8501`

---

## 📁 Project Structure

```
Quarterback_v1/
├── app.py                      # Main entry point (Home Dashboard)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── modules/
│   ├── __init__.py
│   ├── data_loader.py          # Centralized data loading functions
│   └── calculations.py         # Centralized KPI/calculation functions
│
├── pages/
│   ├── __init__.py
│   ├── 1_📊_Basket_Detail.py   # Specific basket detail view
│   └── 2_📅_Calendar.py        # Calendar view with events
│
├── components/
│   ├── __init__.py
│   ├── theme.py                # Bloomberg-style theming
│   └── widgets.py              # Reusable UI widgets
│
├── data/
│   ├── Positions.csv           # Portfolio positions
│   ├── stockmarketdata.csv     # S&P 500 constituent data
│   └── corpactions.csv         # Corporate actions calendar
│
└── .streamlit/
    └── config.toml             # Streamlit configuration
```

---

## 📊 Application Views

### 1. Home Dashboard
- Portfolio-wide summary metrics
- Active alerts panel
- All baskets overview with key KPIs
- Quick navigation to basket details

### 2. Basket Detail View
- Whole basket summary widget
- Derivatives (Futures) widget
- Physical Shares widget
- Borrowing/Lending widget
- Upcoming corporate actions

### 3. Calendar View
- Timeline of upcoming events
- Filter by basket
- Filter by event type (Dividends, Lifecycle, Corporate Actions)
- Date range selection

---

## 🧮 Key Calculations

All calculations are centralized in `modules/calculations.py`:

| Function | Description |
|----------|-------------|
| `calculate_profit_and_loss()` | P&L in $ and basis points |
| `calculate_carry()` | Carry from rate differential |
| `calculate_daily_carry()` | Estimated daily carry |
| `calculate_accrued_carry()` | Carry accrued to date |
| `calculate_expected_carry_to_maturity()` | Expected remaining carry |
| `calculate_futures_equity_exposure()` | Equity exposure from futures |
| `calculate_physical_equity_exposure()` | Equity exposure from stocks |
| `calculate_net_equity_exposure()` | Net (should be ~0 if hedged) |
| `calculate_futures_theoretical_price()` | Fair value calculation |
| `calculate_shares_to_rebalance()` | Shares needed to match index |
| `calculate_dv01()` | Dollar value of 1bp rate move |

---

## 📥 Data Inputs

### Positions.csv
Portfolio positions with fields:
- `BASKET_ID`, `POSITION_ID`, `POSITION_TYPE`
- `STRATEGY_TYPE`, `LONG_SHORT`, `NOTIONAL_USD`
- `FINANCING_RATE_%`, `START_DATE`, `END_DATE`
- `PNL_USD`, `EQUITY_EXPOSURE_USD`

### stockmarketdata.csv
S&P 500 constituent data:
- `COMPANY`, `BLOOMBERG_TICKER`, `LOCAL_PRICE`
- `INDEX_WEIGHT`, `MARKET_CAP`, `IWF`
- `DIVIDEND`, `NET_DIVIDEND`

### corpactions.csv
Corporate actions calendar:
- `EFFECTIVE_DATE`, `CURRENT_TICKER`
- `ACTION_TYPE`, `DIVIDEND`
- `COMMENTS`, `STATUS`

---

## ☁️ Streamlit Cloud Deployment

### Step 1: Push to GitHub
1. Create a new GitHub repository
2. Push this folder to the repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/quarterback.git
   git push -u origin main
   ```

### Step 2: Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Set main file path: `app.py`
6. Click "Deploy"

Your app will be available at:
`https://YOUR_APP_NAME.streamlit.app`

---

## ⚙️ Configuration

### Alert Threshold
Net equity exposure threshold is set to $100,000 in `modules/calculations.py`:
```python
ALERT_THRESHOLD_USD = 100_000
```

### Theme Colors
Bloomberg-style colors can be customized in `components/theme.py`:
```python
COLORS = {
    'accent_orange': '#ff8c00',
    'accent_green': '#00d26a',
    'accent_red': '#ff4444',
    ...
}
```

---

## 🔮 Future Enhancements (Phase 2)

- [ ] TSX 60 AIR Futures support
- [ ] Live data feed integration
- [ ] Trade execution file output (Bloomberg format)
- [ ] Additional index support
- [ ] Real-time alerts/notifications

---

## 📄 License

Proprietary - Demo Version

© 2026 Quarterback Trading Systems
