"""Internet-Enabled Market Data Tool for Trader Team
================================

Provides real-time market data from internet sources for trading analysis.
"""

import json
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from ..base_tool import BaseTool, ToolResult, ToolParameter, ToolExecutionContext, ToolStatus


class InternetMarketTool(BaseTool):
    """Tool for accessing real-time market data from internet sources"""
    
    def __init__(self):
        super().__init__(
            name="internet_market_tool",
            description="Access real-time market data from internet APIs (stocks, crypto, forex)",
            category="trader",
            parameters=[
                ToolParameter(
                    name="symbol",
                    type="string",
                    description="Asset symbol (e.g., AAPL, BTC, EUR/USD)",
                    required=True
                ),
                ToolParameter(
                    name="market_type",
                    type="string", 
                    description="Market type: stock, crypto, forex",
                    required=True,
                    enum=["stock", "crypto", "forex"]
                ),
                ToolParameter(
                    name="data_type",
                    type="string",
                    description="Data type: quote, chart, news, sentiment",
                    required=False,
                    default="quote",
                    enum=["quote", "chart", "news", "sentiment"]
                )
            ]
        )
        
        # API endpoints (using demo/free tiers)
        self.api_endpoints = {
            "crypto": {
                "quote": "https://api.coingecko.com/api/v3/simple/price",
                "chart": "https://api.coingecko.com/api/v3/coins/{id}/market_chart",
                "trending": "https://api.coingecko.com/api/v3/search/trending"
            },
            "stock": {
                # Alpha Vantage free tier (requires API key)
                "quote": "https://www.alphavantage.co/query",
                "news": "https://www.alphavantage.co/query"
            },
            "forex": {
                "quote": "https://api.exchangerate-api.com/v4/latest/"
            }
        }
        
        # Rate limiting
        self.rate_limiter = {
            "coingecko": {"calls": 0, "reset_time": datetime.now(), "limit": 50},
            "alphavantage": {"calls": 0, "reset_time": datetime.now(), "limit": 5},
            "exchangerate": {"calls": 0, "reset_time": datetime.now(), "limit": 100}
        }
    
    async def execute(self, params: Dict[str, Any], context: Optional[ToolExecutionContext] = None) -> ToolResult:
        """Execute market data retrieval from internet sources"""
        
        try:
            symbol = params.get("symbol", "").upper()
            market_type = params.get("market_type", "crypto").lower()
            data_type = params.get("data_type", "quote").lower()
            
            logging.info(f"📊 [INTERNET_MARKET] Fetching {data_type} for {symbol} in {market_type} market")
            
            # Check rate limits
            if not self._check_rate_limit(market_type):
                return ToolResult(
                    status=ToolStatus.ERROR,
                    data={},
                    message="Rate limit exceeded. Please try again later."
                )
            
            # Fetch data based on market type
            if market_type == "crypto":
                result = await self._fetch_crypto_data(symbol, data_type)
            elif market_type == "stock":
                result = await self._fetch_stock_data(symbol, data_type)
            elif market_type == "forex":
                result = await self._fetch_forex_data(symbol, data_type)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    data={},
                    message=f"Invalid market type: {market_type}"
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result,
                metadata={
                    "symbol": symbol,
                    "market_type": market_type,
                    "data_type": data_type,
                    "timestamp": datetime.now().isoformat(),
                    "source": "internet_api"
                }
            )
            
        except Exception as e:
            logging.error(f"❌ [INTERNET_MARKET] Error: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                data={},
                message=str(e)
            )
    
    async def _fetch_crypto_data(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """Fetch cryptocurrency data from CoinGecko API"""
        
        # Map common symbols to CoinGecko IDs
        symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "XRP": "ripple",
            "ADA": "cardano",
            "SOL": "solana",
            "DOGE": "dogecoin"
        }
        
        coin_id = symbol_map.get(symbol, symbol.lower())
        
        async with aiohttp.ClientSession() as session:
            if data_type == "quote":
                url = self.api_endpoints["crypto"]["quote"]
                params = {
                    "ids": coin_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                    "include_market_cap": "true"
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if coin_id in data:
                            coin_data = data[coin_id]
                            return {
                                "symbol": symbol,
                                "price": coin_data.get("usd", 0),
                                "change_24h": coin_data.get("usd_24h_change", 0),
                                "volume_24h": coin_data.get("usd_24h_vol", 0),
                                "market_cap": coin_data.get("usd_market_cap", 0),
                                "last_updated": datetime.now().isoformat()
                            }
                    
            elif data_type == "chart":
                url = self.api_endpoints["crypto"]["chart"].format(id=coin_id)
                params = {
                    "vs_currency": "usd",
                    "days": "7"
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "symbol": symbol,
                            "prices": data.get("prices", [])[-24:],  # Last 24 data points
                            "market_caps": data.get("market_caps", [])[-24:],
                            "volumes": data.get("total_volumes", [])[-24:]
                        }
            
            elif data_type == "news" or data_type == "sentiment":
                # Get trending data as a proxy for sentiment
                url = self.api_endpoints["crypto"]["trending"]
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        trending_coins = data.get("coins", [])
                        
                        # Check if our symbol is trending
                        is_trending = any(coin["item"]["symbol"].upper() == symbol for coin in trending_coins)
                        
                        return {
                            "symbol": symbol,
                            "is_trending": is_trending,
                            "trending_rank": next((i+1 for i, coin in enumerate(trending_coins) 
                                                  if coin["item"]["symbol"].upper() == symbol), None),
                            "sentiment": "bullish" if is_trending else "neutral",
                            "top_trending": [coin["item"]["symbol"] for coin in trending_coins[:5]]
                        }
        
        return {"error": "Failed to fetch crypto data"}
    
    async def _fetch_stock_data(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """Fetch stock data (simulated for demo - would need API key for real data)"""
        
        # Simulated response - in production, use Alpha Vantage or similar API
        logging.warning("📊 [INTERNET_MARKET] Stock data requires API key - returning simulated data")
        
        if data_type == "quote":
            # Simulate real-time quote
            import random
            base_price = 150.0
            return {
                "symbol": symbol,
                "price": round(base_price + random.uniform(-5, 5), 2),
                "change": round(random.uniform(-2, 2), 2),
                "change_percent": round(random.uniform(-1.5, 1.5), 2),
                "volume": random.randint(10000000, 50000000),
                "high": round(base_price + random.uniform(0, 5), 2),
                "low": round(base_price - random.uniform(0, 5), 2),
                "market_status": "open" if datetime.now().hour in range(9, 16) else "closed"
            }
        
        elif data_type == "news":
            # Simulated news headlines
            headlines = [
                f"{symbol} Reports Strong Q4 Earnings, Beats Estimates",
                f"Analysts Upgrade {symbol} to Buy Rating",
                f"{symbol} Announces New Product Launch",
                f"Market Watch: {symbol} Among Top Gainers Today"
            ]
            
            return {
                "symbol": symbol,
                "news": [
                    {
                        "headline": headline,
                        "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                        "sentiment": "positive" if i % 2 == 0 else "neutral"
                    }
                    for i, headline in enumerate(headlines)
                ]
            }
        
        return {"error": "Stock data type not supported"}
    
    async def _fetch_forex_data(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """Fetch forex data from Exchange Rate API"""
        
        if data_type != "quote":
            return {"error": "Only quote data available for forex"}
        
        # Parse currency pair (e.g., EUR/USD -> EUR, USD)
        currencies = symbol.replace("-", "/").split("/")
        if len(currencies) != 2:
            return {"error": "Invalid forex pair format. Use format like EUR/USD"}
        
        base_currency, quote_currency = currencies
        
        async with aiohttp.ClientSession() as session:
            url = self.api_endpoints["forex"]["quote"] + base_currency
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    rates = data.get("rates", {})
                    
                    if quote_currency in rates:
                        rate = rates[quote_currency]
                        
                        return {
                            "symbol": symbol,
                            "base": base_currency,
                            "quote": quote_currency,
                            "rate": rate,
                            "bid": round(rate * 0.9999, 4),
                            "ask": round(rate * 1.0001, 4),
                            "spread": round(rate * 0.0002, 4),
                            "timestamp": data.get("date", datetime.now().isoformat())
                        }
        
        return {"error": "Failed to fetch forex data"}
    
    def _check_rate_limit(self, market_type: str) -> bool:
        """Check and update rate limits"""
        
        # Map market types to rate limiter keys
        limiter_map = {
            "crypto": "coingecko",
            "stock": "alphavantage",
            "forex": "exchangerate"
        }
        
        limiter_key = limiter_map.get(market_type)
        if not limiter_key:
            return True
        
        limiter = self.rate_limiter[limiter_key]
        
        # Reset counter if minute has passed
        if datetime.now() - limiter["reset_time"] > timedelta(minutes=1):
            limiter["calls"] = 0
            limiter["reset_time"] = datetime.now()
        
        # Check limit
        if limiter["calls"] >= limiter["limit"]:
            return False
        
        # Increment counter
        limiter["calls"] += 1
        return True