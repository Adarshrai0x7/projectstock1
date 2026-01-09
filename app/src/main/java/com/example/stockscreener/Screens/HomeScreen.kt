package com.example.stockscreener.Screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.AccountCircle
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.*
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.example.stockscreener.R
import com.example.stockscreener.network.models.Stock
import com.example.stockscreener.ui.theme.AppColors
import com.example.stockscreener.ui.theme.ModernStockTheme
import com.example.stockscreener.viewmodels.HomeScreenUiState
import com.example.stockscreener.viewmodels.HomeScreenViewModel

// --- MAIN SCREEN ---

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(navController: NavController, viewModel: HomeScreenViewModel = viewModel()) {
    val uiState by viewModel.uiState
    var selectedMainTab by remember { mutableIntStateOf(0) }
    var selectedBottomItem by remember { mutableIntStateOf(0) }

    ModernStockTheme {
        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            topBar = {
                TopAppBar(
                    title = { Text("Markets", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.headlineSmall) },
                    actions = {
                        IconButton(onClick = { navController.navigate("search") }) {
                            Icon(Icons.Default.Search, contentDescription = "Search")
                        }
                        IconButton(onClick = { /* Profile logic */ }) {
                            Icon(Icons.Default.AccountCircle, contentDescription = "Profile")
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
                )
            },
            bottomBar = { BottomNavigationBar(selectedItem = selectedBottomItem, onItemSelected = { selectedBottomItem = it }) }
        ) { padding ->
            Column(modifier = Modifier.padding(padding).fillMaxSize()) {
                TabRow(
                    selectedTabIndex = selectedMainTab,
                    containerColor = MaterialTheme.colorScheme.background,
                    indicator = { tabPositions ->
                        TabRowDefaults.SecondaryIndicator(
                            Modifier.tabIndicatorOffset(tabPositions[selectedMainTab]).height(3.dp),
                            color = MaterialTheme.colorScheme.primary
                        )
                    },
                    divider = {}
                ) {
                    Tab(selected = selectedMainTab == 0, onClick = { selectedMainTab = 0 }, text = { Text("Explore", fontWeight = FontWeight.SemiBold) })
                    Tab(selected = selectedMainTab == 1, onClick = { selectedMainTab = 1 }, text = { Text("Watchlists", fontWeight = FontWeight.SemiBold) })
                }
                HorizontalDivider(thickness = 1.dp, color = MaterialTheme.colorScheme.outline.copy(alpha = 0.5f))

                when (selectedMainTab) {
                    0 -> ExploreSection(navController = navController, uiState = uiState)
                    1 -> WatchlistsContainer()
                }
            }
        }
    }
}

// --- EXPLORE SECTION ---

@Composable
fun ExploreSection(navController: NavController, uiState: HomeScreenUiState) {
    LazyColumn(modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 100.dp)) {

        // 1. Overview (Indices)
        item {
            Column(Modifier.background(MaterialTheme.colorScheme.background)) {
                Text("Overview", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, modifier = Modifier.padding(16.dp))
                IndexSection(indices = uiState.marketIndices)
                Spacer(modifier = Modifier.height(24.dp))
            }
        }

        item {
            Column(Modifier.background(AppColors.SurfaceContainer).padding(top = 8.dp)) {

                // 2. Popular Stocks
                SectionHeader(
                    title = "Popular Stocks",
                    onSeeAllClick = { navController.navigate("stockList/popular") }
                )

                if (uiState.popularStocks.isNotEmpty()) {
                    // ✅ StocksGrid now handles navigation
                    StocksGrid(
                        navController = navController,
                        stocks = uiState.popularStocks.take(4)
                    )
                } else {
                    LoadingBox()
                }

                Spacer(modifier = Modifier.height(24.dp))

                // 3. Market Movers (Gainers/Losers)
                MarketMoversSection(
                    navController = navController,
                    gainers = uiState.topGainers,
                    losers = uiState.topLosers
                )
            }
        }

        item {
            TradingScreensSection()
            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

// --- COMPONENTS ---

@Composable
fun IndexSection(indices: List<Stock>) {
    LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        items(indices) { index ->
            Card(
                modifier = Modifier.width(170.dp),
                shape = MaterialTheme.shapes.medium,
                colors = CardDefaults.cardColors(containerColor = AppColors.DarkText),
                elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(text = index.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color.White)
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(text = "₹${String.format("%.2f", index.price)}", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = Color.White)
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = if (index.isPositive) Icons.Default.TrendingUp else Icons.Default.TrendingDown,
                            contentDescription = null,
                            tint = if (index.isPositive) AppColors.Positive else AppColors.Negative,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(text = "${String.format("%.2f", index.change)}%", color = Color.White.copy(alpha = 0.9f), style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
    }
}

@Composable
fun StockCard(stock: Stock, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Card(
        modifier = modifier.clickable(onClick = onClick), // ✅ Click listener is here
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f))
    ) {
        Row(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(text = stock.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, maxLines = 1)
                Text(text = "₹${String.format("%.2f", stock.price)}", style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Bold)
                Text(
                    text = "${if (stock.change > 0) "+" else ""}${String.format("%.2f", stock.change)}%",
                    color = if (stock.isPositive) AppColors.Positive else AppColors.Negative,
                    style = MaterialTheme.typography.labelMedium
                )
            }
            val trendColor = if (stock.isPositive) AppColors.Positive else AppColors.Negative
            Box(Modifier.size(40.dp).clip(CircleShape).background(trendColor.copy(alpha = 0.1f)), contentAlignment = Alignment.Center) {
                Icon(if (stock.isPositive) Icons.Default.TrendingUp else Icons.Default.TrendingDown, null, tint = trendColor, modifier = Modifier.size(24.dp))
            }
        }
    }
}

// --- HELPER: Reusable Grid for 4 items ---
@Composable
fun StocksGrid(navController: NavController, stocks: List<Stock>) {
    Column(modifier = Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        stocks.chunked(2).forEach { rowItems ->
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                rowItems.forEach { stock ->
                    StockCard(
                        stock = stock,
                        modifier = Modifier.weight(1f),
                        onClick = {
                            // ✅ Navigate to Detail Screen using Symbol (e.g., RELIANCE.NS)
                            // Use 'stock.symbol' if available, otherwise 'stock.name' if that holds the ticker
                            navController.navigate("stockDetail/${stock.symbol}")
                        }
                    )
                }
                if (rowItems.size == 1) Spacer(modifier = Modifier.weight(1f))
            }
        }
    }
}

// --- Market Movers Section ---
@Composable
fun MarketMoversSection(navController: NavController, gainers: List<Stock>, losers: List<Stock>) {
    var selectedTab by remember { mutableIntStateOf(0) }

    Column(modifier = Modifier.background(AppColors.SurfaceContainer)) {
        Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text("Market Movers", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            TextButton(onClick = {
                if (selectedTab == 0) navController.navigate("stockList/gainers")
                else navController.navigate("stockList/losers")
            }) {
                Text("VIEW MORE", fontSize = 12.sp)
                Icon(Icons.AutoMirrored.Filled.ArrowForward, null, modifier = Modifier.size(16.dp))
            }
        }

        TabRow(
            selectedTabIndex = selectedTab,
            containerColor = AppColors.SurfaceContainer,
            indicator = { tabPositions ->
                TabRowDefaults.SecondaryIndicator(Modifier.tabIndicatorOffset(tabPositions[selectedTab]), color = AppColors.BluePrimary)
            },
            divider = {}
        ) {
            Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("Top Gainers", fontWeight = if(selectedTab==0) FontWeight.Bold else FontWeight.Normal, color = if(selectedTab==0) AppColors.BluePrimary else Color.Gray) })
            Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Top Losers", fontWeight = if(selectedTab==1) FontWeight.Bold else FontWeight.Normal, color = if(selectedTab==1) AppColors.BluePrimary else Color.Gray) })
        }

        val stocksToShow = if (selectedTab == 0) gainers.take(4) else losers.take(4)

        Spacer(modifier = Modifier.height(16.dp))

        if (stocksToShow.isNotEmpty()) {
            // ✅ Pass navController here too
            StocksGrid(navController, stocksToShow)
        } else {
            LoadingBox()
        }
    }
}

@Composable
fun LoadingBox() {
    Box(Modifier.fillMaxWidth().height(100.dp), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(modifier = Modifier.size(24.dp), color = AppColors.BluePrimary)
    }
}

@Composable
fun WatchlistsContainer() {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Text("Watchlists coming soon", color = Color.Gray)
    }
}

@Composable
fun SectionHeader(title: String, onSeeAllClick: () -> Unit) {
    Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        TextButton(onClick = onSeeAllClick) {
            Text("VIEW MORE", fontSize = 12.sp)
            Icon(Icons.AutoMirrored.Filled.ArrowForward, null, modifier = Modifier.size(16.dp))
        }
    }
}

@Composable
fun TradingScreensSection() {
    val screens = listOf(
        TradingScreen("Resistance breakouts", "Bullish", true, R.drawable.screenshot_2025_11_09_120435),
        TradingScreen("RSI overbought", "Bearish", false, R.drawable.screenshot_2025_11_09_113242)
    )
    Column(modifier = Modifier.padding(16.dp)) {
        Text("Trading Screens", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            screens.forEach { screen -> TradingScreenCard(screen, Modifier.weight(1f)) }
        }
    }
}

data class TradingScreen(val title: String, val type: String, val isBullish: Boolean, val imageResId: Int)

@Composable
fun TradingScreenCard(screen: TradingScreen, modifier: Modifier = Modifier) {
    val labelColor = if (screen.isBullish) AppColors.Positive else AppColors.Negative
    Card(modifier = modifier.height(165.dp), shape = RoundedCornerShape(18.dp)) {
        Box {
            Image(painterResource(screen.imageResId), null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
            Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color.Transparent, Color.Black.copy(0.6f)))))
            Text(screen.type, color = Color.White, modifier = Modifier.padding(12.dp).background(labelColor, RoundedCornerShape(4.dp)).padding(horizontal = 8.dp, vertical = 2.dp))
            Text(screen.title, color = Color.White, fontWeight = FontWeight.Bold, modifier = Modifier.align(Alignment.BottomStart).padding(12.dp))
        }
    }
}

@Composable
fun BottomNavigationBar(selectedItem: Int, onItemSelected: (Int) -> Unit) {
    val items = listOf("Home", "Screener", "Portfolio")
    val icons = listOf(Icons.Outlined.Home, Icons.Outlined.Search, Icons.Outlined.AccountCircle)
    val selectedIcons = listOf(Icons.Filled.Home, Icons.Filled.Search, Icons.Filled.AccountCircle)
    NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
        items.forEachIndexed { index, name ->
            NavigationBarItem(
                selected = selectedItem == index,
                onClick = { onItemSelected(index) },
                icon = { Icon(if (selectedItem == index) selectedIcons[index] else icons[index], name) },
                label = { Text(name) }
            )
        }
    }
}