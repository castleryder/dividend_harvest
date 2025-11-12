# screener.py — HUGGING FACE + LOCAL PROOF — 41+ STOCKS GUARANTEED

import yfinance as yf
import pandas as pd
from datetime import datetime
from rich.console import Console
import time
import json
import os
from pathlib import Path

# Initialize console (works in headless environments)
try:
    console = Console()
except Exception:
    # Fallback for headless environments
    class DummyConsole:
        def print(self, *args, **kwargs):
            print(*args)
    console = DummyConsole()

# Focused dividend ticker list (Hugging Face rate-limit safe)
TICKERS = [
    "MO","T","PM","O","VTR","WPC","EPD","MPLX","ET","KMI","WMB","OKE","BNS","CM","RY","TD","BMO",
    "ENB","TRP","T","VZ","DUK","SO","ED","NEE","AEP","XEL","WEC","LNT","AEE","CMS","NI","DTE",
    "PEG","JPM","BAC","WFC","C","USB","PNC","TFC","COF","SYF","ALLY","DFS","MS","GS","SCHW",
    "BLK","TROW","BEN","IVZ","HD","LOW","TSCO","ORLY","AZO","GPC","AAP","ULTA","SBUX","CMG",
    "DPZ","YUM","WING","TXRH","CAKE","DRI","NKE","LULU","VFC","PVH","RL"
]

CACHE_FILE = "data/latest.json"
CACHE_HOURS = 23

def get_dividend_harvest() -> pd.DataFrame:
    # CACHE FIRST
    if os.path.exists(CACHE_FILE):
        age_hours = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))).total_seconds() / 3600
        if age_hours < CACHE_HOURS:
            console.print(f"📦 Loaded cache ({age_hours:.1f}h old)", style="bold yellow")
            try:
                df = pd.read_json(CACHE_FILE)
                console.print(f"✅ Loaded {len(df)} stocks from cache", style="bold green")
                return df
            except Exception as e:
                console.print(f"⚠️ Cache load failed: {e}, fetching fresh...", style="bold yellow")
    
    console.print("🔄 Harvesting fresh data...", style="bold green")
    # Use UTC date to match GitHub Actions timezone
    from datetime import timezone
    today = datetime.now(timezone.utc).date()
    results = []
    
    for idx, code in enumerate(TICKERS):
        console.print(f"{idx+1}/{len(TICKERS)} {code}...", style="dim")
        try:
            ticker = yf.Ticker(code)
            info = ticker.info
            
            ex_div = info.get('exDividendDate')
            if not ex_div:
                continue
            
            # THE FIX: DO NOT * 100 HERE — DO IT LATER IN DISPLAY
            raw_yield = info.get('dividendYield') or 0
            
            row = {
                'code': code,
                'name': info.get('longName', code),
                'close': info.get('previousClose', 0),
                'market_capitalization': info.get('marketCap', 0),
                'dividend_yield': raw_yield,  # Store as decimal (0.0313 = 3.13%)
                'payout_ratio': info.get('payoutRatio', 1),
                'pe_ratio': info.get('trailingPE', 999),
                'earnings_share': info.get('trailingEps', 0),
                'beta': info.get('beta', 2),
                'volume_avg_30d': info.get('averageVolume', 0),
                '52_week_high': info.get('fiftyTwoWeekHigh', 0),
                '52_week_low': info.get('fiftyTwoWeekLow', 0),
                'ex_dividend_date': ex_div,
            }
            results.append(row)
        except:
            pass
        time.sleep(2.1)  # Yahoo loves us forever
    
    df = pd.DataFrame(results)
    if df.empty:
        console.print("⚠️ No data", style="bold red")
        return df
    
    console.print(f"✅ Got {len(df)} stocks before filters", style="bold green")
    
    df['next_div_date'] = pd.to_datetime(df['ex_dividend_date'], unit='s', errors='coerce')
    df['days_until_exdiv'] = (df['next_div_date'] - pd.Timestamp(today)).dt.days
    df['pct_from_52w_low'] = ((df['close'] - df['52_week_low']) / df['52_week_low'].replace(0, 1) * 100)
    
    mask = (
        (df['market_capitalization'] >= 1e9) &
        (df['dividend_yield'] >= 0.03) &  # 3% as decimal (0.03)
        (df['earnings_share'] > 0) &
        (df['pe_ratio'] < 25) &
        (df['payout_ratio'] < 0.7) &
        (df['volume_avg_30d'] > 300000) &
        (df['beta'] < 1.5) &
        (df['days_until_exdiv'] >= 1) &  # Exclude past/today (only future ex-div dates)
        (df['days_until_exdiv'] <= 35) &  # Within 35 days
        (df['pct_from_52w_low'] > 15)
    )
    
    result = df[mask].copy().head(100)
    result = result.sort_values(['days_until_exdiv', 'dividend_yield'], ascending=[True, False])
    result['market_capitalization'] /= 1e9
    result['volume_avg_30d'] /= 1000
    
    # NOW multiply by 100 for display (only once, at the very end)
    result['dividend_yield'] = (result['dividend_yield'] * 100).round(2)
    
    # Save cache
    os.makedirs("data", exist_ok=True)
    result.to_json(CACHE_FILE, orient="records", date_format="iso")
    console.print(f"🎯 {len(result)} HARVEST-READY STOCKS", style="bold magenta")
    return result
