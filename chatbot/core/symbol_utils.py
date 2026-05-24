"""
Symbol resolution utilities for the FinSight chatbot.
Maps natural company names to stock tickers and normalizes symbols.
Extracted from entity_extractor.py for use by LangGraph agent tools.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# TOP NSE SYMBOL WHITELIST
# ============================================================================

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
# COMPANY NAME → TICKER MAP
# ============================================================================

COMPANY_NAME_MAP = {
    # ------ INDIAN STOCKS (NSE) ------
    # Tata Group
    "tata steel": "TATASTEEL", "tata motors": "TATAMOTORS",
    "tata power": "TATAPOWER", "tata chemicals": "TATACHEM",
    "tata consumer": "TATACONSUM", "tata elxsi": "TATAELXSI",
    "tcs": "TCS", "tata consultancy": "TCS",
    # Reliance
    "reliance": "RELIANCE", "reliance industries": "RELIANCE", "jio": "RELIANCE",
    # Banking
    "hdfc bank": "HDFCBANK", "hdfc": "HDFCBANK",
    "icici bank": "ICICIBANK", "icici": "ICICIBANK",
    "sbi": "SBIN", "state bank": "SBIN", "state bank of india": "SBIN",
    "kotak bank": "KOTAKBANK", "kotak mahindra": "KOTAKBANK",
    "axis bank": "AXISBANK", "indusind bank": "INDUSINDBK",
    "bank of baroda": "BANKBARODA", "punjab national bank": "PNB", "pnb": "PNB",
    "yes bank": "YESBANK", "idfc first bank": "IDFCFIRSTB",
    # IT
    "infosys": "INFY", "wipro": "WIPRO",
    "hcl tech": "HCLTECH", "hcl technologies": "HCLTECH",
    "tech mahindra": "TECHM", "ltimindtree": "LTIM",
    "persistent systems": "PERSISTENT", "coforge": "COFORGE",
    # Automobile
    "maruti": "MARUTI", "maruti suzuki": "MARUTI",
    "mahindra": "M&M", "mahindra and mahindra": "M&M", "m&m": "M&M",
    "bajaj auto": "BAJAJ-AUTO", "hero motocorp": "HEROMOTOCO",
    "eicher motors": "EICHERMOT", "ashok leyland": "ASHOKLEY",
    # Pharma
    "sun pharma": "SUNPHARMA", "dr reddy": "DRREDDY", "dr reddys": "DRREDDY",
    "cipla": "CIPLA", "divi's lab": "DIVISLAB", "divis lab": "DIVISLAB",
    # FMCG
    "hindustan unilever": "HINDUNILVR", "hul": "HINDUNILVR",
    "itc": "ITC", "nestle": "NESTLEIND", "nestle india": "NESTLEIND",
    "britannia": "BRITANNIA", "dabur": "DABUR",
    "godrej consumer": "GODREJCP", "marico": "MARICO",
    # Others
    "adani enterprises": "ADANIENT", "adani ports": "ADANIPORTS",
    "adani green": "ADANIGREEN", "adani power": "ADANIPOWER",
    "bajaj finance": "BAJFINANCE", "bajaj finserv": "BAJAJFINSV",
    "asian paints": "ASIANPAINT", "titan": "TITAN", "titan company": "TITAN",
    "ultratech cement": "ULTRACEMCO", "grasim": "GRASIM",
    "bharti airtel": "BHARTIARTL", "airtel": "BHARTIARTL",
    "lic": "LICI", "life insurance corporation": "LICI",
    "power grid": "POWERGRID", "ntpc": "NTPC", "ongc": "ONGC",
    "coal india": "COALINDIA", "hindalco": "HINDALCO",
    "jsw steel": "JSWSTEEL", "vedanta": "VEDL",
    "larsen": "LT", "larsen and toubro": "LT", "l&t": "LT",
    "zomato": "ZOMATO", "paytm": "PAYTM",
    "dmart": "DMART", "avenue supermarts": "DMART",
    "irctc": "IRCTC", "hal": "HAL", "hindustan aeronautics": "HAL", "bhel": "BHEL",
    # ------ US STOCKS ------
    "nvidia": "NVDA", "apple": "AAPL", "microsoft": "MSFT",
    "google": "GOOGL", "alphabet": "GOOGL", "amazon": "AMZN",
    "meta": "META", "facebook": "META", "tesla": "TSLA", "netflix": "NFLX",
    "amd": "AMD", "intel": "INTC", "disney": "DIS", "walmart": "WMT",
    "coca cola": "KO", "pepsi": "PEP", "pepsico": "PEP",
    "johnson and johnson": "JNJ", "jpmorgan": "JPM", "jp morgan": "JPM",
    "goldman sachs": "GS", "berkshire": "BRK-B", "berkshire hathaway": "BRK-B",
    "paypal": "PYPL", "salesforce": "CRM", "adobe": "ADBE",
    "uber": "UBER", "spotify": "SPOT", "snapchat": "SNAP", "snap": "SNAP",
    "airbnb": "ABNB", "palantir": "PLTR", "coinbase": "COIN",
    "snowflake": "SNOW", "crowdstrike": "CRWD", "shopify": "SHOP",
    "boeing": "BA", "ford": "F", "general motors": "GM",
    "visa": "V", "mastercard": "MA",
}


# ============================================================================
# INDEX MAPPINGS
# ============================================================================

INDICES = {
    "NIFTY": "NIFTY 50", "NIFTY50": "NIFTY 50", "NIFTY 50": "NIFTY 50",
    "SENSEX": "SENSEX", "BSE SENSEX": "SENSEX",
    "BANKNIFTY": "BANK NIFTY", "BANK NIFTY": "BANK NIFTY",
    "NIFTYIT": "NIFTY IT", "NIFTY IT": "NIFTY IT",
    "NIFTYFIN": "NIFTY FINANCIAL", "NIFTYPHARMA": "NIFTY PHARMA",
    "NIFTYAUTO": "NIFTY AUTO", "NIFTYMETAL": "NIFTY METAL",
    "NIFTYENERGY": "NIFTY ENERGY", "NIFTYFMCG": "NIFTY FMCG",
    "NIFTYNEXT50": "NIFTY NEXT 50", "NIFTYMIDCAP": "NIFTY MIDCAP",
    "MIDCAP100": "NIFTY MIDCAP 100",
}


# ============================================================================
# SYMBOL RESOLUTION
# ============================================================================

def resolve_symbol(name: str) -> Optional[str]:
    """
    Resolve a natural-language company name or ticker to a valid stock symbol.

    Tries in order:
    1. Exact match in COMPANY_NAME_MAP (case-insensitive)
    2. Direct uppercase match in NSE_KNOWN_SYMBOLS
    3. Fuzzy match via rapidfuzz (typo recovery)

    Returns:
        Resolved symbol string, or None if unresolvable.
    """
    if not name or not name.strip():
        return None

    name_clean = name.strip()
    name_lower = name_clean.lower()

    # Strategy 1: Exact company name match
    # Sort by length (longest first) to prefer "tata consultancy" over "tata"
    for key in sorted(COMPANY_NAME_MAP.keys(), key=len, reverse=True):
        if key in name_lower:
            return COMPANY_NAME_MAP[key]

    # Strategy 2: Direct symbol lookup (already uppercase)
    name_upper = name_clean.upper()
    if name_upper in NSE_KNOWN_SYMBOLS:
        return name_upper

    # Strategy 3: Fuzzy matching (typo recovery)
    try:
        from rapidfuzz import process as fuzz_process, fuzz

        # Build candidates: individual words + bigrams
        words_raw = name_lower.split()
        candidates = [w for w in words_raw if len(w) >= 4]
        for i in range(len(words_raw) - 1):
            bigram = f"{words_raw[i]} {words_raw[i + 1]}"
            if len(bigram) >= 4:
                candidates.append(bigram)
        for i in range(len(words_raw) - 2):
            trigram = f"{words_raw[i]} {words_raw[i + 1]} {words_raw[i + 2]}"
            candidates.append(trigram)

        best_score, best_symbol = 0, None
        name_keys = list(COMPANY_NAME_MAP.keys())

        for candidate in candidates:
            result = fuzz_process.extractOne(
                candidate, name_keys, scorer=fuzz.WRatio,
            )
            if result and result[1] > best_score:
                best_score = result[1]
                best_symbol = COMPANY_NAME_MAP[result[0]]

        if best_score >= 85 and best_symbol:
            logger.info(f"Fuzzy resolved: '{name}' → {best_symbol} (score={best_score})")
            return best_symbol

    except ImportError:
        import difflib
        name_keys = list(COMPANY_NAME_MAP.keys())
        matches = difflib.get_close_matches(name_lower, name_keys, n=1, cutoff=0.75)
        if matches:
            best_symbol = COMPANY_NAME_MAP[matches[0]]
            logger.info(f"Difflib resolved: '{name}' → {best_symbol}")
            return best_symbol
        
    return None


def resolve_index(name: str) -> Optional[str]:
    """Resolve an index name to its canonical form."""
    if not name:
        return None
    name_upper = name.strip().upper()
    return INDICES.get(name_upper)
