"""
Symbol resolution utilities for the FinSight chatbot.

Uses Screener.in's autocomplete API as the primary resolution strategy
for Indian stocks. This is 100% reliable for Indian stocks with zero
US-bias, unlike Yahoo Finance Search which returns US ADRs.

Strategy:
    A. Edge-case alias lookup  (instant, handles nicknames like "jio")
    B. Screener.in API search  (reliable, returns exact NSE/BSE tickers)
    C. Predict fallback        (for extremely new IPOs — no verification)

All static mappings live in ``chatbot.core.symbol_registry`` (single source
of truth).  This module only contains *resolution logic*.
"""

import logging
import re
from typing import Optional

import requests

from chatbot.core.symbol_registry import EDGE_CASE_ALIASES, INDICES

logger = logging.getLogger(__name__)

# ── Screener.in Search API ──────────────────────────────────────────────

_SCREENER_SEARCH_URL = "https://www.screener.in/api/company/search/"
_SCREENER_HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_ticker_from_screener(company_name: str) -> Optional[str]:
    """
    Uses Screener.in's autocomplete API to find the exact Indian stock ticker.
    Returns the ticker with '.NS' appended, or None.

    Screener.in is trusted completely — no yfinance verification needed.
    """
    try:
        response = requests.get(
            _SCREENER_SEARCH_URL,
            params={"q": company_name},
            headers=_SCREENER_HEADERS,
            timeout=5,
        )
        if response.status_code == 200:
            results = response.json()
            if results and len(results) > 0:
                # Screener returns urls like "/company/ZOMATO/consolidated/"
                # We need the segment right after "company/", not the last one.
                company_url = results[0].get("url", "")
                parts = [p for p in company_url.split("/") if p]
                ticker = None
                for i, part in enumerate(parts):
                    if part.lower() == "company" and i + 1 < len(parts):
                        ticker = parts[i + 1].upper()
                        break
                if ticker:
                    resolved = f"{ticker}.NS"
                    logger.info(
                        f"Screener.in search: '{company_name}' → {resolved}"
                    )
                    return resolved
    except Exception as e:
        logger.debug(f"Screener.in search failed for '{company_name}': {e}")

    return None


# ── Helper: clean company name for prediction ───────────────────────────


def clean_company_name(name: str) -> str:
    """
    Clean a raw company name for ticker prediction.
    Removes common corporate suffixes, spaces, and non-alphanumeric characters.
    Result is always UPPERCASE with no spaces.
    """
    name = re.sub(
        r"\b(ltd|limited|corp|corporation|inc|company|co)\b",
        "",
        name,
        flags=re.IGNORECASE,
    )
    # Remove ALL spaces and special characters — ticker symbols never have them
    name = re.sub(r"[^a-zA-Z0-9]", "", name)
    return name.upper()


# ── Main resolution function ────────────────────────────────────────────


def resolve_symbol(name: str) -> Optional[str]:
    """
    Resolve a company name or ticker to a valid stock symbol.

    Strategy:
        1. Check edge-case aliases (nicknames like "jio", "hul")
        2. Screener.in API search (trusted — no verification needed)
        3. Predict fallback (clean name → append .NS)

    Returns:
        Resolved symbol string (e.g. 'ZOMATO.NS'), or None.
    """
    if not name or not name.strip():
        return None

    raw_name_lower = name.strip().lower()

    # ── Step 1: Edge-case alias lookup ──────────────────────────────
    if raw_name_lower in EDGE_CASE_ALIASES:
        alias = EDGE_CASE_ALIASES[raw_name_lower]
        resolved = f"{alias}.NS"
        logger.info(f"Alias match: '{name}' → {resolved}")
        return resolved

    # ── Step 2: Screener.in API (trusted, no verification) ──────────
    screener_ticker = get_ticker_from_screener(name)
    if screener_ticker:
        return screener_ticker

    # ── Step 3: Predict fallback (clean → .NS) ──────────────────────
    cleaned = clean_company_name(name)
    if not cleaned:
        return None

    predicted_ns = f"{cleaned}.NS"
    logger.info(f"Predicted NSE ticker: '{name}' → {predicted_ns}")
    return predicted_ns


# ── Index resolution ────────────────────────────────────────────────────


def resolve_index(name: str) -> Optional[str]:
    """Resolve an index name to its canonical form."""
    if not name:
        return None
    name_upper = name.strip().upper()
    return INDICES.get(name_upper)
