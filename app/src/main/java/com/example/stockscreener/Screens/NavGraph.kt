package com.example.stockscreener.Screens

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.example.stockscreener.Screens.StockListScreen
import com.example.stockscreener.viewmodels.HomeScreenViewModel

@Composable
fun AppNavigation(navController: NavHostController) {
    // 1. Create the Shared ViewModel HERE so both Home and List screens use the same data
    val homeViewModel: HomeScreenViewModel = viewModel()

    NavHost(navController = navController, startDestination = "login") {

        composable("login") {
            LoginScreen(navController)
        }

        composable("SignUp") {
            SignUp(navController)
        }

        // --- HOME SCREEN ---
        composable("home") {
            // Pass the shared viewModel
            HomeScreen(navController = navController, viewModel = homeViewModel)
        }

        composable("search") {
            SearchScreen(navController)
        }

        // --- NEW: STOCK LIST SCREEN (View More) ---
        composable(
            route = "stockList/{type}",
            arguments = listOf(navArgument("type") { type = NavType.StringType })
        ) { backStackEntry ->
            val type = backStackEntry.arguments?.getString("type") ?: "popular"
            // Reuse the SAME viewModel to show data instantly
            StockListScreen(navController, type, homeViewModel)
        }

        // --- NEW: STOCK DETAIL SCREEN (Chart/History) ---
        composable(
            route = "stockDetail/{symbol}",
            arguments = listOf(navArgument("symbol") { type = NavType.StringType })
        ) { backStackEntry ->
            val symbol = backStackEntry.arguments?.getString("symbol")

            if (symbol != null) {
                StockDetailScreen(symbol = symbol, navController = navController)
            } else {
                navController.popBackStack()
            }
        }
    }
}