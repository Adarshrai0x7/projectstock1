"""
Screener Formatter.
Formats stock analysis and screener results into readable chat responses.
"""

from common.models.schemas import StockAnalysis, ScreenerResult, Market


class ScreenerFormatter:
    """Format screener results for chat display."""
    
    @staticmethod
    def format_analysis(analysis: StockAnalysis) -> str:
        """Format a single stock's full analysis."""
        currency = "$" if analysis.market == Market.US else "₹"
        signal_emoji = {
            "BUY": "🟢 BUY",
            "SELL": "🔴 SELL",
            "HOLD": "🟡 HOLD",
            "NEUTRAL": "⚪ NEUTRAL",
        }
        
        lines = []
        lines.append(f"📊 **{analysis.name or analysis.symbol}** ({analysis.symbol}) — Full Analysis")
        lines.append("")
        
       
        lines.append(f"💰 **Price:** {currency}{analysis.price:,.2f}")
        chg = analysis.change_percent
        chg_icon = "🟢" if chg >= 0 else "🔴"
        lines.append(f"{chg_icon} **Change:** {chg:+.2f}%")
        lines.append(f"🎯 **Signal:** {signal_emoji.get(analysis.signal, analysis.signal)}")
        lines.append(f"📈 **Score:** {analysis.score:.0f}/100")
        lines.append("")
        
     
        tech = analysis.technical
        lines.append("**📉 Technical Analysis**")
        if tech.rsi is not None:
            rsi_tag = ""
            if tech.rsi < 30: rsi_tag = " (Oversold)"
            elif tech.rsi > 70: rsi_tag = " (Overbought)"
            lines.append(f"  • RSI(14): {tech.rsi:.1f}{rsi_tag}")
        if tech.sma_50 is not None:
            pos = "Above ✅" if analysis.price > tech.sma_50 else "Below ❌"
            lines.append(f"  • SMA-50: {currency}{tech.sma_50:,.2f} ({pos})")
        if tech.sma_200 is not None:
            pos = "Above ✅" if analysis.price > tech.sma_200 else "Below ❌"
            lines.append(f"  • SMA-200: {currency}{tech.sma_200:,.2f} ({pos})")
        if tech.macd is not None:
            macd_dir = "Bullish 📈" if (tech.macd_histogram or 0) > 0 else "Bearish 📉"
            lines.append(f"  • MACD: {tech.macd:.2f} ({macd_dir})")
        if tech.bollinger_position is not None:
            lines.append(f"  • Bollinger Position: {tech.bollinger_position:.0%}")
        if tech.supertrend_signal is not None:
            st_icon = "🟢" if tech.supertrend_signal == "BUY" else "🔴"
            lines.append(f"  • Supertrend: {st_icon} {tech.supertrend_signal}")
        if tech.vwap_position is not None:
            vwap_icon = "⬆️" if tech.vwap_position == "BUY" else "⬇️"
            lines.append(f"  • VWAP Pos: {vwap_icon} {tech.vwap_position}")
        if tech.stochastic_k is not None:
            lines.append(f"  • Stoch(%K): {tech.stochastic_k:.1f}")
        if tech.adx is not None:
            trend = "Strong" if tech.adx > 25 else "Weak"
            lines.append(f"  • ADX: {tech.adx:.1f} ({trend})")
        if tech.volume_ratio is not None:
            vol_tag = ""
            if tech.volume_ratio > 1.5: vol_tag = " (High)"
            elif tech.volume_ratio < 0.5: vol_tag = " (Low)"
            lines.append(f"  • Volume: {tech.volume_ratio:.1f}x avg{vol_tag}")
        lines.append("")
        
       
        fund = analysis.fundamental
        lines.append("**📋 Fundamental Analysis**")
        if fund.pe_ratio is not None:
            lines.append(f"  • P/E Ratio: {fund.pe_ratio:.1f}")
        if fund.pb_ratio is not None:
            lines.append(f"  • P/B Ratio: {fund.pb_ratio:.1f}")
        if fund.roe is not None:
            lines.append(f"  • ROE: {fund.roe:.1f}%")
        if fund.eps is not None:
            lines.append(f"  • EPS: {currency}{fund.eps:.2f}")
        if fund.debt_to_equity is not None:
            lines.append(f"  • Debt/Equity: {fund.debt_to_equity:.2f}")
        if fund.dividend_yield is not None:
            lines.append(f"  • Dividend Yield: {fund.dividend_yield:.1f}%")
        if fund.profit_margin is not None:
            lines.append(f"  • Profit Margin: {fund.profit_margin:.1f}%")
        if fund.revenue_growth is not None:
            lines.append(f"  • Revenue Growth: {fund.revenue_growth:+.1f}%")
        if fund.earnings_growth is not None:
            lines.append(f"  • Earnings Growth: {fund.earnings_growth:+.1f}%")
        if fund.institutional_holding is not None:
            lines.append(f"  • Inst. Holding: {fund.institutional_holding:.1f}%")
        if fund.current_ratio is not None:
            lines.append(f"  • Current Ratio: {fund.current_ratio:.2f}")
        if fund.quick_ratio is not None:
            lines.append(f"  • Quick Ratio: {fund.quick_ratio:.2f}")
        if fund.peg_ratio is not None:
            lines.append(f"  • PEG Ratio: {fund.peg_ratio:.2f}")
        if fund.market_cap is not None:
            lines.append(f"  • Market Cap: {ScreenerFormatter._format_market_cap(fund.market_cap, currency)}")
        if fund.free_cash_flow is not None:
            lines.append(f"  • Free Cash Flow: {currency}{fund.free_cash_flow/1e7:,.0f} Cr")
        if fund.sector:
            lines.append(f"  • Sector: {fund.sector}")
        lines.append("")
        lines.append("_Source: yfinance (technical + fundamental)_")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_screener_result(result: ScreenerResult) -> str:
        """Format screener results as a table."""
        signal_emoji = {
            "BUY": "🟢",
            "SELL": "🔴",
            "HOLD": "🟡",
            "NEUTRAL": "⚪",
        }
        
        lines = []
        lines.append(f"📊 **{result.screen_name}**")
        if result.description:
            lines.append(f"_{result.description}_")
        lines.append("")
        lines.append(f"Scanned **{result.total_scanned}** stocks → **{len(result.stocks)}** matches")
        lines.append("")
        
        if not result.stocks:
            lines.append("No stocks matched the criteria. Try adjusting filters.")
            return "\n".join(lines)
        
        
        for i, stock in enumerate(result.stocks[:15], 1):  
            sig = signal_emoji.get(stock.signal, "⚪")
            currency = "$" if stock.market == Market.US else "₹"
            
            pe_str = f"PE:{stock.fundamental.pe_ratio:.1f}" if stock.fundamental.pe_ratio else ""
            rsi_str = f"RSI:{stock.technical.rsi:.0f}" if stock.technical.rsi else ""
            
            chg = stock.change_percent
            chg_icon = "🟢" if chg >= 0 else "🔴"
            
            lines.append(
                f"**{i}.** {sig} **{stock.symbol}** — "
                f"{currency}{stock.price:,.2f} "
                f"{chg_icon}{chg:+.1f}% | "
                f"Score: {stock.score:.0f} | "
                f"{pe_str} {rsi_str}".strip()
            )
        
        if len(result.stocks) > 15:
            lines.append(f"\n_... and {len(result.stocks) - 15} more_")
        
        lines.append("")
        lines.append("_Source: Nifty 50 via yfinance_")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_market_cap(value: float, currency: str = "₹") -> str:
        """Format market cap in human-readable format."""
        if currency == "₹":
            if value >= 1e12:
                return f"₹{value / 1e12:.1f}L Cr"
            elif value >= 1e7:
                return f"₹{value / 1e7:.0f} Cr"
            else:
                return f"₹{value:,.0f}"
        else:
            if value >= 1e12:
                return f"${value / 1e12:.1f}T"
            elif value >= 1e9:
                return f"${value / 1e9:.1f}B"
            elif value >= 1e6:
                return f"${value / 1e6:.1f}M"
            else:
                return f"${value:,.0f}"
