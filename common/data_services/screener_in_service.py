"""
Screener.in free API service.
Provides 10-year fundamental data for Indian stocks.
No API key required. Free public endpoint.
URL: https://www.screener.in/api/company/{SYMBOL}/
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
SCREENER_API_BASE = "https://www.screener.in/api/company"


class ScreenerInService:

    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 3600

    def _get_from_cache(self, key):
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            del self._cache[key]
        return None

    def _set_cache(self, key, value):
        self._cache[key] = (value, datetime.now() + timedelta(seconds=self._cache_ttl))

    async def get_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        cache_key = f"screener:{symbol}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        url = f"{SCREENER_API_BASE}/{symbol.upper()}/"
        try:
            import urllib.request, json
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            result = self._parse(symbol, data)
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Screener.in fetch failed for {symbol}: {e}")
            return None

    def _parse(self, symbol: str, data: dict) -> Dict[str, Any]:
        ratios = {}
        for r in data.get("ratios", []):
            vals = r.get("values", [{}])
            ratios[r.get("name", "")] = vals[-1].get("value") if vals else None

        return {
            "symbol": symbol.upper(),
            "name": data.get("name", symbol),
            "pe_ratio": ratios.get("Stock P/E"),
            "pb_ratio": ratios.get("Price to Book value"),
            "roe": ratios.get("Return on equity"),
            "roce": ratios.get("Return on capital employed"),
            "debt_to_equity": ratios.get("Debt to equity"),
            "current_ratio": ratios.get("Current ratio"),
            "dividend_yield": ratios.get("Dividend Yield"),
            "promoter_holding": data.get("shareholding", {}).get("promoters"),
            "fii_holding": data.get("shareholding", {}).get("fii"),
            "dii_holding": data.get("shareholding", {}).get("dii"),
            "sector": data.get("sector"),
            "industry": data.get("industry"),
            "pros": data.get("pros", [])[:3],
            "cons": data.get("cons", [])[:3],
            "source": "screener.in",
        }

    def format_for_llm(self, data: Dict[str, Any]) -> str:
        if not data:
            return ""
        lines = [f"Screener.in data for {data.get('name', '')} ({data.get('symbol', '')}):"]
        for k, label in [
            ("pe_ratio","PE Ratio"), ("pb_ratio","PB Ratio"), ("roe","ROE %"),
            ("roce","ROCE %"), ("debt_to_equity","Debt/Equity"),
            ("promoter_holding","Promoter Holding %"),
            ("fii_holding","FII Holding %"), ("current_ratio","Current Ratio")
        ]:
            if data.get(k) is not None:
                lines.append(f"{label}: {data[k]}")
        if data.get("pros"):
            lines.append(f"Strengths: {', '.join(data['pros'])}")
        if data.get("cons"):
            lines.append(f"Concerns: {', '.join(data['cons'])}")
        return "\n".join(lines)


_service = None
def get_screener_in_service() -> ScreenerInService:
    global _service
    if _service is None:
        _service = ScreenerInService()
    return _service
