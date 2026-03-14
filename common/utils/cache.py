"""
Cache utilities for the Finance Chatbot.
Provides in-memory caching with TTL support.
"""

from datetime import datetime, timedelta
from typing import Any, Optional, Callable, TypeVar
from functools import wraps
from collections import OrderedDict
from threading import Lock

T = TypeVar('T')


class TTLCache:
    """
    Simple in-memory cache with TTL (Time To Live) support.
    Thread-safe with LRU eviction.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of items
            default_ttl: Default TTL in seconds
        """
        self._cache: OrderedDict[str, tuple] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry = self._cache[key]
            
            if datetime.now() > expiry:
                del self._cache[key]
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            return value
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self._default_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)
        
        with self._lock:
            self._cache[key] = (value, expiry)
            self._cache.move_to_end(key)
            
            # Evict oldest if over capacity
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        with self._lock:
            now = datetime.now()
            expired = [k for k, (v, exp) in self._cache.items() if now > exp]
            for k in expired:
                del self._cache[k]
            return len(expired)
    
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "default_ttl": self._default_ttl,
            }


# Global cache instances
_caches: dict = {}

def get_cache(name: str = "default", max_size: int = 1000, ttl: int = 60) -> TTLCache:
    """Get or create a named cache instance."""
    if name not in _caches:
        _caches[name] = TTLCache(max_size=max_size, default_ttl=ttl)
    return _caches[name]


def cache_with_ttl(ttl: int = 60, cache_name: str = "default"):
    """
    Decorator to cache function results with TTL.
    
    Args:
        ttl: Time to live in seconds
        cache_name: Name of cache to use
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            cache = get_cache(cache_name)
            
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Check cache
            cached = cache.get(key)
            if cached is not None:
                return cached
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        
        return wrapper
    return decorator


def async_cache_with_ttl(ttl: int = 60, cache_name: str = "default"):
    """
    Decorator to cache async function results with TTL.
    
    Args:
        ttl: Time to live in seconds
        cache_name: Name of cache to use
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache = get_cache(cache_name)
            
            # Create cache key
            key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Check cache
            cached = cache.get(key)
            if cached is not None:
                return cached
            
            # Call async function and cache result
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        
        return wrapper
    return decorator
