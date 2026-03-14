"""
Semantic Intent Classifier for the Finance Chatbot.
Uses sentence-transformers embeddings + FAISS top-K voting instead of fragile regex patterns.
Falls back to LLM classification for low-confidence queries.
"""

import logging
import numpy as np
from typing import Optional, Tuple, List, Dict

from common.models.schemas import Intent

logger = logging.getLogger(__name__)


# ============================================================================
# INTENT EXAMPLE UTTERANCES
# Each intent has 15-20 diverse example phrases that semantically define it.
# More varied  = better generalisation at inference time.
# ============================================================================

INTENT_EXAMPLES: Dict[Intent, List[str]] = {

    Intent.GREETING: [
        "hi", "hello", "hey", "hola", "namaste",
        "good morning", "good afternoon", "good evening", "good night",
        "hey there", "hi there", "hello bot", "howdy",
        "thanks", "thank you", "bye", "goodbye", "see you later",
        "how are you", "how are you doing", "what's up",
    ],

    Intent.MARKET_PRICE: [
        "what is the price of TCS",
        "what is the current price of Reliance",
        "TCS stock price",
        "HDFC share price today",
        "how much is Infosys trading at",
        "price of BHEL",
        "current market price of ICICI bank",
        "what is TCS worth right now",
        "LTP of Wipro",
        "CMP of Nifty 50",
        "tell me the price of Tata Motors",
        "Reliance share rate",
        "show me the price for ONGC",
        "how much does TCS cost",
        "what's the price of SBI stock",
        "price check HDFC bank",
        "quote for INFY",
        # Additional: stock + 'today' price queries (to avoid STOCK_HISTORY bleed)
        "Wipro share price today",
        "Reliance price today",
        "SBI stock price today",
        "Infosys current price today",
        "what is ONGC price today",
        "ICICI bank share price today",
        "current price of TCS today",
        "tell me the current price of Wipro",
        "live price of HDFCBANK",
        "real time price of Tata Motors",
        "today price of Maruti",
        "Nifty index price right now",
    ],

    Intent.MARKET_TREND: [
        "how is the market today",
        "how is Nifty doing today",
        "how is Sensex performing",
        "is the market up or down today",
        "market trend today",
        "what is the market doing today",
        "how are markets performing",
        "is Nifty bullish or bearish",
        "market sentiment today",
        "what's happening in the market",
        "top gainers today",
        "top losers today",
        "best performing stocks today",
        "worst performing stocks today",
        "why is the market falling",
        "why is Nifty going down",
        "market outlook today",
        "NSE market summary",
        "BSE today performance",
        "what is going on with the market",
    ],

    Intent.STOCK_INFO: [
        "tell me about TCS",
        "give me details about Infosys",
        "what is Wipro company",
        "information about HDFC Bank stock",
        "stock profile of Infosys",
        "company details for Wipro",
        "PE ratio of TCS",
        "PE ratio of Reliance",
        "PE ratio of HDFC bank",
        "EPS of Tata Motors",
        "market cap of HDFC",
        "dividend yield of Coal India",
        "what sector is ONGC in",
        "tell me about BHEL company",
        "show info on ICICI bank",
        "Infosys stock overview",
        "who is Wipro",
        "price to earnings ratio of Infosys",
        "what is the PE of HDFC bank",
        "book value of Tata Motors",
        "debt to equity ratio of ONGC",
        "ROE of Wipro",
        "company info for SBI",
        "background of Tata Steel Industries",
        "overview of Infosys stock",
        "what does ONGC do",
        # Additional examples to distinguish from STOCK_SCREEN
        "tell me about TCS company",
        "tell me about Reliance company",
        "give me info about HDFC bank",
        "what is the PE ratio of Reliance",
        "PE ratio of Reliance Industries",
        "fundamentals of TCS",
        "stock details of Infosys",
        "company profile of Wipro",
        "what is TCS market cap",
        "HDFC bank fundamentals",
        "give me the EPS of Reliance",
        "show me the ROE of TCS",
    ],

    Intent.STOCK_HISTORY: [
        "last 5 days of TCS",
        "show me 10 day movement of Reliance",
        "HDFC stock performance last week",
        "how has Infosys done this month",
        "historical data for Wipro",
        "price movement of BHEL last 7 days",
        "weekly trend of Nifty",
        "monthly chart for TCS",
        "past 30 days of Tata Motors",
        "how did ONGC perform last month",
        "last few days HDFC bank movement",
        "stock history for Reliance",
        "show price over last 5 days for SBI",
        "how will TCS perform next week",
        "forecast for Reliance",
        "predict HDFC stock movement",
        "what will happen to Infosys next month",
        "TCS price last 5 days",
        "5 day chart of Infosys",
        "trend for Wipro over last month",
        "how has BHEL moved this week",
        "last week performance of SBI",
        "show me 1 month chart of Nifty",
        # Additional examples to fix 'how has X performed this month' ambiguity
        "how has TCS performed this month",
        "how has Reliance performed this week",
        "how has Wipro performed this year",
        "how did TCS perform last week",
        "how did HDFC perform this month",
        "TCS performance this month",
        "Reliance performance last 30 days",
        "Infosys monthly performance",
        "how has Nifty performed this week",
        "HDFC stock movement this month",
    ],

    Intent.TRADING_HOW_TO: [
        "how do I place a market order",
        "how to buy a stock",
        "how to sell shares",
        "how to place a limit order",
        "steps to place a stop loss",
        "how do I set a bracket order",
        "what is a limit order and how to place it",
        "how to trade intraday",
        "how to do delivery trading",
        "guide to placing your first trade",
        "how to use margin in trading",
        "how to set stop loss",
        "what is the process to buy reliance stock",
        "how do I sell my holdings",
        "steps to create a trading account",
        "how to do F&O trading",
    ],

    Intent.PORTFOLIO_QUERY: [
        "show me my portfolio",
        "how is my portfolio doing",
        "my holdings",
        "what are my investments",
        "portfolio performance today",
        "my portfolio returns",
        "what stocks do I hold",
        "how much am I up today",
        "how much am I down",
        "my profit and loss",
        "total value of my portfolio",
        "how has my portfolio performed this month",
        "my investment returns",
        "show my positions",
        "what is my P&L",
    ],

    Intent.NEWS_REQUEST: [
        "latest market news",
        "today's financial news",
        "breaking stock market news",
        "news for Reliance",
        "what's the latest news for TCS",
        "show me news about HDFC bank",
        "market news today",
        "stock news for Infosys",
        "any updates on BHEL",
        "financial news headlines",
        "what is happening with Tata Motors in the news",
        "recent news for Nifty",
        "news update for ONGC",
        "give me stock market updates",
        "latest updates on Indian market",
        "news about IT sector stocks",
        "tell me about recent news",
        # Stock-specific news patterns (fix: these were matching STOCK_HISTORY)
        "latest news for reliance",
        "news for TCS today",
        "any news on HDFC bank",
        "show me news about infosys",
        "what news is there for Wipro",
        "today's news for Tata Motors",
        "news headlines for Nifty 50",
        "Reliance news today",
        "TCS latest news",
        "stock news updates for ICICI",
    ],

    Intent.EDUCATION: [
        "what is intraday trading",
        "explain stop loss",
        "what is a limit order",
        "what does PE ratio mean",
        "explain RSI indicator",
        "what is MACD",
        "difference between delivery and intraday",
        "what is margin trading",
        "explain candlestick patterns",
        "what is a moving average",
        "teach me about fundamental analysis",
        "what is technical analysis",
        "what is a bull market",
        "what is a bear market",
        "what is leverage in trading",
        "what is short selling",
        "explain circuit breaker in stock market",
        "what is upper circuit and lower circuit",
        "how does options trading work",
        "what is futures trading",
        # Additional indicator/concept examples (fix: RSI indicator → EDUCATION)
        "what is RSI indicator",
        "what is RSI",
        "explain the RSI",
        "what is the MACD indicator",
        "what is Bollinger Bands",
        "explain EMA and SMA",
        "what is volume weighted average price",
        "what is VWAP",
        "what does the Stochastic indicator mean",
        "explain moving average convergence divergence",
        "how to read candlesticks",
        "what is OBV indicator",
        "explain ATR in trading",
        "what is ADX indicator",
    ],

    Intent.STOCK_SCREEN: [
        "show me undervalued stocks",
        "find momentum stocks",
        "screen for oversold stocks",
        "high dividend yield stocks",
        "stocks with strong fundamentals",
        "screen for low PE stocks",
        "show me stocks with high ROE",
        "filter stocks with RSI below 30",
        "top value stocks right now",
        "analyze TCS stock",
        "analyze Reliance",
        "analyze Infosys",
        "run analysis on HDFC",
        "full stock analysis of Reliance",
        "technical analysis of Reliance",
        "fundamental analysis of HDFC",
        "give me full analysis of Infosys",
        "best stocks to buy today",
        "stocks in uptrend",
        "bullish stocks right now",
        "quality growth stocks NSE",
        "screen stocks by RSI",
        "do a technical analysis of TCS",
        "run a full stock analysis for BHEL",
        "show stock screener results",
        "screener for Reliance",
        "stock screener Reliance Industries",
    ],

    Intent.GENERAL: [
        "what can you do",
        "help me",
        "what are your features",
        "how can you help me",
        "I need some advice",
        "can you help me with trading",
        "what markets do you cover",
        "tell me something interesting",
        "what is the best stock to buy",
        "should I invest in TCS",
        "is now a good time to invest",
        "what do you think about the market",
        "give me some stock tips",
        "any investment ideas",
    ],
}


# ============================================================================
# EMBEDDING INTENT CLASSIFIER
# ============================================================================

class EmbeddingIntentClassifier:
    """
    Semantic intent classifier using sentence-transformers + FAISS.

    At startup:
      - Loads all-MiniLM-L6-v2 (22 MB, CPU-fast, 384-dim)
        ↳ Upgrade to 'all-mpnet-base-v2' (420 MB, 768-dim) for ~5% better accuracy
      - Embeds all INTENT_EXAMPLES and builds a FAISS cosine-similarity index

    At classify() time:
      - Normalises the query (strip, collapse whitespace)
      - Top-K nearest neighbour search (k=adaptive)
      - SIMILARITY-WEIGHTED vote among top-K → intent + confidence
      - Falls back to LLM if confidence < threshold
    """

    # ── Model ──────────────────────────────────────────────────────────────
    MODEL_NAME = "all-MiniLM-L6-v2"          # fast, good quality
    # MODEL_NAME = "all-mpnet-base-v2"        # slower, better quality (~5% ↑)

    # ── Search ─────────────────────────────────────────────────────────────
    TOP_K = 9          # retrieve 9 neighbours; winner needs clear margin
    MIN_K = 5          # floor when index is small

    # ── Decision boundary ──────────────────────────────────────────────────
    CONFIDENCE_THRESHOLD = 0.52   # below this → LLM fallback
    #   Rationale: weighted-vote confidence is more honest than the old
    #   geometric-mean formula, so 0.52 is a stricter gate than the old 0.45.

    def __init__(self, llm=None):
        self.llm = llm
        self._index = None
        self._labels: List[Intent] = []
        self._model = None
        self._build_index()

    # ------------------------------------------------------------------
    # Index construction
    # ------------------------------------------------------------------

    def _build_index(self):
        """Load model and build FAISS index from INTENT_EXAMPLES."""
        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            logger.info(f"Loading embedding model: {self.MODEL_NAME}")
            self._model = SentenceTransformer(self.MODEL_NAME)

            texts, labels = [], []
            for intent, examples in INTENT_EXAMPLES.items():
                for ex in examples:
                    texts.append(ex)
                    labels.append(intent)

            self._labels = labels

            logger.info(f"Embedding {len(texts)} intent examples...")
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=64,
            ).astype("float32")

            dim = embeddings.shape[1]
            self._index = faiss.IndexFlatIP(dim)
            self._index.add(embeddings)

            logger.info(
                f"✅ Embedding classifier ready — "
                f"{len(texts)} examples, dim={dim}, "
                f"intents={len(INTENT_EXAMPLES)}"
            )

        except ImportError as e:
            logger.error(f"Missing dependency for embedding classifier: {e}")
            logger.warning("Falling back to LLM-only classification.")
        except Exception as e:
            logger.error(f"Failed to build embedding index: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, query: str) -> Tuple[Intent, float]:
        """
        Classify query intent.
        Returns (Intent, confidence) where confidence ∈ [0, 1].
        """
        # FIX 6: normalise query before any processing
        query = self._normalise(query)

        if self._index is not None:
            intent, confidence = self._embedding_classify(query)
            if confidence >= self.CONFIDENCE_THRESHOLD:
                return intent, confidence
            logger.debug(
                f"Low confidence {confidence:.3f} for '{query}' "
                f"({intent.value}) → trying LLM fallback"
            )

        if self.llm:
            return self._llm_classify(query)

        return Intent.GENERAL, 0.4

    # ------------------------------------------------------------------
    # Internal: query normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(text: str) -> str:
        """Strip, collapse internal whitespace, lowercase for scoring."""
        import re
        return re.sub(r'\s+', ' ', text.strip())

    # ------------------------------------------------------------------
    # Internal: similarity-weighted embedding classification
    # ------------------------------------------------------------------

    def _embedding_classify(self, query: str) -> Tuple[Intent, float]:
        """Embed query → FAISS search → similarity-weighted vote."""
        try:
            query_vec = self._model.encode(
                [query],
                normalize_embeddings=True,
                show_progress_bar=False,
            ).astype("float32")

            # FIX 3: adaptive k — don't over-sample small indexes
            k = max(self.MIN_K, min(self.TOP_K, len(self._labels)))
            similarities, indices = self._index.search(query_vec, k)

            similarities = similarities[0]   # shape (k,)
            indices = indices[0]             # shape (k,)

            # FIX 1: similarity-weighted voting
            # Each neighbour contributes its cosine similarity as its vote
            # weight, not a flat 1. A neighbour at sim=0.95 counts ~2× more
            # than one at sim=0.50.
            weighted_scores: Dict[Intent, float] = {}
            top_sim_per_intent: Dict[Intent, float] = {}
            total_weight = 0.0

            for sim, idx in zip(similarities, indices):
                if idx < 0 or sim <= 0:
                    continue
                intent = self._labels[idx]
                w = float(sim)              # weight = cosine similarity
                weighted_scores[intent] = weighted_scores.get(intent, 0.0) + w
                if w > top_sim_per_intent.get(intent, 0.0):
                    top_sim_per_intent[intent] = w
                total_weight += w

            if not weighted_scores or total_weight == 0:
                return Intent.GENERAL, 0.0

            # Winner = highest total weighted score
            winner = max(weighted_scores, key=lambda i: weighted_scores[i])

            # FIX 2: honest confidence formula
            #   weighted_vote_share: how dominant is the winner among all k weights
            #   top1_sim: best single match for the winner (signal strength)
            #   combined: their geometric mean → clear signal + dominance both needed
            weighted_vote_share = weighted_scores[winner] / total_weight
            top1_sim = top_sim_per_intent[winner]
            confidence = float((weighted_vote_share * top1_sim) ** 0.5)

            logger.debug(
                f"Embedding classify: '{query}' → {winner.value} "
                f"(w_share={weighted_vote_share:.3f}, top1_sim={top1_sim:.3f}, "
                f"conf={confidence:.3f})"
            )
            return winner, confidence

        except Exception as e:
            logger.error(f"Embedding classification error: {e}")
            return Intent.GENERAL, 0.0

    # ------------------------------------------------------------------
    # Internal: LLM fallback
    # ------------------------------------------------------------------

    def _llm_classify(self, query: str) -> Tuple[Intent, float]:
        """Use LLM to classify intent when embedding confidence is low."""
        from common.config.prompts import INTENT_CLASSIFICATION_PROMPT
        try:
            prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
            response = self.llm.invoke(prompt)
            # FIX 5: robust parsing — match whole words only so that
            # "NOT MARKET_PRICE" doesn't accidentally match MARKET_PRICE.
            import re
            intent_str = response.content.strip().upper()
            for intent in Intent:
                # \b word-boundary ensures we match the full label token
                if re.search(rf'\b{re.escape(intent.value)}\b', intent_str):
                    logger.debug(f"LLM classified '{query}' → {intent.value}")
                    return intent, 0.75

            return Intent.GENERAL, 0.55

        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return Intent.GENERAL, 0.4

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_intent_description(self, intent: Intent) -> str:
        """Human-readable description of an intent."""
        descriptions = {
            Intent.MARKET_PRICE: "Fetching stock/index price",
            Intent.MARKET_TREND: "Analyzing market trends",
            Intent.STOCK_INFO: "Getting stock information",
            Intent.STOCK_HISTORY: "Stock price history / movement",
            Intent.TRADING_HOW_TO: "Explaining how to trade",
            Intent.PORTFOLIO_QUERY: "Analyzing portfolio",
            Intent.NEWS_REQUEST: "Fetching financial news",
            Intent.EDUCATION: "Teaching financial concepts",
            Intent.STOCK_SCREEN: "Screening / analyzing stocks",
            Intent.GREETING: "Greeting response",
            Intent.GENERAL: "General assistance",
        }
        return descriptions.get(intent, "Processing query")


# ============================================================================
# SINGLETON
# ============================================================================

_classifier: Optional[EmbeddingIntentClassifier] = None


def get_intent_classifier(llm=None) -> EmbeddingIntentClassifier:
    """Get or create the intent classifier singleton."""
    global _classifier
    if _classifier is None:
        _classifier = EmbeddingIntentClassifier(llm)
    elif llm is not None and _classifier.llm is None:
        # Inject LLM if classifier was created without one
        _classifier.llm = llm
    return _classifier
