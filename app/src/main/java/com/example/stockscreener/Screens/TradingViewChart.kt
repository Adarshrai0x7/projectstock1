package com.example.stockscreener.Screens

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import com.example.stockscreener.network.models.StockCandle
import com.tradingview.lightweightcharts.api.chart.models.color.IntColor
import com.tradingview.lightweightcharts.api.options.models.CandlestickSeriesOptions
import com.tradingview.lightweightcharts.api.options.models.crosshairOptions
import com.tradingview.lightweightcharts.api.options.models.gridLineOptions
import com.tradingview.lightweightcharts.api.options.models.gridOptions
import com.tradingview.lightweightcharts.api.options.models.layoutOptions
import com.tradingview.lightweightcharts.api.options.models.priceScaleOptions
import com.tradingview.lightweightcharts.api.options.models.timeScaleOptions
import com.tradingview.lightweightcharts.api.series.models.CandlestickData
import com.tradingview.lightweightcharts.api.series.models.Time
import com.tradingview.lightweightcharts.view.ChartsView
import android.graphics.Color as AndroidColor

@Composable
fun TradingViewChart(
    data: List<StockCandle>,
    modifier: Modifier = Modifier
) {
    AndroidView(
        modifier = modifier.fillMaxSize(),
        factory = { context ->
            ChartsView(context).apply {
                // 1. Setup the Chart Style
                api.applyOptions {
                    // ... inside api.applyOptions ...

                    layout = layoutOptions {
                        // 🔴 FIX: Wrap standard Android colors in IntColor()
                        backgroundColor = IntColor(AndroidColor.WHITE)
                        textColor = IntColor(AndroidColor.BLACK)
                    }

                    grid = gridOptions {
                        vertLines = gridLineOptions {
                            // 🔴 FIX: Wrap parsed color in IntColor()
                            color = IntColor(AndroidColor.parseColor("#E1E1E1"))
                        }
                        horzLines = gridLineOptions {
                            // 🔴 FIX: Wrap parsed color in IntColor()
                            color = IntColor(AndroidColor.parseColor("#E1E1E1"))
                        }
                    }
                    crosshair = crosshairOptions {
                        // Enable the crosshair (the lines that follow your finger)
                        vertLine = com.tradingview.lightweightcharts.api.options.models.crosshairLineOptions {
                            visible = true
                            labelVisible = true
                        }
                        horzLine = com.tradingview.lightweightcharts.api.options.models.crosshairLineOptions {
                            visible = true
                            labelVisible = true
                        }
                    }
                    timeScale = timeScaleOptions {
                        fixLeftEdge = true
                        borderVisible = false
                    }
                    priceScale = priceScaleOptions {
                        borderVisible = false
                    }
                }

                // 2. Add the Candlestick Series
                api.addCandlestickSeries(
                    // ... inside api.addCandlestickSeries ...

                    options = CandlestickSeriesOptions(
                        upColor = IntColor(AndroidColor.parseColor("#00C853")),     // ✅ Wrapped in IntColor
                        downColor = IntColor(AndroidColor.parseColor("#D50000")),   // ✅ Wrapped in IntColor
                        borderUpColor = IntColor(AndroidColor.parseColor("#00C853")),
                        borderDownColor = IntColor(AndroidColor.parseColor("#D50000")),
                        wickUpColor = IntColor(AndroidColor.parseColor("#00C853")),
                        wickDownColor = IntColor(AndroidColor.parseColor("#D50000"))
                    ),
                    onSeriesCreated = { series ->
                        // 3. Convert API Data to TradingView Data
                        val chartData = data.map { candle ->
                            CandlestickData(
                                time = Time.StringTime(candle.datetime), // "2023-10-25"
                                open = candle.open.toFloat(),
                                high = candle.high.toFloat(),
                                low = candle.low.toFloat(),
                                close = candle.close.toFloat()
                            )
                        }
                        series.setData(chartData)
                    }
                )
            }
        },
        // Re-update if data changes
        update = { chartView ->
            // Logic to update data if needed (for live trading)
        }
    )
}