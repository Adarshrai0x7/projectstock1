"""
Central request router for the Finance Chatbot.
Routes user queries to appropriate handlers based on intent.
"""

import asyncio
from typing import Optional, Dict, Any, Tuple
import logging

from langchain_groq import ChatGroq

from common.models.schemas import ChatResponse, Intent, ChatMessage
from chatbot.core.intent_classifier import get_intent_classifier, EmbeddingIntentClassifier
from chatbot.core.entity_extractor import get_entity_extractor, EntityExtractor, ExtractedEntities
from chatbot.core.conversation_memory import get_conversation_memory, ConversationMemory
from common.data_services.market_data import get_market_data_service, MarketDataService
from chatbot.modules.market_formatter import MarketFormatter
from common.data_services.news_service import get_news_service, NewsService
from chatbot.modules.trading_assistant import get_trading_assistant, TradingAssistant
from common.config.prompts import get_prompt_for_intent, FINSIGHT_PERSONA, SYMBOL_RESOLUTION_PROMPT
from common.config.settings import settings
from screener.screener import get_screener_service, PREBUILT_SCREENS
from screener.screener_formatter import ScreenerFormatter

logger = logging.getLogger(__name__)


class ChatRouter:
    """
    Central router that processes user queries and routes to appropriate handlers.
    Orchestrates intent classification, entity extraction, and response generation.
    """
    
    def __init__(self):
        """Initialize router with all required services."""
        # Initialize LLM
        self.llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        
        # Initialize services
        self.intent_classifier = get_intent_classifier(self.llm)
        self.entity_extractor = get_entity_extractor()
        self.memory = get_conversation_memory()
        self.market_service = get_market_data_service()
        self.news_service = get_news_service()
        self.trading_assistant = get_trading_assistant()
        self.formatter = MarketFormatter()
        
        # Load greeting responses
        self._greeting_responses = self._load_greeting_responses()
    
    def _load_greeting_responses(self) -> Dict[str, str]:
        """Load greeting responses from the existing knowledge base."""
        return {
            "hello": "Hello! 👋 Welcome to FinSight – your intelligent trading companion.\n\nI can help you with:\n• 📊 Real-time stock prices\n• 📰 Latest market news\n• 📚 Trading concepts & how-to guides\n• 💼 Portfolio insights\n\nWhat would you like to know?",
            "hi": "Hi there! 👋 I'm your FinSight assistant. How can I help you today?",
            "hey": "Hey! 👋 Ready to help with your trading queries. What's on your mind?",
            "good morning": "Good morning! ☀️ Hope you have a profitable trading day. How can I assist?",
            "good afternoon": "Good afternoon! 🌤️ How can I help you with your investments today?",
            "good evening": "Good evening! 🌙 How can I assist you today?",
            "thanks": "You're welcome! 😊 Feel free to ask anything else.",
            "thank you": "Happy to help! 🙏 Let me know if you need anything else.",
            "bye": "Goodbye! 👋 Happy trading! Come back anytime you need help.",
            "help": self.trading_assistant.get_help_suggestions(),
        }
    
    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Process a user message and generate a response.
        
        Args:
            message: User's input message
            session_id: Optional session ID for context
            
        Returns:
            ChatResponse with reply and metadata
        """
        try:
            # Get or create session
            context = self.memory.get_or_create_session(session_id)
            session_id = context.session_id
            
            # Add user message to context
            context.add_message("user", message)
            
            # Pre-classification guard: detect news explanation requests
            # (before regular classifier, to avoid stock symbol winning over news intent)
            if self._is_news_explanation_request(message):
                intent, confidence = Intent.NEWS_REQUEST, 0.95
                logger.info("Pre-classifier: detected news explanation request → NEWS_REQUEST")
            else:
                # Classify intent
                intent, confidence = self.intent_classifier.classify(message)
            logger.info(f"Intent: {intent.value} (confidence: {confidence:.2f})")
            
            # Extract entities
            entities = self.entity_extractor.extract(message)
            logger.info(f"Entities: {entities.to_dict()}")
            
            # Update context with detected intent and entities
            self.memory.update_context(
                session_id,
                intent=intent,
                entities=entities,
                last_stock=self.entity_extractor.get_primary_symbol(entities)
            )
            
            # Route to appropriate handler
            response = await self._route_to_handler(
                message=message,
                intent=intent,
                entities=entities,
                context=context
            )
            
            # Add assistant response to context
            context.add_message("assistant", response)
            
            # Generate follow-up suggestions
            suggestions = self._get_suggestions(intent, entities)
            
            return ChatResponse(
                reply=response,
                intent=intent.value,
                entities=entities.to_dict(),
                suggestions=suggestions,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return ChatResponse(
                reply=f"I apologize, but I encountered an error processing your request. Please try again. (Error: {str(e)[:100]})",
                intent="ERROR",
                session_id=session_id
            )
    
    async def _route_to_handler(
        self,
        message: str,
        intent: Intent,
        entities: ExtractedEntities,
        context: Any
    ) -> str:
        """Route query to the appropriate handler based on intent."""
        
        # Handle greetings with static responses
        if intent == Intent.GREETING:
            return self._handle_greeting(message)
        
        # Market price queries
        elif intent == Intent.MARKET_PRICE:
            return await self._handle_market_price(message, entities, context)
        
        # Market trend queries
        elif intent == Intent.MARKET_TREND:
            return await self._handle_market_trend(message, entities, context)
        
        # Stock information queries
        elif intent == Intent.STOCK_INFO:
            return await self._handle_stock_info(message, entities, context)
        
        # Trading how-to and education
        elif intent in [Intent.TRADING_HOW_TO, Intent.EDUCATION]:
            return await self._handle_trading_query(message, entities, context)
        
        # News requests
        elif intent == Intent.NEWS_REQUEST:
            if self._is_news_explanation_request(message):
                return await self._handle_news_explanation(message, entities)
            return await self._handle_news_request(message, entities)
        
        # Portfolio queries
        elif intent == Intent.PORTFOLIO_QUERY:
            return self._handle_portfolio_query(message)
        
        # Stock history / movement queries
        elif intent == Intent.STOCK_HISTORY:
            return await self._handle_stock_history(message, entities, context)
        
        # Stock screening / analysis
        elif intent == Intent.STOCK_SCREEN:
            return await self._handle_stock_screen(message, entities, context)
        
        # General queries - use LLM
        else:
            return await self._handle_general_query(message, context)
    
    def _handle_greeting(self, message: str) -> str:
        """Handle greeting messages."""
        message_lower = message.lower().strip()
        
        for key in self._greeting_responses:
            if key in message_lower:
                return self._greeting_responses[key]
        
        return self._greeting_responses["hello"]
    
    async def _resolve_symbol_via_llm(self, message: str) -> str:
        """
        Use LLM to resolve a company name to its stock ticker symbol.
        Called when entity extraction fails to find a stock symbol.
        
        Returns:
            Stock symbol string, or None if resolution fails
        """
        try:
            from langchain_core.prompts import PromptTemplate
            prompt = PromptTemplate.from_template(SYMBOL_RESOLUTION_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke({"query": message})
            
            # Clean the response — should be just a ticker symbol
            symbol = response.content.strip().upper().split()[0]
            
            # Remove any punctuation
            symbol = ''.join(c for c in symbol if c.isalnum() or c in '-&')
            
            if symbol and symbol != "UNKNOWN" and len(symbol) >= 1:
                logger.info(f"LLM resolved symbol: '{message}' → {symbol}")
                return symbol
            
            return None
        except Exception as e:
            logger.error(f"LLM symbol resolution failed: {e}")
            return None
    
    async def _handle_market_price(
        self,
        message: str,
        entities: ExtractedEntities,
        context: Any
    ) -> str:
        """Handle market price queries."""
        # Get stock symbol from entities or context
        symbol = None
        
        if entities.stock_symbols:
            symbol = entities.stock_symbols[0]
        elif entities.indices:
            # Handle index queries
            index = entities.indices[0]
            index_data = await self.market_service.get_index_data(index)
            if index_data:
                return self.formatter.format_index(index_data)
            return self.formatter.format_error(index, "not_found")
        else:
            # Check context for last mentioned stock
            last_stock = self.memory.get_last_stock(context.session_id)
            if last_stock:
                symbol = last_stock
        
        if not symbol:
            # LLM fallback: ask the AI to resolve the company name
            symbol = await self._resolve_symbol_via_llm(message)
        
        if not symbol:
            return "🔍 Which stock would you like to know the price of? Please mention a stock symbol (e.g., TCS, RELIANCE, HDFCBANK)."
        
        # Fetch price
        stock_price = await self.market_service.get_stock_price(symbol)
        
        if stock_price:
            return self.formatter.format_stock_price(stock_price)
        else:
            return self.formatter.format_error(symbol, "not_found")
    
    async def _handle_market_trend(
        self,
        message: str,
        entities: ExtractedEntities,
        context: Any
    ) -> str:
        """Handle market trend queries with smart sub-routing."""
        import re
        message_lower = message.lower()
        
        # --- Sub-route 1: Follow-up about a specific stock ("how will it perform") ---
        if re.search(r'\b(it|this|the\s+stock)\b', message_lower) and not entities.stock_symbols:
            last_stock = self.memory.get_last_stock(context.session_id)
            if last_stock:
                # Redirect to stock history for context-aware response
                entities.stock_symbols = [last_stock]
                return await self._handle_stock_history(message, entities, context)
        
        # --- Sub-route 2: Specific index mentioned ---
        if entities.indices:
            index = entities.indices[0]
            index_data = await self.market_service.get_index_data(index)
            if index_data:
                return self.formatter.format_index(index_data)
        
        # --- Fetch base market summary (used by all remaining paths) ---
        summary = await self.market_service.get_market_summary()
        summary_text = self.formatter.format_market_summary(summary) if summary else ""
        
        # --- Sub-route 3: Best/worst performing or "why" queries → LLM enriched ---
        needs_llm = bool(re.search(
            r'(best|worst|top|bottom)\s*\d*\s*(perform|stock)|'
            r'why\s+(is|are)|'
            r'(reason|detail|analysis|explain).*market|'
            r'(gainer|loser)',
            message_lower
        ))
        
        if needs_llm:
            # Gather extra context: recent news
            news_context = ""
            try:
                articles = await self.news_service.get_market_news(limit=5)
                if articles:
                    news_context = "\n".join(
                        f"- {a.title} ({a.source})" for a in articles[:5]
                    )
            except Exception:
                pass
            
            prompt = get_prompt_for_intent(Intent.MARKET_TREND.value)
            llm_context = f"""Current Market Data:\n{summary_text}\n\nRecent Headlines:\n{news_context}"""
            chat_history = self._get_chat_history(context.session_id)
            
            try:
                chain = prompt | self.llm
                response = chain.invoke({
                    "input": message,
                    "context": llm_context,
                    "chat_history": chat_history
                })
                return response.content
            except Exception as e:
                logger.error(f"LLM market trend error: {e}")
                # Fall through to basic summary
        
        # --- Default: simple market summary ---
        if summary_text:
            return summary_text
        
        return "📊 Unable to fetch market data at the moment. Please try again."
    
    async def _handle_stock_info(
        self,
        message: str,
        entities: ExtractedEntities,
        context: Any
    ) -> str:
        """Handle stock information queries."""
        symbol = None
        
        if entities.stock_symbols:
            symbol = entities.stock_symbols[0]
        else:
            last_stock = self.memory.get_last_stock(context.session_id)
            if last_stock:
                symbol = last_stock
        
        if not symbol:
            # Try LLM symbol resolution with full chat context
            chat_history = self._get_chat_history(context.session_id)
            history_text = " ".join(c for _, c in chat_history[-2:]) if chat_history else ""
            symbol = await self._resolve_symbol_via_llm(f"{history_text} {message}".strip())
        
        if not symbol:
            return "🔍 Which stock would you like information about?"
        
        # Fetch details
        details = await self.market_service.get_stock_details(symbol)
        price = await self.market_service.get_stock_price(symbol)
        
        if details:
            response = self.formatter.format_stock_details(details, price)
            if price:
                response = self.formatter.format_stock_price(price) + "\n\n" + response
            return response
        
        return self.formatter.format_error(symbol, "not_found")
    
    def _get_chat_history(self, session_id: str, limit: int = 6) -> list:
        """Return recent chat history formatted for LLM prompt injection."""
        raw = self.memory.get_chat_history(session_id, limit=limit)
        # Exclude the very last message (current user turn, not yet answered)
        return [(role, content) for role, content in raw[:-1]]

    async def _handle_trading_query(
        self,
        message: str,
        entities: ExtractedEntities,
        context: Any
    ) -> str:
        """Handle trading and educational queries."""
        # Search in knowledge base
        topic = self.trading_assistant.search(message)
        
        if topic:
            return self.trading_assistant.format_response(topic)
        
        # If no direct match, use LLM with chat history for follow-ups
        prompt = get_prompt_for_intent(Intent.EDUCATION.value)
        chat_history = self._get_chat_history(context.session_id)
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "input": message,
                "context": "User is asking about trading concepts.",
                "chat_history": chat_history
            })
            return response.content
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "📚 I couldn't find specific information on that topic. Could you try rephrasing your question?"
    
    def _is_news_explanation_request(self, message: str) -> bool:
        """Detect if the user is asking to explain a piece of news."""
        import re
        msg = message.lower()
        explanation_patterns = [
            r"(explain|summarize|elaborate|detail|break\s+down)\s+(this|the|that)\s+(news|article|headline|story)",
            r"what\s+does\s+this\s+(news|article|headline|mean|say)",
            r"(can\s+you\s+explain|tell\s+me\s+more\s+about)\s+(this|the)\s*(news|article|story|headline)",
            r"this\s+(news|article|headline|story)\s+(in\s+detail|more)",
            r"(explain|elaborate)\s+this\s+news",
            r"what\s+does\s+this\s+mean\s+for\s+(the\s+)?(stock|market|company)",
            r"explain\s+(it|this)\s+in\s+detail",
            r"can\s+you\s+explain\s+this",
        ]
        for pattern in explanation_patterns:
            if re.search(pattern, msg):
                return True
        return False

    async def _handle_news_explanation(
        self,
        message: str,
        entities: ExtractedEntities
    ) -> str:
        """Handle requests to explain a news headline/article in detail."""
        # Extract the "news" portion — everything before the explanation request keyword
        import re
        # Try to split on the explanation trigger phrase
        split_pattern = r"(explain|summarize|elaborate|can you explain|tell me more|what does this|break down)"
        parts = re.split(split_pattern, message, maxsplit=1, flags=re.IGNORECASE)
        news_text = parts[0].strip() if len(parts) > 1 else message

        # If no separate news text found, use whole message
        if not news_text or len(news_text) < 15:
            news_text = message

        # Build stock context if available
        stock_context = ""
        if entities.stock_symbols:
            symbol = entities.stock_symbols[0]
            try:
                price = await self.market_service.get_stock_price(symbol)
                if price:
                    stock_context = f"\n\nCurrent {symbol} price: ₹{price.price:.2f} (Change: {price.change_percent:+.2f}%)"
            except Exception:
                pass

        prompt_text = f"""You are FinSight, an expert financial analyst for Indian markets.

A user has shared the following financial news and wants a detailed explanation:

\"{news_text}\"
{stock_context}

Please explain this news in a clear, detailed way covering:
1. 📌 **What happened** — Summarize the key event
2. 🏢 **About the companies/parties involved** — Brief context
3. 📈 **Market impact** — What this means for the stock and sector
4. 💡 **Key takeaway** — What should an investor keep in mind?

Keep your response concise but insightful. Use bullet points where helpful."""

        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=prompt_text)])
            return response.content
        except Exception as e:
            logger.error(f"News explanation LLM error: {e}")
            return f"📰 Here's the news you shared:\n\n*{news_text}*\n\nI couldn't generate a detailed explanation right now. Please try again."

    async def _handle_news_request(
        self,
        message: str,
        entities: ExtractedEntities
    ) -> str:
        """Handle news requests."""
        if entities.stock_symbols:
            # Stock-specific news
            symbol = entities.stock_symbols[0]
            articles = await self.news_service.get_stock_news(symbol)
            if articles:
                return f"📰 **News for {symbol}**\n\n" + self.news_service.format_news(articles)
        
        # General market news
        articles = await self.news_service.get_market_news()
        return self.news_service.format_news(articles)
    
    def _handle_portfolio_query(self, message: str) -> str:
        """Handle portfolio queries (placeholder for integration)."""
        return """💼 **Portfolio Integration**

To view your portfolio, I would need access to your account data. 

Currently, this feature requires integration with your trading platform's portfolio API.

**What I can help with:**
• Explain portfolio concepts
• Analyze individual stocks you mention
• Provide market insights

Would you like me to check on any specific stock instead?"""
    
    async def _handle_stock_history(
        self,
        message: str,
        entities: ExtractedEntities,
        context: Any
    ) -> str:
        """Handle stock history / movement queries."""
        # Get stock symbol
        symbol = None
        if entities.stock_symbols:
            symbol = entities.stock_symbols[0]
        else:
            last_stock = self.memory.get_last_stock(context.session_id)
            if last_stock:
                symbol = last_stock
        
        if not symbol:
            symbol = await self._resolve_symbol_via_llm(message)
        
        if not symbol:
            return "🔍 Which stock's history would you like to see? Please mention a stock name (e.g., TCS, Tata Steel, NVIDIA)."
        
        # Parse number of days from the query
        import re
        days = 5  # default
        
        # Match digit-based patterns: "last 5 days", "10 day movement"
        day_match = re.search(r'(\d+)\s*day', message.lower())
        if day_match:
            days = min(int(day_match.group(1)), 30)  # cap at 30
        
        # Match word-based patterns: "last five days"
        word_to_num = {'two': 2, 'three': 3, 'five': 5, 'seven': 7, 'ten': 10}
        for word, num in word_to_num.items():
            if word in message.lower():
                days = num
                break
        
        # Match week/month
        if 'week' in message.lower():
            week_match = re.search(r'(\d+)\s*week', message.lower())
            days = (int(week_match.group(1)) if week_match else 1) * 7
        elif 'month' in message.lower():
            month_match = re.search(r'(\d+)\s*month', message.lower())
            days = (int(month_match.group(1)) if month_match else 1) * 30
        
        # Fetch history
        history = await self.market_service.get_stock_history(symbol, days)
        
        if not history:
            return self.formatter.format_error(symbol, "history_unavailable")
        
        # Format the API data
        formatted = self.formatter.format_stock_history(history)
        
        # If user asked a narrative/trend question, enrich with LLM commentary
        import re
        wants_analysis = bool(re.search(
            r'(how\s+(did|has|will)|why|what\s+happened|trend|outlook|perform|forecast)',
            message.lower()
        ))
        if wants_analysis:
            chat_history = self._get_chat_history(context.session_id)
            prompt = get_prompt_for_intent(Intent.STOCK_HISTORY.value)
            try:
                chain = prompt | self.llm
                llm_response = chain.invoke({
                    "input": message,
                    "context": formatted,
                    "chat_history": chat_history
                })
                return llm_response.content
            except Exception as e:
                logger.error(f"LLM history analysis error: {e}")
        
        return formatted
    
    async def _handle_general_query(
        self,
        message: str,
        context: Any
    ) -> str:
        """Handle general queries using LLM."""
        prompt = get_prompt_for_intent(Intent.GENERAL.value)
        
        # Get chat history
        history = self.memory.get_chat_history(context.session_id, limit=6)
        history_formatted = [(role, content) for role, content in history[:-1]]  # Exclude current message
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "input": message,
                "context": "General financial query.",
                "chat_history": history_formatted
            })
            return response.content
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "I apologize, but I couldn't process your request. Please try again."
    
    async def _handle_stock_screen(
        self,
        message: str,
        entities: ExtractedEntities,
        context: Any
    ) -> str:
        """Handle stock screening and analysis queries."""
        import re
        message_lower = message.lower()
        
        screener = get_screener_service()
        
        # Check if it's a single stock analysis request
        # e.g., "analyze TCS", "analysis of reliance"
        if re.search(r'(analyze|analyse|analysis)\s+(of\s+)?', message_lower):
            symbol = None
            if entities.stock_symbols:
                symbol = entities.stock_symbols[0]
            else:
                # Try context
                last_stock = self.memory.get_last_stock(context.session_id)
                if last_stock:
                    symbol = last_stock
            
            if not symbol:
                symbol = await self._resolve_symbol_via_llm(message)
            
            if not symbol:
                return "🔍 Which stock would you like me to analyze? Please mention a stock name (e.g., TCS, Reliance, NVIDIA)."
            
            analysis = await screener.analyze_stock(symbol)
            if analysis:
                return ScreenerFormatter.format_analysis(analysis)
            return f"❌ Could not analyze {symbol}. Please try another stock."
        
        # Detect which pre-built screen to run
        screen_name = None
        if any(w in message_lower for w in ['undervalued', 'undervalue', 'cheap', 'value']):
            screen_name = 'undervalued'
        elif any(w in message_lower for w in ['momentum', 'trending', 'bullish']):
            screen_name = 'momentum'
        elif any(w in message_lower for w in ['oversold', 'beaten down', 'dip', 'bounce']):
            screen_name = 'oversold'
        elif any(w in message_lower for w in ['dividend', 'yield', 'income']):
            screen_name = 'high_dividend'
        elif any(w in message_lower for w in ['strong fundamental', 'quality', 'best fundamental', 'good fundamental']):
            screen_name = 'strong_fundamentals'
        
        if screen_name:
            result = await screener.get_prebuilt_screen(screen_name)
            if result:
                return ScreenerFormatter.format_screener_result(result)
            return "❌ Screen failed. Please try again."
        
        # Default: show available screens
        screens = screener.get_available_screens()
        lines = ["📊 **Stock Screener** — Choose a screen:\n"]
        for s in screens:
            lines.append(f"• **{s['name']}** — {s['description']}")
        lines.append("\nTry: \"show me undervalued stocks\" or \"analyze TCS\"")
        return "\n".join(lines)
    
    def _get_suggestions(
        self,
        intent: Intent,
        entities: ExtractedEntities
    ) -> list:
        """Generate follow-up suggestions based on intent."""
        suggestions = []
        
        if intent == Intent.MARKET_PRICE and entities.stock_symbols:
            symbol = entities.stock_symbols[0]
            suggestions = [
                f"Tell me more about {symbol}",
                f"What's the news for {symbol}?",
                f"Last 5 day movement of {symbol}",
                "How is the market today?"
            ]
        elif intent == Intent.STOCK_HISTORY and entities.stock_symbols:
            symbol = entities.stock_symbols[0]
            suggestions = [
                f"What's the current price of {symbol}?",
                f"News about {symbol}",
                f"Analyze {symbol}",
                f"Tell me about {symbol}"
            ]
        elif intent == Intent.STOCK_SCREEN:
            suggestions = [
                "Show me undervalued stocks",
                "Find momentum stocks",
                "Show oversold stocks",
                "High dividend yield stocks",
            ]
        elif intent == Intent.NEWS_REQUEST:
            suggestions = [
                "How is Nifty doing today?",
                "Explain intraday trading",
                "What's the price of TCS?"
            ]
        elif intent == Intent.GREETING:
            suggestions = [
                "What's the price of Reliance?",
                "Show me market news",
                "Last 5 day movement of TCS",
                "Explain stop-loss"
            ]
        
        return suggestions


# Singleton instance
_router = None

def get_chat_router() -> ChatRouter:
    """Get or create the chat router singleton."""
    global _router
    if _router is None:
        _router = ChatRouter()
    return _router
