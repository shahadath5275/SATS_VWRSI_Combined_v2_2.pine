"""
10 EMA Strategy — Full Pipeline
Steps: 2 (Backtest) -> 9 (Monte Carlo) -> 10 (Drawdown Analysis)

To run with REAL data on your own machine:
    pip install yfinance pandas numpy matplotlib
    python ema_backtest_pipeline.py

Change TICKER / PERIOD / INTERVAL below.
Note: Yahoo only allows 5m data for the last ~60 days.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# CONFIG
# ============================================================
TICKER      = "MU"
PERIOD      = "60d"     # max for 5m interval on yfinance
INTERVAL    = "5m"
EMA_LEN     = 10
TARGET_PCT  = 0.01       # 1% take profit
STOP_PCT    = 0.005      # 0.5% stop loss
COMMISSION  = 0.0005     # 0.05% per side
INITIAL_CAPITAL = 10000
MC_SIMULATIONS  = 5000   # Monte Carlo runs

# ============================================================
# STEP 0: DATA LOADING
# ============================================================
def load_real_data():
    """Uses yfinance. Requires internet — run this locally."""
    import yfinance as yf
    df = yf.download(TICKER, period=PERIOD, interval=INTERVAL, progress=False)
    df.columns = [c.lower() for c in df.columns]
    return df[["open", "high", "low", "close", "volume"]].dropna()


def load_synthetic_data(n=5000, seed=42):
    """Only used here in the sandbox (no internet) to test the pipeline logic."""
    rng = np.random.default_rng(seed)
    # Random walk with slight upward drift + mean-reverting noise, mimics 5-min bars
    returns = rng.normal(loc=0.00003, scale=0.0015, size=n)
    price = 100 * np.exp(np.cumsum(returns))
    df = pd.DataFrame({
        "open": price * (1 + rng.normal(0, 0.0003, n)),
        "high": price * (1 + np.abs(rng.normal(0, 0.0008, n))),
        "low":  price * (1 - np.abs(rng.normal(0, 0.0008, n))),
        "close": price,
        "volume": rng.integers(50000, 500000, n)
    })
    return df


# ============================================================
# STEP 2: BACKTEST
# ============================================================
def run_backtest(df):
    df = df.copy()
    df["ema"] = df["close"].ewm(span=EMA_LEN, adjust=False).mean()

    in_position = False
    entry_price = 0
    trades = []  # list of trade returns (net, after commission)

    for i in range(1, len(df)):
        price = df["close"].iloc[i]
        ema = df["ema"].iloc[i]
        prev_price = df["close"].iloc[i - 1]
        prev_ema = df["ema"].iloc[i - 1]

        if not in_position:
            # entry: bullish crossover of price over EMA
            if prev_price <= prev_ema and price > ema:
                in_position = True
                entry_price = price
        else:
            change = (price - entry_price) / entry_price
            if change >= TARGET_PCT:
                net = TARGET_PCT - 2 * COMMISSION
                trades.append(net)
                in_position = False
            elif change <= -STOP_PCT:
                net = -STOP_PCT - 2 * COMMISSION
                trades.append(net)
                in_position = False

    trades = np.array(trades)
    equity_curve = INITIAL_CAPITAL * np.cumprod(1 + trades)
    equity_curve = np.insert(equity_curve, 0, INITIAL_CAPITAL)

    total_return = (equity_curve[-1] / INITIAL_CAPITAL - 1) * 100
    win_rate = (trades > 0).mean() * 100 if len(trades) else 0
    avg_win = trades[trades > 0].mean() if (trades > 0).any() else 0
    avg_loss = trades[trades < 0].mean() if (trades < 0).any() else 0
    sharpe = (trades.mean() / trades.std()) * np.sqrt(252) if trades.std() > 0 else 0

    results = {
        "num_trades": len(trades),
        "total_return_pct": total_return,
        "win_rate_pct": win_rate,
        "avg_win_pct": avg_win * 100,
        "avg_loss_pct": avg_loss * 100,
        "sharpe_approx": sharpe,
        "trades": trades,
        "equity_curve": equity_curve
    }
    return results


# ============================================================
# STEP 10: DRAWDOWN ANALYSIS
# ============================================================
def drawdown_analysis(equity_curve):
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - running_max) / running_max
    max_dd = drawdown.min() * 100

    # recovery time: bars from trough back to prior peak
    recovery_times = []
    in_dd = False
    dd_start = 0
    for i in range(1, len(equity_curve)):
        if drawdown[i] < 0 and not in_dd:
            in_dd = True
            dd_start = i
        elif drawdown[i] == 0 and in_dd:
            recovery_times.append(i - dd_start)
            in_dd = False

    avg_recovery = np.mean(recovery_times) if recovery_times else None
    return {
        "max_drawdown_pct": max_dd,
        "avg_recovery_bars": avg_recovery,
        "drawdown_series": drawdown
    }


# ============================================================
# STEP 9: MONTE CARLO SIMULATION
# ============================================================
def monte_carlo(trades, n_sims=MC_SIMULATIONS, capital=INITIAL_CAPITAL):
    if len(trades) < 5:
        return None  # not enough trades to resample meaningfully

    final_equities = []
    max_dds = []

    for _ in range(n_sims):
        sim_trades = np.random.choice(trades, size=len(trades), replace=True)
        eq = capital * np.cumprod(1 + sim_trades)
        eq = np.insert(eq, 0, capital)
        running_max = np.maximum.accumulate(eq)
        dd = (eq - running_max) / running_max
        final_equities.append(eq[-1])
        max_dds.append(dd.min() * 100)

    final_equities = np.array(final_equities)
    max_dds = np.array(max_dds)

    prob_loss = (final_equities < capital).mean() * 100
    return {
        "prob_of_loss_pct": prob_loss,
        "median_final_equity": np.median(final_equities),
        "p5_final_equity": np.percentile(final_equities, 5),
        "p95_final_equity": np.percentile(final_equities, 95),
        "worst_case_dd_pct": max_dds.min(),
        "median_dd_pct": np.median(max_dds)
    }


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print(f"Loading data for {TICKER}...")
    try:
        df = load_real_data()
        print("Loaded REAL data via yfinance.")
    except Exception as e:
        print(f"[No internet / yfinance unavailable here: {e}]")
        print("Using SYNTHETIC data to demonstrate pipeline logic instead.")
        df = load_synthetic_data()

    print(f"\nBars loaded: {len(df)}")

    # Step 2
    bt = run_backtest(df)
    print("\n=== STEP 2: BACKTEST RESULTS ===")
    print(f"Trades:          {bt['num_trades']}")
    print(f"Win rate:        {bt['win_rate_pct']:.2f}%")
    print(f"Avg win:         {bt['avg_win_pct']:.3f}%")
    print(f"Avg loss:        {bt['avg_loss_pct']:.3f}%")
    print(f"Total return:    {bt['total_return_pct']:.2f}%")
    print(f"Sharpe (approx): {bt['sharpe_approx']:.2f}")

    # Step 10
    dd = drawdown_analysis(bt["equity_curve"])
    print("\n=== STEP 10: DRAWDOWN ANALYSIS ===")
    print(f"Max drawdown:      {dd['max_drawdown_pct']:.2f}%")
    print(f"Avg recovery bars: {dd['avg_recovery_bars']}")

    # Step 9
    mc = monte_carlo(bt["trades"])
    print("\n=== STEP 9: MONTE CARLO SIMULATION ===")
    if mc:
        print(f"Probability of loss:      {mc['prob_of_loss_pct']:.2f}%")
        print(f"Median final equity:      ${mc['median_final_equity']:.2f}")
        print(f"5th pct (bad case):       ${mc['p5_final_equity']:.2f}")
        print(f"95th pct (good case):     ${mc['p95_final_equity']:.2f}")
        print(f"Worst-case drawdown:      {mc['worst_case_dd_pct']:.2f}%")
        print(f"Median drawdown:          {mc['median_dd_pct']:.2f}%")
    else:
        print("Not enough trades to run Monte Carlo reliably.")

    # Plot
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    axes[0].plot(bt["equity_curve"])
    axes[0].set_title(f"{TICKER} - Equity Curve")
    axes[0].set_ylabel("Equity ($)")

    axes[1].fill_between(range(len(dd["drawdown_series"])), dd["drawdown_series"] * 100, 0, color="red", alpha=0.5)
    axes[1].set_title("Drawdown (%)")
    axes[1].set_ylabel("Drawdown %")

    plt.tight_layout()
    plt.savefig("/mnt/user-data/outputs/ema_backtest_results.png", dpi=120)
    print("\nChart saved.")
