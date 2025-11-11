# streamlit_app.py

import streamlit as st
from datetime import datetime
import pandas as pd
import json
from pathlib import Path


st.set_page_config(
    page_title="Alberta Dividend Harvester",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add this for instant Alberta cowboy vibes
st.markdown("""
<style>
    .css-1d391kg {padding-top: 1rem !important;}
    .css-1v0mbdj {font-family: 'Courier New', monospace;}
    .stMetric > div {
        background: linear-gradient(90deg, #1e3a1e, #2d4d2d); 
        border-radius: 12px; 
        padding: 10px;
    }
    .stMetric label,
    .stMetric [data-testid="stMetricValue"],
    .stMetric [data-testid="stMetricDelta"],
    .stMetric > div > div {
        color: white !important;
    }
    /* Constrain column widths to fit all columns */
    .stDataFrame table {
        font-size: 0.85em;
    }
    .stDataFrame th,
    .stDataFrame td {
        padding: 4px 6px !important;
        white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #2d4d2d;'>The Real Money Isn't Made by Catching Every Little Wave</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Wait for the Right Setup</p>", unsafe_allow_html=True)

# Load data from file (updated by scheduled job, no API calls)
@st.cache_data(ttl=3600)  # Cache for 1 hour (data updates daily via GitHub Actions)
def load_dividend_data():
    """Load dividend data from file (no API calls)"""
    try:
        latest_file = Path("data/latest.json")
        if latest_file.exists():
            with open(latest_file, 'r') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            # Convert date strings back to datetime
            if 'next_div_date' in df.columns:
                df['next_div_date'] = pd.to_datetime(df['next_div_date'], errors='coerce')
            # Convert ex_dividend_date from Unix timestamp to datetime (if it's numeric)
            if 'ex_dividend_date' in df.columns:
                # Check if it's already a datetime or still a Unix timestamp
                if df['ex_dividend_date'].dtype in ['int64', 'float64']:
                    df['ex_dividend_date'] = pd.to_datetime(df['ex_dividend_date'], unit='s', errors='coerce')
                else:
                    df['ex_dividend_date'] = pd.to_datetime(df['ex_dividend_date'], errors='coerce')
            return df
        else:
            st.warning("⚠️ No data file found. Waiting for scheduled update...")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()


# Sidebar for controls
with st.sidebar:
    st.header("⚙️ Controls")
    
    st.info("📅 Data updates daily via scheduled job")
    st.caption("Last update: Check GitHub Actions")
    
    st.divider()
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# Load data from file (no API calls - updated daily via GitHub Actions)
with st.spinner("🔄 Loading dividend data..."):
    df = load_dividend_data()


# Handle empty state
if df.empty:
    st.warning("⚠️ No stocks found matching criteria. Please check your filters or API connection.")
    st.stop()


# ACTIONABLE INSIGHT METRICS - Find specific opportunities
col1, col2, col3, col4 = st.columns(4)

# Helper function to safely get stock info from pandas Series
def get_stock_info(row):
    """Safely extract stock information with defaults"""
    return {
        'code': row.get('code', 'N/A') if 'code' in row.index else 'N/A',
        'yield': row.get('dividend_yield', 0) if 'dividend_yield' in row.index else 0,
        'days': row.get('days_until_exdiv', 0) if 'days_until_exdiv' in row.index else 0,
        'beta': row.get('beta', 0) if 'beta' in row.index else 0,
        'pct': row.get('pct_from_52w_low', 0) if 'pct_from_52w_low' in row.index else 0,
    }

# 1. TOP HARVEST ALERT - Highest yield + closest ex-div (already sorted this way)
with col1:
    if len(df) > 0 and 'code' in df.columns:
        top_harvest = df.iloc[0]
        info = get_stock_info(top_harvest)
        st.metric(
            "TOP HARVEST ALERT",
            f"{info['code']}",
            f"{info['yield']:.2f}% → {int(info['days'])}d",
            help="Highest yield + closest ex-div = immediate income"
        )
    else:
        st.metric("TOP HARVEST ALERT", "N/A", "No data")

# 2. BEST YIELD + PROXIMITY - Best yield-to-time ratio
with col2:
    if len(df) > 0 and 'dividend_yield' in df.columns and 'days_until_exdiv' in df.columns:
        # Sort by yield descending, then days ascending
        best_yield_proximity = df.sort_values(
            by=['dividend_yield', 'days_until_exdiv'],
            ascending=[False, True]
        ).iloc[0]
        info = get_stock_info(best_yield_proximity)
        st.metric(
            "BEST YIELD + PROXIMITY",
            f"{info['code']}",
            f"{info['yield']:.2f}% in {int(info['days'])}d",
            help="Best yield-to-time ratio = efficiency"
        )
    else:
        st.metric("BEST YIELD + PROXIMITY", "N/A", "No data")

# 3. RISK-ADJUSTED GEM - High yield + low beta
with col3:
    if len(df) > 0 and 'beta' in df.columns and 'dividend_yield' in df.columns:
        # Find lowest beta among stocks with yield >= 3%
        high_yield_stocks = df[df['dividend_yield'] >= 3.0]
        if len(high_yield_stocks) > 0:
            low_beta_high_yield = high_yield_stocks.loc[high_yield_stocks['beta'].idxmin()]
            info = get_stock_info(low_beta_high_yield)
            st.metric(
                "RISK-ADJUSTED GEM",
                f"{info['code']}",
                f"{info['yield']:.2f}% @ β{info['beta']:.2f}",
                help="High yield + low beta = sleep-well money"
            )
        else:
            # Fallback: just lowest beta overall
            low_beta_high_yield = df.loc[df['beta'].idxmin()]
            info = get_stock_info(low_beta_high_yield)
            st.metric(
                "RISK-ADJUSTED GEM",
                f"{info['code']}",
                f"β{info['beta']:.2f}",
                help="Lowest beta = safest play"
            )
    else:
        st.metric("RISK-ADJUSTED GEM", "N/A", "No data")

# 4. MOMENTUM DIVER - Deep discount from 52w low
with col4:
    if len(df) > 0 and 'pct_from_52w_low' in df.columns:
        momentum_diver = df.loc[df['pct_from_52w_low'].idxmax()]
        info = get_stock_info(momentum_diver)
        st.metric(
            "MOMENTUM DIVER",
            f"{info['code']}",
            f"↑{info['pct']:.0f}% from low",
            help="Deep discount from 52w low = upside + yield"
        )
    else:
        st.metric("MOMENTUM DIVER", "N/A", "No data")


# Formatting dictionary - only include columns that exist
format_dict = {}
if 'close' in df.columns:
    format_dict['close'] = '${:.2f}'
if 'dividend_yield' in df.columns:
    format_dict['dividend_yield'] = '{:.2f}%'
if 'days_until_exdiv' in df.columns:
    format_dict['days_until_exdiv'] = '{:.0f}d'
if 'market_capitalization' in df.columns:
    format_dict['market_capitalization'] = '{:.1f}B'
if 'volume_avg_30d' in df.columns:
    format_dict['volume_avg_30d'] = '{:.0f}k'
if 'payout_ratio' in df.columns:
    format_dict['payout_ratio'] = '{:.0f}%'
if 'pe_ratio' in df.columns:
    format_dict['pe_ratio'] = '{:.1f}'
if 'pct_from_52w_low' in df.columns:
    format_dict['pct_from_52w_low'] = '{:+.1f}%'
if 'earnings_share' in df.columns:
    format_dict['earnings_share'] = '{:.2f}'  # Reduced from 6 decimals
if 'beta' in df.columns:
    format_dict['beta'] = '{:.2f}'  # Reduced from 6 decimals
if '52_week_high' in df.columns:
    format_dict['52_week_high'] = '{:.2f}'  # Reduced from 6 decimals
if '52_week_low' in df.columns:
    format_dict['52_week_low'] = '{:.2f}'  # Reduced from 6 decimals

# Format dates before styling (convert to date-only strings)
if 'next_div_date' in df.columns:
    if pd.api.types.is_datetime64_any_dtype(df['next_div_date']):
        df['next_div_date'] = df['next_div_date'].dt.strftime('%Y-%m-%d')
    else:
        df['next_div_date'] = pd.to_datetime(df['next_div_date'], errors='coerce').dt.strftime('%Y-%m-%d')

# Convert payout_ratio from decimal to percentage (0.5447 → 54.47%)
# This must be done before creating display_df since format_dict expects percentage
if 'payout_ratio' in df.columns:
    df['payout_ratio'] = df['payout_ratio'] * 100

# Remove ex_dividend_date from display (redundant - same as next_div_date, just in Unix timestamp format)
# Keep it in the data for calculations, but don't show it
display_df = df.drop(columns=['ex_dividend_date'], errors='ignore')

# Reorder columns: Put 52_week_high and 52_week_low next to close for easy comparison
# Define desired column order
desired_order = [
    'code', 'name', 'close', 
    '52_week_high', '52_week_low', 'pct_from_52w_low',  # Price comparison group
    'market_capitalization', 'dividend_yield', 'payout_ratio', 
    'pe_ratio', 'earnings_share', 'beta', 'volume_avg_30d',
    'next_div_date', 'days_until_exdiv'
]

# Get columns that exist in the dataframe
existing_cols = [col for col in desired_order if col in display_df.columns]
# Add any remaining columns that weren't in desired_order
remaining_cols = [col for col in display_df.columns if col not in existing_cols]
# Combine: desired order first, then any extras
final_order = existing_cols + remaining_cols

# Reorder the dataframe
display_df = display_df[final_order]

# Style the dataframe
styled = display_df.style.format(format_dict)

# Add conditional styling only if columns exist
# Note: background_gradient requires matplotlib, removed to keep dependencies minimal
# if 'dividend_yield' in df.columns:
#     styled = styled.background_gradient(subset=['dividend_yield'], cmap='Greens')

if 'days_until_exdiv' in display_df.columns:
    styled = styled.bar(subset=['days_until_exdiv'], color='#ffaa00')


# Display styled dataframe
st.dataframe(styled, use_container_width=True, height=600)


# Download section
st.divider()

col1, col2 = st.columns([1, 4])

with col1:
    csv_data = df.to_csv(index=False).encode()
    st.download_button(
        "📥 Download CSV",
        csv_data,
        f"dividend_harvest_{datetime.now():%Y%m%d}.csv",
        "text/csv",
        use_container_width=True
    )

with col2:
    st.caption(f"💾 {len(df)} stocks • {csv_data.__sizeof__() / 1024:.1f} KB")


# Footer
st.divider()
st.caption("🇨🇦 Alberta Dividend Harvest Machine • Data from Yahoo Finance via yfinance")

