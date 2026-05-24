"""
Stock Screener Service.
Screens and ranks stocks using technical + fundamental analysis.
Uses MarketDataService (from chatbot's modules/) for data access.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    yf = None

from common.models.schemas import (
    Market, StockAnalysis, TechnicalIndicators,
    FundamentalData, ScreenerResult
)
from common.data_services.market_data import get_market_data_service
from screener.technical_indicators import get_indicator_service

logger = logging.getLogger(__name__)


# ============================================================================
# NIFTY 50 STOCK UNIVERSE (Default scan list)
# ============================================================================

NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "BAJFINANCE",
    "HCLTECH", "TITAN", "SUNPHARMA", "WIPRO", "ULTRACEMCO",
    "NESTLEIND", "TATAMOTORS", "TATASTEEL", "POWERGRID", "NTPC",
    "ADANIENT", "ADANIPORTS", "BAJAJFINSV", "TECHM", "ONGC",
    "COALINDIA", "JSWSTEEL", "DIVISLAB", "DRREDDY", "CIPLA",
    "EICHERMOT", "HEROMOTOCO", "BPCL", "GRASIM", "APOLLOHOSP",
    "BRITANNIA", "INDUSINDBK", "SBILIFE", "HDFCLIFE", "TATACONSUM",
    "M&M", "BAJAJ-AUTO", "UPL", "HINDALCO", "LTIM",
]


# Pre-built screen definitions
PREBUILT_SCREENS = {
    "undervalued": {
        "name": "Undervalued Stocks",
        "description": "Stocks with low PE, low PB, and good ROE — potentially undervalued by the market",
        "filters": {
            "pe_ratio_max": 20,
            "pb_ratio_max": 3,
            "roe_min": 12,
        }
    },
    "momentum": {
        "name": "Momentum Stocks",
        "description": "Stocks showing bullish momentum — RSI in sweet zone, above SMA50, positive MACD",
        "filters": {
            "rsi_min": 50,
            "rsi_max": 70,
            "above_sma_50": True,
            "macd_bullish": True,
        }
    },
    "oversold": {
        "name": "Oversold Stocks",
        "description": "Stocks with RSI below 30 or near lower Bollinger Band — potential bounce candidates",
        "filters": {
            "rsi_max": 35,
        }
    },
    "high_dividend": {
        "name": "High Dividend Yield",
        "description": "Stocks with dividend yield above 2% and reasonable PE",
        "filters": {
            "dividend_yield_min": 2.0,
            "pe_ratio_max": 25,
        }
    },
    "strong_fundamentals": {
        "name": "Strong Fundamentals",
        "description": "Stocks with high ROE, low debt, and good profit margins",
        "filters": {
            "roe_min": 15,
            "debt_to_equity_max": 1.0,
            "profit_margin_min": 10,
        }
    },
}


class ScreenerService:
    """
    Stock screener that combines technical and fundamental analysis.
    Uses the chatbot's MarketDataService for data and TechnicalIndicators for calculations.
    """
    
    def __init__(self):
        """Initialize screener with shared services."""
        self.market_service = get_market_data_service()
        self.indicators = get_indicator_service()
    
    # ========================================================================
    # Main Screening Methods
    # ========================================================================
    
    async def analyze_stock(self, symbol: str) -> Optional[StockAnalysis]:
        """
        Full analysis of a single stock (technical + fundamental).
        
        Args:
            symbol: Stock symbol (e.g., 'TCS', 'NVDA')
            
        Returns:
            StockAnalysis with all indicators and signal
        """
        try:
            # Detect market and get yfinance symbol
            yf_symbol, detected_market = self.market_service._detect_market(symbol)
            
            # Get fundamental data from yfinance
            fundamental = await self._get_fundamentals(yf_symbol, symbol)
            
            # Get technical indicators (needs price history)
            tech_data = self.indicators.get_all_indicators(yf_symbol, period="6mo")
            
            # Build TechnicalIndicators model
            technical = TechnicalIndicators(
                rsi=tech_data.get("rsi", {}).get("value"),
                sma_20=tech_data.get("sma_20", {}).get("value"),
                sma_50=tech_data.get("sma_50", {}).get("value"),
                sma_200=tech_data.get("sma_200", {}).get("value"),
                ema_12=tech_data.get("ema_12", {}).get("value"),
                ema_26=tech_data.get("ema_26", {}).get("value"),
                macd=tech_data.get("macd", {}).get("macd"),
                macd_signal=tech_data.get("macd", {}).get("signal_line"),
                macd_histogram=tech_data.get("macd", {}).get("histogram"),
                bollinger_upper=tech_data.get("bollinger", {}).get("upper"),
                bollinger_lower=tech_data.get("bollinger", {}).get("lower"),
                bollinger_position=tech_data.get("bollinger", {}).get("band_position"),
                volume_ratio=tech_data.get("volume_analysis", {}).get("volume_ratio"),
                supertrend_signal=tech_data.get("supertrend", {}).get("signal"),
                adx=tech_data.get("adx", {}).get("value"),
                vwap_position=tech_data.get("vwap", {}).get("signal"),
                stochastic_k=tech_data.get("stochastic", {}).get("k"),
            )
            
            # Get current price
            current_price = tech_data.get("current_price", 0)
            if current_price == 0:
                stock_price = await self.market_service.get_stock_price(symbol)
                if stock_price:
                    current_price = stock_price.price
            
            # Get price change
            stock_price = await self.market_service.get_stock_price(symbol)
            change_pct = stock_price.change_percent if stock_price else 0
            stock_name = stock_price.name if stock_price else symbol
            
            # Determine market enum
            market_enum = Market.US if detected_market == "US" else Market.NSE
            
            return StockAnalysis(
                symbol=symbol.upper(),
                name=stock_name,
                price=current_price,
                change_percent=change_pct,
                technical=technical,
                fundamental=fundamental,
                signal=tech_data.get("composite_signal", "NEUTRAL"),
                score=tech_data.get("composite_score", 50.0),
                market=market_enum,
            )
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    async def screen_stocks(
        self,
        filters: Dict[str, Any],
        stock_list: List[str] = None,
        screen_name: str = "Custom Screen",
        description: str = "",
    ) -> ScreenerResult:
        """
        Screen a list of stocks using given filters.
        
        Args:
            filters: Dict of filter criteria
            stock_list: Stocks to screen (default: Nifty 50)
            screen_name: Name for the screen
            description: Description of the screen
            
        Returns:
            ScreenerResult with matching stocks sorted by score
        """
        stocks_to_scan = stock_list or NIFTY_50
        result_stocks = []
        
        # Analyze stocks concurrently in batches of 5
        batch_size = 5
        for i in range(0, len(stocks_to_scan), batch_size):
            batch = stocks_to_scan[i:i + batch_size]
            tasks = [self.analyze_stock(symbol) for symbol in batch]
            analyses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for analysis in analyses:
                if isinstance(analysis, Exception):
                    logger.error(f"Analysis error: {analysis}")
                    continue
                if analysis is None:
                    continue
                
                # Apply filters
                if self._passes_filters(analysis, filters):
                    result_stocks.append(analysis)
        
        # Sort by composite score (highest first)
        result_stocks.sort(key=lambda s: s.score, reverse=True)
        
        return ScreenerResult(
            screen_name=screen_name,
            description=description,
            stocks=result_stocks,
            total_scanned=len(stocks_to_scan),
        )
    
    async def get_prebuilt_screen(self, screen_name: str) -> Optional[ScreenerResult]:
        """
        Run a pre-built screen by name.
        
        Args:
            screen_name: One of: undervalued, momentum, oversold, high_dividend, strong_fundamentals
            
        Returns:
            ScreenerResult or None if screen not found
        """
        screen = PREBUILT_SCREENS.get(screen_name.lower())
        if not screen:
            logger.warning(f"Unknown screen: {screen_name}")
            return None
        
        return await self.screen_stocks(
            filters=screen["filters"],
            screen_name=screen["name"],
            description=screen["description"],
        )
    
    def get_available_screens(self) -> List[Dict[str, str]]:
        """Get list of available pre-built screens."""
        return [
            {"id": key, "name": val["name"], "description": val["description"]}
            for key, val in PREBUILT_SCREENS.items()
        ]
    
    # ========================================================================
    # Helpers
    # ========================================================================
    
    async def _get_fundamentals(self, yf_symbol: str, symbol: str) -> FundamentalData:
        """Fetch fundamental data from yfinance."""
        try:
            if yf is None:
                return FundamentalData()
            
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            
            # Calculate ROE: Net Income / Shareholder Equity
            net_income = info.get('netIncomeToCommon')
            equity = info.get('totalStockholderEquity')
            roe = (net_income / equity * 100) if (net_income and equity and equity != 0) else None
            
            eg = info.get('earningsGrowth')
            rg = info.get('revenueGrowth')
            inst = info.get('heldPercentInstitutions')
            
            return FundamentalData(
                pe_ratio=info.get('trailingPE'),
                pb_ratio=info.get('priceToBook'),
                roe=round(roe, 2) if roe else None,
                debt_to_equity=info.get('debtToEquity', None),
                eps=info.get('trailingEps'),
                dividend_yield=round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else None,
                market_cap=info.get('marketCap'),
                revenue_growth=round(rg*100,1) if rg is not None else None,
                earnings_growth=round(eg*100,1) if eg is not None else None,
                current_ratio=info.get('currentRatio'),
                quick_ratio=info.get('quickRatio'),
                free_cash_flow=info.get('freeCashflow'),
                institutional_holding=round(inst*100,1) if inst is not None else None,
                peg_ratio=info.get('trailingPegRatio', info.get('pegRatio')),
                profit_margin=round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else None,
                sector=info.get('sector'),
                industry=info.get('industry'),
            )
            
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {symbol}: {e}")
            return FundamentalData()
    
    def _passes_filters(self, analysis: StockAnalysis, filters: Dict[str, Any]) -> bool:
        """Check if a stock analysis passes all given filters."""
        tech = analysis.technical
        fund = analysis.fundamental
        
        # PE ratio filters
        if "pe_ratio_max" in filters:
            if fund.pe_ratio is None or fund.pe_ratio > filters["pe_ratio_max"]:
                return False
        if "pe_ratio_min" in filters:
            if fund.pe_ratio is None or fund.pe_ratio < filters["pe_ratio_min"]:
                return False
        
        # PB ratio filters
        if "pb_ratio_max" in filters:
            if fund.pb_ratio is None or fund.pb_ratio > filters["pb_ratio_max"]:
                return False
        
        # ROE filter
        if "roe_min" in filters:
            if fund.roe is None or fund.roe < filters["roe_min"]:
                return False
        
        # Debt-to-Equity
        if "debt_to_equity_max" in filters:
            if fund.debt_to_equity is not None and fund.debt_to_equity > filters["debt_to_equity_max"]:
                return False
        
        # Dividend yield
        if "dividend_yield_min" in filters:
            if fund.dividend_yield is None or fund.dividend_yield < filters["dividend_yield_min"]:
                return False
        
        # Profit margin
        if "profit_margin_min" in filters:
            if fund.profit_margin is None or fund.profit_margin < filters["profit_margin_min"]:
                return False
        
        # RSI filters
        if "rsi_max" in filters:
            if tech.rsi is None or tech.rsi > filters["rsi_max"]:
                return False
        if "rsi_min" in filters:
            if tech.rsi is None or tech.rsi < filters["rsi_min"]:
                return False
        
        # Above SMA-50
        if filters.get("above_sma_50"):
            if tech.sma_50 is None or analysis.price <= tech.sma_50:
                return False
        
        # MACD bullish
        if filters.get("macd_bullish"):
            if tech.macd_histogram is None or tech.macd_histogram <= 0:
                return False
        
        # Score filter
        if "score_min" in filters:
            if analysis.score < filters["score_min"]:
                return False
        
        return True


# Singleton
_screener_service = None

def get_screener_service() -> ScreenerService:
    """Get or create the screener service singleton."""
    global _screener_service
    if _screener_service is None:
        _screener_service = ScreenerService()
    return _screener_service
