"""
Market Data Tool for Trader Team.

Provides access to market data, price information, and basic financial metrics.
Note: This is a simplified implementation for the S2 system.
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ..base_tool import BaseTool, ToolResult, ToolStatus, ToolParameter, ToolExecutionContext


class MarketDataTool(BaseTool):
    """
    Tool for accessing market data and financial information.
    
    Provides simulated market data for trading analysis and decision making.
    In a production environment, this would connect to real market data APIs.
    """
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="symbol",
                type="string",
                description="Stock or crypto symbol (e.g., AAPL, BTC, ETH)",
                required=True
            ),
            ToolParameter(
                name="timeframe",
                type="string", 
                description="Data timeframe",
                required=False,
                default="1d",
                enum=["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Number of data points to return",
                required=False,
                default=50
            )
        ]
        
        super().__init__(
            name="market_data",
            description="Get market data for stocks, crypto, or other financial instruments",
            parameters=parameters,
            timeout=15.0
        )
    
    async def execute(
        self,
        context: ToolExecutionContext,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 50,
        **kwargs
    ) -> ToolResult:
        """Execute market data retrieval"""
        
        try:
            # Simulate API call delay
            await asyncio.sleep(0.5)
            
            # Generate simulated market data
            data = self._generate_market_data(symbol, timeframe, limit)
            
            # Add market analysis
            analysis = self._analyze_market_data(data)
            
            result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "data_points": len(data["prices"]),
                "current_price": data["current_price"],
                "price_change_24h": data["price_change_24h"],
                "volume_24h": data["volume_24h"],
                "market_cap": data.get("market_cap"),
                "prices": data["prices"][-10:],  # Last 10 data points
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
            return ToolResult(
                success=True,
                status=ToolStatus.SUCCESS,
                result=result,
                metadata={
                    "tool": "market_data",
                    "symbol": symbol,
                    "data_source": "simulated"
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                status=ToolStatus.FAILED,
                error_message=f"Failed to retrieve market data: {str(e)}"
            )
    
    def _generate_market_data(self, symbol: str, timeframe: str, limit: int) -> Dict[str, Any]:
        """Generate simulated market data"""
        
        # Base prices for common symbols
        base_prices = {
            "BTC": 45000,
            "ETH": 3000,
            "AAPL": 180,
            "GOOGL": 140,
            "TSLA": 250,
            "SPY": 420,
            "QQQ": 350
        }
        
        base_price = base_prices.get(symbol.upper(), 100)
        
        # Generate price series with some volatility
        prices = []
        current_price = base_price
        
        for i in range(limit):
            # Random walk with slight upward bias
            change_percent = random.gauss(0.001, 0.02)  # Small positive bias, 2% volatility
            current_price *= (1 + change_percent)
            current_price = max(current_price, base_price * 0.5)  # Floor at 50% of base
            
            timestamp = datetime.now() - timedelta(hours=limit - i)
            
            prices.append({
                "timestamp": timestamp.isoformat(),
                "price": round(current_price, 2),
                "volume": random.randint(1000000, 10000000)
            })
        
        # Calculate metrics
        first_price = prices[0]["price"]
        last_price = prices[-1]["price"]
        price_change_24h = ((last_price - first_price) / first_price) * 100
        
        total_volume = sum(p["volume"] for p in prices[-24:])  # Last 24 periods
        
        return {
            "prices": prices,
            "current_price": last_price,
            "price_change_24h": round(price_change_24h, 2),
            "volume_24h": total_volume,
            "market_cap": int(last_price * random.randint(1000000, 100000000)) if symbol.upper() in ["BTC", "ETH"] else None
        }
    
    def _analyze_market_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform basic technical analysis on market data"""
        
        prices = [p["price"] for p in data["prices"]]
        
        if len(prices) < 10:
            return {"error": "Insufficient data for analysis"}
        
        # Simple moving averages
        sma_10 = sum(prices[-10:]) / 10
        sma_20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else None
        
        current_price = prices[-1]
        
        # Trend analysis
        short_trend = "bullish" if current_price > sma_10 else "bearish"
        long_trend = "bullish" if (sma_20 and current_price > sma_20) else "bearish" if sma_20 else "neutral"
        
        # Volatility (standard deviation of last 10 prices)
        if len(prices) >= 10:
            recent_prices = prices[-10:]
            avg_price = sum(recent_prices) / len(recent_prices)
            variance = sum((p - avg_price) ** 2 for p in recent_prices) / len(recent_prices)
            volatility = (variance ** 0.5) / avg_price * 100
        else:
            volatility = 0
        
        # Support and resistance levels (simplified)
        recent_prices = prices[-20:] if len(prices) >= 20 else prices
        support_level = min(recent_prices)
        resistance_level = max(recent_prices)
        
        return {
            "sma_10": round(sma_10, 2),
            "sma_20": round(sma_20, 2) if sma_20 else None,
            "short_term_trend": short_trend,
            "long_term_trend": long_trend,
            "volatility_percent": round(volatility, 2),
            "support_level": round(support_level, 2),
            "resistance_level": round(resistance_level, 2),
            "recommendation": self._get_trading_recommendation(
                current_price, sma_10, sma_20, volatility, data["price_change_24h"]
            )
        }
    
    def _get_trading_recommendation(
        self,
        current_price: float,
        sma_10: float,
        sma_20: float,
        volatility: float,
        price_change_24h: float
    ) -> str:
        """Generate a simple trading recommendation"""
        
        # Simple rule-based recommendation
        if current_price > sma_10 and (not sma_20 or current_price > sma_20):
            if volatility < 5 and price_change_24h > 0:
                return "Strong Buy"
            elif price_change_24h > 2:
                return "Buy"
            else:
                return "Hold"
        elif current_price < sma_10 and (sma_20 and current_price < sma_20):
            if price_change_24h < -5:
                return "Strong Sell"
            elif price_change_24h < -2:
                return "Sell"
            else:
                return "Hold"
        else:
            return "Hold"


# Register the tool
from ..tool_catalog import register_tool

register_tool(
    MarketDataTool,
    category="financial",
    team_types=["trader"],
    priority=10
)