"""
Specific test to expose async validation bug.

"""

import asyncio
from typing import Any, Tuple

import pytest

from ctxinject.inject import inject_args
from ctxinject.model import DependsInject


class TestAsyncValidationBug:
    """Tests that expose validation bugs with async resolvers."""

    @pytest.mark.asyncio
    async def test_async_dependency_with_sync_validator_fixed(self) -> None:
        """
        Fixed test - async dependency + sync validator.

        The validator is ALWAYS sync, even with async dependency.
        """

        async def async_string_provider() -> str:
            await asyncio.sleep(0.001)
            return "hello_world"

        def sync_validator(instance: Any, **kwargs: Any) -> str:
            """SYNC validator that should receive the resolved value."""

            # If it receives a coroutine, it's buggy!
            if hasattr(instance, "__await__"):
                raise TypeError(
                    f"BUG DETECTED: Validator received coroutine {type(instance)} "
                    f"instead of resolved value!"
                )

            if not isinstance(instance, str):
                raise TypeError(f"Expected str, got {type(instance)}")

            return instance.upper()  # Sync transformation

        async def handler(
            value: str = DependsInject(async_string_provider, validator=sync_validator)
        ) -> str:
            return value

        # After correction, should return the validated value
        injected = await inject_args(handler, {})
        result = await injected()

        assert result == "HELLO_WORLD"

    @pytest.mark.asyncio
    async def test_sync_dependency_with_sync_validator_works(self) -> None:
        """Control test - sync dependency + sync validator should work."""

        def sync_string_provider() -> str:
            return "sync_value"

        def sync_validator(instance: Any, **kwargs: Any) -> str:
            if not isinstance(instance, str):
                raise TypeError(f"Expected str, got {type(instance)}")
            return instance.upper()

        async def handler(
            value: str = DependsInject(sync_string_provider, validator=sync_validator)
        ) -> str:
            return value

        injected = await inject_args(handler, {})
        result = await injected()

        assert result == "SYNC_VALUE"

    @pytest.mark.asyncio
    async def test_async_dependency_with_sync_validator_bug(self) -> None:
        """Async dependency + sync validator - exposes the bug if not fixed."""

        async def async_number_provider() -> int:
            await asyncio.sleep(0.001)
            return 42

        def sync_validator(instance: Any, **kwargs: Any) -> int:
            # If it receives coroutine, it's buggy
            if hasattr(instance, "__await__"):
                raise TypeError(
                    f"BUG DETECTED: Sync validator received coroutine {type(instance)}"
                )

            if not isinstance(instance, int):
                raise TypeError(f"Expected int, got {type(instance)}")

            return instance * 2

        async def handler(
            value: int = DependsInject(async_number_provider, validator=sync_validator)
        ) -> int:
            return value

        injected = await inject_args(handler, {})
        result = await injected()

        assert result == 84  # 42 * 2

    @pytest.mark.asyncio
    async def test_nested_async_dependencies_with_validation(self) -> None:
        """Test with nested async dependencies + validation."""

        async def base_config() -> dict:
            await asyncio.sleep(0.001)
            return {"multiplier": 3}

        async def computed_value(config: dict = DependsInject(base_config)) -> int:
            await asyncio.sleep(0.001)
            return 10 * config["multiplier"]

        def int_validator(instance: Any, **kwargs: Any) -> int:
            if hasattr(instance, "__await__"):
                raise TypeError("Validator received coroutine!")

            if not isinstance(instance, int):
                raise TypeError(f"Expected int, got {type(instance)}")

            if instance <= 0:
                raise ValueError("Must be positive")

            return instance

        async def handler(
            result: int = DependsInject(computed_value, validator=int_validator)
        ) -> int:
            return result

        injected = await inject_args(handler, {})
        result = await injected()

        assert result == 30  # 10 * 3

    @pytest.mark.asyncio
    async def test_validation_error_propagation(self) -> None:
        """Test that validation errors are propagated correctly."""

        async def async_provider() -> str:
            await asyncio.sleep(0.001)
            return "short"

        def length_validator(instance: Any, **kwargs: Any) -> str:
            if hasattr(instance, "__await__"):
                raise TypeError("Validator received coroutine!")

            if len(instance) < 10:
                raise ValueError(f"String too short: {len(instance)} chars")

            return instance

        async def handler(
            value: str = DependsInject(async_provider, validator=length_validator)
        ) -> str:
            return value

        with pytest.raises(ValueError, match="String too short"):
            injected = await inject_args(handler, {})
            await injected()

    @pytest.mark.asyncio
    async def test_no_validator_async_dependency(self) -> None:
        """Test async dependency without validator - should work normally."""

        async def async_provider() -> str:
            await asyncio.sleep(0.001)
            return "no_validation"

        async def handler(
            value: str = DependsInject(async_provider),  # No validator
        ) -> str:
            return value

        injected = await inject_args(handler, {})
        result = await injected()

        assert result == "no_validation"

    @pytest.mark.asyncio
    async def test_multiple_async_deps_with_mixed_validation(self) -> None:
        """Test multiple async deps - some with validator, others without."""

        async def async_string_provider() -> str:
            await asyncio.sleep(0.001)
            return "test_string"

        async def async_number_provider() -> int:
            await asyncio.sleep(0.001)
            return 100

        def string_validator(instance: Any, **kwargs: Any) -> str:
            return instance.upper()

        async def handler(
            validated_str: str = DependsInject(
                async_string_provider, validator=string_validator
            ),
            unvalidated_num: int = DependsInject(async_number_provider),  # No validator
        ) -> Tuple[str, int]:
            return validated_str, unvalidated_num

        injected = await inject_args(handler, {})
        result = await injected()

        assert result == ("TEST_STRING", 100)
