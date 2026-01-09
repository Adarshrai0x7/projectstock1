package com.example.stockscreener.viewmodels

import androidx.compose.runtime.State
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.stockscreener.network.StockApiService
import com.example.stockscreener.network.models.StockCandle
import kotlinx.coroutines.launch

// Define a state class to hold all UI-related data
data class StockDetailUiState(
    val stockHistory: List<StockCandle> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

class StockDetailViewModel : ViewModel() {

    // Private mutable state that can be changed within the ViewModel
    private val _uiState = mutableStateOf(StockDetailUiState())
    // Public, immutable state that the UI can observe
    val uiState: State<StockDetailUiState> = _uiState

    fun fetchStockHistory(symbol: String) {
        viewModelScope.launch {
            // 1. Start Loading
            _uiState.value = StockDetailUiState(isLoading = true)

            try {
                val response = StockApiService.getStockHistory(symbol)
                val history = response.data

                if (history.isNotEmpty()) {
                    _uiState.value = _uiState.value.copy(
                        // 🔴 CRITICAL FIX: Reverse the list so Index 0 is TODAY
                        stockHistory = history.reversed(),
                        isLoading = false,
                        error = null
                    )
                } else {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = "No data available"
                    )
                }

            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "Failed to fetch data: ${e.localizedMessage}"
                )
            }
        }
    }
}