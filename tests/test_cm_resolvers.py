import asyncio
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock

import pytest

from ctxinject.resolver import (
    AsyncContextManagerResolver,
    SyncContextManagerResolver,
    contextmanager_in_threadpool,
    create_context_manager_resolver,
    detect_dependency_type,
    is_async_gen_callable,
    is_gen_callable,
)


class TestContextManagerDetection:
    """Test context manager detection utilities."""

    def test_is_gen_callable_with_generator_function(self):
        """Test detection of generator functions."""

        @contextmanager
        def sync_cm():
            yield "resource"

        def regular_generator():
            yield "item"

        assert is_gen_callable(sync_cm)
        assert is_gen_callable(regular_generator)

    def test_is_gen_callable_with_callable_object(self):
        """Test detection of callable objects with generator __call__."""

        class GeneratorCallable:
            def __call__(self):
                yield "resource"

        obj = GeneratorCallable()
        assert is_gen_callable(obj)

    def test_is_async_gen_callable_with_async_generator(self):
        """Test detection of async generator functions."""

        @asynccontextmanager
        async def async_cm():
            yield "resource"

        async def regular_async_generator():
            yield "item"

        assert is_async_gen_callable(async_cm)
        assert is_async_gen_callable(regular_async_generator)

    def test_detect_dependency_type_categorization(self):
        """Test dependency type detection."""

        @contextmanager
        def sync_cm():
            yield "sync"

        @asynccontextmanager
        async def async_cm():
            yield "async"

        async def async_func():
            return "async"

        def sync_func():
            return "sync"

        assert detect_dependency_type(sync_cm) == "sync_context_manager"
        assert detect_dependency_type(async_cm) == "async_context_manager"
        assert detect_dependency_type(async_func) == "async_function"
        assert detect_dependency_type(sync_func) == "sync_function"


class TestContextManagerInThreadpool:
    """Test sync context manager execution in async threadpool."""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test successful sync CM execution in threadpool."""
        cleanup_called = []

        @contextmanager
        def sync_resource():
            resource = Mock()
            resource.data = "test_data"
            try:
                yield resource
            finally:
                cleanup_called.append(True)

        # cm = sync_resource()

        async with contextmanager_in_threadpool(sync_resource) as resource:
            assert resource.data == "test_data"
            assert len(cleanup_called) == 0  # Not cleaned up yet

        assert len(cleanup_called) == 1  # Cleaned up after context

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test exception handling in threadpool CM."""
        cleanup_called = []
        exception_handled = []

        @contextmanager
        def sync_resource():
            resource = Mock()
            try:
                yield resource
            except Exception as e:
                exception_handled.append(e)
                return True  # Suppress exception
            finally:
                cleanup_called.append(True)

        async with contextmanager_in_threadpool(sync_resource) as resource:
            assert resource is not None
            raise ValueError("Test exception")

        # Exception should be suppressed by CM
        assert len(cleanup_called) == 1
        assert len(exception_handled) == 1
        assert isinstance(exception_handled[0], ValueError)


class TestAsyncContextManagerResolver:
    """Test AsyncContextManagerResolver functionality."""

    @pytest.fixture
    def sample_context(self):
        """Sample context for resolver testing."""
        return {"dep_param": "test_value", "other": 42}

    @pytest.fixture
    def async_cm_function(self):
        """Sample async context manager function."""

        @asynccontextmanager
        async def get_async_resource(dep_param: str):
            resource = AsyncMock()
            resource.value = f"async_{dep_param}"
            resource.cleanup = AsyncMock()
            try:
                yield resource
            finally:
                await resource.cleanup()

        return get_async_resource

    @pytest.fixture
    def sync_cm_function(self):
        """Sample sync context manager function."""

        @contextmanager
        def get_sync_resource(dep_param: str):
            resource = Mock()
            resource.value = f"sync_{dep_param}"
            resource.cleanup = Mock()
            try:
                yield resource
            finally:
                resource.cleanup()

        return get_sync_resource

    def test_init_async_cm(self, async_cm_function):
        """Test initialization of async context manager resolver."""
        ctx_map = {"dep_param": Mock()}
        resolver = AsyncContextManagerResolver(
            async_cm_function, ctx_map, is_sync_cm=False
        )

        assert resolver._func == async_cm_function
        assert resolver._ctx_map == ctx_map
        assert resolver._is_sync_cm == False

    def test_init_sync_cm_in_async_context(self, sync_cm_function):
        """Test initialization of sync CM resolver for async context."""
        ctx_map = {"dep_param": Mock()}
        resolver = AsyncContextManagerResolver(
            sync_cm_function, ctx_map, is_sync_cm=True
        )

        assert resolver._func == sync_cm_function
        assert resolver._is_sync_cm == True

    @pytest.mark.asyncio
    async def test_direct_call_raises_error(self, async_cm_function, sample_context):
        """Test that direct __call__ raises appropriate error."""
        resolver = AsyncContextManagerResolver(async_cm_function, {})

        with pytest.raises(
            RuntimeError, match="cannot be resolved without AsyncExitStack"
        ):
            await resolver(sample_context)

    @pytest.mark.asyncio
    async def test_resolve_async_cm_with_stack(self, async_cm_function, sample_context):
        """Test resolving async context manager with stack."""
        from ctxinject.inject import NameResolver

        ctx_map = {"dep_param": NameResolver("dep_param")}
        resolver = AsyncContextManagerResolver(
            async_cm_function, ctx_map, is_sync_cm=False
        )

        async with AsyncExitStack() as stack:
            resource = await resolver.resolve_with_stack(sample_context, stack)

            assert resource.value == "async_test_value"
            assert hasattr(resource, "cleanup")

    @pytest.mark.asyncio
    async def test_resolve_sync_cm_in_async_context(
        self, sync_cm_function, sample_context
    ):
        """Test resolving sync CM in async context via threadpool."""
        from ctxinject.inject import NameResolver

        ctx_map = {"dep_param": NameResolver("dep_param")}
        resolver = AsyncContextManagerResolver(
            sync_cm_function, ctx_map, is_sync_cm=True
        )

        async with AsyncExitStack() as stack:
            resource = await resolver.resolve_with_stack(sample_context, stack)

            assert resource.value == "sync_test_value"
            assert hasattr(resource, "cleanup")


class TestSyncContextManagerResolver:
    """Test SyncContextManagerResolver functionality."""

    @pytest.fixture
    def sync_cm_function(self):
        """Sample sync context manager function."""

        @contextmanager
        def get_resource(param: str):
            resource = Mock()
            resource.value = f"resource_{param}"
            try:
                yield resource
            finally:
                resource.cleanup = True

        return get_resource

    def test_init(self, sync_cm_function):
        """Test initialization of sync context manager resolver."""
        ctx_map = {"param": Mock()}
        resolver = SyncContextManagerResolver(sync_cm_function, ctx_map)

        assert resolver._func == sync_cm_function
        assert resolver._ctx_map == ctx_map

    def test_direct_call_raises_error(self, sync_cm_function):
        """Test that direct __call__ raises appropriate error."""
        resolver = SyncContextManagerResolver(sync_cm_function, {})

        with pytest.raises(RuntimeError, match="cannot be resolved without ExitStack"):
            resolver({"test": "context"})

    def test_resolve_with_stack_not_implemented(self, sync_cm_function):
        """Test that resolve_with_stack is not yet implemented."""
        resolver = SyncContextManagerResolver(sync_cm_function, {})

        with pytest.raises(NotImplementedError, match="sync resolve_mapped_ctx"):
            with ExitStack() as stack:
                resolver.resolve_with_stack({"test": "context"}, stack)


class TestContextManagerResolverFactory:
    """Test factory functions for creating resolvers."""

    def test_create_async_cm_resolver(self):
        """Test creating async context manager resolver."""

        @asynccontextmanager
        async def async_cm():
            yield "resource"

        ctx_map = {"param": Mock()}
        resolver = create_context_manager_resolver(async_cm, ctx_map)

        assert isinstance(resolver, AsyncContextManagerResolver)
        assert resolver._is_sync_cm == False

    def test_create_sync_cm_resolver(self):
        """Test creating sync context manager resolver."""

        @contextmanager
        def sync_cm():
            yield "resource"

        ctx_map = {"param": Mock()}
        resolver = create_context_manager_resolver(sync_cm, ctx_map)

        # Should create AsyncContextManagerResolver with is_sync_cm=True
        assert isinstance(resolver, AsyncContextManagerResolver)
        assert resolver._is_sync_cm == True

    def test_create_resolver_with_non_cm_function(self):
        """Test error when creating resolver for non-context manager."""

        def regular_function():
            return "not a context manager"

        with pytest.raises(ValueError, match="not a context manager"):
            create_context_manager_resolver(regular_function, {})

    def test_create_resolver_with_callable_object(self):
        """Test creating resolver with callable object that's a CM."""

        class ContextManagerCallable:
            def __call__(self):
                yield "resource"

        cm_callable = ContextManagerCallable()
        resolver = create_context_manager_resolver(cm_callable, {})

        assert isinstance(resolver, AsyncContextManagerResolver)
        assert resolver._is_sync_cm == True


class TestIntegrationScenarios:
    """Test integration scenarios with context managers."""

    @pytest.mark.asyncio
    async def test_nested_dependencies_with_cm(self):
        """Test context manager with its own dependencies."""
        from ctxinject.inject import NameResolver

        cleanup_order = []

        @contextmanager
        def database_connection(host: str):
            cleanup_order.append(f"db_open_{host}")
            conn = Mock()
            conn.host = host
            conn.query = Mock(return_value=[{"id": 1}])
            try:
                yield conn
            finally:
                cleanup_order.append(f"db_close_{host}")

        @asynccontextmanager
        async def redis_connection(host: str):
            cleanup_order.append(f"redis_open_{host}")
            redis = AsyncMock()
            redis.host = host
            redis.get = AsyncMock(return_value="cached_data")
            try:
                yield redis
            finally:
                cleanup_order.append(f"redis_close_{host}")

        # Create resolvers
        context = {"host": "localhost"}
        ctx_map = {"host": NameResolver("host")}

        db_resolver = AsyncContextManagerResolver(
            database_connection, ctx_map, is_sync_cm=True
        )
        redis_resolver = AsyncContextManagerResolver(
            redis_connection, ctx_map, is_sync_cm=False
        )

        # Use both context managers
        async with AsyncExitStack() as stack:
            db = await db_resolver.resolve_with_stack(context, stack)
            redis = await redis_resolver.resolve_with_stack(context, stack)

            assert db.host == "localhost"
            assert redis.host == "localhost"

            # Both should be active
            assert db.query() == [{"id": 1}]
            assert await redis.get("key") == "cached_data"

        # Check cleanup order (should include both opens and closes)
        assert "db_open_localhost" in cleanup_order
        assert "redis_open_localhost" in cleanup_order
        assert "db_close_localhost" in cleanup_order
        assert "redis_close_localhost" in cleanup_order

    @pytest.mark.asyncio
    async def test_cm_exception_propagation(self):
        """Test exception handling with context managers."""
        cleanup_called = []

        @contextmanager
        def failing_resource():
            cleanup_called.append("opened")
            resource = Mock()
            try:
                yield resource
            finally:
                cleanup_called.append("closed")

        @contextmanager
        def good_resource():
            cleanup_called.append("good_opened")
            try:
                yield Mock()
            finally:
                cleanup_called.append("good_closed")

        failing_resolver = AsyncContextManagerResolver(
            failing_resource, {}, is_sync_cm=True
        )
        good_resolver = AsyncContextManagerResolver(good_resource, {}, is_sync_cm=True)

        try:
            async with AsyncExitStack() as stack:
                good_res = await good_resolver.resolve_with_stack({}, stack)
                failing_res = await failing_resolver.resolve_with_stack({}, stack)

                # Simulate exception during usage
                raise ValueError("Something went wrong")

        except ValueError:
            pass  # Expected

        # Both resources should be cleaned up
        assert "good_closed" in cleanup_called
        assert "closed" in cleanup_called

    @pytest.mark.asyncio
    async def test_performance_with_multiple_cms(self):
        """Test performance characteristics with multiple context managers."""
        import time

        @contextmanager
        def slow_resource(name: str):
            time.sleep(0.01)  # Simulate slow setup
            yield f"resource_{name}"

        @asynccontextmanager
        async def fast_async_resource(name: str):
            await asyncio.sleep(0.005)  # Simulate async setup
            yield f"async_resource_{name}"

        from ctxinject.inject import NameResolver

        # Create multiple resolvers
        resolvers = []
        for i in range(3):
            ctx_map = {"name": NameResolver(f"name_{i}")}
            resolvers.append(
                AsyncContextManagerResolver(slow_resource, ctx_map, is_sync_cm=True)
            )
            resolvers.append(
                AsyncContextManagerResolver(
                    fast_async_resource, ctx_map, is_sync_cm=False
                )
            )

        context = {f"name_{i}": f"test_{i}" for i in range(3)}

        start = time.time()
        async with AsyncExitStack() as stack:
            resources = []
            for resolver in resolvers:
                resource = await resolver.resolve_with_stack(context, stack)
                resources.append(resource)

        elapsed = time.time() - start

        # Should complete reasonably fast despite multiple slow operations
        # (thanks to threadpool execution)
        assert elapsed < 0.5
        assert len(resources) == 6  # 3 slow + 3 fast resources
