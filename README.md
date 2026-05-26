# Nexora — Automated Pairs Trading Bot

> Statistical arbitrage system for US equity indices  
> Built from scratch as a quantitative finance learning project

![Status](https://img.shields.io/badge/Status-Paper%20Trading-yellow)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Platform](https://img.shields.io/badge/Platform-MetaTrader%205-lightgrey)

---

## Overview

Nexora is a fully automated pairs trading bot that exploits mean reversion in the price spread between correlated US index CFDs. The system statistically identifies when a spread has deviated significantly from its historical equilibrium and trades the reversion back to mean.

**Instruments:** US30 (DOW) | US500 (S&P500) | USTEC (NASDAQ)  
**Timeframes:** H1 | M30 | M15  
**Broker:** Exness — MetaTrader 5  
**Language:** Python 3.11

---

## Strategy

### Core Logic
1. Fit OLS regression between two correlated indices over a 504-bar formation window
2. Calculate z-score of current spread vs historical mean and standard deviation
3. Enter when |z-score| > 0.5σ — exit when z-score reverts to 0

### Pairs Traded
| Pair | Instruments |
|------|-------------|
| NQ / SP | USTEC vs US500 |
| NQ / DOW | USTEC vs US30 |
| DOW / SP | US30 vs US500 |

### Risk Filters
| Filter | Threshold | Reason |
|--------|-----------|--------|
| VIX | < 25 | Avoid high volatility regimes |
| ADX | < 25 | Avoid trending markets |
| Free margin check | 120% estimated margin | Prevent overleveraging |
| Max holding time | Per-TF timeout | Force exit stale positions |

### Position Sizing
- **Base:** ATR-based dynamic lot sizing (TARGET_RISK / ATR)
- **Overlay:** Half-Kelly Criterion — updates every 10 trades
- **Range:** 0.01 — 0.10 lot

---

## Development Journey

### Phase 1 — Research & Strategy Evaluation
Replicated Gatev (2006) pairs trading on DOW/SP/NQ. Found fundamental issues: cointegration failures across all pairs, Sharpe ratio calculated from trade list instead of daily equity curve, OOS > IS anomaly, insufficient sample size.

### Phase 2 — Backtest Methodology Fix
- Fixed Sharpe ratio → calculated from daily equity curve
- Lowered entry threshold 1.0σ → 0.5σ to increase signal frequency
- Replaced cointegration with correlation-based spread mean reversion
- Added permutation test & bootstrap validation → beat random 100% across all periods

### Phase 3 — Risk Management Layer
- Replaced z-score stop loss with spread PnL-based stop loss
- Added VIX filter and ADX regime filter
- Implemented ATR volatility position sizing
- Max drawdown reduced from -7,784 → controlled levels

### Phase 4 — Timeframe Optimization
Analyzed mean reversion half-life across timeframes:
- Daily TF: half-life = 69 days (too slow for practical trading)
- M15 TF: half-life = 1.5 days (optimal)

Decision: focus on intraday timeframes H1 / M30 / M15.

### Phase 5 — Production Bot
Built full automated execution system with MetaTrader 5 integration, risk management, state persistence, and Telegram control interface.

---

## Backtest Results

*Intraday v7 Final — validated with permutation test and bootstrap resampling*

| Period | Trades | Win Rate | Sharpe |
|--------|--------|----------|--------|
| IS (2022–2023) | 102 | 74.5% | 2.40 |
| Validation (2024) | 215 | 69.8% | 3.28 |
| OOS (2025–2026) | 345 | 76.2% | 4.28 |

> OOS Sharpe improvement attributed to favorable mean-reverting regime in 2025. Continued forward testing in progress to validate consistency.

---

## System Architecture

```
nexora/
├── nexora_bot.py          # Core bot — MT5 execution, signal engine, risk management
├── nexora_dashboard.py    # Streamlit performance dashboard
├── nexora_trades.csv      # Live trade log (auto-generated)
├── nexora_state.json      # Position state persistence (auto-generated)
└── settings.example.py   # Config template (copy to settings.py)
```

### Bot Features
| Feature | Status |
|---------|--------|
| Auto execution via MT5 API | ✅ |
| Z-score entry & exit signals | ✅ |
| Spread PnL stop loss | ✅ |
| Double position protection | ✅ |
| Free margin validation | ✅ |
| State persistence (safe restart) | ✅ |
| Weekend position restore | ✅ |
| Kelly Criterion sizing | ✅ |
| VIX regime filter | ✅ |
| ADX regime filter | ✅ |
| CSV trade logging | ✅ |
| Telegram control interface | ✅ |

### Telegram Commands
```
/on      — Activate bot
/off     — Deactivate bot
/status  — Open positions + z-score + floating PnL
/zscore  — Real-time z-score all pairs
/stats   — Overall trading statistics
/journal — Last 10 closed trades
/kelly   — Kelly sizing statistics
/close   — Close all positions
/vix     — Current VIX reading
/adx     — ADX per timeframe
/help    — Command list
```

---

## Performance Dashboard

Built with Streamlit. Auto-reads `nexora_trades.csv` every 30 seconds — no manual input required.

**Metrics:**
- Equity curve with drawdown shading
- Rolling Sharpe (20-trade window)
- PnL breakdown by pair, timeframe, direction
- Average win / average loss analysis
- PnL distribution histogram
- Live trade log table

**Run locally:**
```bash
pip install streamlit plotly pandas numpy
streamlit run nexora_dashboard.py --server.port 8501
```

---

## Dependencies

```bash
pip install MetaTrader5 pandas numpy statsmodels yfinance requests pytz streamlit plotly
```

---

## Configuration

Copy `settings.example.py` to `settings.py` and fill in your credentials:

```python
TOKEN   = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
```

---

## Status

🟡 **Paper Trading** — Forward testing in progress  
Target: 100 trades before live capital evaluation

---

## Background

Built by a Physics Engineering student at a Indonesian university, exploring the intersection of statistical physics, signal processing, and quantitative finance. This project applies time series analysis, regression modeling, and statistical validation methods to systematic trading strategy development.

*Part of a long-term path toward quantitative trading research and prop trading.*
