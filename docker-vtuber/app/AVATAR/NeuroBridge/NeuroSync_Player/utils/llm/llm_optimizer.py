"""
LLM Optimizer - Fast response caching and intelligent model selection
Created: 2025-08-11 18:15
"""
import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from collections import OrderedDict
import redis
import re

class LLMOptimizer:
    """Optimizes LLM responses through caching and intelligent model selection"""
    
    def __init__(self, redis_url: str = "redis://redis_scb:6379/0", cache_size: int = 100):
        self.cache_size = cache_size
        self.memory_cache = OrderedDict()  # In-memory LRU cache
        
        # Try to connect to Redis for persistent caching
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            self.redis_enabled = True
            print("[LLMOptimizer] Redis connected for persistent caching")
        except:
            self.redis_client = None
            self.redis_enabled = False
            print("[LLMOptimizer] Redis unavailable, using memory cache only")
        
        # Pre-generated responses per character
        self.common_responses = {
            'trader': {
                'greetings': [
                    "Hey there! Ready to dive into the markets?",
                    "Welcome back, trader! What's on your watchlist today?",
                    "Good to see you! The markets are looking interesting today."
                ],
                'acknowledgments': {
                    'yes': "Absolutely, let's get to it!",
                    'no': "Alright, no problem. What else can I help with?",
                    'okay': "Perfect! Moving right along.",
                    'thanks': "You're welcome! Always here to help with your trading."
                }
            },
            'educator': {
                'greetings': [
                    "Hello! I'm excited to learn together today.",
                    "Welcome! What would you like to explore?",
                    "Hi there! Ready for another learning adventure?"
                ],
                'acknowledgments': {
                    'yes': "Excellent! Let's continue our exploration.",
                    'no': "That's fine. Let's try a different approach.",
                    'okay': "Great! Let's proceed with the lesson.",
                    'thanks': "You're most welcome! Learning is a journey we share."
                }
            },
            'streamer': {
                'greetings': [
                    "Hey hey! Welcome to the stream!",
                    "What's up everyone! Ready for some fun?",
                    "Yo! Great to have you here!"
                ],
                'acknowledgments': {
                    'yes': "Let's gooo! This is gonna be awesome!",
                    'no': "No worries! We'll find something else fun!",
                    'okay': "Sweet! Let's keep the energy going!",
                    'thanks': "No problem! That's what we're here for!"
                }
            }
        }
    
    def get_query_complexity(self, text: str) -> str:
        """Determine query complexity for model selection"""
        text_lower = text.lower()
        word_count = len(text.split())
        
        # Simple queries - use tinyllama (fastest)
        if word_count <= 5:
            simple_patterns = [
                r'^(hi|hello|hey|yo|sup)[\s!?]*$',
                r'^(yes|no|okay|ok|sure|thanks|thank you)[\s!?]*$',
                r'^(good|great|nice|cool|awesome)[\s!?]*$',
                r'^what[\'s]* (up|new)[\s!?]*$',
                r'^how are you[\s!?]*$'
            ]
            for pattern in simple_patterns:
                if re.match(pattern, text_lower):
                    return 'simple'
        
        # Complex queries - use llama3.2:3b
        complex_indicators = [
            'explain', 'analyze', 'compare', 'describe in detail',
            'comprehensive', 'step by step', 'how does', 'why does',
            'tell me about', 'what is the difference'
        ]
        if any(indicator in text_lower for indicator in complex_indicators):
            return 'complex'
        
        # Medium complexity - use phi-2
        if word_count > 20 or '?' in text:
            return 'medium'
        
        return 'simple' if word_count < 10 else 'medium'
    
    def select_model(self, text: str, provider: str = 'ollama') -> str:
        """Select optimal model based on query complexity"""
        if provider != 'ollama':
            return None  # Use default for non-Ollama providers
        
        complexity = self.get_query_complexity(text)
        
        model_map = {
            'simple': 'tinyllama:latest',    # 1.1B params, ~100ms
            'medium': 'phi-2:latest',         # 2.7B params, ~300ms
            'complex': 'llama3.2:3b'          # 3B params, ~500ms
        }
        
        selected = model_map.get(complexity, 'llama3.2:3b')
        print(f"[LLMOptimizer] Query complexity: {complexity}, using model: {selected}")
        return selected
    
    def get_cache_key(self, text: str, character: Optional[str] = None) -> str:
        """Generate cache key for the input"""
        # Normalize text for better cache hits
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        normalized = re.sub(r'[!?.,]+$', '', normalized)  # Remove trailing punctuation
        
        # Include character in key for character-specific responses
        cache_string = f"{character or 'default'}:{normalized}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def check_common_response(self, text: str, character: str) -> Optional[str]:
        """Check if this is a common query with pre-generated response"""
        text_lower = text.lower().strip()
        
        # Check greetings
        greeting_patterns = ['hello', 'hi', 'hey', 'yo', 'sup', 'greetings']
        if any(pattern in text_lower for pattern in greeting_patterns):
            responses = self.common_responses.get(character, {}).get('greetings', [])
            if responses:
                import random
                return random.choice(responses)
        
        # Check acknowledgments
        ack_map = {
            'yes': ['yes', 'yeah', 'yep', 'sure', 'absolutely', 'definitely'],
            'no': ['no', 'nope', 'nah', 'not really', 'negative'],
            'okay': ['okay', 'ok', 'alright', 'fine', 'sounds good'],
            'thanks': ['thanks', 'thank you', 'thx', 'ty', 'appreciated']
        }
        
        for ack_type, patterns in ack_map.items():
            if any(pattern == text_lower or f"{pattern}!" == text_lower for pattern in patterns):
                response = self.common_responses.get(character, {}).get('acknowledgments', {}).get(ack_type)
                if response:
                    return response
        
        return None
    
    def get_cached_response(self, text: str, character: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if available"""
        # First check common responses
        common = self.check_common_response(text, character or 'streamer')
        if common:
            return {
                'response': common,
                'cache_hit': 'common',
                'latency_ms': 1
            }
        
        # Check cache
        cache_key = self.get_cache_key(text, character)
        
        # Try memory cache first
        if cache_key in self.memory_cache:
            # Move to end (LRU)
            self.memory_cache.move_to_end(cache_key)
            print(f"[LLMOptimizer] Memory cache hit for: {text[:30]}...")
            return {
                'response': self.memory_cache[cache_key],
                'cache_hit': 'memory',
                'latency_ms': 2
            }
        
        # Try Redis if available
        if self.redis_enabled:
            try:
                cached = self.redis_client.get(f"llm_cache:{cache_key}")
                if cached:
                    response_data = json.loads(cached)
                    # Also store in memory cache
                    self.store_in_memory_cache(cache_key, response_data['response'])
                    print(f"[LLMOptimizer] Redis cache hit for: {text[:30]}...")
                    return {
                        'response': response_data['response'],
                        'cache_hit': 'redis',
                        'latency_ms': 5
                    }
            except Exception as e:
                print(f"[LLMOptimizer] Redis cache error: {e}")
        
        return None
    
    def store_response(self, text: str, response: str, character: Optional[str] = None, ttl: int = 3600):
        """Store response in cache"""
        cache_key = self.get_cache_key(text, character)
        
        # Store in memory cache
        self.store_in_memory_cache(cache_key, response)
        
        # Store in Redis if available
        if self.redis_enabled:
            try:
                cache_data = {
                    'response': response,
                    'timestamp': time.time(),
                    'character': character
                }
                self.redis_client.setex(
                    f"llm_cache:{cache_key}",
                    ttl,
                    json.dumps(cache_data)
                )
            except Exception as e:
                print(f"[LLMOptimizer] Redis store error: {e}")
    
    def store_in_memory_cache(self, key: str, value: str):
        """Store in memory cache with LRU eviction"""
        if key in self.memory_cache:
            self.memory_cache.move_to_end(key)
        else:
            self.memory_cache[key] = value
            if len(self.memory_cache) > self.cache_size:
                self.memory_cache.popitem(last=False)
    
    def optimize_context(self, chat_history: List[Dict], max_exchanges: int = 3) -> List[Dict]:
        """Optimize chat history to reduce token count"""
        if not chat_history:
            return []
        
        # Keep only the last N exchanges
        if len(chat_history) > max_exchanges:
            optimized = chat_history[-max_exchanges:]
            print(f"[LLMOptimizer] Reduced context from {len(chat_history)} to {max_exchanges} exchanges")
            return optimized
        
        return chat_history
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            'memory_cache_size': len(self.memory_cache),
            'redis_enabled': self.redis_enabled,
            'memory_cache_keys': list(self.memory_cache.keys())[:10]  # First 10 keys
        }
        
        if self.redis_enabled:
            try:
                # Count Redis cache entries
                keys = self.redis_client.keys("llm_cache:*")
                stats['redis_cache_size'] = len(keys)
            except:
                stats['redis_cache_size'] = 0
        
        return stats


# Global optimizer instance
_optimizer = None

def get_optimizer() -> LLMOptimizer:
    """Get or create the global optimizer instance"""
    global _optimizer
    if _optimizer is None:
        _optimizer = LLMOptimizer()
    return _optimizer