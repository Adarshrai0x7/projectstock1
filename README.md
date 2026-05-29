# 📊 FBOT — AI-Powered Financial Assistant

An intelligent financial assistant that combines **real-time market data, technical analysis, fundamental analysis, news intelligence, stock screening, and Retrieval-Augmented Generation (RAG)** into a single conversational interface.

Built using **LangGraph, FastAPI, Streamlit, Groq LLMs, FAISS, and financial data services**, FBot enables users to analyze Indian stocks, explore market trends, screen opportunities, and learn trading concepts through natural language conversations.

## 🚀 Highlights

* 📈 Real-time stock prices and market index tracking
* 🔬 Technical analysis (RSI, MACD, Bollinger Bands, Supertrend, ADX, VWAP)
* 📊 Fundamental analysis using Screener.in data
* 📰 AI-powered financial news with sentiment analysis
* 🔍 Stock screening engine with custom filters
* 🧠 Retrieval-Augmented Generation (RAG) using FAISS and Sentence Transformers
* 📚 Trading education and financial concept explanations
* ⚡ Streaming responses via SSE and WebSockets
* 💾 Persistent conversation memory using LangGraph checkpoints
* 🌐 REST API + Interactive Chat Interface

## 🏗 System Architecture

```text
User
 │
 ▼
Streamlit Frontend
 │
 ▼
FastAPI Backend
 │
 ▼
LangGraph ReAct Agent
 │
 ├── Market Data (yfinance)
 ├── Technical Analysis Engine
 ├── Fundamental Analysis (Screener.in)
 ├── News Intelligence
 ├── RAG Knowledge Base (FAISS)
 ├── Wikipedia Search
 └── Tavily Web Search
```

## 🛠 Tech Stack

### AI & Agent Framework

* LangGraph
* LangChain
* Groq (LLaMA 3.3 70B)
* Google Gemini (Fallback)

### Backend

* FastAPI
* Uvicorn
* Pydantic
* SlowAPI
* SQLite

### Frontend

* Streamlit

### Data & Analytics

* yfinance
* Screener.in
* pandas
* numpy
* pandas-ta

### Knowledge & Search

* FAISS
* Sentence Transformers
* Wikipedia API
* Tavily Search

## ✨ Key Features

| Feature              | Capability                                 |
| -------------------- | ------------------------------------------ |
| Stock Prices         | Live NSE/BSE stock data                    |
| Market Overview      | NIFTY, SENSEX, Bank NIFTY                  |
| Technical Analysis   | 12+ indicators                             |
| Fundamental Analysis | PE, PB, ROE, ROCE, D/E                     |
| News Intelligence    | Sentiment-based news summaries             |
| Stock Screener       | Momentum, Value, Dividend & Custom Screens |
| RAG Search           | Knowledge base retrieval                   |
| Trading Education    | Financial concepts and strategies          |
| Streaming            | SSE & WebSocket support                    |

## 🚀 Deployment

```bash
# Backend
uvicorn main:app --reload

# Frontend
streamlit run streamlit_app.py
```

## 🔮 Future Enhancements

* Portfolio Analytics
* Watchlists & Alerts
* AI Trade Journal
* Predictive Forecasting Models
* Multi-Agent Financial Research System

---

Built using LangGraph, FastAPI, Streamlit, and LLMs.
