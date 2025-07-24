"""
Tests for constraint validation functionality.

This module tests all constraint validators including string, number, datetime,
UUID, enum, and collection constraints. It also tests the constraint factory
and integration with the injection system.
"""

from datetime import datetime
from functools import partial
from typing import Any, Dict
from uuid import UUID

import pytest
from typing_extensions import Annotated

from ctxinject.constrained import (
    ConstrainedDatetime,
    ConstrainedEnum,
    ConstrainedItems,
    ConstrainedNumber,
    ConstrainedStr,
    ConstrainedUUID,
    constrained_factory,
)
from ctxinject.inject import inject_args
from ctxinject.model import ConstrArgInject
from tests.conftest import (
    INVALID_CONSTRAINT_TEST_DATA,
    VALID_CONSTRAINT_TEST_DATA,
    MyEnum,
    SecondaryEnum,
    sample_constrained_function,
)


class TestConstrainedValidators:
    """Test cases for individual constraint validators."""

    @pytest.mark.parametrize("test_name,value,kwargs", VALID_CONSTRAINT_TEST_DATA)
    def test_valid_constraints(
        self, test_name: str, value: Any, kwargs: Dict[str, Any]
    ) -> None:
        """Test that valid values pass constraint validation."""
        if test_name.startswith("string"):
            result = ConstrainedStr(value, **kwargs)
            assert result == value
        elif test_name.startswith("number"):
            result = ConstrainedNumber(value, **kwargs)
            assert result == value
        elif test_name.startswith("datetime"):
            result = ConstrainedDatetime(value, **kwargs)
            assert isinstance(result, datetime)
        elif test_name.startswith("uuid"):
            result = ConstrainedUUID(value, **kwargs)
            assert isinstance(result, UUID)
        elif test_name.startswith("enum"):
            result = ConstrainedEnum(value, **kwargs)
            assert result == value

    @pytest.mark.parametrize("test_name,value,kwargs", INVALID_CONSTRAINT_TEST_DATA)
    def test_invalid_constraints(
        self, test_name: str, value: Any, kwargs: Dict[str, Any]
    ) -> None:
        """Test that invalid values fail constraint validation."""
        with pytest.raises(ValueError):
            if test_name.startswith("string"):
                ConstrainedStr(value, **kwargs)
            elif test_name.startswith("number"):
                ConstrainedNumber(value, **kwargs)
            elif test_name.startswith("datetime"):
                ConstrainedDatetime(value, **kwargs)
            elif test_name.startswith("uuid"):
                ConstrainedUUID(value, **kwargs)
            elif test_name.startswith("enum"):
                ConstrainedEnum(value, **kwargs)

    def test_constrained_items_collections(self) -> None:
        """Test constraint validation for different collection types."""
        # List validation
        ConstrainedItems([1, 2, 3], [int], min_items=1, max_items=10, gt=0, lt=5)
        ConstrainedItems(
            ["1", "2", "3"],
            [str],
            min_items=1,
            max_items=10,
            min_length=1,
            max_length=10,
        )

        # Dict validation
        ConstrainedItems(
            {"foo": "bar"}, [str], min_items=0, max_items=2, min_length=1, max_length=10
        )

        # Set validation
        ConstrainedItems({1, 2}, [int], min_items=1, max_items=3, gt=0)

        # Tuple validation
        with pytest.raises(ValueError):
            ConstrainedItems((1, 2, 3, 4), [int], max_items=3)

    def test_constrained_items_failures(self) -> None:
        """Test various failure cases for constrained items."""
        with pytest.raises(ValueError):
            ConstrainedItems([1, 2, 3], [int], max_items=2)

        with pytest.raises(ValueError):
            ConstrainedItems([1, 2, 3], [int], gt=3)

        with pytest.raises(ValueError):
            ConstrainedItems(["1", "2", "3"], [str], min_items=1, max_items=2)

        with pytest.raises(ValueError):
            ConstrainedItems(["1", "2", "3"], [str], min_length=2)

        # Dict with values check
        with pytest.raises(ValueError):
            ConstrainedItems(
                {"f": "bar"},
                [str, str],
                values_check={"max_length": 2},
                min_items=0,
                max_items=2,
                max_length=2,
            )

    def test_constrained_datetime_formats(self) -> None:
        """Test datetime constraint with various formats."""
        may_1_24 = "2024-05-01"
        result = ConstrainedDatetime(may_1_24)
        assert result == datetime(2024, 5, 1)

        # Custom format
        result_custom = ConstrainedDatetime(may_1_24, fmt="%Y-%m-%d")
        assert result_custom == datetime(2024, 5, 1)

        # Wrong format should fail
        with pytest.raises(ValueError):
            ConstrainedDatetime("01/05/2024", fmt="%Y-%m-%d")

        # Date range validation
        with pytest.raises(ValueError):
            ConstrainedDatetime("01/05/2024", from_=datetime(2025, 1, 1))

        with pytest.raises(ValueError):
            ConstrainedDatetime("01/05/2024", to_=datetime(2023, 1, 1))


class TestConstrainedFactory:
    """Test cases for the constraint factory system."""

    def test_factory_type_mapping(self) -> None:
        """Test that factory correctly maps types to constraint functions."""
        assert constrained_factory(str) is ConstrainedStr
        assert constrained_factory(int) is ConstrainedNumber
        assert constrained_factory(float) is ConstrainedNumber
        assert constrained_factory(UUID) is ConstrainedUUID

    def test_factory_generic_types(self) -> None:
        """Test factory behavior with generic types."""
        # List factory
        constr_list = constrained_factory(list[str])
        assert isinstance(constr_list, partial)
        assert "basetype" in constr_list.keywords
        assert constr_list.keywords["basetype"][0] is str

        # Should work with valid data
        constr_list(["foo", "bar"])

        # Should fail with constraint violation
        with pytest.raises(ValueError):
            constr_list(["1", "2", "3"], min_length=2)

        # Int list factory
        constr_listint = constrained_factory(list[int])
        constr_listint([40, 45])

        with pytest.raises(ValueError):
            constr_listint([40, 45], gt=42)

        # Dict factory
        constr_dict = constrained_factory(dict[str, str])
        constr_dict({"foo": "bar"})

    def test_factory_enum_types(self) -> None:
        """Test factory behavior with enum types."""
        constr_enum = constrained_factory(MyEnum)
        constr_enum(MyEnum.INVALID)

        with pytest.raises(ValueError):
            constr_enum(0)  # Raw value instead of enum

    def test_factory_datetime_types(self) -> None:
        """Test factory behavior with datetime types."""
        constr_date = constrained_factory(datetime)
        assert isinstance(constr_date, partial)

    def test_factory_annotated_types(self) -> None:
        """Test factory behavior with Annotated types."""
        factory = constrained_factory(Annotated[list[int], "whatever"])
        assert isinstance(factory, partial)
        assert factory.keywords["basetype"][0] is int

    def test_factory_fallback(self) -> None:
        """Test factory fallback for unsupported types."""

        class UnsupportedType:
            pass

        factory = constrained_factory(UnsupportedType)
        assert callable(factory)
        # Should return value unchanged
        assert factory("any_value") == "any_value"


class TestConstrainedIntegration:
    """Test cases for constraint integration with injection system."""

    @pytest.mark.asyncio
    async def test_full_constrained_injection_success(
        self, sample_uuid: str, sample_datetime_str: str
    ) -> None:
        """Test successful injection with all constraint types."""
        ctx: Dict[str, Any] = {
            "arg1": sample_uuid,
            "arg2": sample_datetime_str,
            "arg3": "foobar",
            "arg4": MyEnum.INVALID,
            "arg5": ["hello"],
        }

        # Should not raise any exceptions
        await inject_args(sample_constrained_function, ctx)

    @pytest.mark.asyncio
    async def test_full_constrained_injection_uuid_failure(
        self, invalid_uuid: str, sample_datetime_str: str
    ) -> None:
        """Test injection failure with invalid UUID."""
        ctx: Dict[str, Any] = {
            "arg1": invalid_uuid,
            "arg2": sample_datetime_str,
            "arg3": "foobar",
            "arg4": MyEnum.INVALID,
            "arg5": ["hello"],
        }

        with pytest.raises(ValueError, match="valid UUID string"):
            await inject_args(sample_constrained_function, ctx)

    @pytest.mark.asyncio
    async def test_full_constrained_injection_datetime_failure(
        self, sample_uuid: str, invalid_datetime_str: str
    ) -> None:
        """Test injection failure with invalid datetime."""
        ctx: Dict[str, Any] = {
            "arg1": sample_uuid,
            "arg2": invalid_datetime_str,
            "arg3": "foobar",
            "arg4": MyEnum.INVALID,
            "arg5": ["hello"],
        }

        with pytest.raises(ValueError, match="valid datetime string"):
            await inject_args(sample_constrained_function, ctx)

    @pytest.mark.asyncio
    async def test_custom_validator_integration(self) -> None:
        """Test integration with custom validator functions."""

        def custom_validator(instance: Any, **kwargs: Any) -> str:
            if instance == "forbidden":
                raise ValueError("Custom validation failed")
            return instance

        # Create injectable with custom validator
        injectable = ConstrArgInject(constrained_factory, validator=custom_validator)

        with pytest.raises(ValueError, match="Custom validation failed"):
            injectable.validate("forbidden", str)

    @pytest.mark.asyncio
    async def test_constraint_with_string_length(self) -> None:
        """Test string constraint with length validation."""

        def func(
            text: str = ConstrArgInject(constrained_factory, ..., min_length=5)
        ) -> str:
            return text

        # Should work with valid length
        ctx = {"text": "hello world"}
        injected = await inject_args(func, ctx)
        result = injected()
        assert result == "hello world"

        # Should fail with short string
        ctx_fail = {"text": "hi"}
        with pytest.raises(ValueError, match="String length"):
            await inject_args(func, ctx_fail)

    @pytest.mark.asyncio
    async def test_constraint_with_number_range(self) -> None:
        """Test number constraint with range validation."""

        def func(
            num: int = ConstrArgInject(constrained_factory, ..., gt=0, lt=100)
        ) -> int:
            return num

        # Should work with valid number
        ctx = {"num": 50}
        injected = await inject_args(func, ctx)
        result = injected()
        assert result == 50

        # Should fail with out of range number
        ctx_fail = {"num": 150}
        with pytest.raises(ValueError, match="Value must be"):
            await inject_args(func, ctx_fail)

    def test_constraint_string_pattern(self) -> None:
        """Test string constraint with regex pattern."""
        # Should pass with valid pattern
        result = ConstrainedStr("hello", pattern=r"^[a-z]+$")
        assert result == "hello"

        # Should fail with invalid pattern
        with pytest.raises(ValueError, match="does not match pattern"):
            ConstrainedStr("Hello123", pattern=r"^[a-z]+$")

    def test_constraint_number_multiple_of(self) -> None:
        """Test number constraint with multiple_of validation."""
        # Should pass
        result = ConstrainedNumber(15, multiple_of=5)
        assert result == 15

        # Should fail
        with pytest.raises(ValueError, match="multiple of"):
            ConstrainedNumber(16, multiple_of=5)

    def test_constraint_items_with_nested_validation(self) -> None:
        """Test constrained items with nested item validation."""
        # Should pass with valid items
        ConstrainedItems(
            [5, 10, 15], [int], min_items=2, max_items=5, gt=0, multiple_of=5
        )

        # Should fail with invalid nested validation
        with pytest.raises(ValueError):
            ConstrainedItems(
                [1, 2, 3],
                [int],
                min_items=2,
                max_items=5,
                gt=5,  # All items must be > 5
            )

    def test_constraint_items_dict_values(self) -> None:
        """Test constrained items with dictionary value validation."""
        # Should pass
        ConstrainedItems(
            {"a": "hello", "b": "world"},
            [str, str],
            values_check={"min_length": 3},
            min_items=1,
            max_items=3,
        )

        # Should fail with short values
        with pytest.raises(ValueError):
            ConstrainedItems(
                {"a": "hi", "b": "ok"},
                [str, str],
                values_check={"min_length": 3},
                min_items=1,
                max_items=3,
            )


class TestConstraintEdgeCases:
    """Test edge cases and error conditions for constraints."""

    def test_constraint_factory_with_none_type(self) -> None:
        """Test factory behavior with None type."""
        factory = constrained_factory(type(None))
        # Should return pass-through function
        assert factory(None) is None
        assert factory("anything") == "anything"

    def test_constraint_datetime_edge_cases(self) -> None:
        """Test datetime constraint edge cases."""
        # Test with different datetime types
        from datetime import date, time

        # Date constraint
        date_factory = constrained_factory(date)
        assert isinstance(date_factory, partial)

        # Time constraint
        time_factory = constrained_factory(time)
        assert isinstance(time_factory, partial)

    def test_constraint_enum_with_invalid_values(self) -> None:
        """Test enum constraint with various invalid inputs."""
        # Integer instead of enum
        with pytest.raises(ValueError, match="should be of type"):
            ConstrainedEnum(1, MyEnum)

        # Wrong enum type
        with pytest.raises(ValueError, match="should be of type"):
            ConstrainedEnum(SecondaryEnum.FOO, MyEnum)

        # String instead of enum
        with pytest.raises(ValueError, match="should be of type"):
            ConstrainedEnum("VALID", MyEnum)

    def test_constraint_uuid_edge_cases(self) -> None:
        """Test UUID constraint with various invalid formats."""
        invalid_uuids = [
            "not-a-uuid",
            "12345",
            "",
            "3cd4d94e-61e9-4c90-bd39",  # Too short
            "3cd4d94e-61e9-4c90-bd39-9207a1fb7227-extra",  # Too long
            "3cd4d94e/61e9/4c90/bd39/9207a1fb7227",  # Wrong separators
        ]

        for invalid_uuid in invalid_uuids:
            with pytest.raises(ValueError, match="valid UUID string"):
                ConstrainedUUID(invalid_uuid)

    def test_constraint_datetime_invalid_formats(self) -> None:
        """Test datetime constraint with invalid date formats."""
        invalid_dates = [
            "2023-13-01",  # Invalid month
            "2023-01-32",  # Invalid day
            "not-a-date",
            "2023/13/01",  # Different format
            "",
            "2023-02-30",  # Invalid date for February
        ]

        for invalid_date in invalid_dates:
            with pytest.raises(ValueError):
                ConstrainedDatetime(invalid_date)

    def test_constraint_number_boundary_conditions(self) -> None:
        """Test number constraints at boundary conditions."""
        # Test exact boundaries
        ConstrainedNumber(10, ge=10)  # Should pass
        ConstrainedNumber(10, le=10)  # Should pass

        with pytest.raises(ValueError):
            ConstrainedNumber(10, gt=10)  # Should fail (not strictly greater)

        with pytest.raises(ValueError):
            ConstrainedNumber(10, lt=10)  # Should fail (not strictly less)

        # Test with floats
        ConstrainedNumber(10.0, ge=10.0)
        ConstrainedNumber(9.999, lt=10.0)

        with pytest.raises(ValueError):
            ConstrainedNumber(10.001, le=10.0)

    def test_constraint_string_empty_and_whitespace(self) -> None:
        """Test string constraints with empty strings and whitespace."""
        # Empty string validation
        with pytest.raises(ValueError):
            ConstrainedStr("", min_length=1)

        # Whitespace handling
        ConstrainedStr("   ", min_length=3)  # Whitespace counts

        # Pattern with whitespace
        ConstrainedStr("hello world", pattern=r"^[a-z ]+$")

        with pytest.raises(ValueError):
            ConstrainedStr("hello\tworld", pattern=r"^[a-z ]+$")  # Tab not allowed

    @pytest.mark.parametrize("collection_type", [list, tuple, set])
    def test_constraint_items_different_collections(
        self, collection_type: type
    ) -> None:
        """Test constrained items with different collection types."""
        data = collection_type([1, 2, 3])

        # Should work with all collection types
        result = ConstrainedItems(data, [int], min_items=1, max_items=5, gt=0)
        assert result == data

    def test_constraint_items_empty_collections(self) -> None:
        """Test constrained items with empty collections."""
        # Empty list with min_items=0 should pass
        ConstrainedItems([], [int], min_items=0, max_items=5)

        # Empty list with min_items>0 should fail
        with pytest.raises(ValueError):
            ConstrainedItems([], [int], min_items=1, max_items=5)

        # Empty dict
        ConstrainedItems({}, [str], min_items=0, max_items=5)


class TestConstraintPerformance:
    """Performance and stress tests for constraints."""

    @pytest.mark.slow
    def test_constraint_large_collections(self) -> None:
        """Test constraint performance with large collections."""
        large_list = list(range(1000))

        # Should handle large collections efficiently
        result = ConstrainedItems(
            large_list, [int], min_items=500, max_items=2000, ge=0
        )
        assert result == large_list

    @pytest.mark.slow
    def test_constraint_complex_patterns(self) -> None:
        """Test constraint performance with complex regex patterns."""
        complex_pattern = (
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        )

        # Valid password
        ConstrainedStr("MyPass123!", pattern=complex_pattern)

        # Invalid password
        with pytest.raises(ValueError):
            ConstrainedStr("weak", pattern=complex_pattern)

    @pytest.mark.performance
    def test_constraint_factory_caching(self) -> None:
        """Test that constraint factory results can be cached effectively."""
        # Multiple calls should return same function for same type
        factory1 = constrained_factory(str)
        factory2 = constrained_factory(str)
        assert factory1 is factory2  # Should be same function reference

        # Different types should return different functions
        str_factory = constrained_factory(str)
        int_factory = constrained_factory(int)
        assert str_factory is not int_factory
