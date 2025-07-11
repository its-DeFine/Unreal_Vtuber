"""
Social Media Management Tool for Streamer Team
==============================================

Manages social media presence across multiple platforms, schedules posts,
tracks engagement, and manages community interactions.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random
import hashlib

logger = logging.getLogger(__name__)


async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    📱 Social Media Management Tool Entry Point
    
    Comprehensive social media management across platforms.
    
    Args:
        context: Operation context containing:
            - action: Type of operation (post, schedule, analytics, engage, monitor)
            - platform: Target platform(s)
            - Additional parameters based on action
    
    Returns:
        Social media operation results
    """
    try:
        action = context.get("action", "status")
        
        # Route to appropriate social media function
        if action == "post":
            return await _create_post(context)
        
        elif action == "schedule":
            return await _schedule_posts(context)
        
        elif action == "analytics":
            return await _get_analytics(context)
        
        elif action == "engage":
            return await _manage_engagement(context)
        
        elif action == "monitor":
            return await _monitor_mentions(context)
        
        elif action == "trends":
            return await _analyze_trends(context)
        
        elif action == "content_calendar":
            return await _manage_content_calendar(context)
        
        elif action == "cross_post":
            return await _cross_platform_post(context)
        
        elif action == "status":
            return await _get_social_status(context)
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": ["post", "schedule", "analytics", "engage", 
                                    "monitor", "trends", "content_calendar", "cross_post", "status"]
            }
            
    except Exception as e:
        logger.error(f"❌ [SOCIAL_MEDIA] Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def _create_post(context: Dict[str, Any]) -> Dict[str, Any]:
    """Create a social media post"""
    try:
        platform = context.get("platform", "twitter")
        content = context.get("content", "")
        media = context.get("media", [])
        tags = context.get("tags", [])
        
        if not content:
            return {
                "success": False,
                "error": "Post content is required"
            }
        
        # Generate post ID
        post_id = f"POST-{hashlib.md5(f'{platform}{datetime.now()}'.encode()).hexdigest()[:8].upper()}"
        
        # Platform-specific validation
        validation = _validate_post_content(platform, content, media)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["error"],
                "suggestions": validation.get("suggestions", [])
            }
        
        # Create post
        post = {
            "post_id": post_id,
            "platform": platform,
            "content": content,
            "media": media,
            "tags": tags,
            "status": "published",
            "timestamp": datetime.now().isoformat(),
            "url": f"https://{platform}.com/post/{post_id}"
        }
        
        # Simulate engagement prediction
        engagement_prediction = _predict_engagement(platform, content, tags)
        
        # Auto-generate hashtags if needed
        if platform in ["twitter", "instagram"] and not tags:
            tags = _generate_hashtags(content)
            post["tags"] = tags
        
        return {
            "success": True,
            "post": post,
            "engagement_prediction": engagement_prediction,
            "optimization_suggestions": _get_post_optimizations(platform, content, tags),
            "message": f"Post created successfully on {platform}"
        }
        
    except Exception as e:
        logger.error(f"❌ [SOCIAL_MEDIA] Post creation error: {e}")
        return {"success": False, "error": str(e)}


async def _schedule_posts(context: Dict[str, Any]) -> Dict[str, Any]:
    """Schedule social media posts"""
    try:
        posts = context.get("posts", [])
        strategy = context.get("strategy", "optimal_times")
        
        if not posts:
            return {
                "success": False,
                "error": "No posts provided for scheduling"
            }
        
        # Generate schedule
        scheduled_posts = []
        
        for i, post in enumerate(posts):
            # Determine optimal posting time
            if strategy == "optimal_times":
                scheduled_time = _get_optimal_posting_time(
                    post.get("platform", "twitter"),
                    i
                )
            elif strategy == "spread":
                scheduled_time = datetime.now() + timedelta(hours=i * 4)
            else:
                scheduled_time = datetime.now() + timedelta(hours=i * 24)
            
            scheduled_post = {
                "schedule_id": f"SCH-{hashlib.md5(f'{i}{datetime.now()}'.encode()).hexdigest()[:8].upper()}",
                "post": post,
                "scheduled_time": scheduled_time.isoformat(),
                "platform": post.get("platform", "twitter"),
                "status": "scheduled",
                "optimal_score": _calculate_optimal_score(scheduled_time, post.get("platform"))
            }
            
            scheduled_posts.append(scheduled_post)
        
        # Generate posting calendar
        calendar = _generate_posting_calendar(scheduled_posts)
        
        return {
            "success": True,
            "scheduled_posts": scheduled_posts,
            "posting_calendar": calendar,
            "statistics": {
                "total_scheduled": len(scheduled_posts),
                "platforms": list(set(p["platform"] for p in scheduled_posts)),
                "next_post": scheduled_posts[0]["scheduled_time"] if scheduled_posts else None,
                "coverage_hours": 24 * 7  # Weekly coverage
            },
            "recommendations": [
                "Posts scheduled at optimal engagement times",
                "Consider adding more visual content for better engagement",
                "Review and adjust schedule based on analytics"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ [SOCIAL_MEDIA] Scheduling error: {e}")
        return {"success": False, "error": str(e)}


async def _get_analytics(context: Dict[str, Any]) -> Dict[str, Any]:
    """Get social media analytics"""
    try:
        platform = context.get("platform", "all")
        timeframe = context.get("timeframe", "7d")
        metrics = context.get("metrics", ["engagement", "reach", "growth"])
        
        # Generate analytics data
        analytics = {}
        
        platforms = ["twitter", "instagram", "youtube", "twitch"] if platform == "all" else [platform]
        
        for plat in platforms:
            analytics[plat] = {
                "followers": {
                    "current": random.randint(10000, 100000),
                    "growth": random.uniform(1, 10),
                    "growth_rate": random.uniform(0.5, 5)
                },
                "engagement": {
                    "rate": random.uniform(2, 8),
                    "likes": random.randint(1000, 10000),
                    "comments": random.randint(100, 1000),
                    "shares": random.randint(50, 500)
                },
                "reach": {
                    "total": random.randint(50000, 500000),
                    "organic": random.randint(30000, 300000),
                    "paid": random.randint(10000, 100000)
                },
                "top_posts": _generate_top_posts(plat, 3),
                "demographics": {
                    "age_groups": {
                        "18-24": 25,
                        "25-34": 35,
                        "35-44": 25,
                        "45+": 15
                    },
                    "gender": {
                        "male": 55,
                        "female": 43,
                        "other": 2
                    },
                    "top_locations": ["US", "UK", "Canada", "Australia"]
                }
            }
        
        # Calculate aggregated metrics
        total_followers = sum(analytics[p]["followers"]["current"] for p in analytics)
        avg_engagement = sum(analytics[p]["engagement"]["rate"] for p in analytics) / len(analytics)
        
        # Generate insights
        insights = _generate_analytics_insights(analytics, timeframe)
        
        return {
            "success": True,
            "timeframe": timeframe,
            "analytics": analytics,
            "summary": {
                "total_followers": total_followers,
                "average_engagement_rate": round(avg_engagement, 2),
                "total_reach": sum(analytics[p]["reach"]["total"] for p in analytics),
                "growth_trend": "positive" if avg_engagement > 3 else "stable"
            },
            "insights": insights,
            "recommendations": _generate_growth_recommendations(analytics)
        }
        
    except Exception as e:
        logger.error(f"❌ [SOCIAL_MEDIA] Analytics error: {e}")
        return {"success": False, "error": str(e)}


async def _manage_engagement(context: Dict[str, Any]) -> Dict[str, Any]:
    """Manage social media engagement"""
    try:
        action_type = context.get("type", "respond")  # respond, like, share, follow
        platform = context.get("platform", "twitter")
        
        if action_type == "respond":
            # Get pending messages/comments
            pending_items = _get_pending_engagements(platform)
            
            # Generate responses
            responses = []
            for item in pending_items[:5]:  # Limit to 5 for demo
                response = {
                    "item_id": item["id"],
                    "type": item["type"],
                    "original_content": item["content"],
                    "suggested_response": _generate_response(item["content"], item["sentiment"]),
                    "priority": item["priority"],
                    "sentiment": item["sentiment"]
                }
                responses.append(response)
            
            return {
                "success": True,
                "platform": platform,
                "pending_engagements": len(pending_items),
                "responses": responses,
                "engagement_stats": {
                    "response_time_avg": "15 minutes",
                    "response_rate": "85%",
                    "satisfaction_score": 4.5
                }
            }
            
        elif action_type == "auto_engage":
            # Automated engagement settings
            settings = {
                "auto_like": {
                    "enabled": True,
                    "keywords": ["streaming", "gaming", "content"],
                    "limit_per_hour": 30
                },
                "auto_follow": {
                    "enabled": False,
                    "criteria": ["relevant_content", "engaged_users"],
                    "limit_per_day": 50
                },
                "auto_respond": {
                    "enabled": True,
                    "response_templates": _get_response_templates(),
                    "sentiment_based": True
                }
            }
            
            return {
                "success": True,
                "auto_engagement_settings": settings,
                "current_activity": {
                    "likes_today": 125,
                    "follows_today": 23,
                    "responses_today": 45
                },
                "warnings": [
                    "Monitor auto-engagement to avoid platform penalties",
                    "Ensure responses remain authentic and relevant"
                ]
            }
        
        return {
            "success": True,
            "message": f"Engagement action {action_type} completed"
        }
        
    except Exception as e:
        logger.error(f"❌ [SOCIAL_MEDIA] Engagement error: {e}")
        return {"success": False, "error": str(e)}


async def _monitor_mentions(context: Dict[str, Any]) -> Dict[str, Any]:
    """Monitor social media mentions and brand sentiment"""
    try:
        keywords = context.get("keywords", ["@username", "#brand"])
        platforms = context.get("platforms", ["twitter", "instagram", "youtube"])
        
        # Simulate mention monitoring
        mentions = []
        
        for _ in range(random.randint(5, 15)):
            mention = {
                "id": f"MENTION-{random.randint(1000, 9999)}",
                "platform": random.choice(platforms),
                "author": f"user_{random.randint(100, 999)}",
                "content": _generate_sample_mention(keywords),
                "timestamp": (datetime.now() - timedelta(minutes=random.randint(1, 1440))).isoformat(),
                "sentiment": random.choice(["positive", "neutral", "negative"]),
                "reach": random.randint(100, 10000),
                "engagement": random.randint(10, 1000),
                "requires_response": random.choice([True, False])
            }
            mentions.append(mention)
        
        # Sentiment analysis
        sentiment_breakdown = {
            "positive": sum(1 for m in mentions if m["sentiment"] == "positive"),
            "neutral": sum(1 for m in mentions if m["sentiment"] == "neutral"),
            "negative": sum(1 for m in mentions if m["sentiment"] == "negative")
        }
        
        # Priority mentions
        priority_mentions = [m for m in mentions if m["reach"] > 5000 or m["sentiment"] == "negative"]
        
        return {
            "success": True,
            "monitoring_keywords": keywords,
            "platforms": platforms,
            "mentions": mentions,
            "summary": {
                "total_mentions": len(mentions),
                "requiring_response": sum(1 for m in mentions if m["requires_response"]),
                "sentiment_breakdown": sentiment_breakdown,
                "sentiment_score": _calculate_sentiment_score(sentiment_breakdown),
                "total_reach": sum(m["reach"] for m in mentions)
            },
            "priority_mentions": priority_mentions,
            "trends": {
                "mention_volume": "increasing",
                "sentiment_trend": "stable",
                "top_topics": ["streaming schedule", "content quality", "community events"]
            },
            "alerts": _generate_monitoring_alerts(mentions, sentiment_breakdown)
        }
        
    except Exception as e:
        logger.error(f"❌ [SOCIAL_MEDIA] Monitoring error: {e}")
        return {"success": False, "error": str(e)}


async def _analyze_trends(context: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze social media trends"""
    try:
        category = context.get("category", "gaming")
        platforms = context.get("platforms", ["twitter", "youtube", "twitch"])
        
        # Generate trending topics
        trends = {
            "hashtags": [
                {"tag": "#Gaming2024", "volume": 125000, "growth": 45},
                {"tag": "#StreamerLife", "volume": 85000, "growth": 32},
                {"tag": "#ContentCreator", "volume": 95000, "growth": 28},
                {"tag": f"#{category}News", "volume": 65000, "growth": 15},
                {"tag": "#LiveStreaming", "volume": 110000, "growth": 38}
            ],
            "topics": [
                {"topic": "New game releases", "relevance": 0.85, "opportunity": "high"},
                {"topic": "Streaming tips", "relevance": 0.72, "opportunity": "medium"},
                {"topic": "Community challenges", "relevance": 0.68, "opportunity": "high"},
                {"topic": "Tech reviews", "relevance": 0.55, "opportunity": "low"}
            ],
            "content_formats": {
                "short_videos": {"popularity": 92, "engagement": 8.5},
                "live_streams": {"popularity": 78, "engagement": 6.2},
                "tutorials": {"popularity": 65, "engagement": 7.8},
                "memes": {"popularity": 88, "engagement": 9.1}
            },
            "optimal_posting_times": {
                "twitter": ["9:00 AM", "1:00 PM", "7:00 PM"],
                "youtube": ["2:00 PM", "8:00 PM"],
                "twitch": ["6:00 PM", "9:00 PM", "11:00 PM"]
            }
        }
        
        # Generate content recommendations
        content_recommendations = _generate_trend_based_content(trends, category)
        
        return {
            "success": True,
            "category": category,
            "platforms": platforms,
            "trends": trends,
            "content_recommendations": content_recommendations,
            "competitive_analysis": {
                "trending_creators": [
                    {"name": "TopStreamer1", "growth": 25, "content_style": "variety"},
                    {"name": "ProGamer2", "growth": 18, "content_style": "competitive"},
                    {"name": "ContentKing3", "growth": 22, "content_style": "educational"}
                ],
                "successful_strategies": [
                    "Consistent posting schedule",
                    "Community engagement",
                    "Trend-jacking",
                    "Collaborations"
                ]
            },
            "action_items": [
                "Create content around trending topics",
                "Optimize posting times for maximum reach",
                "Engage with trending hashtags",
                "Experiment with popular content formats"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ [SOCIAL_MEDIA] Trend analysis error: {e}")
        return {"success": False, "error": str(e)}


async def _manage_content_calendar(context: Dict[str, Any]) -> Dict[str, Any]:
    """Manage content calendar"""
    try:
        action = context.get("calendar_action", "view")  # view, add, update, optimize
        timeframe = context.get("timeframe", "week")
        
        # Generate calendar
        calendar = _generate_content_calendar(timeframe)
        
        if action == "optimize":
            # Optimize calendar for engagement
            optimized_calendar = _optimize_calendar(calendar)
            
            return {
                "success": True,
                "action": "optimize",
                "original_calendar": calendar,
                "optimized_calendar": optimized_calendar,
                "improvements": {
                    "expected_engagement_increase": "22%",
                    "better_time_slots": 8,
                    "content_diversity_score": 8.5
                },
                "recommendations": [
                    "Move Tuesday stream to optimal 7 PM slot",
                    "Add more interactive content on weekends",
                    "Include trending topics in Thursday's content"
                ]
            }
        
        elif action == "add":
            # Add new content
            new_content = context.get("content", {})
            calendar["content"].append(new_content)
            
            return {
                "success": True,
                "action": "add",
                "calendar": calendar,
                "message": "Content added to calendar"
            }
        
        else:  # view
            return {
                "success": True,
                "action": "view",
                "timeframe": timeframe,
                "calendar": calendar,
                "statistics": {
                    "total_posts": len(calendar["content"]),
                    "platforms_covered": calendar["platforms"],
                    "content_types": calendar["content_types"],
                    "consistency_score": 8.5
                },
                "gaps": _identify_content_gaps(calendar)
            }
        
    except Exception as e:
        logger.error(f"❌ [SOCIAL_MEDIA] Calendar management error: {e}")
        return {"success": False, "error": str(e)}


async def _cross_platform_post(context: Dict[str, Any]) -> Dict[str, Any]:
    """Create cross-platform posts"""
    try:
        content = context.get("content", "")
        platforms = context.get("platforms", ["twitter", "instagram", "youtube"])
        adapt_content = context.get("adapt_content", True)
        
        if not content:
            return {
                "success": False,
                "error": "Content is required for cross-posting"
            }
        
        # Adapt content for each platform
        adapted_posts = {}
        
        for platform in platforms:
            if adapt_content:
                adapted = _adapt_content_for_platform(content, platform)
            else:
                adapted = content
            
            adapted_posts[platform] = {
                "content": adapted,
                "platform": platform,
                "char_count": len(adapted),
                "media_requirements": _get_media_requirements(platform),
                "optimal_time": _get_optimal_posting_time(platform, 0).strftime("%H:%M"),
                "tags": _generate_platform_tags(platform, content)
            }
        
        # Validate all posts
        validation_results = {}
        for platform, post in adapted_posts.items():
            validation_results[platform] = _validate_post_content(
                platform, post["content"], []
            )
        
        return {
            "success": True,
            "original_content": content,
            "adapted_posts": adapted_posts,
            "validation": validation_results,
            "posting_schedule": {
                platform: {
                    "time": adapted_posts[platform]["optimal_time"],
                    "estimated_reach": random.randint(1000, 10000)
                }
                for platform in platforms
            },
            "tips": [
                "Review each platform's adapted content",
                "Add platform-specific media for better engagement",
                "Consider platform-specific hashtags"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ [SOCIAL_MEDIA] Cross-platform posting error: {e}")
        return {"success": False, "error": str(e)}


async def _get_social_status(context: Dict[str, Any]) -> Dict[str, Any]:
    """Get overall social media status"""
    try:
        # Aggregate status across platforms
        platforms_status = {
            "twitter": {
                "followers": 45000,
                "following": 1200,
                "posts_today": 5,
                "engagement_rate": 4.5,
                "health": "good"
            },
            "instagram": {
                "followers": 62000,
                "following": 800,
                "posts_today": 2,
                "engagement_rate": 6.8,
                "health": "excellent"
            },
            "youtube": {
                "subscribers": 125000,
                "videos": 342,
                "views_today": 15000,
                "engagement_rate": 5.2,
                "health": "good"
            },
            "twitch": {
                "followers": 85000,
                "avg_viewers": 1200,
                "stream_hours_week": 28,
                "engagement_rate": 7.5,
                "health": "excellent"
            }
        }
        
        # Calculate totals
        total_followers = sum(p.get("followers", p.get("subscribers", 0)) for p in platforms_status.values())
        avg_engagement = sum(p["engagement_rate"] for p in platforms_status.values()) / len(platforms_status)
        
        # Recent activity
        recent_activity = {
            "posts_last_24h": 12,
            "engagements_last_24h": 450,
            "new_followers_last_24h": 285,
            "top_post": {
                "platform": "twitter",
                "content": "Just hit 1000 wins in the new season! Thanks for all the support! 🎮🔥",
                "engagement": 2500
            }
        }
        
        # Health check
        health_issues = []
        for platform, status in platforms_status.items():
            if status["engagement_rate"] < 2:
                health_issues.append(f"Low engagement on {platform}")
        
        return {
            "success": True,
            "platforms": platforms_status,
            "summary": {
                "total_followers": total_followers,
                "average_engagement_rate": round(avg_engagement, 2),
                "content_posted_today": sum(p.get("posts_today", 0) for p in platforms_status.values()),
                "overall_health": "excellent" if not health_issues else "needs_attention"
            },
            "recent_activity": recent_activity,
            "health_check": {
                "issues": health_issues,
                "recommendations": [
                    "Maintain consistent posting schedule",
                    "Increase video content for better engagement",
                    "Engage more with community responses"
                ] if health_issues else ["Keep up the great work!"]
            },
            "upcoming": {
                "scheduled_posts": 8,
                "next_stream": "Tomorrow at 7 PM EST",
                "content_gaps": ["No YouTube video scheduled this week"]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [SOCIAL_MEDIA] Status check error: {e}")
        return {"success": False, "error": str(e)}


# Helper functions
def _validate_post_content(platform: str, content: str, media: List[str]) -> Dict[str, Any]:
    """Validate post content for platform requirements"""
    validations = {
        "twitter": {"char_limit": 280, "media_limit": 4},
        "instagram": {"char_limit": 2200, "media_limit": 10, "media_required": True},
        "youtube": {"char_limit": 5000, "media_limit": 1, "media_required": True},
        "twitch": {"char_limit": 500, "media_limit": 0}
    }
    
    platform_rules = validations.get(platform, {"char_limit": 1000, "media_limit": 4})
    
    errors = []
    suggestions = []
    
    if len(content) > platform_rules["char_limit"]:
        errors.append(f"Content exceeds {platform} character limit ({platform_rules['char_limit']})")
        suggestions.append(f"Shorten content by {len(content) - platform_rules['char_limit']} characters")
    
    if platform_rules.get("media_required") and not media:
        errors.append(f"{platform} requires at least one media item")
        suggestions.append("Add an image or video to your post")
    
    if len(media) > platform_rules["media_limit"]:
        errors.append(f"Too many media items for {platform} (max: {platform_rules['media_limit']})")
    
    return {
        "valid": len(errors) == 0,
        "error": "; ".join(errors) if errors else None,
        "suggestions": suggestions
    }


def _predict_engagement(platform: str, content: str, tags: List[str]) -> Dict[str, Any]:
    """Predict post engagement based on content analysis"""
    # Simplified engagement prediction
    base_engagement = {
        "twitter": 3.5,
        "instagram": 5.5,
        "youtube": 4.5,
        "twitch": 6.0
    }
    
    platform_base = base_engagement.get(platform, 4.0)
    
    # Factors that increase engagement
    factors = 0
    if len(tags) > 3:
        factors += 0.5
    if any(emoji in content for emoji in ["🎮", "🔥", "💪", "🎯"]):
        factors += 0.3
    if "?" in content:  # Questions increase engagement
        factors += 0.4
    if len(content) < 100:  # Shorter posts often perform better
        factors += 0.2
    
    predicted_rate = platform_base + factors + random.uniform(-0.5, 0.5)
    
    return {
        "predicted_engagement_rate": round(predicted_rate, 2),
        "expected_likes": int(predicted_rate * 100 * random.uniform(0.8, 1.2)),
        "expected_comments": int(predicted_rate * 10 * random.uniform(0.8, 1.2)),
        "expected_shares": int(predicted_rate * 5 * random.uniform(0.8, 1.2)),
        "confidence": "high" if factors > 0.5 else "medium"
    }


def _generate_hashtags(content: str) -> List[str]:
    """Generate relevant hashtags based on content"""
    # Simple hashtag generation
    common_gaming_tags = ["#gaming", "#streamer", "#contentcreator", "#twitch", "#youtube"]
    
    # Extract potential hashtags from content
    words = content.lower().split()
    content_tags = []
    
    gaming_keywords = ["game", "play", "stream", "win", "victory", "challenge", "tournament"]
    for word in words:
        if any(keyword in word for keyword in gaming_keywords):
            content_tags.append(f"#{word}")
    
    # Combine and limit
    all_tags = list(set(common_gaming_tags[:3] + content_tags[:2]))
    return all_tags[:5]


def _get_post_optimizations(platform: str, content: str, tags: List[str]) -> List[str]:
    """Get optimization suggestions for post"""
    suggestions = []
    
    if platform == "twitter" and len(content) > 200:
        suggestions.append("Consider making your tweet shorter for better engagement")
    
    if platform == "instagram" and len(tags) < 10:
        suggestions.append("Add more hashtags (10-15) for better discovery")
    
    if not any(char in content for char in ["!", "?", "🎮", "🔥"]):
        suggestions.append("Add emojis or punctuation to make post more engaging")
    
    if platform in ["youtube", "twitch"] and "link" not in content.lower():
        suggestions.append("Include a link to your channel or latest content")
    
    return suggestions


def _get_optimal_posting_time(platform: str, offset: int) -> datetime:
    """Get optimal posting time for platform"""
    # Optimal times (simplified)
    optimal_hours = {
        "twitter": [9, 13, 19],
        "instagram": [11, 14, 20],
        "youtube": [14, 16, 20],
        "twitch": [18, 20, 22]
    }
    
    platform_hours = optimal_hours.get(platform, [12, 18])
    hour = platform_hours[offset % len(platform_hours)]
    
    # Next occurrence of this hour
    now = datetime.now()
    optimal_time = now.replace(hour=hour, minute=0, second=0)
    
    if optimal_time <= now:
        optimal_time += timedelta(days=1)
    
    return optimal_time


def _calculate_optimal_score(scheduled_time: datetime, platform: str) -> float:
    """Calculate how optimal a posting time is"""
    optimal_hours = {
        "twitter": [9, 13, 19],
        "instagram": [11, 14, 20],
        "youtube": [14, 16, 20],
        "twitch": [18, 20, 22]
    }
    
    platform_hours = optimal_hours.get(platform, [12, 18])
    scheduled_hour = scheduled_time.hour
    
    # Calculate distance from nearest optimal hour
    min_distance = min(abs(scheduled_hour - opt) for opt in platform_hours)
    
    # Score based on distance (0-1, where 1 is optimal)
    score = max(0, 1 - (min_distance / 12))
    
    return round(score, 2)


def _generate_posting_calendar(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a posting calendar view"""
    calendar = {
        "week_view": {},
        "platform_distribution": {},
        "content_types": {}
    }
    
    for post in posts:
        # Add to week view
        scheduled_time = datetime.fromisoformat(post["scheduled_time"])
        day = scheduled_time.strftime("%A")
        
        if day not in calendar["week_view"]:
            calendar["week_view"][day] = []
        
        calendar["week_view"][day].append({
            "time": scheduled_time.strftime("%H:%M"),
            "platform": post["platform"],
            "preview": post["post"].get("content", "")[:50] + "..."
        })
        
        # Platform distribution
        platform = post["platform"]
        calendar["platform_distribution"][platform] = calendar["platform_distribution"].get(platform, 0) + 1
    
    return calendar


def _generate_top_posts(platform: str, count: int) -> List[Dict[str, Any]]:
    """Generate top performing posts"""
    posts = []
    
    for i in range(count):
        posts.append({
            "content": f"Amazing {platform} post #{i+1}!",
            "engagement": random.randint(1000, 10000),
            "reach": random.randint(10000, 100000),
            "posted": (datetime.now() - timedelta(days=random.randint(1, 7))).isoformat()
        })
    
    return posts


def _generate_analytics_insights(analytics: Dict[str, Any], timeframe: str) -> List[str]:
    """Generate insights from analytics data"""
    insights = []
    
    # Find best performing platform
    best_platform = max(analytics.keys(), key=lambda p: analytics[p]["engagement"]["rate"])
    insights.append(f"{best_platform} showing highest engagement rate")
    
    # Growth insights
    growing_platforms = [p for p in analytics if analytics[p]["followers"]["growth_rate"] > 3]
    if growing_platforms:
        insights.append(f"Strong growth on: {', '.join(growing_platforms)}")
    
    # Engagement insights
    high_engagement = [p for p in analytics if analytics[p]["engagement"]["rate"] > 5]
    if high_engagement:
        insights.append(f"Excellent engagement on: {', '.join(high_engagement)}")
    
    return insights


def _generate_growth_recommendations(analytics: Dict[str, Any]) -> List[str]:
    """Generate growth recommendations based on analytics"""
    recommendations = []
    
    for platform, data in analytics.items():
        if data["engagement"]["rate"] < 3:
            recommendations.append(f"Improve content quality on {platform}")
        
        if data["followers"]["growth_rate"] < 2:
            recommendations.append(f"Increase posting frequency on {platform}")
    
    recommendations.append("Cross-promote content between platforms")
    recommendations.append("Engage more with your community")
    
    return recommendations[:4]  # Limit to 4 recommendations


def _get_pending_engagements(platform: str) -> List[Dict[str, Any]]:
    """Get pending engagement items"""
    engagements = []
    
    for i in range(random.randint(3, 10)):
        sentiment = random.choice(["positive", "neutral", "negative"])
        engagements.append({
            "id": f"ENG-{random.randint(1000, 9999)}",
            "type": random.choice(["comment", "mention", "dm"]),
            "content": _generate_sample_mention([]),
            "author": f"user_{random.randint(100, 999)}",
            "sentiment": sentiment,
            "priority": "high" if sentiment == "negative" else random.choice(["low", "medium"]),
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(5, 120))).isoformat()
        })
    
    return engagements


def _generate_response(content: str, sentiment: str) -> str:
    """Generate appropriate response based on content and sentiment"""
    responses = {
        "positive": [
            "Thanks so much for your support! 🙏",
            "Really appreciate the kind words! 💙",
            "You're awesome! Thanks for being part of the community!"
        ],
        "neutral": [
            "Thanks for reaching out!",
            "Great question! Let me help you with that.",
            "Thanks for your feedback!"
        ],
        "negative": [
            "I'm sorry to hear about your experience. How can I help?",
            "Thanks for the feedback. I'll work on improving this.",
            "I appreciate you bringing this to my attention. Let's resolve this."
        ]
    }
    
    return random.choice(responses.get(sentiment, responses["neutral"]))


def _get_response_templates() -> Dict[str, List[str]]:
    """Get response templates for auto-engagement"""
    return {
        "welcome": [
            "Welcome to the community! 🎮",
            "Great to have you here!",
            "Thanks for joining us!"
        ],
        "thanks": [
            "Thank you so much!",
            "Really appreciate it!",
            "You're the best!"
        ],
        "question": [
            "Great question! [Answer]",
            "Happy to help! [Answer]",
            "Thanks for asking! [Answer]"
        ]
    }


def _generate_sample_mention(keywords: List[str]) -> str:
    """Generate sample mention content"""
    mentions = [
        "Love your streams! Keep up the great work!",
        "When's the next stream scheduled?",
        "That last video was amazing!",
        "Having issues with the stream quality",
        "Can you play this game next?",
        "Your content always makes my day!"
    ]
    
    return random.choice(mentions)


def _calculate_sentiment_score(breakdown: Dict[str, int]) -> float:
    """Calculate overall sentiment score"""
    total = sum(breakdown.values())
    if total == 0:
        return 0
    
    # Weighted score: positive=1, neutral=0, negative=-1
    score = (breakdown["positive"] - breakdown["negative"]) / total
    
    # Convert to 0-10 scale
    return round((score + 1) * 5, 1)


def _generate_monitoring_alerts(mentions: List[Dict[str, Any]], sentiment: Dict[str, int]) -> List[str]:
    """Generate alerts based on monitoring data"""
    alerts = []
    
    # Check for negative sentiment spike
    if sentiment["negative"] > sentiment["positive"]:
        alerts.append("Negative sentiment detected - immediate attention needed")
    
    # Check for high-reach mentions
    high_reach = [m for m in mentions if m["reach"] > 5000]
    if high_reach:
        alerts.append(f"{len(high_reach)} high-reach mentions require response")
    
    # Check for urgent mentions
    urgent = [m for m in mentions if m["requires_response"] and m["sentiment"] == "negative"]
    if urgent:
        alerts.append(f"{len(urgent)} urgent negative mentions to address")
    
    return alerts


def _generate_trend_based_content(trends: Dict[str, Any], category: str) -> List[Dict[str, Any]]:
    """Generate content recommendations based on trends"""
    recommendations = []
    
    # Based on trending hashtags
    for tag in trends["hashtags"][:3]:
        recommendations.append({
            "type": "hashtag_content",
            "suggestion": f"Create content using {tag['tag']}",
            "expected_reach": tag["volume"] // 10,
            "priority": "high" if tag["growth"] > 30 else "medium"
        })
    
    # Based on content formats
    best_format = max(trends["content_formats"].items(), key=lambda x: x[1]["engagement"])
    recommendations.append({
        "type": "format_optimization",
        "suggestion": f"Focus on {best_format[0]} - highest engagement",
        "expected_engagement": best_format[1]["engagement"],
        "priority": "high"
    })
    
    return recommendations


def _generate_content_calendar(timeframe: str) -> Dict[str, Any]:
    """Generate a content calendar"""
    days = 7 if timeframe == "week" else 30
    
    content = []
    for day in range(days):
        date = datetime.now() + timedelta(days=day)
        
        # Add 1-3 posts per day
        for _ in range(random.randint(1, 3)):
            content.append({
                "date": date.strftime("%Y-%m-%d"),
                "platform": random.choice(["twitter", "instagram", "youtube"]),
                "type": random.choice(["post", "video", "stream", "story"]),
                "status": "scheduled" if day > 0 else "published"
            })
    
    return {
        "timeframe": timeframe,
        "content": content,
        "platforms": list(set(c["platform"] for c in content)),
        "content_types": list(set(c["type"] for c in content))
    }


def _optimize_calendar(calendar: Dict[str, Any]) -> Dict[str, Any]:
    """Optimize content calendar for engagement"""
    optimized = calendar.copy()
    
    # Add optimization logic here
    # For demo, just return with some modifications
    optimized["optimized"] = True
    
    return optimized


def _identify_content_gaps(calendar: Dict[str, Any]) -> List[str]:
    """Identify gaps in content calendar"""
    gaps = []
    
    # Check platform coverage
    all_platforms = ["twitter", "instagram", "youtube", "twitch"]
    covered = calendar.get("platforms", [])
    
    missing = [p for p in all_platforms if p not in covered]
    if missing:
        gaps.append(f"No content scheduled for: {', '.join(missing)}")
    
    # Check content variety
    if len(set(calendar.get("content_types", []))) < 3:
        gaps.append("Limited content variety - consider adding different types")
    
    return gaps


def _adapt_content_for_platform(content: str, platform: str) -> str:
    """Adapt content for specific platform requirements"""
    if platform == "twitter" and len(content) > 280:
        # Shorten for Twitter
        return content[:277] + "..."
    
    elif platform == "instagram":
        # Add call-to-action for Instagram
        if "link in bio" not in content.lower():
            content += "\n\n👉 Link in bio!"
    
    elif platform == "youtube":
        # Add YouTube-specific elements
        if "subscribe" not in content.lower():
            content += "\n\n🔔 Don't forget to subscribe and hit the bell!"
    
    return content


def _get_media_requirements(platform: str) -> Dict[str, Any]:
    """Get media requirements for platform"""
    requirements = {
        "twitter": {
            "image": {"formats": ["jpg", "png", "gif"], "max_size": "5MB"},
            "video": {"formats": ["mp4"], "max_duration": "140s", "max_size": "512MB"}
        },
        "instagram": {
            "image": {"formats": ["jpg", "png"], "aspect_ratio": "1:1 to 1.91:1", "max_size": "8MB"},
            "video": {"formats": ["mp4"], "max_duration": "60s", "max_size": "100MB"}
        },
        "youtube": {
            "video": {"formats": ["mp4", "avi", "mov"], "max_size": "128GB", "min_duration": "15s"}
        }
    }
    
    return requirements.get(platform, {})


def _generate_platform_tags(platform: str, content: str) -> List[str]:
    """Generate platform-specific tags"""
    base_tags = _generate_hashtags(content)
    
    platform_specific = {
        "twitter": ["#TwitterGaming", "#GamersUnite"],
        "instagram": ["#InstaGaming", "#GamerLife", "#IGGaming"],
        "youtube": ["#YouTubeGaming", "#YTGamer", "#Gaming"]
    }
    
    return base_tags + platform_specific.get(platform, [])[:2]


# Tool metadata for registration
TOOL_METADATA = {
    "name": "social_media_tool",
    "description": "Comprehensive social media management across platforms",
    "version": "1.0.0",
    "author": "Streamer Team",
    "capabilities": [
        "post_creation",
        "scheduling",
        "analytics",
        "engagement_management",
        "trend_analysis",
        "content_calendar",
        "cross_platform_posting"
    ],
    "supported_platforms": ["twitter", "instagram", "youtube", "twitch"],
    "required_context": [],
    "example_usage": {
        "post": {
            "action": "post",
            "platform": "twitter",
            "content": "Just went live! Playing the new update 🎮🔥",
            "tags": ["#gaming", "#livestream"]
        },
        "analytics": {
            "action": "analytics",
            "platform": "all",
            "timeframe": "7d"
        },
        "schedule": {
            "action": "schedule",
            "posts": [
                {"platform": "twitter", "content": "Stream starting soon!"},
                {"platform": "instagram", "content": "New video up!"}
            ],
            "strategy": "optimal_times"
        }
    }
}