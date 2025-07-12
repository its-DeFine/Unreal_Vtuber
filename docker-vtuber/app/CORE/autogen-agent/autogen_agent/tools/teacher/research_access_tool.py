"""Research Access Tool for Educator Team
================================

Provides access to educational resources, research papers, and learning materials from the internet.
"""

import json
import logging
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from ..base_tool import BaseTool, ToolResult, ToolParameter, ToolExecutionContext, ToolStatus


class ResearchAccessTool(BaseTool):
    """Tool for accessing educational resources and research materials from internet sources"""
    
    def __init__(self):
        super().__init__(
            name="research_access_tool",
            description="Access educational resources, research papers, and learning materials from the internet",
            category="teacher",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query for educational content",
                    required=True
                ),
                ToolParameter(
                    name="resource_type",
                    type="string", 
                    description="Type of resource: papers, courses, tutorials, educational_videos",
                    required=False,
                    default="papers",
                    enum=["papers", "courses", "tutorials", "educational_videos"]
                ),
                ToolParameter(
                    name="level",
                    type="string",
                    description="Education level: beginner, intermediate, advanced",
                    required=False,
                    default="intermediate",
                    enum=["beginner", "intermediate", "advanced"]
                ),
                ToolParameter(
                    name="subject",
                    type="string",
                    description="Subject area (e.g., mathematics, science, programming, history)",
                    required=False,
                    default="general"
                )
            ]
        )
        
        # API endpoints for educational resources
        self.api_endpoints = {
            "arxiv": "http://export.arxiv.org/api/query",
            "core": "https://core.ac.uk/api-v2/search/",
            "crossref": "https://api.crossref.org/works",
            "openlibrary": "https://openlibrary.org/search.json",
            "wikipedia": "https://en.wikipedia.org/api/rest_v1/page/summary/"
        }
        
        # Rate limiting
        self.rate_limiter = {
            "arxiv": {"calls": 0, "reset_time": datetime.now(), "limit": 10},
            "crossref": {"calls": 0, "reset_time": datetime.now(), "limit": 50},
            "wikipedia": {"calls": 0, "reset_time": datetime.now(), "limit": 200}
        }
    
    async def execute(self, params: Dict[str, Any], context: Optional[ToolExecutionContext] = None) -> ToolResult:
        """Execute research material retrieval from internet sources"""
        
        try:
            query = params.get("query", "")
            resource_type = params.get("resource_type", "papers")
            level = params.get("level", "intermediate")
            subject = params.get("subject", "general")
            
            logging.info(f"📚 [RESEARCH_ACCESS] Searching for {resource_type} on: {query}")
            
            # Fetch resources based on type
            if resource_type == "papers":
                resources = await self._fetch_research_papers(query, subject)
            elif resource_type == "courses":
                resources = await self._fetch_online_courses(query, level, subject)
            elif resource_type == "tutorials":
                resources = await self._fetch_tutorials(query, level, subject)
            elif resource_type == "educational_videos":
                resources = await self._fetch_educational_videos(query, level, subject)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    data={},
                    message=f"Invalid resource type: {resource_type}"
                )
            
            # Generate learning path suggestion
            learning_path = self._generate_learning_path(query, resources, level)
            
            # Get related topics
            related_topics = await self._get_related_topics(query, subject)
            
            result = {
                "query": query,
                "resource_type": resource_type,
                "level": level,
                "subject": subject,
                "resources_found": len(resources),
                "resources": resources[:10],  # Limit to top 10
                "learning_path": learning_path,
                "related_topics": related_topics,
                "timestamp": datetime.now().isoformat()
            }
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result,
                metadata={
                    "query": query,
                    "resource_type": resource_type,
                    "source": "internet_research"
                }
            )
            
        except Exception as e:
            logging.error(f"❌ [RESEARCH_ACCESS] Error: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                data={},
                message=str(e)
            )
    
    async def _fetch_research_papers(self, query: str, subject: str) -> List[Dict[str, Any]]:
        """Fetch research papers from arXiv API"""
        
        papers = []
        
        # Check rate limit
        if not self._check_rate_limit("arxiv"):
            logging.warning("ArXiv rate limit reached")
            return papers
        
        async with aiohttp.ClientSession() as session:
            # Search arXiv
            url = self.api_endpoints["arxiv"]
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": 10,
                "sortBy": "relevance"
            }
            
            if subject != "general":
                # Add subject filter
                subject_map = {
                    "mathematics": "math",
                    "science": "physics",
                    "programming": "cs",
                    "biology": "q-bio",
                    "economics": "econ"
                }
                if subject.lower() in subject_map:
                    params["search_query"] += f" AND cat:{subject_map[subject.lower()]}"
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        content = await response.text()
                        # Parse XML response (simplified)
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(content)
                        
                        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                            title = entry.find("{http://www.w3.org/2005/Atom}title")
                            summary = entry.find("{http://www.w3.org/2005/Atom}summary")
                            authors = entry.findall("{http://www.w3.org/2005/Atom}author")
                            link = entry.find("{http://www.w3.org/2005/Atom}id")
                            published = entry.find("{http://www.w3.org/2005/Atom}published")
                            
                            author_names = []
                            for author in authors:
                                name = author.find("{http://www.w3.org/2005/Atom}name")
                                if name is not None:
                                    author_names.append(name.text)
                            
                            if title is not None and summary is not None:
                                papers.append({
                                    "title": title.text.strip(),
                                    "authors": author_names,
                                    "abstract": summary.text.strip()[:300] + "...",
                                    "url": link.text if link is not None else "",
                                    "published": published.text if published is not None else "Unknown",
                                    "source": "arXiv",
                                    "type": "research_paper"
                                })
            except Exception as e:
                logging.error(f"Error fetching from arXiv: {e}")
        
        return papers
    
    async def _fetch_online_courses(self, query: str, level: str, subject: str) -> List[Dict[str, Any]]:
        """Fetch online courses (simulated - would need API keys for real data)"""
        
        # Simulated course data
        courses = []
        
        # Generate realistic course suggestions
        course_templates = [
            {
                "title": f"Introduction to {query}",
                "provider": "Coursera",
                "level": "beginner",
                "duration": "4 weeks",
                "rating": 4.5
            },
            {
                "title": f"Advanced {query} Techniques",
                "provider": "edX",
                "level": "advanced",
                "duration": "8 weeks",
                "rating": 4.7
            },
            {
                "title": f"{query}: From Theory to Practice",
                "provider": "Udacity",
                "level": "intermediate",
                "duration": "6 weeks",
                "rating": 4.6
            },
            {
                "title": f"Mastering {query}",
                "provider": "Khan Academy",
                "level": level,
                "duration": "Self-paced",
                "rating": 4.8
            }
        ]
        
        for template in course_templates:
            if template["level"] == level or level == "intermediate":
                courses.append({
                    "title": template["title"],
                    "provider": template["provider"],
                    "level": template["level"],
                    "duration": template["duration"],
                    "rating": template["rating"],
                    "enrollment": f"{(template['rating'] * 1000):.0f} students",
                    "url": f"https://example.com/course/{query.replace(' ', '-')}",
                    "type": "online_course",
                    "certificate": "Yes" if template["provider"] in ["Coursera", "edX"] else "No"
                })
        
        return courses
    
    async def _fetch_tutorials(self, query: str, level: str, subject: str) -> List[Dict[str, Any]]:
        """Fetch tutorials and guides"""
        
        tutorials = []
        
        # Search Wikipedia for educational content
        async with aiohttp.ClientSession() as session:
            wiki_url = self.api_endpoints["wikipedia"] + quote(query)
            
            try:
                async with session.get(wiki_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        tutorials.append({
                            "title": data.get("title", query),
                            "summary": data.get("extract", "No summary available"),
                            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                            "type": "wiki_article",
                            "level": "general",
                            "source": "Wikipedia"
                        })
            except Exception as e:
                logging.warning(f"Wikipedia fetch error: {e}")
        
        # Add simulated tutorial resources
        tutorial_sources = [
            {"name": "MDN Web Docs", "focus": "web development"},
            {"name": "W3Schools", "focus": "programming"},
            {"name": "GeeksforGeeks", "focus": "computer science"},
            {"name": "TutorialsPoint", "focus": "technology"}
        ]
        
        for source in tutorial_sources:
            if subject.lower() in source["focus"] or subject == "general":
                tutorials.append({
                    "title": f"{query} Tutorial - {source['name']}",
                    "description": f"Comprehensive {level} guide to {query}",
                    "url": f"https://example.com/{source['name'].lower()}/{query.replace(' ', '-')}",
                    "type": "tutorial",
                    "level": level,
                    "source": source["name"],
                    "interactive": "Yes" if source["name"] in ["MDN Web Docs", "W3Schools"] else "No"
                })
        
        return tutorials
    
    async def _fetch_educational_videos(self, query: str, level: str, subject: str) -> List[Dict[str, Any]]:
        """Fetch educational video resources (simulated)"""
        
        videos = []
        
        # Simulated educational video content
        video_channels = [
            {"name": "Khan Academy", "focus": "all subjects", "quality": "high"},
            {"name": "Crash Course", "focus": "science and humanities", "quality": "high"},
            {"name": "3Blue1Brown", "focus": "mathematics", "quality": "exceptional"},
            {"name": "MIT OpenCourseWare", "focus": "university level", "quality": "academic"},
            {"name": "TED-Ed", "focus": "general education", "quality": "high"}
        ]
        
        for channel in video_channels:
            if subject == "general" or subject.lower() in channel["focus"]:
                videos.append({
                    "title": f"{query} - {channel['name']}",
                    "channel": channel["name"],
                    "duration": "10-15 minutes" if channel["name"] != "MIT OpenCourseWare" else "50 minutes",
                    "level": level if channel["name"] != "MIT OpenCourseWare" else "advanced",
                    "views": f"{(500 + (ord(channel['name'][0]) * 10)):.0f}K views",
                    "quality": channel["quality"],
                    "url": f"https://example.com/video/{query.replace(' ', '-')}-{channel['name'].lower()}",
                    "type": "educational_video",
                    "has_transcript": "Yes",
                    "has_exercises": "Yes" if channel["name"] == "Khan Academy" else "No"
                })
        
        return videos
    
    def _generate_learning_path(self, query: str, resources: List[Dict[str, Any]], level: str) -> Dict[str, Any]:
        """Generate a suggested learning path based on resources found"""
        
        learning_path = {
            "topic": query,
            "current_level": level,
            "estimated_time": "4-8 weeks",
            "steps": []
        }
        
        # Create learning steps based on level
        if level == "beginner":
            learning_path["steps"] = [
                {"step": 1, "action": "Watch introductory videos", "duration": "1 week"},
                {"step": 2, "action": "Read basic tutorials", "duration": "1 week"},
                {"step": 3, "action": "Complete online course", "duration": "4 weeks"},
                {"step": 4, "action": "Practice with exercises", "duration": "2 weeks"}
            ]
        elif level == "intermediate":
            learning_path["steps"] = [
                {"step": 1, "action": "Review foundational concepts", "duration": "3 days"},
                {"step": 2, "action": "Study advanced tutorials", "duration": "1 week"},
                {"step": 3, "action": "Read research papers", "duration": "2 weeks"},
                {"step": 4, "action": "Work on practical projects", "duration": "3 weeks"}
            ]
        else:  # advanced
            learning_path["steps"] = [
                {"step": 1, "action": "Read latest research papers", "duration": "2 weeks"},
                {"step": 2, "action": "Analyze case studies", "duration": "1 week"},
                {"step": 3, "action": "Contribute to open projects", "duration": "4 weeks"},
                {"step": 4, "action": "Create original content", "duration": "ongoing"}
            ]
        
        # Add resource recommendations
        learning_path["recommended_resources"] = len(resources)
        
        return learning_path
    
    async def _get_related_topics(self, query: str, subject: str) -> List[str]:
        """Get related educational topics"""
        
        # Simulated related topics based on subject
        topic_map = {
            "mathematics": ["Calculus", "Linear Algebra", "Statistics", "Discrete Math", "Number Theory"],
            "science": ["Physics", "Chemistry", "Biology", "Astronomy", "Earth Science"],
            "programming": ["Data Structures", "Algorithms", "Web Development", "Machine Learning", "Databases"],
            "history": ["World History", "Ancient Civilizations", "Modern History", "Cultural Studies", "Archaeology"],
            "general": ["Critical Thinking", "Research Methods", "Academic Writing", "Study Skills", "Problem Solving"]
        }
        
        base_topics = topic_map.get(subject.lower(), topic_map["general"])
        
        # Add query-specific related topics
        related = base_topics[:3]
        related.append(f"Advanced {query}")
        related.append(f"{query} Applications")
        
        return related
    
    def _check_rate_limit(self, service: str) -> bool:
        """Check and update rate limits"""
        
        if service not in self.rate_limiter:
            return True
        
        limiter = self.rate_limiter[service]
        
        # Reset counter if minute has passed
        if (datetime.now() - limiter["reset_time"]).seconds > 60:
            limiter["calls"] = 0
            limiter["reset_time"] = datetime.now()
        
        # Check limit
        if limiter["calls"] >= limiter["limit"]:
            return False
        
        # Increment counter
        limiter["calls"] += 1
        return True