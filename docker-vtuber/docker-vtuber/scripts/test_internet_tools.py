#!/usr/bin/env python3
"""
Test script for internet-enabled S2 tools
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add the autogen agent path to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "CORE" / "autogen-agent"))

from autogen_agent.tools.trader.internet_market_tool import InternetMarketTool
from autogen_agent.tools.trader.financial_news_tool import FinancialNewsTool
from autogen_agent.tools.teacher.research_access_tool import ResearchAccessTool
from autogen_agent.tools.teacher.educational_search_tool import EducationalSearchTool
from autogen_agent.tools.streamer.trending_topics_tool import TrendingTopicsTool
from autogen_agent.tools.streamer.social_analytics_tool import SocialAnalyticsTool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_trader_tools():
    """Test trader team internet tools"""
    logger.info("\n=== Testing Trader Tools ===")
    
    # Test Internet Market Tool
    market_tool = InternetMarketTool()
    logger.info("\n1. Testing Internet Market Tool - Crypto Quote")
    result = await market_tool.execute({
        "symbol": "BTC",
        "market_type": "crypto",
        "data_type": "quote"
    })
    logger.info(f"Result: {result.status.value}")
    if result.status.value == "success":
        logger.info(f"BTC Price: ${result.data.get('price')}")
        logger.info(f"24h Change: {result.data.get('change_24h')}%")
    
    # Test Financial News Tool
    news_tool = FinancialNewsTool()
    logger.info("\n2. Testing Financial News Tool")
    result = await news_tool.execute({
        "query": "Bitcoin",
        "source_type": "crypto",
        "time_range": "today"
    })
    logger.info(f"Result: {result.status.value}")
    if result.status.value == "success":
        logger.info(f"News items found: {result.data.get('news_count')}")
        logger.info(f"Sentiment: {result.data.get('sentiment', {}).get('overall')}")


async def test_educator_tools():
    """Test educator team internet tools"""
    logger.info("\n=== Testing Educator Tools ===")
    
    # Test Research Access Tool
    research_tool = ResearchAccessTool()
    logger.info("\n1. Testing Research Access Tool")
    result = await research_tool.execute({
        "query": "machine learning",
        "resource_type": "papers",
        "level": "intermediate",
        "subject": "programming"
    })
    logger.info(f"Result: {result.status.value}")
    if result.status.value == "success":
        logger.info(f"Resources found: {result.data.get('resources_found')}")
        logger.info(f"Learning path steps: {len(result.data.get('learning_path', {}).get('steps', []))}")
    
    # Test Educational Search Tool
    edu_search_tool = EducationalSearchTool()
    logger.info("\n2. Testing Educational Search Tool")
    result = await edu_search_tool.execute({
        "topic": "Python programming",
        "grade_level": "high_school",
        "content_type": "lesson_plans"
    })
    logger.info(f"Result: {result.status.value}")
    if result.status.value == "success":
        logger.info(f"Results count: {result.data.get('results_count')}")
        logger.info(f"Learning objectives: {len(result.data.get('learning_objectives', []))}")


async def test_streamer_tools():
    """Test streamer team internet tools"""
    logger.info("\n=== Testing Streamer Tools ===")
    
    # Test Trending Topics Tool
    trending_tool = TrendingTopicsTool()
    logger.info("\n1. Testing Trending Topics Tool")
    result = await trending_tool.execute({
        "platform": "youtube",
        "category": "gaming",
        "region": "global"
    })
    logger.info(f"Result: {result.status.value}")
    if result.status.value == "success":
        logger.info(f"Trending topics: {len(result.data.get('trending_topics', []))}")
        logger.info(f"Content ideas: {len(result.data.get('content_ideas', []))}")
        logger.info(f"Engagement forecast: {result.data.get('engagement_forecast', {}).get('expected_growth')}")
    
    # Test Social Analytics Tool
    analytics_tool = SocialAnalyticsTool()
    logger.info("\n2. Testing Social Analytics Tool")
    result = await analytics_tool.execute({
        "analysis_type": "performance",
        "platform": "youtube",
        "time_period": "week"
    })
    logger.info(f"Result: {result.status.value}")
    if result.status.value == "success":
        if "current_metrics" in result.data:
            logger.info(f"Subscribers: {result.data['current_metrics'].get('subscribers')}")
            logger.info(f"Growth rate: {result.data.get('growth', {}).get('follower_growth')}")


async def main():
    """Run all tests"""
    logger.info("Starting Internet-Enabled Tools Test Suite")
    logger.info("=========================================")
    
    try:
        # Test each team's tools
        await test_trader_tools()
        await test_educator_tools()
        await test_streamer_tools()
        
        logger.info("\n=== All Tests Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())