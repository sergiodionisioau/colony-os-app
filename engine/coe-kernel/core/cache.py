"""Redis Caching Layer for COE Kernel.

Implements caching for frequently accessed data:
- Business statistics
- Memory context
- Embedding results
- Health status
- Module metadata
"""

import os
import json
import hashlib
import pickle
from typing import Any, Dict, List, Optional, Union
from functools import wraps
import time

# Cache TTL configuration (seconds)
CACHE_TTL = {
    'business_stats': 300,      # 5 minutes
    'business_detail': 600,     # 10 minutes
    'memory_context': 60,       # 1 minute
    'embedding': 3600,          # 1 hour
    'health_status': 30,        # 30 seconds
    'module_metadata': 600,     # 10 minutes
    'api_response': 120,        # 2 minutes
}


class CacheKeyBuilder:
    """Build cache keys with proper namespacing."""
    
    PREFIX = "coe"
    
    @classmethod
    def business_stats(cls, business_id: Optional[str] = None) -> str:
        if business_id:
            return f"{cls.PREFIX}:biz:stats:{business_id}"
        return f"{cls.PREFIX}:biz:stats:all"
    
    @classmethod
    def business_detail(cls, business_id: str) -> str:
        return f"{cls.PREFIX}:biz:{business_id}"
    
    @classmethod
    def memory_search(cls, query_hash: str) -> str:
        return f"{cls.PREFIX}:mem:search:{query_hash}"
    
    @classmethod
    def embedding(cls, text_hash: str) -> str:
        return f"{cls.PREFIX}:emb:{text_hash}"
    
    @classmethod
    def health(cls, service: str) -> str:
        return f"{cls.PREFIX}:health:{service}"
    
    @classmethod
    def module_metadata(cls, module_name: str) -> str:
        return f"{cls.PREFIX}:mod:{module_name}"
    
    @classmethod
    def api_response(cls, endpoint: str, params_hash: str) -> str:
        return f"{cls.PREFIX}:api:{endpoint}:{params_hash}"


class RedisCache:
    """Redis cache wrapper with serialization."""
    
    def __init__(self, host: str = None, port: int = None, password: str = None):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", "6379"))
        self.password = password or os.getenv("REDIS_PASSWORD")
        self._redis = None
        self._connected = False
        
    def _connect(self):
        """Lazy connection to Redis."""
        if self._connected:
            return
        
        try:
            import redis
            self._redis = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=False,  # We handle serialization
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=50
            )
            self._redis.ping()
            self._connected = True
        except Exception as e:
            print(f"⚠️  Redis cache unavailable: {e}")
            self._connected = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        self._connect()
        if not self._connected:
            return None
        
        try:
            data = self._redis.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            print(f"⚠️  Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        self._connect()
        if not self._connected:
            return False
        
        try:
            serialized = pickle.dumps(value)
            self._redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"⚠️  Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        self._connect()
        if not self._connected:
            return False
        
        try:
            self._redis.delete(key)
            return True
        except Exception as e:
            print(f"⚠️  Cache delete error: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        self._connect()
        if not self._connected:
            return 0
        
        try:
            keys = self._redis.keys(pattern)
            if keys:
                return self._redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"⚠️  Cache invalidate error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._connect()
        if not self._connected:
            return {"connected": False}
        
        try:
            info = self._redis.info()
            return {
                "connected": True,
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "hit_rate": self._calculate_hit_rate(info)
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calculate cache hit rate."""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return round(hits / total * 100, 2)


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


def cached(ttl: int = 300, key_builder=None):
    """Decorator for caching function results.
    
    Args:
        ttl: Cache time-to-live in seconds
        key_builder: Optional function to build cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default: hash of function name and arguments
                key_data = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                cache_key = f"coe:func:{hashlib.md5(key_data.encode()).hexdigest()}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern: str) -> int:
    """Invalidate cache keys matching pattern."""
    cache = get_cache()
    return cache.invalidate_pattern(pattern)


# Specific cache helpers for COE Kernel

def cache_business_stats(business_id: Optional[str] = None, stats: Dict = None) -> bool:
    """Cache business statistics."""
    if stats is None:
        return False
    cache = get_cache()
    key = CacheKeyBuilder.business_stats(business_id)
    return cache.set(key, stats, CACHE_TTL['business_stats'])


def get_cached_business_stats(business_id: Optional[str] = None) -> Optional[Dict]:
    """Get cached business statistics."""
    cache = get_cache()
    key = CacheKeyBuilder.business_stats(business_id)
    return cache.get(key)


def cache_embedding(text: str, embedding: List[float]) -> bool:
    """Cache embedding result."""
    text_hash = hashlib.md5(text.encode()).hexdigest()
    cache = get_cache()
    key = CacheKeyBuilder.embedding(text_hash)
    return cache.set(key, embedding, CACHE_TTL['embedding'])


def get_cached_embedding(text: str) -> Optional[List[float]]:
    """Get cached embedding."""
    text_hash = hashlib.md5(text.encode()).hexdigest()
    cache = get_cache()
    key = CacheKeyBuilder.embedding(text_hash)
    return cache.get(key)


def cache_memory_search(query: str, results: List[Dict]) -> bool:
    """Cache memory search results."""
    query_hash = hashlib.md5(query.encode()).hexdigest()
    cache = get_cache()
    key = CacheKeyBuilder.memory_search(query_hash)
    return cache.set(key, results, CACHE_TTL['memory_context'])


def get_cached_memory_search(query: str) -> Optional[List[Dict]]:
    """Get cached memory search results."""
    query_hash = hashlib.md5(query.encode()).hexdigest()
    cache = get_cache()
    key = CacheKeyBuilder.memory_search(query_hash)
    return cache.get(key)


def invalidate_business_cache(business_id: Optional[str] = None) -> int:
    """Invalidate business-related cache."""
    cache = get_cache()
    if business_id:
        return cache.invalidate_pattern(f"coe:biz:*{business_id}*")
    return cache.invalidate_pattern("coe:biz:*")
