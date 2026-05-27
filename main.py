"""
FastAPI application for the FinSight Chatbot.
Powered by a LangGraph ReAct agent with tool-calling.
Includes REST and WebSocket endpoints, health checks, and CORS support.
"""

import json
import logging
import re
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from common.config.settings import settings
from chatbot.agent import get_agent, get_graph
from common.models.schemas import ChatRequest, ChatResponse, HealthResponse



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
        )
        logger.info("🛡️ Sentry error monitoring enabled")
    logger.info("🚀 Starting FinSight Chatbot API...")
    logger.info(f"📊 Default market: {settings.default_market}")
    logger.info(f"🤖 LLM Model: {settings.llm_model}")
    
    # Initialize LangGraph agent with async SQLite checkpointer
    agent = get_agent()
    await agent.initialize()
    logger.info("✅ FinSight LangGraph agent initialized")
    
    yield
    
    # Shutdown — close the SQLite checkpointer connection
    await agent.shutdown()
    logger.info("👋 Shutting down FinSight Chatbot API...")



app = FastAPI(
    title="FinSight Chatbot API",
    description="AI-powered financial assistant using LangGraph agent architecture",
    version="3.0.0",
    lifespan=lifespan
)

# Rate limiting — only enable if configured
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Dynamic rate-limit string from settings
_RATE_LIMIT = f"{settings.rate_limit_per_minute}/minute"


def _validate_symbol(symbol: str) -> str:
    """Validate and sanitize a stock/index symbol."""
    if not re.match(r'^[A-Za-z0-9._&-]{1,20}$', symbol):
        raise HTTPException(status_code=400, detail=f"Invalid symbol format: '{symbol}'")
    return symbol.upper()


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageInput(BaseModel):
    """Simple message input for backward compatibility."""
    message: str
    session_id: Optional[str] = None



@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with API info."""
    return HealthResponse(
        status="healthy",
        version="3.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="3.0.0"
    )


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(_RATE_LIMIT)
async def chat_endpoint(request: Request, input: MessageInput):
    """
    Main chat endpoint — powered by LangGraph ReAct agent.
    
    The agent dynamically selects the right tool(s) to answer the query:
    stock prices, news, analysis, education, screening, and more.
    """
    try:
        if not input.message or not input.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        agent = get_agent()
        response = await agent.process_message(
            message=input.message.strip(),
            session_id=input.session_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v2/chat", response_model=ChatResponse)
@limiter.limit(_RATE_LIMIT)
async def chat_v2_endpoint(request: Request, request_body: ChatRequest):
    """V2 chat endpoint with full request model."""
    try:
        agent = get_agent()
        response = await agent.process_message(
            message=request_body.message.strip(),
            session_id=request_body.session_id
        )
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/stream")
@limiter.limit(_RATE_LIMIT)
async def stream_chat(request: Request, input: MessageInput):
    """
    Streaming chat endpoint — returns Server-Sent Events (SSE).

    Events:
      - {type: "token", content: "..."} — LLM output tokens
      - {type: "status", content: "..."} — tool usage notifications
      - {type: "done", intent: "...", suggestions: [...], session_id: "..."}
    """
    if not input.message or not input.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    agent = get_agent()
    session_id = input.session_id or str(uuid.uuid4())

    async def event_generator():
        full_reply_parts = []
        tools_used = []

        async for chunk in agent.stream_message(
            message=input.message.strip(),
            session_id=session_id,
        ):
            full_reply_parts.append(chunk)
            stripped = chunk.strip()

            if stripped.startswith("\u2699\ufe0f Using ") and stripped.endswith("..."):
                tool_name = stripped.replace("\u2699\ufe0f Using ", "").rstrip(".")
                tools_used.append(tool_name)
                yield f"data: {json.dumps({'type': 'status', 'content': stripped})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

        full_reply = "".join(full_reply_parts)
        intent = agent.derive_intent(tools_used, input.message.strip())
        try:
            suggestions = await agent.get_suggestions(full_reply[:500])
        except Exception:
            suggestions = []

        yield f"data: {json.dumps({'type': 'done', 'intent': intent, 'suggestions': suggestions, 'session_id': session_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )



@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat via LangGraph agent."""
    await websocket.accept()
    session_id = None
    agent = get_agent()
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()
            session_id = data.get("session_id", session_id)
            
            if not message:
                await websocket.send_json({"error": "Empty message"})
                continue
            
            # Process message via LangGraph agent
            response = await agent.process_message(
                message=message,
                session_id=session_id
            )
            
            # Send response
            await websocket.send_json({
                "reply": response.reply,
                "intent": response.intent,
                "entities": response.entities,
                "suggestions": response.suggestions,
                "session_id": response.session_id
            })
            
            # Update session_id for continuity
            session_id = response.session_id
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()



@app.get("/market/{symbol}")
@limiter.limit(_RATE_LIMIT)
async def get_stock_price(request: Request, symbol: str):
    """Get current price for a stock symbol."""
    symbol = _validate_symbol(symbol)
    from common.data_services.market_data import get_market_data_service
    from chatbot.modules.market_formatter import MarketFormatter
    
    service = get_market_data_service()
    price = await service.get_stock_price(symbol)
    
    if price:
        return {
            "symbol": price.symbol,
            "price": price.price,
            "change": price.change,
            "change_percent": price.change_percent,
            "formatted": MarketFormatter.format_quick_price(price)
        }
    
    raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")


@app.get("/index/{index_name}")
@limiter.limit(_RATE_LIMIT)
async def get_index_data(request: Request, index_name: str):
    """Get current data for a market index."""
    index_name = _validate_symbol(index_name)
    from common.data_services.market_data import get_market_data_service
    
    service = get_market_data_service()
    data = await service.get_index_data(index_name)
    
    if data:
        return {
            "name": data.name,
            "value": data.value,
            "change": data.change,
            "change_percent": data.change_percent
        }
    
    raise HTTPException(status_code=404, detail=f"Index {index_name} not found")


@app.get("/news")
@limiter.limit(_RATE_LIMIT)
async def get_news(request: Request, symbol: Optional[str] = None, limit: int = 5):
    """Get financial news (optionally filtered by stock symbol)."""
    from common.data_services.news_service import get_news_service
    
    service = get_news_service()
    
    limit = min(max(limit, 1), 50)  # clamp between 1–50
    if symbol:
        symbol = _validate_symbol(symbol)
        articles = await service.get_stock_news(symbol, limit)
    else:
        articles = await service.get_market_news(limit)
    
    return {
        "articles": [
            {
                "title": a.title,
                "summary": a.summary,
                "source": a.source,
                "url": a.url,
                "published_at": a.published_at.isoformat()
            }
            for a in articles
        ]
    }



@app.get("/screener/screens")
@limiter.limit(_RATE_LIMIT)
async def list_screens(request: Request):
    """List all available pre-built screener screens."""
    from screener.screener import get_screener_service
    screener = get_screener_service()
    return {"screens": screener.get_available_screens()}


@app.get("/analyze/{symbol}")
@limiter.limit(_RATE_LIMIT)
async def analyze_stock(request: Request, symbol: str):
    """Get full technical + fundamental analysis for a stock."""
    symbol = _validate_symbol(symbol)
    from screener.screener import get_screener_service
    screener = get_screener_service()
    analysis = await screener.analyze_stock(symbol)
    if not analysis:
        return {"error": f"Could not analyze {symbol}"}
    return analysis.model_dump()


@app.get("/screener/{screen_name}")
@limiter.limit(_RATE_LIMIT)
async def run_screen(request: Request, screen_name: str):
    """
    Run a pre-built stock screen.
    Options: undervalued, momentum, oversold, high_dividend, strong_fundamentals
    """
    from screener.screener import get_screener_service
    screener = get_screener_service()
    result = await screener.get_prebuilt_screen(screen_name)
    if not result:
        return {"error": f"Unknown screen: {screen_name}", "available": list(screener.get_available_screens())}
    return result.model_dump()


class CustomScreenInput(BaseModel):
    filters: dict
    stock_list: Optional[list] = None


@app.post("/screener/custom")
@limiter.limit(_RATE_LIMIT)
async def custom_screen(request: Request, input: CustomScreenInput):
    """Run a custom stock screen with user-defined filters."""
    from screener.screener import get_screener_service
    screener = get_screener_service()
    result = await screener.screen_stocks(
        filters=input.filters,
        stock_list=input.stock_list,
        screen_name="Custom Screen",
    )
    return result.model_dump()




if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", settings.server_port))
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=port,
        reload=False
    )
