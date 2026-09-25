"""
Symbol resolution utilities for the FBOT chatbot.

Uses Screener.in's autocomplete API as the primary resolution strategy
for Indian stocks. This is 100% reliable for Indian stocks with zero
US-bias, unlike Yahoo Finance Search which returns US ADRs.

Strategy:
    A. Edge-case alias lookup   (instant, handles nicknames like "jio")
    B. Fuzzy alias match        (rapidfuzz, handles typos like "reliace")
    C. Screener.in API search   (reliable, returns exact NSE/BSE tickers)
    D. Predict fallback         (cleaned name → .NS, validated via yfinance)

All static mappings live in ``chatbot.core.symbol_registry`` (single source
of truth).  This module only contains *resolution logic*.
"""

import logging
import re
from typing import Optional

import aiohttp
from rapidfuzz import process, fuzz

from chatbot.core.symbol_registry import EDGE_CASE_ALIASES, INDICES

logger = logging.getLogger(__name__)

# Pre-compute alias keys list once at module load for rapidfuzz
_ALIAS_KEYS = list(EDGE_CASE_ALIASES.keys())
_FUZZY_SCORE_CUTOFF = 75  # Minimum similarity threshold (0–100)

# ── Screener.in Search API ──────────────────────────────────────────────

_SCREENER_SEARCH_URL = "https://www.screener.in/api/company/search/"
_SCREENER_HEADERS = {"User-Agent": "Mozilla/5.0"}


async def get_ticker_from_screener(company_name: str) -> Optional[str]:
    """
    Uses Screener.in's autocomplete API to find the exact Indian stock ticker.
    Returns the ticker with '.NS' appended, or None.

    Uses async aiohttp to avoid blocking the event loop.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _SCREENER_SEARCH_URL,
                params={"q": company_name},
                headers=_SCREENER_HEADERS,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    results = await response.json()
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


# ── yfinance validation helper ──────────────────────────────────────────


async def _validate_ticker(symbol: str) -> bool:
    """
    Validate that a predicted ticker actually exists on yfinance.
    Returns True if the ticker has a valid price, False otherwise.
    Runs in a thread pool to avoid blocking the async event loop.
    """
    import asyncio
    try:
        import yfinance as yf
    except ImportError:
        # If yfinance is not installed, skip validation
        return True

    def _check():
        try:
            info = yf.Ticker(symbol).info
            price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            return bool(price and price > 0)
        except Exception:
            return False

    return await asyncio.to_thread(_check)


# ── Main resolution function ────────────────────────────────────────────


async def resolve_symbol(name: str) -> Optional[str]:
    """
    Resolve a company name or ticker to a valid stock symbol.

    Strategy:
        1. Check edge-case aliases (nicknames like "jio", "hul")
        2. Screener.in API search (trusted — no verification needed)
        3. Predict fallback (clean name → append .NS → validate via yfinance)

    Returns:
        Resolved symbol string (e.g. 'ZOMATO.NS'), or None.
    """
    if not name or not name.strip():
        return None

    raw_name_lower = name.strip().lower()

    # ── Step 1: Edge-case alias lookup (exact, O(1)) ───────────────
    if raw_name_lower in EDGE_CASE_ALIASES:
        alias = EDGE_CASE_ALIASES[raw_name_lower]
        resolved = f"{alias}.NS"
        logger.info(f"Alias match: '{name}' → {resolved}")
        return resolved

    # ── Step 2: Fuzzy alias match (handles typos, <0.1ms) ──────────
    fuzzy_result = process.extractOne(
        raw_name_lower,
        _ALIAS_KEYS,
        scorer=fuzz.ratio,
        score_cutoff=_FUZZY_SCORE_CUTOFF,
    )
    if fuzzy_result:
        matched_key, score, _ = fuzzy_result
        alias = EDGE_CASE_ALIASES[matched_key]
        resolved = f"{alias}.NS"
        logger.info(
            f"Fuzzy match: '{name}' → '{matched_key}' (score={score:.1f}) → {resolved}"
        )
        return resolved

    # ── Step 3: Screener.in API (trusted, no verification) ──────────
    screener_ticker = await get_ticker_from_screener(name)
    if screener_ticker:
        return screener_ticker

    # ── Step 4: Predict fallback (clean → .NS → validate) ───────────
    cleaned = clean_company_name(name)
    if not cleaned:
        return None

    predicted_ns = f"{cleaned}.NS"

    # Validate the predicted ticker actually exists
    if await _validate_ticker(predicted_ns):
        logger.info(f"Predicted NSE ticker (validated): '{name}' → {predicted_ns}")
        return predicted_ns

    logger.warning(
        f"Predicted ticker '{predicted_ns}' failed yfinance validation for input '{name}'"
    )
    return None


# ── Index resolution ────────────────────────────────────────────────────


def resolve_index(name: str) -> Optional[str]:
    """Resolve an index name to its canonical form."""
    if not name:
        return None
    name_upper = name.strip().upper()
    return INDICES.get(name_upper)
