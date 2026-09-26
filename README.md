# Nexora — Automated Pairs Trading Bot (US Indices)

Nexora is a statistical-arbitrage trading bot built as a personal quant-trading portfolio project, combining an Engineering Physics background with systematic trading research. It trades mean-reversion pairs across US30 (Dow), US500 (S&P), and USTEC (Nasdaq) CFDs on MetaTrader 5, with a full research → risk-management → machine-learning pipeline built and validated iteratively over several months.

**Status: research/paper-trading project, not intended for live capital.** Built to learn end-to-end systematic trading infrastructure and to serve as a portfolio piece.

---

## Overview

- **Strategy**: Z-score mean reversion on the spread between two correlated US index CFDs, with the hedge ratio estimated via OLS regression.
- **Instruments**: US30m, US500m, USTECm (Exness demo, hedging-type account) across 3 pairs (DOW-SP, NQ-SP, NQ-DOW) and 3 timeframes (M15, M30, H1).
- **Execution**: Fully automated — signal generation, order execution, exit monitoring, and risk controls all run unattended on a Windows VPS.
- **Control surface**: A Telegram bot (`/stats`, `/journal`, `/kelly`, `/ml`, `/fng`, `/sentiment`, etc.) for live monitoring and a Streamlit + Plotly dashboard for deeper performance analysis.
- **Research discipline**: Every proposed upgrade (dynamic hedge ratio, trend-following overlays, sentiment/regime filters, ML meta-labeling) was backtested and validated — or explicitly rejected — before being shipped to the live bot.

## Strategy

For each pair, a formation window (504 bars) is used to estimate the hedge ratio via OLS regression on the two instruments' prices. The resulting spread is z-scored, and:

- **Entry**: `|z| > 0.5σ` — long the undervalued leg, short the overvalued leg.
- **Exit**: z-score reverts toward 0, a fixed spread-based stop loss is hit, or the position times out (max holding time per timeframe).
- **Position sizing**: ATR-based sizing combined with a Half-Kelly Criterion overlay (50-trade rolling window, minimum 20 trades of history required before Kelly sizing activates).

## Development Journey

**Phase 1 — Core strategy**: Z-score mean-reversion pairs trading with OLS hedge ratios, ATR-based sizing, spread stop-loss and timeout exits, running as paper trades.

**Phase 2 — Infrastructure**: GitHub repo, Streamlit/Plotly performance dashboard, Telegram bot for remote monitoring and control, deployment to a Windows VPS as a persistent auto-restarting service (NSSM, running interactively so MetaTrader5's Python API can share a session with the MT5 terminal GUI).

**Phase 3 — Research validation (accept/reject upgrades on evidence)**:
- *Kalman Filter vs. static OLS* for dynamic hedge-ratio estimation — tested head-to-head via walk-forward backtests. Rejected: after tuning (minimum holding period, z-score smoothing, hedge-ratio change caps, higher entry threshold), Kalman didn't produce a statistically meaningful edge over static OLS for this intraday setup, so OLS was kept.
- *Trend-following overlays* (Volatility Breakout, Supertrend) to complement mean reversion during trending regimes — tested walk-forward (IS 2022–2023 / Val 2024 / OOS 2025–2026) with permutation tests and bootstrap confidence intervals. Rejected: consistently negative Sharpe/Sortino across all instruments and timeframes in OOS, not statistically significant even where marginally positive in-sample. Conclusion: a genuine strategy-fit issue — US indices in this period are too choppy for trend-following at these timeframes.

**Phase 4 — Risk management additions**:
- Dynamic ADX threshold (rolling mean + 0.5×rolling std, clamped 20–35) replacing a static filter.
- **Weekly gap management**: close all open positions before the weekend (Saturday 03:00 WIB, ahead of the ~04:00 WIB market close) and block new entries through the weekend until Monday 06:00 WIB (after the ~05:00 WIB market open) — added after observing repeated weekend-gap floating losses and timeouts.
- Sentiment and regime-based lot-size multipliers: Finnhub news-sentiment scoring and the Fear & Greed Index (Alternative.me), applied multiplicatively to position size rather than as a hard entry filter (e.g. extreme F&G → ×0.5 lot; strong bullish/bearish sentiment → ×1.2/×0.8).

**Phase 5 — Machine learning meta-labeling**: Every trade signal has its context logged at entry (ADX, VIX, dynamic ADX threshold, sentiment score, F&G value, lot multipliers, entry z-score, hour, day-of-week) specifically to support this phase. Four candidate models — Logistic Regression, Random Forest, XGBoost, LightGBM — were compared via stratified 5-fold cross-validation with nested hyperparameter search (Accuracy/Precision/Recall/F1/ROC-AUC) before selecting a winner, rather than assuming a model upfront. **XGBoost** was selected and deployed live as a meta-label filter: it scores the probability that a given rule-based signal will be a winner, and the bot skips low-probability signals and halves size on marginal ones, rather than predicting price directly (meta-labeling, per López de Prado's framework).

## Backtest Research Summary

| Upgrade tested | Method | Result |
|---|---|---|
| Kalman Filter hedge ratio | Walk-forward vs. static OLS | Rejected — no meaningful edge over OLS after tuning |
| Volatility Breakout | Walk-forward, IS/Val/OOS, permutation + bootstrap CI | Rejected — negative OOS Sharpe across all pairs/timeframes |
| Supertrend | Walk-forward, IS/Val/OOS | Rejected — no valid signals generated; moot given VolBreakout result |
| Meta-labeling model selection | Stratified 5-fold CV, nested GridSearchCV, 4 models | XGBoost selected on ROC-AUC/F1; deployed live |

## Live Trading Log — Results and an Honest Caveat

Across the most complete surviving trade log (303 logged trades, spanning legacy-imported history and native bot logging from late May through mid-July 2026):

| Metric | Value |
|---|---|
| Total trades | 303 |
| Net P/L | +$511.82 |
| Win rate | 58.7% |
| Profit factor | 1.27 |
| Avg win / avg loss | +$13.62 / -$16.34 |
| Trades with full ML feature logging | 127 |

**Caveat, stated plainly:** the account's actual growth over its life was larger than this log shows — informally tracked at roughly $1,000 → $1,700–1,800 in balance. Two data-loss events prevent fully reconciling that with the trade log above: the Exness demo account was auto-deleted after a period of inactivity (so no complete official MT5 statement can be pulled retroactively), and a VPS migration left an earlier segment of the CSV trade log unrecoverable. The 303-trade log above is the most complete surviving dataset and is reported as-is rather than adjusted upward to match a recalled balance figure. This gap is a real lesson from the project: **production trading infrastructure needs redundant, off-box logging (e.g. logs mirrored to cloud storage or a database) from day one, not just a local CSV.**

## System Architecture

- **bot.py** — core trading engine: MT5 data fetch, OLS spread/z-score calculation, dynamic ADX + VIX regime filters, sentiment/F&G lot multipliers, XGBoost meta-label filter, Half-Kelly position sizing, order execution with leg-rollback on partial failure, exit monitoring, weekly gap management, state persistence, Telegram command polling.
- **nexora_dashboard.py** — Streamlit + Plotly dashboard reading the trade log directly (auto-refreshing), showing equity curve with drawdown shading, rolling Sharpe, per-pair/per-timeframe/per-direction breakdowns, and a full trade journal table.
- **Deployment** — Windows Server VPS, running as an NSSM-managed interactive service (required for MetaTrader5's Python API to share a session with the MT5 terminal GUI) under a dedicated Windows account.

## Bot Features

| Feature | Description |
|---|---|
| Z-score mean reversion | OLS-based spread, 504-bar formation window |
| Dynamic ADX/VIX filters | Adaptive regime filtering vs. static thresholds |
| Half-Kelly position sizing | Rolling 50-trade window, 20-trade minimum |
| Weekly gap management | Auto-close before weekend, entry block until Monday |
| Sentiment lot multiplier | Finnhub news sentiment, multiplicative sizing |
| Fear & Greed lot multiplier | Alternative.me index, multiplicative sizing |
| ML meta-label filter | XGBoost signal-quality scoring, skip/halve on low confidence |
| Feature logging | Full entry-context logging per trade for ML research |
| Telegram control | Remote monitoring and commands |

## Telegram Commands

`/stats` `/journal` `/kelly` `/ml` `/fng` `/sentiment` — live stats, trade journal, Kelly sizing stats, ML model status, Fear & Greed reading, and sentiment reading, all queryable remotely.

## Performance Dashboard

A Streamlit + Plotly dashboard (`nexora_dashboard.py`) reads the live trade log and renders the equity curve, drawdown, rolling Sharpe, per-pair/per-timeframe/per-direction performance, and win/loss distribution — no manual data entry required.

## Dependencies

`MetaTrader5`, `pandas`, `numpy`, `statsmodels`, `scipy`, `requests`, `python-telegram-bot` (or raw polling), `scikit-learn`, `xgboost`, `joblib`, `streamlit`, `plotly`.

## Configuration

Copy `settings.example.py` to `settings.py` and fill in your own Telegram bot `TOKEN` and `CHAT_ID`. Credential-bearing files are excluded from version control via `.gitignore`.

## Status

Project complete as a research/portfolio piece. Development effort has shifted to a separate crypto-trading project. Nexora remains a reference implementation of a full systematic-trading pipeline: strategy research → validated risk management → sentiment/regime awareness → ML-based signal filtering → live deployment with monitoring.

## Background

Built by Qaishar Nabil Ishak, an Engineering Physics student, as a self-directed project to combine a physics/quantitative background with systematic trading, and to build a credible, honestly-documented portfolio piece toward a future in quantitative trading.