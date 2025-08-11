"""
Tests for anyio task group optimization in resolve_mapped_ctx.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from ctxinject.inject import get_mapped_ctx, resolve_mapped_ctx
from ctxinject.model import DependsInject


# Test dependencies with controlled timing
async def fast_dependency() -> str:
    """Fast dependency for testing."""
    await asyncio.sleep(0.01)
    return "fast_result"


async def slow_dependency() -> str:
    """Slower dependency for testing."""
    await asyncio.sleep(0.05)
    return "slow_result"


async def failing_dependency() -> str:
    """Dependency that fails for fail-fast testing."""
    await asyncio.sleep(0.03)
    raise ValueError("Intentional failure")


async def very_slow_dependency() -> str:
    """Very slow dependency that should be cancelled in fail-fast."""
    await asyncio.sleep(0.2)  # This should be cancelled before completing
    return "very_slow_result"


@pytest.mark.asyncio
class TestAnyioTaskGroupOptimization:
    """Tests for anyio task group optimization."""
    
    async def test_multiple_async_dependencies_success(self):
        """Test that multiple async dependencies resolve concurrently."""
        async def test_func(
            fast: str = DependsInject(fast_dependency),
            slow: str = DependsInject(slow_dependency),
        ) -> str:
            return f"{fast},{slow}"
        
        context = {}
        mapped = get_mapped_ctx(test_func, context)
        
        start = time.perf_counter()
        resolved = await resolve_mapped_ctx(context, mapped)
        end = time.perf_counter()
        
        # Should resolve concurrently (max time ~50ms, not sum ~60ms)
        elapsed_ms = (end - start) * 1000
        assert elapsed_ms < 80  # Allow some overhead
        
        # Results should be correct
        assert resolved["fast"] == "fast_result"
        assert resolved["slow"] == "slow_result"
    
    async def test_single_async_dependency_fallback(self):
        """Test that single async dependency uses asyncio.gather fallback."""
        async def test_func(
            single: str = DependsInject(fast_dependency)
        ) -> str:
            return single
        
        context = {}
        mapped = get_mapped_ctx(test_func, context)
        
        # Should work correctly with single dependency
        resolved = await resolve_mapped_ctx(context, mapped)
        assert resolved["single"] == "fast_result"
    
    async def test_fail_fast_behavior(self):
        """Test that anyio task groups provide fail-fast behavior."""
        async def test_func(
            fast: str = DependsInject(fast_dependency),
            failing: str = DependsInject(failing_dependency),
            very_slow: str = DependsInject(very_slow_dependency),
        ) -> str:
            return f"{fast},{failing},{very_slow}"
        
        context = {}
        mapped = get_mapped_ctx(test_func, context)
        
        start = time.perf_counter()
        
        with pytest.raises(ValueError, match="Intentional failure"):
            await resolve_mapped_ctx(context, mapped)
        
        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        
        # Should fail fast (~30ms) rather than waiting for very_slow_dependency (200ms)
        assert elapsed_ms < 100, f"Expected fail-fast ~30ms, got {elapsed_ms:.1f}ms"
    
    async def test_mixed_sync_async_dependencies(self):
        """Test mixing sync and async dependencies."""
        def sync_dependency() -> str:
            return "sync_result"
        
        async def test_func(
            sync_val: str = DependsInject(sync_dependency),
            async_val: str = DependsInject(fast_dependency),
        ) -> str:
            return f"{sync_val},{async_val}"
        
        context = {}
        mapped = get_mapped_ctx(test_func, context)
        
        resolved = await resolve_mapped_ctx(context, mapped)
        assert resolved["sync_val"] == "sync_result"
        assert resolved["async_val"] == "fast_result"
    
    async def test_no_anyio_fallback(self):
        """Test fallback to asyncio.gather when anyio unavailable."""
        async def test_func(
            dep1: str = DependsInject(fast_dependency),
            dep2: str = DependsInject(slow_dependency),
        ) -> str:
            return f"{dep1},{dep2}"
        
        context = {}
        mapped = get_mapped_ctx(test_func, context)
        
        # Mock HAS_ANYIO to False to test fallback
        with patch('ctxinject.inject.HAS_ANYIO', False):
            resolved = await resolve_mapped_ctx(context, mapped)
            
        # Should still work correctly using asyncio.gather
        assert resolved["dep1"] == "fast_result"
        assert resolved["dep2"] == "slow_result"
    
    async def test_exception_preservation(self):
        """Test that original exceptions are preserved without wrapping."""
        async def test_func(
            failing: str = DependsInject(failing_dependency),
        ) -> str:
            return failing
        
        context = {}
        mapped = get_mapped_ctx(test_func, context)
        
        # Should get original exception, not wrapped in ExceptionGroup
        with pytest.raises(ValueError, match="Intentional failure") as exc_info:
            await resolve_mapped_ctx(context, mapped)
        
        # Should be original exception, not wrapped
        assert type(exc_info.value) is ValueError
        assert str(exc_info.value) == "Intentional failure"
    
    async def test_empty_mapped_context(self):
        """Test handling of empty mapped context."""
        resolved = await resolve_mapped_ctx({}, {})
        assert resolved == {}
    
    async def test_only_sync_dependencies(self):
        """Test that only sync dependencies don't trigger async path."""
        def sync_dep1() -> str:
            return "sync1"
        
        def sync_dep2() -> int:
            return 42
        
        async def test_func(
            val1: str = DependsInject(sync_dep1),
            val2: int = DependsInject(sync_dep2),
        ) -> str:
            return f"{val1}:{val2}"
        
        context = {}
        mapped = get_mapped_ctx(test_func, context)
        
        resolved = await resolve_mapped_ctx(context, mapped)
        assert resolved["val1"] == "sync1"
        assert resolved["val2"] == 42


@pytest.mark.asyncio 
class TestPerformanceComparison:
    """Performance comparison tests."""
    
    async def test_concurrent_vs_sequential_timing(self):
        """Verify that async dependencies run concurrently, not sequentially."""
        # Each dependency takes ~30ms
        async def dep_30ms_1() -> str:
            await asyncio.sleep(0.03)
            return "dep1"
        
        async def dep_30ms_2() -> str:
            await asyncio.sleep(0.03)
            return "dep2"
        
        async def dep_30ms_3() -> str:
            await asyncio.sleep(0.03)
            return "dep3"
        
        async def test_func(
            d1: str = DependsInject(dep_30ms_1),
            d2: str = DependsInject(dep_30ms_2),
            d3: str = DependsInject(dep_30ms_3),
        ) -> str:
            return f"{d1},{d2},{d3}"
        
        context = {}
        mapped = get_mapped_ctx(test_func, context)
        
        start = time.perf_counter()
        resolved = await resolve_mapped_ctx(context, mapped)
        end = time.perf_counter()
        
        elapsed_ms = (end - start) * 1000
        
        # Concurrent: ~30ms, Sequential would be: ~90ms
        assert elapsed_ms < 60, f"Expected concurrent ~30ms, got {elapsed_ms:.1f}ms"
        assert resolved["d1"] == "dep1"
        assert resolved["d2"] == "dep2"  
        assert resolved["d3"] == "dep3"