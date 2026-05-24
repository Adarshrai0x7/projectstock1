"""
Technical Indicators Module.
Calculates RSI, MACD, SMA, EMA, Bollinger Bands, and volume analysis
from historical price data fetched via yfinance.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    yf = None
    pd = None
    np = None
    logger.warning("yfinance/pandas/numpy not available")

try:
    import pandas_ta as ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    logger.warning("pandas-ta not available — extended technical indicators disabled")


@dataclass
class IndicatorResult:
    """Result of a single indicator calculation."""
    value: Optional[float] = None
    signal: str = "NEUTRAL"  # "BUY", "SELL", "NEUTRAL"
    description: str = ""


class TechnicalIndicators:
    """
    Calculate technical analysis indicators from stock price data.
    Uses pandas for efficient vectorized calculations.
    """
    
    def __init__(self):
        """Initialize with empty state."""
        self._cache: Dict[str, Any] = {}
    
    def get_all_indicators(self, symbol: str, period: str = "6mo") -> Dict[str, Any]:
        """
        Calculate ALL technical indicators for a stock.
        
        Args:
            symbol: yfinance-compatible symbol (e.g., 'TCS.NS', 'NVDA')
            period: Data period for calculations (default: 6 months)
            
        Returns:
            Dict with all indicator values and signals
        """
        if pd is None or yf is None:
            logger.warning("pandas/yfinance not available")
            return self._empty_indicators()
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            
            if df.empty or len(df) < 20:
                logger.warning(f"Insufficient data for {symbol}: {len(df)} rows")
                return self._empty_indicators()
            
            # Calculate all indicators
            indicators = {
                "rsi": self.calculate_rsi(df),
                "sma_20": self.calculate_sma(df, 20),
                "sma_50": self.calculate_sma(df, 50),
                "sma_200": self.calculate_sma(df, 200),
                "ema_12": self.calculate_ema(df, 12),
                "ema_26": self.calculate_ema(df, 26),
                "macd": self.calculate_macd(df),
                "bollinger": self.calculate_bollinger(df),
                "volume_analysis": self.calculate_volume_analysis(df),
                "current_price": float(df['Close'].iloc[-1]),
            }
            
            # Merge extended indicators if available
            extended = self.get_extended_indicators(df)
            indicators.update(extended)
            
            # Generate composite signal
            indicators["composite_signal"] = self._composite_signal(indicators)
            indicators["composite_score"] = self._composite_score(indicators)
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            return self._empty_indicators()
    
    # ========================================================================
    # RSI (Relative Strength Index)
    # ========================================================================
    
    def calculate_rsi(self, df, period: int = 14) -> Dict[str, Any]:
        """
        Calculate RSI (Relative Strength Index).
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss over N periods
        
        Signal:
            < 30: Oversold (potential BUY)
            > 70: Overbought (potential SELL)
            30-70: Neutral
        """
        try:
            delta = df['Close'].diff()
            
            gain = delta.where(delta > 0, 0.0)
            loss = (-delta).where(delta < 0, 0.0)
            
            avg_gain = gain.rolling(window=period, min_periods=period).mean()
            avg_loss = loss.rolling(window=period, min_periods=period).mean()
            
            rs = avg_gain / avg_loss.replace(0, float('inf'))
            rsi = 100 - (100 / (1 + rs))
            
            current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
            
            # Determine signal
            signal = "NEUTRAL"
            description = ""
            if current_rsi is not None:
                if current_rsi < 30:
                    signal = "BUY"
                    description = f"RSI {current_rsi:.1f} — Oversold (potential reversal up)"
                elif current_rsi > 70:
                    signal = "SELL"
                    description = f"RSI {current_rsi:.1f} — Overbought (potential reversal down)"
                else:
                    description = f"RSI {current_rsi:.1f} — Neutral zone"
            
            return {
                "value": round(current_rsi, 2) if current_rsi else None,
                "signal": signal,
                "description": description,
            }
        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            return {"value": None, "signal": "NEUTRAL", "description": "RSI unavailable"}
    
    # ========================================================================
    # SMA (Simple Moving Average)
    # ========================================================================
    
    def calculate_sma(self, df, period: int = 20) -> Dict[str, Any]:
        """
        Calculate Simple Moving Average.
        
        Signal:
            Price > SMA: Bullish
            Price < SMA: Bearish
        """
        try:
            if len(df) < period:
                return {"value": None, "signal": "NEUTRAL", "description": f"Insufficient data for SMA-{period}"}
            
            sma = df['Close'].rolling(window=period).mean()
            current_sma = float(sma.iloc[-1])
            current_price = float(df['Close'].iloc[-1])
            
            signal = "BUY" if current_price > current_sma else "SELL"
            position = "above" if current_price > current_sma else "below"
            diff_pct = ((current_price - current_sma) / current_sma) * 100
            
            return {
                "value": round(current_sma, 2),
                "signal": signal,
                "description": f"Price {position} SMA-{period} by {abs(diff_pct):.1f}%",
            }
        except Exception as e:
            logger.error(f"SMA-{period} calculation error: {e}")
            return {"value": None, "signal": "NEUTRAL", "description": f"SMA-{period} unavailable"}
    
    # ========================================================================
    # EMA (Exponential Moving Average)
    # ========================================================================
    
    def calculate_ema(self, df, period: int = 12) -> Dict[str, Any]:
        """
        Calculate Exponential Moving Average.
        EMA gives more weight to recent prices (reacts faster than SMA).
        """
        try:
            ema = df['Close'].ewm(span=period, adjust=False).mean()
            current_ema = float(ema.iloc[-1])
            current_price = float(df['Close'].iloc[-1])
            
            signal = "BUY" if current_price > current_ema else "SELL"
            position = "above" if current_price > current_ema else "below"
            
            return {
                "value": round(current_ema, 2),
                "signal": signal,
                "description": f"Price {position} EMA-{period}",
            }
        except Exception as e:
            logger.error(f"EMA-{period} calculation error: {e}")
            return {"value": None, "signal": "NEUTRAL", "description": f"EMA-{period} unavailable"}
    
    # ========================================================================
    # MACD (Moving Average Convergence Divergence)
    # ========================================================================
    
    def calculate_macd(self, df) -> Dict[str, Any]:
        """
        Calculate MACD.
        
        MACD Line = EMA(12) - EMA(26)
        Signal Line = EMA(9) of MACD Line
        Histogram = MACD - Signal
        
        Signal:
            MACD > Signal (histogram > 0): Bullish
            MACD < Signal (histogram < 0): Bearish
            Crossover: Strong signal
        """
        try:
            ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
            
            macd_line = ema_12 - ema_26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            histogram = macd_line - signal_line
            
            current_macd = float(macd_line.iloc[-1])
            current_signal = float(signal_line.iloc[-1])
            current_histogram = float(histogram.iloc[-1])
            
            # Check for crossover (last 2 bars)
            prev_histogram = float(histogram.iloc[-2]) if len(histogram) >= 2 else 0
            
            signal = "NEUTRAL"
            description = ""
            
            if current_histogram > 0 and prev_histogram <= 0:
                signal = "BUY"
                description = "MACD bullish crossover (strong buy signal)"
            elif current_histogram < 0 and prev_histogram >= 0:
                signal = "SELL"
                description = "MACD bearish crossover (strong sell signal)"
            elif current_histogram > 0:
                signal = "BUY"
                description = f"MACD bullish (histogram: +{current_histogram:.2f})"
            else:
                signal = "SELL"
                description = f"MACD bearish (histogram: {current_histogram:.2f})"
            
            return {
                "macd": round(current_macd, 2),
                "signal_line": round(current_signal, 2),
                "histogram": round(current_histogram, 2),
                "signal": signal,
                "description": description,
            }
        except Exception as e:
            logger.error(f"MACD calculation error: {e}")
            return {"macd": None, "signal_line": None, "histogram": None, "signal": "NEUTRAL", "description": "MACD unavailable"}
    
    # ========================================================================
    # Bollinger Bands
    # ========================================================================
    
    def calculate_bollinger(self, df, period: int = 20, std_dev: float = 2.0) -> Dict[str, Any]:
        """
        Calculate Bollinger Bands.
        
        Upper Band = SMA(20) + 2 × StdDev
        Lower Band = SMA(20) - 2 × StdDev
        
        Signal:
            Price near lower band: Potential buy (oversold)
            Price near upper band: Potential sell (overbought)
            Band squeeze: Volatility breakout coming
        """
        try:
            sma = df['Close'].rolling(window=period).mean()
            std = df['Close'].rolling(window=period).std()
            
            upper = sma + (std_dev * std)
            lower = sma - (std_dev * std)
            
            current_price = float(df['Close'].iloc[-1])
            current_upper = float(upper.iloc[-1])
            current_lower = float(lower.iloc[-1])
            current_sma = float(sma.iloc[-1])
            
            # Band width (measure of volatility)
            band_width = ((current_upper - current_lower) / current_sma) * 100
            
            # Position within bands (0 = lower, 1 = upper)
            band_position = (current_price - current_lower) / (current_upper - current_lower) if (current_upper - current_lower) > 0 else 0.5
            
            signal = "NEUTRAL"
            description = ""
            
            if band_position <= 0.1:
                signal = "BUY"
                description = f"Price at lower Bollinger Band — oversold"
            elif band_position >= 0.9:
                signal = "SELL"
                description = f"Price at upper Bollinger Band — overbought"
            elif band_width < 5:
                description = f"Bollinger squeeze — volatility breakout expected"
            else:
                description = f"Price within Bollinger Bands ({band_position:.0%} position)"
            
            return {
                "upper": round(current_upper, 2),
                "lower": round(current_lower, 2),
                "middle": round(current_sma, 2),
                "band_width": round(band_width, 2),
                "band_position": round(band_position, 2),
                "signal": signal,
                "description": description,
            }
        except Exception as e:
            logger.error(f"Bollinger calculation error: {e}")
            return {"upper": None, "lower": None, "middle": None, "signal": "NEUTRAL", "description": "Bollinger unavailable"}
    
    # ========================================================================
    # Volume Analysis
    # ========================================================================
    
    def calculate_volume_analysis(self, df, period: int = 20) -> Dict[str, Any]:
        """
        Analyze volume relative to average.
        
        Volume Ratio = Current Volume / Avg Volume (20-day)
        
        Signal:
            > 2.0: Very high volume (confirmation of trend)
            > 1.5: Above average
            < 0.5: Very low volume (weak move)
        """
        try:
            avg_volume = df['Volume'].rolling(window=period).mean()
            current_volume = float(df['Volume'].iloc[-1])
            current_avg = float(avg_volume.iloc[-1])
            
            ratio = current_volume / current_avg if current_avg > 0 else 1.0
            
            description = ""
            if ratio > 2.0:
                description = f"Very high volume ({ratio:.1f}x avg) — strong conviction"
            elif ratio > 1.5:
                description = f"Above average volume ({ratio:.1f}x avg)"
            elif ratio < 0.5:
                description = f"Very low volume ({ratio:.1f}x avg) — weak move"
            else:
                description = f"Normal volume ({ratio:.1f}x avg)"
            
            return {
                "current_volume": int(current_volume),
                "avg_volume_20d": int(current_avg),
                "volume_ratio": round(ratio, 2),
                "description": description,
            }
        except Exception as e:
            logger.error(f"Volume analysis error: {e}")
            return {"current_volume": None, "avg_volume_20d": None, "volume_ratio": None, "description": "Volume unavailable"}
    
    # ========================================================================
    # Composite Signal & Score
    # ========================================================================
    
    def _composite_signal(self, indicators: Dict) -> str:
        """Generate a composite BUY/SELL/HOLD signal from all indicators."""
        buy_count = 0
        sell_count = 0
        total = 0
        
        # Count signals from each indicator
        for key in ["rsi", "sma_20", "sma_50", "ema_12", "ema_26"]:
            if key in indicators and indicators[key].get("signal"):
                total += 1
                if indicators[key]["signal"] == "BUY":
                    buy_count += 1
                elif indicators[key]["signal"] == "SELL":
                    sell_count += 1
        
        # MACD
        if "macd" in indicators and indicators["macd"].get("signal"):
            total += 1
            if indicators["macd"]["signal"] == "BUY":
                buy_count += 1
            elif indicators["macd"]["signal"] == "SELL":
                sell_count += 1
        
        # Bollinger
        if "bollinger" in indicators and indicators["bollinger"].get("signal"):
            total += 1
            if indicators["bollinger"]["signal"] == "BUY":
                buy_count += 1
            elif indicators["bollinger"]["signal"] == "SELL":
                sell_count += 1
        
        if total == 0:
            return "NEUTRAL"
        
        buy_pct = buy_count / total
        sell_pct = sell_count / total
        
        if buy_pct >= 0.6:
            return "BUY"
        elif sell_pct >= 0.6:
            return "SELL"
        else:
            return "HOLD"
    
    def _composite_score(self, indicators: Dict) -> float:
        """
        Generate a 0-100 composite technical score.
        
        50 = neutral, >70 = bullish, <30 = bearish
        """
        scores = []
        
        # RSI contributes (inverted scale for oversold)
        rsi_val = indicators.get("rsi", {}).get("value")
        if rsi_val is not None:
            # RSI 30 = score 80 (oversold = buy opportunity)
            # RSI 50 = score 50 (neutral)
            # RSI 70 = score 20 (overbought = sell risk)
            rsi_score = max(0, min(100, 100 - rsi_val))
            scores.append(rsi_score)
        
        # SMA signals
        for key in ["sma_20", "sma_50"]:
            sig = indicators.get(key, {}).get("signal")
            if sig == "BUY":
                scores.append(70)
            elif sig == "SELL":
                scores.append(30)
            else:
                scores.append(50)
        
        # MACD
        macd_sig = indicators.get("macd", {}).get("signal")
        if macd_sig == "BUY":
            scores.append(75)
        elif macd_sig == "SELL":
            scores.append(25)
        else:
            scores.append(50)
        
        # Bollinger position
        bb_pos = indicators.get("bollinger", {}).get("band_position")
        if bb_pos is not None:
            # Lower position = higher score (buy opportunity)
            bb_score = max(0, min(100, (1 - bb_pos) * 100))
            scores.append(bb_score)
        
        if not scores:
            return 50.0
        
        return round(sum(scores) / len(scores), 1)
    
    def _empty_indicators(self) -> Dict[str, Any]:
        """Return empty indicators when data is unavailable."""
        empty = {"value": None, "signal": "NEUTRAL", "description": "Data unavailable"}
        return {
            "rsi": empty.copy(),
            "sma_20": empty.copy(),
            "sma_50": empty.copy(),
            "sma_200": empty.copy(),
            "ema_12": empty.copy(),
            "ema_26": empty.copy(),
            "macd": {"macd": None, "signal_line": None, "histogram": None, "signal": "NEUTRAL", "description": "Data unavailable"},
            "bollinger": {"upper": None, "lower": None, "middle": None, "signal": "NEUTRAL", "description": "Data unavailable"},
            "volume_analysis": {"current_volume": None, "avg_volume_20d": None, "volume_ratio": None, "description": "Data unavailable"},
            "current_price": None,
            "composite_signal": "NEUTRAL",
            "composite_score": 50.0,
            "supertrend": {"value": None, "signal": "NEUTRAL", "description": "Data unavailable"},
            "adx": {"value": None, "signal": "NEUTRAL", "description": "Data unavailable"},
            "stochastic": {"k": None, "d": None, "signal": "NEUTRAL", "description": "Data unavailable"},
            "vwap": {"value": None, "signal": "NEUTRAL", "description": "Data unavailable"},
        }
    
    # ========================================================================
    # Extended Indicators (pandas-ta required)
    # ========================================================================
    
    def get_extended_indicators(self, df) -> Dict[str, Any]:
        """Calculate advanced indicators using pandas-ta."""
        extended = {}
        if not TA_AVAILABLE or len(df) < 50:
            return extended
            
        try:
            # 1. Supertrend (7, 3)
            sti = df.ta.supertrend(length=7, multiplier=3)
            if sti is not None and not sti.empty:
                direction_col = [c for c in sti.columns if c.startswith('SUPERTd_')][0]
                value_col = [c for c in sti.columns if c.startswith('SUPERT_')][0]
                
                direction = int(sti[direction_col].iloc[-1])
                st_value = float(sti[value_col].iloc[-1])
                
                signal = "BUY" if direction > 0 else "SELL"
                desc = f"Price above Supertrend ({st_value:.2f})" if direction > 0 else f"Price below Supertrend ({st_value:.2f})"
                
                extended["supertrend"] = {
                    "value": round(st_value, 2),
                    "signal": signal,
                    "description": desc
                }
                
            # 2. ADX (Average Directional Index) — trend strength
            adx_df = df.ta.adx(length=14)
            if adx_df is not None and not adx_df.empty:
                adx_col = [c for c in adx_df.columns if c.startswith('ADX_')][0]
                adx_val = float(adx_df[adx_col].iloc[-1])
                
                desc = "Strong Trend" if adx_val > 25 else "Weak/No Trend"
                
                extended["adx"] = {
                    "value": round(adx_val, 2),
                    "signal": "NEUTRAL", # ADX just shows strength, not direction
                    "description": f"ADX is {adx_val:.1f} ({desc})"
                }
                
            # 3. Stochastic Oscillator
            stoch_df = df.ta.stoch()
            if stoch_df is not None and not stoch_df.empty:
                k_col = [c for c in stoch_df.columns if c.startswith('STOCHk_')][0]
                d_col = [c for c in stoch_df.columns if c.startswith('STOCHd_')][0]
                
                k = float(stoch_df[k_col].iloc[-1])
                d = float(stoch_df[d_col].iloc[-1])
                
                signal = "NEUTRAL"
                desc = f"Stoch%K: {k:.1f}, %D: {d:.1f}"
                
                if k < 20 and d < 20:
                    signal = "BUY"
                    desc += " (Oversold)"
                elif k > 80 and d > 80:
                    signal = "SELL"
                    desc += " (Overbought)"
                    
                extended["stochastic"] = {
                    "k": round(k, 2),
                    "d": round(d, 2),
                    "signal": signal,
                    "description": desc
                }
                
            # 4. VWAP (Volume Weighted Average Price)
            # VWAP requires an intraday timeframe typically, but pandas-ta can approximate
            vwap_df = df.ta.vwap()
            if vwap_df is not None and not vwap_df.empty:
                vwap_val = float(vwap_df.iloc[-1])
                current_price = float(df['Close'].iloc[-1])
                
                signal = "BUY" if current_price > vwap_val else "SELL"
                pos = "above" if current_price > vwap_val else "below"
                
                extended["vwap"] = {
                    "value": round(vwap_val, 2),
                    "signal": signal,
                    "description": f"Price {pos} VWAP ({vwap_val:.2f})"
                }
                
        except Exception as e:
            logger.error(f"Error calculating extended indicators: {e}")
            
        return extended


# Singleton
_indicator_service = None

def get_indicator_service() -> TechnicalIndicators:
    """Get or create the technical indicators singleton."""
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = TechnicalIndicators()
    return _indicator_service
