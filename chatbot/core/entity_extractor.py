"""
Entity extraction for the Finance Chatbot.
Extracts stock symbols, indices, time periods, and financial entities.
"""

import re
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


# ============================================================================
# KNOWN ENTITIES DATABASE
# ============================================================================

# Common words to exclude from stock symbol detection
# Instead of maintaining a list of all stocks, we detect patterns and exclude common words
EXCLUDED_WORDS = {
    # Common English words that might look like stock symbols
    "THE", "AND", "FOR", "WITH", "FROM", "INTO", "THAT", "THIS", "WHAT",
    "HOW", "WHY", "WHO", "WHERE", "WHEN", "WHICH",
    # Verbs
    "IS", "ARE", "WAS", "WERE", "WILL", "WOULD", "COULD", "SHOULD", "CAN",
    "BUY", "SELL", "HOLD", "EXIT", "GET", "SHOW", "TELL", "GIVE", "MAKE",
    "PUT", "CALL", "SET", "HAS", "HAVE", "HAD", "DO", "DOES", "DID",
    # Trading terms that shouldn't be extracted as symbols
    "STOCK", "STOCKS", "SHARE", "SHARES", "PRICE", "PRICES", "MARKET",
    "TRADE", "TRADING", "ORDER", "ORDERS", "LIMIT", "STOP", "LOSS",
    "PROFIT", "LOSS", "GAIN", "GAINS", "VOLUME", "HIGH", "LOW", "OPEN",
    "CLOSE", "TODAY", "YESTERDAY", "WEEK", "MONTH", "YEAR", "DAY",
    # Common question words
    "ABOUT", "TELL", "GIVE", "PLEASE", "NEED", "WANT", "KNOW", "FIND",
    # Other common words
    "ALL", "ANY", "SOME", "MORE", "MOST", "MUCH", "MANY", "FEW", "LESS",
    "OTHER", "NEW", "OLD", "GOOD", "BAD", "BEST", "WORST", "TOP", "BOTTOM",
    "UP", "DOWN", "IN", "OUT", "ON", "OFF", "AT", "BY", "TO", "OF", "OR",
    # Financial terms
    "PE", "EPS", "ROE", "ROA", "NAV", "IPO", "FII", "DII", "ETF", "MF",
    "SIP", "AMC", "AUM", "CAGR", "YOY", "QOQ", "MOM", "NSE", "BSE",
    # Single letters (except valid single-letter tickers if any)
    "A", "I", "S", "M", "P", "Q", "R", "T", "U", "V", "W", "X", "Y", "Z",
    # History/movement related words
    "LAST", "PAST", "FIVE", "THREE", "SEVEN", "TEN", "MOVEMENT", "HISTORY",
    "DAYS", "PERFORMANCE", "PERFORM", "PERFORMED", "MOVE", "MOVED",
    "TREND", "TRENDING", "DATA", "CHART", "GRAPH", "RECENT",
    # ---- NEW: common false-positives observed in real queries ----
    # Analysis / explanation verbs
    "EXPLAIN", "ANALYSE", "ANALYSIS", "ANALYZE", "ELABORATE",
    "SUMMARIZE", "DESCRIBE", "DETAIL", "DETAILS", "OVERVIEW",
    # Adjectives / descriptors
    "STRONG", "WEAK", "QUICK", "DAILY", "BASIC", "FULL", "BRIEF",
    "LATEST", "RECENT", "CURRENT", "SIMPLE", "COMPLETE",
    # Action verbs
    "CHECK", "LOOK", "FETCH", "LIST", "SCREEN", "SCREENER",
    "RUN", "COMPUTE", "CALCULATE", "UPDATE", "REFRESH",
    # Pronouns / determiners
    "THEM", "THESE", "THEIR", "THERE", "THEY", "EACH", "EVERY",
    "THEN", "ALSO", "JUST", "ONLY", "BEEN", "BEING",
    # Financial concepts (not symbols)
    "SECTOR", "INFO", "RESULT", "RESULTS", "REPORT", "REPORTS",
    "FUNDAMENTAL", "TECHNICAL", "INDICATOR", "INDICATORS",
    "DIVIDEND", "EARNINGS", "REVENUE", "GROWTH", "RETURN",
    "PORTFOLIO", "HOLDINGS", "POSITIONS", "INVESTMENT",
}


# ============================================================================
# TOP NSE SYMBOL WHITELIST
# ============================================================================
# Only uppercase tokens found by the open-ended scanner that appear here
# will be kept as stock-symbol candidates.  Everything else is discarded
# (unless it was already captured via COMPANY_NAME_MAP in Strategy 1).
# Covers the ~120 most actively traded NSE equities.

NSE_KNOWN_SYMBOLS: set = {
    # Nifty 50 & large-caps
    "TCS", "RELIANCE", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
    "SBIN", "BAJFINANCE", "BHARTIARTL", "KOTAKBANK", "WIPRO", "HCLTECH",
    "ASIANPAINT", "AXISBANK", "MARUTI", "SUNPHARMA", "TITAN", "TATAMOTORS",
    "TATASTEEL", "ULTRACEMCO", "LT", "NTPC", "POWERGRID", "ONGC",
    "COALINDIA", "JSWSTEEL", "HINDALCO", "DRREDDY", "CIPLA", "DIVISLAB",
    "ADANIENT", "ADANIPORTS", "ADANIGREEN", "ADANIPOWER", "BAJAJ-AUTO",
    "BAJAJFINSV", "TECHM", "GRASIM", "NESTLEIND", "ITC", "BRITANNIA",
    "DABUR", "MARICO", "GODREJCP", "VEDL", "ZOMATO", "PAYTM", "IRCTC",
    "HAL", "BHEL", "LICI", "TATAPOWER", "TATACHEM", "TATACONSUM",
    "TATAELXSI", "HEROMOTOCO", "EICHERMOT", "ASHOKLEY", "INDUSINDBK",
    "BANKBARODA", "PNB", "YESBANK", "IDFCFIRSTB", "LTIM", "PERSISTENT",
    "COFORGE", "DMART", "M&M",
    # Mid-caps frequently asked about
    "TATVA", "IRFC", "NHPC", "RECLTD", "PFC", "SAIL",
    "NMDC", "RVNL", "IRCON", "HUDCO", "CANBK", "UNIONBANK",
    "FEDERALBNK", "BANDHANBNK", "CHOLAFIN", "MUTHOOTFIN",
    "SBICARD", "HDFCLIFE", "ICICIPRULI", "SBILIFE",
    "PGHL", "AUROPHARMA", "LUPIN", "TORNTPHARM", "ALKEM",
    "PIIND", "NAUKRI", "INDIGO", "SPICEJET", "TRENT",
    "VOLTAS", "HAVELLS", "POLYCAB", "DIXON", "ABB",
    "SIEMENS", "CUMMINSIND", "THERMAX", "GMRINFRA", "ADANIGAS",
    # US stocks commonly asked about
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA",
    "NFLX", "AMD", "INTC", "DIS", "WMT", "KO", "PEP", "JNJ",
    "JPM", "GS", "PYPL", "CRM", "ADBE", "UBER", "SPOT",
    "SNAP", "ABNB", "PLTR", "COIN", "SNOW", "CRWD", "SHOP",
    "BA", "GM", "V", "MA", "BRK-B",
}


# ============================================================================
# Maps natural company names (lowercase) to stock symbols.
# This allows users to type "tata steel" instead of "TATASTEEL".

COMPANY_NAME_MAP = {
    # ------ INDIAN STOCKS (NSE) ------
    # Tata Group
    "tata steel": "TATASTEEL",
    "tata motors": "TATAMOTORS",
    "tata power": "TATAPOWER",
    "tata chemicals": "TATACHEM",
    "tata consumer": "TATACONSUM",
    "tata elxsi": "TATAELXSI",
    "tcs": "TCS",
    "tata consultancy": "TCS",
    # Reliance
    "reliance": "RELIANCE",
    "reliance industries": "RELIANCE",
    "jio": "RELIANCE",
    # Banking
    "hdfc bank": "HDFCBANK",
    "hdfc": "HDFCBANK",
    "icici bank": "ICICIBANK",
    "icici": "ICICIBANK",
    "sbi": "SBIN",
    "state bank": "SBIN",
    "state bank of india": "SBIN",
    "kotak bank": "KOTAKBANK",
    "kotak mahindra": "KOTAKBANK",
    "axis bank": "AXISBANK",
    "indusind bank": "INDUSINDBK",
    "bank of baroda": "BANKBARODA",
    "punjab national bank": "PNB",
    "pnb": "PNB",
    "yes bank": "YESBANK",
    "idfc first bank": "IDFCFIRSTB",
    # IT
    "infosys": "INFY",
    "wipro": "WIPRO",
    "hcl tech": "HCLTECH",
    "hcl technologies": "HCLTECH",
    "tech mahindra": "TECHM",
    "ltimindtree": "LTIM",
    "persistent systems": "PERSISTENT",
    "coforge": "COFORGE",
    # Automobile
    "maruti": "MARUTI",
    "maruti suzuki": "MARUTI",
    "mahindra": "M&M",
    "mahindra and mahindra": "M&M",
    "m&m": "M&M",
    "bajaj auto": "BAJAJ-AUTO",
    "hero motocorp": "HEROMOTOCO",
    "eicher motors": "EICHERMOT",
    "ashok leyland": "ASHOKLEY",
    # Pharma
    "sun pharma": "SUNPHARMA",
    "dr reddy": "DRREDDY",
    "dr reddys": "DRREDDY",
    "cipla": "CIPLA",
    "divi's lab": "DIVISLAB",
    "divis lab": "DIVISLAB",
    # FMCG
    "hindustan unilever": "HINDUNILVR",
    "hul": "HINDUNILVR",
    "itc": "ITC",
    "nestle": "NESTLEIND",
    "nestle india": "NESTLEIND",
    "britannia": "BRITANNIA",
    "dabur": "DABUR",
    "godrej consumer": "GODREJCP",
    "marico": "MARICO",
    # Others
    "adani enterprises": "ADANIENT",
    "adani ports": "ADANIPORTS",
    "adani green": "ADANIGREEN",
    "adani power": "ADANIPOWER",
    "bajaj finance": "BAJFINANCE",
    "bajaj finserv": "BAJAJFINSV",
    "asian paints": "ASIANPAINT",
    "titan": "TITAN",
    "titan company": "TITAN",
    "ultratech cement": "ULTRACEMCO",
    "grasim": "GRASIM",
    "bharti airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "lic": "LICI",
    "life insurance corporation": "LICI",
    "power grid": "POWERGRID",
    "ntpc": "NTPC",
    "ongc": "ONGC",
    "coal india": "COALINDIA",
    "hindalco": "HINDALCO",
    "jsw steel": "JSWSTEEL",
    "vedanta": "VEDL",
    "larsen": "LT",
    "larsen and toubro": "LT",
    "l&t": "LT",
    "zomato": "ZOMATO",
    "paytm": "PAYTM",
    "dmart": "DMART",
    "avenue supermarts": "DMART",
    "irctc": "IRCTC",
    "hal": "HAL",
    "hindustan aeronautics": "HAL",
    "bhel": "BHEL",

    # ------ US STOCKS ------
    "nvidia": "NVDA",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "tesla": "TSLA",
    "netflix": "NFLX",
    "amd": "AMD",
    "intel": "INTC",
    "disney": "DIS",
    "walmart": "WMT",
    "coca cola": "KO",
    "pepsi": "PEP",
    "pepsico": "PEP",
    "johnson and johnson": "JNJ",
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "goldman sachs": "GS",
    "berkshire": "BRK-B",
    "berkshire hathaway": "BRK-B",
    "paypal": "PYPL",
    "salesforce": "CRM",
    "adobe": "ADBE",
    "uber": "UBER",
    "spotify": "SPOT",
    "snapchat": "SNAP",
    "snap": "SNAP",
    "airbnb": "ABNB",
    "palantir": "PLTR",
    "coinbase": "COIN",
    "snowflake": "SNOW",
    "crowdstrike": "CRWD",
    "shopify": "SHOP",
    "boeing": "BA",
    "ford": "F",
    "general motors": "GM",
    "visa": "V",
    "mastercard": "MA",
}

# Market Indices
INDICES = {
    "NIFTY": "NIFTY 50",
    "NIFTY50": "NIFTY 50",
    "NIFTY 50": "NIFTY 50",
    "SENSEX": "SENSEX", 
    "BSE SENSEX": "SENSEX",
    "BANKNIFTY": "BANK NIFTY",
    "BANK NIFTY": "BANK NIFTY",
    "NIFTYIT": "NIFTY IT",
    "NIFTY IT": "NIFTY IT",
    "NIFTYFIN": "NIFTY FINANCIAL",
    "NIFTYPHARMA": "NIFTY PHARMA",
    "NIFTYAUTO": "NIFTY AUTO",
    "NIFTYMETAL": "NIFTY METAL",
    "NIFTYENERGY": "NIFTY ENERGY",
    "NIFTYFMCG": "NIFTY FMCG",
    "NIFTYNEXT50": "NIFTY NEXT 50",
    "NIFTYMIDCAP": "NIFTY MIDCAP",
    "MIDCAP100": "NIFTY MIDCAP 100",
}

# Time Period Patterns
TIME_PATTERNS = {
    r"\btoday\b": "today",
    r"\byesterday\b": "yesterday",
    r"\bthis\s+week\b": "this_week",
    r"\blast\s+week\b": "last_week",
    r"\bthis\s+month\b": "this_month",
    r"\blast\s+month\b": "last_month",
    r"\bthis\s+year\b": "this_year",
    r"\blast\s+year\b": "last_year",
    r"\b(\d+)\s*(day|week|month|year)s?\s*(ago)?\b": "relative",
    r"\b(1|3|6|12)\s*months?\b": "period",
    r"\b(52|26)\s*weeks?\b": "period",
    r"\bYTD\b": "ytd",
    r"\bMTD\b": "mtd",
    r"\bQTD\b": "qtd",
}

# Order Types
ORDER_TYPES = {
    "market order": "MARKET",
    "limit order": "LIMIT", 
    "stop loss": "STOP_LOSS",
    "stop-loss": "STOP_LOSS",
    "stoploss": "STOP_LOSS",
    "sl order": "STOP_LOSS",
    "bracket order": "BRACKET",
    "bo order": "BRACKET",
    "cover order": "COVER",
    "co order": "COVER",
    "amo": "AMO",
    "after market order": "AMO",
    "gtc": "GTC",
    "gtt": "GTT",
    "good till triggered": "GTT",
}

# Trading Actions
TRADING_ACTIONS = ["buy", "sell", "hold", "exit", "short", "long", "square off"]


@dataclass
class ExtractedEntities:
    """Container for extracted entities."""
    stock_symbols: List[str]
    indices: List[str]
    time_period: Optional[str]
    order_type: Optional[str]
    amount: Optional[str]
    action: Optional[str]
    raw_query: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stock_symbols": self.stock_symbols,
            "indices": self.indices,
            "time_period": self.time_period,
            "order_type": self.order_type,
            "amount": self.amount,
            "action": self.action,
        }
    
    def has_stock_context(self) -> bool:
        """Check if any stock/index is mentioned."""
        return bool(self.stock_symbols or self.indices)


class EntityExtractor:
    """
    Extract financial entities from user queries.
    Uses pattern matching and fuzzy matching for robustness.
    """
    
    def __init__(self):
        """Initialize entity extractor."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns."""
        self.time_patterns = {
            re.compile(p, re.IGNORECASE): v 
            for p, v in TIME_PATTERNS.items()
        }
        
        # Stock symbol pattern (uppercase letters, 2-15 chars)
        self.stock_pattern = re.compile(r'\b([A-Z]{2,15}(?:-[A-Z]+)?)\b')
        
        # Amount patterns (₹, Rs, rupees, dollars)
        self.amount_pattern = re.compile(
            r'(?:₹|Rs\.?|INR|USD|\$)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)|'
            r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:rupees?|dollars?|lakhs?|crores?|k|L|Cr)',
            re.IGNORECASE
        )
        
        # Quantity pattern
        self.quantity_pattern = re.compile(r'(\d+)\s*(?:shares?|units?|stocks?|qty)', re.IGNORECASE)
    
    def extract(self, query: str) -> ExtractedEntities:
        """
        Extract all entities from a query.
        
        Args:
            query: User's natural language query
            
        Returns:
            ExtractedEntities with all found entities
        """
        query_upper = query.upper()
        query_lower = query.lower()
        
        return ExtractedEntities(
            stock_symbols=self._extract_stocks(query_upper),
            indices=self._extract_indices(query),
            time_period=self._extract_time_period(query_lower),
            order_type=self._extract_order_type(query_lower),
            amount=self._extract_amount(query),
            action=self._extract_action(query_lower),
            raw_query=query
        )
    
    def _extract_stocks(self, query: str) -> List[str]:
        """
        Extract potential stock symbols from query.

        Uses THREE strategies in priority order:
        1. Company name matching (lowercase) — catches "tata steel", "nvidia", etc.
        2. Fuzzy name matching via rapidfuzz — resolves typos like "reliace" → RELIANCE
        3. Uppercase pattern matching — catches NSE-whitelisted tickers like TCS, HDFCBANK

        Strategy 3 is gated by NSE_KNOWN_SYMBOLS so that random
        uppercase words (EXPLAIN, PERFORM, etc.) are never extracted.
        """
        found_stocks = []
        query_lower = query.lower()

        # ------------------------------------------------------------------
        # Strategy 1: Exact company name match from COMPANY_NAME_MAP
        # ------------------------------------------------------------------
        # Sort by length (longest first) so "tata consultancy" wins over "tata"
        for name in sorted(COMPANY_NAME_MAP.keys(), key=len, reverse=True):
            if name in query_lower:
                symbol = COMPANY_NAME_MAP[name]
                if symbol not in found_stocks:
                    found_stocks.append(symbol)
                # Remove the matched name to avoid partial re-matches
                query_lower = query_lower.replace(name, " ")

        # ------------------------------------------------------------------
        # Strategy 2: Fuzzy name matching (typo recovery)
        # Only runs if Strategy 1 found nothing.
        # Generates word unigrams, bigrams, and trigrams from the query and
        # fuzzy-matches each against COMPANY_NAME_MAP keys.
        # This way "reliace" (1 word typo) matches "reliance" and
        # "tata moters" (2-word typo) matches "tata motors" not "tata steel".
        # ------------------------------------------------------------------
        if not found_stocks:
            try:
                from rapidfuzz import process as fuzz_process, fuzz

                # Build candidates: individual words + consecutive n-grams
                words_raw = query_lower.split()
                candidates = [w for w in words_raw if len(w) >= 4]
                for i in range(len(words_raw) - 1):
                    bigram = f"{words_raw[i]} {words_raw[i+1]}"
                    if len(bigram) >= 4:
                        candidates.append(bigram)
                for i in range(len(words_raw) - 2):
                    trigram = f"{words_raw[i]} {words_raw[i+1]} {words_raw[i+2]}"
                    candidates.append(trigram)

                best_score, best_symbol = 0, None
                name_keys = list(COMPANY_NAME_MAP.keys())

                for candidate in candidates:
                    result = fuzz_process.extractOne(
                        candidate,
                        name_keys,
                        scorer=fuzz.WRatio,
                    )
                    if result and result[1] > best_score:
                        best_score = result[1]
                        best_symbol = COMPANY_NAME_MAP[result[0]]

                if best_score >= 85 and best_symbol and best_symbol not in found_stocks:
                    found_stocks.append(best_symbol)

            except ImportError:
                pass  # rapidfuzz not installed; skip fuzzy step silently


        # ------------------------------------------------------------------
        # Strategy 3: Uppercase token scan — whitelisted symbols only
        # ------------------------------------------------------------------
        # Matches: TCS, RELIANCE, HDFCBANK, M&M, BAJAJ-AUTO, etc.
        words = re.findall(r'\b[A-Z][A-Z0-9&-]{1,14}\b', query.upper())

        for word in words:
            # Clean for validation
            word_clean = word.replace('-', '').replace('&', '')

            # Skip excluded words
            if word in EXCLUDED_WORDS or word_clean in EXCLUDED_WORDS:
                continue

            # Skip very short tokens after cleaning
            if len(word_clean) < 2:
                continue

            # *** Gate: only accept if the token is in the known-symbol whitelist ***
            if word not in NSE_KNOWN_SYMBOLS and word_clean not in NSE_KNOWN_SYMBOLS:
                continue

            if word not in found_stocks:
                found_stocks.append(word)

        return found_stocks
    
    def _extract_indices(self, query: str) -> List[str]:
        """Extract market indices from query."""
        found_indices = []
        query_upper = query.upper()
        
        for key, normalized in INDICES.items():
            if key.upper() in query_upper:
                if normalized not in found_indices:
                    found_indices.append(normalized)
        
        return found_indices
    
    def _extract_time_period(self, query: str) -> Optional[str]:
        """Extract time period from query."""
        for pattern, time_value in self.time_patterns.items():
            match = pattern.search(query)
            if match:
                if time_value == "relative":
                    # Extract the actual time period
                    groups = match.groups()
                    return f"{groups[0]}_{groups[1]}s_ago"
                return time_value
        return None
    
    def _extract_order_type(self, query: str) -> Optional[str]:
        """Extract order type from query."""
        for pattern, order_type in ORDER_TYPES.items():
            if pattern in query:
                return order_type
        return None
    
    def _extract_amount(self, query: str) -> Optional[str]:
        """Extract monetary amounts or quantities."""
        # Check for monetary amounts
        match = self.amount_pattern.search(query)
        if match:
            return match.group(0)
        
        # Check for quantities
        qty_match = self.quantity_pattern.search(query)
        if qty_match:
            return f"{qty_match.group(1)} shares"
        
        return None
    
    def _extract_action(self, query: str) -> Optional[str]:
        """Extract trading action from query."""
        for action in TRADING_ACTIONS:
            if action in query:
                return action.upper()
        return None
    
    def get_primary_symbol(self, entities: ExtractedEntities) -> Optional[str]:
        """Get the primary stock/index from extracted entities."""
        if entities.stock_symbols:
            return entities.stock_symbols[0]
        if entities.indices:
            return entities.indices[0]
        return None


# Singleton instance
_extractor = None

def get_entity_extractor() -> EntityExtractor:
    """Get or create the entity extractor singleton."""
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor
