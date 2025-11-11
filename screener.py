# screener.py — DYNAMIC YFINANCE FULL UNIVERSE — FINAL VERSION

import yfinance as yf
import pandas as pd
from datetime import datetime
from rich.console import Console
import time

# Initialize console (works in headless environments)
try:
    console = Console()
except Exception:
    # Fallback for headless environments
    class DummyConsole:
        def print(self, *args, **kwargs):
            print(*args)
    console = DummyConsole()

# Full universe — we pull these once and cache forever
US_TICKERS = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
TSX_TICKERS = pd.read_html('https://en.wikipedia.org/wiki/S%26P/TSX_Composite_Index')[0]['Ticker symbol'].tolist()

ALL_TICKERS = list(set(US_TICKERS + TSX_TICKERS))
console.print(f"Scanning {len(ALL_TICKERS)} S&P 500 + TSX stocks...", style="bold blue")


def get_dividend_harvest() -> pd.DataFrame:
    today = datetime.now().date()
    results = []

    # yfinance batch mode — 50 at a time to avoid rate limits
    for i in range(0, len(ALL_TICKERS), 50):
        batch = ALL_TICKERS[i:i+50]
        console.print(f"Batch {i//50 + 1}/{(len(ALL_TICKERS)-1)//50 + 1}...", style="dim")
        
        try:
            data = yf.Tickers(" ".join(batch))
            for ticker in data.tickers:
                info = ticker.info
                try:
                    # Skip if no dividend data
                    if not info.get('dividendYield'): continue
                    
                    row = {
                        'code': info.get('symbol', ''),
                        'name': info.get('longName', ''),
                        'exchange': info.get('exchange', ''),
                        'close': info.get('previousClose', 0),
                        'market_capitalization': info.get('marketCap', 0),
                        'dividend_yield': info.get('dividendYield', 0) * 100,
                        'payout_ratio': info.get('payoutRatio', 0),
                        'pe_ratio': info.get('trailingPE', 999),
                        'earnings_share': info.get('trailingEps', 0),
                        'beta': info.get('beta', 0),
                        'volume_avg_30d': info.get('averageVolume', 0),
                        '52_week_high': info.get('fiftyTwoWeekHigh', 0),
                        '52_week_low': info.get('fiftyTwoWeekLow', 0),
                        'ex_dividend_date': info.get('exDividendDate'),
                        'sector': info.get('sector', ''),
                    }
                    results.append(row)
                except:
                    continue
        except:
            continue
        
        time.sleep(0.5)  # be nice to Yahoo

    df = pd.DataFrame(results)
    if df.empty:
        console.print("No data found!", style="bold red")
        return df

    console.print(f"✅ Got {len(df)} stocks before filters", style="bold green")

    # Convert ex-div date
    df['next_div_date'] = pd.to_datetime(df['ex_dividend_date'], unit='s', errors='coerce')
    df['days_until_exdiv'] = (df['next_div_date'].dt.date - today).dt.days
    df['52w_mid'] = (df['52_week_high'] + df['52_week_low']) / 2
    df['pct_from_52w_mid'] = ((df['close'] - df['52w_mid']) / df['52w_mid'].replace(0, pd.NA) * 100).fillna(0)
    df['pct_from_52w_low'] = ((df['close'] - df['52_week_low']) / df['52_week_low'].replace(0, pd.NA) * 100).fillna(0)

    # YOUR EXACT PRO FILTERS
    mask = (
        (df['market_capitalization'] >= 1e9) &
        (df['dividend_yield'] >= 3.0) &
        (df['earnings_share'] > 0) &
        (df['pe_ratio'] < 25) &
        (df['payout_ratio'] < 0.7) &
        (df['volume_avg_30d'] > 300_000) &
        (df['beta'] < 1.5) &
        (df['days_until_exdiv'].between(0, 35)) &
        (df['pct_from_52w_low'] > 15)
    )

    result = df[mask].copy()
    result = result.sort_values(['days_until_exdiv', 'dividend_yield'], ascending=[True, False])

    # Pretty units
    result['market_capitalization'] /= 1e9
    result['volume_avg_30d'] /= 1000

    console.print(f"🎯 {len(result)} BRAND NEW HARVEST OPPORTUNITIES FOUND", style="bold magenta")
    return result.head(100)
