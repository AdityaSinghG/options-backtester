import numpy as np
import pandas as pd
from greeks import compute_greeks


def _nearest_strike(chain_day, S, target_moneyness=1.0, option_type="call"):
    sub = chain_day[chain_day["option_type"] == option_type].copy()
    sub["dist"] = abs(sub["strike"] - S * target_moneyness)
    return sub.loc[sub["dist"].idxmin()]


def run_covered_call(prices, chain, risk_free_rate=0.05, roll_days=30):
    """Long 100 shares + short 1 ATM call, rolled every roll_days."""
    dates = prices.index
    records = []

    i = 0
    while i < len(dates):
        entry_date = dates[i]
        expiry_idx = min(i + roll_days, len(dates) - 1)
        expiry_date = dates[expiry_idx]

        S_entry = prices.iloc[i]
        day_chain = chain[chain["date"] == entry_date]
        if day_chain.empty:
            i += roll_days
            continue

        opt = _nearest_strike(day_chain, S_entry, 1.0, "call")
        K = opt["strike"]
        sigma = opt["sigma"]
        call_premium_received = opt["price"]

        for j in range(i, expiry_idx + 1):
            date = dates[j]
            S = prices.iloc[j]
            T_remaining = max((expiry_idx - j) / 365, 0)
            g = compute_greeks(S, K, T_remaining, risk_free_rate, sigma, "call")
            call_value = g["price"]

            stock_pnl = S - S_entry
            option_pnl = call_premium_received - call_value
            total_pnl = stock_pnl + option_pnl

            records.append({
                "date": date,
                "S": S,
                "K": K,
                "T_remaining": T_remaining,
                "stock_pnl": stock_pnl,
                "option_pnl": option_pnl,
                "total_pnl": total_pnl,
                "delta": g["delta"],
                "gamma": g["gamma"],
                "theta": g["theta"],
                "vega":  g["vega"],
                "strategy": "covered_call",
            })

        i = expiry_idx + 1

    return pd.DataFrame(records).set_index("date")


def run_protective_put(prices, chain, risk_free_rate=0.05, roll_days=30):
    """Long 100 shares + long 1 ATM put."""
    dates = prices.index
    records = []

    i = 0
    while i < len(dates):
        entry_date = dates[i]
        expiry_idx = min(i + roll_days, len(dates) - 1)

        S_entry = prices.iloc[i]
        day_chain = chain[chain["date"] == entry_date]
        if day_chain.empty:
            i += roll_days
            continue

        opt = _nearest_strike(day_chain, S_entry, 1.0, "put")
        K = opt["strike"]
        sigma = opt["sigma"]
        put_premium_paid = opt["price"]

        for j in range(i, expiry_idx + 1):
            date = dates[j]
            S = prices.iloc[j]
            T_remaining = max((expiry_idx - j) / 365, 0)
            g = compute_greeks(S, K, T_remaining, risk_free_rate, sigma, "put")
            put_value = g["price"]

            stock_pnl = S - S_entry
            option_pnl = put_value - put_premium_paid
            total_pnl = stock_pnl + option_pnl

            records.append({
                "date": date,
                "S": S,
                "K": K,
                "T_remaining": T_remaining,
                "stock_pnl": stock_pnl,
                "option_pnl": option_pnl,
                "total_pnl": total_pnl,
                "delta": g["delta"],
                "gamma": g["gamma"],
                "theta": g["theta"],
                "vega":  g["vega"],
                "strategy": "protective_put",
            })

        i = expiry_idx + 1

    return pd.DataFrame(records).set_index("date")


def run_straddle(prices, chain, risk_free_rate=0.05, roll_days=30):
    """Long ATM call + long ATM put (long volatility)."""
    dates = prices.index
    records = []

    i = 0
    while i < len(dates):
        entry_date = dates[i]
        expiry_idx = min(i + roll_days, len(dates) - 1)

        S_entry = prices.iloc[i]
        day_chain = chain[chain["date"] == entry_date]
        if day_chain.empty:
            i += roll_days
            continue

        call_opt = _nearest_strike(day_chain, S_entry, 1.0, "call")
        put_opt  = _nearest_strike(day_chain, S_entry, 1.0, "put")
        K = call_opt["strike"]
        sigma = call_opt["sigma"]
        call_paid = call_opt["price"]
        put_paid  = put_opt["price"]
        total_paid = call_paid + put_paid

        for j in range(i, expiry_idx + 1):
            date = dates[j]
            S = prices.iloc[j]
            T_remaining = max((expiry_idx - j) / 365, 0)
            cg = compute_greeks(S, K, T_remaining, risk_free_rate, sigma, "call")
            pg = compute_greeks(S, K, T_remaining, risk_free_rate, sigma, "put")

            straddle_value = cg["price"] + pg["price"]
            total_pnl = straddle_value - total_paid

            records.append({
                "date": date,
                "S": S,
                "K": K,
                "T_remaining": T_remaining,
                "stock_pnl": 0.0,
                "option_pnl": total_pnl,
                "total_pnl": total_pnl,
                "delta": cg["delta"] + pg["delta"],
                "gamma": cg["gamma"] + pg["gamma"],
                "theta": cg["theta"] + pg["theta"],
                "vega":  cg["vega"]  + pg["vega"],
                "strategy": "straddle",
            })

        i = expiry_idx + 1

    return pd.DataFrame(records).set_index("date")