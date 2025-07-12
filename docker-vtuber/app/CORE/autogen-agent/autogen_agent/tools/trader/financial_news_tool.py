"""Financial News Tool for Trader Team
================================

Provides real-time financial news and market analysis from internet sources.
"""

import json
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import feedparser
from ..base_tool import BaseTool, ToolResult, ToolParameter, ToolExecutionContext, ToolStatus


class FinancialNewsTool(BaseTool):
    """Tool for accessing financial news and market analysis from internet sources"""
    
    def __init__(self):
        super().__init__(
            name="financial_news_tool",
            description="Access real-time financial news, market analysis, and economic indicators",
            category="trader",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query or topic (e.g., 'AAPL earnings', 'Fed rate decision')",
                    required=True
                ),
                ToolParameter(
                    name="source_type",
                    type="string", 
                    description="News source type: general, earnings, economic, crypto",
                    required=False,
                    default="general",
                    enum=["general", "earnings", "economic", "crypto"]
                ),
                ToolParameter(
                    name="time_range",
                    type="string",
                    description="Time range: today, week, month",
                    required=False,
                    default="today",
                    enum=["today", "week", "month"]
                )
            ]
        )
        
        # RSS feeds for financial news
        self.rss_feeds = {
            "general": [
                "https://feeds.finance.yahoo.com/rss/2.0/headline",
                "https://feeds.bloomberg.com/markets/news.rss",
                "https://www.investing.com/rss/news.rss"
            ],
            "earnings": [
                "https://feeds.finance.yahoo.com/rss/2.0/category-earnings",
                "https://seekingalpha.com/market_currents.xml"
            ],
            "economic": [
                "https://www.federalreserve.gov/feeds/press_all.xml",
                "https://www.ecb.europa.eu/rss/press.html"
            ],
            "crypto": [
                "https://cointelegraph.com/rss",
                "https://www.coindesk.com/arc/outboundfeeds/rss/"
            ]
        }
        
        # News API endpoints (for future enhancement with API keys)
        self.api_endpoints = {
            "newsapi": "https://newsapi.org/v2/everything",
            "finnhub": "https://finnhub.io/api/v1/news",
            "marketaux": "https://api.marketaux.com/v1/news/all"
        }
    
    async def execute(self, params: Dict[str, Any], context: Optional[ToolExecutionContext] = None) -> ToolResult:
        """Execute financial news retrieval from internet sources"""
        
        try:
            query = params.get("query", "")
            source_type = params.get("source_type", "general")
            time_range = params.get("time_range", "today")
            
            logging.info(f"📰 [FINANCIAL_NEWS] Searching for: {query} in {source_type} sources")
            
            # Fetch news from RSS feeds
            news_items = await self._fetch_rss_news(query, source_type, time_range)
            
            # Analyze sentiment if we have news
            if news_items:
                sentiment_analysis = self._analyze_news_sentiment(news_items)
            else:
                sentiment_analysis = {"overall": "neutral", "score": 0}
            
            # Get trending topics
            trending_topics = await self._get_trending_topics(source_type)
            
            result = {
                "query": query,
                "news_count": len(news_items),
                "news_items": news_items[:10],  # Limit to top 10 items
                "sentiment": sentiment_analysis,
                "trending_topics": trending_topics,
                "sources": list(set(item.get("source", "Unknown") for item in news_items)),
                "time_range": time_range
            }
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result,
                metadata={
                    "query": query,
                    "source_type": source_type,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logging.error(f"❌ [FINANCIAL_NEWS] Error: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                data={},
                message=str(e)
            )
    
    async def _fetch_rss_news(self, query: str, source_type: str, time_range: str) -> List[Dict[str, Any]]:
        """Fetch news from RSS feeds"""
        
        news_items = []
        feeds = self.rss_feeds.get(source_type, self.rss_feeds["general"])
        
        # Calculate time cutoff
        time_cutoffs = {
            "today": datetime.now() - timedelta(days=1),
            "week": datetime.now() - timedelta(days=7),
            "month": datetime.now() - timedelta(days=30)
        }
        cutoff_time = time_cutoffs.get(time_range, time_cutoffs["today"])
        
        async with aiohttp.ClientSession() as session:
            for feed_url in feeds:
                try:
                    async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries:
                                # Parse publication date
                                pub_date = None
                                if hasattr(entry, 'published_parsed'):
                                    pub_date = datetime.fromtimestamp(
                                        entry.published_parsed.tm_sec if hasattr(entry.published_parsed, 'tm_sec') else 0
                                    )
                                elif hasattr(entry, 'updated_parsed'):
                                    pub_date = datetime.fromtimestamp(
                                        entry.updated_parsed.tm_sec if hasattr(entry.updated_parsed, 'tm_sec') else 0
                                    )
                                
                                # Skip old entries
                                if pub_date and pub_date < cutoff_time:
                                    continue
                                
                                # Check if entry matches query
                                title = entry.get('title', '')
                                summary = entry.get('summary', '')
                                
                                if query.lower() in title.lower() or query.lower() in summary.lower():
                                    news_items.append({
                                        "title": title,
                                        "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                                        "url": entry.get('link', ''),
                                        "published": pub_date.isoformat() if pub_date else "Unknown",
                                        "source": feed.feed.get('title', 'Unknown')
                                    })
                                
                except Exception as e:
                    logging.warning(f"Failed to fetch from {feed_url}: {e}")
                    continue
        
        # Sort by publication date (newest first)
        news_items.sort(key=lambda x: x.get('published', ''), reverse=True)
        
        return news_items
    
    def _analyze_news_sentiment(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment of news items (simplified version)"""
        
        # Sentiment keywords
        positive_keywords = [
            'surge', 'gain', 'rise', 'profit', 'beat', 'exceed', 'strong', 'growth',
            'bullish', 'upgrade', 'buy', 'positive', 'record', 'high', 'breakthrough'
        ]
        
        negative_keywords = [
            'fall', 'drop', 'loss', 'decline', 'miss', 'weak', 'concern', 'risk',
            'bearish', 'downgrade', 'sell', 'negative', 'low', 'crash', 'recession'
        ]
        
        positive_count = 0
        negative_count = 0
        
        for item in news_items:
            text = (item.get('title', '') + ' ' + item.get('summary', '')).lower()
            
            # Count keyword occurrences
            for keyword in positive_keywords:
                if keyword in text:
                    positive_count += 1
            
            for keyword in negative_keywords:
                if keyword in text:
                    negative_count += 1
        
        # Calculate sentiment score
        total_keywords = positive_count + negative_count
        if total_keywords == 0:
            sentiment_score = 0
            overall_sentiment = "neutral"
        else:
            sentiment_score = (positive_count - negative_count) / total_keywords
            
            if sentiment_score > 0.2:
                overall_sentiment = "bullish"
            elif sentiment_score < -0.2:
                overall_sentiment = "bearish"
            else:
                overall_sentiment = "neutral"
        
        return {
            "overall": overall_sentiment,
            "score": round(sentiment_score, 2),
            "positive_signals": positive_count,
            "negative_signals": negative_count,
            "confidence": "high" if total_keywords > 10 else "medium" if total_keywords > 5 else "low"
        }
    
    async def _get_trending_topics(self, source_type: str) -> List[str]:
        """Get trending financial topics"""
        
        # Simulated trending topics based on source type
        trending_map = {
            "general": [
                "Fed Interest Rates",
                "Tech Earnings Season",
                "AI Stock Rally",
                "China Economic Data",
                "Oil Prices"
            ],
            "earnings": [
                "Q4 Earnings Reports",
                "Revenue Guidance",
                "EPS Beats",
                "Profit Margins",
                "Forward Guidance"
            ],
            "economic": [
                "Inflation Data",
                "GDP Growth",
                "Unemployment Rate",
                "Consumer Confidence",
                "Trade Balance"
            ],
            "crypto": [
                "Bitcoin ETF",
                "Ethereum Upgrade",
                "DeFi Trends",
                "Regulatory News",
                "Institutional Adoption"
            ]
        }
        
        return trending_map.get(source_type, trending_map["general"])