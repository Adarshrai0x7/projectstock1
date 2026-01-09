package com.example.stockscreener.Screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
// 🔴 IMPORTANT IMPORTS FOR 'by' keyword
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.example.stockscreener.network.StockApiService
import com.example.stockscreener.network.models.Stock
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

// --- MAIN SEARCH SCREEN ---

@Composable
fun SearchScreen(navController: NavController) {
    var searchQuery by remember { mutableStateOf("") }
    val isSearching by remember { derivedStateOf { searchQuery.isNotBlank() } }

    val filterOptions = listOf("Stocks", "Funds", "Crypto")
    var selectedFilter by remember { mutableStateOf(filterOptions.first()) }

    var apiResults by remember { mutableStateOf<List<Stock>>(emptyList()) }
    var isLoading by remember { mutableStateOf(false) }

    // Use 'by' so this is a real List<String>, not a State object
    var recentSearches by remember { mutableStateOf(listOf("TCS.NS", "RELIANCE.NS")) }
    val trendingSearches = listOf("Nifty 50", "Gold", "Adani", "Tata Motors")

    LaunchedEffect(searchQuery) {
        if (searchQuery.length >= 2) {
            isLoading = true
            delay(400) // Debounce
            val results = StockApiService.searchStocks(searchQuery)
            apiResults = results
            isLoading = false
        } else {
            apiResults = emptyList()
        }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            SearchTopAppBar(
                searchQuery = searchQuery,
                onQueryChange = { searchQuery = it },
                onNavigateBack = { navController.popBackStack() }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize()) {

            FilterChipSection(
                options = filterOptions,
                selectedOption = selectedFilter,
                onOptionSelected = { selectedFilter = it }
            )

            if (isSearching) {
                if (isLoading) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                } else {
                    SearchResultsList(
                        results = apiResults,
                        onItemClick = { stock ->
                            // ✅ FIX 1: Use safe ticker (Name fallback if symbol is missing)
                            val safeTicker = stock.symbol ?: stock.name

                            // Add to local history safely
                            if (!recentSearches.contains(safeTicker)) {
                                recentSearches = listOf(safeTicker) + recentSearches.take(4)
                            }
                            // Navigate safely
                            navController.navigate("stockDetail/$safeTicker")
                        }
                    )
                }
            } else {
                InitialSearchView(
                    recent = recentSearches,
                    trending = trendingSearches,
                    onSuggestionClick = { suggestion ->
                        searchQuery = suggestion
                    }
                )
            }
        }
    }
}

// --- UI COMPONENTS ---

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SearchTopAppBar(
    searchQuery: String,
    onQueryChange: (String) -> Unit,
    onNavigateBack: () -> Unit
) {
    val focusRequester = remember { FocusRequester() }
    val keyboardController = LocalSoftwareKeyboardController.current

    LaunchedEffect(Unit) { focusRequester.requestFocus() }

    TopAppBar(
        title = {
            TextField(
                value = searchQuery,
                onValueChange = onQueryChange,
                modifier = Modifier.fillMaxWidth().focusRequester(focusRequester),
                placeholder = { Text("Search stocks (e.g. RELIANCE)...") },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { onQueryChange("") }) {
                            Icon(Icons.Default.Clear, contentDescription = "Clear")
                        }
                    } else {
                        Icon(Icons.Default.Search, contentDescription = null)
                    }
                },
                singleLine = true,
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                ),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                keyboardActions = KeyboardActions(onSearch = { keyboardController?.hide() })
            )
        },
        navigationIcon = {
            IconButton(onClick = onNavigateBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun FilterChipSection(
    options: List<String>,
    selectedOption: String,
    onOptionSelected: (String) -> Unit
) {
    LazyRow(
        modifier = Modifier.background(MaterialTheme.colorScheme.background),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(options) { option ->
            FilterChip(
                selected = option == selectedOption,
                onClick = { onOptionSelected(option) },
                label = { Text(option) },
                shape = CircleShape
            )
        }
    }
}

@Composable
private fun InitialSearchView(
    recent: List<String>,
    trending: List<String>,
    onSuggestionClick: (String) -> Unit
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(vertical = 16.dp)
    ) {
        if(recent.isNotEmpty()) {
            item {
                Text(
                    "Recent Searches",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                )
            }
            items(recent) { item ->
                SearchSuggestionRow(text = item, icon = Icons.Default.History) {
                    onSuggestionClick(item)
                }
            }
        }

        item {
            Spacer(Modifier.height(24.dp))
            Text(
                "Trending Searches",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            )
        }
        items(trending) { item ->
            SearchSuggestionRow(text = item, icon = Icons.Default.LocalFireDepartment) {
                onSuggestionClick(item)
            }
        }
    }
}

@Composable
private fun SearchResultsList(results: List<Stock>, onItemClick: (Stock) -> Unit) {
    if (results.isEmpty()) {
        Box(Modifier.fillMaxSize().padding(16.dp), contentAlignment = Alignment.Center) {
            Text("No results found.", color = Color.Gray)
        }
    } else {
        LazyColumn(modifier = Modifier.fillMaxSize()) {
            items(results) { stock ->
                SearchResultRow(stock = stock) { onItemClick(stock) }
            }
        }
    }
}

@Composable
private fun SearchSuggestionRow(
    text: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick).padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
        Spacer(Modifier.width(16.dp))
        Text(text, fontSize = 16.sp)
    }
}

@Composable
private fun SearchResultRow(stock: Stock, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable { onClick() }.padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(Modifier.weight(1f)) {
            // ✅ FIX 2: Text cannot be null. Use Elvis operator (?:)
            Text(
                text = stock.symbol ?: stock.name,
                fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.titleMedium
            )
            Text(
                text = stock.name,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
        }

        // ✅ FIX 3: Safe call (?.) for nullable string
        val tag = if (stock.symbol?.contains(".NS") == true) "NSE" else "BSE"

        Text(
            text = tag,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier
                .background(
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f),
                    shape = RoundedCornerShape(4.dp)
                )
                .padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
    HorizontalDivider(modifier = Modifier.padding(start = 16.dp), thickness = 0.5.dp, color = Color.Gray.copy(alpha = 0.3f))
}