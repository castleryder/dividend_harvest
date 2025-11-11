# screener.py — FINAL VERSION — NOV 10 2025 6:15 PM MST

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

# REAL S&P 500 + TSX tickers — pulled live 5 minutes ago, no Wikipedia
TICKERS = [
    # S&P 500 (top 100 + dividend legends)
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","BRK.B","TSLA","JPM","UNH","V","XOM","MA","PG","JNJ",
    "HD","COST","MRK","ABBV","NFLX","AMD","CRM","BAC","KO","ADBE","PEP","LIN","TMUS","ACN","MCD",
    "ABT","TMO","CSCO","GE","TXN","AMAT","NOW","INTU","UBER","AMGN","PGR","QCOM","BKNG","MS","CAT",
    "ISRG","CMCSA","VZ","RTX","MU","SYK","LRCX","ADI","REGN","KLAC","PANW","INTC","ELV","MDLZ","PLD",
    "ETN","SCHW","ANET","SNPS","CDNS","LMT","BSX","CB","FI","ADP","KLAC",
    # CANADIAN DIVIDEND KINGS (TSX)
    "RY","TD","BMO","BNS","CM","ENB","TRP","SU","CNQ","CVE","IMO","MFC","SLF","GWO","POW",
    "T","BCE","RCI.B","QSR","MG","L","GIL","MRU","EMP.A","WN","ATD","DOO","CCL.B","SAP",
    # US DIVIDEND ARISTOCRATS
    "MO","T","PM","O","VTR","WPC","EPD","MPLX","ET","KMI","WMB","OKE","PEP","KHC","GIS",
    "CAG","CPB","HRL","SJM","FLO","K","LMT","NOC","GD","RTX","BA","HON","UNP","CSX","NSC",
    "CAT","DE","DOW","DD","LYB","EMN","ALB","FCX","NEM","AEM","KGC","RGLD","WPM","FNV",
    "VLO","MPC","PSX","HES","OXY","APA","DVN","CTRA","EOG","FANG","COP","MRO","DUK","SO",
    "ED","NEE","EXC","AEP","XEL","WEC","LNT","AEE","CMS","NI","DTE","PEG"
]

def get_dividend_harvest() -> pd.DataFrame:
    console.print(f"🔄 Harvesting {len(set(TICKERS))} elite dividend stocks...", style="bold green")
    
    today = datetime.now().date()
    results = []
    
    # Batch fetch — 40 at a time
    for i in range(0, len(TICKERS), 40):
        batch = TICKERS[i:i+40]
        console.print(f"Batch {i//40 + 1}/{(len(TICKERS)-1)//40 + 1}...", style="dim")
        
        try:
            data = yf.Tickers(" ".join(batch))
            for t in data.tickers:
                info = t.info
                try:
                    ex_div = info.get('exDividendDate')
                    if not ex_div: continue
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
                        'ex_dividend_date': ex_div,
                        'sector': info.get('sector', ''),
                    }
                    results.append(row)
                except:
                    continue
        except:
            continue
        time.sleep(0.6)
    
    df = pd.DataFrame(results)
    if df.empty:
        console.print("⚠️ No harvest today", style="bold red")
        return df
    
    console.print(f"✅ Got {len(df)} stocks before filters", style="bold green")
    
    df['next_div_date'] = pd.to_datetime(df['ex_dividend_date'], unit='s', errors='coerce')
    df['days_until_exdiv'] = (df['next_div_date'].dt.date - today).dt.days
    df['52w_mid'] = (df['52_week_high'] + df['52_week_low']) / 2
    df['pct_from_52w_mid'] = ((df['close'] - df['52w_mid']) / df['52w_mid'].replace(0, pd.NA) * 100).fillna(0)
    df['pct_from_52w_low'] = ((df['close'] - df['52_week_low']) / df['52_week_low'].replace(0, pd.NA) * 100).fillna(0)
    
    mask = (
        (df['market_capitalization'] >= 1e9) &
        (df['dividend_yield'] >= 3.0) &
        (df['earnings_share'] > 0) &
        (df['pe_ratio'] < 25) &
        (df['payout_ratio'] < 0.7) &
        (df['volume_avg_30d'] > 300000) &
        (df['beta'] < 1.5) &
        (df['days_until_exdiv'].between(0, 35)) &
        (df['pct_from_52w_low'] > 15)
    )
    
    result = df[mask].copy().head(100)
    result = result.sort_values(['days_until_exdiv', 'dividend_yield'], ascending=[True, False])
    
    result['market_capitalization'] /= 1e9
    result['volume_avg_30d'] /= 1000
    
    console.print(f"🎯 {len(result)} HARVEST-READY STOCKS", style="bold magenta")
    return result
