"""
Centralized symbol registry for the FBOT platform.

All stock name mappings, index symbol mappings, and edge-case aliases
live here as the SINGLE SOURCE OF TRUTH. Every other module should
import from this file instead of maintaining its own copy.
"""


EDGE_CASE_ALIASES: dict[str, str] = {
    # ── Abbreviations / nicknames ───────────────────────────────────────
    "jio": "RELIANCE",
    "hul": "HINDUNILVR",
    "dmart": "DMART",
    "l&t": "LT",
    "m&m": "M&M",
    "sbi": "SBIN",
    "pnb": "PNB",
    "lic": "LICI",
    "hal": "HAL",
    "bhel": "BHEL",
    "irctc": "IRCTC",

    # ── NIFTY 50 — common spoken names ──────────────────────────────────
    "reliance": "RELIANCE",
    "reliance industries": "RELIANCE",
    "tcs": "TCS",
    "tata consultancy": "TCS",
    "hdfc bank": "HDFCBANK",
    "hdfc": "HDFCBANK",
    "infosys": "INFY",
    "icici bank": "ICICIBANK",
    "icici": "ICICIBANK",
    "hindustan unilever": "HINDUNILVR",
    "itc": "ITC",
    "state bank": "SBIN",
    "state bank of india": "SBIN",
    "bharti airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "kotak": "KOTAKBANK",
    "kotak bank": "KOTAKBANK",
    "kotak mahindra": "KOTAKBANK",
    "bajaj finance": "BAJFINANCE",
    "bajaj finserv": "BAJAJFINSV",
    "tata motors": "TATAMOTORS",
    "tata steel": "TATASTEEL",
    "maruti": "MARUTI",
    "maruti suzuki": "MARUTI",
    "asian paints": "ASIANPAINT",
    "wipro": "WIPRO",
    "titan": "TITAN",
    "adani enterprises": "ADANIENT",
    "adani": "ADANIENT",
    "adani ports": "ADANIPORTS",
    "axis bank": "AXISBANK",
    "axis": "AXISBANK",
    "sun pharma": "SUNPHARMA",
    "sun pharmaceutical": "SUNPHARMA",
    "ultratech": "ULTRACEMCO",
    "ultratech cement": "ULTRACEMCO",
    "nestle": "NESTLEIND",
    "nestle india": "NESTLEIND",
    "power grid": "POWERGRID",
    "ntpc": "NTPC",
    "ongc": "ONGC",
    "coal india": "COALINDIA",
    "cipla": "CIPLA",
    "dr reddy": "DRREDDY",
    "dr reddys": "DRREDDY",
    "tech mahindra": "TECHM",
    "hero motocorp": "HEROMOTOCO",
    "hero": "HEROMOTOCO",
    "hindalco": "HINDALCO",
    "tata consumer": "TATACONSUM",
    "bajaj auto": "BAJAJ-AUTO",
    "indusind bank": "INDUSINDBK",
    "indusind": "INDUSINDBK",
    "britannia": "BRITANNIA",
    "grasim": "GRASIM",
    "divis lab": "DIVISLAB",
    "divis": "DIVISLAB",
    "eicher motors": "EICHERMOT",
    "eicher": "EICHERMOT",
    "zomato": "ZOMATO",
    "paytm": "PAYTM",
    "nykaa": "NYKAA",
    "apollo hospitals": "APOLLOHOSP",
    "apollo": "APOLLOHOSP",
    "sbi life": "SBILIFE",
    "hdfc life": "HDFCLIFE",
    "tata power": "TATAPOWER",
    "vedanta": "VEDL",
    "jsw steel": "JSWSTEEL",
    "jsw": "JSWSTEEL",
}



INDICES: dict[str, str] = {
    "NIFTY": "NIFTY 50", "NIFTY50": "NIFTY 50", "NIFTY 50": "NIFTY 50",
    "SENSEX": "SENSEX", "BSE SENSEX": "SENSEX",
    "BANKNIFTY": "BANK NIFTY", "BANK NIFTY": "BANK NIFTY",
    "NIFTYIT": "NIFTY IT", "NIFTY IT": "NIFTY IT",
    "NIFTYFIN": "NIFTY FINANCIAL", "NIFTY FINANCIAL": "NIFTY FINANCIAL",
    "NIFTYPHARMA": "NIFTY PHARMA", "NIFTY PHARMA": "NIFTY PHARMA",
    "NIFTYAUTO": "NIFTY AUTO", "NIFTY AUTO": "NIFTY AUTO",
    "NIFTYMETAL": "NIFTY METAL", "NIFTY METAL": "NIFTY METAL",
    "NIFTYENERGY": "NIFTY ENERGY", "NIFTY ENERGY": "NIFTY ENERGY",
    "NIFTYFMCG": "NIFTY FMCG", "NIFTY FMCG": "NIFTY FMCG",
    "NIFTYNEXT50": "NIFTY NEXT 50", "NIFTY NEXT 50": "NIFTY NEXT 50",
    "NIFTYMIDCAP": "NIFTY MIDCAP", "NIFTY MIDCAP": "NIFTY MIDCAP",
    "MIDCAP100": "NIFTY MIDCAP 100", "NIFTY MIDCAP 100": "NIFTY MIDCAP 100",
    "NIFTY BANK": "BANK NIFTY",
}

INDEX_YF_SYMBOLS: dict[str, str] = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY FINANCIAL": "^CNXFIN",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY FMCG": "^CNXFMCG",
}


def get_index_yf_symbol(name: str) -> str | None:
    """
    Resolve any index name variant to its yfinance ticker.

    Examples:
        get_index_yf_symbol("NIFTY")       → "^NSEI"
        get_index_yf_symbol("BANK NIFTY")  → "^NSEBANK"
        get_index_yf_symbol("RANDOM")      → None
    """
    canonical = INDICES.get(name.strip().upper())
    if canonical:
        return INDEX_YF_SYMBOLS.get(canonical)
    return None



STOCK_NAME_MAP: dict[str, str] = {
    "RELIANCE": "Reliance Industries Ltd",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank Ltd",
    "INFY": "Infosys Ltd",
    "ICICIBANK": "ICICI Bank Ltd",
    "HINDUNILVR": "Hindustan Unilever Ltd",
    "ITC": "ITC Ltd",
    "SBIN": "State Bank of India",
    "BHARTIARTL": "Bharti Airtel Ltd",
    "KOTAKBANK": "Kotak Mahindra Bank Ltd",
    "LIC": "Life Insurance Corporation",
    "BAJFINANCE": "Bajaj Finance Ltd",
    "TATAMOTORS": "Tata Motors Ltd",
    "MARUTI": "Maruti Suzuki India Ltd",
    "ASIANPAINT": "Asian Paints Ltd",
    "WIPRO": "Wipro Ltd",
    "TITAN": "Titan Company Ltd",
    "ADANIENT": "Adani Enterprises Ltd",
    "AXISBANK": "Axis Bank Ltd",
    "SUNPHARMA": "Sun Pharmaceutical Industries Ltd",
}
NSE_SUFFIX = ".NS"
BSE_SUFFIX = ".BO"
