---
title: Alberta Dividend Harvest Machine
emoji: 💰
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: "1.51.0"
app_file: app.py
pinned: false
---

# Alberta Dividend Harvest Machine

**Real-time scanner for high-conviction dividend captures**  
US + TSX stocks only • >3% yield • >$1B market cap • Ex-dividend in the next 35 days  
Built by @xbitsofalex in Calgary, Alberta

## Why These Exact Filters? (Pro-Level Reasoning)

| Filter | Value | Why It Matters (the edge) |
|--------|------|---------------------------|
| **Exchange** | `US,TO` | Only NYSE/NASDAQ + TSX → deep liquidity, proper regulation, CAD/USD easy |
| **Market Cap** | ≥ $1 000 000 000 | Eliminates micro-cap trash. You can buy 10 000 shares without moving the price |
| **Dividend Yield** | ≥ 3.0 % | Minimum acceptable annual juice. Below 3 % = bond, not dividend stock |
| **EPS (earnings_share)** | > 0 | Must actually be profitable. No zombie companies |
| **P/E Ratio** | < 25 | Avoids insane growth valuations that crush you when rates rise |
| **Payout Ratio** | < 70 % | Dividend is sustainable. Above 80 % = future cut risk |
| **30-day Avg Volume** | > 300 000 shares | You can enter/exit $500k position without slippage |
| **Beta** | < 1.5 | Lower volatility → sleep-well-at-night portfolio |
| **% from 52-week Low** | > 15 % | Avoids value traps in death spirals. Stock already has momentum |
| **Days to Ex-Div** | 0–35 days | Perfect window: buy → capture dividend → sell after ex-div pop (or hold forever) |

Result: **~15–60 elite names every day** — MO, BNS, T, CM, VZ, ENB, etc.  
Zero garbage. Pure alpha.

## One-Command Setup

```bash
git clone https://github.com/castleryder/dividend_harvest.git
cd dividend_harvest
pip install -r requirements.txt
cp .env.example .env
# ← paste your free EODHD key into .env
```

## Run CLI

```bash
python run.py
```

## Run Dashboard

```bash
streamlit run streamlit_app.py
```
