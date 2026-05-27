"""
Market data service for real-time stock and index information.
Uses yfinance as the primary data source (free, reliable for Indian stocks).
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from functools import lru_cache
import logging

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    from jugaad_data.nse import NSELive
    _nse_live = NSELive()
    JUGAAD_AVAILABLE = True
except ImportError:
    _nse_live = None
    JUGAAD_AVAILABLE = False
    
from common.models.schemas import StockPrice, IndexData, StockDetails, MarketMovers, Market, StockHistory, StockHistoryDay
from common.utils.cache import cache_with_ttl
from chatbot.core.symbol_registry import (
    INDEX_YF_SYMBOLS, INDICES, STOCK_NAME_MAP, NSE_SUFFIX, BSE_SUFFIX,
    get_index_yf_symbol,
)

logger = logging.getLogger(__name__)

INDEX_SYMBOLS: dict[str, str] = {}
for _variant, _canonical in INDICES.items():
    _yf = INDEX_YF_SYMBOLS.get(_canonical)
    if _yf:
        INDEX_SYMBOLS[_variant] = _yf


class MarketDataService:
    """
    Service for fetching real-time and historical market data.
    Uses yfinance for data retrieval with caching.
    """
    
    def __init__(self, default_market: str = "NSE"):
        """
        Initialize market data service.
        
        Args:
            default_market: Default market (NSE or BSE)
        """
        self.default_market = default_market
        self._cache: Dict[str, tuple] = {}  # (value, expiry_time)
        self._cache_ttl = 30  # seconds
        
        if yf is None:
            logger.error("CRITICAL: yfinance not installed. Run: pip install yfinance")
    
    def _get_yf_symbol(self, symbol: str, market: str = None) -> str:
        """Convert symbol to yfinance format."""
        market = market or self.default_market
        
        # Check if it's an index
        if symbol.upper() in INDEX_SYMBOLS:
            return INDEX_SYMBOLS[symbol.upper()]
        
        # Add market suffix
        symbol = symbol.upper()
        if market == "US":
            return symbol  # US stocks use bare symbol
        elif market == "NSE" and not symbol.endswith(NSE_SUFFIX):
            return f"{symbol}{NSE_SUFFIX}"
        elif market == "BSE" and not symbol.endswith(BSE_SUFFIX):
            return f"{symbol}{BSE_SUFFIX}"
        
        return symbol
    
    def _detect_market(self, symbol: str) -> tuple:
        """
        Smart market detection: tries NSE first, then US.
        Returns (yf_symbol, detected_market) tuple.
        """
        if yf is None:
            return f"{symbol.upper()}{NSE_SUFFIX}", "NSE"
        
        symbol_upper = symbol.upper()
        
        
        if symbol_upper in INDEX_SYMBOLS:
            return INDEX_SYMBOLS[symbol_upper], "INDEX"
        
       
        nse_symbol = symbol_upper if symbol_upper.endswith(NSE_SUFFIX) else f"{symbol_upper}{NSE_SUFFIX}"
        try:
            ticker = yf.Ticker(nse_symbol)
            info = ticker.info
            price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            if price and price > 0:
                return nse_symbol, "NSE"
        except Exception:
            pass
        
        # Try US market (bare symbol)
        try:
            ticker = yf.Ticker(symbol_upper)
            info = ticker.info
            price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            if price and price > 0:
                return symbol_upper, "US"
        except Exception:
            pass
        
        # Default to NSE
        return nse_symbol, "NSE"
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any, ttl: int = None):
        """Set value in cache with TTL."""
        ttl = ttl or self._cache_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)
    
    async def get_stock_price(
        self, 
        symbol: str, 
        market: str = None
    ) -> Optional[StockPrice]:
        """
        Get current stock price. Automatically detects market if not specified.
        
        Args:
            symbol: Stock symbol (e.g., 'TCS', 'RELIANCE', 'NVDA', 'AAPL')
            market: Market hint (NSE, BSE, US) — auto-detected if None
            
        Returns:
            StockPrice object or None if not found
        """
        cache_key = f"price:{symbol}:{market or 'auto'}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
           
            if JUGAAD_AVAILABLE and market != "US":
                try:
                    quote = _nse_live.get_quote(symbol.upper())
                    if quote and "priceInfo" in quote:
                        pi = quote["priceInfo"]
                        current = pi.get("lastPrice", 0)
                        prev = pi.get("previousClose", current)
                        if current and current > 0:
                            change = current - prev
                            change_pct = (change / prev * 100) if prev else 0
                            stock_price = StockPrice(
                                symbol=symbol.upper(),
                                name=STOCK_NAME_MAP.get(symbol.upper(), symbol),
                                price=round(current, 2),
                                change=round(change, 2),
                                change_percent=round(change_pct, 2),
                                volume=pi.get("totalTradedVolume"),
                                high=pi.get("intraDayHighLow", {}).get("max"),
                                low=pi.get("intraDayHighLow", {}).get("min"),
                                prev_close=prev,
                                market=Market.NSE
                            )
                            self._set_cache(cache_key, stock_price)
                            return stock_price
                except Exception as je:
                    logger.debug(f"jugaad-trader failed for {symbol}, falling back to yfinance: {je}")

            if yf is None:
                return None
            
            if market:
                yf_symbol = self._get_yf_symbol(symbol, market)
                detected_market = market
            else:
                yf_symbol, detected_market = self._detect_market(symbol)
            
           
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            
          
            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            if not current_price or current_price == 0:
                return None
            
            prev_close = info.get('previousClose', info.get('regularMarketPreviousClose', current_price))
            
            change = current_price - prev_close
            change_percent = (change / prev_close * 100) if prev_close else 0
            
           
            currency = "$" if detected_market == "US" else "\u20b9"
            
            stock_price = StockPrice(
                symbol=symbol.upper(),
                name=STOCK_NAME_MAP.get(symbol.upper(), info.get('shortName', symbol)),
                price=round(current_price, 2),
                change=round(change, 2),
                change_percent=round(change_percent, 2),
                volume=info.get('volume', info.get('regularMarketVolume')),
                high=info.get('dayHigh', info.get('regularMarketDayHigh')),
                low=info.get('dayLow', info.get('regularMarketDayLow')),
                open=info.get('open', info.get('regularMarketOpen')),
                prev_close=prev_close,
                market=Market.US if detected_market == "US" else (
                    Market.BSE if detected_market == "BSE" else Market.NSE
                )
            )
            
            self._set_cache(cache_key, stock_price)
            return stock_price
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    async def get_index_data(self, index: str) -> Optional[IndexData]:
        """
        Get market index data.
        
        Args:
            index: Index name (e.g., 'NIFTY 50', 'SENSEX')
            
        Returns:
            IndexData object or None
        """
        cache_key = f"index:{index}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            yf_symbol = INDEX_SYMBOLS.get(index.upper())
            if not yf_symbol:
                logger.warning(f"Unknown index: {index}")
                return None
            
            if yf is None:
                return None
            
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="2d")
            
            if hist.empty:
                return None
            
            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
            change = current - prev
            change_percent = (change / prev * 100) if prev else 0
            
            index_data = IndexData(
                symbol=yf_symbol,
                name=index.upper(),
                value=round(current, 2),
                change=round(change, 2),
                change_percent=round(change_percent, 2)
            )
            
            self._set_cache(cache_key, index_data)
            return index_data
            
        except Exception as e:
            logger.error(f"Error fetching index {index}: {e}")
            return None
    
    async def get_stock_details(self, symbol: str) -> Optional[StockDetails]:
        """
        Get detailed stock information.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            StockDetails object or None
        """
        cache_key = f"details:{symbol}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            yf_symbol = self._get_yf_symbol(symbol)
            
            if yf is None:
                return None
            
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            
            details = StockDetails(
                symbol=symbol.upper(),
                name=info.get('shortName', symbol),
                sector=info.get('sector'),
                industry=info.get('industry'),
                market_cap=info.get('marketCap'),
                pe_ratio=info.get('trailingPE'),
                eps=info.get('trailingEps'),
                dividend_yield=info.get('dividendYield'),
                week_52_high=info.get('fiftyTwoWeekHigh'),
                week_52_low=info.get('fiftyTwoWeekLow'),
                description=info.get('longBusinessSummary')
            )
            
           
            self._set_cache(cache_key, details, ttl=300)
            return details
            
        except Exception as e:
            logger.error(f"Error fetching details for {symbol}: {e}")
            return None
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """Get overall market summary with key indices."""
        indices = ["NIFTY 50", "SENSEX", "BANK NIFTY"]
        results = {}
        
        for index in indices:
            data = await self.get_index_data(index)
            if data:
                results[index] = data
        
        return results
    
    async def get_stock_history(
        self,
        symbol: str,
        days: int = 5,
        market: str = None
    ) -> Optional[StockHistory]:
        """
        Get historical stock data for last N days.
        
        Args:
            symbol: Stock symbol (e.g., 'TCS', 'NVDA')
            days: Number of days of history (default 5)
            market: Market hint (auto-detected if None)
            
        Returns:
            StockHistory object or None
        """
        cache_key = f"history:{symbol}:{days}:{market or 'auto'}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            if yf is None:
                return None
            
          
            if market:
                yf_symbol = self._get_yf_symbol(symbol, market)
                detected_market = market
            else:
                yf_symbol, detected_market = self._detect_market(symbol)
            
            ticker = yf.Ticker(yf_symbol)
           
            period = f"{days + 5}d"
            hist = ticker.history(period=period)
            
            if hist.empty:
                return None
            
            
            hist = hist.tail(days)
            
            history_days = []
            prev_close = None
            for date, row in hist.iterrows():
                change_pct = None
                if prev_close and prev_close > 0:
                    change_pct = round((row['Close'] - prev_close) / prev_close * 100, 2)
                
                history_days.append(StockHistoryDay(
                    date=date.strftime('%Y-%m-%d'),
                    open=round(row['Open'], 2),
                    high=round(row['High'], 2),
                    low=round(row['Low'], 2),
                    close=round(row['Close'], 2),
                    volume=int(row['Volume']) if row['Volume'] else None,
                    change_percent=change_pct
                ))
                prev_close = row['Close']
            
          
            overall_change = None
            if len(history_days) >= 2:
                first_close = hist['Close'].iloc[0]
                last_close = hist['Close'].iloc[-1]
                if first_close > 0:
                    overall_change = round((last_close - first_close) / first_close * 100, 2)
            
            stock_name = STOCK_NAME_MAP.get(symbol.upper(), 
                                            ticker.info.get('shortName', symbol.upper()))
            
            history = StockHistory(
                symbol=symbol.upper(),
                name=stock_name,
                days=history_days,
                period=f"{days}d",
                overall_change_percent=overall_change,
                market=Market.US if detected_market == "US" else Market.NSE
            )
            
            self._set_cache(cache_key, history, ttl=60)  
            return history
            
        except Exception as e:
            logger.error(f"Error fetching history for {symbol}: {e}")
            return self._simulate_stock_history(symbol, days)
   
    
    def _simulate_stock_price(self, symbol: str) -> StockPrice:
        """Generate simulated stock price for demo purposes."""
        import random
        base_price = random.uniform(100, 5000)
        change = random.uniform(-50, 50)
        
        return StockPrice(
            symbol=symbol.upper(),
            name=STOCK_NAME_MAP.get(symbol.upper(), f"{symbol} Ltd"),
            price=round(base_price, 2),
            change=round(change, 2),
            change_percent=round(change / base_price * 100, 2),
            volume=random.randint(100000, 10000000),
            high=round(base_price * 1.02, 2),
            low=round(base_price * 0.98, 2),
            market=Market.NSE
        )
    
    def _simulate_index_data(self, index: str) -> IndexData:
        """Generate simulated index data for demo purposes."""
        import random
        base_values = {
            "NIFTY 50": 22500,
            "SENSEX": 74000,
            "BANK NIFTY": 48000,
        }
        base = base_values.get(index.upper(), 20000)
        change = random.uniform(-200, 200)
        
        return IndexData(
            symbol=INDEX_SYMBOLS.get(index.upper(), index),
            name=index.upper(),
            value=round(base + random.uniform(-100, 100), 2),
            change=round(change, 2),
            change_percent=round(change / base * 100, 2)
        )
    
    def _simulate_stock_details(self, symbol: str) -> StockDetails:
        """Generate simulated stock details for demo purposes."""
        import random
        return StockDetails(
            symbol=symbol.upper(),
            name=STOCK_NAME_MAP.get(symbol.upper(), f"{symbol} Ltd"),
            sector="Technology",
            industry="IT Services",
            market_cap=random.randint(10000, 1000000) * 10000000,
            pe_ratio=round(random.uniform(10, 50), 2),
            eps=round(random.uniform(10, 200), 2),
            week_52_high=round(random.uniform(1000, 5000), 2),
            week_52_low=round(random.uniform(500, 2000), 2),
        )
    
    def _simulate_stock_history(self, symbol: str, days: int = 5) -> StockHistory:
        """Generate simulated stock history for demo purposes."""
        import random
        from datetime import date
        
        base_price = random.uniform(100, 5000)
        history_days = []
        
        for i in range(days):
            day_date = date.today() - timedelta(days=days - i)
            change = random.uniform(-3, 3)
            close = round(base_price * (1 + change / 100), 2)
            
            history_days.append(StockHistoryDay(
                date=day_date.strftime('%Y-%m-%d'),
                open=round(close * random.uniform(0.99, 1.01), 2),
                high=round(close * random.uniform(1.0, 1.03), 2),
                low=round(close * random.uniform(0.97, 1.0), 2),
                close=close,
                volume=random.randint(100000, 10000000),
                change_percent=round(change, 2) if i > 0 else None
            ))
            base_price = close
        
        overall = None
        if len(history_days) >= 2:
            first = history_days[0].close
            last = history_days[-1].close
            overall = round((last - first) / first * 100, 2)
        
        return StockHistory(
            symbol=symbol.upper(),
            name=STOCK_NAME_MAP.get(symbol.upper(), f"{symbol} Ltd"),
            days=history_days,
            period=f"{days}d",
            overall_change_percent=overall,
            market=Market.NSE
        )


_market_service = None

def get_market_data_service() -> MarketDataService:
    """Get or create the market data service singleton."""
    global _market_service
    if _market_service is None:
        _market_service = MarketDataService()
    return _market_service
