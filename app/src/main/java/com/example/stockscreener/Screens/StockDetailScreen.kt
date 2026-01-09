package com.example.stockscreener.Screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.example.stockscreener.network.models.StockCandle
import com.example.stockscreener.ui.theme.AppColors
import com.example.stockscreener.ui.theme.ModernStockTheme
import com.example.stockscreener.viewmodels.StockDetailViewModel

// ✅ IMPORTANT: Make sure TradingViewChart is in the same package (Screens)
// If it's in a different package, import it here:
// import com.example.stockscreener.Screens.TradingViewChart

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StockDetailScreen(
    symbol: String,
    navController: NavController,
    viewModel: StockDetailViewModel = viewModel()
) {
    val uiState by viewModel.uiState

    LaunchedEffect(key1 = symbol) {
        viewModel.fetchStockHistory(symbol)
    }

    ModernStockTheme {
        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            topBar = {
                TopAppBar(
                    title = {
                        Column {
                            Text(
                                text = symbol.replace(".NS", ""),
                                fontWeight = FontWeight.Bold,
                                style = MaterialTheme.typography.headlineSmall
                            )
                            Text(
                                text = "NSE Equity",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                            )
                        }
                    },
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
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
            ) {
                // --- Handle Loading and Error States ---
                when {
                    uiState.isLoading -> {
                        item {
                            Box(
                                modifier = Modifier
                                    .fillParentMaxSize()
                                    .padding(top = 150.dp),
                                contentAlignment = Alignment.TopCenter
                            ) {
                                CircularProgressIndicator()
                            }
                        }
                    }
                    uiState.error != null -> {
                        item {
                            Text(
                                text = "Failed to load stock data.\nPlease check your connection.",
                                modifier = Modifier
                                    .fillParentMaxWidth()
                                    .padding(48.dp),
                                textAlign = TextAlign.Center,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                            )
                        }
                    }
                    uiState.stockHistory.isNotEmpty() -> {
                        // --- 1. Stock Header ---
                        item {
                            StockDetailHeader(stockHistory = uiState.stockHistory)
                        }

                        // --- 2. TRADINGVIEW CHART SECTION ---
                        item {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(400.dp) // Large height for the chart
                                    .background(Color.White) // Charts look best on White
                            ) {
                                // ✅ Calling the Wrapper we created earlier
                                TradingViewChart(
                                    // ✅ Fix: Force Oldest-First order
                                    data = uiState.stockHistory.sortedBy { it.datetime }
                                )
                            }
                        }

                        // --- 3. Historical Data Table ---
                        item {
                            Text(
                                text = "Historical Data",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(horizontal = 16.dp, vertical = 16.dp)
                            )
                        }

                        // Header Row
                        item {
                            HistoricalDataRow(
                                date = "Date", close = "Close", high = "High", low = "Low", isHeader = true
                            )
                        }

                        // Data Rows (Last 20 days)
                        // Note: If API returns oldest-first, we reverse to show newest at top of table
                        val tableData = if (uiState.stockHistory.first().datetime < uiState.stockHistory.last().datetime) {
                            uiState.stockHistory.reversed()
                        } else {
                            uiState.stockHistory
                        }

                        items(items = tableData.take(20)) { candle ->
                            HistoricalDataRow(
                                date = candle.datetime,
                                close = "%.2f".format(candle.close),
                                high = "%.2f".format(candle.high),
                                low = "%.2f".format(candle.low)
                            )
                        }
                    }
                }
            }
        }
    }
}

// --- EXISTING HELPER COMPONENTS (Header & Table) ---

@Composable
private fun StockDetailHeader(stockHistory: List<StockCandle>) {
    // Logic to find the latest price safely
    // Assuming API sends Oldest -> Newest (Chart standard), so last() is today.
    val latestData = stockHistory.lastOrNull() ?: return
    val previousData = stockHistory.dropLast(1).lastOrNull()

    val price = latestData.close
    val prevPrice = previousData?.close ?: price
    val change = price - prevPrice
    val changePercent = if (prevPrice != 0.0) (change / prevPrice) * 100 else 0.0

    val isPositive = change >= 0
    val trendColor = if (isPositive) AppColors.Positive else AppColors.Negative
    val sign = if (isPositive) "+" else ""

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Text(
            text = "₹${"%.2f".format(price)}",
            style = MaterialTheme.typography.displaySmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = "%s%.2f".format(sign, change),
                color = trendColor,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "(%s%.2f%%)".format(sign, changePercent),
                color = trendColor,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
        }
        Text(
            text = "As of ${latestData.datetime}",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )
    }
}

@Composable
private fun HistoricalDataRow(date: String, close: String, high: String, low: String, isHeader: Boolean = false) {
    val fontWeight = if (isHeader) FontWeight.Bold else FontWeight.Normal
    val textColor = if (isHeader) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.9f)
    val background = if (isHeader) AppColors.SurfaceContainer else Color.Transparent

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(background)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = date, modifier = Modifier.weight(1.2f), fontWeight = fontWeight, color = textColor, fontSize = 14.sp)
        Text(text = close, modifier = Modifier.weight(1f), fontWeight = fontWeight, color = textColor, fontSize = 14.sp, textAlign = TextAlign.End)
        Text(text = high, modifier = Modifier.weight(1f), fontWeight = fontWeight, color = textColor, fontSize = 14.sp, textAlign = TextAlign.End)
        Text(text = low, modifier = Modifier.weight(1f), fontWeight = fontWeight, color = textColor, fontSize = 14.sp, textAlign = TextAlign.End)
    }
    if (!isHeader) {
        HorizontalDivider(thickness = 1.dp, color = MaterialTheme.colorScheme.outline.copy(alpha = 0.5f), modifier = Modifier.padding(horizontal = 16.dp))
    }
}