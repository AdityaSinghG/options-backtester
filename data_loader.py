import numpy as np
import pandas as pd
import yfinance as yf


def fetch_stock_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    df.columns = df.columns.droplevel(1) if isinstance(df.columns, pd.MultiIndex) else df.columns
    df = df[["Close"]].rename(columns={"Close": "price"})
    df.index.name = "date"
    return df.dropna()


def estimate_historical_vol(prices: pd.Series, window: int = 21) -> pd.Series:
    log_ret = np.log(prices / prices.shift(1))
    return log_ret.rolling(window).std() * np.sqrt(252)


def build_synthetic_options_chain(
    prices: pd.Series,
    expiry_days: int = 30,
    moneyness_range: tuple = (0.90, 1.10),
    num_strikes: int = 9,
    risk_free_rate: float = 0.05,
) -> pd.DataFrame:
    from greeks import compute_greeks

    vols = estimate_historical_vol(prices).fillna(0.25)
    records = []

    for date, S in prices.items():
        S = float(S)
        
        # Safely extract scalar vol
        vol_val = vols.get(date, 0.25)
        if isinstance(vol_val, pd.Series):
            vol_val = vol_val.iloc[0]
        sigma = float(vol_val)
        if sigma < 0.01 or np.isnan(sigma):
            sigma = 0.25

        lo, hi = moneyness_range
        strikes = np.linspace(S * lo, S * hi, num_strikes)

        for K in strikes:
            K = round(float(K), 0)
            for opt_type in ["call", "put"]:
                T = expiry_days / 365
                g = compute_greeks(S, K, T, risk_free_rate, sigma, opt_type)
                records.append({
                    "date": date,
                    "underlying_price": S,
                    "strike": K,
                    "option_type": opt_type,
                    "expiry_days": expiry_days,
                    "T": T,
                    "sigma": sigma,
                    **g,
                })

    return pd.DataFrame(records)