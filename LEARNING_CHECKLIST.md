# 📚 Finance Chatbot - Learning Checklist

Track your progress by checking off topics as you learn them.

---

## Level 1: Python Foundations
- [ ] Python basics (variables, functions, classes, loops)
- [ ] Object-Oriented Programming (classes, inheritance, `@dataclass`)
- [ ] Type hints (`typing` module: `List`, `Dict`, `Optional`)
- [ ] Async/Await programming (`async def`, `await`, `asyncio`)
- [ ] Exception handling (`try/except`)
- [ ] Regular Expressions (`re` module)

---

## Level 2: Web Development (FastAPI)
- [ ] FastAPI basics - creating routes (`@app.get`, `@app.post`)
- [ ] Pydantic models for request/response validation
- [ ] Dependency injection
- [ ] CORS middleware
- [ ] REST API concepts (GET, POST, JSON, status codes)
- [ ] WebSockets for real-time communication
- [ ] Environment variables (`.env`, `python-dotenv`)

---

## Level 3: AI/LLM & NLU
- [ ] LangChain basics (prompt templates, chains)
- [ ] LLM APIs (Groq, OpenAI)
- [ ] RAG (Retrieval Augmented Generation)
- [ ] Vector stores (ChromaDB, FAISS)
- [ ] Embeddings and semantic search
- [ ] Intent Classification
- [ ] Entity Extraction (regex + NLP)

---

## Level 4: Domain Knowledge (Finance)
- [ ] Stock symbols (NSE/BSE)
- [ ] Market indices (NIFTY, SENSEX, BANKNIFTY)
- [ ] Order types (market, limit, stop-loss, GTT)
- [ ] Financial APIs (`yfinance`)
- [ ] News APIs integration

---

## Level 5: Software Design
- [ ] Singleton Pattern
- [ ] Router/Handler Pattern
- [ ] Service Layer Pattern
- [ ] Caching (in-memory with TTL)
- [ ] Configuration Management (Pydantic settings)
- [ ] Modular code organization

---

## 🎯 Weekly Learning Plan

| Week | Focus | Build |
|------|-------|-------|
| 1 | Python + async | Practice scripts |
| 2 | FastAPI | Simple REST API |
| 3 | LangChain + LLM | Basic chat endpoint |
| 4 | Entity extraction | NLU module |
| 5 | External APIs | Market data service |
| 6 | Integration | Complete chatbot |

---

## 📖 Resources

| Topic | Resource |
|-------|----------|
| FastAPI | https://fastapi.tiangolo.com |
| LangChain | https://python.langchain.com |
| yfinance | https://pypi.org/project/yfinance |
| Regex Practice | https://regex101.com |
| Async Python | https://realpython.com/async-io-python |

---

## 📂 Project Files to Study

| File | Learn About |
|------|-------------|
| `main.py` | FastAPI app structure |
| `core/router.py` | Intent routing pattern |
| `core/entity_extractor.py` | Regex, pattern matching |
| `core/intent_classifier.py` | LLM-based classification |
| `modules/market_data.py` | External API integration |
| `config/settings.py` | Pydantic settings |
