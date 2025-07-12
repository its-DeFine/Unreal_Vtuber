# S2 Internet-Enabled Tools Documentation

## Overview

This document describes the internet-enabled tools added to the S2 AutoGen system for each specialized team (Trader, Educator, Streamer). These tools provide real-time data access from internet sources to enhance the capabilities of each team.

## Trader Team Internet Tools

### 1. Internet Market Tool (`internet_market_tool`)

**Purpose**: Access real-time market data from internet APIs for stocks, crypto, and forex.

**Features**:
- Real-time price quotes from CoinGecko (crypto)
- Stock data simulation (Alpha Vantage ready)
- Forex rates from Exchange Rate API
- Historical chart data
- Market sentiment analysis

**Parameters**:
- `symbol`: Asset symbol (e.g., BTC, AAPL, EUR/USD)
- `market_type`: stock, crypto, or forex
- `data_type`: quote, chart, news, or sentiment

**Rate Limiting**: Implemented per API source

### 2. Financial News Tool (`financial_news_tool`)

**Purpose**: Fetch real-time financial news and market analysis from RSS feeds and news APIs.

**Features**:
- RSS feed aggregation from multiple sources
- News sentiment analysis
- Trending financial topics
- Time-based filtering (today, week, month)

**Parameters**:
- `query`: Search query or topic
- `source_type`: general, earnings, economic, or crypto
- `time_range`: today, week, or month

**Data Sources**:
- Yahoo Finance RSS
- Bloomberg RSS
- CoinTelegraph (crypto)
- Federal Reserve (economic)

## Educator Team Internet Tools

### 3. Research Access Tool (`research_access_tool`)

**Purpose**: Access educational resources, research papers, and learning materials from internet sources.

**Features**:
- arXiv paper search and retrieval
- Online course recommendations
- Tutorial and guide aggregation
- Educational video resources
- Learning path generation

**Parameters**:
- `query`: Search query for educational content
- `resource_type`: papers, courses, tutorials, or educational_videos
- `level`: beginner, intermediate, or advanced
- `subject`: Subject area (mathematics, science, programming, etc.)

**Data Sources**:
- arXiv API for research papers
- Wikipedia API for general knowledge
- Simulated course catalogs

### 4. Educational Search Tool (`educational_search_tool`)

**Purpose**: Comprehensive search for lesson plans, worksheets, and teaching resources.

**Features**:
- Lesson plan generation and templates
- Learning objective creation (Bloom's Taxonomy)
- Educational standards alignment
- Assessment idea generation
- Grade-appropriate content filtering

**Parameters**:
- `topic`: Educational topic to search
- `grade_level`: elementary, middle_school, high_school, or college
- `content_type`: lesson_plans, worksheets, activities, or assessments
- `standards`: Educational standards (Common Core, NGSS, etc.)

## Streamer Team Internet Tools

### 5. Trending Topics Tool (`trending_topics_tool`)

**Purpose**: Access real-time trending topics and viral content across social platforms.

**Features**:
- Platform-specific trending topics
- Viral content analysis
- Hashtag analytics and recommendations
- Content idea generation
- Engagement predictions
- Optimal posting times

**Parameters**:
- `platform`: twitter, youtube, twitch, tiktok, or general
- `category`: gaming, technology, entertainment, news, or lifestyle
- `region`: global, us, europe, or asia

### 6. Social Analytics Tool (`social_analytics_tool`)

**Purpose**: Comprehensive social media analytics and competitor analysis.

**Features**:
- Multi-platform performance metrics
- Competitor analysis and benchmarking
- Audience demographics and behavior
- Content performance analysis
- Growth recommendations

**Parameters**:
- `analysis_type`: performance, competitors, audience, or content
- `platform`: youtube, twitch, twitter, instagram, tiktok, or multi_platform
- `time_period`: day, week, or month
- `username`: Username to analyze (optional)

## Implementation Details

### Base Tool Framework

All tools inherit from `BaseTool` and implement:
- Async execution pattern
- Standardized parameter validation
- Consistent error handling
- Rate limiting where applicable

### Key Dependencies

```python
# Core dependencies
aiohttp>=3.9.0  # Async HTTP requests
feedparser>=6.0.0  # RSS feed parsing

# APIs used (mostly free tiers)
- CoinGecko API (crypto data)
- Exchange Rate API (forex)
- arXiv API (research papers)
- Wikipedia API (educational content)
```

### Error Handling

All tools implement:
- Graceful API failure handling
- Rate limit management
- Timeout protection
- Fallback data when APIs unavailable

## Usage Examples

### Trader Team Example

```python
# Get real-time Bitcoin price
result = await internet_market_tool.execute({
    "symbol": "BTC",
    "market_type": "crypto",
    "data_type": "quote"
})

# Get financial news with sentiment
result = await financial_news_tool.execute({
    "query": "Federal Reserve",
    "source_type": "economic",
    "time_range": "week"
})
```

### Educator Team Example

```python
# Search for research papers
result = await research_access_tool.execute({
    "query": "deep learning",
    "resource_type": "papers",
    "level": "advanced",
    "subject": "programming"
})

# Find lesson plans
result = await educational_search_tool.execute({
    "topic": "photosynthesis",
    "grade_level": "middle_school",
    "content_type": "lesson_plans"
})
```

### Streamer Team Example

```python
# Get trending topics
result = await trending_topics_tool.execute({
    "platform": "youtube",
    "category": "gaming",
    "region": "global"
})

# Analyze social media performance
result = await social_analytics_tool.execute({
    "analysis_type": "performance",
    "platform": "multi_platform",
    "time_period": "month"
})
```

## Integration with S2 Teams

The tools are automatically loaded for each team through the `character_team_tools.py` mapping:

- **Trader Team**: Gains access to real-time market data and news
- **Educator Team**: Can search for educational resources and research
- **Streamer Team**: Gets trending topics and social analytics

This enables the AutoGen agents to make informed decisions based on current internet data rather than relying solely on their training data.

## Future Enhancements

1. **API Key Integration**: Add support for premium APIs with authentication
2. **Caching Layer**: Implement Redis caching for frequently accessed data
3. **WebSocket Support**: Real-time data streaming for market data
4. **More Data Sources**: Expand to include more educational and social platforms
5. **Custom Alerts**: Set up triggers for specific market conditions or trends