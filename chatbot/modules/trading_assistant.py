"""
Trading assistant module with comprehensive trading knowledge.
Provides Q&A for trading concepts, how-to guides, and educational content.
"""

from typing import Optional, List, Dict, Any
import json
import os
from pathlib import Path


# ============================================================================
# TRADING KNOWLEDGE BASE
# ============================================================================

TRADING_KNOWLEDGE = {
    # ORDER TYPES
    "market_order": {
        "title": "Market Order",
        "content": """A **Market Order** is an order to buy or sell a stock immediately at the best available current price.

**Key Points:**
• Executes instantly during market hours
• Price is not guaranteed - you get the current market price
• Best for: Highly liquid stocks when speed is priority
• Risk: Slippage in volatile markets

**Example:** If TCS is trading at ₹3,500, a market buy order will execute at approximately that price.""",
        "keywords": ["market order", "instant order", "immediate buy", "immediate sell"]
    },
    
    "limit_order": {
        "title": "Limit Order",
        "content": """A **Limit Order** lets you specify the maximum price for buying or minimum price for selling.

**Key Points:**
• Buy Limit: Order executes only at your price or lower
• Sell Limit: Order executes only at your price or higher
• May not execute if price doesn't reach your limit
• Gives you price control

**Example:** Set a buy limit at ₹3,400 for TCS - it only buys if price falls to ₹3,400 or below.""",
        "keywords": ["limit order", "price limit", "set price", "target price"]
    },
    
    "stop_loss": {
        "title": "Stop Loss Order",
        "content": """A **Stop Loss (SL)** order helps limit your losses by automatically selling when price falls to a certain level.

**Key Points:**
• Protects against large losses
• Triggers a market order when stop price is hit
• Essential for risk management
• Can also be used to protect profits (trailing SL)

**How to set:**
1. Go to your holdings/positions
2. Select the stock
3. Click 'Add Stop Loss'
4. Set your trigger price

**Example:** Bought stock at ₹100, set SL at ₹90 to limit loss to 10%.""",
        "keywords": ["stop loss", "stoploss", "sl", "cut loss", "limit loss", "protect"]
    },
    
    "bracket_order": {
        "title": "Bracket Order",
        "content": """A **Bracket Order** is an advanced order type that places 3 orders at once: entry, target, and stop-loss.

**Components:**
1. **Entry Order**: Your buy/sell order
2. **Target Order**: Profit booking level
3. **Stop Loss**: Loss limiting level

**Benefits:**
• Automated risk management
• Lock in profit targets
• Popular for intraday trading

**Note:** Only available for intraday positions on most platforms.""",
        "keywords": ["bracket order", "bo", "bracket", "three leg order"]
    },
    
    # TRADING CONCEPTS
    "intraday": {
        "title": "Intraday Trading",
        "content": """**Intraday Trading** means buying and selling stocks within the same trading day.

**Key Points:**
• All positions must be squared off before market close
• Requires less capital (leverage available)
• Higher risk, higher reward potential
• Profits/losses settled same day

**Tips for Beginners:**
• Start small
• Use stop losses always
• Focus on liquid stocks
• Avoid trading on news/events initially

**Timing:** NSE market hours are 9:15 AM - 3:30 PM IST.""",
        "keywords": ["intraday", "day trading", "same day", "square off"]
    },
    
    "delivery": {
        "title": "Delivery Trading",
        "content": """**Delivery Trading** means buying stocks to hold for more than one day.

**Key Points:**
• Stocks are delivered to your demat account
• No time limit - hold for days, months, or years
• Requires full payment (no leverage)
• Pay STT on buy and sell

**Benefits:**
• No daily monitoring needed
• Can benefit from long-term growth
• No forced square-off
• Eligible for dividends and bonuses""",
        "keywords": ["delivery", "cash", "cnc", "long term", "hold", "invest"]
    },
    
    "margin": {
        "title": "Margin Trading",
        "content": """**Margin Trading** allows you to trade with borrowed funds from your broker.

**Key Points:**
• Trade larger positions with less capital
• Amplifies both profits AND losses
• Interest charged on borrowed amount
• Margin call if position moves against you

**Types:**
• **Intraday Margin**: Up to 5x for intraday
• **Delivery Margin**: Usually 2x-4x

⚠️ **Risk Warning:** Margin trading is risky. You can lose more than your initial investment.""",
        "keywords": ["margin", "leverage", "borrowed", "mis", "margin trading"]
    },
    
    # TECHNICAL ANALYSIS
    "candlestick": {
        "title": "Candlestick Patterns",
        "content": """**Candlestick Charts** show price movement with visual candles.

**Anatomy of a Candle:**
• **Body**: Opening to closing price
• **Wicks/Shadows**: High and low prices
• **Green/White**: Closing higher than opening (bullish)
• **Red/Black**: Closing lower than opening (bearish)

**Common Patterns:**
• **Doji**: Indecision, opening = closing
• **Hammer**: Potential reversal at bottom
• **Shooting Star**: Potential reversal at top
• **Engulfing**: Strong reversal signal

**Tip:** Combine with volume and other indicators for confirmation.""",
        "keywords": ["candlestick", "candle", "pattern", "chart pattern", "doji", "hammer"]
    },
    
    "moving_average": {
        "title": "Moving Averages",
        "content": """**Moving Averages** smooth out price data to show trends.

**Types:**
• **SMA (Simple)**: Average of last N prices
• **EMA (Exponential)**: Gives more weight to recent prices

**Popular Periods:**
• 9 & 21 day: Short-term trends
• 50 day: Medium-term trend
• 200 day: Long-term trend

**Crossover Signals:**
• **Golden Cross**: 50 MA crosses above 200 MA (bullish)
• **Death Cross**: 50 MA crosses below 200 MA (bearish)

**Usage:** Price above MA = uptrend, below MA = downtrend.""",
        "keywords": ["moving average", "sma", "ema", "ma", "average", "trend"]
    },
    
    "rsi": {
        "title": "RSI (Relative Strength Index)",
        "content": """**RSI** is a momentum indicator measuring speed and change of price movements.

**Scale:** 0 to 100

**Key Levels:**
• **Above 70**: Overbought (potential sell signal)
• **Below 30**: Oversold (potential buy signal)
• **50**: Neutral level

**How to Use:**
• Look for divergences (price vs RSI)
• Combine with price action
• Don't trade solely on RSI
• Works best in ranging markets

**Period:** Standard is 14 periods.""",
        "keywords": ["rsi", "relative strength", "overbought", "oversold", "momentum"]
    },
    
    # FUNDAMENTAL TERMS
    "pe_ratio": {
        "title": "P/E Ratio (Price to Earnings)",
        "content": """**P/E Ratio** shows how much investors pay per rupee of company earnings.

**Formula:** P/E = Stock Price ÷ Earnings Per Share (EPS)

**Interpretation:**
• **High P/E (>30)**: Expensive, high growth expectations
• **Low P/E (<15)**: Cheap or low growth expectations
• **Compare within same industry**

**Types:**
• **Trailing P/E**: Based on past 12 months earnings
• **Forward P/E**: Based on expected future earnings

**Example:** Stock at ₹500 with EPS of ₹25 = P/E of 20.""",
        "keywords": ["pe ratio", "price to earnings", "p/e", "pe", "valuation", "earnings"]
    },
    
    "market_cap": {
        "title": "Market Capitalization",
        "content": """**Market Cap** is the total market value of a company's outstanding shares.

**Formula:** Market Cap = Share Price × Total Shares Outstanding

**Categories:**
• **Large Cap**: > ₹20,000 Cr (stable, lower risk)
• **Mid Cap**: ₹5,000 - ₹20,000 Cr (moderate risk/reward)
• **Small Cap**: < ₹5,000 Cr (higher risk/reward)

**Why It Matters:**
• Indicates company size
• Larger = more stable, less volatile
• Smaller = more growth potential but riskier""",
        "keywords": ["market cap", "market capitalization", "cap", "large cap", "mid cap", "small cap"]
    },
    
    # PLATFORM/HOW-TO
    "how_to_buy": {
        "title": "How to Buy Stocks",
        "content": """**Steps to Buy Stocks:**

1. **Search** for the stock by name or symbol
2. **Click Buy** button
3. **Select order type:**
   • Market Order (instant execution)
   • Limit Order (specify your price)
4. **Choose product type:**
   • CNC/Delivery (long-term)
   • MIS/Intraday (same day)
5. **Enter quantity** (number of shares)
6. **Review** your order details
7. **Swipe/Click** to confirm

**Tips:**
• Always check the price before confirming
• Use limit orders for better price control
• Set stop-loss for risk management""",
        "keywords": ["how to buy", "buy stock", "purchase", "place order", "buying"]
    },
    
    "how_to_sell": {
        "title": "How to Sell Stocks",
        "content": """**Steps to Sell Stocks:**

1. Go to **Portfolio/Holdings**
2. **Select** the stock you want to sell
3. **Click Sell**
4. **Choose order type:**
   • Market Order
   • Limit Order
5. **Enter quantity** to sell
6. **Review** the order
7. **Confirm** the sale

**For Intraday/Short Selling:**
• Go to the stock page
• Select "Sell" (without owning)
• Choose MIS product type
• Must buy back before market close""",
        "keywords": ["how to sell", "sell stock", "exit", "selling", "book profit"]
    },
    
    "t_plus_one": {
        "title": "T+1 Settlement",
        "content": """**T+1 Settlement** means trades are settled the next business day after the trade date.

India moved to T+1 settlement for all NSE/BSE stocks in 2023, making it one of the fastest settlement systems globally.

**What this means for traders:**
- Buy today, shares credited to demat account next trading day
- Sell today, money credited to bank account next trading day
- No more waiting 2 days like the old T+2 system
- Reduces counterparty risk significantly

**Intraday exception:** Intraday trades are squared off same day — no delivery involved.""",
        "keywords": ["t+1", "settlement", "t plus one", "trade settlement", "demat credit"]
    },

    "circuit_breaker": {
        "title": "Circuit Breakers and Price Bands",
        "content": """**Circuit Breakers** halt trading when markets move sharply to prevent panic.

**Market-wide circuit breakers (NSE/BSE):**
- 10% move → 45 minute halt (before 1 PM) / 15 minutes (between 1-2:30 PM) / no halt after 2:30 PM
- 15% move → 1 hour 45 minute halt / 45 minutes / no halt after 2:30 PM
- 20% move → Trading halted for rest of the day

**Stock-specific price bands:**
- 2%, 5%, 10%, or 20% upper/lower circuit limits
- Stock hitting upper circuit = only buyers, no sellers (very bullish signal)
- Stock hitting lower circuit = only sellers, no buyers (very bearish signal)
- F&O stocks: no price band (but index circuit breakers apply)""",
        "keywords": ["circuit breaker", "upper circuit", "lower circuit", "price band", "halt trading"]
    },

    "sebi_investor": {
        "title": "SEBI Investor Protection Rules",
        "content": """**SEBI (Securities and Exchange Board of India)** regulates Indian stock markets.

**Key investor protections:**
- Mandatory demat account for all share holdings
- Broker margins must be in segregated accounts
- SEBI SCORES: Online complaint portal for investor grievances
- Investor Protection Fund: Covers up to ₹25 lakh if broker defaults
- KYC mandatory for all trading accounts

**SEBI registration check:**
Always verify your broker/advisor is SEBI registered at sebi.gov.in/sebiweb/home/HomeAction.do

**Disclaimer:** FinSight is an informational tool. Always verify with SEBI-registered advisors.""",
        "keywords": ["SEBI", "investor protection", "broker default", "SCORES", "KYC", "regulation"]
    },

    "fii_dii": {
        "title": "FII and DII Activity",
        "content": """**FII (Foreign Institutional Investors)** and **DII (Domestic Institutional Investors)** are major market movers.

**FII:**
- Foreign funds investing in Indian markets
- When FIIs buy heavily = bullish signal, market tends to rise
- When FIIs sell (net sellers) = bearish signal, market tends to fall
- Tracked daily on NSE website

**DII:**
- Indian mutual funds, insurance companies, pension funds
- Often counter FII selling (buy when FIIs sell)
- DII buying during FII selloff = market support signal

**Where to check:**
NSE India publishes daily FII/DII data. Important for understanding whether institutional money is flowing in or out of Indian markets.""",
        "keywords": ["FII", "DII", "foreign investors", "institutional buying", "institutional selling", "net buy", "net sell"]
    },
}


class TradingAssistant:
    """
    Provides trading knowledge, how-to guides, and educational content.
    Uses the built-in knowledge base and optional RAG for enhanced responses.
    """
    
    def __init__(self):
        """Initialize trading assistant."""
        self.knowledge = TRADING_KNOWLEDGE
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """Build reverse index from keywords to topics."""
        self.keyword_index: Dict[str, List[str]] = {}
        
        for topic_id, topic in self.knowledge.items():
            for keyword in topic.get("keywords", []):
                keyword_lower = keyword.lower()
                if keyword_lower not in self.keyword_index:
                    self.keyword_index[keyword_lower] = []
                self.keyword_index[keyword_lower].append(topic_id)
    
    def search(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for relevant trading knowledge.
        
        Args:
            query: User's query
            
        Returns:
            Matching topic or None
        """
        query_lower = query.lower()
        
        # Direct keyword match
        for keyword, topics in self.keyword_index.items():
            if keyword in query_lower:
                # Return the first matching topic
                topic_id = topics[0]
                return {
                    "id": topic_id,
                    **self.knowledge[topic_id]
                }
        
        # Fuzzy match on topic titles
        for topic_id, topic in self.knowledge.items():
            title_lower = topic["title"].lower()
            if any(word in query_lower for word in title_lower.split()):
                return {
                    "id": topic_id,
                    **topic
                }
        
        return None
    
    def get_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific topic by ID."""
        if topic_id in self.knowledge:
            return {
                "id": topic_id,
                **self.knowledge[topic_id]
            }
        return None
    
    def format_response(self, topic: Dict[str, Any]) -> str:
        """Format a topic into a response."""
        return f"📚 **{topic['title']}**\n\n{topic['content']}"
    
    def get_all_topics(self) -> List[str]:
        """Get list of all available topics."""
        return list(self.knowledge.keys())
    
    def get_help_suggestions(self) -> str:
        """Get suggestions for what users can ask about."""
        return """💡 **I can help you with:**

**Order Types:**
• Market orders, limit orders, stop-loss
• Bracket orders, cover orders

**Trading Concepts:**
• Intraday vs Delivery trading
• Margin trading explained
• Short selling basics

**Technical Analysis:**
• Candlestick patterns
• Moving averages (SMA, EMA)
• RSI and other indicators

**Fundamentals:**
• P/E ratio, Market Cap
• EPS, Dividend Yield

**How-To Guides:**
• How to buy/sell stocks
• Setting stop-loss
• Reading charts

Just ask me anything! 🚀"""


# Singleton instance
_trading_assistant = None

def get_trading_assistant() -> TradingAssistant:
    """Get or create the trading assistant singleton."""
    global _trading_assistant
    if _trading_assistant is None:
        _trading_assistant = TradingAssistant()
    return _trading_assistant
