"""
Test for override state mutation bug.

This test ensures that dependency overrides don't mutate the original
dependency objects, which is critical for test isolation.
"""

import pytest

from ctxinject.inject import inject_args
from ctxinject.model import DependsInject


class TestOverrideStateMutation:
    """Tests for dependency override state mutation issues."""

    @pytest.mark.asyncio
    async def test_override_state_mutation_bug(self) -> None:
        """Test that overrides don't mutate original dependency state."""

        call_log = []

        def original_dep():
            call_log.append("original_called")
            return "original_result"

        def override_dep():
            call_log.append("override_called")
            return "override_result"

        async def handler(value: str = DependsInject(original_dep)) -> str:
            return value

        # First injection WITH override
        call_log.clear()
        overrides = {original_dep: override_dep}
        injected1 = await inject_args(handler, {}, overrides=overrides)
        result1 = await injected1()

        assert result1 == "override_result"
        assert "override_called" in call_log
        assert "original_called" not in call_log

        # Second injection WITHOUT override - should use original!
        call_log.clear()
        injected2 = await inject_args(handler, {})  # No overrides
        result2 = await injected2()

        # ✅ Should use the original dependency, not the override
        assert result2 == "original_result"
        assert "original_called" in call_log
        assert "override_called" not in call_log

    @pytest.mark.asyncio
    async def test_multiple_override_scenarios(self) -> None:
        """Test multiple override scenarios don't interfere with each other."""

        def dep_a():
            return "dep_a_original"

        def dep_b():
            return "dep_b_original"

        def override_a():
            return "dep_a_override"

        def override_b():
            return "dep_b_override"

        async def handler(
            a: str = DependsInject(dep_a), b: str = DependsInject(dep_b)
        ) -> tuple[str, str]:
            return a, b

        # Test 1: Override only A
        overrides1 = {dep_a: override_a}
        injected1 = await inject_args(handler, {}, overrides=overrides1)
        result1 = await injected1()
        assert result1 == ("dep_a_override", "dep_b_original")

        # Test 2: Override only B
        overrides2 = {dep_b: override_b}
        injected2 = await inject_args(handler, {}, overrides=overrides2)
        result2 = await injected2()
        assert result2 == ("dep_a_original", "dep_b_override")

        # Test 3: Override both
        overrides3 = {dep_a: override_a, dep_b: override_b}
        injected3 = await inject_args(handler, {}, overrides=overrides3)
        result3 = await injected3()
        assert result3 == ("dep_a_override", "dep_b_override")

        # Test 4: No overrides (should be back to original)
        injected4 = await inject_args(handler, {})
        result4 = await injected4()
        assert result4 == ("dep_a_original", "dep_b_original")

    @pytest.mark.asyncio
    async def test_nested_dependency_overrides(self) -> None:
        """Test that overrides work correctly with nested dependencies."""

        def base_config():
            return {"env": "production"}

        def test_config():
            return {"env": "test"}

        async def service(config: dict = DependsInject(base_config)) -> str:
            return f"Service in {config['env']}"

        async def handler(svc: str = DependsInject(service)) -> str:
            return svc

        # Test with override
        overrides = {base_config: test_config}
        injected_override = await inject_args(handler, {}, overrides=overrides)
        result_override = await injected_override()
        assert result_override == "Service in test"

        # Test without override - should use original
        injected_normal = await inject_args(handler, {})
        result_normal = await injected_normal()
        assert result_normal == "Service in production"

    @pytest.mark.asyncio
    async def test_async_dependency_overrides(self) -> None:
        """Test overrides with async dependencies."""

        async def original_async_dep():
            return "async_original"

        async def override_async_dep():
            return "async_override"

        def sync_override():
            return "sync_override"

        async def handler(value: str = DependsInject(original_async_dep)) -> str:
            return value

        # Test async -> async override
        overrides1 = {original_async_dep: override_async_dep}
        injected1 = await inject_args(handler, {}, overrides=overrides1)
        result1 = await injected1()
        assert result1 == "async_override"

        # Test async -> sync override
        overrides2 = {original_async_dep: sync_override}
        injected2 = await inject_args(handler, {}, overrides=overrides2)
        result2 = await injected2()
        assert result2 == "sync_override"

        # Test without override - should use original async
        injected3 = await inject_args(handler, {})
        result3 = await injected3()
        assert result3 == "async_original"

    @pytest.mark.asyncio
    async def test_override_with_validation(self) -> None:
        """Test that overrides work correctly when validation is involved."""

        def original_provider():
            return "original_value"

        def override_provider():
            return "override_value"

        def validator(instance, **kwargs):
            return instance.upper()

        async def handler(
            value: str = DependsInject(original_provider, validator=validator)
        ) -> str:
            return value

        # Test with override + validation
        overrides = {original_provider: override_provider}
        injected_override = await inject_args(handler, {}, overrides=overrides)
        result_override = await injected_override()
        assert result_override == "OVERRIDE_VALUE"  # Validated (uppercase)

        # Test without override + validation
        injected_normal = await inject_args(handler, {})
        result_normal = await injected_normal()
        assert result_normal == "ORIGINAL_VALUE"  # Validated (uppercase)

    @pytest.mark.asyncio
    async def test_concurrent_injections_isolation(self) -> None:
        """Test that concurrent injections with different overrides are isolated."""

        import asyncio

        def shared_dep():
            return "shared_original"

        def override_1():
            return "override_1"

        def override_2():
            return "override_2"

        async def handler(value: str = DependsInject(shared_dep)) -> str:
            await asyncio.sleep(0.01)  # Simulate some async work
            return value

        # Run concurrent injections with different overrides
        overrides1 = {shared_dep: override_1}
        overrides2 = {shared_dep: override_2}

        task1 = inject_args(handler, {}, overrides=overrides1)
        task2 = inject_args(handler, {}, overrides=overrides2)
        task3 = inject_args(handler, {})  # No overrides

        injected1, injected2, injected3 = await asyncio.gather(task1, task2, task3)

        # Execute the injected functions concurrently
        result_task1 = injected1()
        result_task2 = injected2()
        result_task3 = injected3()

        result1, result2, result3 = await asyncio.gather(
            result_task1, result_task2, result_task3
        )

        # Each should have used the correct dependency
        assert result1 == "override_1"
        assert result2 == "override_2"
        assert result3 == "shared_original"
