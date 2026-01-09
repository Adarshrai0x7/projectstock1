package com.example.stockscreener.network

import com.example.stockscreener.network.models.MarketOverviewResponse
import com.example.stockscreener.network.models.Stock
import com.example.stockscreener.network.models.StockApiResponse
import com.example.stockscreener.network.models.StockHistoryResponse
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.engine.android.Android
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

object StockApiService {

    // 🔴 IMPORTANT: Use 10.0.2.2 for Emulator, or your PC IP for Physical Device
    private const val BASE_URL = "http://10.0.2.2:8000"

    private val client = HttpClient(Android) {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                isLenient = true
                coerceInputValues = true
            })
        }
    }
    suspend fun getTrendingStocks(): StockApiResponse {
        return try {
            val response = client.get("$BASE_URL/api/market/trending").body<StockApiResponse>()
            response
        } catch (e: Exception) {
            StockApiResponse(emptyList(), "Error")
        }
    }
    suspend fun getMarketOverview(symbols: List<String>): MarketOverviewResponse {
        return try {
            // ✅ FIX 1: Updated URL to match new backend structure
            // Old: /api/market-overview
            // New: /api/market/overview
            client.get("$BASE_URL/api/market/overview") {
                symbols.forEach { parameter("symbols", it) }
            }.body()
        } catch (e: Exception) {
            android.util.Log.e("StockApi", "Indices Error: ${e.message}")
            MarketOverviewResponse(emptyList(), "Error")
        }
    }

    suspend fun getTopGainers(): StockApiResponse {
        return try {
            // This was already correct!
            val response = client.get("$BASE_URL/api/market/gainers").body<StockApiResponse>()
            android.util.Log.d("StockApi", "Gainers fetched: ${response.data.size}")
            response
        } catch (e: Exception) {
            android.util.Log.e("StockApi", "Gainers Error: ${e.message}")
            StockApiResponse(emptyList(), "Error")
        }
    }

    suspend fun getTopLosers(): StockApiResponse {
        return try {
            // This was already correct!
            client.get("$BASE_URL/api/market/losers").body()
        } catch (e: Exception) {
            android.util.Log.e("StockApi", "Losers Error: ${e.message}")
            StockApiResponse(emptyList(), "Error")
        }
    }
    suspend fun searchStocks(query: String): List<Stock> {
        if (query.length < 2) return emptyList() // Optimization: Don't search for "A"

        return try {
            // Calls: GET http://10.0.2.2:8000/api/search?q=TATA
            val response = client.get("$BASE_URL/api/search") {
                parameter("q", query)
            }.body<SearchResponseWrapper>()

            response.results
        } catch (e: Exception) {
            android.util.Log.e("StockApi", "Search Error: ${e.message}")
            emptyList()
        }
    }

    suspend fun getStockHistory(symbol: String): StockHistoryResponse {
        return try {
            // ✅ FIX 2: Updated URL structure for Stock Details
            // Old: /api/stock?symbol=RELIANCE.NS
            // New: /api/stock/RELIANCE.NS (Symbol is now part of the path)
            client.get("$BASE_URL/api/stock/$symbol") {
                parameter("period", "1mo")
                parameter("interval", "1d")
            }.body()
        } catch (e: Exception) {
            StockHistoryResponse(emptyList())
        }
    }
    @Serializable
    data class SearchResponseWrapper(
        val results: List<Stock>
    )
}