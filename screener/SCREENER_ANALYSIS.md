# Screener Analysis Report

## Current Architecture

```
screener/
├── technical_indicators.py  (486 lines) — Indicator calculations
├── screener.py              (363 lines) — Core screening engine
└── screener_formatter.py    (159 lines) — Chat output formatting
```

---

## Existing Features

### Technical Indicators (`technical_indicators.py`)

| Indicator | What It Does | Buy/Sell Signal Logic |
|---|---|---|
| **RSI (14)** | Measures momentum (0–100) | <30 = Buy (oversold), >70 = Sell (overbought) |
| **SMA (20, 50, 200)** | Simple Moving Averages | Price above = Buy, below = Sell |
| **EMA (12, 26)** | Exponential Moving Averages | Price above = Buy, below = Sell |
| **MACD** | EMA(12)−EMA(26) with signal line | Histogram >0 = Bullish, crossover detected |
| **Bollinger Bands** | 20-day SMA ± 2σ bands | Near lower band = Buy, upper = Sell, squeeze detected |
| **Volume Analysis** | Current vs 20-day avg volume | >1.5x = high, <0.5x = weak move |
| **Composite Signal** | Majority-vote of all indicators | ≥60% BUY = BUY, ≥60% SELL = SELL, else HOLD |
| **Composite Score** | 0–100 weighted blend | Combines RSI, SMA, MACD, Bollinger into one number |

### Fundamental Metrics (`screener.py → _get_fundamentals`)

| Metric | Source |
|---|---|
| P/E Ratio | `yfinance.info.trailingPE` |
| P/B Ratio | `yfinance.info.priceToBook` |
| ROE | Computed: Net Income / Equity |
| Debt/Equity | `yfinance.info.debtToEquity` |
| EPS | `yfinance.info.trailingEps` |
| Dividend Yield | `yfinance.info.dividendYield` |
| Market Cap | `yfinance.info.marketCap` |
| Revenue Growth | `yfinance.info.revenueGrowth` |
| Profit Margin | `yfinance.info.profitMargins` |
| Sector & Industry | `yfinance.info.sector` / `industry` |

### Pre-Built Screens (5 total)

| Screen | Key Filters |
|---|---|
| **Undervalued** | PE ≤ 20, PB ≤ 3, ROE ≥ 12% |
| **Momentum** | RSI 50–70, above SMA-50, MACD bullish |
| **Oversold** | RSI ≤ 35 |
| **High Dividend** | Dividend yield ≥ 2%, PE ≤ 25 |
| **Strong Fundamentals** | ROE ≥ 15%, D/E ≤ 1.0, Margin ≥ 10% |

### Filtering Engine (12 filter types)

`pe_ratio_max/min`, `pb_ratio_max`, `roe_min`, `debt_to_equity_max`, `dividend_yield_min`, `profit_margin_min`, `rsi_max/min`, `above_sma_50`, `macd_bullish`, `score_min`

### API Endpoints (4 total)

| Endpoint | Method | Function |
|---|---|---|
| `/screener/screens` | GET | List available screens |
| `/analyze/{symbol}` | GET | Full stock analysis |
| `/screener/{screen_name}` | GET | Run pre-built screen |
| `/screener/custom` | POST | Run custom screen with filters |

### Other Details
- **Stock Universe:** Hardcoded Nifty 50 list (50 stocks)
- **Concurrency:** Batch-scans 5 stocks in parallel
- **Market Support:** NSE (India) + US market detection
- **Formatter:** Emoji-rich chat output with signal colors, tables, currency formatting (₹/$ aware)

---

## What We Can Add

### 🔴 High Priority — Missing Core Indicators

| Feature | Why It Matters |
|---|---|
| **ADX (Average Directional Index)** | Measures trend strength (0–100). Currently no way to detect strong vs weak trends |
| **Stochastic Oscillator** | Better oversold/overbought detection than RSI alone — uses %K and %D crossovers |
| **VWAP (Volume-Weighted Avg Price)** | Standard institutional indicator — shows fair value based on volume |
| **ATR (Average True Range)** | Measures volatility in absolute terms — useful for position sizing and stop-loss |
| **OBV (On-Balance Volume)** | Detects volume-driven accumulation/distribution before price moves |
| **Support & Resistance Levels** | Auto-detect key price levels from historical pivots |

### 🟡 Medium Priority — Smarter Screening

| Feature | Why It Matters |
|---|---|
| **More pre-built screens** | Add: "52-week high breakouts", "golden cross (SMA50×SMA200)", "gap-up stocks", "large cap growth" |
| **Sector-wise screening** | Filter/group results by sector (IT, Banking, Pharma, etc.) — data already available |
| **Comparative rankings** | Rank stocks within a sector (e.g., "best IT stock by score") |
| **Dynamic stock universe** | Replace hardcoded Nifty 50 with Nifty 100/200/500 or user-provided watchlists |
| **Score breakdown** | Show users *why* a stock scored 73 — which indicators contributed what |
| **Historical screen results** | Cache/store past screen results to track how picks performed over time |
| **Multi-timeframe analysis** | Run indicators on daily + weekly + monthly for stronger confirmation |
| **Trend classification** | Label stocks as "Uptrend / Downtrend / Sideways / Breakout" using SMA alignment |

### 🟢 Nice to Have — UX & Performance

| Feature | Why It Matters |
|---|---|
| **Caching for screener results** | Full Nifty 50 scan is slow (~50 API calls). Cache for 15–30 min |
| **Progress updates** | Stream progress during screening: "Analyzing 12/50..." via WebSocket |
| **PDF/Excel export** | Let users export analysis results |
| **Alert system** | Notify when a stock hits certain RSI/price/volume thresholds |
| **Backtesting** | Test how a screen would have performed historically |
| **Candlestick patterns** | Detect doji, hammer, engulfing etc. from OHLC data |

---

## Summary

**What's solid:** The screener has a good foundation — 6 technical indicators, 9 fundamental metrics, 5 pre-built screens, composite scoring, and a clean filtering engine.

**Biggest gaps:**
1. **No trend-strength indicators** (ADX, Stochastic) — hard to tell if a trend is real
2. **No volatility/risk metrics** (ATR) — can't size positions or set stop-losses
3. **No support/resistance** — the most-watched levels by traders are missing
4. **Hardcoded Nifty 50** — no flexibility in stock universe
5. **No caching** — every screen scans all 50 stocks from scratch
