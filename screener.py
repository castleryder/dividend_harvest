# screener.py

from rich.console import Console
import os

# Initialize console (works in headless environments)
try:
    console = Console()
except Exception:
    # Fallback for headless environments
    class DummyConsole:
        def print(self, *args, **kwargs):
            print(*args)
    console = DummyConsole()

from dotenv import load_dotenv

# Load .env file if it exists (won't fail if missing)
load_dotenv()

API_KEY = os.getenv("API_KEY")

import requests
import pandas as pd
from datetime import datetime, timedelta
from time import sleep

# Constants
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30
DAYS_WINDOW = 35


def _robust_get(url: str) -> requests.Response:
    """API call with retry logic and exponential backoff"""
    response = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                raise Exception(f"API request timed out after {MAX_RETRIES} attempts")
            console.print(f"⏳ Timeout, retrying ({attempt + 1}/{MAX_RETRIES})...", style="bold yellow")
            sleep(2 ** attempt)  # Exponential backoff
        except requests.exceptions.HTTPError:
            if response and response.status_code == 429:  # Rate limit
                if attempt == MAX_RETRIES - 1:
                    raise Exception(f"Rate limit exceeded: {response.text}")
                wait_time = 2 ** attempt
                console.print(f"⏳ Rate limited, waiting {wait_time}s...", style="bold yellow")
                sleep(wait_time)
            else:
                status_code = response.status_code if response else "unknown"
                error_text = response.text if response else "No response"
                raise Exception(f"API error ({status_code}): {error_text}")
        except requests.exceptions.RequestException as e:
            # Catch all other request exceptions (ConnectionError, etc.)
            if attempt == MAX_RETRIES - 1:
                raise Exception(f"API request failed: {str(e)}")
            console.print(f"⏳ Request failed, retrying ({attempt + 1}/{MAX_RETRIES}): {str(e)}", style="bold yellow")
            sleep(2 ** attempt)


def get_dividend_harvest() -> pd.DataFrame:
    # Validate API key
    if not API_KEY or API_KEY == "your_actual_eodhd_key_here_replace_me":
        raise ValueError("API_KEY not set. Please set it in environment variables or .env file")
    
    today = datetime.now().date()
    
    url = (
        f"https://eodhd.com/api/v4/screener?api_token={API_KEY}&fmt=json"
        f"&exchange=US,TO"
        f"&market_capitalization.gte=1000000000"
        f"&dividend_yield.gte=3"
        f"&earnings_share.gt=0"
        f"&pe_ratio.lt=25"
        f"&payout_ratio.lt=70"
        f"&volume_avg_30d.gt=300000"
        f"&beta.lt=1.5"
        f"&sort=dividend_yield.desc"
        f"&limit=500"
    )
    
    # API call with retry logic
    console.print("🔄 Pulling fresh data from EODHD...", style="bold blue")
    # Format URL for debugging (can't use backslash in f-string expression)
    debug_url = url.replace('&', '\n&')
    console.print(f"🌎 Query URL (copy-paste to browser to debug): {debug_url}", style="dim")
    response = _robust_get(url)
    
    # Validate response structure
    try:
        json_data = response.json()
        if 'data' not in json_data:
            raise ValueError("API response missing 'data' key")
        data = json_data['data']
    except ValueError as e:
        raise Exception(f"Invalid API response: {e}")
    except Exception as e:
        raise Exception(f"Failed to parse API response: {e}")
    
    if not data:
        console.print("⚠️ No data returned from API", style="bold yellow")
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    console.print(f"✅ Got {len(df)} stocks before filters", style="bold green")
    
    # Parse dates (with null handling)
    if 'next_dividend_date' not in df.columns:
        console.print("⚠️ Warning: 'next_dividend_date' column not found", style="bold yellow")
        df['next_div_date'] = pd.NaT
        df['days_until_exdiv'] = pd.NA
    else:
        df['next_div_date'] = pd.to_datetime(df['next_dividend_date'], errors='coerce')
        df['days_until_exdiv'] = (df['next_div_date'].dt.date - today).dt.days
    
    # 52-week math (with division by zero protection)
    required_cols = ['52_week_high', '52_week_low', 'close']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        console.print(f"⚠️ Warning: Missing columns {missing_cols}, using defaults", style="bold yellow")
        for col in missing_cols:
            if col == 'close':
                df[col] = 0
            else:
                # Use 'close' if available, otherwise 0
                df[col] = df['close'] if 'close' in df.columns else 0
    
    df['52w_mid'] = (df['52_week_high'] + df['52_week_low']) / 2
    df['pct_from_52w_mid'] = ((df['close'] - df['52w_mid']) / df['52w_mid'].replace(0, pd.NA) * 100).fillna(0)
    df['pct_from_52w_low'] = ((df['close'] - df['52_week_low']) / df['52_week_low'].replace(0, pd.NA) * 100).fillna(0)
    
    # FINAL PRO FILTERS (with null-safe operations)
    mask = pd.Series(True, index=df.index)
    
    if 'days_until_exdiv' in df.columns:
        mask &= df['days_until_exdiv'].notna() & df['days_until_exdiv'].between(0, DAYS_WINDOW)
    if 'pct_from_52w_low' in df.columns:
        mask &= df['pct_from_52w_low'].notna() & (df['pct_from_52w_low'] > 15)
    if 'dividend_yield' in df.columns:
        mask &= df['dividend_yield'].notna() & (df['dividend_yield'] >= 3.0)
    
    final = df[mask].copy()
    
    # Sort with null handling
    sort_cols = []
    if 'days_until_exdiv' in final.columns:
        sort_cols.append('days_until_exdiv')
    if 'dividend_yield' in final.columns:
        sort_cols.append('dividend_yield')
    
    if sort_cols:
        final = final.sort_values(sort_cols, ascending=[True, False], na_position='last')
    
    # Columns we actually care about (only include if they exist)
    desired_cols = [
        'code', 'name', 'exchange', 'close', 'dividend_yield',
        'days_until_exdiv', 'next_div_date', 'payout_ratio', 'pe_ratio',
        'pct_from_52w_low', 'pct_from_52w_mid', 'sector', 'volume_avg_30d',
        'market_capitalization'
    ]
    cols = [col for col in desired_cols if col in final.columns]
    
    if not cols:
        console.print("⚠️ Warning: No expected columns found, returning all columns", style="bold yellow")
        cols = list(final.columns)
    
    result = final[cols].head(100).copy()
    
    # Pretty formatting for CSV (only if columns exist)
    if 'market_capitalization' in result.columns:
        result['market_capitalization'] = result['market_capitalization'] / 1_000_000_000
    if 'volume_avg_30d' in result.columns:
        result['volume_avg_30d'] = result['volume_avg_30d'] / 1000
    
    return result
