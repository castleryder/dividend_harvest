# streamlit_app.py

import streamlit as st
from datetime import datetime
from screener import get_dividend_harvest
import pandas as pd


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
    .stMetric > div {background: linear-gradient(90deg, #1e3a1e, #2d4d2d); border-radius: 12px; padding: 10px;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #2d4d2d;'>🇨🇦 Alberta Dividend Harvest Machine</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Built by @xbitsofalex • Harvesting dividends while the market sleeps</p>", unsafe_allow_html=True)

# Load data from file (updated by scheduled job, no API calls)
@st.cache_data(ttl=3600)  # Cache for 1 hour (data updates daily via GitHub Actions)
def load_dividend_data():
    """Load dividend data from file (no API calls)"""
    try:
        import json
        from pathlib import Path
        
        latest_file = Path("data/latest.json")
        if latest_file.exists():
            with open(latest_file, 'r') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            # Convert date strings back to datetime
            if 'next_div_date' in df.columns:
                df['next_div_date'] = pd.to_datetime(df['next_div_date'])
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


# Metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Stocks Ready to Harvest", len(df))

with col2:
    if 'dividend_yield' in df.columns:
        avg_yield = df['dividend_yield'].mean()
        st.metric("Avg Dividend Yield", f"{avg_yield:.2f}%")

with col3:
    if 'close' in df.columns:
        avg_price = df['close'].mean()
        st.metric("Avg Price", f"${avg_price:.2f}")

with col4:
    if 'days_until_exdiv' in df.columns:
        avg_days = df['days_until_exdiv'].mean()
        st.metric("Avg Days to Ex-Div", f"{avg_days:.0f} days")


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


# Style the dataframe
styled = df.style.format(format_dict)

# Add conditional styling only if columns exist
if 'dividend_yield' in df.columns:
    styled = styled.background_gradient(subset=['dividend_yield'], cmap='Greens')

if 'days_until_exdiv' in df.columns:
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
st.caption("🇨🇦 Alberta Dividend Harvest Machine • Data from EODHD API")

