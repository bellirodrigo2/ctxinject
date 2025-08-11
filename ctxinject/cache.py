"""
Simple dependency caching for ctxinject - FastAPI style.

This module provides a simple cache that stores whatever you put in it,
with no magic detection. Developer controls what gets cached.
"""

from typing import Any, Dict


class DependencyCache:
    """
    Simple cache for dependency resolution results.

    Following FastAPI's approach: no automatic safety detection,
    developer explicitly controls what gets cached via usage patterns.
    """

    def __init__(self) -> None:
        """Initialize empty dependency cache."""
        self._cache: Dict[str, Any] = {}
        self._stats = {"hits": 0, "misses": 0}

    def get(self, key: str) -> tuple[bool, Any]:
        """
        Get cached value for a dependency.

        Args:
            key: Dependency key to lookup

        Returns:
            Tuple of (found, value) where found indicates cache hit
        """
        if key in self._cache:
            self._stats["hits"] += 1
            return True, self._cache[key]

        self._stats["misses"] += 1
        return False, None

    def set(self, key: str, value: Any) -> None:
        """
        Cache a resolved dependency value.

        Args:
            key: Dependency key
            value: Resolved value to cache

        Note:
            No safety checks - developer responsibility to only cache safe values.
            For stateful resources (DB sessions, connections), don't use caching.
        """
        self._cache[key] = value

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def size(self) -> int:
        """Get number of cached items."""
        return len(self._cache)

    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return self._stats.copy()

    def __contains__(self, key: str) -> bool:
        """Check if key is in cache."""
        return key in self._cache

    def __len__(self) -> int:
        """Get cache size."""
        return len(self._cache)


def create_dependency_cache() -> DependencyCache:
    """
    Create a dependency cache.

    Returns:
        DependencyCache instance

    Example:
        ```python
        # Create cache - you control what gets cached
        cache = create_dependency_cache()

        # Use with resolve_mapped_ctx for performance
        mapped = get_mapped_ctx(my_func, context)
        resolved = await resolve_mapped_ctx(context, mapped, cache=cache)

        # Safe: mostly immutable config/settings
        # Unsafe: DB sessions, connections, clients (don't cache these!)
        ```
    """
    return DependencyCache()
