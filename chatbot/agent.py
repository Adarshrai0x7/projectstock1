"""
LangGraph Agent for the FBOT chatbot.

Architecture:
    User Message → StateGraph agent node → LLM picks tool(s) → ToolNode
    executes → LLM synthesises final answer → ChatResponse

Tools wrap existing data services (yfinance, Screener.in, news RSS, knowledge base).

## Changes Made
1.  [ARCHITECTURE] Replaced create_react_agent with a full StateGraph using typed
    AgentState (TypedDict with Annotated message list, intent, tools_used, session_id).
2.  [MEMORY] Replaced MemorySaver with AsyncSqliteSaver from
    langgraph.checkpoint.sqlite.aio using connection string "fbot.db".
    Added get_graph() async factory that lazily initialises and caches the graph.
3.  [STREAMING] Added stream_message() async generator using astream_events v2.
    Yields token chunks on on_chat_model_stream and tool-start banners.
4.  [TOOLS] Wrapped get_stock_price, get_index_data, get_market_summary,
    get_stock_details with response_format="content_and_artifact".
    Each returns tuple[str, dict] with symbol/value/timestamp artifact.
5.  [ERROR_HANDLING] Added InjectedToolCallId to all tools. Replaced bare
    "❌ Could not find…" returns with raise ToolException(...). Configured
    ToolNode(handle_tool_errors=True). Removed manual 3-attempt retry loop.
6.  [ERROR_HANDLING] Added conditional edge after agent node → tools / fallback / END.
    Fallback node catches Groq bad-format errors and returns a safe ChatResponse.
7.  [PERFORMANCE] Converted get_stock_details to use asyncio.gather() for
    concurrent price + details + fundamentals fetching.
8.  [PERFORMANCE] Extracted analyze_stock into a LangGraph sub-graph with
    fan-out (START → 3 fetch nodes in parallel) and fan-in (→ synthesise → END).
9.  [ARCHITECTURE] Replaced regex _extract_suggestions() with structured LLM
    call using .with_structured_output() on AgentSuggestions Pydantic model.
"""

import asyncio
import logging
import operator
import uuid
from typing import Optional, List, Annotated, TypedDict
from datetime import datetime, timezone
from langchain_groq import ChatGroq
from langchain_core.tools import tool, ToolException, InjectedToolCallId
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.constants import Send
from pydantic import BaseModel, Field

from common.config.settings import settings
from common.config.prompts import AGENT_SYSTEM_PROMPT
from common.models.schemas import ChatResponse
from chatbot.core.symbol_utils import resolve_symbol, resolve_index

logger = logging.getLogger(__name__)
class AgentState(TypedDict):
    """Typed state for the main agent graph."""
    messages: Annotated[list, add_messages]
    intent: str
    tools_used: list[str]
    session_id: str


class AnalysisSubState(TypedDict):
    """State for the analyze_stock fan-out sub-graph."""
    symbol: str
    price_data: Annotated[list, operator.add]
    fundamentals_data: Annotated[list, operator.add]
    technicals_data: Annotated[list, operator.add]
    final_output: str


class AgentSuggestions(BaseModel):
    """Structured output model for follow-up suggestions."""
    suggestions: list[str] = Field(default_factory=list, max_length=4)


# ── Pydantic input schemas for LLM tool calling ────────────────────────
# These force the LLM to cleanly extract the company name / query
# from the user's message before calling the tool.

class StockQueryInput(BaseModel):
    """Input schema for tools that operate on a single stock."""
    company_name: str = Field(
        description=(
            "The name of the company or stock the user is asking about. "
            "Extract the plain name exactly as the user said it, "
            "e.g. 'Tata Motors', 'ICICI Bank', 'Zomato', 'RELIANCE'."
        )
    )


class StockHistoryInput(BaseModel):
    """Input schema for historical stock data requests."""
    company_name: str = Field(
        description=(
            "The name of the company or stock. "
            "Extract the plain name, e.g. 'Infosys', 'HDFC Bank'."
        )
    )
    days: int = Field(
        description=(
            "Number of trading days of history to fetch. "
            "Use 5 for recent, 7 for 'last week', 30 for 'last month', "
            "90 for 'last quarter'."
        )
    )


class NewsQueryInput(BaseModel):
    """Input schema for news queries."""
    query: str = Field(
        description=(
            "The company name or topic for news. "
            "Pass the plain company name like 'TCS' or 'Reliance' "
            "for stock-specific news. Pass 'market' for general news."
        )
    )


class ScreenerInput(BaseModel):
    """Input schema for stock screener."""
    screen_name: str = Field(
        description=(
            "The type of stock screen to run. "
            "One of: 'undervalued', 'momentum', 'oversold', "
            "'high_dividend', 'strong_fundamentals'."
        )
    )


@tool(args_schema=StockQueryInput, response_format="content_and_artifact")
async def get_stock_price(
    company_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> tuple[str, dict]:
    """
    Get the current real-time price of a stock.
    Use this when the user asks for a stock's price, rate, CMP, LTP, or value.
    Accepts company names (Tata Motors, Infosys) or stock symbols (TCS, RELIANCE).
    """
    from common.data_services.market_data import get_market_data_service
    from chatbot.modules.market_formatter import MarketFormatter

    resolved = resolve_symbol(company_name) or company_name.upper()
    service = get_market_data_service()
    price = await service.get_stock_price(resolved)

    if price:
        content = MarketFormatter.format_stock_price(price)
        artifact = {
            "symbol": resolved,
            "value": price.price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return content, artifact
    raise ToolException(f"Could not find price data for '{company_name}'. Please check the stock name.")


@tool(response_format="content_and_artifact")
async def get_index_data(
    index_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> tuple[str, dict]:
    """
    Get the current value of a market index like NIFTY 50, SENSEX, or BANK NIFTY.
    Use this when the user asks about market indices.
    """
    from common.data_services.market_data import get_market_data_service
    from chatbot.modules.market_formatter import MarketFormatter

    resolved = resolve_index(index_name) or index_name.upper()
    service = get_market_data_service()
    data = await service.get_index_data(resolved)

    if data:
        content = MarketFormatter.format_index(data)
        artifact = {
            "symbol": resolved,
            "value": data.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return content, artifact
    raise ToolException(f"Could not find data for index '{index_name}'.")


@tool(response_format="content_and_artifact")
async def get_market_summary(
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> tuple[str, dict]:
    """
    Get an overview of the entire Indian stock market — NIFTY 50, SENSEX, Bank NIFTY levels.
    Use this when the user asks 'how is the market today' or wants a market overview.
    """
    from common.data_services.market_data import get_market_data_service
    from chatbot.modules.market_formatter import MarketFormatter

    service = get_market_data_service()
    summary = await service.get_market_summary()

    if summary:
        content = MarketFormatter.format_market_summary(summary)
        artifact = {
            "symbol": "MARKET_OVERVIEW",
            "value": "summary",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return content, artifact
    raise ToolException("Unable to fetch market data at the moment.")


@tool(args_schema=StockQueryInput, response_format="content_and_artifact")
async def get_stock_details(
    company_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> tuple[str, dict]:
    """
    Get detailed company information including sector, PE ratio, EPS, market cap,
    52-week range, and fundamental data from Screener.in.
    Use this when the user asks 'tell me about TCS', 'PE ratio of X', or wants company info.
    """
    from common.data_services.market_data import get_market_data_service
    from common.data_services.screener_in_service import get_screener_in_service
    from chatbot.modules.market_formatter import MarketFormatter
    from chatbot.rag_chain import get_wikipedia_summary

    resolved = resolve_symbol(company_name) or company_name.upper()
    service = get_market_data_service()
    screener = get_screener_in_service()

    # Upgrade 7: fetch concurrently with asyncio.gather
    details, price, fundamentals = await asyncio.gather(
        service.get_stock_details(resolved),
        service.get_stock_price(resolved),
        screener.get_fundamentals(resolved),
    )

    parts = []

    if price:
        parts.append(MarketFormatter.format_stock_price(price))

    if details:
        parts.append(MarketFormatter.format_stock_details(details, price))
        wiki = get_wikipedia_summary((details.name or resolved) + " company India")
        if wiki:
            parts.append(f"\n📖 **Wikipedia:** {wiki}")

    if fundamentals:
        parts.append(f"\n📊 **Screener.in Fundamentals:**\n{screener.format_for_llm(fundamentals)}")

    if parts:
        content = "\n\n".join(parts)
        artifact = {
            "symbol": resolved,
            "value": price.price if price else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return content, artifact
    raise ToolException(f"Could not find details for '{company_name}'.")


@tool(args_schema=StockHistoryInput)
async def get_stock_history(
    company_name: str,
    days: int,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """
    Get historical stock price data (OHLCV) for the last N trading days.
    Use this when the user asks about past performance, price movement, trends over days/weeks.
    """
    from common.data_services.market_data import get_market_data_service
    from chatbot.modules.market_formatter import MarketFormatter

    resolved = resolve_symbol(company_name) or company_name.upper()
    days = min(max(days, 1), 90)

    service = get_market_data_service()
    history = await service.get_stock_history(resolved, days)

    if history:
        return MarketFormatter.format_stock_history(history)
    raise ToolException(f"Could not fetch history for '{company_name}'.")


@tool(args_schema=NewsQueryInput)
async def get_stock_news(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """
    Get the latest financial news articles.
    Pass a company name like 'TCS' or 'Reliance' for stock-specific news.
    Pass 'market' for general market news and headlines.
    """
    from common.data_services.news_service import get_news_service

    service = get_news_service()

    if query.lower() in ("market", "general", "latest", "all", "news"):
        articles = await service.get_market_news(limit=5)
    else:
        resolved = resolve_symbol(query) or query.upper()
        articles = await service.get_stock_news(resolved, limit=5)

    return service.format_news(articles)


@tool
def search_knowledge_base(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """
    Search the trading knowledge base and Wikipedia for educational content.
    Use this when the user asks 'what is X', 'explain Y', or wants to learn
    about trading concepts like stop-loss, PE ratio, intraday, candlestick patterns, etc.
    """
    from chatbot.modules.trading_assistant import get_trading_assistant
    from chatbot.rag_chain import get_rag_retriever, get_tavily_search
    from common.data_services.wikipedia_service import get_wikipedia_service

    parts = []


    assistant = get_trading_assistant()
    topic = assistant.search(query)
    if topic:
        parts.append(assistant.format_response(topic))

    retriever = get_rag_retriever()
    if retriever:
        try:
            docs = retriever.invoke(query)
            if docs:
                rag_text = "\n".join(d.page_content for d in docs[:2])
                parts.append(f"📚 **Local Knowledge:**\n{rag_text}")
        except Exception:
            pass
            
   
    tavily_context = get_tavily_search(query)
    if tavily_context:
        parts.append(f"🌐 **Web Context:**\n{tavily_context}")

   
    wiki_service = get_wikipedia_service()
    search_query = query.lower()
    for prefix in ("what is", "tell me about", "explain", "define"):
        search_query = search_query.replace(prefix, "").strip()
    search_query = search_query.rstrip("?")

    wiki_summary = wiki_service.search_concept(search_query) if search_query else None
    if wiki_summary:
        parts.append(wiki_service.format_for_llm(search_query, wiki_summary))

    if parts:
        return "\n\n".join(parts)
    return f"No specific knowledge found for '{query}'. Please answer from your financial expertise."


@tool(args_schema=ScreenerInput)
async def screen_stocks(
    screen_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """
    Run a predefined stock screener to find stocks matching criteria.
    Use this when the user asks for 'undervalued stocks', 'momentum stocks', 'best stocks', etc.
    """
    from screener.screener import get_screener_service
    from screener.screener_formatter import ScreenerFormatter

    screener = get_screener_service()

    screen_map = {
        "undervalued": "undervalued", "cheap": "undervalued", "value": "undervalued",
        "momentum": "momentum", "trending": "momentum", "bullish": "momentum",
        "oversold": "oversold", "beaten down": "oversold", "dip": "oversold",
        "dividend": "high_dividend", "yield": "high_dividend", "income": "high_dividend",
        "strong fundamentals": "strong_fundamentals", "quality": "strong_fundamentals",
    }

    resolved_screen = screen_map.get(screen_name.lower(), screen_name.lower())
    result = await screener.get_prebuilt_screen(resolved_screen)

    if result:
        return ScreenerFormatter.format_screener_result(result)

    screens = screener.get_available_screens()
    lines = ["📊 **Available Stock Screens:**\n"]
    for s in screens:
        lines.append(f"• **{s['name']}** — {s['description']}")
    return "\n".join(lines)



async def _fetch_price_node(state: AnalysisSubState) -> dict:
    """Fetch current stock price."""
    try:
        from common.data_services.market_data import get_market_data_service
        service = get_market_data_service()
        price = await service.get_stock_price(state["symbol"])
        return {"price_data": [price]}
    except Exception as e:
        logger.error(f"Sub-graph fetch_price error: {e}")
        return {"price_data": [None]}


async def _fetch_fundamentals_node(state: AnalysisSubState) -> dict:
    """Fetch fundamental data via screener service."""
    try:
        from common.data_services.market_data import get_market_data_service
        from screener.screener import get_screener_service
        service = get_market_data_service()
        yf_symbol, _ = service._detect_market(state["symbol"])
        screener = get_screener_service()
        fundamental = await screener._get_fundamentals(yf_symbol, state["symbol"])
        return {"fundamentals_data": [fundamental]}
    except Exception as e:
        logger.error(f"Sub-graph fetch_fundamentals error: {e}")
        return {"fundamentals_data": [None]}


def _fetch_technicals_node(state: AnalysisSubState) -> dict:
    """Fetch technical indicators (sync — runs in thread pool)."""
    try:
        from common.data_services.market_data import get_market_data_service
        from screener.technical_indicators import get_indicator_service
        service = get_market_data_service()
        yf_symbol, _ = service._detect_market(state["symbol"])
        indicators = get_indicator_service()
        tech_data = indicators.get_all_indicators(yf_symbol, period="6mo")
        return {"technicals_data": [tech_data]}
    except Exception as e:
        logger.error(f"Sub-graph fetch_technicals error: {e}")
        return {"technicals_data": [{}]}


async def _synthesise_node(state: AnalysisSubState) -> dict:
    """Combine fetched data into a formatted analysis string."""
    from screener.screener_formatter import ScreenerFormatter
    from common.data_services.market_data import get_market_data_service
    from common.models.schemas import (
        StockAnalysis, TechnicalIndicators, FundamentalData, Market,
    )

    symbol = state["symbol"]
    price = state["price_data"][0] if state.get("price_data") else None
    tech_data = state["technicals_data"][0] if state.get("technicals_data") else {}
    fundamental = state["fundamentals_data"][0] if state.get("fundamentals_data") else None

    if not tech_data and not price:
        return {"final_output": ""}

    service = get_market_data_service()
    _, detected_market = service._detect_market(symbol)
    market_enum = Market.US if detected_market == "US" else Market.NSE

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

    current_price = tech_data.get("current_price", 0)
    if current_price == 0 and price:
        current_price = price.price
    change_pct = price.change_percent if price else 0
    stock_name = price.name if price else symbol

    analysis = StockAnalysis(
        symbol=symbol.upper(),
        name=stock_name,
        price=current_price,
        change_percent=change_pct,
        technical=technical,
        fundamental=fundamental or FundamentalData(),
        signal=tech_data.get("composite_signal", "NEUTRAL"),
        score=tech_data.get("composite_score", 50.0),
        market=market_enum,
    )
    return {"final_output": ScreenerFormatter.format_analysis(analysis)}


def _dispatch_analysis(state: AnalysisSubState):
    """Fan-out: send state to all 3 fetch nodes in parallel."""
    return [
        Send("fetch_price", state),
        Send("fetch_fundamentals", state),
        Send("fetch_technicals", state),
    ]


_analysis_subgraph = None


def _get_analysis_subgraph():
    """Build and cache the analysis sub-graph."""
    global _analysis_subgraph
    if _analysis_subgraph is None:
        builder = StateGraph(AnalysisSubState)
        builder.add_node("fetch_price", _fetch_price_node)
        builder.add_node("fetch_fundamentals", _fetch_fundamentals_node)
        builder.add_node("fetch_technicals", _fetch_technicals_node)
        builder.add_node("synthesise", _synthesise_node)

        builder.add_conditional_edges(START, _dispatch_analysis)
        builder.add_edge("fetch_price", "synthesise")
        builder.add_edge("fetch_fundamentals", "synthesise")
        builder.add_edge("fetch_technicals", "synthesise")
        builder.add_edge("synthesise", END)

        _analysis_subgraph = builder.compile()
    return _analysis_subgraph


@tool(args_schema=StockQueryInput)
async def analyze_stock(
    company_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """
    Run a full technical + fundamental analysis on a single stock.
    Returns composite score, signal (BUY/SELL/HOLD), RSI, MACD, PE ratio, etc.
    Use this when the user asks to 'analyze X', 'full analysis of X', 'should I look at X'.
    """
    resolved = resolve_symbol(company_name) or company_name.upper()
    subgraph = _get_analysis_subgraph()
    result = await subgraph.ainvoke({
        "symbol": resolved,
        "price_data": [],
        "fundamentals_data": [],
        "technicals_data": [],
        "final_output": "",
    })

    if result.get("final_output"):
        return result["final_output"]
    raise ToolException(f"Could not analyze '{company_name}'. Please try another stock.")




TOOL_INTENT_MAP = {
    "get_stock_price": "MARKET_PRICE",
    "get_index_data": "MARKET_TREND",
    "get_market_summary": "MARKET_TREND",
    "get_stock_details": "STOCK_INFO",
    "get_stock_history": "STOCK_HISTORY",
    "get_stock_news": "NEWS_REQUEST",
    "search_knowledge_base": "EDUCATION",
    "screen_stocks": "STOCK_SCREEN",
    "analyze_stock": "STOCK_SCREEN",
}




ALL_TOOLS = [
    get_stock_price,
    get_index_data,
    get_market_summary,
    get_stock_details,
    get_stock_history,
    get_stock_news,
    search_knowledge_base,
    screen_stocks,
    analyze_stock,
]




def _build_main_graph(llm: ChatGroq, checkpointer):
    """Build and compile the main agent StateGraph."""

    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    # --- nodes -----------------------------------------------------------

    async def agent_node(state: AgentState) -> dict:
        """Invoke the LLM with bound tools."""
        try:
            system_msg = SystemMessage(content=AGENT_SYSTEM_PROMPT)
            response = await llm_with_tools.ainvoke(
                [system_msg] + list(state["messages"])
            )
            return {"messages": [response]}
        except Exception as e:
            error_str = str(e)
            if any(kw in error_str for kw in [
                "Failed to call a function",
                "failed_generation",
            ]):
                marker = AIMessage(
                    content=f"__GROQ_FORMAT_ERROR__:{error_str[:200]}"
                )
                return {"messages": [marker]}
            raise

    async def fallback_node(state: AgentState) -> dict:
        """Return a safe message when Groq produces malformed tool calls."""
        safe = AIMessage(
            content=(
                "I apologize, but I encountered a temporary processing issue. "
                "Please try rephrasing your question or try again in a moment."
            )
        )
        return {"messages": [safe]}

    # --- routing ---------------------------------------------------------

    def route_after_agent(state: AgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage):
            if (isinstance(last.content, str)
                    and last.content.startswith("__GROQ_FORMAT_ERROR__")):
                return "fallback"
            if getattr(last, "tool_calls", None):
                return "tools"
        return END

    # --- assemble --------------------------------------------------------

    tools_node = ToolNode(ALL_TOOLS, handle_tool_errors=True)

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tools_node)
    builder.add_node("fallback", fallback_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "fallback": "fallback", END: END},
    )
    builder.add_edge("tools", "agent")   # loop back for multi-step
    builder.add_edge("fallback", END)

    return builder.compile(checkpointer=checkpointer)




class FBotAgent:
    """
    LangGraph-powered FBOT agent.
    Uses a custom StateGraph with an agent node, tool node, and fallback node.
    Must call ``await initialize()`` before first use to set up the async
    SQLite checkpointer.
    """

    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        self.graph = None
        self._saver_cm = None  # async context-manager handle

    # --- lifecycle -------------------------------------------------------

    async def initialize(self):
        """Compile the graph inside an async context manager (required for
        AsyncSqliteSaver). Call once at application startup."""
        if self.graph is not None:
            return
        self._saver_cm = AsyncSqliteSaver.from_conn_string("fbot.db")
        saver = await self._saver_cm.__aenter__()
        self.graph = _build_main_graph(self.llm, saver)
        logger.info(
            f"✅ FBOT LangGraph agent ready — {len(ALL_TOOLS)} tools loaded"
        )

    async def shutdown(self):
        """Close the SQLite checkpointer connection."""
        if self._saver_cm:
            await self._saver_cm.__aexit__(None, None, None)
            self._saver_cm = None

    # --- main entry point ------------------------------------------------

    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> ChatResponse:
        """Process a user message through the LangGraph agent."""
        session_id = session_id or str(uuid.uuid4())

        try:
            config = {"configurable": {"thread_id": session_id}}
            result = await self.graph.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config=config,
            )

            # Walk messages for tools used and final reply
            messages = result.get("messages", [])
            reply = ""
            tools_used: list[str] = []

            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tools_used.append(tc.get("name", ""))
                if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                    reply = msg.content

            if not reply:
                reply = (
                    messages[-1].content if messages
                    else "I couldn't process your request."
                )

            intent = self._derive_intent(tools_used, message)
            suggestions = await self._get_suggestions(reply)

            return ChatResponse(
                reply=reply,
                intent=intent,
                suggestions=suggestions,
                session_id=session_id,
            )

        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            return ChatResponse(
                reply=(
                    "I apologize, but I encountered an error. "
                    f"Please try again. (Error: {str(e)[:100]})"
                ),
                intent="ERROR",
                session_id=session_id,
            )

    # --- streaming entry point (Upgrade 3) -------------------------------

    async def stream_message(
        self,
        message: str,
        session_id: Optional[str] = None,
    ):
        """Async generator that yields token chunks and tool-start banners.

        Usage::

            async for chunk in agent.stream_message("price of TCS"):
                print(chunk, end="", flush=True)
        """
        session_id = session_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": session_id}}

        async for event in self.graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            version="v2",
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk_content = event["data"]["chunk"].content
                if chunk_content:
                    yield chunk_content
            elif kind == "on_tool_start":
                tool_name = event.get("name", "tool")
                yield f"\n⚙️ Using {tool_name}...\n"
            elif kind == "on_tool_end":
                tool_output = event["data"].get("output", "")
                # ToolMessage objects have a .content attribute
                if hasattr(tool_output, "content"):
                    tool_output = tool_output.content
                if isinstance(tool_output, str) and tool_output.strip():
                    yield f"\n{tool_output}\n\n"

    # --- helpers (unchanged) ---------------------------------------------

    def derive_intent(self, tools_used: List[str], message: str) -> str:
        """Map tool usage back to an intent string for the UI badge."""
        if not tools_used:
            msg_lower = message.lower().strip()
            greetings = [
                "hi", "hello", "hey", "thanks", "bye", "good morning",
                "good afternoon", "good evening", "how are you",
            ]
            if any(g in msg_lower for g in greetings):
                return "GREETING"
            return "GENERAL"
        primary_tool = tools_used[0]
        return TOOL_INTENT_MAP.get(primary_tool, "GENERAL")

    # Keep backward-compatible alias
    _derive_intent = derive_intent

    # --- structured suggestions (Upgrade 9) ------------------------------

    async def get_suggestions(self, reply: str) -> List[str]:
        """Extract follow-up suggestions via structured LLM output."""
        try:
            structured_llm = self.llm.with_structured_output(AgentSuggestions)
            result = await structured_llm.ainvoke(
                "Based on this financial assistant response, suggest 2-3 "
                "relevant follow-up questions the user might want to ask. "
                "Keep them concise and actionable.\n\n"
                f"Response:\n{reply[:500]}"
            )
            return result.suggestions[:4]
        except Exception:
            logger.debug("Structured suggestions extraction failed", exc_info=True)
            return []

    # Keep backward-compatible alias
    _get_suggestions = get_suggestions




_agent: Optional[FBotAgent] = None


def get_agent() -> FBotAgent:
    """Get or create the FBOT agent singleton.
    NOTE: You must call ``await get_agent().initialize()`` once at startup
    before invoking process_message / stream_message."""
    global _agent
    if _agent is None:
        _agent = FBotAgent()
    return _agent


_graph_cache = None


async def get_graph():
    """Async factory that lazily initialises and caches the compiled graph."""
    global _graph_cache
    if _graph_cache is None:
        agent = get_agent()
        if agent.graph is None:
            await agent.initialize()
        _graph_cache = agent.graph
    return _graph_cache
