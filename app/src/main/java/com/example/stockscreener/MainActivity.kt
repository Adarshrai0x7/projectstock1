package com.example.stockscreener

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.navigation.compose.rememberNavController
import com.example.stockscreener.Screens.AppNavigation
import com.example.stockscreener.Screens.HomeScreen
import com.example.stockscreener.Screens.SearchScreen
import com.example.stockscreener.Screens.StockDetailScreen
import com.example.stockscreener.ui.theme.StockscreenerTheme
import com.google.firebase.FirebaseApp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // ✅ Initialize Firebase
        FirebaseApp.initializeApp(this)
        enableEdgeToEdge()

        // CORRECT
        setContent {
            StockscreenerTheme {
                val navController = rememberNavController()
                StockDetailScreen(
                    symbol = "RELIANCE.NS",
                    navController = navController
                )
            }}

    }
}
