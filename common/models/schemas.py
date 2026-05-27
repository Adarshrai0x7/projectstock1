"""
Pydantic models/schemas for the Finance Chatbot.
Defines request/response structures and domain objects.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum



class Market(str, Enum):
    """Supported stock markets."""
    NSE = "NSE"
    BSE = "BSE"
    US = "US"



class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Incoming chat request."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="Session ID for context")
    include_context: bool = Field(True, description="Include conversation history")


class ChatResponse(BaseModel):
    """Chat response with metadata."""
    reply: str = Field(..., description="Bot response")
    intent: Optional[str] = Field(None, description="Detected intent")
    entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities")
    sources: Optional[List[str]] = Field(None, description="Source references")
    suggestions: Optional[List[str]] = Field(None, description="Follow-up suggestions")
    session_id: Optional[str] = Field(None, description="Session ID")



class StockPrice(BaseModel):
    """Stock price data."""
    symbol: str
    name: Optional[str] = None
    price: float
    change: float = Field(..., description="Price change")
    change_percent: float = Field(..., description="Percentage change")
    volume: Optional[int] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    prev_close: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    market: Market = Market.NSE


class IndexData(BaseModel):
    """Market index data."""
    symbol: str
    name: str
    value: float
    change: float
    change_percent: float
    timestamp: datetime = Field(default_factory=datetime.now)


class MarketMovers(BaseModel):
    """Top gainers and losers."""
    gainers: List[StockPrice]
    losers: List[StockPrice]
    timestamp: datetime = Field(default_factory=datetime.now)


class StockDetails(BaseModel):
    """Detailed stock information."""
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    description: Optional[str] = None


class StockHistoryDay(BaseModel):
    """Single day of stock history."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None
    change_percent: Optional[float] = None


class StockHistory(BaseModel):
    """Historical stock data over a period."""
    symbol: str
    name: Optional[str] = None
    days: List[StockHistoryDay]
    period: Optional[str] = "5d"
    overall_change_percent: Optional[float] = None
    market: Market = Market.NSE


class NewsArticle(BaseModel):
    """Financial news article."""
    title: str
    summary: Optional[str] = None
    source: str
    url: str
    published_at: datetime
    related_symbols: Optional[List[str]] = None
    sentiment: Optional[str] = None  


class NewsFeed(BaseModel):
    """Collection of news articles."""
    articles: List[NewsArticle]
    query: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PortfolioHolding(BaseModel):
    """Single portfolio holding."""
    symbol: str
    name: Optional[str] = None
    quantity: int
    avg_buy_price: float
    current_price: float
    current_value: float
    pnl: float = Field(..., description="Profit/Loss")
    pnl_percent: float


class PortfolioSummary(BaseModel):
    """Portfolio overview."""
    total_invested: float
    current_value: float
    total_pnl: float
    total_pnl_percent: float
    holdings: List[PortfolioHolding]
    last_updated: datetime = Field(default_factory=datetime.now)


class TechnicalIndicators(BaseModel):
    """Technical analysis indicator values."""
    rsi: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    bollinger_position: Optional[float] = None
    volume_ratio: Optional[float] = None
    supertrend_signal: Optional[str] = None
    adx: Optional[float] = None
    vwap_position: Optional[str] = None
    stochastic_k: Optional[float] = None


class FundamentalData(BaseModel):
    """Fundamental analysis data."""
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    eps: Optional[float] = None
    market_cap: Optional[float] = None
    book_value: Optional[float] = None
    dividend_yield: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    earnings_growth: Optional[float] = None
    revenue_growth: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    free_cash_flow: Optional[float] = None
    institutional_holding: Optional[float] = None
    peg_ratio: Optional[float] = None
    profit_margin: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


class StockAnalysis(BaseModel):
    """Complete analysis of a single stock (technical + fundamental)."""
    symbol: str
    name: Optional[str] = None
    price: float
    change_percent: float = 0.0
    technical: TechnicalIndicators = Field(default_factory=TechnicalIndicators)
    fundamental: FundamentalData = Field(default_factory=FundamentalData)
    signal: str = "NEUTRAL" 
    score: float = 50.0  
    market: Market = Market.NSE


class ScreenerResult(BaseModel):
    """Results from a stock screening operation."""
    screen_name: str
    description: str = ""
    stocks: List[StockAnalysis] = Field(default_factory=list)
    total_scanned: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)




class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "3.0.0"
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
