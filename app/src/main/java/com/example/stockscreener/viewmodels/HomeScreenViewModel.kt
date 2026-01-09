package com.example.stockscreener.viewmodels

import androidx.compose.runtime.State
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.stockscreener.network.models.Stock
import com.example.stockscreener.network.StockApiService
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

// ✅ 1. MODERN INDICES LIST (Global Pulse)
object TickerSymbols {
    val INDICES = listOf(
        "^NSEI",       // Nifty 50 (India)
        "^NSEBANK",    // Bank Nifty (Traders' Favorite)
        "BTC-USD",     // Bitcoin (Crypto)
        // S&P 500 (Global Health)
    )

    // Note: We removed POPULAR_STOCKS because we now fetch them dynamically!
}

data class HomeScreenUiState(
    val isLoading: Boolean = true,
    val marketIndices: List<Stock> = emptyList(),
    val popularStocks: List<Stock> = emptyList(), // This will now hold "Trending" stocks
    val topGainers: List<Stock> = emptyList(),
    val topLosers: List<Stock> = emptyList(),
    val error: String? = null
)

class HomeScreenViewModel : ViewModel() {

    private val _uiState = mutableStateOf(HomeScreenUiState())
    val uiState: State<HomeScreenUiState> = _uiState

    init {
        startMarketDataUpdates()
    }

    private fun startMarketDataUpdates() {
        viewModelScope.launch {
            while (isActive) {
                try {
                    // 1. Fetch ALL data concurrently
                    val indicesDeferred = async { StockApiService.getMarketOverview(TickerSymbols.INDICES) }

                    // ✅ 2. DYNAMIC TRENDING STOCKS
                    // Instead of a hardcoded list, we ask the backend "What is trending?"
                    val popularDeferred = async { StockApiService.getTrendingStocks() }

                    val gainersDeferred = async { StockApiService.getTopGainers() }
                    val losersDeferred = async { StockApiService.getTopLosers() }

                    // 3. Wait for results
                    val indicesResponse = indicesDeferred.await()
                    val popularResponse = popularDeferred.await()
                    val gainersList = gainersDeferred.await().data
                    val losersList = losersDeferred.await().data

                    // 4. Update UI
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        marketIndices = indicesResponse.data,

                        // Now this list updates automatically based on backend Volume!
                        popularStocks = popularResponse.data,

                        topGainers = gainersList.sortedByDescending { it.change },
                        topLosers = losersList.sortedBy { it.change },
                        error = null
                    )

                } catch (e: Exception) {
                    android.util.Log.e("HomeScreenViewModel", "Error fetching data", e)
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = "Connection Error: ${e.localizedMessage}"
                    )
                }

                // 5. Refresh every 15 seconds
                delay(15000)
            }
        }
    }
}