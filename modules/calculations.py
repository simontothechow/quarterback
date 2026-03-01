"""
Quarterback Calculations Module
===============================
Centralized calculation functions for all KPIs and metrics.

All numerical calculations for the trading strategy are defined here as 
individual functions that can be tested and refined independently.

IMPORTANT: This module is critical to the functioning of the application.
Each function should be used consistently throughout the app.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Optional, Union, Tuple

# Constants
DAYS_IN_YEAR = 360  # Money market convention
BASIS_POINT = 0.0001  # 1 basis point = 0.01%
ALERT_THRESHOLD_USD = 100_000  # Net equity notional threshold for alerts
REBALANCING_THRESHOLD_SHARES = 1000  # Shares difference threshold for rebalancing alerts


def calculate_profit_and_loss(
    current_value: float,
    initial_value: float,
    notional: Optional[float] = None
) -> Tuple[float, float]:
    """
    Calculate Profit and Loss in dollar terms and basis points.
    
    Args:
        current_value: Current market value of the position
        initial_value: Initial value or cost basis
        notional: Notional amount for BPS calculation (uses initial_value if not provided)
    
    Returns:
        Tuple of (pnl_dollars, pnl_bps)
    """
    pnl_dollars = current_value - initial_value
    
    # Calculate PNL in basis points
    reference_notional = notional if notional is not None else abs(initial_value)
    if reference_notional != 0:
        pnl_bps = (pnl_dollars / reference_notional) * 10_000  # Convert to BPS
    else:
        pnl_bps = 0.0
    
    return pnl_dollars, pnl_bps


def calculate_carry(
    implied_rate: float,
    funding_rate: float,
    notional: float,
    days: int
) -> float:
    """
    Calculate carry (profit from rate differential) in dollar terms.
    
    Carry = (Implied Futures Financing Rate - Funding Rate) × Notional × Days / 360
    
    Args:
        implied_rate: Implied financing rate from futures (as decimal, e.g., 0.054 for 5.4%)
        funding_rate: Actual funding/borrowing rate (as decimal)
        notional: Notional amount in USD
        days: Number of days
    
    Returns:
        Carry amount in USD
    """
    rate_differential = implied_rate - funding_rate
    carry = rate_differential * abs(notional) * days / DAYS_IN_YEAR
    return carry


def calculate_daily_carry(
    implied_rate: float,
    funding_rate: float,
    notional: float
) -> float:
    """
    Calculate estimated daily carry.
    
    Args:
        implied_rate: Implied financing rate from futures (as decimal)
        funding_rate: Actual funding/borrowing rate (as decimal)
        notional: Notional amount in USD
    
    Returns:
        Daily carry amount in USD
    """
    return calculate_carry(implied_rate, funding_rate, notional, days=1)


def calculate_accrued_carry(
    implied_rate: float,
    funding_rate: float,
    notional: float,
    start_date: Union[datetime, date, str],
    as_of_date: Optional[Union[datetime, date]] = None
) -> float:
    """
    Calculate carry accrued to date from start date.
    
    Args:
        implied_rate: Implied financing rate from futures (as decimal)
        funding_rate: Actual funding/borrowing rate (as decimal)
        notional: Notional amount in USD
        start_date: Trade start date
        as_of_date: Date to calculate accrual to (defaults to today)
    
    Returns:
        Accrued carry in USD
    """
    if as_of_date is None:
        as_of_date = datetime.now().date()
    
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date).date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.date()
    
    days_elapsed = (as_of_date - start_date).days
    if days_elapsed < 0:
        days_elapsed = 0
    
    return calculate_carry(implied_rate, funding_rate, notional, days_elapsed)


def calculate_expected_carry_to_maturity(
    implied_rate: float,
    funding_rate: float,
    notional: float,
    end_date: Union[datetime, date, str],
    as_of_date: Optional[Union[datetime, date]] = None
) -> float:
    """
    Calculate expected carry from now to maturity.
    
    Args:
        implied_rate: Implied financing rate from futures (as decimal)
        funding_rate: Actual funding/borrowing rate (as decimal)
        notional: Notional amount in USD
        end_date: Trade/position end date (maturity)
        as_of_date: Current date (defaults to today)
    
    Returns:
        Expected carry to maturity in USD
    """
    if as_of_date is None:
        as_of_date = datetime.now().date()
    
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date).date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.date()
    
    days_remaining = (end_date - as_of_date).days
    if days_remaining < 0:
        days_remaining = 0
    
    return calculate_carry(implied_rate, funding_rate, notional, days_remaining)


def calculate_total_expected_carry(
    implied_rate: float,
    funding_rate: float,
    notional: float,
    start_date: Union[datetime, date, str],
    end_date: Union[datetime, date, str]
) -> float:
    """
    Calculate total expected carry for the full trade duration.
    
    Args:
        implied_rate: Implied financing rate from futures (as decimal)
        funding_rate: Actual funding/borrowing rate (as decimal)
        notional: Notional amount in USD
        start_date: Trade start date
        end_date: Trade end date (maturity)
    
    Returns:
        Total expected carry in USD
    """
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date).date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date).date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    total_days = (end_date - start_date).days
    if total_days < 0:
        total_days = 0
    
    return calculate_carry(implied_rate, funding_rate, notional, total_days)


def calculate_futures_equity_exposure(
    quantity: float,
    price: float,
    multiplier: float = 1.0
) -> float:
    """
    Calculate equity exposure from futures position.
    
    Args:
        quantity: Number of contracts (positive for long, negative for short)
        price: Futures price level
        multiplier: Contract multiplier (default 1 for notional-based)
    
    Returns:
        Equity exposure in USD
    """
    return quantity * price * multiplier


def calculate_physical_equity_exposure(
    market_value: float
) -> float:
    """
    Calculate equity exposure from physical stock positions.
    
    Args:
        market_value: Current market value of physical positions
    
    Returns:
        Equity exposure in USD (positive for long, negative for short)
    """
    return market_value


def calculate_net_equity_exposure(
    futures_exposure: float,
    physical_exposure: float
) -> float:
    """
    Calculate net equity exposure (should be close to zero for hedged basket).
    
    Args:
        futures_exposure: Equity exposure from futures
        physical_exposure: Equity exposure from physical stocks
    
    Returns:
        Net equity exposure in USD
    """
    return futures_exposure + physical_exposure


def calculate_long_futures_notional(positions_df: pd.DataFrame) -> float:
    """
    Calculate total notional for long futures positions.
    
    Args:
        positions_df: DataFrame with position data
    
    Returns:
        Total long futures notional in USD
    """
    mask = (positions_df['POSITION_TYPE'] == 'FUTURE') & \
           (positions_df['LONG_SHORT'] == 'LONG')
    
    if 'NOTIONAL_USD' in positions_df.columns:
        return positions_df.loc[mask, 'NOTIONAL_USD'].sum()
    return 0.0


def calculate_short_futures_notional(positions_df: pd.DataFrame) -> float:
    """
    Calculate total notional for short futures positions.
    
    Args:
        positions_df: DataFrame with position data
    
    Returns:
        Total short futures notional in USD (as positive number)
    """
    mask = (positions_df['POSITION_TYPE'] == 'FUTURE') & \
           (positions_df['LONG_SHORT'] == 'SHORT')
    
    if 'NOTIONAL_USD' in positions_df.columns:
        return abs(positions_df.loc[mask, 'NOTIONAL_USD'].sum())
    return 0.0


def calculate_futures_theoretical_price(
    spot_price: float,
    financing_rate: float,
    dividend_yield: float,
    days_to_maturity: int
) -> float:
    """
    Calculate theoretical fair value price for futures.
    
    Formula: F = S × (1 + (r - d) × T/360)
    
    Where:
        S = Spot price of underlying
        r = Financing rate (annualized, as decimal)
        d = Dividend yield (annualized, as decimal)
        T = Days to maturity
    
    Args:
        spot_price: Current spot price of underlying index
        financing_rate: Annualized financing rate (as decimal, e.g., 0.053 for 5.3%)
        dividend_yield: Annualized dividend yield (as decimal)
        days_to_maturity: Number of days until futures expiration
    
    Returns:
        Theoretical futures price
    """
    time_factor = days_to_maturity / DAYS_IN_YEAR
    cost_of_carry = financing_rate - dividend_yield
    theoretical_price = spot_price * (1 + cost_of_carry * time_factor)
    return theoretical_price


def calculate_days_to_maturity(
    maturity_date: Union[datetime, date, str],
    as_of_date: Optional[Union[datetime, date]] = None
) -> int:
    """
    Calculate number of days until maturity.
    
    Args:
        maturity_date: The maturity/expiration date
        as_of_date: Current date (defaults to today)
    
    Returns:
        Days to maturity (0 if already matured)
    """
    if as_of_date is None:
        as_of_date = datetime.now().date()
    
    if isinstance(maturity_date, str):
        maturity_date = pd.to_datetime(maturity_date).date()
    elif isinstance(maturity_date, datetime):
        maturity_date = maturity_date.date()
    
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.date()
    
    days = (maturity_date - as_of_date).days
    return max(0, days)


def calculate_shares_to_rebalance(
    current_weight: float,
    target_weight: float,
    portfolio_value: float,
    share_price: float
) -> float:
    """
    Calculate number of shares needed to rebalance to target weight.
    
    This function compares the current weight of a stock in the portfolio
    to the target weight (from S&P 500 index) and calculates the number
    of shares to buy or sell to match.
    
    Args:
        current_weight: Current weight in portfolio (as decimal)
        target_weight: Target weight from index (as decimal)
        portfolio_value: Total portfolio value in USD
        share_price: Current share price
    
    Returns:
        Number of shares to buy (positive) or sell (negative)
    """
    weight_difference = target_weight - current_weight
    value_difference = weight_difference * portfolio_value
    
    if share_price > 0:
        shares_to_trade = value_difference / share_price
    else:
        shares_to_trade = 0.0
    
    return shares_to_trade


def calculate_dv01(
    notional: float,
    days_to_maturity: int
) -> float:
    """
    Calculate DV01 (Dollar Value of 1 Basis Point).
    
    DV01 represents the change in position value for a 1 basis point
    move in the financing rate.
    
    Formula: DV01 = Notional × (T/360) × 0.0001
    
    Args:
        notional: Position notional in USD
        days_to_maturity: Days until maturity
    
    Returns:
        DV01 in USD
    """
    time_factor = days_to_maturity / DAYS_IN_YEAR
    dv01 = abs(notional) * time_factor * BASIS_POINT
    return dv01


def calculate_implied_financing_rate(
    futures_price: float,
    spot_price: float,
    dividend_yield: float,
    days_to_maturity: int
) -> float:
    """
    Calculate implied financing rate from futures price.
    
    Rearranging F = S × (1 + (r - d) × T/360):
    r = ((F/S - 1) × 360/T) + d
    
    Args:
        futures_price: Current futures price
        spot_price: Current spot price
        dividend_yield: Expected dividend yield (as decimal)
        days_to_maturity: Days to futures expiration
    
    Returns:
        Implied financing rate (as decimal)
    """
    if spot_price == 0 or days_to_maturity == 0:
        return 0.0
    
    price_ratio = futures_price / spot_price
    time_factor = DAYS_IN_YEAR / days_to_maturity
    implied_rate = ((price_ratio - 1) * time_factor) + dividend_yield
    
    return implied_rate


def check_hedge_alert(net_equity_exposure: float) -> bool:
    """
    Check if net equity exposure exceeds alert threshold.
    
    Args:
        net_equity_exposure: Net equity exposure in USD
    
    Returns:
        True if alert should be triggered
    """
    return abs(net_equity_exposure) > ALERT_THRESHOLD_USD


def calculate_basket_metrics(basket_positions: pd.DataFrame) -> dict:
    """
    Calculate all key metrics for a basket.
    
    Args:
        basket_positions: DataFrame with positions for a single basket
    
    Returns:
        Dictionary with all calculated metrics
    """
    # Initialize metrics
    metrics = {
        'total_equity_exposure': 0.0,
        'futures_equity_exposure': 0.0,
        'physical_equity_exposure': 0.0,
        'net_equity_exposure': 0.0,
        'long_futures_notional': 0.0,
        'short_futures_notional': 0.0,
        'total_notional': 0.0,
        'total_pnl_usd': 0.0,
        'total_pnl_bps': 0.0,
        'daily_carry': 0.0,
        'accrued_carry': 0.0,
        'expected_carry_to_maturity': 0.0,
        'total_dv01': 0.0,
        'hedge_alert': False,
        'start_date': None,
        'end_date': None,
    }
    
    if basket_positions.empty:
        return metrics
    
    # Calculate futures exposure
    futures_mask = basket_positions['POSITION_TYPE'] == 'FUTURE'
    futures_positions = basket_positions[futures_mask]
    
    if not futures_positions.empty:
        for _, pos in futures_positions.iterrows():
            exposure = pos.get('EQUITY_EXPOSURE_USD', 0) or 0
            metrics['futures_equity_exposure'] += exposure
            
            notional = pos.get('NOTIONAL_USD', 0) or 0
            if pos.get('LONG_SHORT') == 'LONG':
                metrics['long_futures_notional'] += abs(notional)
            else:
                metrics['short_futures_notional'] += abs(notional)
    
    # Calculate physical equity exposure (handle both EQUITY_BASKET and individual EQUITY positions)
    equity_mask = (basket_positions['POSITION_TYPE'] == 'EQUITY_BASKET') | \
                  (basket_positions['POSITION_TYPE'] == 'EQUITY')
    equity_positions = basket_positions[equity_mask]
    
    if not equity_positions.empty:
        for _, pos in equity_positions.iterrows():
            # Try EQUITY_EXPOSURE_USD first, then MARKET_VALUE_USD
            exposure = pos.get('EQUITY_EXPOSURE_USD', 0) or pos.get('MARKET_VALUE_USD', 0) or 0
            metrics['physical_equity_exposure'] += exposure
    
    # Net equity exposure
    metrics['net_equity_exposure'] = metrics['futures_equity_exposure'] + \
                                      metrics['physical_equity_exposure']
    
    # Total equity exposure (absolute)
    metrics['total_equity_exposure'] = abs(metrics['futures_equity_exposure']) + \
                                        abs(metrics['physical_equity_exposure'])
    
    # Total notional
    metrics['total_notional'] = metrics['long_futures_notional'] + \
                                 metrics['short_futures_notional']
    
    # PNL
    if 'PNL_USD' in basket_positions.columns:
        metrics['total_pnl_usd'] = basket_positions['PNL_USD'].sum()
        if metrics['total_notional'] > 0:
            metrics['total_pnl_bps'] = (metrics['total_pnl_usd'] / 
                                        metrics['total_notional']) * 10_000
    
    # Dates
    if 'START_DATE' in basket_positions.columns:
        start_dates = basket_positions['START_DATE'].dropna()
        if not start_dates.empty:
            metrics['start_date'] = start_dates.min()
    
    if 'END_DATE' in basket_positions.columns:
        end_dates = basket_positions['END_DATE'].dropna()
        if not end_dates.empty:
            metrics['end_date'] = end_dates.max()
    
    # Carry calculations (using average rates)
    if 'FINANCING_RATE_%' in basket_positions.columns:
        futures_rates = basket_positions.loc[futures_mask, 'FINANCING_RATE_%'].dropna()
        if not futures_rates.empty:
            implied_rate = futures_rates.mean() / 100  # Convert from percentage
            
            # Assume funding rate from borrowing positions
            borrow_mask = basket_positions['POSITION_TYPE'] == 'CASH_BORROW'
            borrow_rates = basket_positions.loc[borrow_mask, 'FINANCING_RATE_%'].dropna()
            funding_rate = borrow_rates.mean() / 100 if not borrow_rates.empty else 0.053
            
            notional = metrics['total_notional']
            if notional > 0 and metrics['start_date'] and metrics['end_date']:
                metrics['daily_carry'] = calculate_daily_carry(
                    implied_rate, funding_rate, notional
                )
                metrics['accrued_carry'] = calculate_accrued_carry(
                    implied_rate, funding_rate, notional, metrics['start_date']
                )
                metrics['expected_carry_to_maturity'] = calculate_expected_carry_to_maturity(
                    implied_rate, funding_rate, notional, metrics['end_date']
                )
    
    # DV01
    if metrics['end_date']:
        days_to_maturity = calculate_days_to_maturity(metrics['end_date'])
        metrics['total_dv01'] = calculate_dv01(metrics['total_notional'], days_to_maturity)
    
    # Hedge alert
    metrics['hedge_alert'] = check_hedge_alert(metrics['net_equity_exposure'])
    
    return metrics


def convert_to_bps(value: float, notional: float) -> float:
    """
    Convert dollar value to basis points.
    
    Args:
        value: Dollar value
        notional: Reference notional
    
    Returns:
        Value in basis points
    """
    if notional == 0:
        return 0.0
    return (value / abs(notional)) * 10_000


def calculate_trade_value(shares: Union[int, float], price: Union[int, float]) -> float:
    """
    Calculate trade market value (absolute dollars).
    
    Used by the Transaction page to recompute estimated value when the user edits shares.
    
    Args:
        shares: Number of shares (can be int or float; sign does not matter)
        price: Price per share
    
    Returns:
        Estimated trade value in USD (always non-negative)
    """
    try:
        return abs(float(shares)) * float(price)
    except (TypeError, ValueError):
        return 0.0


def format_currency(value: float, include_sign: bool = True) -> str:
    """
    Format a number as currency string.
    
    Args:
        value: Dollar value
        include_sign: Whether to include +/- sign
    
    Returns:
        Formatted currency string
    """
    if include_sign:
        sign = '+' if value >= 0 else ''
        return f"{sign}${value:,.0f}"
    return f"${abs(value):,.0f}"


def format_bps(value: float) -> str:
    """
    Format a number as basis points string.
    
    Args:
        value: Value in basis points
    
    Returns:
        Formatted BPS string
    """
    sign = '+' if value >= 0 else ''
    return f"{sign}{value:.1f} bps"


def calculate_rebalancing_needs(
    positions_df: pd.DataFrame,
    market_data_df: pd.DataFrame,
    threshold_shares: int = None
) -> pd.DataFrame:
    """
    Calculate rebalancing needs by comparing current positions to index weights.
    
    Supports all strategy types:
        - Simple Carry: SHORT futures + LONG physical → physical targets POSITIVE
        - Reverse Carry: LONG futures + SHORT physical → physical targets NEGATIVE
        - Calendar Spread: Net futures direction determines physical direction
    
    Calculation Logic:
        1. BASKET_NOTIONAL = abs(NOTIONAL_USD) from FUTURE positions
        2. NET_FUTURES_DIRECTION = determined from LONG/SHORT of futures
        3. PHYSICAL_DIRECTION = opposite of futures (to hedge)
        4. INDEX_WEIGHT = from stockmarketdata.csv (EXACT match on BLOOMBERG_TICKER)
        5. TARGET_SHARES = (BASKET_NOTIONAL × INDEX_WEIGHT / PRICE) × PHYSICAL_DIRECTION
        6. SHARES_DIFF = TARGET_SHARES - CURRENT_SHARES
    
    Args:
        positions_df: DataFrame with all basket positions (including FUTURE for notional)
        market_data_df: DataFrame with index weights
        threshold_shares: Minimum share difference to flag for rebalancing
    
    Returns:
        DataFrame with rebalancing analysis for each equity position
    """
    if threshold_shares is None:
        threshold_shares = REBALANCING_THRESHOLD_SHARES
    
    results = []
    
    # Get futures positions to determine notional and direction
    futures_mask = positions_df['POSITION_TYPE'] == 'FUTURE'
    futures_positions = positions_df[futures_mask]
    
    if not futures_positions.empty:
        # Calculate basket notional (sum of absolute notionals)
        basket_notional = abs(futures_positions['NOTIONAL_USD']).sum()
        
        # Determine NET futures direction
        # LONG futures = positive exposure, SHORT futures = negative exposure
        net_futures_exposure = 0
        for _, fut in futures_positions.iterrows():
            notional = fut.get('NOTIONAL_USD', 0)
            direction = fut.get('LONG_SHORT', '')
            if direction == 'LONG':
                net_futures_exposure += abs(notional)
            elif direction == 'SHORT':
                net_futures_exposure -= abs(notional)
        
        # Physical direction is OPPOSITE of net futures direction to hedge
        # If net futures LONG → physical should be SHORT (negative) → multiplier = -1
        # If net futures SHORT → physical should be LONG (positive) → multiplier = +1
        if net_futures_exposure > 0:
            physical_direction = -1  # Reverse Carry: LONG futures, SHORT physical
        else:
            physical_direction = +1  # Simple Carry: SHORT futures, LONG physical
    else:
        # No futures - fallback to sum of equity market values
        equity_mask = positions_df['POSITION_TYPE'] == 'EQUITY'
        basket_notional = abs(positions_df[equity_mask]['MARKET_VALUE_USD'].sum())
        physical_direction = +1  # Default to long
    
    # Filter for equity positions only
    equity_mask = positions_df['POSITION_TYPE'] == 'EQUITY'
    equity_positions = positions_df[equity_mask]
    
    if equity_positions.empty:
        return pd.DataFrame()
    
    # Build lookup dict for market data (EXACT match on BLOOMBERG_TICKER)
    # INDEX_WEIGHT in stockmarketdata.csv is already in decimal form (e.g., 0.002 = 0.2%)
    weight_lookup = {}
    if not market_data_df.empty and 'BLOOMBERG_TICKER' in market_data_df.columns:
        for _, row in market_data_df.iterrows():
            ticker = row['BLOOMBERG_TICKER']
            weight = row.get('INDEX_WEIGHT', 0)
            if pd.notna(ticker) and pd.notna(weight):
                weight_lookup[ticker] = float(weight)
    
    # Calculate rebalancing for each equity position
    for _, pos in equity_positions.iterrows():
        ticker = pos.get('UNDERLYING', '')
        current_shares = pos.get('QUANTITY', 0)
        price = pos.get('PRICE_OR_LEVEL', 0)
        market_value = pos.get('MARKET_VALUE_USD', 0)
        basket_id = pos.get('BASKET_ID', '')
        pnl = pos.get('PNL_USD', 0)
        if pd.isna(pnl):
            pnl = 0
        
        # EXACT match to get index weight
        index_weight = weight_lookup.get(ticker, 0)
        
        # Calculate target shares with correct direction
        if index_weight > 0 and price > 0 and basket_notional > 0:
            target_value = basket_notional * index_weight
            target_shares = (target_value / price) * physical_direction
            shares_diff = target_shares - current_shares
        else:
            target_shares = current_shares
            shares_diff = 0
        
        # Determine action based on shares_diff
        if shares_diff > 0:
            action = 'BUY'
        elif shares_diff < 0:
            action = 'SELL'
        else:
            action = 'NONE'
        
        # Flag if rebalancing needed
        needs_rebalancing = abs(shares_diff) >= threshold_shares
        
        results.append({
            'TICKER': ticker,
            'BASKET_ID': basket_id,
            'CURRENT_SHARES': current_shares,
            'TARGET_SHARES': target_shares,
            'SHARES_DIFF': shares_diff,
            'PRICE': price,
            'MARKET_VALUE_USD': market_value,
            'PNL_USD': pnl,
            'INDEX_WEIGHT': index_weight * 100,  # Convert to percentage for display
            'ACTION': action,
            'NEEDS_REBALANCING': needs_rebalancing,
            'TRADE_VALUE': abs(shares_diff * price),
        })
    
    return pd.DataFrame(results)


def get_rebalancing_alerts(
    positions_df: pd.DataFrame,
    market_data_df: pd.DataFrame,
    basket_id: str = None
) -> list:
    """
    Get list of rebalancing alerts for positions that need adjustment.
    
    Uses UPPERCASE keys consistent with the data model.
    
    Args:
        positions_df: DataFrame with position data
        market_data_df: DataFrame with market data
        basket_id: Optional filter for specific basket
    
    Returns:
        List of alert dictionaries with UPPERCASE keys:
        TICKER, ACTION, SHARES, MESSAGE, CURRENT_SHARES, TARGET_SHARES,
        PRICE, TRADE_VALUE, VALUE, BASKET_ID
    """
    alerts = []
    
    # Filter by basket if specified
    if basket_id:
        positions_df = positions_df[positions_df['BASKET_ID'] == basket_id]
    
    # Calculate rebalancing needs
    rebal_df = calculate_rebalancing_needs(positions_df, market_data_df)
    
    if rebal_df.empty:
        return alerts
    
    # Filter for positions that need rebalancing (use UPPERCASE column name)
    needs_rebal = rebal_df[rebal_df['NEEDS_REBALANCING'] == True]
    
    for _, row in needs_rebal.iterrows():
        shares_diff = abs(int(row['SHARES_DIFF']))
        action = row['ACTION']
        ticker = row['TICKER']
        
        # All UPPERCASE keys for consistency
        alert = {
            'TICKER': ticker,
            'ACTION': action,
            'SHARES': shares_diff,
            'MESSAGE': f"{ticker} – {shares_diff:,} share {action.title()} needed",
            'CURRENT_SHARES': row['CURRENT_SHARES'],
            'TARGET_SHARES': row['TARGET_SHARES'],
            'PRICE': row['PRICE'],
            'TRADE_VALUE': row['TRADE_VALUE'],
            'VALUE': row['TRADE_VALUE'],
            'BASKET_ID': row['BASKET_ID'],
            # Lowercase aliases for widget compatibility
            'ticker': ticker,
            'action': action,
            'shares': shares_diff,
            'message': f"{ticker} – {shares_diff:,} share {action.title()} needed",
            'price': row['PRICE'],
            'value': row['TRADE_VALUE'],
            'current_shares': row['CURRENT_SHARES'],
            'target_shares': row['TARGET_SHARES'],
            'basket_id': row['BASKET_ID'],
            'position_id': f"{row['BASKET_ID']}_{ticker.replace(' ', '_')}",
        }
        alerts.append(alert)
    
    return alerts


def calculate_equity_basket_summary(positions_df: pd.DataFrame, market_data_df: pd.DataFrame = None) -> dict:
    """
    Calculate summary statistics for the physical equity basket.
    
    Args:
        positions_df: DataFrame with equity positions
        market_data_df: Optional DataFrame with market data (for rebalancing alerts)
    
    Returns:
        Dictionary with summary metrics
    """
    # Filter for equity positions
    equity_mask = positions_df['POSITION_TYPE'] == 'EQUITY'
    equity_positions = positions_df[equity_mask]
    
    summary = {
        'total_positions': len(equity_positions),
        'position_count': len(equity_positions),
        'total_market_value': 0.0,
        'total_pnl': 0.0,
        'long_positions': 0,
        'short_positions': 0,
        'long_market_value': 0.0,
        'short_market_value': 0.0,
        'long_short': 'LONG',  # Default direction
        'alerts_count': 0,
    }
    
    if equity_positions.empty:
        return summary
    
    # Calculate totals
    if 'MARKET_VALUE_USD' in equity_positions.columns:
        summary['total_market_value'] = equity_positions['MARKET_VALUE_USD'].sum()
    
    if 'PNL_USD' in equity_positions.columns:
        pnl_values = equity_positions['PNL_USD'].fillna(0)
        summary['total_pnl'] = pnl_values.sum()
    
    # Long/short breakdown
    if 'LONG_SHORT' in equity_positions.columns:
        long_mask = equity_positions['LONG_SHORT'] == 'LONG'
        short_mask = equity_positions['LONG_SHORT'] == 'SHORT'
        
        summary['long_positions'] = int(long_mask.sum())
        summary['short_positions'] = int(short_mask.sum())
        summary['long_market_value'] = equity_positions.loc[long_mask, 'MARKET_VALUE_USD'].sum()
        summary['short_market_value'] = equity_positions.loc[short_mask, 'MARKET_VALUE_USD'].sum()
        
        # Determine overall direction based on majority of positions
        if summary['long_positions'] >= summary['short_positions']:
            summary['long_short'] = 'LONG'
        else:
            summary['long_short'] = 'SHORT'
    
    # Calculate rebalancing alerts count
    if market_data_df is not None and not market_data_df.empty:
        alerts = get_rebalancing_alerts(positions_df, market_data_df)
        summary['alerts_count'] = len(alerts)
    
    return summary


def calculate_stock_borrow_summary(positions_df: pd.DataFrame) -> dict:
    """
    Calculate summary statistics for stock borrow positions.
    
    Args:
        positions_df: DataFrame with positions including stock borrows
    
    Returns:
        Dictionary with summary metrics
    """
    # Filter for stock borrow positions
    borrow_mask = positions_df['POSITION_TYPE'] == 'STOCK_BORROW'
    borrow_positions = positions_df[borrow_mask]
    
    summary = {
        'total_positions': len(borrow_positions),
        'total_market_value': 0.0,
        'total_quantity': 0,
        'unique_tickers': 0,
    }
    
    if borrow_positions.empty:
        return summary
    
    # Calculate totals
    if 'MARKET_VALUE_USD' in borrow_positions.columns:
        summary['total_market_value'] = borrow_positions['MARKET_VALUE_USD'].sum()
    
    if 'QUANTITY' in borrow_positions.columns:
        summary['total_quantity'] = int(borrow_positions['QUANTITY'].sum())
    
    if 'UNDERLYING' in borrow_positions.columns:
        summary['unique_tickers'] = borrow_positions['UNDERLYING'].nunique()
    
    return summary


def calculate_corp_action_impact(event: dict, market_data_df: pd.DataFrame) -> dict:
    """
    Calculate the impact of a corporate action on index weight.
    
    Args:
        event: Dictionary with corporate action event data
        market_data_df: DataFrame with market data including INDEX_WEIGHT
    
    Returns:
        Dictionary with impact metrics
    """
    ticker = event.get('CURRENT_BLOOMBERG_TICKER', '')
    prior_shares = event.get('INDEX_SHARES_PRIOR_EVENTS', 0)
    post_shares = event.get('INDEX_SHARES_POST_EVENTS', 0)
    
    impact = {
        'ticker': ticker,
        'has_weight_change': False,
        'prior_shares': prior_shares if pd.notna(prior_shares) else 0,
        'post_shares': post_shares if pd.notna(post_shares) else 0,
        'shares_change_pct': 0.0,
        'current_index_weight': 0.0,
        'new_index_weight': 0.0,
        'current_price': 0.0,
    }
    
    # Check if there's a meaningful weight change
    if pd.isna(prior_shares) or pd.isna(post_shares):
        return impact
    
    prior_shares = float(prior_shares)
    post_shares = float(post_shares)
    
    if prior_shares == 0 or prior_shares == post_shares:
        return impact
    
    # Calculate percentage change
    shares_change_pct = ((post_shares - prior_shares) / prior_shares) * 100
    impact['shares_change_pct'] = shares_change_pct
    impact['has_weight_change'] = abs(shares_change_pct) > 0.01  # More than 0.01% change
    
    # Get current index weight and price from market data
    if ticker and not market_data_df.empty:
        market_match = market_data_df[market_data_df['BLOOMBERG_TICKER'] == ticker]
        if not market_match.empty:
            row = market_match.iloc[0]
            # INDEX_WEIGHT is already a decimal (e.g., 0.0063 for 0.63%)
            current_weight = row.get('INDEX_WEIGHT', 0)
            if pd.notna(current_weight):
                impact['current_index_weight'] = float(current_weight)
                # New weight is proportionally adjusted
                impact['new_index_weight'] = float(current_weight) * (1 + shares_change_pct / 100)
            
            current_price = row.get('LOCAL_PRICE', 0)
            if pd.notna(current_price):
                impact['current_price'] = float(current_price)
    
    return impact


def get_affected_baskets_for_ticker(ticker: str, positions_df: pd.DataFrame) -> list:
    """
    Find which baskets hold a given ticker.
    
    Args:
        ticker: Bloomberg ticker to search for
        positions_df: DataFrame with all positions
    
    Returns:
        List of basket IDs that hold this ticker
    """
    if positions_df.empty or not ticker:
        return []
    
    # Find positions with this ticker
    equity_positions = positions_df[
        (positions_df['POSITION_TYPE'] == 'EQUITY') & 
        (positions_df['UNDERLYING'] == ticker)
    ]
    
    if equity_positions.empty:
        return []
    
    return equity_positions['BASKET_ID'].unique().tolist()


def calculate_event_trade_recommendations(
    event: dict, 
    positions_df: pd.DataFrame, 
    market_data_df: pd.DataFrame
) -> list:
    """
    Calculate trade recommendations for a corporate action event.
    
    Args:
        event: Dictionary with corporate action event data
        positions_df: DataFrame with all positions
        market_data_df: DataFrame with market data
    
    Returns:
        List of trade recommendation dictionaries
    """
    recommendations = []
    
    # Get impact metrics
    impact = calculate_corp_action_impact(event, market_data_df)
    
    if not impact['has_weight_change']:
        return recommendations
    
    ticker = impact['ticker']
    new_index_weight = impact['new_index_weight']
    current_price = impact['current_price']
    
    # Find affected baskets
    affected_baskets = get_affected_baskets_for_ticker(ticker, positions_df)
    
    for basket_id in affected_baskets:
        basket_positions = positions_df[positions_df['BASKET_ID'] == basket_id]
        
        # Get current equity position for this ticker
        equity_pos = basket_positions[
            (basket_positions['POSITION_TYPE'] == 'EQUITY') & 
            (basket_positions['UNDERLYING'] == ticker)
        ]
        
        if equity_pos.empty:
            continue
        
        current_shares = equity_pos.iloc[0].get('QUANTITY', 0)
        if pd.isna(current_shares):
            current_shares = 0
        current_shares = float(current_shares)
        
        # Determine basket notional and direction from futures positions
        futures_positions = basket_positions[basket_positions['POSITION_TYPE'] == 'FUTURE']
        
        if futures_positions.empty:
            continue
        
        # Calculate net futures exposure
        net_futures_exposure = 0.0
        for _, fut in futures_positions.iterrows():
            notional = fut.get('NOTIONAL_USD', 0)
            if pd.isna(notional):
                notional = 0
            notional = abs(float(notional))
            long_short = fut.get('LONG_SHORT', '')
            if long_short == 'LONG':
                net_futures_exposure += notional
            else:
                net_futures_exposure -= notional
        
        basket_notional = abs(net_futures_exposure)
        
        # Determine physical direction multiplier
        # Long futures -> Short physical (multiplier = -1)
        # Short futures -> Long physical (multiplier = 1)
        if net_futures_exposure > 0:
            physical_direction = -1
            strategy_type = 'SIMPLE_CARRY'  # Long future, short physical
        else:
            physical_direction = 1
            strategy_type = 'REVERSE_CARRY'  # Short future, long physical
        
        # Calculate target shares
        if new_index_weight > 0 and current_price > 0 and basket_notional > 0:
            target_value = basket_notional * new_index_weight
            target_shares = (target_value / current_price) * physical_direction
        else:
            target_shares = 0  # If index weight becomes 0, target 0 shares
        
        shares_diff = target_shares - current_shares
        
        # Determine trade action
        action = 'NONE'
        if abs(shares_diff) >= 1:  # At least 1 share difference
            if shares_diff > 0:
                action = 'BUY'
            else:
                action = 'SELL'
        
        trade_value = abs(shares_diff * current_price)
        
        recommendations.append({
            'basket_id': basket_id,
            'ticker': ticker,
            'strategy_type': strategy_type,
            'current_shares': int(current_shares),
            'target_shares': int(round(target_shares)),
            'shares_diff': int(round(abs(shares_diff))),
            'action': action,
            'trade_value': trade_value,
            'price': current_price,
            'index_weight_change_pct': impact['shares_change_pct'],
            'current_index_weight': impact['current_index_weight'],
            'new_index_weight': impact['new_index_weight'],
        })
    
    return recommendations


# =============================================================================
# UNWIND / RESIZE CALCULATION FUNCTIONS
# =============================================================================

# SPX AIR Futures contract multiplier
SPX_FUTURES_MULTIPLIER = 25


def calculate_futures_contracts_from_notional(
    notional: float,
    futures_price: float,
    multiplier: float = SPX_FUTURES_MULTIPLIER
) -> float:
    """
    Calculate number of futures contracts from a notional amount.
    
    Formula: contracts = notional / (futures_price × multiplier)
    
    Args:
        notional: Target notional in USD (positive for long, negative for short)
        futures_price: Current futures price level
        multiplier: Contract multiplier (default 25 for SPX AIR)
    
    Returns:
        Number of contracts (positive for long, negative for short)
    """
    if futures_price <= 0 or multiplier <= 0:
        return 0.0
    
    contracts = notional / (futures_price * multiplier)
    return contracts


def calculate_notional_from_contracts(
    contracts: float,
    futures_price: float,
    multiplier: float = SPX_FUTURES_MULTIPLIER
) -> float:
    """
    Calculate notional amount from number of futures contracts.
    
    Formula: notional = contracts × futures_price × multiplier
    
    Args:
        contracts: Number of contracts (positive for long, negative for short)
        futures_price: Current futures price level
        multiplier: Contract multiplier (default 25 for SPX AIR)
    
    Returns:
        Notional in USD
    """
    return contracts * futures_price * multiplier


def calculate_unwind_trades_futures(
    positions_df: pd.DataFrame,
    basket_id: str
) -> list:
    """
    Calculate trades to fully unwind all futures positions in a basket.
    
    Unwind = opposite direction trade to close position.
    
    Args:
        positions_df: DataFrame with all positions
        basket_id: Basket identifier
    
    Returns:
        List of trade dictionaries with: ticker, action, contracts, notional, price
    """
    trades = []
    
    futures_mask = (positions_df['BASKET_ID'] == basket_id) & \
                   (positions_df['POSITION_TYPE'] == 'FUTURE')
    futures_positions = positions_df[futures_mask]
    
    for _, pos in futures_positions.iterrows():
        current_notional = pos.get('NOTIONAL_USD', 0) or 0
        current_quantity = pos.get('QUANTITY', 0) or 0
        price = pos.get('PRICE_OR_LEVEL', 0) or 0
        direction = pos.get('LONG_SHORT', '')
        contract_month = pos.get('CONTRACT_MONTH', '')
        instrument = pos.get('INSTRUMENT_NAME', 'SPX Futures')
        
        # Unwind = flip the sign
        unwind_notional = -1 * current_notional
        unwind_contracts = -1 * current_quantity
        
        # Determine action based on unwind direction
        if unwind_notional > 0:
            action = 'BUY'
        elif unwind_notional < 0:
            action = 'SELL'
        else:
            action = 'NONE'
        
        trades.append({
            'position_id': pos.get('POSITION_ID', ''),
            'instrument': instrument,
            'contract_month': contract_month,
            'ticker': f"SPX {contract_month}",
            'action': action,
            'contracts': int(round(abs(unwind_contracts))),
            'contracts_signed': int(round(unwind_contracts)),
            'notional': unwind_notional,
            'price': price,
            'current_notional': current_notional,
            'current_contracts': int(current_quantity),
            'current_direction': direction,
            'basket_id': basket_id,
            'position_type': 'FUTURE',
        })
    
    return trades


def calculate_resize_trades_futures(
    positions_df: pd.DataFrame,
    basket_id: str,
    transaction_notional: float
) -> list:
    """
    Calculate trades to resize futures positions by a given notional amount.
    
    Transaction notional:
        - Positive = buying (going more long / reducing short)
        - Negative = selling (going more short / reducing long)
    
    Args:
        positions_df: DataFrame with all positions
        basket_id: Basket identifier
        transaction_notional: The notional change to apply (signed)
    
    Returns:
        List of trade dictionaries
    """
    trades = []
    
    futures_mask = (positions_df['BASKET_ID'] == basket_id) & \
                   (positions_df['POSITION_TYPE'] == 'FUTURE')
    futures_positions = positions_df[futures_mask]
    
    # If multiple futures positions, split proportionally by current notional
    total_notional = abs(futures_positions['NOTIONAL_USD'].sum())
    
    for _, pos in futures_positions.iterrows():
        current_notional = pos.get('NOTIONAL_USD', 0) or 0
        price = pos.get('PRICE_OR_LEVEL', 0) or 0
        direction = pos.get('LONG_SHORT', '')
        contract_month = pos.get('CONTRACT_MONTH', '')
        instrument = pos.get('INSTRUMENT_NAME', 'SPX Futures')
        current_quantity = pos.get('QUANTITY', 0) or 0
        
        # Proportional allocation if multiple futures
        if total_notional > 0 and len(futures_positions) > 1:
            proportion = abs(current_notional) / total_notional
            pos_transaction_notional = transaction_notional * proportion
        else:
            pos_transaction_notional = transaction_notional
        
        # Calculate contracts from notional
        transaction_contracts = calculate_futures_contracts_from_notional(
            pos_transaction_notional, price
        )
        
        # Determine action
        if pos_transaction_notional > 0:
            action = 'BUY'
        elif pos_transaction_notional < 0:
            action = 'SELL'
        else:
            action = 'NONE'
        
        # Calculate new position
        new_notional = current_notional + pos_transaction_notional
        new_contracts = current_quantity + transaction_contracts
        
        trades.append({
            'position_id': pos.get('POSITION_ID', ''),
            'instrument': instrument,
            'contract_month': contract_month,
            'ticker': f"SPX {contract_month}",
            'action': action,
            'contracts': int(round(abs(transaction_contracts))),
            'contracts_signed': int(round(transaction_contracts)),
            'notional': pos_transaction_notional,
            'price': price,
            'current_notional': current_notional,
            'current_contracts': int(current_quantity),
            'current_direction': direction,
            'new_notional': new_notional,
            'new_contracts': int(round(new_contracts)),
            'basket_id': basket_id,
            'position_type': 'FUTURE',
        })
    
    return trades


def calculate_unwind_trades_cash(
    positions_df: pd.DataFrame,
    basket_id: str
) -> list:
    """
    Calculate trades to fully unwind cash borrow/lend positions.
    
    Cash Borrow: negative notional (owe money) → unwind with positive (repay)
    Cash Lend: positive notional (owed money) → unwind with negative (recall)
    
    Args:
        positions_df: DataFrame with all positions
        basket_id: Basket identifier
    
    Returns:
        List of trade dictionaries
    """
    trades = []
    
    cash_mask = (positions_df['BASKET_ID'] == basket_id) & \
                (positions_df['POSITION_TYPE'].isin(['CASH_BORROW', 'CASH_LEND']))
    cash_positions = positions_df[cash_mask]
    
    for _, pos in cash_positions.iterrows():
        pos_type = pos.get('POSITION_TYPE', '')
        current_notional = pos.get('NOTIONAL_USD', 0) or 0
        rate = pos.get('FINANCING_RATE_%', 0) or 0
        counterparty = pos.get('EXCHANGE_OR_COUNTERPARTY', 'N/A')
        
        # Unwind = flip the sign
        unwind_notional = -1 * current_notional
        
        # Determine action
        if pos_type == 'CASH_BORROW':
            action = 'REPAY' if unwind_notional > 0 else 'BORROW'
        else:  # CASH_LEND
            action = 'RECALL' if unwind_notional < 0 else 'LEND'
        
        trades.append({
            'position_id': pos.get('POSITION_ID', ''),
            'position_type': pos_type,
            'ticker': 'Cash',
            'action': action,
            'notional': unwind_notional,
            'current_notional': current_notional,
            'new_notional': 0,
            'rate': rate,
            'counterparty': counterparty,
            'basket_id': basket_id,
        })
    
    return trades


def calculate_resize_trades_cash(
    positions_df: pd.DataFrame,
    basket_id: str,
    transaction_notional: float
) -> list:
    """
    Calculate trades to resize cash borrow/lend positions.
    
    For Cash Borrow (negative position):
        - Positive transaction = repay some/borrow less
        - Negative transaction = borrow more
    
    For Cash Lend (positive position):
        - Positive transaction = lend more
        - Negative transaction = recall some
    
    Args:
        positions_df: DataFrame with all positions
        basket_id: Basket identifier
        transaction_notional: The notional change to apply (signed)
    
    Returns:
        List of trade dictionaries
    """
    trades = []
    
    cash_mask = (positions_df['BASKET_ID'] == basket_id) & \
                (positions_df['POSITION_TYPE'].isin(['CASH_BORROW', 'CASH_LEND']))
    cash_positions = positions_df[cash_mask]
    
    for _, pos in cash_positions.iterrows():
        pos_type = pos.get('POSITION_TYPE', '')
        current_notional = pos.get('NOTIONAL_USD', 0) or 0
        rate = pos.get('FINANCING_RATE_%', 0) or 0
        counterparty = pos.get('EXCHANGE_OR_COUNTERPARTY', 'N/A')
        
        new_notional = current_notional + transaction_notional
        
        # Determine action
        if pos_type == 'CASH_BORROW':
            action = 'REPAY' if transaction_notional > 0 else 'BORROW'
        else:  # CASH_LEND
            action = 'LEND' if transaction_notional > 0 else 'RECALL'
        
        trades.append({
            'position_id': pos.get('POSITION_ID', ''),
            'position_type': pos_type,
            'ticker': 'Cash',
            'action': action,
            'notional': transaction_notional,
            'current_notional': current_notional,
            'new_notional': new_notional,
            'rate': rate,
            'counterparty': counterparty,
            'basket_id': basket_id,
        })
    
    return trades


def calculate_unwind_trades_stock_borrow(
    positions_df: pd.DataFrame,
    basket_id: str
) -> list:
    """
    Calculate trades to fully unwind stock borrow positions.
    
    Stock Borrow: positive notional (borrowed shares) → unwind with negative (return)
    
    Args:
        positions_df: DataFrame with all positions
        basket_id: Basket identifier
    
    Returns:
        List of trade dictionaries
    """
    trades = []
    
    borrow_mask = (positions_df['BASKET_ID'] == basket_id) & \
                  (positions_df['POSITION_TYPE'] == 'STOCK_BORROW')
    borrow_positions = positions_df[borrow_mask]
    
    # Get aggregate info
    total_market_value = borrow_positions['MARKET_VALUE_USD'].sum() if not borrow_positions.empty else 0
    position_count = len(borrow_positions)
    
    if borrow_positions.empty:
        return trades
    
    # Get rate and counterparty from first position (typically same for all)
    first_pos = borrow_positions.iloc[0]
    rate = first_pos.get('FINANCING_RATE_%', 0) or 0
    counterparty = first_pos.get('EXCHANGE_OR_COUNTERPARTY', 'N/A')
    
    # Return all borrowed shares (aggregate level)
    unwind_notional = -1 * abs(total_market_value)
    
    trades.append({
        'position_id': 'STOCK_BORROW_AGGREGATE',
        'position_type': 'STOCK_BORROW',
        'ticker': 'Stock Borrow (Aggregate)',
        'action': 'RETURN',
        'notional': unwind_notional,
        'current_notional': total_market_value,
        'new_notional': 0,
        'position_count': position_count,
        'rate': rate,
        'counterparty': counterparty,
        'basket_id': basket_id,
    })
    
    return trades


def calculate_resize_trades_stock_borrow(
    positions_df: pd.DataFrame,
    basket_id: str,
    transaction_notional: float
) -> list:
    """
    Calculate trades to resize stock borrow positions.
    
    Positive transaction = borrow more shares
    Negative transaction = return some shares
    
    Args:
        positions_df: DataFrame with all positions
        basket_id: Basket identifier
        transaction_notional: The notional change to apply (signed)
    
    Returns:
        List of trade dictionaries
    """
    trades = []
    
    borrow_mask = (positions_df['BASKET_ID'] == basket_id) & \
                  (positions_df['POSITION_TYPE'] == 'STOCK_BORROW')
    borrow_positions = positions_df[borrow_mask]
    
    if borrow_positions.empty:
        return trades
    
    total_market_value = borrow_positions['MARKET_VALUE_USD'].sum()
    position_count = len(borrow_positions)
    
    first_pos = borrow_positions.iloc[0]
    rate = first_pos.get('FINANCING_RATE_%', 0) or 0
    counterparty = first_pos.get('EXCHANGE_OR_COUNTERPARTY', 'N/A')
    
    new_notional = total_market_value + transaction_notional
    
    action = 'BORROW' if transaction_notional > 0 else 'RETURN'
    
    trades.append({
        'position_id': 'STOCK_BORROW_AGGREGATE',
        'position_type': 'STOCK_BORROW',
        'ticker': 'Stock Borrow (Aggregate)',
        'action': action,
        'notional': transaction_notional,
        'current_notional': total_market_value,
        'new_notional': new_notional,
        'position_count': position_count,
        'rate': rate,
        'counterparty': counterparty,
        'basket_id': basket_id,
    })
    
    return trades


def calculate_equity_trades_for_notional(
    positions_df: pd.DataFrame,
    market_data_df: pd.DataFrame,
    basket_id: str,
    transaction_notional: float
) -> pd.DataFrame:
    """
    Calculate per-stock trades to achieve a given notional change in equity basket.
    
    Uses index weights from market data to proportionally allocate the notional
    across all S&P 500 constituents.
    
    Transaction notional:
        - Positive = buying shares (going more long / reducing short)
        - Negative = selling shares (going more short / reducing long)
    
    Args:
        positions_df: DataFrame with all positions
        market_data_df: DataFrame with index weights (stockmarketdata.csv)
        basket_id: Basket identifier
        transaction_notional: Total notional change to apply (signed)
    
    Returns:
        DataFrame with columns:
            TICKER, COMPANY, CURRENT_SHARES, CURRENT_MARKET_VALUE,
            TRANSACTION_VALUE, SHARES_TRANSACTED, SHARES_AFTER, MARKET_VALUE_AFTER
    """
    results = []
    
    # Get current equity positions
    equity_mask = (positions_df['BASKET_ID'] == basket_id) & \
                  (positions_df['POSITION_TYPE'] == 'EQUITY')
    equity_positions = positions_df[equity_mask]
    
    # Build lookup for current positions
    current_positions = {}
    for _, pos in equity_positions.iterrows():
        ticker = pos.get('UNDERLYING', '')
        current_positions[ticker] = {
            'shares': pos.get('QUANTITY', 0) or 0,
            'market_value': pos.get('MARKET_VALUE_USD', 0) or 0,
            'price': pos.get('PRICE_OR_LEVEL', 0) or 0,
        }
    
    # Build lookup for market data
    market_lookup = {}
    if not market_data_df.empty and 'BLOOMBERG_TICKER' in market_data_df.columns:
        for _, row in market_data_df.iterrows():
            ticker = row.get('BLOOMBERG_TICKER', '')
            if pd.notna(ticker):
                market_lookup[ticker] = {
                    'company': row.get('COMPANY', ''),
                    'price': row.get('LOCAL_PRICE', 0) or 0,
                    'index_weight': row.get('INDEX_WEIGHT', 0) or 0,
                }
    
    # Calculate trades for each stock in index
    for ticker, mkt_data in market_lookup.items():
        index_weight = mkt_data['index_weight']
        price = mkt_data['price']
        company = mkt_data['company']
        
        if index_weight <= 0 or price <= 0:
            continue
        
        # Get current position (may not exist)
        current = current_positions.get(ticker, {'shares': 0, 'market_value': 0, 'price': price})
        current_shares = current['shares']
        current_market_value = current['market_value']
        
        # Calculate transaction for this stock
        transaction_value = transaction_notional * index_weight
        shares_transacted = transaction_value / price
        
        # Calculate post-transaction state
        shares_after = current_shares + shares_transacted
        market_value_after = shares_after * price
        
        # Determine action
        if shares_transacted > 0:
            action = 'BUY'
        elif shares_transacted < 0:
            action = 'SELL'
        else:
            action = 'NONE'
        
        results.append({
            'TICKER': ticker,
            'COMPANY': company,
            'CURRENT_SHARES': current_shares,
            'CURRENT_MARKET_VALUE': current_market_value,
            'PRICE': price,
            'INDEX_WEIGHT': index_weight,
            'TRANSACTION_VALUE': transaction_value,
            'SHARES_TRANSACTED': shares_transacted,
            'SHARES_AFTER': shares_after,
            'MARKET_VALUE_AFTER': market_value_after,
            'ACTION': action,
        })
    
    return pd.DataFrame(results)


def calculate_unwind_trades_equities(
    positions_df: pd.DataFrame,
    market_data_df: pd.DataFrame,
    basket_id: str
) -> pd.DataFrame:
    """
    Calculate trades to fully unwind all equity positions in a basket.
    
    For each position, the unwind trade is the opposite of current holdings:
        - Long 100 shares → Sell 100 shares
        - Short 100 shares → Buy 100 shares
    
    Args:
        positions_df: DataFrame with all positions
        market_data_df: DataFrame with market data (for company names)
        basket_id: Basket identifier
    
    Returns:
        DataFrame with trade details per stock
    """
    results = []
    
    # Get current equity positions
    equity_mask = (positions_df['BASKET_ID'] == basket_id) & \
                  (positions_df['POSITION_TYPE'] == 'EQUITY')
    equity_positions = positions_df[equity_mask]
    
    # Company name lookup
    company_lookup = {}
    if not market_data_df.empty and 'BLOOMBERG_TICKER' in market_data_df.columns:
        for _, row in market_data_df.iterrows():
            ticker = row.get('BLOOMBERG_TICKER', '')
            if pd.notna(ticker):
                company_lookup[ticker] = row.get('COMPANY', '')
    
    for _, pos in equity_positions.iterrows():
        ticker = pos.get('UNDERLYING', '')
        current_shares = pos.get('QUANTITY', 0) or 0
        current_market_value = pos.get('MARKET_VALUE_USD', 0) or 0
        price = pos.get('PRICE_OR_LEVEL', 0) or 0
        
        # Unwind = flip the sign
        shares_transacted = -1 * current_shares
        transaction_value = shares_transacted * price if price > 0 else -1 * current_market_value
        
        # Determine action
        if shares_transacted > 0:
            action = 'BUY'
        elif shares_transacted < 0:
            action = 'SELL'
        else:
            action = 'NONE'
        
        results.append({
            'TICKER': ticker,
            'COMPANY': company_lookup.get(ticker, ''),
            'CURRENT_SHARES': current_shares,
            'CURRENT_MARKET_VALUE': current_market_value,
            'PRICE': price,
            'INDEX_WEIGHT': 0,  # Not used for unwind
            'TRANSACTION_VALUE': transaction_value,
            'SHARES_TRANSACTED': shares_transacted,
            'SHARES_AFTER': 0,
            'MARKET_VALUE_AFTER': 0,
            'ACTION': action,
        })
    
    return pd.DataFrame(results)


def calculate_basket_component_totals(
    positions_df: pd.DataFrame,
    basket_id: str
) -> dict:
    """
    Calculate current total notional/market value for each component type in a basket.
    
    Args:
        positions_df: DataFrame with all positions
        basket_id: Basket identifier
    
    Returns:
        Dictionary with totals for each component type
    """
    basket_mask = positions_df['BASKET_ID'] == basket_id
    basket_positions = positions_df[basket_mask]
    
    totals = {
        'futures_notional': 0.0,
        'futures_contracts': 0,
        'cash_borrow_notional': 0.0,
        'cash_lend_notional': 0.0,
        'stock_borrow_notional': 0.0,
        'equity_market_value': 0.0,
        'equity_position_count': 0,
        'has_futures': False,
        'has_cash_borrow': False,
        'has_cash_lend': False,
        'has_stock_borrow': False,
        'has_equities': False,
    }
    
    for _, pos in basket_positions.iterrows():
        pos_type = pos.get('POSITION_TYPE', '')
        notional = pos.get('NOTIONAL_USD', 0) or 0
        market_value = pos.get('MARKET_VALUE_USD', 0) or 0
        quantity = pos.get('QUANTITY', 0) or 0
        
        if pos_type == 'FUTURE':
            totals['futures_notional'] += notional
            totals['futures_contracts'] += int(quantity) if pd.notna(quantity) else 0
            totals['has_futures'] = True
        elif pos_type == 'CASH_BORROW':
            totals['cash_borrow_notional'] += notional
            totals['has_cash_borrow'] = True
        elif pos_type == 'CASH_LEND':
            totals['cash_lend_notional'] += notional
            totals['has_cash_lend'] = True
        elif pos_type == 'STOCK_BORROW':
            totals['stock_borrow_notional'] += market_value
            totals['has_stock_borrow'] = True
        elif pos_type == 'EQUITY':
            totals['equity_market_value'] += market_value
            totals['equity_position_count'] += 1
            totals['has_equities'] = True
    
    return totals


def calculate_basket_unwind_all(
    positions_df: pd.DataFrame,
    market_data_df: pd.DataFrame,
    basket_id: str
) -> dict:
    """
    Calculate all trades needed to fully unwind a basket.
    
    Returns separate trade lists for each component type.
    
    Args:
        positions_df: DataFrame with all positions
        market_data_df: DataFrame with market data
        basket_id: Basket identifier
    
    Returns:
        Dictionary with trade lists:
            - futures_trades: list
            - cash_trades: list
            - stock_borrow_trades: list
            - equity_trades: DataFrame
    """
    return {
        'futures_trades': calculate_unwind_trades_futures(positions_df, basket_id),
        'cash_trades': calculate_unwind_trades_cash(positions_df, basket_id),
        'stock_borrow_trades': calculate_unwind_trades_stock_borrow(positions_df, basket_id),
        'equity_trades': calculate_unwind_trades_equities(positions_df, market_data_df, basket_id),
        'basket_id': basket_id,
        'mode': 'unwind',
    }


def calculate_basket_resize_all(
    positions_df: pd.DataFrame,
    market_data_df: pd.DataFrame,
    basket_id: str,
    transaction_notional: float
) -> dict:
    """
    Calculate all trades needed to resize a basket by a given notional.
    
    All components are resized by the same notional amount to maintain
    the hedge relationship.
    
    Args:
        positions_df: DataFrame with all positions
        market_data_df: DataFrame with market data
        basket_id: Basket identifier
        transaction_notional: The notional change to apply (signed)
    
    Returns:
        Dictionary with trade lists for each component type
    """
    return {
        'futures_trades': calculate_resize_trades_futures(positions_df, basket_id, transaction_notional),
        'cash_trades': calculate_resize_trades_cash(positions_df, basket_id, transaction_notional),
        'stock_borrow_trades': calculate_resize_trades_stock_borrow(positions_df, basket_id, transaction_notional),
        'equity_trades': calculate_equity_trades_for_notional(
            positions_df, market_data_df, basket_id, transaction_notional
        ),
        'basket_id': basket_id,
        'mode': 'resize',
        'transaction_notional': transaction_notional,
    }


def calculate_equivalent_futures_contracts(
    notional: float,
    positions_df: pd.DataFrame,
    basket_id: str
) -> float:
    """
    Calculate how many futures contracts are equivalent to a given notional.
    
    Uses the current futures price from the basket's futures positions.
    This is a reference calculation for display purposes.
    
    Args:
        notional: Notional amount in USD
        positions_df: DataFrame with all positions
        basket_id: Basket identifier
    
    Returns:
        Number of equivalent futures contracts
    """
    # Get futures price from basket
    futures_mask = (positions_df['BASKET_ID'] == basket_id) & \
                   (positions_df['POSITION_TYPE'] == 'FUTURE')
    futures_positions = positions_df[futures_mask]
    
    if futures_positions.empty:
        # Use a default SPX price if no futures in basket
        default_price = 5300
        return calculate_futures_contracts_from_notional(notional, default_price)
    
    # Use average price if multiple futures
    avg_price = futures_positions['PRICE_OR_LEVEL'].mean()
    
    return calculate_futures_contracts_from_notional(notional, avg_price)


def calculate_basket_calendar_trade_recommendations(
    basket_id: str,
    positions_df: pd.DataFrame,
    corp_actions_df: pd.DataFrame,
    market_data_df: pd.DataFrame,
    days_back: int = 120,
    days_forward: int = 365,
    max_events: int = 25,
) -> list:
    """
    For a given basket, find relevant corporate actions and produce actionable trade recommendations.
    
    This is used by the Basket Detail "Calendar Events" widget to unify calendar + basket context.
    In the demo, these recommendations are assumed to be forward-starting and use the event
    effective date as the execution date.
    
    Notes:
    - Currently focuses on corporate actions with index share changes (i.e., those that generate
      trade recommendations via calculate_event_trade_recommendations()).
    - Filters to tickers actually held in the basket's EQUITY positions.
    
    Args:
        basket_id: Basket identifier (e.g., "Basket1")
        positions_df: Full positions dataframe (all baskets)
        corp_actions_df: Corporate actions dataframe
        market_data_df: Market data dataframe (for COMPANY, PRICE, weights)
        days_back: Include events this many days before today (demo-friendly "pretend date" window)
        days_forward: Include events this many days after today
        max_events: Max number of actionable recommendations to return
    
    Returns:
        List of dictionaries with event + trade recommendation fields.
    """
    if (
        positions_df is None
        or positions_df.empty
        or corp_actions_df is None
        or corp_actions_df.empty
        or not basket_id
    ):
        return []

    # Basket tickers (only positions actually held)
    basket_positions = positions_df[positions_df["BASKET_ID"] == basket_id]
    basket_equities = basket_positions[basket_positions["POSITION_TYPE"] == "EQUITY"]
    if basket_equities.empty:
        return []

    tickers = (
        basket_equities.get("UNDERLYING", pd.Series([], dtype=str))
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    if not tickers:
        return []

    # Company lookup (optional)
    company_lookup = {}
    if market_data_df is not None and not market_data_df.empty:
        if "BLOOMBERG_TICKER" in market_data_df.columns and "COMPANY" in market_data_df.columns:
            for _, r in market_data_df[["BLOOMBERG_TICKER", "COMPANY"]].dropna().iterrows():
                company_lookup[str(r["BLOOMBERG_TICKER"])] = str(r["COMPANY"])

    # Time window (demo-friendly; includes some recent past so Dec 2025 shows up in Feb 2026)
    today = datetime.now().date()
    start_date = today - timedelta(days=days_back)
    end_date = today + timedelta(days=days_forward)

    df = corp_actions_df.copy()
    if "EFFECTIVE_DATE" not in df.columns:
        return []

    df["EFFECTIVE_DATE"] = pd.to_datetime(df["EFFECTIVE_DATE"], errors="coerce")
    df = df[df["EFFECTIVE_DATE"].notna()]
    df = df[(df["EFFECTIVE_DATE"].dt.date >= start_date) & (df["EFFECTIVE_DATE"].dt.date <= end_date)]

    # Only events for tickers in this basket (use Bloomberg ticker field first)
    if "CURRENT_BLOOMBERG_TICKER" in df.columns:
        df = df[df["CURRENT_BLOOMBERG_TICKER"].astype(str).isin(tickers)]
    elif "CURRENT_TICKER" in df.columns:
        df = df[df["CURRENT_TICKER"].astype(str).isin(tickers)]
    else:
        return []

    # Build actionable recommendations for this basket only
    out = []
    for _, row in df.sort_values("EFFECTIVE_DATE").iterrows():
        event = row.to_dict()
        recs = calculate_event_trade_recommendations(event, positions_df, market_data_df)
        for rec in recs:
            if rec.get("basket_id") != basket_id:
                continue
            if rec.get("action") not in ("BUY", "SELL"):
                continue

            # Effective date as forward-start execution date
            eff_date = pd.Timestamp(row["EFFECTIVE_DATE"]).date()
            execution_date = eff_date.strftime("%Y-%m-%d")

            ticker = rec.get("ticker", "")
            out.append(
                {
                    "basket_id": basket_id,
                    "ticker": ticker,
                    "company": company_lookup.get(str(ticker), ""),
                    "event_type": str(row.get("ACTION_TYPE", row.get("ACTION_GROUP", "Corporate Action"))),
                    "effective_date": execution_date,
                    "comments": str(row.get("COMMENTS", "") or "")[:120],
                    # Trade recommendation fields
                    "action": rec.get("action"),
                    "shares": int(rec.get("shares_diff", 0) or 0),
                    "price": float(rec.get("price", 0) or 0),
                    "value": float(rec.get("trade_value", 0) or 0),
                    "current_shares": int(rec.get("current_shares", 0) or 0),
                    "target_shares": int(rec.get("target_shares", 0) or 0),
                    "execution_date": execution_date,
                }
            )

        if len(out) >= max_events:
            break

    return out


# =============================================================================
# IMPLIED FORWARD RATE / CALENDAR SPREAD CALCULATIONS
# =============================================================================

def calculate_implied_forward_rate(
    from_price: float,
    to_price: float,
    days_to_from: int,
    days_to_to: int,
    days_to_from_static: Optional[int] = None,
    days_to_to_static: Optional[int] = None
) -> Optional[float]:
    """
    Calculate the implied forward rate between two futures contracts.
    
    This is the rate the market is implying for the period BETWEEN the two
    contract maturities, derived from their current prices.
    
    Formula (matches Excel spreadsheet):
        Forward Rate = (TO_Price - (FROM_Price × Time_Ratio)) ÷ Day_Count_Fraction
    
    Where:
        Time_Ratio = Days_to_FROM / Days_to_TO (dynamic, from delivery dates)
        Day_Count_Fraction = (Days_to_TO - Days_to_FROM) / Days_to_TO (can use static)
    
    The spreadsheet uses a hybrid approach:
        - Numerator time ratio: calculated from delivery dates (dynamic)
        - Denominator day count: from static days values (Row 2 / Column A)
    
    Args:
        from_price: Price of the near-dated (FROM) contract in basis points
        to_price: Price of the far-dated (TO) contract in basis points
        days_to_from: Days until FROM contract delivery (dynamic, from dates)
        days_to_to: Days until TO contract delivery (dynamic, from dates)
        days_to_from_static: Optional static days for FROM (for denominator)
        days_to_to_static: Optional static days for TO (for denominator)
    
    Returns:
        Implied forward rate in basis points, or None if invalid
    
    Example:
        >>> calculate_implied_forward_rate(
        ...     from_price=44.5,   # AXWH6 (March) price
        ...     to_price=51.5,     # AXWM6 (June) price
        ...     days_to_from=20,   # Days to March delivery
        ...     days_to_to=110     # Days to June delivery
        ... )
        53.54  # Implied forward rate for March→June period
    """
    # Use static days for denominator if provided, otherwise use dynamic
    if days_to_from_static is None:
        days_to_from_static = days_to_from
    if days_to_to_static is None:
        days_to_to_static = days_to_to
    
    # Validation: FROM must expire BEFORE TO
    if days_to_from >= days_to_to:
        return None
    
    # Validation: avoid division by zero
    if days_to_to <= 0 or days_to_to_static <= 0:
        return None
    
    # Time ratio for numerator: uses DYNAMIC days
    time_ratio = days_to_from / days_to_to
    
    # Day count fraction for denominator: uses STATIC days
    day_count_fraction = (days_to_to_static - days_to_from_static) / days_to_to_static
    
    if day_count_fraction == 0:
        return None
    
    # Numerator: TO price minus time-adjusted FROM price
    numerator = to_price - (from_price * time_ratio)
    
    # Final calculation
    forward_rate = numerator / day_count_fraction
    
    return forward_rate


def calculate_calendar_spread_carry(
    from_price: float,
    to_price: float,
    days_between_contracts: int,
    notional: float,
    holding_period_days: Optional[int] = None
) -> dict:
    """
    Calculate carry metrics for a calendar spread position.
    
    A calendar spread involves:
        - LONG the near-dated (FROM) contract
        - SHORT the far-dated (TO) contract
    
    Carry is earned as time passes and the spread converges.
    
    Args:
        from_price: Price of near-dated contract (in basis points)
        to_price: Price of far-dated contract (in basis points)
        days_between_contracts: Days between the two contract maturities
        notional: Position notional in USD
        holding_period_days: Optional holding period (defaults to days_between)
    
    Returns:
        Dictionary with carry metrics:
            - spread_bps: Initial spread locked in (basis points)
            - daily_carry_bps: Daily carry in basis points
            - daily_carry_usd: Daily carry in USD
            - total_carry_bps: Total carry for holding period (bps)
            - total_carry_usd: Total carry for holding period (USD)
            - annualized_carry_bps: Annualized carry rate (bps)
    
    Example:
        >>> calculate_calendar_spread_carry(
        ...     from_price=44.5,
        ...     to_price=51.5,
        ...     days_between_contracts=90,
        ...     notional=100_000_000,
        ...     holding_period_days=20
        ... )
        {
            'spread_bps': 7.0,
            'daily_carry_bps': 0.078,
            'daily_carry_usd': 7778,
            'total_carry_bps': 1.56,
            'total_carry_usd': 155556,
            'annualized_carry_bps': 28.4
        }
    """
    if holding_period_days is None:
        holding_period_days = days_between_contracts
    
    # Spread locked in at trade inception
    spread_bps = to_price - from_price
    
    # Daily carry (spread earned per day)
    if days_between_contracts > 0:
        daily_carry_bps = spread_bps / days_between_contracts
    else:
        daily_carry_bps = 0.0
    
    # Convert to USD (1 bp = 0.0001)
    daily_carry_usd = (daily_carry_bps * BASIS_POINT) * abs(notional)
    
    # Total carry for holding period
    total_carry_bps = daily_carry_bps * holding_period_days
    total_carry_usd = daily_carry_usd * holding_period_days
    
    # Annualized carry
    annualized_carry_bps = daily_carry_bps * 365
    
    return {
        'spread_bps': spread_bps,
        'daily_carry_bps': round(daily_carry_bps, 5),
        'daily_carry_usd': round(daily_carry_usd, 2),
        'total_carry_bps': round(total_carry_bps, 5),
        'total_carry_usd': round(total_carry_usd, 2),
        'annualized_carry_bps': round(annualized_carry_bps, 2),
        'holding_period_days': holding_period_days,
        'days_between_contracts': days_between_contracts,
    }


def calculate_forward_rate_matrix(
    contracts_df: pd.DataFrame,
    price_column: str = 'last_price',
    days_column: str = 'Days_to_maturity',
    contract_column: str = 'Contract_Code',
    maturity_column: str = 'Maturity',
    as_of_date: Optional[date] = None
) -> pd.DataFrame:
    """
    Calculate a full matrix of implied forward rates between all contract pairs.
    
    This recreates the "Mid Spreads" spreadsheet matrix where:
        - Rows = FROM contracts (the near-dated leg)
        - Columns = TO contracts (the far-dated leg)
        - Cell values = Implied forward rate for that period
    
    Args:
        contracts_df: DataFrame with futures contract data containing:
            - Contract code (e.g., 'AXWH6')
            - Price (in basis points)
            - Days to maturity OR Maturity date
        price_column: Name of the price column
        days_column: Name of the days-to-maturity column
        contract_column: Name of the contract code column
        maturity_column: Name of the maturity date column (optional, for dynamic days)
        as_of_date: Date for calculating dynamic days (defaults to today)
    
    Returns:
        DataFrame with contract codes as both index and columns,
        containing implied forward rates (NaN for invalid pairs)
    
    Example:
        >>> df = pd.DataFrame({
        ...     'Contract_Code': ['AXWH6', 'AXWM6', 'AXWU6'],
        ...     'last_price': [44.5, 51.5, 54.5],
        ...     'Days_to_maturity': [20, 110, 202],
        ...     'Maturity': ['2026-03-20', '2026-06-18', '2026-09-18']
        ... })
        >>> matrix = calculate_forward_rate_matrix(df)
        >>> matrix.loc['AXWH6', 'AXWM6']
        53.54
    """
    if contracts_df.empty:
        return pd.DataFrame()
    
    # Get as_of_date for dynamic day calculation
    if as_of_date is None:
        as_of_date = datetime.now().date()
    
    # Calculate dynamic days if maturity column exists
    if maturity_column in contracts_df.columns:
        contracts_df = contracts_df.copy()
        contracts_df[maturity_column] = pd.to_datetime(contracts_df[maturity_column])
        contracts_df['_days_dynamic'] = contracts_df[maturity_column].apply(
            lambda x: (x.date() - as_of_date).days if pd.notna(x) else None
        )
    else:
        contracts_df = contracts_df.copy()
        contracts_df['_days_dynamic'] = contracts_df[days_column]
    
    # Get list of contracts
    contracts = contracts_df[contract_column].tolist()
    n = len(contracts)
    
    # Create empty matrix
    matrix = pd.DataFrame(index=contracts, columns=contracts, dtype=float)
    
    # Build lookup for contract data
    contract_data = {}
    for _, row in contracts_df.iterrows():
        code = row[contract_column]
        contract_data[code] = {
            'price': row[price_column],
            'days_static': row[days_column],
            'days_dynamic': row['_days_dynamic'],
        }
    
    # Fill the matrix
    for from_contract in contracts:
        from_data = contract_data[from_contract]
        from_price = from_data['price']
        from_days_dynamic = from_data['days_dynamic']
        from_days_static = from_data['days_static']
        
        for to_contract in contracts:
            to_data = contract_data[to_contract]
            to_price = to_data['price']
            to_days_dynamic = to_data['days_dynamic']
            to_days_static = to_data['days_static']
            
            # Skip if any values are missing
            if pd.isna(from_price) or pd.isna(to_price):
                continue
            if pd.isna(from_days_dynamic) or pd.isna(to_days_dynamic):
                continue
            
            # Calculate forward rate
            fwd_rate = calculate_implied_forward_rate(
                from_price=from_price,
                to_price=to_price,
                days_to_from=int(from_days_dynamic),
                days_to_to=int(to_days_dynamic),
                days_to_from_static=int(from_days_static) if pd.notna(from_days_static) else None,
                days_to_to_static=int(to_days_static) if pd.notna(to_days_static) else None,
            )
            
            matrix.loc[from_contract, to_contract] = fwd_rate
    
    return matrix


def identify_calendar_spread_opportunities(
    forward_rate_matrix: pd.DataFrame,
    threshold_high: float = 100.0,
    threshold_low: float = 20.0
) -> list:
    """
    Identify potential calendar spread trading opportunities from the forward rate matrix.
    
    Opportunities are identified where:
        - HIGH implied rate: Market may be overpricing the spread (sell opportunity)
        - LOW implied rate: Market may be underpricing the spread (buy opportunity)
    
    Args:
        forward_rate_matrix: DataFrame from calculate_forward_rate_matrix()
        threshold_high: Forward rates above this are flagged as "rich" (sell candidates)
        threshold_low: Forward rates below this are flagged as "cheap" (buy candidates)
    
    Returns:
        List of opportunity dictionaries with:
            - from_contract: Near-dated contract
            - to_contract: Far-dated contract
            - forward_rate: Implied forward rate
            - signal: 'RICH' or 'CHEAP'
            - trade_action: 'SELL_SPREAD' or 'BUY_SPREAD'
    """
    opportunities = []
    
    for from_contract in forward_rate_matrix.index:
        for to_contract in forward_rate_matrix.columns:
            rate = forward_rate_matrix.loc[from_contract, to_contract]
            
            if pd.isna(rate):
                continue
            
            if rate >= threshold_high:
                opportunities.append({
                    'from_contract': from_contract,
                    'to_contract': to_contract,
                    'forward_rate': round(rate, 2),
                    'signal': 'RICH',
                    'trade_action': 'SELL_SPREAD',
                    'description': f"Sell {from_contract}/{to_contract} spread - implied rate {rate:.1f} bps is high"
                })
            elif rate <= threshold_low:
                opportunities.append({
                    'from_contract': from_contract,
                    'to_contract': to_contract,
                    'forward_rate': round(rate, 2),
                    'signal': 'CHEAP',
                    'trade_action': 'BUY_SPREAD',
                    'description': f"Buy {from_contract}/{to_contract} spread - implied rate {rate:.1f} bps is low"
                })
    
    # Sort by absolute distance from neutral (most extreme first)
    neutral = (threshold_high + threshold_low) / 2
    opportunities.sort(key=lambda x: abs(x['forward_rate'] - neutral), reverse=True)
    
    return opportunities
