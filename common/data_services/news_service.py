"""
News service for fetching and summarizing financial news.
Uses multiple sources: NewsAPI, RSS feeds, and web scraping fallback.
LLM enrichment adds sentiment analysis, better summaries, and symbol extraction.
"""

import asyncio
import json
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

from pydantic import BaseModel, Field
from common.models.schemas import NewsArticle, NewsFeed
from chatbot.core.symbol_registry import STOCK_NAME_MAP

logger = logging.getLogger(__name__)

class ArticleAnalysis(BaseModel):
    """LLM analysis for a single news article."""
    summary: str = Field(description="1-2 sentence summary of the article's market impact")
    sentiment: str = Field(description="One of: bullish, bearish, neutral")
    is_relevant: bool = Field(
        default=True,
        description="Whether this article is relevant to the queried stock/topic"
    )
    related_symbols: list[str] = Field(
        default_factory=list,
        description="NSE/BSE stock symbols mentioned or directly affected (e.g. TCS, RELIANCE)"
    )


class NewsAnalysisBatch(BaseModel):
    """Batch analysis result for multiple articles."""
    articles: list[ArticleAnalysis]


RSS_FEEDS = {
    "market": "https://news.google.com/rss/search?q=indian+stock+market&hl=en-IN&gl=IN&ceid=IN:en",
    "nse": "https://news.google.com/rss/search?q=NSE+stocks&hl=en-IN&gl=IN&ceid=IN:en",
    "business": "https://news.google.com/rss/search?q=business+india&hl=en-IN&gl=IN&ceid=IN:en",
    "economy": "https://news.google.com/rss/search?q=indian+economy&hl=en-IN&gl=IN&ceid=IN:en",
}

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
        articles = await self._enrich_with_llm(articles)
        
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
        articles = await self._fetch_rss_news(url, limit * 2)
        
        
        full_name = STOCK_NAME_MAP.get(symbol.upper(), "")
        stock_context = f"{symbol.upper()}" + (f" ({full_name})" if full_name else "")
        
       
        result = await self._enrich_with_llm(articles, stock_context=stock_context)
        
       
        result = result[:limit]
        
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
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)
            
            articles = []
            for entry in feed.entries[:limit]:
                published = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                title = entry.title
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                
                summary = entry.get('summary', '')
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

    
    async def _enrich_with_llm(
        self,
        articles: List[NewsArticle],
        stock_context: Optional[str] = None,
    ) -> List[NewsArticle]:
        """
        Enrich articles with LLM-powered sentiment, summaries, and symbols.
        When stock_context is provided, also filters for relevance.
        Uses a single batch call for efficiency. Falls back gracefully on error.
        """
        if not articles:
            return articles
        
        try:
            from langchain_groq import ChatGroq
            from common.config.settings import settings
            
            llm = ChatGroq(
                groq_api_key=settings.groq_api_key,
                model_name=settings.llm_model,
                temperature=0.1,
                max_tokens=1024,
            )
            structured_llm = llm.with_structured_output(NewsAnalysisBatch)
            
           
            article_list = "\n".join(
                f"{i+1}. {a.title}" + (f" — {a.summary[:80]}" if a.summary else "")
                for i, a in enumerate(articles)
            )
            
         
            relevance_instruction = ""
            if stock_context:
                relevance_instruction = (
                    f"\n- is_relevant: true if the article is about or directly impacts "
                    f"{stock_context} (including its subsidiaries, promoters, sector peers, "
                    f"or regulatory changes affecting it). false otherwise."
                )
            
            prompt = (
                f"Analyze these {len(articles)} financial news headlines.\n"
                f"For EACH article, provide:\n"
                f"- summary: 1-2 sentence summary of market impact\n"
                f"- sentiment: exactly one of 'bullish', 'bearish', or 'neutral'"
                f"{relevance_instruction}\n"
                f"- related_symbols: list of NSE/BSE stock ticker symbols mentioned "
                f"or directly affected (e.g. ['TCS', 'INFY']). Use empty list if none.\n\n"
                f"Articles:\n{article_list}\n\n"
                f"Return exactly {len(articles)} article analyses in the same order."
            )
            
            result: NewsAnalysisBatch = await structured_llm.ainvoke(prompt)
            
            
            enriched = []
            for i, article in enumerate(articles):
                if i < len(result.articles):
                    analysis = result.articles[i]
                    
                    if stock_context and not analysis.is_relevant:
                        continue
                    article = article.model_copy(update={
                        "summary": analysis.summary,
                        "sentiment": analysis.sentiment,
                        "related_symbols": analysis.related_symbols or None,
                    })
                enriched.append(article)
            
            logger.info(
                f"LLM enriched {len(enriched)}/{len(articles)} news articles"
                + (f" for {stock_context}" if stock_context else "")
            )
            return enriched
            
        except Exception as e:
            logger.warning(f"LLM news enrichment failed (using raw articles): {e}")
            return articles
    
    def _get_fallback_news(self) -> List[NewsArticle]:
        """Return empty list when actual news is unavailable."""
        return []
    
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
        
    
        sentiment_badge = {
            "bullish": "🟢 Bullish",
            "bearish": "🔴 Bearish",
            "neutral": "⚪ Neutral",
        }
        
        response = "📰 **Latest Financial News**\n\n"
        
        for i, article in enumerate(articles, 1):
            # Time ago
            time_ago = self._format_time_ago(article.published_at)
            
            # Sentiment indicator
            badge = ""
            if article.sentiment:
                badge = f" • {sentiment_badge.get(article.sentiment, article.sentiment)}"
            
            response += f"**{i}. {article.title}**\n"
            response += f"   ⏰ {time_ago} • 📌 {article.source}{badge}\n"
            
            if include_summary and article.summary:
                response += f"   {article.summary[:200]}{'...' if len(article.summary) > 200 else ''}\n"
            
            # Show related symbols if available
            if article.related_symbols:
                symbols = ", ".join(article.related_symbols[:5])
                response += f"   🏷️ Related: {symbols}\n"
            
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



_news_service = None

def get_news_service(api_key: Optional[str] = None) -> NewsService:
    """Get or create the news service singleton."""
    global _news_service
    if _news_service is None:
        _news_service = NewsService(api_key)
    return _news_service
