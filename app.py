import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from data_loader import fetch_stock_data, build_synthetic_options_chain
from strategies import run_covered_call, run_protective_put, run_straddle
from backtester import run_backtest

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Options Backtester",
    page_icon="📈",
    layout="wide",
)
st.title("📈 Options Strategy Backtester")
st.caption("Covered Call · Protective Put · Straddle — with live Greeks dashboard")

# ── Sidebar controls ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Parameters")
    ticker    = st.text_input("Ticker", value="AAPL")
    start     = st.date_input("Start Date", value=pd.Timestamp("2022-01-01"))
    end       = st.date_input("End Date",   value=pd.Timestamp("2023-12-31"))
    strategy  = st.selectbox("Strategy", ["Covered Call", "Protective Put", "Straddle"])
    roll_days = st.slider("Roll Period (days)", 15, 60, 30)
    rfr       = st.slider("Risk-Free Rate (%)", 0.0, 10.0, 5.0) / 100
    run_btn   = st.button("▶ Run Backtest", use_container_width=True)

# ── Run ────────────────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner("Fetching data and running backtest…"):
        prices = fetch_stock_data(ticker, str(start), str(end))["price"]
        if prices.empty:
            st.error("No data found. Check ticker and date range.")
            st.stop()

        chain = build_synthetic_options_chain(prices, expiry_days=roll_days)

        strat_map = {
            "Covered Call":   run_covered_call,
            "Protective Put": run_protective_put,
            "Straddle":       run_straddle,
        }
        strat_df = strat_map[strategy](prices, chain, rfr, roll_days)
        result   = run_backtest(strat_df, prices)

    # ── Metrics row ────────────────────────────────────────────────────────────
    st.subheader("Performance Summary")
    sm = result["strategy_metrics"]
    bm = result["benchmark_metrics"]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Strategy Return",  f"{sm['total_return_pct']}%")
    c2.metric("Strategy Sharpe",  sm['sharpe_ratio'])
    c3.metric("Strategy Max DD",  f"{sm['max_drawdown_pct']}%")
    c4.metric("Benchmark Return", f"{bm['total_return_pct']}%",
              delta=f"{sm['total_return_pct'] - bm['total_return_pct']:.2f}%")
    c5.metric("Benchmark Sharpe", bm['sharpe_ratio'])
    c6.metric("Benchmark Max DD", f"{bm['max_drawdown_pct']}%")

    # ── P&L Chart ──────────────────────────────────────────────────────────────
    st.subheader("P&L vs Benchmark")
    fig_pnl = go.Figure()
    fig_pnl.add_trace(go.Scatter(
        x=result["strategy_pnl"].index,
        y=result["strategy_pnl"],
        name=strategy, line=dict(color="#00b4d8", width=2)
    ))
    fig_pnl.add_trace(go.Scatter(
        x=result["benchmark_pnl"].index,
        y=result["benchmark_pnl"],
        name="Stock Only", line=dict(color="#f77f00", width=2, dash="dash")
    ))
    fig_pnl.update_layout(
        xaxis_title="Date", yaxis_title="P&L ($)",
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="white", hovermode="x unified", height=350
    )
    st.plotly_chart(fig_pnl, use_container_width=True)

    # ── Greeks Dashboard ───────────────────────────────────────────────────────
    st.subheader("Greeks Over Time")
    greeks = result["greeks"]

    fig_g = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Delta", "Gamma", "Theta (daily $)", "Vega (per 1% vol)"),
        shared_xaxes=True,
    )
    colors     = ["#06d6a0", "#ef476f", "#ffd166", "#118ab2"]
    greek_cols = ["delta", "gamma", "theta", "vega"]
    positions  = [(1, 1), (1, 2), (2, 1), (2, 2)]

    for col, pos, color in zip(greek_cols, positions, colors):
        fig_g.add_trace(
            go.Scatter(x=greeks.index, y=greeks[col],
                       name=col.capitalize(), line=dict(color=color, width=1.5)),
            row=pos[0], col=pos[1]
        )
        fig_g.add_hline(y=0, line_dash="dot", line_color="gray",
                        row=pos[0], col=pos[1])

    fig_g.update_layout(
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="white", height=500,
        legend=dict(orientation="h", y=-0.12),
    )
    st.plotly_chart(fig_g, use_container_width=True)

    # ── Greeks Animation ───────────────────────────────────────────────────────
    st.subheader("🎬 Greeks Animation — Option Lifetime")
    st.caption("Watch how Delta, Gamma, and Theta evolve as time-to-expiry collapses")

    anim_greek = st.selectbox("Animate Greek", ["delta", "gamma", "theta", "vega"])

    # Take just one cycle for clean animation
    cycle = strat_df.copy().reset_index()
    cycle = cycle.head(roll_days).copy()
    cycle["day"] = list(range(len(cycle)))
    cycle["date_str"] = cycle["date"].astype(str)

    fig_anim = go.Figure()

    # Build frames
    frames = []
    for i in range(len(cycle)):
        frames.append(go.Frame(
            data=[go.Scatter(
                x=cycle["date_str"].iloc[:i + 1],
                y=cycle[anim_greek].iloc[:i + 1],
                mode="lines+markers",
                line=dict(color="#00b4d8", width=2),
                marker=dict(size=4),
            )],
            name=str(i)
        ))

    # Initial trace (first point)
    fig_anim.add_trace(go.Scatter(
        x=cycle["date_str"].iloc[:1],
        y=cycle[anim_greek].iloc[:1],
        mode="lines+markers",
        line=dict(color="#00b4d8", width=2),
        marker=dict(size=4),
    ))

    fig_anim.frames = frames

    y_min = cycle[anim_greek].min()
    y_max = cycle[anim_greek].max()
    padding = max(abs(y_max - y_min) * 0.1, 0.05)

    fig_anim.update_layout(
        title=f"{anim_greek.capitalize()} over one option cycle ({roll_days} days)",
        xaxis_title="Date",
        yaxis_title=anim_greek.capitalize(),
        yaxis=dict(range=[y_min - padding, y_max + padding]),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="white", height=420,
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            y=1.15, x=0.5, xanchor="center",
            buttons=[
                dict(
                    label="▶ Play",
                    method="animate",
                    args=[None, dict(frame=dict(duration=80, redraw=True), fromcurrent=True)]
                ),
                dict(
                    label="⏸ Pause",
                    method="animate",
                    args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]
                ),
            ]
        )],
        sliders=[dict(
            steps=[
                dict(method="animate",
                     args=[[str(i)], dict(mode="immediate", frame=dict(duration=80, redraw=True))],
                     label=str(i))
                for i in range(len(cycle))
            ],
            x=0.1, y=0, len=0.8,
            currentvalue=dict(prefix="Day: ", visible=True, xanchor="center"),
        )]
    )

    st.plotly_chart(fig_anim, use_container_width=True)

    # ── Raw data ───────────────────────────────────────────────────────────────
    with st.expander("📊 Raw Strategy Data"):
        st.dataframe(strat_df.round(4), use_container_width=True)

else:
    st.info("👈 Configure parameters in the sidebar and click **Run Backtest**")