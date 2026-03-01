"""
Quarterback Data Loader Module
==============================
Centralized data loading functions for all data sources.
Each function loads and processes a specific dataset.

In Phase 2, these functions can be modified to pull from live/intraday data sources
instead of CSV files, without changing the rest of the application.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
from datetime import datetime

# Base path for data files - can be configured for different environments
DATA_PATH = Path(__file__).parent.parent / "data"


def load_positions(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load and process positions data from CSV.
    
    This function loads the portfolio positions including all baskets,
    futures, equity positions, cash borrowing/lending, and stock borrowing.
    
    Args:
        file_path: Optional custom path to positions file. 
                   Defaults to positions_physicalequities.csv (in project root)
    
    Returns:
        DataFrame with processed positions data
    
    Columns of interest:
        - BASKET_ID: Unique identifier for each basket
        - POSITION_ID: Unique identifier for each position
        - POSITION_TYPE: FUTURE, EQUITY, CASH_BORROW, CASH_LEND, STOCK_BORROW
        - STRATEGY_TYPE: Simple Carry, Reverse Carry, Calendar Spread
        - LONG_SHORT: Direction of the position (LONG or SHORT)
        - QUANTITY: Number of shares/contracts (negative for shorts)
        - PRICE_OR_LEVEL: Price per share
        - NOTIONAL_USD, MARKET_VALUE_USD, EQUITY_EXPOSURE_USD
        - FINANCING_RATE_%, EXPECTED_DIVIDENDS_USD
        - START_DATE, END_DATE
        - PNL_USD
    """
    if file_path is None:
        # Use the new positions file with physical equities
        # NOTE: Keep filename casing consistent (important on Linux / Streamlit Cloud).
        file_path = DATA_PATH.parent / "Positions_physicalequities.csv"
    
    df = pd.read_csv(file_path)
    
    # Clean up PNL column - remove formatting characters
    if 'PNL_USD' in df.columns:
        df['PNL_USD'] = df['PNL_USD'].astype(str).str.replace(r'[\s,$()]', '', regex=True)
        df['PNL_USD'] = df['PNL_USD'].str.replace(r'^-$', '0', regex=True)
        df['PNL_USD'] = pd.to_numeric(df['PNL_USD'], errors='coerce').fillna(0)
        # Handle negative values in parentheses
        df.loc[df['PNL_USD'].astype(str).str.contains(r'\(', regex=True, na=False), 'PNL_USD'] *= -1
    
    # Parse dates
    date_columns = ['TRADE_DATE', 'START_DATE', 'END_DATE']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Convert numeric columns
    numeric_columns = [
        'QUANTITY', 'PRICE_OR_LEVEL', 'NOTIONAL_USD', 'MARKET_VALUE_USD',
        'EQUITY_EXPOSURE_USD', 'DELTA_EQUIVALENT_USD', 'GROSS_NOTIONAL_USD',
        'FINANCING_RATE_%', 'EXPECTED_DIVIDENDS_USD'
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def load_stock_market_data(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load and process S&P 500 constituent stock market data.
    
    This function loads pricing, weights, and market cap data for all
    constituents of the S&P 500 index.
    
    Args:
        file_path: Optional custom path to market data file.
                   Defaults to data/stockmarketdata.csv
    
    Returns:
        DataFrame with processed stock market data
    
    Key columns:
        - COMPANY: Company name
        - CURRENCY: Trading currency
        - CUSIP: Security identifier
        - BLOOMBERG_TICKER: Bloomberg ticker symbol
        - LOCAL_PRICE: Current stock price
        - MARKET_CAP: Market capitalization
        - IWF: Investable Weight Factor
        - INDEX_SHARES: Number of shares in the index
        - INDEX_WEIGHT: Weight in the index
        - DIVIDEND, NET_DIVIDEND: Dividend information
    """
    if file_path is None:
        file_path = DATA_PATH / "stockmarketdata.csv"
    
    df = pd.read_csv(file_path)
    
    # Parse date columns
    if 'FILE_DATE' in df.columns:
        df['FILE_DATE'] = pd.to_datetime(df['FILE_DATE'], errors='coerce')
    
    # Ensure numeric columns are properly typed
    numeric_columns = [
        'LOCAL_PRICE', 'SHARES_OUTSTANDING', 'MARKET_CAP', 'IWF', 'AWF',
        'INDEX_SHARES', 'INDEX_MARKET_CAP', 'INDEX_WEIGHT', 'GROWTH', 'VALUE',
        'FX_RATE', 'DIVIDEND', 'NET_DIVIDEND'
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calculate index weight if not present
    if 'INDEX_WEIGHT' in df.columns:
        # Normalize to ensure weights sum to 1
        total_weight = df['INDEX_WEIGHT'].sum()
        if total_weight > 0:
            df['INDEX_WEIGHT_NORMALIZED'] = df['INDEX_WEIGHT'] / total_weight
    
    return df


def load_corporate_actions(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load and process corporate actions data for calendar events.
    
    This function loads upcoming corporate actions including dividends,
    mergers, acquisitions, spin-offs, and index rebalancing events.
    
    Args:
        file_path: Optional custom path to corporate actions file.
                   Defaults to data/corpactions.csv
    
    Returns:
        DataFrame with processed corporate actions data
    
    Key columns:
        - FILE_DATE: Date the data was generated
        - EFFECTIVE_DATE: Date the action takes effect
        - CURRENT_TICKER: Stock ticker symbol
        - CURRENT_CUSIP: Security identifier
        - CURRENT_BLOOMBERG_TICKER: Bloomberg ticker
        - NET_DIVIDEND: Dividend amount (net of withholding)
        - ACTION_TYPE: Type of corporate action
        - DIVIDEND: Gross dividend amount
        - ACTION_GROUP: Category of action (Distribution, Merger, etc.)
        - STATUS: Finalized, Pending, etc.
        - COMMENTS: Additional details about the action
    """
    if file_path is None:
        file_path = DATA_PATH / "corpactions.csv"
    
    df = pd.read_csv(file_path)
    
    # Parse date columns
    date_columns = ['FILE_DATE', 'EFFECTIVE_DATE', 'CLOSE_OF_BUSINESS_DATE', 
                    'LAST_UPDATED_DATE', 'REFERENCE_DATE']
    for col in date_columns:
        if col in df.columns:
            # Handle YYYYMMDD format
            df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')
    
    # Ensure numeric columns are properly typed
    numeric_columns = [
        'NET_DIVIDEND', 'DIVIDEND', 'IWF', 'FX_RATE', 'CURRENT_SHARES_OUTSTANDING',
        'INDEX_SHARES_PRIOR_EVENTS', 'INDEX_SHARES_POST_EVENTS', 'CURRENT_PRICE',
        'FRANKING_RATE', 'CURRENT_TAX_RATE', 'RATIO_RECEIVED', 'RATIO_HELD', 'CASH_AMOUNT'
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Sort by effective date
    if 'EFFECTIVE_DATE' in df.columns:
        df = df.sort_values('EFFECTIVE_DATE', na_position='last')
    
    return df


def load_top50_earnings(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load and process Top 50 S&P 500 earnings dates (demo dataset).
    
    Expected columns (as provided in the demo Excel):
        - Ticker
        - Company Name
        - Earnings Announcement Date
        - BLOOMBERG_TICKER
    
    Normalized output columns:
        - TICKER
        - COMPANY_NAME
        - EARNINGS_DATE
        - BLOOMBERG_TICKER
    """
    if file_path is None:
        # Stored in project root (demo asset)
        file_path = DATA_PATH.parent / "top50_earnings_dates.xlsx"

    df = pd.read_excel(file_path)

    # Normalize column names
    rename_map = {
        "Ticker": "TICKER",
        "Company Name": "COMPANY_NAME",
        "Earnings Announcement Date": "EARNINGS_DATE",
        "BLOOMBERG_TICKER": "BLOOMBERG_TICKER",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Coerce required columns
    for col in ["TICKER", "COMPANY_NAME", "BLOOMBERG_TICKER"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "EARNINGS_DATE" in df.columns:
        df["EARNINGS_DATE"] = pd.to_datetime(df["EARNINGS_DATE"], errors="coerce")

    # Drop rows without a date or ticker
    if "EARNINGS_DATE" in df.columns and "BLOOMBERG_TICKER" in df.columns:
        df = df[df["EARNINGS_DATE"].notna() & df["BLOOMBERG_TICKER"].notna()]

    return df


def load_market_events(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load and process market events data (FOMC announcements, holidays, early closes).
    
    Expected columns:
        - DATE: Event date (YYYY-MM-DD)
        - EVENT_TYPE: FOMC, HOLIDAY, or EARLY_CLOSE
        - EVENT_NAME: Name of the event
        - DESCRIPTION: Detailed description
        - MARKET_CLOSED: TRUE if markets fully closed, FALSE otherwise
    
    Returns:
        DataFrame with processed market events data
    """
    if file_path is None:
        file_path = DATA_PATH / "market_events.csv"
    
    if not Path(file_path).exists():
        # Return empty DataFrame if file doesn't exist
        return pd.DataFrame(columns=['DATE', 'EVENT_TYPE', 'EVENT_NAME', 'DESCRIPTION', 'MARKET_CLOSED'])
    
    df = pd.read_csv(file_path)
    
    # Parse date column
    if 'DATE' in df.columns:
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
    
    # Convert MARKET_CLOSED to boolean
    if 'MARKET_CLOSED' in df.columns:
        df['MARKET_CLOSED'] = df['MARKET_CLOSED'].astype(str).str.upper() == 'TRUE'
    
    # Sort by date
    if 'DATE' in df.columns:
        df = df.sort_values('DATE', na_position='last')
    
    return df


def get_basket_list(positions_df: pd.DataFrame) -> list:
    """
    Extract unique basket IDs from positions data.
    
    Args:
        positions_df: DataFrame from load_positions()
    
    Returns:
        List of unique basket IDs
    """
    if 'BASKET_ID' in positions_df.columns:
        return sorted(positions_df['BASKET_ID'].unique().tolist())
    return []


def get_basket_positions(positions_df: pd.DataFrame, basket_id: str) -> pd.DataFrame:
    """
    Filter positions for a specific basket.
    
    Args:
        positions_df: DataFrame from load_positions()
        basket_id: The basket ID to filter for
    
    Returns:
        DataFrame with positions for the specified basket
    """
    return positions_df[positions_df['BASKET_ID'] == basket_id].copy()


def get_basket_underlying_index(positions_df: pd.DataFrame, basket_id: str) -> str:
    """
    Determine the underlying index for a basket based on its positions.
    
    Args:
        positions_df: DataFrame from load_positions()
        basket_id: The basket ID to check
    
    Returns:
        String identifying the underlying index (e.g., "S&P 500", "TSX 60")
    """
    basket_positions = get_basket_positions(positions_df, basket_id)
    
    if 'UNDERLYING' in basket_positions.columns:
        underlyings = basket_positions['UNDERLYING'].dropna().unique()
        if len(underlyings) > 0:
            return underlyings[0]
    
    return "S&P 500"  # Default for this demo


def get_upcoming_events(corp_actions_df: pd.DataFrame, 
                        days_ahead: int = 30,
                        underlying_index: Optional[str] = None) -> pd.DataFrame:
    """
    Get corporate actions occurring within the specified number of days.
    
    Args:
        corp_actions_df: DataFrame from load_corporate_actions()
        days_ahead: Number of days to look ahead
        underlying_index: Filter by underlying index (e.g., "S&P 500")
    
    Returns:
        DataFrame with upcoming events
    """
    today = pd.Timestamp.now().normalize()
    end_date = today + pd.Timedelta(days=days_ahead)
    
    mask = (corp_actions_df['EFFECTIVE_DATE'] >= today) & \
           (corp_actions_df['EFFECTIVE_DATE'] <= end_date)
    
    filtered_df = corp_actions_df[mask].copy()
    
    if underlying_index and 'INDEX_NAME' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['INDEX_NAME'] == underlying_index]
    
    return filtered_df.sort_values('EFFECTIVE_DATE')


def get_dividend_events(corp_actions_df: pd.DataFrame,
                        tickers: Optional[list] = None) -> pd.DataFrame:
    """
    Get dividend events, optionally filtered by ticker list.
    
    Args:
        corp_actions_df: DataFrame from load_corporate_actions()
        tickers: Optional list of tickers to filter for
    
    Returns:
        DataFrame with dividend events
    """
    dividend_mask = corp_actions_df['ACTION_TYPE'] == 'Dividend'
    
    if 'ACTION_GROUP' in corp_actions_df.columns:
        dividend_mask = dividend_mask | (corp_actions_df['ACTION_GROUP'] == 'Distribution')
    
    filtered_df = corp_actions_df[dividend_mask].copy()
    
    if tickers is not None and len(tickers) > 0:
        ticker_mask = filtered_df['CURRENT_TICKER'].isin(tickers) | \
                      filtered_df['CURRENT_BLOOMBERG_TICKER'].isin(tickers)
        filtered_df = filtered_df[ticker_mask]
    
    return filtered_df


# Cache for loaded data to avoid repeated file reads
_cache = {}

def get_cached_data(data_type: str, force_reload: bool = False) -> pd.DataFrame:
    """
    Get cached data or load if not cached.
    
    Args:
        data_type: One of 'positions', 'market_data', 'corp_actions', 'earnings', 
                   'market_events', 'futures_prices'
        force_reload: Force reload from file even if cached
    
    Returns:
        Requested DataFrame
    """
    global _cache
    
    if force_reload or data_type not in _cache:
        if data_type == 'positions':
            _cache[data_type] = load_positions()
        elif data_type == 'market_data':
            _cache[data_type] = load_stock_market_data()
        elif data_type == 'corp_actions':
            _cache[data_type] = load_corporate_actions()
        elif data_type == 'earnings':
            _cache[data_type] = load_top50_earnings()
        elif data_type == 'market_events':
            _cache[data_type] = load_market_events()
        elif data_type == 'futures_prices':
            _cache[data_type] = load_futures_prices()
        else:
            raise ValueError(f"Unknown data type: {data_type}")
    
    return _cache[data_type]


def clear_cache():
    """Clear all cached data."""
    global _cache
    _cache = {}


def get_equity_positions(positions_df: pd.DataFrame, basket_id: str) -> pd.DataFrame:
    """
    Get equity positions for a specific basket.
    
    Args:
        positions_df: DataFrame from load_positions()
        basket_id: The basket ID to filter for
    
    Returns:
        DataFrame with equity positions for the basket
    """
    mask = (positions_df['BASKET_ID'] == basket_id) & \
           (positions_df['POSITION_TYPE'] == 'EQUITY')
    return positions_df[mask].copy()


def get_stock_borrow_positions(positions_df: pd.DataFrame, basket_id: str) -> pd.DataFrame:
    """
    Get stock borrow positions for a specific basket.
    
    Args:
        positions_df: DataFrame from load_positions()
        basket_id: The basket ID to filter for
    
    Returns:
        DataFrame with stock borrow positions for the basket
    """
    mask = (positions_df['BASKET_ID'] == basket_id) & \
           (positions_df['POSITION_TYPE'] == 'STOCK_BORROW')
    return positions_df[mask].copy()


def get_futures_positions(positions_df: pd.DataFrame, basket_id: str) -> pd.DataFrame:
    """
    Get futures positions for a specific basket.
    
    Args:
        positions_df: DataFrame from load_positions()
        basket_id: The basket ID to filter for
    
    Returns:
        DataFrame with futures positions for the basket
    """
    mask = (positions_df['BASKET_ID'] == basket_id) & \
           (positions_df['POSITION_TYPE'] == 'FUTURE')
    return positions_df[mask].copy()


def get_cash_positions(positions_df: pd.DataFrame, basket_id: str) -> pd.DataFrame:
    """
    Get cash borrow/lend positions for a specific basket.
    
    Args:
        positions_df: DataFrame from load_positions()
        basket_id: The basket ID to filter for
    
    Returns:
        DataFrame with cash positions for the basket
    """
    mask = (positions_df['BASKET_ID'] == basket_id) & \
           (positions_df['POSITION_TYPE'].isin(['CASH_BORROW', 'CASH_LEND']))
    return positions_df[mask].copy()


def load_futures_prices(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load S&P 500 AIR futures prices data for calendar spread analysis.
    
    This data is used by the Markets page to calculate implied forward rates
    and identify calendar spread trading opportunities.
    
    Args:
        file_path: Optional custom path to futures prices file.
                   Defaults to data/futures_prices.xlsx
    
    Returns:
        DataFrame with futures price data
    
    Expected columns:
        - Contract_Code: Futures contract identifier (e.g., 'AXWH6' for March 2026)
        - Days_to_maturity: Days until contract delivery
        - last_price: Current futures price in basis points
        - Maturity: Contract maturity/delivery date
    
    Contract Code Convention:
        - AXW = S&P 500 AIR futures root
        - H = March, M = June, U = September, Z = December
        - 6 = 2026, 7 = 2027, etc.
    """
    if file_path is None:
        file_path = DATA_PATH / "futures_prices.xlsx"
    
    if not Path(file_path).exists():
        # Return empty DataFrame if file doesn't exist
        return pd.DataFrame(columns=['Contract_Code', 'Days_to_maturity', 'last_price', 'Maturity'])
    
    df = pd.read_excel(file_path)
    
    # Parse maturity date column
    if 'Maturity' in df.columns:
        df['Maturity'] = pd.to_datetime(df['Maturity'], errors='coerce')
    
    # Ensure numeric columns are properly typed
    numeric_columns = ['Days_to_maturity', 'last_price']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Sort by days to maturity (nearest first)
    if 'Days_to_maturity' in df.columns:
        df = df.sort_values('Days_to_maturity', na_position='last')
    
    return df
