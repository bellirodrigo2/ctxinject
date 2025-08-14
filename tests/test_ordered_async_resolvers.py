import asyncio
import pytest
import warnings

from ctxinject.inject import inject_args
from ctxinject.model import DependsInject


class TestOrderedAsyncResolvers:
    """Test ordered execution of async resolvers with proper sequencing."""

    @pytest.mark.asyncio
    async def test_async_resolvers_execute_in_order(self):
        """Test that async resolvers execute in the correct order (1, 2, 3, ...)."""
        execution_order = []
        
        async def dep_order_1():
            await asyncio.sleep(0.1)  # Simulate some work
            execution_order.append(1)
            return "order_1_result"
        
        async def dep_order_2():
            await asyncio.sleep(0.05)  # Faster than order 1, but should wait
            execution_order.append(2)
            return "order_2_result"
        
        async def dep_order_3():
            await asyncio.sleep(0.01)  # Fastest, but should wait for others
            execution_order.append(3)
            return "order_3_result"
        
        def test_func(
            val1: str = DependsInject(dep_order_1, order=1),
            val2: str = DependsInject(dep_order_2, order=2), 
            val3: str = DependsInject(dep_order_3, order=3)
        ):
            return f"{val1}, {val2}, {val3}"
        
        injected = await inject_args(test_func, {})
        result = injected()
        
        # Verify execution order is correct despite different sleep times
        assert execution_order == [1, 2, 3]
        assert result == "order_1_result, order_2_result, order_3_result"

    @pytest.mark.asyncio 
    async def test_order_n_plus_1_waits_for_order_n_completion(self):
        """Test that order n+1 doesn't start until order n completes entirely."""
        events = []
        
        async def dep_order_1_slow():
            events.append("order_1_start")
            await asyncio.sleep(0.2)  # Long running task
            events.append("order_1_end") 
            return "slow_result"
        
        async def dep_order_2_fast():
            events.append("order_2_start")
            await asyncio.sleep(0.01)  # Fast task but should wait
            events.append("order_2_end")
            return "fast_result"
        
        def test_func(
            slow: str = DependsInject(dep_order_1_slow, order=1),
            fast: str = DependsInject(dep_order_2_fast, order=2)
        ):
            return f"{slow}, {fast}"
        
        injected = await inject_args(test_func, {})
        result = injected()
        
        # Verify order 2 doesn't start until order 1 is completely done
        assert events == ["order_1_start", "order_1_end", "order_2_start", "order_2_end"]
        assert result == "slow_result, fast_result"

    @pytest.mark.asyncio
    async def test_exception_in_order_n_prevents_order_n_plus_1(self):
        """Test that an exception in order n prevents order n+1 from starting."""
        events = []
        
        async def dep_order_1_fails():
            events.append("order_1_start")
            await asyncio.sleep(0.1)
            events.append("order_1_about_to_fail")
            raise ValueError("Order 1 failed")
        
        async def dep_order_2_should_not_run():
            events.append("order_2_start")  # This should never be added
            return "order_2_result"
        
        def test_func(
            val1: str = DependsInject(dep_order_1_fails, order=1),
            val2: str = DependsInject(dep_order_2_should_not_run, order=2)
        ):
            return f"{val1}, {val2}"
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with pytest.raises(ValueError, match="Order 1 failed"):
                injected = await inject_args(test_func, {})
                injected()
        
        # Verify order 2 never started
        assert "order_2_start" not in events
        assert events == ["order_1_start", "order_1_about_to_fail"]

    @pytest.mark.asyncio
    async def test_concurrent_execution_within_same_order(self):
        """Test that resolvers with the same order execute concurrently."""
        start_times = {}
        end_times = {}
        
        async def dep_order_1_task_a():
            start_times['task_a'] = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)
            end_times['task_a'] = asyncio.get_event_loop().time()
            return "task_a_result"
        
        async def dep_order_1_task_b(): 
            start_times['task_b'] = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)
            end_times['task_b'] = asyncio.get_event_loop().time()
            return "task_b_result"
        
        def test_func(
            val_a: str = DependsInject(dep_order_1_task_a, order=1),
            val_b: str = DependsInject(dep_order_1_task_b, order=1)
        ):
            return f"{val_a}, {val_b}"
        
        injected = await inject_args(test_func, {})
        result = injected()
        
        # Verify tasks started concurrently (within a reasonable time window)
        time_diff = abs(start_times['task_a'] - start_times['task_b'])
        assert time_diff < 0.01  # Should start within 10ms of each other
        
        # Verify both completed
        assert result == "task_a_result, task_b_result"

    @pytest.mark.asyncio
    async def test_mixed_orders_with_exception_isolation(self):
        """Test that exception in one resolver of an order doesn't affect others in same order."""
        events = []
        
        async def dep_order_1_success():
            events.append("order_1_success_start")
            await asyncio.sleep(0.1)
            events.append("order_1_success_end")
            return "success"
        
        async def dep_order_1_fails():
            events.append("order_1_fail_start") 
            await asyncio.sleep(0.05)
            events.append("order_1_fail_about_to_fail")
            raise RuntimeError("Task failed")
        
        async def dep_order_2_should_not_run():
            events.append("order_2_start")
            return "order_2_result"
        
        def test_func(
            success: str = DependsInject(dep_order_1_success, order=1),
            fail: str = DependsInject(dep_order_1_fails, order=1),
            later: str = DependsInject(dep_order_2_should_not_run, order=2)
        ):
            return f"{success}, {fail}, {later}"
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with pytest.raises(RuntimeError, match="Task failed"):
                injected = await inject_args(test_func, {})
                injected()
        
        # Both order 1 tasks should have started, but order 2 should not
        assert "order_1_success_start" in events
        assert "order_1_fail_start" in events  
        assert "order_2_start" not in events

    @pytest.mark.asyncio
    async def test_complex_ordering_scenario(self):
        """Test complex scenario with multiple orders and dependencies."""
        execution_log = []
        
        async def foundation():
            execution_log.append("foundation_start")
            await asyncio.sleep(0.1)
            execution_log.append("foundation_end")
            return "foundation_ready"
        
        async def service_a():
            execution_log.append("service_a_start") 
            await asyncio.sleep(0.08)
            execution_log.append("service_a_end")
            return "service_a_ready"
        
        async def service_b():
            execution_log.append("service_b_start")
            await asyncio.sleep(0.06)
            execution_log.append("service_b_end") 
            return "service_b_ready"
        
        async def application():
            execution_log.append("application_start")
            await asyncio.sleep(0.05)
            execution_log.append("application_end")
            return "application_ready"
        
        def test_func(
            base: str = DependsInject(foundation, order=1),
            svc_a: str = DependsInject(service_a, order=2),
            svc_b: str = DependsInject(service_b, order=2), 
            app: str = DependsInject(application, order=3)
        ):
            return f"{base} -> {svc_a}, {svc_b} -> {app}"
        
        injected = await inject_args(test_func, {})
        result = injected()
        
        # Verify proper ordering: foundation first, then services, then application
        foundation_end_idx = execution_log.index("foundation_end")
        service_a_start_idx = execution_log.index("service_a_start") 
        service_b_start_idx = execution_log.index("service_b_start")
        service_a_end_idx = execution_log.index("service_a_end")
        service_b_end_idx = execution_log.index("service_b_end")
        app_start_idx = execution_log.index("application_start")
        
        # Foundation must complete before services start
        assert foundation_end_idx < service_a_start_idx
        assert foundation_end_idx < service_b_start_idx
        
        # Services can start concurrently
        start_diff = abs(service_a_start_idx - service_b_start_idx)
        assert start_diff <= 1  # Should be adjacent or same in log
        
        # Application must wait for both services to complete
        assert max(service_a_end_idx, service_b_end_idx) < app_start_idx
        
        assert result == "foundation_ready -> service_a_ready, service_b_ready -> application_ready"