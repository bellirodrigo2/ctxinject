"""
Extended tests for sigcheck.py - covering edge cases and bugs.
"""

from pathlib import Path
from typing import Callable, Optional, Protocol, Union

from typemapping import get_func_args
from typing_extensions import Annotated

from ctxinject.model import DependsInject, Injectable, ModelFieldInject
from ctxinject.sigcheck import (
    check_all_typed,
    check_depends_types,
    check_modefield_types,
    func_signature_check,
)


class TestSigcheckBugs:
    """Test known bugs in sigcheck.py"""

    def test_args_mutation_bug(self) -> None:
        """Test that check functions mutate the input args list - THIS IS A BUG!"""

        def untyped_func(arg1, arg2: str) -> None:
            pass

        original_args = get_func_args(untyped_func)
        original_count = len(original_args)

        # This SHOULD NOT mutate original_args, but it does!
        errors = check_all_typed(original_args)

        # BUG: original_args is now mutated (shorter)
        assert len(original_args) < original_count, "BUG: args list was mutated!"
        assert len(errors) > 0

        # This affects subsequent checks on the same args
        more_errors = check_all_typed(original_args)
        assert (
            len(more_errors) == 0
        ), "Second check finds no errors because args were removed"

    def test_return_type_annotated_inconsistency(self) -> None:
        """Test inconsistent handling of Annotated in return types vs parameter types."""

        def dep_with_annotated_return() -> Annotated[str, "metadata"]:
            return "test"

        def func(arg: str = DependsInject(dep_with_annotated_return)) -> None:
            pass

        # This should work - both are str under the Annotated wrapper
        errors = check_depends_types(get_func_args(func))
        assert len(errors) == 0

    def test_type_cast_bidirectional_bug(self) -> None:
        """Test that type_cast only works in one direction."""

        class Model:
            x: str

        def func(arg: str = ModelFieldInject(Model, field="x")) -> None:
            pass

        # This works: (actual_type, expected_type)
        errors1 = check_modefield_types(get_func_args(func), type_cast=[(str, str)])
        assert errors1 == []

        # But reverse direction might not work
        class Model2:
            y: int

        def func2(arg: str = ModelFieldInject(Model2, field="y")) -> None:
            pass

        errors2 = check_modefield_types(
            get_func_args(func2), type_cast=[(str, int)]  # Reverse direction
        )
        assert errors2 == []


class TestSigcheckEdgeCases:
    """Test edge cases not covered in original tests."""

    def test_forward_references(self) -> None:
        """Test handling of forward references in type hints."""

        # Forward reference (string annotation)
        def func_with_forward_ref(arg: "str" = Injectable()) -> None:
            pass

        errors = func_signature_check(func_with_forward_ref)
        assert errors == []

    def test_union_types(self) -> None:
        """Test Union types with Injectable."""

        def func_with_union(arg: Union[str, int] = Injectable()) -> None:
            pass

        errors = func_signature_check(func_with_union)
        assert errors == []

    def test_optional_types(self) -> None:
        """Test Optional types with Injectable."""

        def func_with_optional(arg: Optional[str] = Injectable(None)) -> None:
            pass

        errors = func_signature_check(func_with_optional)
        assert errors == []

    def test_callable_types(self) -> None:
        """Test Callable types with Injectable."""

        def func_with_callable(arg: Callable[[int], str] = Injectable()) -> None:
            pass

        errors = func_signature_check(func_with_callable)
        assert errors == []

    def test_protocol_types(self) -> None:
        """Test Protocol types."""

        class MyProtocol(Protocol):
            def method(self) -> str: ...

        def func_with_protocol(arg: MyProtocol = Injectable()) -> None:
            pass

        errors = func_signature_check(func_with_protocol)
        assert errors == []

    def test_async_dependency_in_sync_function(self) -> None:
        """Test async dependency in sync function."""

        async def async_dep() -> str:
            return "async_result"

        def sync_func(arg: str = DependsInject(async_dep)) -> None:
            pass

        # Should this be allowed?
        errors = check_depends_types(get_func_args(sync_func))
        assert errors == []

    def test_lambda_dependency(self) -> None:
        """Test lambda as dependency (no __name__ attribute)."""

        def func_with_lambda(arg: str = DependsInject(lambda: "test")) -> None:
            pass

        errors = check_depends_types(get_func_args(func_with_lambda))
        assert errors == []

        def func_with_lambda_path(
            arg: Path = DependsInject(lambda: Path("./")),
        ) -> None:
            pass

        errors = check_depends_types(get_func_args(func_with_lambda_path))
        assert errors == []

    def test_nested_annotated(self) -> None:
        """Test nested Annotated types."""

        def func_with_nested_annotated(
            arg: Annotated[Annotated[str, "inner"], Injectable(), "outer"],
        ) -> None:
            pass

        errors = func_signature_check(func_with_nested_annotated)
        assert errors == []

    def test_model_inheritance_field_resolution(self) -> None:
        """Test field resolution with model inheritance."""

        class BaseModel:
            base_field: str

        class DerivedModel(BaseModel):
            derived_field: int

        def func_with_inherited_field(
            # Should find base_field in DerivedModel
            arg: str = ModelFieldInject(DerivedModel, field="base_field")
        ) -> None:
            pass

        errors = check_modefield_types(get_func_args(func_with_inherited_field))
        assert errors == []

    def test_complex_generic_types(self) -> None:
        """Test deeply nested generic types."""

        def func_with_complex_generics(
            arg: dict[str, list[Optional[Union[int, str]]]] = Injectable(),
        ) -> None:
            pass

        errors = func_signature_check(func_with_complex_generics)
        assert errors == []

    def test_type_hints_failure(self) -> None:
        """Test when get_type_hints fails."""

        # Create a function with unresolvable type hints
        def problematic_dep():
            # No return annotation
            return "test"

        def func_with_bad_dep(arg: str = DependsInject(problematic_dep)) -> None:
            pass

        errors = check_depends_types(get_func_args(func_with_bad_dep))
        assert len(errors) == 1
        assert "Depends Return should a be type, but None was found" in errors[0]


class TestSigcheckStress:
    """Stress tests for sigcheck."""

    def test_many_arguments(self) -> None:
        """Test function with many arguments."""

        # Dynamically create function with 50 arguments
        arg_list = []
        for i in range(50):
            arg_list.append(f"arg{i}: str = Injectable()")

        func_code = f"""
def many_args_func({', '.join(arg_list)}) -> None:
    pass
"""

        # Execute the function definition
        local_vars = {}
        exec(func_code, {"Injectable": Injectable}, local_vars)
        func = local_vars["many_args_func"]

        import time

        start = time.perf_counter()
        errors = func_signature_check(func)
        end = time.perf_counter()
        assert errors == []
        print(f"50 args check took {end - start:.4f}s, errors: {len(errors)}")

    def test_error_recovery(self) -> None:
        """Test that system recovers gracefully from multiple errors."""

        def broken_func(
            untyped1,  # No type
            untyped2,  # No type
            bad_injectable: int,  # No injectable
            bad_model: str = ModelFieldInject("not_a_type"),  # Invalid model
            bad_dep: str = DependsInject("not_callable"),  # Invalid dependency
        ) -> None:
            pass

        # Should get multiple errors but not crash
        errors = func_signature_check(broken_func, bt_default_fallback=False)
        assert len(errors) == 5  # Should find multiple distinct errors


class TestSigcheckImprovements:
    """Test areas where sigcheck could be improved."""

    def test_error_message_quality(self) -> None:
        """Test that error messages are helpful."""

        def bad_func(arg) -> None:  # Missing type
            pass

        errors = func_signature_check(bad_func, bt_default_fallback=False)

        # Error should mention the argument name
        assert any(
            'Argument "arg" error: has no type definition' in error for error in errors
        )
        assert len(errors) == 1

    def test_suggestion_context(self) -> None:
        """Test that errors provide context for fixes."""

        from pathlib import Path

        def uninjectable_func(path: Path) -> None:  # Path not in modeltype
            pass

        errors = func_signature_check(uninjectable_func, modeltype=[])

        # Should suggest how to fix
        assert any("cannot be injected" in error for error in errors)
        assert len(errors) == 1
        assert 'Argument "path" error:' in errors[0]

    def test_validation_integration_readiness(self) -> None:
        """Test that sigcheck prepares args for actual injection."""

        def valid_func(
            arg1: str = Injectable(), arg2: int = DependsInject(lambda: 42)
        ) -> None:
            pass

        # Should pass sigcheck
        errors = func_signature_check(valid_func)
        assert errors == []
