"""
News service for fetching and summarizing financial news.
Uses multiple sources: NewsAPI, RSS feeds, and web scraping fallback.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import re

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import aiohttp
except ImportError:
    aiohttp = None

from common.models.schemas import NewsArticle, NewsFeed

logger = logging.getLogger(__name__)


# ============================================================================
# NEWS SOURCE CONFIGURATION
# ============================================================================

# Google Finance RSS feeds (free, no API key needed)
RSS_FEEDS = {
    "market": "https://news.google.com/rss/search?q=indian+stock+market&hl=en-IN&gl=IN&ceid=IN:en",
    "nse": "https://news.google.com/rss/search?q=NSE+stocks&hl=en-IN&gl=IN&ceid=IN:en",
    "business": "https://news.google.com/rss/search?q=business+india&hl=en-IN&gl=IN&ceid=IN:en",
    "economy": "https://news.google.com/rss/search?q=indian+economy&hl=en-IN&gl=IN&ceid=IN:en",
}

# Stock-specific news search template
STOCK_NEWS_URL = "https://news.google.com/rss/search?q={symbol}+stock+india&hl=en-IN&gl=IN&ceid=IN:en"


class NewsService:
    """
    Service for fetching and processing financial news.
    Supports RSS feeds and optional NewsAPI integration.
    """
    
    def __init__(self, news_api_key: Optional[str] = None):
        """
        Initialize news service.
        
        Args:
            news_api_key: Optional NewsAPI.org API key
        """
        self.news_api_key = news_api_key
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 300  # 5 minutes
        
        if feedparser is None:
            logger.warning("feedparser not installed. News features may be limited.")
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Set value in cache."""
        expiry = datetime.now() + timedelta(seconds=self._cache_ttl)
        self._cache[key] = (value, expiry)
    
    async def get_market_news(self, limit: int = 5) -> List[NewsArticle]:
        """
        Get latest market news.
        
        Args:
            limit: Maximum number of articles
            
        Returns:
            List of NewsArticle objects
        """
        cache_key = f"news:market:{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        articles = await self._fetch_rss_news(RSS_FEEDS["market"], limit)
        
        if not articles:
            articles = self._get_fallback_news()
        
        self._set_cache(cache_key, articles)
        return articles
    
    async def get_stock_news(self, symbol: str, limit: int = 5) -> List[NewsArticle]:
        """
        Get news for a specific stock.
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of articles
            
        Returns:
            List of NewsArticle objects
        """
        cache_key = f"news:stock:{symbol}:{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        url = STOCK_NEWS_URL.format(symbol=symbol)
        articles = await self._fetch_rss_news(url, limit)
        
        # Filter to ensure articles are actually related to the stock
        filtered = [
            a for a in articles 
            if symbol.lower() in a.title.lower() or 
               symbol.lower() in (a.summary or "").lower()
        ]
        
        result = filtered if filtered else articles[:limit]
        self._set_cache(cache_key, result)
        return result
    
    async def _fetch_rss_news(self, url: str, limit: int = 5) -> List[NewsArticle]:
        """
        Fetch news from RSS feed.
        
        Args:
            url: RSS feed URL
            limit: Maximum articles
            
        Returns:
            List of NewsArticle objects
        """
        if feedparser is None:
            return self._get_fallback_news()[:limit]
        
        try:
            # Use asyncio to not block
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)
            
            articles = []
            for entry in feed.entries[:limit]:
                # Parse published date
                published = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                # Clean up title (remove source suffix)
                title = entry.title
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                
                # Get summary
                summary = entry.get('summary', '')
                # Remove HTML tags
                summary = re.sub(r'<[^>]+>', '', summary)[:200]
                
                articles.append(NewsArticle(
                    title=title,
                    summary=summary if summary else None,
                    source=entry.get('source', {}).get('title', 'Google News'),
                    url=entry.link,
                    published_at=published
                ))
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS news: {e}")
            return self._get_fallback_news()[:limit]
    
    def _get_fallback_news(self) -> List[NewsArticle]:
        """Return demo news when actual news unavailable."""
        now = datetime.now()
        return [
            NewsArticle(
                title="Markets show mixed trends amid global uncertainty",
                summary="Indian markets traded flat today with Nifty hovering around key levels.",
                source="FinSight Demo",
                url="https://example.com/news/1",
                published_at=now
            ),
            NewsArticle(
                title="Banking stocks lead gains in early trade",
                summary="HDFC Bank and ICICI Bank among top gainers as sector shows strength.",
                source="FinSight Demo",
                url="https://example.com/news/2",
                published_at=now - timedelta(hours=1)
            ),
            NewsArticle(
                title="IT sector faces headwinds on global tech slowdown concerns",
                summary="TCS, Infosys trade lower amid concerns over US recession.",
                source="FinSight Demo",
                url="https://example.com/news/3",
                published_at=now - timedelta(hours=2)
            ),
            NewsArticle(
                title="Auto sales data exceeds expectations for December",
                summary="Maruti, Tata Motors report better-than-expected monthly sales.",
                source="FinSight Demo",
                url="https://example.com/news/4",
                published_at=now - timedelta(hours=3)
            ),
            NewsArticle(
                title="RBI policy decision awaited by markets",
                summary="Analysts expect status quo on interest rates in upcoming MPC meeting.",
                source="FinSight Demo",
                url="https://example.com/news/5",
                published_at=now - timedelta(hours=4)
            ),
        ]
    
    def format_news(self, articles: List[NewsArticle], include_summary: bool = True) -> str:
        """
        Format news articles into a conversational response.
        
        Args:
            articles: List of news articles
            include_summary: Whether to include article summaries
            
        Returns:
            Formatted news string
        """
        if not articles:
            return "📰 No news articles available at the moment. Please try again later."
        
        response = "📰 **Latest Financial News**\n\n"
        
        for i, article in enumerate(articles, 1):
            # Time ago
            time_ago = self._format_time_ago(article.published_at)
            
            response += f"**{i}. {article.title}**\n"
            response += f"   ⏰ {time_ago} • 📌 {article.source}\n"
            
            if include_summary and article.summary:
                response += f"   {article.summary[:150]}{'...' if len(article.summary) > 150 else ''}\n"
            
            response += "\n"
        
        return response.strip()
    
    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as 'X hours ago' style."""
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"


# Singleton instance
_news_service = None

def get_news_service(api_key: Optional[str] = None) -> NewsService:
    """Get or create the news service singleton."""
    global _news_service
    if _news_service is None:
        _news_service = NewsService(api_key)
    return _news_service
