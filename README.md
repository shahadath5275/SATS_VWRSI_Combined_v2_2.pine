# Pine Script Trading Strategies

TradingView Pine Script strategies and the tooling used to test them.

## Scripts

### `SATS_VWRSI_Combined_v2_2.pine`

**SATS + VWRSI Combined v2** — a merge of the Self-Aware Trend System (10 EMA
Strategy Combined) and AlgoAlpha's Volume Weighted RSI, plus a Take Profit
Planner decision layer.

The merge removed the duplication that came from running two indicators side by
side:

- Three separate RSI engines collapsed into one volume-weighted RSI.
- Chandelier Exit removed — it duplicated the SATS adaptive SuperTrend's ATR
  trailing stop and emitted competing Buy/Sell labels. Trailing is now an option
  on the SATS line.
- Two volume-confirmation paths collapsed into one z-score check.
- Standalone RSI table folded into the main dashboard.

It also fixes several logic bugs, most importantly that entries are now gated on
trend, TQI, ER, consolidation and regime edge — previously those were computed,
displayed on the dashboard, and then ignored by the order logic.

**Main components**

| Block | What it does |
| --- | --- |
| Entry Gate | Blocks counter-trend entries and enforces minimum TQI / ER / volume, consolidation limits, and a circuit breaker on loss streaks |
| Trend Quality Engine (TQI) | Blends efficiency, volatility regime, structure and momentum persistence into a 0–1 trend quality score |
| Adaptive SuperTrend | Single ATR trailing engine with quality-scaled, optionally asymmetric bands |
| Take Profit Planner | Scores the path to the nearest unhit target 0–100 and reports a plan state (TARGET READY / MONITOR / BLOCKED / …) |
| Self-Learning | Rolling R statistics, per-regime expectancy grid, optional auto-calibration |

**Take Profit Planner**

Scores the prospective or live plan on six weighted components — path clear
(0.24), distance (0.22), trend support (0.18), progress (0.14), volatility fit
(0.12), confluence (0.10) — then maps the result onto a state:

```
INVALID REVIEW  ->  stop touched (live trade only)
PLAN COMPLETE   ->  3 exec tiers tagged
TARGET NEAR     ->  within 0.30x ATR of nearest TP
BLOCKED         ->  obstruction in path AND score < Ready threshold
TARGET READY    ->  score >= Ready threshold (default 72)
MONITOR         ->  score >= Monitor threshold (default 54)
LOW QUALITY     ->  below that
```

State changes are marked on the chart, and the full ladder (entry reference,
invalidation, TP1–TP7 zones, obstruction rail) is projected to the right of
price whether you are flat or in a trade.

The Target Engine group lets you override the plan anchor: forced direction,
anchor source (pivot / close / session open / manual), and invalidation mode
(strategy SL / hybrid ATR+structure / ATR only / structure only / manual). All
defaults reproduce the strategy's native behaviour.

### `ema_strategy_combined_1.pine`

The earlier 10 EMA Strategy (Combined) that v2 was built from.

## `pinescript/`

`ema_backtest_pipeline.py` — offline backtest pipeline for the EMA strategy,
with `ema_backtest_results.png` as sample output.

## Usage

Open a script in the TradingView Pine Editor, paste the source, and click
**Add to chart**. All inputs are grouped and documented with tooltips in the
settings dialog.

## Disclaimer

For research and education. Not financial advice. Backtest results do not
predict future performance.
