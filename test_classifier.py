import logging
logging.basicConfig(level=logging.WARNING)

from chatbot.core.intent_classifier import get_intent_classifier

c = get_intent_classifier()

tests = [
    ("what is the price of TCS", "MARKET_PRICE"),
    ("HDFC share price today", "MARKET_PRICE"),
    ("how is nifty today", "MARKET_TREND"),
    ("top gainers today", "MARKET_TREND"),
    ("latest news for reliance", "NEWS_REQUEST"),
    ("market news today", "NEWS_REQUEST"),
    ("explain intraday trading", "EDUCATION"),
    ("what is RSI indicator", "EDUCATION"),
    ("last 5 days of HDFC", "STOCK_HISTORY"),
    ("how has TCS performed this month", "STOCK_HISTORY"),
    ("show undervalued stocks", "STOCK_SCREEN"),
    ("analyze Reliance", "STOCK_SCREEN"),
    ("hi", "GREETING"),
    ("good morning", "GREETING"),
    ("how do I place a limit order", "TRADING_HOW_TO"),
    ("how to buy a stock", "TRADING_HOW_TO"),
    ("show my portfolio", "PORTFOLIO_QUERY"),
    ("my holdings", "PORTFOLIO_QUERY"),
    ("tell me about TCS company", "STOCK_INFO"),
    ("PE ratio of Reliance", "STOCK_INFO"),
]

passed = 0
failed = []
for q, expected in tests:
    intent, conf = c.classify(q)
    ok = intent.value == expected
    passed += ok
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] [{conf:.2f}] {q!r} => {intent.value} (expected {expected})")
    if not ok:
        failed.append((q, expected, intent.value, conf))

print(f"\n{passed}/{len(tests)} passed")
if failed:
    print("\nFailed cases:")
    for q, exp, got, conf in failed:
        print(f"  '{q}' expected={exp} got={got} conf={conf:.2f}")


# =============================================================================
# ENTITY EXTRACTION SMOKE TESTS
# =============================================================================
print("\n" + "="*60)
print("ENTITY EXTRACTION SMOKE TESTS")
print("="*60)

from chatbot.core.entity_extractor import get_entity_extractor

e = get_entity_extractor()

entity_tests = [
    # (query, expected_symbols_contain, should_be_empty)
    # --- Fuzzy matching: typos should resolve ---
    ("reliace share price",         ["RELIANCE"],   False),
    ("infossys pe ratio",           ["INFY"],       False),
    ("tata moters stock",           ["TATAMOTORS"], False),
    ("wipro stock",                 ["WIPRO"],      False),
    # --- False-positive prevention: no stock should be extracted ---
    ("explain stop loss",           [],             True),
    ("best performing stocks today",[], True),
    ("what is RSI indicator",       [],             True),
    ("show me the latest results",  [],             True),
    ("how to analyse a stock",      [],             True),
    # --- Exact match still works ---
    ("price of TCS",                ["TCS"],        False),
    ("HDFCBANK share price",        ["HDFCBANK"],   False),
    ("Reliance industries news",    ["RELIANCE"],   False),
]

ep, ef = 0, []
for query, expected_symbols, expect_empty in entity_tests:
    result = e.extract(query)
    symbols = result.stock_symbols

    if expect_empty:
        ok = len(symbols) == 0
    else:
        ok = all(s in symbols for s in expected_symbols)

    ep += ok
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] '{query}' => {symbols} (expected {'empty' if expect_empty else expected_symbols})")
    if not ok:
        ef.append((query, expected_symbols if not expect_empty else [], symbols))

print(f"\n{ep}/{len(entity_tests)} passed")
if ef:
    print("\nFailed entity cases:")
    for q, exp, got in ef:
        print(f"  '{q}' expected={exp} got={got}")
