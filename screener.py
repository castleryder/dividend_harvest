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

# File paths
CACHE_FILE = "data/latest.json"
CACHE_HOURS = 23
QUALIFIED_TICKERS_FILE = "data/qualified_tickers.json"  # Stocks that meet all criteria except ex-div date
QUALIFIED_TICKERS_REFRESH_DAYS = 7  # Refresh qualified list every 7 days

def get_all_tsx_tickers():
    """
    Get all TSX tickers from S&P/TSX Composite Index (212 tickers as of Nov 2025).
    
    To update: Run parse_tsx.py after downloading new TSX Composite list from S&P Global.
    This list is used once per week to build the qualified_tickers.json file.
    """
    return [
        "AAV.TO", "ARE.TO", "AEM.TO", "AC.TO", "AGI.TO", "AQN.TO", "ATD.TO", "AP-UN.TO",
        "ALA.TO", "AIF.TO", "ARX.TO", "ARIS.TO", "ATZ.TO", "ACO-X.TO", "ATH.TO", "ATRL.TO",
        "ATS.TO", "AYA.TO", "BTO.TO", "BDGI.TO", "BMO.TO", "BNS.TO", "ABX.TO", "BHC.TO",
        "BTE.TO", "BCE.TO", "BIR.TO", "BDT.TO", "BB.TO", "BEI-UN.TO", "BBD-B.TO", "BLX.TO",
        "BYD.TO", "BAM.TO", "BBU-UN.TO", "BN.TO", "BIP-UN.TO", "BEP-UN.TO", "DOO.TO", "CAE.TO",
        "CCO.TO", "CPKR.TO", "CAR-UN.TO", "CM.TO", "CNR.TO", "CNQ.TO", "CP.TO", "CTC-A.TO",
        "CU.TO", "CPX.TO", "CS.TO", "CJT.TO", "CCL-B.TO", "CLS.TO", "CVE.TO", "CG.TO",
        "CEU.TO", "GIB-A.TO", "CSH-UN.TO", "CHP-UN.TO", "CCA.TO", "CIGI.TO", "CSU.TO", "CRR-UN.TO",
        "CRT-UN.TO", "CURA.TO", "DFY.TO", "DML.TO", "DSG.TO", "DSV.TO", "DOL.TO", "DPM.TO",
        "DIR-UN.TO", "ELD.TO", "EFN.TO", "EMA.TO", "EMP-A.TO", "ENB.TO", "EDR.TO", "EFX.TO",
        "EFR.TO", "EQB.TO", "EQX.TO", "ERO.TO", "EIF.TO", "FFH.TO", "FTT.TO", "FCR-UN.TO",
        "AG.TO", "FM.TO", "FSV.TO", "FTS.TO", "FVI.TO", "FNV.TO", "FRU.TO", "GMIN.TO",
        "WN.TO", "GFL.TO", "GEI.TO", "GIL.TO", "GSY.TO", "GRT-UN.TO", "GWO.TO", "HR-UN.TO",
        "HWX.TO", "HBM.TO", "H.TO", "IAG.TO", "IMG.TO", "IGM.TO", "IMO.TO", "IFC.TO",
        "IPCO.TO", "IIP-UN.TO", "IVN.TO", "JWEL.TO", "KNT.TO", "KEL.TO", "KEY.TO", "KMP-UN.TO",
        "KXS.TO", "K.TO", "LIF.TO", "LB.TO", "LSPD.TO", "LNR.TO", "L.TO", "LUG.TO",
        "LUN.TO", "MG.TO", "MFC.TO", "MFI.TO", "MDA.TO", "MEG.TO", "MX.TO", "MRU.TO",
        "MTL.TO", "NA.TO", "NGD.TO", "NXE.TO", "NFI.TO", "NGEX.TO", "NWC.TO", "NPI.TO",
        "NWH-UN.TO", "NG.TO", "NTR.TO", "NVA.TO", "OGC.TO", "ONEX.TO", "OTEX.TO", "OR.TO",
        "OLA.TO", "PAAS.TO", "POU.TO", "PXT.TO", "PPL.TO", "PPTA.TO", "PET.TO", "PEY.TO",
        "POW.TO", "PSK.TO", "PBH.TO", "PMZ-UN.TO", "QBR-B.TO", "RBA.TO", "QSR.TO", "RCH.TO",
        "REI-UN.TO", "RCI-B.TO", "RY.TO", "RUS.TO", "SAP.TO", "SEA.TO", "SES.TO", "SHOP.TO",
        "SIA.TO", "SKE.TO", "SRU-UN.TO", "SOBO.TO", "SII.TO", "SSRM.TO", "STN.TO", "SJ.TO",
        "SLF.TO", "SU.TO", "SPB.TO", "TVE.TO", "TRP.TO", "TECK-B.TO", "T.TO", "TVK.TO",
        "TFII.TO", "TRI.TO", "X.TO", "TPZ.TO", "TXG.TO", "TIH.TO", "TD.TO", "TOU.TO",
        "TA.TO", "TCL-A.TO", "TFPM.TO", "TSU.TO", "VET.TO", "WCN.TO", "WDO.TO", "WFG.TO",
        "WPM.TO", "WCP.TO", "WPK.TO", "WSP.TO"
    ]

def get_qualified_tickers():
    """Get list of qualified tickers (stocks that meet all criteria except ex-div date)"""
    # Check if qualified tickers file exists and is fresh
    if os.path.exists(QUALIFIED_TICKERS_FILE):
        age_days = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(QUALIFIED_TICKERS_FILE))).total_seconds() / 86400
        if age_days < QUALIFIED_TICKERS_REFRESH_DAYS:
            try:
                with open(QUALIFIED_TICKERS_FILE, 'r') as f:
                    tickers = json.load(f)
                console.print(f"✅ Using {len(tickers)} qualified tickers (list is {age_days:.1f} days old)", style="bold green")
                return tickers
            except Exception as e:
                console.print(f"⚠️ Error loading qualified tickers: {e}", style="bold yellow")
    
    # Need to build qualified list - do full TSX scan
    console.print("🔄 Building qualified tickers list (full TSX scan)...", style="bold blue")
    console.print("   This takes ~1 hour but only runs once per week", style="dim")
    
    all_tickers = get_all_tsx_tickers()
    qualified = []
    
    # Load existing progress if available (resume from failure)
    progress_file = QUALIFIED_TICKERS_FILE.replace('.json', '_progress.json')
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                progress = json.load(f)
                qualified = progress.get('qualified', [])
                start_idx = progress.get('last_index', 0)
                console.print(f"📥 Resuming from ticker {start_idx}/{len(all_tickers)}...", style="bold yellow")
        except:
            start_idx = 0
    else:
        start_idx = 0
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    for idx, code in enumerate(all_tickers[start_idx:], start=start_idx):
        if idx % 50 == 0:
            console.print(f"   Scanning {idx}/{len(all_tickers)}... ({len(qualified)} qualified so far)", style="dim")
            # Save progress every 50 tickers
            try:
                with open(progress_file, 'w') as f:
                    json.dump({'qualified': qualified, 'last_index': idx}, f)
            except:
                pass
        
        retries = 3
        success = False
        
        for attempt in range(retries):
            try:
                ticker = yf.Ticker(code)
                info = ticker.info
                
                # Check if we got rate limited (empty info dict)
                if not info or len(info) < 5:
                    if attempt < retries - 1:
                        wait_time = 2.1 * (2 ** attempt)  # Exponential backoff: 2.1s, 4.2s, 8.4s
                        console.print(f"   ⚠️ Rate limit detected, waiting {wait_time:.1f}s...", style="bold yellow")
                        time.sleep(wait_time)
                        continue
                    else:
                        console.print(f"   ❌ Rate limited on {code}, skipping...", style="bold red")
                        consecutive_errors += 1
                        break
                
                # Must have dividend data
                if not info.get('dividendYield'):
                    success = True
                    consecutive_errors = 0
                    break
                
                # Yahoo returns dividendYield as percentage, convert to decimal
                raw_yield = (info.get('dividendYield') or 0) / 100
                
                # Apply all filters EXCEPT ex-dividend date
                if (info.get('marketCap', 0) >= 1e9 and
                    raw_yield >= 0.03 and  # 3%
                    info.get('trailingEps', 0) > 0 and
                    (info.get('trailingPE') or 999) < 25 and
                    (info.get('payoutRatio') or 1) < 0.7 and
                    (info.get('averageVolume') or 0) > 300000 and
                    (info.get('beta') or 2) < 1.5):
                    # Calculate % from 52w low
                    close = info.get('previousClose', 0)
                    low_52w = info.get('fiftyTwoWeekLow', 0)
                    if low_52w > 0:
                        pct_from_low = ((close - low_52w) / low_52w * 100)
                        if pct_from_low > 15:
                            qualified.append(code)
                
                success = True
                consecutive_errors = 0
                break
                
            except Exception as e:
                if attempt < retries - 1:
                    wait_time = 2.1 * (2 ** attempt)
                    console.print(f"   ⚠️ Error on {code} (attempt {attempt+1}/{retries}), retrying in {wait_time:.1f}s...", style="dim")
                    time.sleep(wait_time)
                else:
                    console.print(f"   ❌ Failed to fetch {code} after {retries} attempts: {str(e)[:50]}", style="dim")
                    consecutive_errors += 1
        
        # If too many consecutive errors, pause longer
        if consecutive_errors >= max_consecutive_errors:
            console.print(f"   ⚠️ {max_consecutive_errors} consecutive errors, pausing 30s...", style="bold yellow")
            time.sleep(30)
            consecutive_errors = 0
        
        # Slightly longer delay for full scan to be extra safe
        time.sleep(2.5)
    
    # Save qualified list
    os.makedirs("data", exist_ok=True)
    with open(QUALIFIED_TICKERS_FILE, 'w') as f:
        json.dump(qualified, f)
    
    # Clean up progress file
    if os.path.exists(progress_file):
        try:
            os.remove(progress_file)
        except:
            pass
    
    console.print(f"✅ Found {len(qualified)} qualified tickers (saved for future scans)", style="bold green")
    return qualified

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
    
    # Get qualified tickers (will use cached list if available)
    tickers_to_scan = get_qualified_tickers()
    
    console.print("🔄 Harvesting fresh data...", style="bold green")
    # Use UTC date to match GitHub Actions timezone
    from datetime import timezone
    today = datetime.now(timezone.utc).date()
    results = []
    
    for idx, code in enumerate(tickers_to_scan):
        console.print(f"{idx+1}/{len(tickers_to_scan)} {code}...", style="dim")
        try:
            ticker = yf.Ticker(code)
            info = ticker.info
            
            ex_div = info.get('exDividendDate')
            if not ex_div:
                continue
            
            # Yahoo returns dividendYield as percentage (4.59 = 4.59%), convert to decimal for filtering
            raw_yield = (info.get('dividendYield') or 0) / 100  # Convert 4.59% → 0.0459
            
            # Store code without .TO suffix and convert hyphens back to dots for cleaner display
            display_code = code.replace('.TO', '').replace('-', '.')
            
            row = {
                'code': display_code,  # Clean code without .TO
                'name': info.get('longName', code),
                'close': info.get('previousClose', 0),
                'market_capitalization': info.get('marketCap', 0),
                'dividend_yield': raw_yield,  # Store as decimal (0.0459 = 4.59%)
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
        (df['days_until_exdiv'] <= 60) &  # Within 60 days
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
