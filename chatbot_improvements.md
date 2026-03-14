# FinSight Chatbot — Improvement Roadmap

A prioritized list of improvements to make the chatbot more accurate and helpful, based on a full code review.

---

## 🔴 HIGH IMPACT — Accuracy Killers

### 1. Intent Classifier: Too Many Ambiguous Classes → Wrong Routing

**Problem**: `STOCK_INFO` vs `STOCK_SCREEN` vs `MARKET_TREND` vs `STOCK_HISTORY` all overlap heavily. A query like _"analyze Reliance"_ gets close similarity scores across multiple intents. The current geometric-mean confidence formula penalises valid queries, pushing them into the LLM fallback unnecessarily.

**Current code**: [intent_classifier.py](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/intent_classifier.py) → [_embedding_classify()](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/intent_classifier.py#363-416) — confidence = [(vote_fraction * avg_sim) ** 0.5](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/entity_extractor.py#276-286)

**Fix**:
- Raise `CONFIDENCE_THRESHOLD` from `0.45` → `0.55` and use **weighted voting** (similarity-weighted, not count-weighted)
- Add 10–15 more diverse examples to the most-confused pairs (`STOCK_SCREEN` / `STOCK_INFO`, `MARKET_TREND` / `STOCK_HISTORY`)
- Inject **conversation context** into classification: if the last intent was `MARKET_PRICE` and user says "how did it do last week", force `STOCK_HISTORY`

---

### 2. Entity Extractor: Greedy Uppercase Matching Causes False Positives

**Problem**: [_extract_stocks()](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/entity_extractor.py#345-389) in [entity_extractor.py](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/entity_extractor.py) pattern-matches ANY uppercase word ≥ 2 chars that isn't in `EXCLUDED_WORDS`. Words like `"EXPLAIN"`, `"BEST"`, `"PE"` often slip through because `EXCLUDED_WORDS` is incomplete and the API validation failure happens silently downstream. Result: the router picks a garbage symbol and returns "stock not found" instead of answering correctly.

**Fix**:
- **Whitelist mode first**: check `COMPANY_NAME_MAP` and a curated top-500 NSE/BSE symbol list before doing open-ended uppercase scanning
- Only fall back to open-ended scan if no whitelist match is found, and mark those as "low-confidence symbols" needing API validation *before* routing
- Add `"EXPLAIN", "PERFORM", "ANALYSE", "ANALYSIS", "WHEN", "THEN", "THEM"` to `EXCLUDED_WORDS`

---

### 3. Chat History NOT Passed to LLM in Most Handlers

**Problem**: [_handle_trading_query](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py#381-407), [_handle_market_trend](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py#276-346), [_handle_stock_info](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py#347-380), and [_handle_news_request](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py#478-494) all call the LLM with `chat_history: []`. Only [_handle_general_query()](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py#564-587) actually passes history. This means the LLM cannot answer follow-up questions like _"can you elaborate?"_ or _"why?"_ correctly — it has no memory of what was just said.

**Fix**: In [router.py](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py), pass the last 4–6 messages from `self.memory.get_chat_history(context.session_id, limit=6)` to **every** LLM handler that uses `chain.invoke(...)`.

---

## 🟠 MEDIUM IMPACT — Answer Quality

### 4. LLM Prompts Are Too Generic — No Persona Specialization Per Intent

**Problem**: `PROMPT_REGISTRY` in [prompts.py](file:///c:/Users/adars/OneDrive/Desktop/project1/common/config/prompts.py) maps 5 different intents (`MARKET_PRICE`, `MARKET_TREND`, `STOCK_INFO`, `STOCK_HISTORY`, `STOCK_SCREEN`) all to the **same** `MARKET_DATA_PROMPT`. Each intent needs different framing for quality answers.

**Fix**: Create separate prompt templates for `STOCK_INFO` (focus on fundamentals + company background), `STOCK_HISTORY` (focus on trend summary + risk), and `STOCK_SCREEN` (focus on screening criteria + actionable picks).

---

### 5. No Spell Check / Fuzzy Match for Company Names

**Problem**: A user typing _"reliace"_, _"infossys"_, or _"tata moters"_ gets no stock back because `COMPANY_NAME_MAP` is exact-match only. The LLM symbol resolution fallback ([_resolve_symbol_via_llm](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py#207-235)) does work but adds 1–2 second latency for every typo.

**Fix**: Add **rapidfuzz** (fast, pure Python) fuzzy matching against `COMPANY_NAME_MAP` keys with a similarity cutoff of 85%. This resolves most typos instantly without an LLM call.

```python
from rapidfuzz import process
match, score, _ = process.extractOne(query_lower, COMPANY_NAME_MAP.keys())
if score >= 85:
    symbol = COMPANY_NAME_MAP[match]
```

---

### 6. Conversation Memory Does Not Store Topic / Sector Context

**Problem**: `ConversationContext` stores only `last_stock_mentioned`. If a user asks about "IT sector stocks" and then says "which one has the best PE?", there's no sector context to use. The router answers generically.

**Fix**: Extend `ConversationContext` with `last_sector`, `last_intent_category`, and `last_news_topic` fields. Update `_update_context()` in the router to populate them using simple keyword extraction.

---

### 7. Pre-Classifier Guard is Fragile Regex

**Problem**: [_is_news_explanation_request()](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py#408-426) in [router.py](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py) uses ~8 regex patterns. It can fail on slight rephrasings like _"tell me what this article is about"_ or _"break this down for me"_, routing the query to the wrong handler entirely.

**Fix**: Replace the hard-coded regex list with a small dedicated **embedding similarity** check against ~10 canonical "explain this news" phrases using the same FAISS index already loaded. Reuse the existing classifier infrastructure.

---

## 🟡 LOWER IMPACT — Polish & Robustness

### 8. Follow-Up Suggestions Are Static — Not Context-Aware

**Problem**: [_get_suggestions()](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py#650-696) in [router.py](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/router.py) returns hard-coded suggestions per intent, not personalised to what was actually discussed. After asking about Reliance's news, the suggestions are generic market questions.

**Fix**: Make suggestions dynamic — include the last-mentioned stock and last-mentioned topic. E.g., after a news query for Reliance: `["What is the current price of Reliance?", "Analyze Reliance", "Explain this news in detail"]`.

---

### 9. Session TTL is 1 Hour — Kills Context in Long Sessions

**Problem**: [ConversationMemory](file:///c:/Users/adars/OneDrive/Desktop/project1/chatbot/core/conversation_memory.py#15-228) defaults to `session_ttl_hours=1`. If a user pauses for an hour (common in trading — they check back after market close), all context is lost and the next message starts fresh.

**Fix**: Extend TTL to `session_ttl_hours=8` (a full trading day). Also add a `last_topic_summary` string field to `ConversationContext` that compresses the last 3 turns into a short summary for low-memory sessions.

---

## Implementation Priority

| Priority | Improvement | Effort | Impact |
|----------|-------------|--------|--------|
| 1 | Chat history in all LLM handlers (#3) | Low | 🔴 High |
| 2 | Entity extractor false positives (#2) | Medium | 🔴 High |
| 3 | Fuzzy company name matching (#5) | Low | 🟠 Medium |
| 4 | Weighted intent voting + more examples (#1) | Medium | 🟠 Medium |
| 5 | Per-intent LLM prompts (#4) | Medium | 🟠 Medium |
| 6 | Dynamic follow-up suggestions (#8) | Low | 🟡 Low |
| 7 | Conversation context: sector/topic (#6) | Medium | 🟡 Low |
| 8 | Session TTL + topic summary (#9) | Low | 🟡 Low |
| 9 | Embedding-based news guard (#7) | High | 🟡 Low |

---

> **Want me to implement any of these?** Start with #3 (chat history) and #5 (fuzzy matching) — together they take ~30 minutes to implement and will noticeably improve answer quality immediately.
