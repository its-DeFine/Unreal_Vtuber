"""
Market Data Tool for Trader Team
================================

Provides real-time and historical market data access for trading analysis.
"""

import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from ..base_tool import BaseTool, ToolResult, ToolParameter, ToolExecutionContext


class MarketDataTool(BaseTool):
    """Tool for accessing market data and price information"""
    
    def __init__(self):
        super().__init__(
            name="market_data_tool",
            description="Access real-time and historical market data for various assets",
            category="trader",
            parameters=[
                ToolParameter(
                    name="symbol",
                    type="string",
                    description="Asset symbol (e.g., AAPL, BTC-USD, EUR/USD)",
                    required=True
                ),
                ToolParameter(
                    name="data_type",
                    type="string", 
                    description="Type of data: price, volume, ohlc, orderbook",
                    required=True
                ),
                ToolParameter(
                    name="timeframe",
                    type="string",
                    description="Timeframe: 1m, 5m, 1h, 1d, 1w",
                    required=False,
                    default="1d"
                ),
                ToolParameter(
                    name="period",
                    type="integer",
                    description="Number of periods to retrieve",
                    required=False,
                    default=30
                )
            ]
        )
        
        # Simulated market data for demonstration
        self.market_data = {
            "AAPL": {"price": 185.50, "volume": 52000000, "change": 1.25},
            "GOOGL": {"price": 142.30, "volume": 28000000, "change": -0.85},
            "BTC-USD": {"price": 43250.00, "volume": 18500000000, "change": 3.45},
            "ETH-USD": {"price": 2280.00, "volume": 8200000000, "change": 2.15},
            "EUR/USD": {"price": 1.0875, "volume": 125000000000, "change": 0.15}
        }
    
    async def execute(self, context: ToolExecutionContext) -> ToolResult:
        """Execute market data retrieval"""
        
        try:
            symbol = context.parameters.get("symbol", "").upper()
            data_type = context.parameters.get("data_type", "price").lower()
            timeframe = context.parameters.get("timeframe", "1d")
            period = context.parameters.get("period", 30)
            
            logging.info(f"📊 [MARKET_DATA] Retrieving {data_type} for {symbol}")
            
            if symbol not in self.market_data:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"Symbol {symbol} not found in available markets"
                )
            
            # Generate appropriate data based on type
            if data_type == "price":
                result = self._get_price_data(symbol)
            elif data_type == "volume":
                result = self._get_volume_data(symbol)
            elif data_type == "ohlc":
                result = self._get_ohlc_data(symbol, timeframe, period)
            elif data_type == "orderbook":
                result = self._get_orderbook_data(symbol)
            else:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"Invalid data type: {data_type}"
                )
            
            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "symbol": symbol,
                    "data_type": data_type,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logging.error(f"❌ [MARKET_DATA] Error: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e)
            )
    
    def _get_price_data(self, symbol: str) -> Dict[str, Any]:
        """Get current price data"""
        base_data = self.market_data[symbol]
        
        # Add some realistic variation
        variation = random.uniform(-0.5, 0.5)
        current_price = base_data["price"] * (1 + variation / 100)
        
        return {
            "symbol": symbol,
            "price": round(current_price, 2),
            "change_percent": base_data["change"],
            "change_amount": round(current_price * base_data["change"] / 100, 2),
            "bid": round(current_price * 0.9995, 2),
            "ask": round(current_price * 1.0005, 2),
            "spread": round(current_price * 0.001, 2),
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_volume_data(self, symbol: str) -> Dict[str, Any]:
        """Get volume data"""
        base_data = self.market_data[symbol]
        
        # Generate realistic volume profile
        return {
            "symbol": symbol,
            "volume_24h": base_data["volume"],
            "volume_1h": base_data["volume"] // 24,
            "avg_volume_30d": int(base_data["volume"] * 0.95),
            "volume_profile": {
                "buy_volume": int(base_data["volume"] * 0.52),
                "sell_volume": int(base_data["volume"] * 0.48)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_ohlc_data(self, symbol: str, timeframe: str, period: int) -> Dict[str, Any]:
        """Get OHLC (Open, High, Low, Close) data"""
        base_price = self.market_data[symbol]["price"]
        
        # Generate historical OHLC data
        ohlc_data = []
        current_time = datetime.now()
        
        # Map timeframe to timedelta
        timeframe_map = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "1h": timedelta(hours=1),
            "1d": timedelta(days=1),
            "1w": timedelta(weeks=1)
        }
        
        delta = timeframe_map.get(timeframe, timedelta(days=1))
        
        for i in range(period):
            # Generate realistic OHLC values
            variation = random.uniform(-2, 2)
            close = base_price * (1 + (variation + random.uniform(-1, 1)) / 100)
            open_price = close * (1 + random.uniform(-0.5, 0.5) / 100)
            high = max(open_price, close) * (1 + random.uniform(0, 0.5) / 100)
            low = min(open_price, close) * (1 - random.uniform(0, 0.5) / 100)
            
            ohlc_data.append({
                "timestamp": (current_time - delta * i).isoformat(),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": self.market_data[symbol]["volume"] // 24
            })
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": list(reversed(ohlc_data))
        }
    
    def _get_orderbook_data(self, symbol: str) -> Dict[str, Any]:
        """Get order book data"""
        current_price = self.market_data[symbol]["price"]
        
        # Generate realistic order book
        bids = []
        asks = []
        
        for i in range(10):
            bid_price = current_price * (1 - (i + 1) * 0.0001)
            ask_price = current_price * (1 + (i + 1) * 0.0001)
            
            bid_size = random.randint(1000, 50000)
            ask_size = random.randint(1000, 50000)
            
            bids.append({
                "price": round(bid_price, 2),
                "size": bid_size,
                "total": round(bid_price * bid_size, 2)
            })
            
            asks.append({
                "price": round(ask_price, 2),
                "size": ask_size,
                "total": round(ask_price * ask_size, 2)
            })
        
        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "spread": round(asks[0]["price"] - bids[0]["price"], 2),
            "mid_price": round((asks[0]["price"] + bids[0]["price"]) / 2, 2),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_required_context(self) -> List[str]:
        """Get required context keys for this tool"""
        return []