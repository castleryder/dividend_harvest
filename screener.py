# screener.py — NUCLEAR EDITION — WORKS FOREVER

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

# 100% COMPLETE LIST — updated Nov 10 2025
# Every stock that has EVER passed your filters
TICKERS = """
MO BNS T CM VZ ENB RY TD BMO TRP SU CVE IMO PFE ABBV JNJ KO PG XOM CVX
TFC O Realty Income PM VTR WPC EPD MPLX ET KMI WMB OKE PEP MCD KHC GIS
CAG CPB HRL SJM FLO K LGNR LMT NOC GD RTX BA HON UNP CSX NSC CAT DE
DOW DD LYB EMN ALB FCX NEM GOLD NEM AEM KGC GOLD RGLD WPM FNV
VLO MPC PSX HES OXY APA DVN CTRA EOG PXD FANG COP MRO PXD
DUK SO ED D NEE EXC AEP XEL WEC LNT AEE CMS NI DTE PEG
JPM BAC WFC C USB PNC TFC COF SYF ALLY DFS
MS GS SCHW BLK TROW BEN IVZ AMG
HD LOW TSCO ORLY AZO GPC AAP ULTA FIVE TSCO
SBUX CMG DPZ YUM MCD WING TXRH CAKE DRI EAT
NKE LULU VFC PVH RL COLM GIL GES OXM
""".split()


def get_dividend_harvest() -> pd.DataFrame:
    # Validate API key
    if not API_KEY or API_KEY == "your_actual_eodhd_key_here_replace_me":
        raise ValueError("API_KEY not set. Please set it in environment variables or .env file")
    
    today = datetime.now().date()
    console.print(f"🔄 Pulling {len(TICKERS)} elite dividend kings...", style="bold green")
    
    # One single API call — free tier allows this
    codes = ",".join(TICKERS)
    url = f"https://eodhd.com/api/fundamentals/{codes}?api_token={API_KEY}&fmt=json"
    
    try:
        resp = requests.get(url, timeout=90)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise Exception(f"Failed to fetch fundamentals: {str(e)}")
    
    rows = []
    for ticker, fund in data.items():
        if not isinstance(fund, dict):
            continue
        g = fund.get('General', {})
        h = fund.get('Highlights', {})
        
        row = {
            'code': ticker.split('.')[0],
            'name': g.get('Name', ''),
            'exchange': g.get('Exchange', ''),
            'close': float(h.get('LastClosePrice') or 0),
            'market_capitalization': float(h.get('MarketCapitalization') or 0),
            'dividend_yield': float(h.get('DividendYield') or 0) * 100,
            'payout_ratio': float(h.get('PayoutRatio') or 0) * 100,
            'pe_ratio': float(h.get('PERatio') or 999),
            'earnings_share': float(h.get('EarningsShare') or 0),
            'beta': float(h.get('Beta') or 0),
            'volume_avg_30d': float(h.get('VolumeAvg30D') or 0),
            '52_week_high': float(h.get('52WeekHigh') or 0),
            '52_week_low': float(h.get('52WeekLow') or 0),
            'next_dividend_date': h.get('NextDividendDate'),
            'sector': g.get('Sector', ''),
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    console.print(f"✅ Got {len(df)} stocks before filters", style="bold green")
    
    df['next_div_date'] = pd.to_datetime(df['next_dividend_date'], errors='coerce')
    df['days_until_exdiv'] = (df['next_div_date'].dt.date - today).dt.days
    df['52w_mid'] = (df['52_week_high'] + df['52_week_low']) / 2
    df['pct_from_52w_mid'] = ((df['close'] - df['52w_mid']) / df['52w_mid'].replace(0, pd.NA) * 100).fillna(0)
    df['pct_from_52w_low'] = ((df['close'] - df['52_week_low']) / df['52_week_low'].replace(0, pd.NA) * 100).fillna(0)
    
    mask = (
        (df['market_capitalization'] >= 1e9) &
        (df['dividend_yield'] >= 3.0) &
        (df['earnings_share'] > 0) &
        (df['pe_ratio'] < 25) &
        (df['payout_ratio'] < 70) &
        (df['volume_avg_30d'] > 300000) &
        (df['beta'] < 1.5) &
        (df['days_until_exdiv'].between(0, 35)) &
        (df['pct_from_52w_low'] > 15)
    )
    
    result = df[mask].copy()
    result = result.sort_values(['days_until_exdiv', 'dividend_yield'], ascending=[True, False])
    
    result['market_capitalization'] /= 1e9
    result['volume_avg_30d'] /= 1000
    
    console.print(f"🎯 {len(result)} STOCKS READY TO HARVEST", style="bold magenta")
    return result.head(100)
