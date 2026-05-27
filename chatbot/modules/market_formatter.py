"""
Response formatting for market data.
Converts raw data into beautiful, conversational responses.
"""

from typing import Optional
from common.models.schemas import StockPrice, IndexData, StockDetails, StockHistory, Market


class MarketFormatter:
    """
    Format market data into user-friendly responses.
    Uses emojis and clear formatting for better readability.
    """
    
    @staticmethod
    def _get_change_indicators(change: float) -> tuple[str, str, str]:
        """Return (trend_emoji, color_emoji, sign) based on change value."""
        if change > 0:
            return "📈", "🟢", "+"
        elif change < 0:
            return "📉", "🔴", ""
        return "⚪", "⚪", ""

    @staticmethod
    def format_price(price: float, currency: str = "₹") -> str:
        """Format price with currency symbol and thousand separators."""
        if price >= 10000000:  # 1 Crore
            return f"{currency}{price/10000000:.2f} Cr"
        elif price >= 100000:  # 1 Lakh  
            return f"{currency}{price/100000:.2f} L"
        else:
            return f"{currency}{price:,.2f}"
    
    @staticmethod
    def format_change(change: float, change_percent: float) -> str:
        """Format price change with emoji indicator."""
        _, color, sign = MarketFormatter._get_change_indicators(change)
        return f"{color} {sign}₹{abs(change):.2f} ({sign}{change_percent:.2f}%)"
    
    @staticmethod
    def format_stock_price(stock: StockPrice) -> str:
        """Format stock price into a conversational response."""
        trend, color, sign = MarketFormatter._get_change_indicators(stock.change)
        
        response = f"""**{stock.name or stock.symbol}** ({stock.symbol}) {trend}

💰 **Current Price:** ₹{stock.price:,.2f}
{color} **Change:** {sign}₹{abs(stock.change):.2f} ({sign}{stock.change_percent:.2f}%)"""
        
        # Add day's range if available
        if stock.high and stock.low:
            response += f"\n📊 **Day's Range:** ₹{stock.low:,.2f} - ₹{stock.high:,.2f}"
        
        # Add volume if available
        if stock.volume:
            vol_formatted = MarketFormatter._format_volume(stock.volume)
            response += f"\n📦 **Volume:** {vol_formatted}"
        
        return response
    
    @staticmethod
    def format_index(index: IndexData) -> str:
        """Format index data into a conversational response."""
        trend, color, sign = MarketFormatter._get_change_indicators(index.change)
        
        return f"""**{index.name}** {trend}

🎯 **Current Value:** {index.value:,.2f}
{color} **Change:** {sign}{abs(index.change):.2f} ({sign}{index.change_percent:.2f}%)"""
    
    @staticmethod
    def format_stock_details(details: StockDetails, price: Optional[StockPrice] = None) -> str:
        """Format detailed stock information."""
        response = f"**{details.name}** ({details.symbol}) 📊\n\n"
        
        if details.sector:
            response += f"🏢 **Sector:** {details.sector}\n"
        
        if details.industry:
            response += f"🏭 **Industry:** {details.industry}\n"
        
        if details.market_cap:
            response += f"💎 **Market Cap:** {MarketFormatter.format_price(details.market_cap)}\n"
        
        if details.pe_ratio:
            response += f"📈 **P/E Ratio:** {details.pe_ratio:.2f}\n"
        
        if details.eps:
            response += f"💵 **EPS:** ₹{details.eps:.2f}\n"
        
        if details.dividend_yield:
            response += f"🎁 **Dividend Yield:** {details.dividend_yield*100:.2f}%\n"
        
        if details.week_52_high and details.week_52_low:
            response += f"📅 **52-Week Range:** ₹{details.week_52_low:,.2f} - ₹{details.week_52_high:,.2f}\n"
        
        if details.description:
            # Truncate long descriptions
            desc = details.description[:300] + "..." if len(details.description) > 300 else details.description
            response += f"\n📝 **About:** {desc}"
        
        return response
    
    @staticmethod
    def format_market_summary(indices: dict) -> str:
        """Format overall market summary."""
        response = "📊 **Market Summary**\n\n"
        
        for name, index in indices.items():
            _, color, sign = MarketFormatter._get_change_indicators(index.change)
            response += f"**{name}:** {index.value:,.2f} {color} {sign}{index.change_percent:.2f}%\n"
        
        return response
    
    @staticmethod
    def format_quick_price(stock: StockPrice) -> str:
        """Format a quick one-line price response."""
        _, color, sign = MarketFormatter._get_change_indicators(stock.change)
        return f"{stock.symbol}: ₹{stock.price:,.2f} {color} {sign}{stock.change_percent:.2f}%"
    
    @staticmethod
    def _format_volume(volume: int) -> str:
        """Format volume with appropriate suffix."""
        if volume >= 10000000:
            return f"{volume/10000000:.2f} Cr"
        elif volume >= 100000:
            return f"{volume/100000:.2f} L"
        elif volume >= 1000:
            return f"{volume/1000:.1f}K"
        return str(volume)
    
    @staticmethod
    def format_error(symbol: str, error_type: str = "not_found") -> str:
        """Format error messages."""
        messages = {
            "not_found": f"❓ Sorry, I couldn't find data for **{symbol}**. Please check the symbol and try again.",
            "market_closed": f"🌙 Markets are currently closed. Showing last available price for **{symbol}**.",
            "timeout": "⏱️ The request timed out. Please try again in a moment.",
            "history_unavailable": f"📊 Sorry, I couldn't fetch historical data for **{symbol}**. The stock might be newly listed or data is temporarily unavailable."
        }
        return messages.get(error_type, f"⚠️ There was an error fetching data for **{symbol}**. Please try again.")
    
    @staticmethod
    def format_stock_history(history: StockHistory) -> str:
        """Format historical stock data into a readable table."""
        currency = "$" if history.market == Market.US else "₹"
        name_display = f"{history.name} ({history.symbol})" if history.name else history.symbol
        days_count = len(history.days)
        
        lines = [f"📊 **{name_display}** — Last {days_count} Trading Days\n"]
        
        for day in history.days:
            if day.change_percent is not None:
                _, color, sign = MarketFormatter._get_change_indicators(day.change_percent)
                change_str = f"{color} {sign}{day.change_percent:.2f}%"
            else:
                change_str = "—"
            
            try:
                from datetime import datetime
                dt = datetime.strptime(day.date, '%Y-%m-%d')
                date_str = dt.strftime('%b %d')
            except Exception:
                date_str = day.date
            
            lines.append(f"📅 **{date_str}**: {currency}{day.close:,.2f}  {change_str}")
        
        if history.overall_change_percent is not None:
            _, color, sign = MarketFormatter._get_change_indicators(history.overall_change_percent)
            overall = f"{color} {sign}{history.overall_change_percent:.2f}%"
            lines.append(f"\n**Overall Change**: {overall} over {days_count} days")
        
        market_label = "US Market" if history.market == Market.US else "NSE"
        lines.append(f"\n_Source: {market_label} via yfinance_")
        
        return "\n".join(lines)
