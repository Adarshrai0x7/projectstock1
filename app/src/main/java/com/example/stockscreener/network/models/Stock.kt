package com.example.stockscreener.network.models

import kotlinx.serialization.Serializable

/**
 * Matches the /api/market-overview response
 */
@Serializable
data class MarketOverviewResponse(
    val data: List<Stock>,
    val source: String? = null
)

/**
 * Matches the /api/stock (historical chart) response
 */
@Serializable
data class StockHistoryResponse(
    val data: List<StockCandle>,
    val source: String? = null,
    val symbol: String? = null
)

/**
 * Matches the /api/market/gainers and /api/market/losers response
 */
@Serializable
data class StockApiResponse(
    val data: List<Stock>,
    val source: String? = null
)

/**
 * ✅ UPDATED CORE MODEL
 * Works for both Market Data (Price/Change) and Search Results (Symbol/Exchange)
 */
@Serializable
data class Stock(
    val name: String,                 // Market API: "RELIANCE.NS" | Search API: "Reliance Industries"
    val symbol: String? = null,       // Search API: "RELIANCE.NS" (Nullable because Market API doesn't send it)
    val price: Double = 0.0,          // Default 0.0 prevents crash during Search
    val change: Double = 0.0,         // Default 0.0 prevents crash during Search
    val isPositive: Boolean = false,
    val exchange: String? = null      // Search API: "NSE" or "BSE"
) {
    // Helper: Smartly get the Ticker ID (Use symbol if available, else name)
    // This fixes the issue where different APIs send the ID in different fields
    fun getTicker(): String {
        return symbol ?: name
    }
}

/**
 * Model for Chart Data
 */
@Serializable
data class StockCandle(
    val datetime: String = "",       // ✅ Default to empty string
    val open: Double = 0.0,          // ✅ Default to 0.0
    val high: Double = 0.0,
    val low: Double = 0.0,
    val close: Double = 0.0,
    val volume: Double? = 0.0
)