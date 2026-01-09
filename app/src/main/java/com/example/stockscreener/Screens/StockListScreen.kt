package com.example.stockscreener.Screens


import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.example.stockscreener.ui.theme.ModernStockTheme
import com.example.stockscreener.viewmodels.HomeScreenViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StockListScreen(
    navController: NavController,
    listType: String, // "popular", "gainers", or "losers"
    viewModel: HomeScreenViewModel
) {
    val uiState by viewModel.uiState

    // 1. Decide which list to show based on the "type" passed from navigation
    val (title, stockList) = when (listType) {
        "gainers" -> "🔥 Top Gainers" to uiState.topGainers
        "losers" -> "🔻 Top Losers" to uiState.topLosers
        "popular" -> "⭐ Popular Stocks" to uiState.popularStocks
        else -> "Stocks" to emptyList()
    }

    ModernStockTheme {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text(title, fontWeight = FontWeight.Bold) },
                    navigationIcon = {
                        IconButton(onClick = { navController.popBackStack() }) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = MaterialTheme.colorScheme.background
                    )
                )
            }
        ) { padding ->
            // 2. Show the FULL LIST
            if (stockList.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = androidx.compose.ui.Alignment.Center) {
                    Text("No stocks found.")
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(horizontal = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    contentPadding = PaddingValues(top = 16.dp, bottom = 16.dp)
                ) {
                    items(stockList) { stock ->
                        // Re-using the StockCard from your HomeScreen
                        // Note: If 'StockCard' is not found, copy it from HomeScreen.kt to here
                        StockCard(
                            stock = stock,
                            onClick = { navController.navigate("stockDetail/${stock.name}") }
                        )
                    }
                }
            }
        }
    }
}