# 📈 Options Strategy Backtester

A Python-based backtesting engine for options strategies with a live Greeks dashboard built using Streamlit.

## Strategies Supported
- **Covered Call** — Long stock + short ATM call
- **Protective Put** — Long stock + long ATM put
- **Straddle** — Long ATM call + long ATM put

## Features
- Black-Scholes Greeks calculator (Delta, Gamma, Theta, Vega) built from scratch in NumPy
- Daily P&L tracking vs buy-and-hold benchmark
- Performance metrics: Total Return, Sharpe Ratio, Max Drawdown
- Animated Greeks dashboard showing how Delta/Gamma/Theta evolve as expiry approaches
- Works on any ticker via yfinance

## Tech Stack
Python · NumPy · SciPy · Pandas · Plotly · Streamlit · yfinance

## Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Live Demo
[Click here to open the app](https://options-backtester-uxhcbobskzhjojwnyscp2j.streamlit.app/)