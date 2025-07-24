"""
Tests for dependency injection functionality.

This module tests the core injection mechanisms including argument resolution,
type-based injection, model field injection, and validation integration.
"""

from functools import partial
from typing import Any, Dict, Union

import pytest
from typemapping import get_func_args
from typing_extensions import Annotated

from ctxinject.inject import UnresolvedInjectableError, inject_args
from ctxinject.model import ArgsInjectable
from tests.conftest import (
    MyModel,
    MyModelField,
    MyModelMethod,
    No42,
    NoValidation,
    sample_injected_function,
    sample_method_injection_function,
)


class TestInjectArgs:
    """Test cases for argument injection functionality."""

    @pytest.mark.asyncio
    async def test_inject_by_name(self) -> None:
        """Test injection by parameter name."""
        ctx: Dict[Union[str, type], Any] = {
            "a": "hello",
            "b": "world",
            "c": 123,
            "e": "foobar",
            "h": 0.1,
        }

        injected = await inject_args(sample_injected_function, ctx)
        assert isinstance(injected, partial)

        result = injected()
        expected = ("hello", "world", 123, 44, "foobar", 3.14, True, 0.1)
        assert result == expected

    @pytest.mark.asyncio
    async def test_inject_by_type(self, model_field_instance: MyModelField) -> None:
        """Test injection by parameter type."""
        ctx: Dict[Union[str, type], Any] = {
            str: "typed!",
            int: 43,
            MyModel: 100,
            MyModelField: model_field_instance,
        }

        injected = await inject_args(sample_injected_function, ctx)
        result = injected(a="X")
        expected = ("X", "typed!", 100, 43, "foobar", 3.14, True, 2.2)
        assert result == expected

    @pytest.mark.asyncio
    async def test_inject_default_used(self) -> None:
        """Test that default values are used when not provided in context."""
        ctx = {
            "a": "A",
            "c": 100,
            "e": "hello",
            "h": 0.12,
        }  # 'b' and 'd' will use defaults

        injected = await inject_args(sample_injected_function, ctx)
        result = injected()
        expected = ("A", "abc", 100, 44, "hello", 3.14, True, 0.12)
        assert result == expected

    @pytest.mark.asyncio
    async def test_inject_changed_func_signature(self) -> None:
        """Test that injection changes function signature by removing resolved args."""
        original_args = get_func_args(sample_injected_function)
        ctx = {"a": "foobar", "b": "helloworld"}

        resolved_func = await inject_args(
            func=sample_injected_function, context=ctx, allow_incomplete=True
        )
        resolved_args = get_func_args(resolved_func)

        assert resolved_args != original_args
        assert len(resolved_args) < len(original_args)

    @pytest.mark.asyncio
    async def test_inject_chained(self) -> None:
        """Test chaining multiple injections on the same function."""
        original_args = get_func_args(sample_injected_function)

        # First injection
        ctx1 = {"a": "foobar"}
        resolved_func1 = await inject_args(sample_injected_function, ctx1, True)
        args1 = get_func_args(resolved_func1)
        assert args1 != original_args

        # Second injection on already injected function
        ctx2 = {"c": 2}
        resolved_func2 = await inject_args(resolved_func1, ctx2, True)
        args2 = get_func_args(resolved_func2)
        assert args2 != args1

    @pytest.mark.asyncio
    async def test_inject_name_over_type(self) -> None:
        """Test that name-based injection takes precedence over type-based."""
        ctx = {
            "b": "by_name",
            str: "by_type",  # Should be ignored since 'b' is provided by name
            "a": "ok",
            "c": 1,
            "e": "x",
            "h": 0.0,
        }

        injected = await inject_args(sample_injected_function, ctx)
        result = injected()
        assert result[1] == "by_name"  # Verify name takes precedence

    def test_annotated_multiple_extras(self) -> None:
        """Test that multiple injectable extras in Annotated are handled correctly."""

        def func(a: Annotated[int, No42(44), NoValidation()]) -> int:
            return a

        args = get_func_args(func)
        arg = args[0]

        # Should be able to get both injectable types
        assert isinstance(arg.getinstance(No42), No42)
        assert isinstance(arg.getinstance(NoValidation), NoValidation)

    @pytest.mark.asyncio
    async def test_missing_required_arg(self) -> None:
        """Test that missing required arguments raise appropriate error."""

        def func(a: Annotated[str, ArgsInjectable(...)]) -> str:
            return a

        with pytest.raises(UnresolvedInjectableError, match="incomplete or missing"):
            await inject_args(func, {}, allow_incomplete=False)

    @pytest.mark.asyncio
    async def test_model_method_inject_basic(
        self, model_method_instance: MyModelMethod
    ) -> None:
        """Test basic model method injection."""
        ctx = {"x": "test_input", MyModelMethod: model_method_instance}

        injected = await inject_args(sample_method_injection_function, ctx)
        result = injected()
        expected = ("test_input", "basic_value", "basic_other")
        assert result == expected

    @pytest.mark.asyncio
    async def test_model_method_inject_name_overrides(self) -> None:
        """Test that name-based injection overrides model method injection."""
        ctx = {
            "x": "override_test",
            "y": "by_name_y",
            "z": "by_name_z",
            MyModelMethod: MyModelMethod(prefix="should_not_use"),
        }

        injected = await inject_args(sample_method_injection_function, ctx)
        result = injected()
        expected = ("override_test", "by_name_y", "by_name_z")
        assert result == expected

    @pytest.mark.asyncio
    async def test_model_method_inject_missing_model(self) -> None:
        """Test that missing model for method injection raises error."""
        ctx = {"x": "fail_case"}  # Missing MyModelMethod

        with pytest.raises(UnresolvedInjectableError, match="incomplete or missing"):
            await inject_args(
                sample_method_injection_function, ctx, allow_incomplete=False
            )

    @pytest.mark.asyncio
    async def test_validation_integration(self) -> None:
        """Test that validation is applied during injection when properly configured."""

        def func(value: int = No42(50)) -> int:
            return value

        # Should work with non-42 value
        ctx = {"value": 100}
        injected = await inject_args(func, ctx)
        result = injected()
        assert result == 100

        # Should fail with 42 because No42 validator rejects 42
        ctx_fail = {"value": 42}
        with pytest.raises(ValueError, match="Value 42 is not allowed"):
            await inject_args(func, ctx_fail)

    @pytest.mark.asyncio
    async def test_allow_incomplete_flag(self) -> None:
        """Test the allow_incomplete flag behavior."""

        def func(
            required: str = ArgsInjectable(...),
            optional: str = ArgsInjectable("default"),
        ) -> tuple[str, str]:
            return required, optional

        # With allow_incomplete=True, should succeed
        injected = await inject_args(func, {}, allow_incomplete=True)
        result = injected(required="provided")
        assert result == ("provided", "default")

        # With allow_incomplete=False, should fail for missing required
        with pytest.raises(UnresolvedInjectableError):
            await inject_args(func, {}, allow_incomplete=False)

    @pytest.mark.asyncio
    async def test_complex_type_resolution(self) -> None:
        """Test resolution with complex type hierarchies."""

        class BaseType:
            pass

        class DerivedType(BaseType):
            pass

        def func(
            base: BaseType = ArgsInjectable(), derived: DerivedType = ArgsInjectable()
        ) -> tuple[BaseType, DerivedType]:
            return base, derived

        derived_instance = DerivedType()
        ctx = {
            BaseType: BaseType(),
            DerivedType: derived_instance,
        }

        injected = await inject_args(func, ctx)
        result = injected()

        assert isinstance(result[0], BaseType)
        assert isinstance(result[1], DerivedType)
        assert result[1] is derived_instance

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "context_type,expected_value",
        [
            ("by_name", "name_value"),
            ("by_type", "type_value"),
        ],
    )
    async def test_parametrized_injection(
        self, context_type: str, expected_value: str
    ) -> None:
        """Test injection with parametrized contexts."""

        def func(param: str = ArgsInjectable()) -> str:
            return param

        if context_type == "by_name":
            ctx = {"param": expected_value}
        else:
            ctx = {str: expected_value}

        injected = await inject_args(func, ctx)
        result = injected()
        assert result == expected_value
