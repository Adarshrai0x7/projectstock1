"""
Enhanced FastAPI application for the Finance Chatbot.
Includes REST and WebSocket endpoints, health checks, and CORS support.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.config.settings import settings
from chatbot.core.router import get_chat_router
from common.models.schemas import ChatRequest, ChatResponse, HealthResponse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    logger.info("🚀 Starting FinSight Chatbot API...")
    logger.info(f"📊 Default market: {settings.default_market}")
    logger.info(f"🤖 LLM Model: {settings.llm_model}")
    
    # Initialize router (preload models)
    get_chat_router()
    logger.info("✅ ChatRouter initialized")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down FinSight Chatbot API...")


# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="FinSight Chatbot API",
    description="Advanced AI-powered financial assistant for trading platforms",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST MODELS (for backward compatibility)
# ============================================================================

class MessageInput(BaseModel):
    """Simple message input for backward compatibility."""
    message: str
    session_id: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with API info."""
    return HealthResponse(
        status="healthy",
        version="2.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="2.0.0"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(input: MessageInput):
    """
    Main chat endpoint.
    
    Accepts a message and returns an AI-generated response with:
    - reply: The chatbot's response
    - intent: Detected intent type
    - entities: Extracted entities (stocks, indices, etc.)
    - suggestions: Follow-up suggestions
    - session_id: Session ID for conversation continuity
    """
    try:
        if not input.message or not input.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        router = get_chat_router()
        response = await router.process_message(
            message=input.message.strip(),
            session_id=input.session_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v2/chat", response_model=ChatResponse)
async def chat_v2_endpoint(request: ChatRequest):
    """
    V2 chat endpoint with full request model.
    """
    try:
        router = get_chat_router()
        response = await router.process_message(
            message=request.message.strip(),
            session_id=request.session_id
        )
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.
    """
    await websocket.accept()
    session_id = None
    router = get_chat_router()
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()
            session_id = data.get("session_id", session_id)
            
            if not message:
                await websocket.send_json({"error": "Empty message"})
                continue
            
            # Process message
            response = await router.process_message(
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


# ============================================================================
# DIRECT DATA ENDPOINTS
# ============================================================================

@app.get("/market/{symbol}")
async def get_stock_price(symbol: str):
    """
    Get current price for a stock symbol.
    """
    from common.data_services.market_data import get_market_data_service
    from chatbot.modules.market_formatter import MarketFormatter
    
    service = get_market_data_service()
    price = await service.get_stock_price(symbol.upper())
    
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
async def get_index_data(index_name: str):
    """
    Get current data for a market index.
    """
    from common.data_services.market_data import get_market_data_service
    
    service = get_market_data_service()
    data = await service.get_index_data(index_name.upper())
    
    if data:
        return {
            "name": data.name,
            "value": data.value,
            "change": data.change,
            "change_percent": data.change_percent
        }
    
    raise HTTPException(status_code=404, detail=f"Index {index_name} not found")


@app.get("/news")
async def get_news(symbol: Optional[str] = None, limit: int = 5):
    """
    Get financial news (optionally filtered by stock symbol).
    """
    from common.data_services.news_service import get_news_service
    
    service = get_news_service()
    
    if symbol:
        articles = await service.get_stock_news(symbol.upper(), limit)
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


# ============================================================================
# SCREENER ENDPOINTS
# ============================================================================

@app.get("/screener/screens")
async def list_screens():
    """List all available pre-built screener screens."""
    from screener.screener import get_screener_service
    screener = get_screener_service()
    return {"screens": screener.get_available_screens()}


@app.get("/analyze/{symbol}")
async def analyze_stock(symbol: str):
    """
    Get full technical + fundamental analysis for a stock.
    """
    from screener.screener import get_screener_service
    screener = get_screener_service()
    analysis = await screener.analyze_stock(symbol)
    if not analysis:
        return {"error": f"Could not analyze {symbol}"}
    return analysis.model_dump()


@app.get("/screener/{screen_name}")
async def run_screen(screen_name: str):
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
async def custom_screen(input: CustomScreenInput):
    """
    Run a custom stock screen with user-defined filters.
    
    Filter options: pe_ratio_max, pe_ratio_min, pb_ratio_max, roe_min,
    debt_to_equity_max, dividend_yield_min, profit_margin_min,
    rsi_max, rsi_min, above_sma_50, macd_bullish, score_min
    """
    from screener.screener import get_screener_service
    screener = get_screener_service()
    result = await screener.screen_stocks(
        filters=input.filters,
        stock_list=input.stock_list,
        screen_name="Custom Screen",
    )
    return result.model_dump()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True
    )
