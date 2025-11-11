# screener.py — 100% FREE PLAN COMPATIBLE

import requests
import pandas as pd
from datetime import datetime
import os
from rich.console import Console

# Initialize console (works in headless environments)
try:
    console = Console()
except Exception:
    # Fallback for headless environments
    class DummyConsole:
        def print(self, *args, **kwargs):
            print(*args)
    console = DummyConsole()

API_KEY = os.getenv("API_KEY")

def get_dividend_harvest() -> pd.DataFrame:
    # Validate API key
    if not API_KEY or API_KEY == "your_actual_eodhd_key_here_replace_me":
        raise ValueError("API_KEY not set. Please set it in environment variables or .env file")
    
    today = datetime.now().date()
    
    # Step 1: Get ALL US + TO tickers (free, 1 call/month)
    console.print("🔄 Fetching ticker list...", style="bold blue")
    
    tickers = []
    for exchange in ['US', 'TO']:
        url_symbols = f"https://eodhd.com/api/v3/exchange-symbols?api_token={API_KEY}&fmt=json&exchange={exchange}"
        try:
            symbols_response = requests.get(url_symbols, timeout=30)
            symbols_response.raise_for_status()
            symbols = symbols_response.json()
            exchange_tickers = [s['code'] for s in symbols if s.get('type') == 'Common Stock']
            tickers.extend(exchange_tickers)
            console.print(f"✅ Loaded {len(exchange_tickers)} tickers from {exchange}", style="bold green")
        except Exception as e:
            console.print(f"⚠️ Warning: Failed to fetch {exchange} tickers: {str(e)}", style="bold yellow")
            continue
    
    if not tickers:
        raise Exception("Failed to fetch any tickers from exchanges")
    
    console.print(f"✅ Total: {len(tickers)} tickers loaded", style="bold green")
    
    # Step 2: Pull fundamentals for all (free bulk fundamentals — unlimited on free tier!)
    codes = ",".join(tickers[:2000])  # free tier allows huge batches
    url = f"https://eodhd.com/api/fundamentals/{codes}?api_token={API_KEY}&fmt=json"
    
    console.print("🔄 Fetching fundamentals data...", style="bold blue")
    try:
        response = requests.get(url, timeout=60)  # Longer timeout for bulk request
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise Exception(f"Failed to fetch fundamentals: {str(e)}")
    
    rows = []
    for ticker, fund in data.items():
        gen = fund.get('General', {})
        fin = fund.get('Financials', {})
        high = fund.get('Highlights', {})
        
        row = {
            'code': ticker,
            'name': gen.get('Name', ''),
            'exchange': gen.get('Exchange', ''),
            'close': high.get('LastClosePrice', 0) or 0,
            'market_capitalization': high.get('MarketCapitalization', 0) or 0,
            'dividend_yield': high.get('DividendYield', 0) or 0,
            'payout_ratio': high.get('PayoutRatio', 0) or 0,
            'pe_ratio': high.get('PE', 0) or 0,
            'earnings_share': high.get('EarningsShare', 0) or 0,
            'beta': high.get('Beta', 0) or 0,
            'volume_avg_30d': fund.get('Technicals', {}).get('VolumeAvg30d', 0) or 0,
            '52_week_high': high.get('52WeekHigh', 0) or 0,
            '52_week_low': high.get('52WeekLow', 0) or 0,
            'next_dividend_date': high.get('NextDividendDate', None),
            'sector': gen.get('Sector', ''),
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    console.print(f"✅ Got {len(df)} stocks before filters", style="bold green")
    
    # Same exact calculations as before
    df['next_div_date'] = pd.to_datetime(df['next_dividend_date'], errors='coerce')
    df['days_until_exdiv'] = (df['next_div_date'].dt.date - today).dt.days
    df['52w_mid'] = (df['52_week_high'] + df['52_week_low']) / 2
    df['pct_from_52w_mid'] = ((df['close'] - df['52w_mid']) / df['52w_mid'].replace(0, pd.NA) * 100).fillna(0)
    df['pct_from_52w_low'] = ((df['close'] - df['52_week_low']) / df['52_week_low'].replace(0, pd.NA) * 100).fillna(0)
    
    # SAME PRO FILTERS
    mask = (
        (df['market_capitalization'] >= 1_000_000_000) &
        (df['dividend_yield'] >= 3.0) &
        (df['earnings_share'] > 0) &
        (df['pe_ratio'] < 25) &
        (df['payout_ratio'] < 70) &
        (df['volume_avg_30d'] > 300_000) &
        (df['beta'] < 1.5) &
        (df['days_until_exdiv'].between(0, 35)) &
        (df['pct_from_52w_low'] > 15)
    )
    
    result = df[mask].copy()
    result = result.sort_values(['days_until_exdiv', 'dividend_yield'], ascending=[True, False])
    
    # Pretty units
    result['market_capitalization'] = result['market_capitalization'] / 1_000_000_000
    result['volume_avg_30d'] = result['volume_avg_30d'] / 1000
    
    return result[result.columns]
