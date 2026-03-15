import numpy as np
import pandas as pd


def compute_metrics(pnl_series: pd.Series, prices: pd.Series) -> dict:
    """Compute return, Sharpe, max drawdown for a P&L series."""
    total_return = pnl_series.iloc[-1] / prices.iloc[0] * 100

    daily_pnl = pnl_series.diff().fillna(0)
    daily_ret = daily_pnl / prices.iloc[0]
    sharpe = (daily_ret.mean() / daily_ret.std() * np.sqrt(252)
              if daily_ret.std() > 0 else 0.0)

    cumulative = pnl_series
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / prices.iloc[0] * 100
    max_drawdown = drawdown.min()

    return {
        "total_return_pct": round(total_return, 2),
        "sharpe_ratio":     round(sharpe, 3),
        "max_drawdown_pct": round(max_drawdown, 2),
    }


def benchmark_stock_only(prices: pd.Series) -> pd.Series:
    """Buy-and-hold benchmark P&L."""
    return prices - prices.iloc[0]


def run_backtest(strategy_df: pd.DataFrame, prices: pd.Series) -> dict:
    pnl = strategy_df["total_pnl"]
    bench = benchmark_stock_only(prices.reindex(pnl.index))

    strat_metrics = compute_metrics(pnl, prices)
    bench_metrics = compute_metrics(bench, prices)

    return {
        "strategy_pnl":    pnl,
        "benchmark_pnl":   bench,
        "strategy_metrics": strat_metrics,
        "benchmark_metrics": bench_metrics,
        "greeks": strategy_df[["delta", "gamma", "theta", "vega"]],
    }