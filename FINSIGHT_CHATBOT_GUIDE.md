# 🤖 FinSight Chatbot — Complete Build Guide

> **Everything we did, what we used, and why — so you can learn, recall, and rebuild anytime.**

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & How It All Connects](#2-architecture--how-it-all-connects)
3. [Step-by-Step: What We Built & Why](#3-step-by-step-what-we-built--why)
4. [Technology Stack Explained](#4-technology-stack-explained)
5. [File-by-File Breakdown](#5-file-by-file-breakdown)
6. [How a Message Flows Through the System](#6-how-a-message-flows-through-the-system)
7. [Key Concepts You Learned](#7-key-concepts-you-learned)
8. [Quick Reference Cheat Sheet](#8-quick-reference-cheat-sheet)

---

## 1. Project Overview

**FinSight** is an AI-powered financial chatbot for a trading platform (similar to Groww). It can:

| Feature | Example Query |
|---------|---------------|
| 📊 Real-time stock prices | "What's the price of TCS?" |
| 📈 Market trends | "How is Nifty doing today?" |
| 📰 Financial news | "Show me market news" |
| 📚 Trading education | "Explain stop-loss" |
| 💬 Smart conversations | Remembers context across messages |
| 🔌 REST + WebSocket API | Can be plugged into any frontend |

---

## 2. Architecture & How It All Connects

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────┐
│  main.py (FastAPI Server)                       │
│  Receives HTTP/WebSocket requests               │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  core/router.py (ChatRouter)                    │
│  The BRAIN — orchestrates everything            │
│                                                 │
│  1. Classifies intent (what user wants)         │
│  2. Extracts entities (stocks, indices, etc.)   │
│  3. Routes to the right handler                 │
│  4. Returns formatted response                  │
└──┬──────────┬──────────┬──────────┬─────────────┘
   │          │          │          │
   ▼          ▼          ▼          ▼
┌──────┐ ┌────────┐ ┌───────┐ ┌──────────┐
│Intent│ │Entity  │ │Market │ │Trading   │
│Class.│ │Extract.│ │Data   │ │Assistant │
└──────┘ └────────┘ │+ News │ │+ Memory  │
                    └───────┘ └──────────┘
```

---

## 3. Step-by-Step: What We Built & Why

### Step 1: Project Setup & Environment

**What we did:**
- Created the project folder structure with separate directories for each concern
- Set up a `.env` file to store API keys securely
- Created `requirements.txt` to list all dependencies

**Why:** Clean project structure makes code maintainable. Environment variables keep secrets out of code.

**Folder structure we created:**
```
CHATBOT/
├── main.py              ← Entry point (FastAPI app)
├── rag_chain.py          ← RAG pipeline (early version)
├── requirements.txt      ← All Python packages
├── .env                  ← API keys (GROQ_API_KEY)
├── config/               ← Settings & prompts
├── core/                 ← Brain: routing, intent, entities, memory
├── modules/              ← Features: market data, news, trading knowledge
├── models/               ← Data structures (Pydantic schemas)
├── utils/                ← Utilities: caching
└── data/                 ← Static data: greeting_data.json
```

---

### Step 2: Data Models & Schemas (`models/schemas.py`)

**What we did:**
- Defined all data structures using **Pydantic** models
- Created enums for Intent types (`MARKET_PRICE`, `GREETING`, etc.) and Markets (`NSE`, `BSE`)
- Defined models for: `ChatRequest`, `ChatResponse`, `StockPrice`, `IndexData`, `NewsArticle`, `ConversationContext`, etc.

**Why:** Pydantic models give us:
- **Automatic validation** — bad data gets rejected automatically
- **Type safety** — IDE tells you if you use wrong types
- **API docs** — FastAPI auto-generates documentation from these models

**Key models and what they represent:**

| Model | Purpose |
|-------|---------|
| `Intent` (Enum) | All possible user intents (9 types) |
| `ChatRequest` | What the frontend sends us |
| `ChatResponse` | What we send back (reply + metadata) |
| `StockPrice` | Stock price data from yfinance |
| `IndexData` | Market index data (Nifty, Sensex) |
| `NewsArticle` | A news article with title, summary, source |
| `ConversationContext` | Session state with message history |

---

### Step 3: Configuration Management (`config/settings.py`)

**What we did:**
- Created a `Settings` class using **Pydantic Settings** (`BaseSettings`)
- All config values loaded from `.env` or use smart defaults
- Used `@lru_cache()` to create a singleton settings instance

**Why:** Centralized config means you change settings in ONE place, not scattered across files.

**Key settings configured:**

| Setting | Default | Purpose |
|---------|---------|---------|
| `groq_api_key` | From `.env` | Authenticates with Groq LLM API |
| `llm_model` | `llama3-8b-8192` | Which AI model to use |
| `llm_temperature` | `0.7` | Creativity level (0=focused, 1=creative) |
| `embedding_model` | `all-MiniLM-L6-v2` | For converting text to vectors (RAG) |
| `cache_ttl_market_data` | `30s` | How long to cache stock prices |
| `default_market` | `NSE` | Default Indian stock exchange |

---

### Step 4: Prompt Engineering (`config/prompts.py`)

**What we did:**
- Defined the chatbot's **persona** (FinSight — expert financial assistant)
- Created **separate prompt templates** for each intent type using LangChain's `ChatPromptTemplate`
- Built a **prompt registry** to map intents → prompts

**Why:** Different queries need different system prompts. A market price query needs "present data clearly with change %" while an education query needs "be educational, use examples."

**Prompts we created:**

| Prompt | Used For | Key Instruction |
|--------|----------|-----------------|
| `MARKET_DATA_PROMPT` | Stock prices, trends | "Present price with change, sentiment" |
| `NEWS_SUMMARY_PROMPT` | News requests | "Lead with impactful headline, cite sources" |
| `TRADING_QA_PROMPT` | Trading how-to | "Be educational, include disclaimers" |
| `EDUCATION_PROMPT` | Concept explanations | "Start simple, use analogies" |
| `GENERAL_PROMPT` | Everything else | "Redirect to finance if off-topic" |

---

### Step 5: Intent Classification (`core/intent_classifier.py`)

**What we did:**
- Built a **hybrid intent classifier** using TWO methods:
  1. **Fast regex pattern matching** — for common, clear queries (high confidence)
  2. **LLM fallback** — for ambiguous queries that patterns can't handle

**Why:** Regex is instant and free (no API calls). LLM is smarter but costs time and tokens. Combining both = fast when possible, smart when needed.

**How it works:**
```
User: "What's the price of TCS?"
  │
  ├─ Step 1: Regex pattern match
  │    Pattern: r"(what|whats)\\s+(is\\s+)?(the\\s+)?(price|rate)"
  │    Match found! → MARKET_PRICE (confidence: 0.85) ✅
  │    Confidence ≥ 0.8, so we stop here
  │
  └─ Step 2: (skipped — pattern match was confident enough)
```

```
User: "Should I invest in IT stocks right now?"
  │
  ├─ Step 1: Regex pattern match → no strong match (confidence: 0.3)
  │
  └─ Step 2: LLM classification
       Sends query to Groq LLM with INTENT_CLASSIFICATION_PROMPT
       LLM returns: "GENERAL" (confidence: 0.75) ✅
```

**9 Intents we detect:**

| Intent | Example Triggers |
|--------|-----------------|
| `GREETING` | "hi", "hello", "bye", "thanks" |
| `MARKET_PRICE` | "price of TCS", "how much is Reliance" |
| `MARKET_TREND` | "how is Nifty today", "market sentiment" |
| `STOCK_INFO` | "tell me about TCS", "PE ratio of Infosys" |
| `TRADING_HOW_TO` | "how to buy stocks", "what is stop loss" |
| `NEWS_REQUEST` | "latest market news", "news about TCS" |
| `EDUCATION` | "explain candlestick", "what is P/E ratio" |
| `PORTFOLIO_QUERY` | "show my portfolio", "my returns" |
| `GENERAL` | Everything else |

---

### Step 6: Entity Extraction (`core/entity_extractor.py`)

**What we did:**
- Built a **regex-based entity extractor** that pulls out financial entities from natural language
- Used an **exclusion list** approach — instead of listing all valid stocks, we detect patterns that *look like* stock symbols and exclude common English words
- Extract: stock symbols, indices, time periods, order types, amounts, trading actions

**Why:** When a user says "What's the price of TCS today?", the system needs to know: **which stock** (TCS) and **when** (today).

**What it extracts:**

| Entity | Pattern | Example |
|--------|---------|---------|
| Stock symbols | Uppercase 2-15 chars, not in excluded list | "TCS", "RELIANCE", "HDFCBANK" |
| Indices | Match against known index names | "NIFTY", "SENSEX", "BANK NIFTY" |
| Time period | Regex for temporal words | "today", "last week", "YTD" |
| Order type | Match against known order types | "market order", "stop loss" |
| Amount | Currency patterns | "₹5000", "10 shares" |
| Action | Trading verbs | "buy", "sell", "hold" |

**The exclusion list trick:** Instead of maintaining a list of 2000+ valid NSE stocks (which changes!), we:
1. Find all uppercase words that *look like* stock symbols
2. Filter out common English words (`THE`, `AND`, `BUY`, `STOCK`, etc.)
3. Let the downstream `yfinance` API validate if the symbol actually exists

---

### Step 7: Conversation Memory (`core/conversation_memory.py`)

**What we did:**
- Built an **in-memory session manager** with LRU (Least Recently Used) eviction
- Each session stores: messages, last intent, last entities, last stock mentioned
- Sessions expire after 1 hour, max 1000 concurrent sessions

**Why:** Multi-turn conversations need context. If user asks "price of TCS" then follows with "what about its PE ratio?" — we need to remember TCS was the last stock mentioned.

**Key features:**
- **Session creation** — auto-generates UUID for new sessions
- **LRU eviction** — when memory is full, oldest unused sessions get deleted
- **Thread-safe** — uses `Lock` for concurrent access
- **Context tracking** — remembers last stock, last intent for follow-up questions

---

### Step 8: Market Data Service (`modules/market_data.py`)

**What we did:**
- Created a service that fetches **real-time stock prices** using the `yfinance` library
- Added **NSE/BSE symbol mapping** (TCS → TCS.NS for yfinance)
- Built **in-memory caching** (30-second TTL) to avoid hammering the API
- Added **simulation fallback** — returns random realistic data if yfinance is unavailable

**Why:** Users need live market data. yfinance is free and reliable for Indian stocks.

**What it provides:**

| Method | Returns | Cache TTL |
|--------|---------|-----------|
| `get_stock_price("TCS")` | Price, change, volume, high/low | 30 seconds |
| `get_index_data("NIFTY 50")` | Index value and change | 30 seconds |
| `get_stock_details("TCS")` | Sector, PE, EPS, 52-week range | 5 minutes |
| `get_market_summary()` | Nifty + Sensex + Bank Nifty | 30 seconds |

**Symbol conversion:**
```
User says: "TCS"  →  yfinance needs: "TCS.NS"  (NSE)
User says: "TCS"  →  yfinance needs: "TCS.BO"  (BSE)
User says: "NIFTY" →  yfinance needs: "^NSEI"  (Index)
```

---

### Step 9: News Service (`modules/news_service.py`)

**What we did:**
- Built a news fetcher using **Google News RSS feeds** (free, no API key needed!)
- Added stock-specific news search
- Created a **fallback with demo news** when RSS fails
- Added **5-minute caching** to avoid repeated requests

**Why:** Traders need financial news. RSS feeds from Google News are free and provide relevant results.

**How it works:**
```
General news → "https://news.google.com/rss/search?q=indian+stock+market"
Stock news  → "https://news.google.com/rss/search?q=TCS+stock+india"
```

**The `feedparser` library** parses the RSS XML into Python objects with title, summary, source, link, and published date.

---

### Step 10: Trading Knowledge Base (`modules/trading_assistant.py`)

**What we did:**
- Created a **built-in knowledge base** as a Python dictionary with 14 trading topics
- Built a **keyword search index** for fast topic matching
- Topics cover: order types, trading concepts, technical analysis, fundamentals, how-to guides

**Why:** For common trading questions, we don't need to call the LLM — we already have perfect answers ready. This is faster and more consistent.

**Topics in the knowledge base:**

| Category | Topics |
|----------|--------|
| **Order Types** | Market order, Limit order, Stop loss, Bracket order |
| **Trading** | Intraday, Delivery, Margin trading |
| **Technical Analysis** | Candlestick patterns, Moving averages, RSI |
| **Fundamentals** | P/E ratio, Market cap |
| **How-To** | How to buy stocks, How to sell stocks |

---

### Step 11: Response Formatting (`modules/market_formatter.py`)

**What we did:**
- Created a `MarketFormatter` class that converts raw data into **beautiful, emoji-rich responses**
- Formats prices with ₹ symbol, Indian number system (L = Lakh, Cr = Crore)
- Color-codes changes: 🟢 for up, 🔴 for down

**Why:** Raw data like `{"price": 3456.78, "change": 23.5}` is hard to read. Formatted output like:

```
📈 TCS (Tata Consultancy Services)
💰 Current Price: ₹3,456.78
🟢 Change: +₹23.50 (+0.68%)
📊 Day's Range: ₹3,430.00 - ₹3,470.00
```
...is much better for users!

---

### Step 12: Central Router (`core/router.py`)

**What we did:**
- Built the `ChatRouter` — the **central brain** that ties everything together
- On every message, it: classifies intent → extracts entities → routes to handler → formats response → returns
- Each intent has its own handler method

**Why:** The router is the **orchestrator pattern**. Each component does ONE thing well, and the router coordinates them.

**Routing logic:**

| Intent | Handler Method | What It Does |
|--------|---------------|--------------|
| `GREETING` | `_handle_greeting()` | Returns static greeting from dictionary |
| `MARKET_PRICE` | `_handle_market_price()` | Calls yfinance → format price |
| `MARKET_TREND` | `_handle_market_trend()` | Fetches index data for overview |
| `STOCK_INFO` | `_handle_stock_info()` | Fetches details + price |
| `TRADING_HOW_TO` | `_handle_trading_query()` | Searches knowledge base, fallback to LLM |
| `EDUCATION` | `_handle_trading_query()` | Same as above |
| `NEWS_REQUEST` | `_handle_news_request()` | Fetches RSS news |
| `PORTFOLIO_QUERY` | `_handle_portfolio_query()` | Placeholder message |
| `GENERAL` | `_handle_general_query()` | Calls Groq LLM directly |

---

### Step 13: FastAPI Server (`main.py`)

**What we did:**
- Created a **FastAPI application** with multiple endpoints
- Added **CORS middleware** so the frontend (React/Next.js) on `localhost:3000` can call our API
- Added a **WebSocket endpoint** for real-time chat
- Added **direct data endpoints** for stock prices, indices, and news

**Why:** FastAPI gives us: automatic API docs, request validation, async support, and WebSocket support — all out of the box.

**Endpoints we created:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Main chat endpoint |
| `POST` | `/v2/chat` | Chat with full request model |
| `WS` | `/ws/chat` | WebSocket for real-time chat |
| `GET` | `/market/{symbol}` | Direct stock price lookup |
| `GET` | `/index/{index_name}` | Direct index data |
| `GET` | `/news` | Get financial news |

---

### Step 14: RAG Chain (`rag_chain.py`)

**What we did:**
- Built a **Retrieval-Augmented Generation (RAG)** pipeline with:
  1. **JSONLoader** — loads greeting data from `greeting_data.json`
  2. **Text Splitter** — chunks documents into 500-char pieces
  3. **HuggingFace Embeddings** — converts text to vectors using `all-MiniLM-L6-v2`
  4. **FAISS Vector Store** — stores and searches vectors efficiently
  5. **Smart Router** — if query matches greeting data → return RAG result, else → call LLM

**Why:** RAG lets the chatbot answer from its **own knowledge base** instead of relying solely on the LLM. The LLM might hallucinate, but RAG retrieves exact data.

**The flow:**
```
User: "What can you do?"
  │
  ├─ Step 1: Convert query to vector (embedding)
  ├─ Step 2: Search FAISS for similar vectors
  ├─ Step 3: Found match in greeting_data.json!
  └─ Step 4: Return the stored response (no LLM needed)

User: "What is short selling?"
  │
  ├─ Step 1: Convert query to vector
  ├─ Step 2: Search FAISS — no good match
  └─ Step 3: Fallback to Groq LLM → generate answer
```

---

### Step 15: Caching Layer (`utils/cache.py`)

**What we did:**
- Built a **TTLCache** (Time-To-Live Cache) class
- Thread-safe with LRU eviction (least recently used items get deleted when full)
- Created decorator functions `@cache_with_ttl(ttl=60)` for easy caching

**Why:** Without caching, every "price of TCS" query would hit the yfinance API. With 30-second cache, repeated queries are instant.

---

### Step 16: Universal Stock Access & Historical Data (Upgrade)

> **This step documents a major upgrade to make the chatbot work with ALL stocks (Indian + US) and support historical movement queries.**

#### 🔴 Problem 1: Couldn't detect company names typed in lowercase

**The Issue:** If a user typed `"what is the price of tata steel"` or `"nvidia stock price"`, the entity extractor couldn't find any stock because it only detected uppercase patterns like `TCS` or `RELIANCE`.

**The Fix — Company Name Mapping** (`core/entity_extractor.py`):
- Added a `COMPANY_NAME_MAP` dictionary with **80+ entries** mapping natural company names to their symbols
- Added both **Indian stocks** (tata steel → TATASTEEL, hdfc bank → HDFCBANK, etc.) and **US stocks** (nvidia → NVDA, apple → AAPL, etc.)
- Updated `_extract_stocks()` to use a **dual strategy**:
  1. **First**: Scan for company name matches (case-insensitive, longest match first)
  2. **Then**: Fall back to the original uppercase pattern matching

```python
# Strategy 1: Company name matching (NEW)
for name in sorted(COMPANY_NAME_MAP.keys(), key=len, reverse=True):
    if name in query_lower:
        symbol = COMPANY_NAME_MAP[name]
        found_stocks.append(symbol)

# Strategy 2: Original uppercase pattern matching
words = re.findall(r'\b[A-Z][A-Z0-9&-]{1,14}\b', query.upper())
```

Also added movement-related words (`LAST`, `FIVE`, `MOVEMENT`, `HISTORY`, `DAYS`, etc.) to `EXCLUDED_WORDS` so they don't get falsely detected as stock symbols.

---

#### 🔴 Problem 2: US stocks didn't work (only NSE/BSE)

**The Issue:** The market data service always appended `.NS` (NSE suffix) to symbols. So `NVDA` became `NVDA.NS` which doesn't exist on yfinance, and the query failed.

**The Fix — Smart Market Detection** (`modules/market_data.py`):
- Added `_detect_market()` method that **tries NSE first, then US automatically**
- Updated `_get_yf_symbol()` to handle `market="US"` by returning the bare symbol
- Updated `get_stock_price()` to use smart detection when no market is specified

```python
def _detect_market(self, symbol):
    # Try NSE first (.NS suffix)
    ticker = yf.Ticker(f"{symbol}.NS")
    if ticker.info.get('currentPrice', 0) > 0:
        return f"{symbol}.NS", "NSE"   # ✅ Found on NSE
    
    # Try US market (bare symbol)
    ticker = yf.Ticker(symbol)
    if ticker.info.get('currentPrice', 0) > 0:
        return symbol, "US"            # ✅ Found on US market
    
    return f"{symbol}.NS", "NSE"       # Default fallback
```

The Market enum already had `US = "US"` in `schemas.py`, so no schema change was needed for this.

---

#### 🔴 Problem 3: No historical data support

**The Issue:** Users asking `"last 5 day movement of TCS"` or `"how did nvidia perform this week"` got no meaningful response because the chatbot had no historical data capability.

**The Fix — Across 7 files:**

**1. New data models** (`models/schemas.py`):
```python
class StockHistoryDay(BaseModel):   # One day's data
    date, open, high, low, close, volume, change_percent

class StockHistory(BaseModel):       # Multiple days
    symbol, name, days: List[StockHistoryDay],
    period, overall_change_percent, market
```
Also added `STOCK_HISTORY = "STOCK_HISTORY"` to the `Intent` enum.

**2. New intent patterns** (`core/intent_classifier.py`):
```python
Intent.STOCK_HISTORY: [
    r"(last|past)\s+(\d+|five|three|seven|ten)\s*(day|week|month)",
    r"(movement|performance|trend|history)\s+(of|for)\s+\w+",
    r"how\s+(has|did|does)\s+\w+\s+(perform|move|do|done)",
    r"\d+\s*day\s*(movement|trend|history|performance)",
]
```

**3. New `get_stock_history()` method** (`modules/market_data.py`):
- Uses `yf.Ticker().history(period="Xd")` to get last N days of OHLCV data
- Calculates day-over-day change percentages
- Computes overall change from first to last day
- Includes simulation fallback
- Cached for 60 seconds

**4. New handler** (`core/router.py`):
- `_handle_stock_history()` parses the number of days from the query
- Supports both digit-based (`"last 5 days"`) and word-based (`"last five days"`) parsing
- Supports weeks and months (`"last 2 weeks"` → 14 days)
- Falls back to context (last mentioned stock) if no stock specified

**5. New formatter** (`modules/market_formatter.py`):
```python
def format_stock_history(history: StockHistory) -> str:
    # Auto-selects ₹ or $ based on market
    # Shows day-by-day table with 🟢/🔴 indicators
    # Shows overall change at the bottom
```

**6. Updated prompt registry** (`config/prompts.py`):
- Added `STOCK_HISTORY` to `INTENT_CLASSIFICATION_PROMPT` for LLM fallback
- Added `"STOCK_HISTORY": MARKET_DATA_PROMPT` to `PROMPT_REGISTRY`

**Example output for `"last 5 day movement of tata steel"`:**
```
📊 Tata Steel Ltd (TATASTEEL) — Last 5 Trading Days

📅 Feb 06: ₹142.50  —
📅 Feb 07: ₹143.20  🟢 +0.49%
📅 Feb 08: ₹141.80  🔴 -0.98%
📅 Feb 10: ₹144.30  🟢 +1.76%
📅 Feb 11: ₹145.10  🟢 +0.55%

Overall Change: 🟢 +1.82% over 5 days

_Source: NSE via yfinance_
```

---

#### 🔴 Problem 4: Unknown company names still failed

**The Issue:** Even after adding 80+ entries to `COMPANY_NAME_MAP`, if someone typed a company name that wasn't in the map (e.g., `"price of indian railway finance"` or `"vedanta resources share price"`), no stock would be detected.

**The Fix — LLM-based Symbol Resolution** (`core/router.py` + `config/prompts.py`):
- Added a `SYMBOL_RESOLUTION_PROMPT` that asks the LLM: *"What is the stock ticker for this company?"*
- Added `_resolve_symbol_via_llm()` method in the router
- Wired it into **all 3 stock handlers** (`_handle_market_price`, `_handle_stock_info`, `_handle_stock_history`) as a fallback

**The 3-layer fallback chain for finding a stock symbol:**
```
User: "price of indian railway finance"
  │
  ├─ Layer 1: Entity Extractor (COMPANY_NAME_MAP)
  │    → No match found ❌
  │
  ├─ Layer 2: Context (last mentioned stock)
  │    → No previous stock ❌
  │
  └─ Layer 3: LLM Resolution (NEW!)
       → Asks Groq LLM: "What is the ticker for 'indian railway finance'?"
       → LLM returns: "IRFC" ✅
       → Proceeds to fetch IRFC price from yfinance
```

**The prompt in `config/prompts.py`:**
```python
SYMBOL_RESOLUTION_PROMPT = """Extract the stock ticker symbol from this query.
Rules:
- Return ONLY the stock exchange ticker symbol (e.g., TCS, IRFC, NVDA, AAPL)
- For Indian stocks, return the NSE symbol
- For US stocks, return the NASDAQ/NYSE symbol
- If no company/stock is mentioned, return UNKNOWN
- Return a single word only, no explanation

Query: {query}
Ticker:"""
```

**Why this approach:**
- **Covers ALL stocks** — the LLM knows company names globally
- **No maintenance needed** — no need to update lists when new stocks are listed
- **Small cost** — only called when entity extraction AND context both fail
- **Fast** — Groq's LLaMA 3 returns a single word in ~100ms

---

## 4. Technology Stack Explained

### Core Technologies

| Technology | What It Is | Why We Used It |
|------------|-----------|----------------|
| **Python 3.10+** | Programming language | Best for AI/ML, huge ecosystem |
| **FastAPI** | Web framework | Async, auto-docs, Pydantic integration |
| **Uvicorn** | ASGI server | Runs the FastAPI app |
| **Pydantic** | Data validation | Type-safe models, auto-validation |

### AI & NLP

| Technology | What It Is | Why We Used It |
|------------|-----------|----------------|
| **LangChain** | LLM framework | Chains, prompts, memory management |
| **Groq API** | LLM provider | Fast inference for LLaMA3 model |
| **LLaMA 3 (8B)** | AI model | Our chatbot's "brain" — generates responses |
| **HuggingFace Transformers** | ML library | Embedding models |
| **Sentence-Transformers** | Embedding models | `all-MiniLM-L6-v2` for text→vector |
| **FAISS** | Vector database | Fast similarity search for RAG |

### Data & APIs

| Technology | What It Is | Why We Used It |
|------------|-----------|----------------|
| **yfinance** | Stock data library | Free real-time NSE/BSE/US prices |
| **feedparser** | RSS parser | Parse Google News feeds |
| **aiohttp** | Async HTTP client | Non-blocking API calls |
| **python-dotenv** | Env loader | Load `.env` file variables |

### Caching & Utilities

| Technology | What It Is | Why We Used It |
|------------|-----------|----------------|
| **cachetools** | Caching library | Additional caching utilities |
| **OrderedDict** | Python built-in | LRU cache implementation |
| **threading.Lock** | Python built-in | Thread safety |
| **uuid** | Python built-in | Session ID generation |

---

## 5. File-by-File Breakdown

| File | Lines | Purpose | Key Concepts |
|------|-------|---------|-------------|
| `main.py` | 285 | FastAPI app, endpoints | Routes, CORS, WebSocket, lifespan |
| `rag_chain.py` | 82 | RAG pipeline | Embeddings, FAISS, document loading |
| `config/settings.py` | 72 | App configuration | Pydantic Settings, env vars, `@lru_cache` |
| `config/prompts.py` | 182 | LLM prompts | `ChatPromptTemplate`, persona design |
| `core/router.py` | 450+ | Central brain | Orchestrator pattern, intent routing, history handler |
| `core/intent_classifier.py` | 200+ | Intent detection | Regex patterns, LLM fallback, hybrid, STOCK_HISTORY |
| `core/entity_extractor.py` | 460+ | Entity extraction | Regex, exclusion lists, company name mapping |
| `core/conversation_memory.py` | 239 | Session memory | LRU, TTL, thread safety, `OrderedDict` |
| `modules/market_data.py` | 430+ | Live stock data | yfinance, smart market detection, history, simulation |
| `modules/news_service.py` | 280 | Financial news | RSS feeds, `feedparser`, caching |
| `modules/trading_assistant.py` | 401 | Trading knowledge | Keyword indexing, knowledge base |
| `modules/market_formatter.py` | 200+ | Response formatting | Emoji, Indian number system, history formatting |
| `models/schemas.py` | 240+ | Data models | Pydantic, Enums, StockHistory, validation |
| `utils/cache.py` | 163 | Caching | TTL cache, decorators, thread safety |
| `data/greeting_data.json` | 48 | Greeting responses | RAG source data |

---

## 6. How a Message Flows Through the System

Here's the complete journey of **"What's the price of TCS?"**:

```
1️⃣  User sends POST /chat with {"message": "What's the price of TCS?"}

2️⃣  main.py receives it → calls router.process_message()

3️⃣  Router gets/creates a session (ConversationMemory)
    → Session ID: "a1b2c3d4-..."

4️⃣  Intent Classifier runs:
    → Regex pattern matches: r"(what|whats)...price" → MARKET_PRICE ✅
    → Confidence: 0.85

5️⃣  Entity Extractor runs:
    → Finds "TCS" (uppercase, 3 chars, not in excluded words)
    → stock_symbols: ["TCS"], indices: [], time_period: None

6️⃣  Router updates session context:
    → intent: MARKET_PRICE, last_stock: "TCS"

7️⃣  Routes to _handle_market_price():
    → Calls market_service.get_stock_price("TCS")
    → Smart detection: tries TCS.NS → found on NSE ✅
    → Returns StockPrice object

8️⃣  MarketFormatter formats the response:
    → "📈 Tata Consultancy Services (TCS)
        💰 Current Price: ₹3,456.78
        🟢 Change: +₹23.50 (+0.68%)"

9️⃣  Router generates follow-up suggestions:
    → ["Tell me more about TCS", "What's the news for TCS?", ...]

🔟  Returns ChatResponse:
    {
      "reply": "📈 Tata Consultancy Services...",
      "intent": "MARKET_PRICE",
      "entities": {"stock_symbols": ["TCS"], ...},
      "suggestions": ["Tell me more about TCS", ...],
      "session_id": "a1b2c3d4-..."
    }
```

### How `"last 5 day movement of nvidia"` Flows:

```
1️⃣  User sends: "last 5 day movement of nvidia"

2️⃣  Intent Classifier:
    → Pattern: r"(last|past)\s+(\d+)\s*day" matches → STOCK_HISTORY ✅

3️⃣  Entity Extractor:
    → Company name match: "nvidia" → NVDA (from COMPANY_NAME_MAP) ✅
    → "LAST", "FIVE", "MOVEMENT", "DAYS" filtered by EXCLUDED_WORDS

4️⃣  Router → _handle_stock_history():
    → Parses "5" from query
    → Calls market_service.get_stock_history("NVDA", 5)

5️⃣  Market Data Service:
    → _detect_market("NVDA")
    → Tries NVDA.NS → no valid price
    → Tries NVDA (bare) → found on US market ✅
    → yf.Ticker("NVDA").history(period="10d").tail(5)

6️⃣  MarketFormatter.format_stock_history():
    → Currency: $ (US market detected)
    → Day-by-day table with 🟢/🔴 indicators

7️⃣  Returns formatted history response
```

---

## 7. Key Concepts You Learned

### Design Patterns Used

| Pattern | Where | What It Does |
|---------|-------|--------------|
| **Singleton** | Every service (`_router = None; get_chat_router()`) | One instance shared everywhere |
| **Router/Handler** | `core/router.py` | Route requests to correct handler |
| **Service Layer** | `modules/` directory | Business logic separated from API |
| **Registry** | `PROMPT_REGISTRY` in prompts.py | Map keys to values dynamically |
| **Strategy** | Intent → Handler mapping | Different behavior based on intent |
| **Decorator** | `@cache_with_ttl()` | Add caching without modifying functions |
| **Fallback Chain** | `_detect_market()` in market_data.py | Try NSE → Try US → Default |

### Programming Concepts Applied

| Concept | Where You Used It |
|---------|-------------------|
| **Async/Await** | All service methods, FastAPI endpoints |
| **Regex** | Intent patterns, entity extraction |
| **Enums** | `Intent`, `Market` in schemas |
| **Dataclasses** | `ExtractedEntities` |
| **Type Hints** | Every function signature |
| **Pydantic Models** | All request/response schemas |
| **LRU Cache** | Settings singleton, TTLCache |
| **Thread Safety** | `Lock` in cache and memory |
| **Error Handling** | Try/except with fallbacks everywhere |
| **Logging** | `logging.getLogger(__name__)` |
| **Dictionary-based Lookup** | `COMPANY_NAME_MAP` for name→symbol resolution |

---

## 8. Quick Reference Cheat Sheet

### How to Run
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
# Make sure .env has: GROQ_API_KEY=your_key_here

# Run the server
python main.py
# or
uvicorn main:app --reload --port 8000
```

### How to Test
```bash
# Health check
curl http://localhost:8000/health

# Chat — Indian stock by name
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the price of tata steel?"}'

# Chat — US stock
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "nvidia stock price"}'

# Chat — Historical movement
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "last 5 day movement of TCS"}'

# Direct stock price
curl http://localhost:8000/market/TCS

# News
curl http://localhost:8000/news
```

### Key Files to Study First
1. `models/schemas.py` — Understand the data structures
2. `config/settings.py` — See how config works
3. `core/intent_classifier.py` — Learn regex + LLM hybrid
4. `core/entity_extractor.py` — Learn entity extraction + company name mapping
5. `core/router.py` — See how everything connects
6. `main.py` — See how FastAPI serves it all

---

> 💡 **Tip:** When in doubt about how something works, trace a real query through the system starting from `main.py` → `router.py` → the specific handler. Follow the code flow!

---

*Document generated on 2026-02-11 for the FinSight Chatbot project. Updated with universal stock access & historical data support.*

