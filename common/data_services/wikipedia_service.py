"""
Wikipedia Service.
Provides a fallback knowledge base for financial concepts.
Uses the free Wikipedia API.
"""

import logging
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

try:
    import wikipediaapi
except ImportError:
    wikipediaapi = None
    logger.warning("wikipedia-api package not found. Wikipedia service disabled.")


class WikipediaService:
    """Service to fetch summaries of financial concepts from Wikipedia."""
    
    def __init__(self):
        if wikipediaapi:
            # Requires a meaningful user agent
            self.wiki = wikipediaapi.Wikipedia(
                user_agent='FinSightBot/1.0 (https://github.com/FinSight)',
                language='en',
                extract_format=wikipediaapi.ExtractFormat.WIKI
            )
        else:
            self.wiki = None

    @lru_cache(maxsize=128)
    def search_concept(self, query: str) -> Optional[str]:
        """
        Search Wikipedia for a concept and return its summary.
        Adds 'finance' or 'economics' context to help disambiguate.
        """
        if not self.wiki:
            return None
            
        search_terms = [
            f"{query} finance",
            f"{query} economics",
            f"{query} investment",
            query
        ]
        
        for term in search_terms:
            try:
                page = self.wiki.page(term)
                if page.exists():
                    
                    title_lower = page.title.lower()
                    query_words = query.lower().split()
                    
                    if any(w in title_lower for w in query_words) or len(query_words) <= 1:
                        summary = page.summary
                        if summary and len(summary) > 50:
                            truncated = summary[:800]
                            if len(summary) > 800:
                                last_period = truncated.rfind('.')
                                if last_period > 0:
                                    truncated = truncated[:last_period + 1]
                            return truncated
            except Exception as e:
                logger.debug(f"Wikipedia search failed for '{term}': {e}")
                
        return None

    def format_for_llm(self, concept: str, summary: str) -> str:
        """Format the Wikipedia summary for the LLM context."""
        return f"WIKIPEDIA KNOWLEDGE - {concept}:\n{summary}"


_wiki_service = None

def get_wikipedia_service() -> WikipediaService:
    """Get the Wikipedia service singleton."""
    global _wiki_service
    if _wiki_service is None:
        _wiki_service = WikipediaService()
    return _wiki_service
