"""
Tests for ctxinject.cache module - FastAPI style (simple, no magic).
"""

import pytest

from ctxinject.cache import DependencyCache, create_dependency_cache


class MockSession:
    """Mock database session to test that cache stores everything (developer responsibility)."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_active = True
    
    def __repr__(self):
        return f"MockSession({self.session_id})"


class TestDependencyCache:
    """Tests for DependencyCache class."""
    
    def test_cache_initialization(self):
        """Test cache starts empty with zero stats."""
        cache = DependencyCache()
        
        assert len(cache) == 0
        assert cache.size() == 0
        stats = cache.stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
    
    def test_cache_miss(self):
        """Test cache miss behavior."""
        cache = DependencyCache()
        
        found, value = cache.get("nonexistent")
        assert not found
        assert value is None
        
        stats = cache.stats()
        assert stats['misses'] == 1
        assert stats['hits'] == 0
    
    def test_cache_set_and_hit(self):
        """Test basic set and get operations."""
        cache = DependencyCache()
        
        # Set a value
        cache.set("key1", "value1")
        assert len(cache) == 1
        assert "key1" in cache
        
        # Get the value - should be a hit
        found, value = cache.get("key1")
        assert found
        assert value == "value1"
        
        stats = cache.stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 0
    
    def test_cache_stores_anything(self):
        """Test that cache stores any type - no safety checks (FastAPI style)."""
        cache = DependencyCache()
        
        # Can store any type - developer responsibility for safety
        test_values = {
            "string": "test_string",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"key": "value"},
            "none": None,
            "object": object(),
            "session": MockSession("test_session"),  # Unsafe but allowed
        }
        
        # Set all values
        for key, value in test_values.items():
            cache.set(key, value)
        
        assert len(cache) == len(test_values)
        
        # Retrieve and verify all values
        for key, expected_value in test_values.items():
            found, actual_value = cache.get(key)
            assert found, f"Key {key} not found"
            assert actual_value == expected_value, f"Value mismatch for {key}"
            assert actual_value is expected_value, f"Identity mismatch for {key}"
    
    def test_cache_overwrite(self):
        """Test that cache allows overwriting values."""
        cache = DependencyCache()
        
        # Set initial value
        cache.set("key", "original")
        found, value = cache.get("key")
        assert found and value == "original"
        
        # Overwrite with new value
        cache.set("key", "updated")
        found, value = cache.get("key")
        assert found and value == "updated"
        
        # Size should still be 1
        assert len(cache) == 1
    
    def test_cache_clear(self):
        """Test cache clearing functionality."""
        cache = DependencyCache()
        
        # Add multiple items
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert len(cache) == 3
        
        # Clear cache
        cache.clear()
        
        assert len(cache) == 0
        assert cache.size() == 0
        
        # Keys should no longer exist
        for key in ["key1", "key2", "key3"]:
            assert key not in cache
            found, _ = cache.get(key)
            assert not found
    
    def test_cache_stats_tracking(self):
        """Test detailed statistics tracking."""
        cache = DependencyCache()
        
        # Initial stats
        stats = cache.stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        
        # Add some items
        cache.set("item1", "value1")
        cache.set("item2", "value2")
        
        # Mix of hits and misses
        cache.get("item1")      # hit
        cache.get("missing1")   # miss
        cache.get("item2")      # hit  
        cache.get("missing2")   # miss
        cache.get("item1")      # hit again
        
        stats = cache.stats()
        assert stats['hits'] == 3
        assert stats['misses'] == 2
        
        # Stats should be independent copies
        stats['hits'] = 999
        new_stats = cache.stats()
        assert new_stats['hits'] == 3  # Original unchanged
    
    def test_cache_contains_operator(self):
        """Test __contains__ operator (in keyword)."""
        cache = DependencyCache()
        
        assert "nonexistent" not in cache
        
        cache.set("exists", "value")
        assert "exists" in cache
        assert "still_nonexistent" not in cache
    
    def test_cache_len_operator(self):
        """Test __len__ operator."""
        cache = DependencyCache()
        
        assert len(cache) == 0
        
        cache.set("item1", "value1")
        assert len(cache) == 1
        
        cache.set("item2", "value2")
        assert len(cache) == 2
        
        # Overwriting doesn't increase length
        cache.set("item1", "new_value")
        assert len(cache) == 2
        
        cache.clear()
        assert len(cache) == 0
    
    def test_cache_size_method(self):
        """Test size() method consistency with __len__."""
        cache = DependencyCache()
        
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
            assert cache.size() == len(cache)
            assert cache.size() == i + 1


class TestCreateDependencyCache:
    """Tests for create_dependency_cache function."""
    
    def test_create_dependency_cache(self):
        """Test the convenience factory function."""
        cache = create_dependency_cache()
        
        assert isinstance(cache, DependencyCache)
        assert len(cache) == 0
        
        # Should work like regular cache
        cache.set("test", "value")
        found, value = cache.get("test")
        assert found and value == "value"


class TestCacheEdgeCases:
    """Edge case tests for cache functionality."""
    
    def test_empty_string_key(self):
        """Test that empty string is a valid key."""
        cache = DependencyCache()
        
        cache.set("", "empty_key_value")
        found, value = cache.get("")
        assert found and value == "empty_key_value"
        
        assert "" in cache
        assert len(cache) == 1
    
    def test_none_value_caching(self):
        """Test that None can be cached as a value."""
        cache = DependencyCache()
        
        cache.set("none_key", None)
        found, value = cache.get("none_key")
        assert found  # Found should be True
        assert value is None  # But value is None
        
        assert "none_key" in cache
    
    def test_duplicate_keys_with_different_types(self):
        """Test overwriting with different value types."""
        cache = DependencyCache()
        
        # Start with string
        cache.set("key", "string_value")
        found, value = cache.get("key")
        assert found and value == "string_value"
        
        # Overwrite with int
        cache.set("key", 42)
        found, value = cache.get("key")
        assert found and value == 42
        
        # Overwrite with object
        obj = MockSession("test")
        cache.set("key", obj)
        found, value = cache.get("key")
        assert found and value is obj
        
        # Size should remain 1
        assert len(cache) == 1


@pytest.mark.integration
class TestCacheIntegrationScenarios:
    """Integration-style tests for realistic usage scenarios."""
    
    def test_config_caching_scenario(self):
        """Test typical config/settings caching scenario."""
        cache = create_dependency_cache()
        
        # Simulate app configuration that's safe to cache
        config_data = {
            "app_name": "MyApp",
            "version": "1.2.3",
            "debug": False,
            "max_connections": 100,
            "timeout": 30.0,
            "features": {"feature_a": True, "feature_b": False}
        }
        
        # Cache configuration
        for key, value in config_data.items():
            cache.set(key, value)
        
        # Verify all cached correctly
        assert len(cache) == len(config_data)
        
        for key, expected in config_data.items():
            found, actual = cache.get(key)
            assert found, f"Config key '{key}' not found in cache"
            assert actual == expected, f"Config value mismatch for '{key}'"
        
        # Simulate repeated access (hits)
        for _ in range(3):
            for key in config_data.keys():
                found, _ = cache.get(key)
                assert found
        
        stats = cache.stats()
        # Total hits = initial verification (6) + 3 rounds of repeated access (18) = 24
        assert stats['hits'] == len(config_data) * 4  # 1 verification + 3 repeated rounds
        assert stats['misses'] == 0
    
    def test_mixed_safe_unsafe_scenario(self):
        """Test scenario mixing safe config with unsafe resources."""
        cache = create_dependency_cache()
        
        # Safe to cache - immutable config
        cache.set("app_name", "MyApp")
        cache.set("port", 8080)
        cache.set("debug", True)
        
        
        # Verify safe items are cached
        assert cache.get("app_name")[0]
        assert cache.get("port")[0] 
        assert cache.get("debug")[0]
        assert len(cache) == 3
        
        # Verify unsafe items are not in cache (developer responsibility)
        assert not cache.get("db_session")[0]
        assert not cache.get("redis_client")[0]
        
        stats = cache.stats()
        assert stats['hits'] == 3  # Safe items
        assert stats['misses'] == 2  # Unsafe items not found
    
    def test_cache_performance_simulation(self):
        """Test cache behavior under repeated access patterns."""
        cache = create_dependency_cache()
        
        # Simulate expensive computations cached once
        expensive_results = {
            f"computation_{i}": f"expensive_result_{i}"
            for i in range(100)
        }
        
        # Cache all results (simulating first computation)
        for key, value in expensive_results.items():
            cache.set(key, value)
        
        # Simulate many repeated accesses (cache hits)
        hit_count = 0
        for _ in range(10):  # 10 rounds
            for key in expensive_results.keys():
                found, value = cache.get(key)
                if found:
                    hit_count += 1
        
        assert hit_count == 1000  # 10 rounds × 100 items
        
        stats = cache.stats()
        assert stats['hits'] == 1000
        assert stats['misses'] == 0
        assert len(cache) == 100