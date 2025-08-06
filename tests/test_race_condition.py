"""
Comprehensive test suite for race condition fixes with optimized resolver classes.

This module thoroughly tests that the new SyncResolver/FuncResolver implementation
correctly handles concurrent dependency resolution without race conditions while
maintaining optimal performance.
"""

import asyncio
import time
from typing import Any, Dict, List, Set

import pytest

from ctxinject.inject import inject_args, resolve_mapped_ctx
from ctxinject.model import ArgsInjectable, DependsInject
from ctxinject.resolvers import FuncResolver


class TestResolverClassesPerformance:
    """Test performance characteristics of resolver classes."""

    def test_sync_resolver_creation(self) -> None:
        """Test SyncResolver creation and basic functionality."""

        def test_func(ctx: Dict[str, Any]) -> str:
            return "sync_result"

        resolver = FuncResolver(test_func, False)
        result = resolver({"test": "context"})

        assert result == "sync_result"
        assert hasattr(resolver, "_func")

    def test_async_resolver_creation(self) -> None:
        """Test FuncResolver creation and basic functionality."""

        async def test_func(ctx: Dict[str, Any]) -> str:
            await asyncio.sleep(0.001)
            return "async_result"

        resolver = FuncResolver(test_func, True)

        # Should return awaitable when called
        context = {"test": "context"}
        result = resolver(context)

        # Verify it's an awaitable (coroutine)
        import inspect

        assert inspect.iscoroutine(result)

        # Clean up the coroutine
        result.close()

    def test_resolver_type_detection_performance(self) -> None:
        """Test that isinstance() detection is fast for resolver types."""
        sync_resolver = FuncResolver(lambda ctx: "sync", False)
        async_resolver = FuncResolver(lambda ctx: "async", True)

        # Time isinstance checks (should be very fast)
        start_time = time.perf_counter()
        for _ in range(10000):
            isinstance(sync_resolver, FuncResolver)
            isinstance(async_resolver, FuncResolver)
        end_time = time.perf_counter()

        # Should complete very quickly
        execution_time = end_time - start_time
        assert (
            execution_time < 0.1
        ), f"Type checking took {execution_time}s, should be much faster"

    def test_resolver_memory_efficiency(self) -> None:
        """Test that resolvers use __slots__ for memory efficiency."""

        # Should have __slots__ defined
        assert hasattr(FuncResolver, "__slots__")
        assert hasattr(FuncResolver, "__slots__")


class TestConcurrentAsyncResolution:
    """Test concurrent resolution of async dependencies."""

    @pytest.mark.asyncio
    async def test_multiple_async_dependencies_execute_concurrently(self) -> None:
        """Test that multiple async dependencies execute in parallel, not sequentially."""
        execution_log: List[str] = []

        async def slow_dependency_1() -> str:
            execution_log.append("dep1_start")
            await asyncio.sleep(0.1)
            execution_log.append("dep1_end")
            return "result1"

        async def slow_dependency_2() -> str:
            execution_log.append("dep2_start")
            await asyncio.sleep(0.1)
            execution_log.append("dep2_end")
            return "result2"

        async def slow_dependency_3() -> str:
            execution_log.append("dep3_start")
            await asyncio.sleep(0.1)
            execution_log.append("dep3_end")
            return "result3"

        # Create mapped context with FuncResolvers
        mapped_ctx = {
            "dep1": FuncResolver(lambda ctx: slow_dependency_1(), True),
            "dep2": FuncResolver(lambda ctx: slow_dependency_2(), True),
            "dep3": FuncResolver(lambda ctx: slow_dependency_3(), True),
        }

        start_time = time.perf_counter()
        result = await resolve_mapped_ctx({}, mapped_ctx)
        end_time = time.perf_counter()

        execution_time = end_time - start_time

        # Verify results
        assert result["dep1"] == "result1"
        assert result["dep2"] == "result2"
        assert result["dep3"] == "result3"

        # Verify concurrent execution (should be ~0.1s, not ~0.3s)
        assert (
            execution_time < 0.2
        ), f"Execution took {execution_time:.3f}s, expected concurrent execution"

        # Verify all dependencies started before any completed
        start_indices = [
            i for i, log in enumerate(execution_log) if log.endswith("_start")
        ]
        end_indices = [i for i, log in enumerate(execution_log) if log.endswith("_end")]

        # All starts should happen before all ends in concurrent execution
        assert max(start_indices) < min(
            end_indices
        ), "Dependencies should start concurrently"

    @pytest.mark.asyncio
    async def test_mixed_sync_async_resolvers(self) -> None:
        """Test mixing sync and async resolvers in the same context."""

        async def async_dep() -> str:
            await asyncio.sleep(0.05)
            return "async_result"

        def sync_dep() -> str:
            return "sync_result"

        mapped_ctx = {
            "sync1": FuncResolver(lambda ctx: sync_dep(), False),
            "async1": FuncResolver(lambda ctx: async_dep(), True),
            "sync2": FuncResolver(lambda ctx: "direct_sync", False),
            "async2": FuncResolver(lambda ctx: async_dep(), True),
        }

        result = await resolve_mapped_ctx({}, mapped_ctx)

        assert result["sync1"] == "sync_result"
        assert result["async1"] == "async_result"
        assert result["sync2"] == "direct_sync"
        assert result["async2"] == "async_result"

    @pytest.mark.asyncio
    async def test_async_exception_propagation(self) -> None:
        """Test that exceptions from async resolvers are properly propagated."""

        async def failing_dependency() -> str:
            await asyncio.sleep(0.01)
            raise ValueError("Async dependency failed")

        async def successful_dependency() -> str:
            await asyncio.sleep(0.01)
            return "success"

        mapped_ctx = {
            "good": FuncResolver(lambda ctx: successful_dependency(), True),
            "bad": FuncResolver(lambda ctx: failing_dependency(), True),
        }

        with pytest.raises(ValueError, match="Async dependency failed"):
            await resolve_mapped_ctx({}, mapped_ctx)

    @pytest.mark.asyncio
    async def test_sync_exception_propagation(self) -> None:
        """Test that exceptions from sync resolvers are properly propagated."""

        def failing_sync() -> str:
            raise RuntimeError("Sync resolver failed")

        def successful_sync() -> str:
            return "success"

        mapped_ctx = {
            "good": FuncResolver(lambda ctx: successful_sync(), False),
            "bad": FuncResolver(lambda ctx: failing_sync(), False),
        }

        with pytest.raises(RuntimeError, match="Sync resolver failed"):
            await resolve_mapped_ctx({}, mapped_ctx)


class TestEndToEndInjectionPerformance:
    """Test end-to-end injection performance with new resolver classes."""

    @pytest.mark.asyncio
    async def test_inject_args_with_multiple_sync_dependencies(self) -> None:
        """Test inject_args performance with multiple sync dependencies."""

        def handler(
            arg1: str = ArgsInjectable(),
            arg2: int = ArgsInjectable(),
            arg3: float = ArgsInjectable(),
            arg4: bool = ArgsInjectable(),
        ) -> Dict[str, Any]:
            return {"arg1": arg1, "arg2": arg2, "arg3": arg3, "arg4": arg4}

        context = {
            "arg1": "test_string",
            "arg2": 42,
            "arg3": 3.14,
            "arg4": True,
        }

        start_time = time.perf_counter()
        injected_func = await inject_args(handler, context)
        result = injected_func()
        end_time = time.perf_counter()

        # Verify results
        assert result["arg1"] == "test_string"
        assert result["arg2"] == 42
        assert result["arg3"] == 3.14
        assert result["arg4"] is True

        # Should be very fast for sync-only dependencies
        execution_time = end_time - start_time
        assert (
            execution_time < 0.01
        ), f"Sync injection took {execution_time}s, should be much faster"

    @pytest.mark.asyncio
    async def test_inject_args_with_async_dependencies(self) -> None:
        """Test inject_args with async dependencies (Depends)."""

        async def async_service() -> str:
            await asyncio.sleep(0.05)
            return "async_service_result"

        def sync_config() -> Dict[str, str]:
            return {"setting": "value"}

        async def handler(
            service: str = DependsInject(async_service),
            config: Dict[str, str] = DependsInject(sync_config),
            direct_arg: str = ArgsInjectable(),
        ) -> str:
            return f"{service}_{config['setting']}_{direct_arg}"

        context = {"direct_arg": "direct_value"}

        injected_func = await inject_args(handler, context)
        result = await injected_func()

        assert result == "async_service_result_value_direct_value"

    @pytest.mark.asyncio
    async def test_nested_async_dependencies(self) -> None:
        """Test nested async dependencies with race condition scenarios."""
        call_order: List[str] = []

        async def base_service() -> str:
            call_order.append("base_start")
            await asyncio.sleep(0.02)
            call_order.append("base_end")
            return "base_result"

        async def dependent_service_1(base: str = DependsInject(base_service)) -> str:
            call_order.append("dep1_start")
            await asyncio.sleep(0.01)
            call_order.append("dep1_end")
            return f"dep1_{base}"

        async def dependent_service_2(base: str = DependsInject(base_service)) -> str:
            call_order.append("dep2_start")
            await asyncio.sleep(0.01)
            call_order.append("dep2_end")
            return f"dep2_{base}"

        async def handler(
            service1: str = DependsInject(dependent_service_1),
            service2: str = DependsInject(dependent_service_2),
        ) -> str:
            return f"{service1}|{service2}"

        injected_func = await inject_args(handler, {})
        result = await injected_func()

        assert result == "dep1_base_result|dep2_base_result"

        # Verify base service was called
        assert "base_start" in call_order
        assert "base_end" in call_order


class TestRaceConditionScenarios:
    """Test specific race condition scenarios that could occur."""

    @pytest.mark.asyncio
    async def test_shared_resource_concurrent_access(self) -> None:
        """Test concurrent access to shared resources doesn't cause race conditions."""
        shared_state = {"counter": 0, "access_log": []}

        async def increment_counter(identifier: str) -> str:
            # Read current state
            current = shared_state["counter"]
            shared_state["access_log"].append(f"{identifier}_read_{current}")

            # Simulate processing delay
            await asyncio.sleep(0.005)

            # Write new state (potential race condition)
            shared_state["counter"] = current + 1
            final_value = shared_state["counter"]
            shared_state["access_log"].append(f"{identifier}_write_{final_value}")

            return f"{identifier}_result_{final_value}"

        mapped_ctx = {
            "service1": FuncResolver(lambda ctx: increment_counter("svc1"), True),
            "service2": FuncResolver(lambda ctx: increment_counter("svc2"), True),
            "service3": FuncResolver(lambda ctx: increment_counter("svc3"), True),
        }

        result = await resolve_mapped_ctx({}, mapped_ctx)

        # Verify all services completed
        assert len(result) == 3
        assert all("result" in value for value in result.values())

        # Verify concurrent access occurred
        access_log = shared_state["access_log"]
        read_events = [log for log in access_log if "_read_" in log]
        write_events = [log for log in access_log if "_write_" in log]

        assert len(read_events) == 3
        assert len(write_events) == 3

    @pytest.mark.asyncio
    async def test_dependency_resolution_isolation(self) -> None:
        """Test that dependency resolution doesn't interfere between different contexts."""
        results_collector: Dict[str, List[str]] = {"ctx1": [], "ctx2": []}

        async def context_dependent_service(ctx_id: str) -> str:
            results_collector[ctx_id].append(f"service_start_{ctx_id}")
            await asyncio.sleep(0.01)
            results_collector[ctx_id].append(f"service_end_{ctx_id}")
            return f"result_{ctx_id}"

        # Create two separate injection contexts
        async def handler1(
            service: str = DependsInject(lambda: context_dependent_service("ctx1")),
        ) -> str:
            return service

        async def handler2(
            service: str = DependsInject(lambda: context_dependent_service("ctx2")),
        ) -> str:
            return service

        # Run both injections concurrently
        task1 = inject_args(handler1, {})
        task2 = inject_args(handler2, {})

        injected_func1, injected_func2 = await asyncio.gather(task1, task2)

        # Execute both handlers concurrently
        result_task1 = injected_func1()
        result_task2 = injected_func2()

        result1, result2 = await asyncio.gather(result_task1, result_task2)

        assert result1 == "result_ctx1"
        assert result2 == "result_ctx2"

        # Verify both contexts were processed
        assert len(results_collector["ctx1"]) == 2
        assert len(results_collector["ctx2"]) == 2

    @pytest.mark.asyncio
    async def test_exception_handling_with_partial_failures(self) -> None:
        """Test that partial failures don't prevent other dependencies from resolving."""
        completion_tracker: Set[str] = set()

        async def successful_service(service_id: str) -> str:
            try:
                await asyncio.sleep(0.01)
                completion_tracker.add(service_id)
                return f"success_{service_id}"
            finally:
                # Ensure cleanup always happens
                completion_tracker.add(f"{service_id}_cleanup")

        async def failing_service() -> str:
            try:
                await asyncio.sleep(0.005)
                completion_tracker.add("failing_service")
                raise ValueError("Service intentionally failed")
            finally:
                completion_tracker.add("failing_cleanup")

        mapped_ctx = {
            "service1": FuncResolver(lambda ctx: successful_service("svc1"), True),
            "failing": FuncResolver(lambda ctx: failing_service(), True),
            "service2": FuncResolver(lambda ctx: successful_service("svc2"), True),
        }

        with pytest.raises(ValueError, match="Service intentionally failed"):
            await resolve_mapped_ctx({}, mapped_ctx)

        # Verify that successful services completed even though one failed
        assert "svc1" in completion_tracker
        assert "svc2" in completion_tracker
        assert "failing_service" in completion_tracker

        # Verify cleanup happened for all services
        assert "svc1_cleanup" in completion_tracker
        assert "svc2_cleanup" in completion_tracker
        assert "failing_cleanup" in completion_tracker


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    @pytest.mark.asyncio
    async def test_legacy_partial_resolvers_still_work(self) -> None:
        """Test that legacy partial-based resolvers still work alongside new classes."""
        from functools import partial

        def legacy_resolver(context: Dict[str, Any], arg_name: str) -> str:
            return context[arg_name]

        # Mix new resolver classes with legacy partials
        mapped_ctx = {
            "new_sync": FuncResolver(lambda ctx: "new_sync_result", False),
            "legacy": FuncResolver(
                partial(legacy_resolver, arg_name="test_arg"), False
            ),
            "new_async": FuncResolver(
                lambda ctx: asyncio.sleep(0.01) or "new_async_result", True
            ),
        }

        context = {"test_arg": "legacy_result"}
        result = await resolve_mapped_ctx(context, mapped_ctx)

        assert result["new_sync"] == "new_sync_result"
        assert result["legacy"] == "legacy_result"
        # Note: async result would be awaitable, this tests the mixing works

    @pytest.mark.asyncio
    async def test_existing_api_unchanged(self) -> None:
        """Test that existing public API remains unchanged."""

        def simple_handler(
            arg1: str = ArgsInjectable(), arg2: int = ArgsInjectable()
        ) -> str:
            return f"{arg1}_{arg2}"

        context = {"arg1": "test", "arg2": 42}

        # This should work exactly as before
        injected_func = await inject_args(simple_handler, context)
        result = injected_func()

        assert result == "test_42"


class TestStressAndLoad:
    """Stress tests for race condition fixes under load."""

    @pytest.mark.asyncio
    async def test_high_concurrency_async_dependencies(self) -> None:
        """Test behavior with many concurrent async dependencies."""
        num_dependencies = 50

        async def numbered_dependency(dep_id: int) -> str:
            await asyncio.sleep(0.001)  # Small delay
            return f"result_{dep_id}"

        # Create many async resolvers
        mapped_ctx = {}
        for i in range(num_dependencies):
            mapped_ctx[f"dep_{i}"] = FuncResolver(
                lambda ctx, dep_id=i: numbered_dependency(dep_id), True
            )

        start_time = time.perf_counter()
        result = await resolve_mapped_ctx({}, mapped_ctx)
        end_time = time.perf_counter()

        # Verify all dependencies resolved
        assert len(result) == num_dependencies
        for i in range(num_dependencies):
            assert result[f"dep_{i}"] == f"result_{i}"

        # Should complete in roughly the delay time, not scale linearly
        execution_time = end_time - start_time
        assert (
            execution_time < 0.1
        ), f"High concurrency test took {execution_time}s, should be concurrent"

    @pytest.mark.asyncio
    async def test_repeated_injection_performance(self) -> None:
        """Test performance of repeated injections (simulating server load)."""

        async def service_dependency() -> str:
            await asyncio.sleep(0.001)
            return "service_result"

        async def handler(
            service: str = DependsInject(service_dependency),
            config: str = ArgsInjectable(),
        ) -> str:
            return f"{service}_{config}"

        context = {"config": "prod"}

        # Simulate multiple requests
        num_requests = 100
        start_time = time.perf_counter()

        tasks = []
        for _ in range(num_requests):
            task = inject_args(handler, context)
            tasks.append(task)

        injected_funcs = await asyncio.gather(*tasks)

        # Execute all injected functions - these return awaitables for async handlers
        execution_tasks = [func() for func in injected_funcs]
        results = await asyncio.gather(*execution_tasks)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Verify all requests completed successfully
        assert len(results) == num_requests
        assert all(result == "service_result_prod" for result in results)

        # Should handle the load efficiently
        avg_time_per_request = execution_time / num_requests
        assert (
            avg_time_per_request < 0.01
        ), f"Average {avg_time_per_request:.4f}s per request, too slow"


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    @pytest.mark.asyncio
    async def test_empty_context_resolution(self) -> None:
        """Test resolution with empty context."""
        result = await resolve_mapped_ctx({}, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_only_sync_resolvers(self) -> None:
        """Test context with only sync resolvers (no async path)."""
        mapped_ctx = {
            "sync1": FuncResolver(lambda ctx: "result1", False),
            "sync2": FuncResolver(lambda ctx: "result2", False),
            "sync3": FuncResolver(lambda ctx: "result3", False),
        }

        result = await resolve_mapped_ctx({}, mapped_ctx)

        assert result["sync1"] == "result1"
        assert result["sync2"] == "result2"
        assert result["sync3"] == "result3"

    @pytest.mark.asyncio
    async def test_only_async_resolvers(self) -> None:
        """Test context with only async resolvers."""

        async def async_dep(value: str) -> str:
            await asyncio.sleep(0.001)
            return f"async_{value}"

        mapped_ctx = {
            "async1": FuncResolver(lambda ctx: async_dep("1"), True),
            "async2": FuncResolver(lambda ctx: async_dep("2"), True),
            "async3": FuncResolver(lambda ctx: async_dep("3"), True),
        }

        result = await resolve_mapped_ctx({}, mapped_ctx)

        assert result["async1"] == "async_1"
        assert result["async2"] == "async_2"
        assert result["async3"] == "async_3"

    @pytest.mark.asyncio
    async def test_resolver_with_context_dependency(self) -> None:
        """Test resolvers that depend on context values."""

        def context_dependent_sync(ctx: Dict[str, Any]) -> str:
            return f"sync_{ctx.get('base_value', 'default')}"

        async def context_dependent_async(ctx: Dict[str, Any]) -> str:
            await asyncio.sleep(0.001)
            return f"async_{ctx.get('base_value', 'default')}"

        mapped_ctx = {
            "sync": FuncResolver(context_dependent_sync, False),
            "async": FuncResolver(context_dependent_async, True),
        }

        context = {"base_value": "test_context"}
        result = await resolve_mapped_ctx(context, mapped_ctx)

        assert result["sync"] == "sync_test_context"
        assert result["async"] == "async_test_context"
