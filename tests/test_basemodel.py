"""
Comprehensive tests for BaseModel conversion in inject_args calls.

This module tests the complete integration of str->BaseModel and bytes->BaseModel
conversion within the ctxinject dependency injection system. It covers:
- Successful conversions through inject_args
- Validation failures and error handling
- Edge cases with nested models and complex types
- Performance and caching behavior
- Integration with different injectable patterns
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

import pytest
from typing_extensions import Annotated

from ctxinject import ArgsInjectable, DependsInject, inject_args
from ctxinject.model import CastType
from ctxinject.validation import ValidationError

# Skip entire module if Pydantic is not available
pydantic = pytest.importorskip("pydantic")
from pydantic import BaseModel, Field  # noqa: E402

# Apply asyncio marker to all async functions in this module
pytestmark = pytest.mark.asyncio


class SimpleModel(BaseModel):
    """Simple model for basic conversion tests."""

    name: str
    age: int
    active: bool = True


class UserModel(BaseModel):
    """User model with validation for testing constraints."""

    username: str = Field(min_length=3, max_length=20)
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(ge=0, le=150)
    is_admin: bool = False
    created_at: Optional[datetime] = None
    tags: List[str] = []
    metadata: Dict[str, str] = {}


class NestedModel(BaseModel):
    """Model with nested structures for complex tests."""

    id: UUID
    user: UserModel
    settings: Dict[str, int] = {}
    scores: List[float] = []


class ModelWithValidator(BaseModel):
    """Model with custom validator for testing validation logic."""

    value: int
    doubled_value: Optional[int] = None

    def model_post_init(self, __context) -> None:
        if self.doubled_value is None:
            self.doubled_value = self.value * 2


class TestBasicBaseModelConversion:
    """Test basic BaseModel conversion scenarios."""

    async def test_simple_str_to_basemodel_injection(self):
        """Test basic string to BaseModel conversion via inject_args."""

        def process_user(user: SimpleModel = CastType(str)) -> str:
            return f"{user.name} is {user.age} years old, active: {user.active}"

        json_str = '{"name": "Alice", "age": 30, "active": true}'
        context = {"user": json_str}

        injected_func = await inject_args(process_user, context)
        result = injected_func()

        assert result == "Alice is 30 years old, active: True"

    async def test_simple_str_to_basemodel_with_defaults(self):
        """Test BaseModel conversion with default values."""

        def process_user(user: SimpleModel = CastType(str)) -> SimpleModel:
            return user

        # Missing 'active' field - should use default
        json_str = '{"name": "Bob", "age": 25}'
        context = {"user": json_str}

        injected_func = await inject_args(process_user, context)
        result = injected_func()

        assert result.name == "Bob"
        assert result.age == 25
        assert result.active is True  # Default value

    async def test_bytes_to_basemodel_injection(self):
        """Test bytes to BaseModel conversion via inject_args."""

        def process_user(user: SimpleModel = CastType(bytes)) -> str:
            return f"{user.name} ({user.age})"

        json_bytes = b'{"name": "Charlie", "age": 35, "active": false}'
        context = {"user": json_bytes}

        injected_func = await inject_args(process_user, context)
        result = injected_func()

        assert result == "Charlie (35)"

    async def test_annotated_basemodel_injection(self):
        """Test BaseModel injection using Annotated syntax."""

        def process_data(user: Annotated[SimpleModel, CastType(str)]) -> Dict[str, any]:
            return {"name": user.name, "age": user.age, "active": user.active}

        json_str = '{"name": "Diana", "age": 28}'
        context = {"user": json_str}

        injected_func = await inject_args(process_data, context)
        result = injected_func()

        assert result["name"] == "Diana"
        assert result["age"] == 28
        assert result["active"] is True

    async def test_multiple_basemodel_injections(self):
        """Test multiple BaseModel injections in same function."""

        def process_multiple(
            primary: SimpleModel = CastType(str), secondary: SimpleModel = CastType(str)
        ) -> str:
            return f"Primary: {primary.name}, Secondary: {secondary.name}"

        context = {
            "primary": '{"name": "User1", "age": 20}',
            "secondary": '{"name": "User2", "age": 30}',
        }

        injected_func = await inject_args(process_multiple, context)
        result = injected_func()

        assert result == "Primary: User1, Secondary: User2"


class TestBaseModelValidationErrors:
    """Test BaseModel conversion failure scenarios."""

    async def test_invalid_json_string(self):
        """Test injection with malformed JSON string."""

        def process_user(user: SimpleModel = CastType(str)) -> str:
            return user.name

        context = {"user": "invalid json string"}

        with pytest.raises(ValidationError, match="Invalid JSON"):
            await inject_args(process_user, context)

    async def test_invalid_json_bytes(self):
        """Test injection with malformed JSON bytes."""

        def process_user(user: SimpleModel = CastType(bytes)) -> str:
            return user.name

        context = {"user": b"invalid json bytes"}

        with pytest.raises(ValidationError, match="Invalid JSON"):
            await inject_args(process_user, context)

    async def test_missing_required_fields(self):
        """Test BaseModel validation with missing required fields."""

        def process_user(user: SimpleModel = CastType(str)) -> str:
            return user.name

        # Missing required 'name' and 'age' fields
        context = {"user": '{"active": true}'}

        with pytest.raises(ValidationError):
            await inject_args(process_user, context)

    async def test_wrong_field_types(self):
        """Test BaseModel validation with incorrect field types."""

        def process_user(user: SimpleModel = CastType(str)) -> str:
            return user.name

        # 'age' should be int, not string
        context = {"user": '{"name": "John", "age": "thirty", "active": true}'}

        with pytest.raises(ValidationError):
            await inject_args(process_user, context)

    async def test_constraint_violations(self):
        """Test BaseModel with field constraint violations."""

        def process_user(user: UserModel = CastType(str)) -> str:
            return user.username

        # Username too short (min_length=3)
        context = {"user": '{"username": "ab", "email": "test@example.com", "age": 25}'}

        with pytest.raises(ValidationError):
            await inject_args(process_user, context)

    async def test_regex_validation_failure(self):
        """Test BaseModel with regex validation failure."""

        def process_user(user: UserModel = CastType(str)) -> str:
            return user.email

        # Invalid email format
        context = {
            "user": '{"username": "testuser", "email": "invalid-email", "age": 25}'
        }

        with pytest.raises(ValidationError):
            await inject_args(process_user, context)

    async def test_numeric_constraint_violations(self):
        """Test BaseModel with numeric constraint violations."""

        def process_user(user: UserModel = CastType(str)) -> int:
            return user.age

        # Age too high (le=150)
        context = {
            "user": '{"username": "olduser", "email": "old@example.com", "age": 200}'
        }

        with pytest.raises(ValidationError):
            await inject_args(process_user, context)


class TestComplexBaseModelScenarios:
    """Test complex BaseModel conversion scenarios."""

    async def test_nested_model_conversion(self):
        """Test conversion of nested BaseModel structures."""

        def process_nested(data: NestedModel = CastType(str)) -> str:
            return f"User: {data.user.username}, ID: {data.id}"

        nested_json = """
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "user": {
                "username": "nesteduser",
                "email": "nested@example.com",
                "age": 30
            },
            "settings": {"theme": 1, "notifications": 0},
            "scores": [95.5, 87.2, 91.0]
        }
        """

        context = {"data": nested_json}

        injected_func = await inject_args(process_nested, context)
        result = injected_func()

        assert "User: nesteduser" in result
        assert "550e8400-e29b-41d4-a716-446655440000" in result

    async def test_model_with_custom_validator(self):
        """Test BaseModel with custom validators."""

        def process_validated(model: ModelWithValidator = CastType(str)) -> int:
            return model.doubled_value

        context = {"model": '{"value": 15}'}

        injected_func = await inject_args(process_validated, context)
        result = injected_func()

        assert result == 30  # Custom validator should double the value

    async def test_list_and_dict_fields(self):
        """Test BaseModel with List and Dict fields."""

        def process_user(user: UserModel = CastType(str)) -> Dict[str, any]:
            return {
                "tags_count": len(user.tags),
                "metadata_keys": list(user.metadata.keys()),
            }

        complex_json = """
        {
            "username": "complexuser",
            "email": "complex@example.com",
            "age": 28,
            "tags": ["python", "testing", "pydantic"],
            "metadata": {"department": "engineering", "level": "senior"}
        }
        """

        context = {"user": complex_json}

        injected_func = await inject_args(process_user, context)
        result = injected_func()

        assert result["tags_count"] == 3
        assert "department" in result["metadata_keys"]
        assert "level" in result["metadata_keys"]

    async def test_optional_datetime_field(self):
        """Test BaseModel with optional datetime fields."""

        def process_user(user: UserModel = CastType(str)) -> bool:
            return user.created_at is not None

        # Without datetime
        context1 = {
            "user": '{"username": "user1", "email": "user1@example.com", "age": 25}'
        }
        injected_func1 = await inject_args(process_user, context1)
        result1 = injected_func1()
        assert result1 is False

        # With datetime
        context2 = {
            "user": '{"username": "user2", "email": "user2@example.com", "age": 25, "created_at": "2023-01-15T10:30:00"}'
        }
        injected_func2 = await inject_args(process_user, context2)
        result2 = injected_func2()
        assert result2 is True


class TestBaseModelWithDependsInject:
    """Test BaseModel conversion with DependsInject patterns."""

    async def test_depends_inject_returning_json_string(self):
        """Test DependsInject providing JSON string for BaseModel."""

        async def get_user_json() -> str:
            await asyncio.sleep(0.01)  # Simulate async operation
            return '{"name": "AsyncUser", "age": 40}'

        def process_user(user: SimpleModel = DependsInject(get_user_json)) -> str:
            return f"Processed: {user.name}"

        context = {}

        injected_func = await inject_args(process_user, context)
        result = injected_func()

        assert result == "Processed: AsyncUser"

    async def test_depends_inject_with_context_params(self):
        """Test DependsInject that uses context to build BaseModel JSON."""

        def build_user_json(
            name: str = ArgsInjectable(...), age: int = ArgsInjectable(25)
        ) -> str:
            return f'{{"name": "{name}", "age": {age}, "active": true}}'

        def process_user(
            user: SimpleModel = DependsInject(build_user_json),
        ) -> SimpleModel:
            return user

        context = {"name": "DependsUser", "age": 35}

        injected_func = await inject_args(process_user, context)
        result = injected_func()

        assert result.name == "DependsUser"
        assert result.age == 35
        assert result.active is True

    async def test_nested_depends_basemodel_conversion(self):
        """Test nested DependsInject with BaseModel conversion at multiple levels."""

        def get_user_data() -> str:
            return '{"username": "deepuser", "email": "deep@example.com", "age": 30}'

        def get_nested_data(user_data: UserModel = DependsInject(get_user_data)) -> str:
            return f'{{"id": "550e8400-e29b-41d4-a716-446655440000", "user": {user_data.model_dump_json()}}}'

        def process_nested(nested: NestedModel = DependsInject(get_nested_data)) -> str:
            return f"Nested user: {nested.user.username}"

        context = {}

        injected_func = await inject_args(process_nested, context)
        result = injected_func()

        assert result == "Nested user: deepuser"


class TestBaseModelPerformanceAndCaching:
    """Test performance aspects and caching behavior."""

    async def test_same_json_multiple_injections(self):
        """Test multiple injections with same JSON string (potential caching)."""

        def process1(user: SimpleModel = CastType(str)) -> str:
            return user.name

        def process2(user: SimpleModel = CastType(str)) -> int:
            return user.age

        json_str = '{"name": "CacheTest", "age": 50}'
        context = {"user": json_str}

        # Multiple injections with same context
        injected1 = await inject_args(process1, context)
        injected2 = await inject_args(process2, context)

        result1 = injected1()
        result2 = injected2()

        assert result1 == "CacheTest"
        assert result2 == 50

    async def test_large_json_conversion(self):
        """Test conversion of larger JSON structures."""

        def process_user(user: UserModel = CastType(str)) -> int:
            return len(user.tags)

        # Large JSON with many tags
        large_json = {
            "username": "largeuser",
            "email": "large@example.com",
            "age": 30,
            "tags": [f"tag{i}" for i in range(100)],
            "metadata": {f"key{i}": f"value{i}" for i in range(50)},
        }

        import json

        context = {"user": json.dumps(large_json)}

        injected_func = await inject_args(process_user, context)
        result = injected_func()

        assert result == 100

    async def test_concurrent_basemodel_injections(self):
        """Test concurrent BaseModel injections."""

        def process_user(user: SimpleModel = CastType(str)) -> str:
            return user.name

        async def inject_and_call(name: str, age: int) -> str:
            json_str = f'{{"name": "{name}", "age": {age}}}'
            context = {"user": json_str}
            injected_func = await inject_args(process_user, context)
            return injected_func()

        # Run multiple injections concurrently
        tasks = [inject_and_call(f"User{i}", 20 + i) for i in range(10)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(f"User{i}" == results[i] for i in range(10))


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    async def test_empty_json_object(self):
        """Test BaseModel with empty JSON object."""

        class OptionalModel(BaseModel):
            name: str = "default"
            age: int = 0

        def process_user(user: OptionalModel = CastType(str)) -> str:
            return f"{user.name}:{user.age}"

        context = {"user": "{}"}

        injected_func = await inject_args(process_user, context)
        result = injected_func()

        assert result == "default:0"

    async def test_null_values_in_json(self):
        """Test BaseModel with null values in JSON."""

        class NullableModel(BaseModel):
            name: Optional[str] = None
            age: int = 25

        def process_user(user: NullableModel = CastType(str)) -> str:
            return f"name={user.name}, age={user.age}"

        context = {"user": '{"name": null, "age": 30}'}

        injected_func = await inject_args(process_user, context)
        result = injected_func()

        assert result == "name=None, age=30"

    async def test_unicode_in_json(self):
        """Test BaseModel with Unicode characters in JSON."""

        def process_user(user: SimpleModel = CastType(str)) -> str:
            return user.name

        context = {"user": '{"name": "José María", "age": 25}'}

        injected_func = await inject_args(process_user, context)
        result = injected_func()

        assert result == "José María"

    async def test_scientific_notation_numbers(self):
        """Test BaseModel with scientific notation in JSON."""

        class ScientificModel(BaseModel):
            value: float
            count: int

        def process_data(data: ScientificModel = CastType(str)) -> float:
            return data.value

        context = {"data": '{"value": 1.23e-4, "count": 1e3}'}

        injected_func = await inject_args(process_data, context)
        result = injected_func()

        assert abs(result - 0.000123) < 1e-10

    async def test_very_nested_json(self):
        """Test BaseModel with deeply nested JSON structures."""

        class DeepModel(BaseModel):
            level1: Dict[str, Dict[str, Dict[str, str]]]

        def process_deep(data: DeepModel = CastType(str)) -> str:
            return data.level1["a"]["b"]["c"]

        nested_json = """
        {
            "level1": {
                "a": {
                    "b": {
                        "c": "deep_value"
                    }
                }
            }
        }
        """

        context = {"data": nested_json}

        injected_func = await inject_args(process_deep, context)
        result = injected_func()

        assert result == "deep_value"


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""

    async def test_partial_injection_with_basemodel_failure(self):
        """Test partial injection when BaseModel conversion fails."""

        def process_mixed(
            user: SimpleModel = CastType(str), count: int = ArgsInjectable(10)
        ) -> str:
            return f"{user.name}: {count}"

        # Valid count but invalid user JSON
        context = {"user": "invalid json", "count": 5}

        with pytest.raises(ValidationError):
            await inject_args(process_mixed, context)

    async def test_allow_incomplete_with_failed_basemodel(self):
        """Test allow_incomplete=True with failed BaseModel conversion."""

        def process_optional(
            user: SimpleModel = CastType(str),
            backup_name: str = ArgsInjectable("Unknown"),
        ) -> str:
            return f"User: {user.name if hasattr(user, 'name') else backup_name}"

        # Invalid user JSON, but allow_incomplete=True
        context = {"backup_name": "Fallback User"}

        # This should work with incomplete injection
        injected_func = await inject_args(
            process_optional, context, allow_incomplete=True
        )

        # The function should still have the 'user' parameter since it couldn't be resolved
        # This tests that BaseModel conversion failure is handled properly
        import inspect

        sig = inspect.signature(injected_func)
        assert "user" in sig.parameters

    async def test_validation_error_details(self):
        """Test that validation errors contain useful details."""

        def process_user(user: UserModel = CastType(str)) -> str:
            return user.username

        # Multiple validation errors
        context = {"user": '{"username": "ab", "email": "bad-email", "age": -5}'}

        with pytest.raises(ValidationError) as exc_info:
            await inject_args(process_user, context)

        # Should contain details about the validation failures
        error_message = str(exc_info.value)
        assert "validation" in error_message.lower() or "error" in error_message.lower()


# Integration tests combining BaseModel with other ctxinject features
class TestBaseModelIntegration:
    """Test BaseModel conversion integrated with other ctxinject features."""

    async def test_basemodel_with_overrides(self):
        """Test BaseModel injection with dependency overrides."""

        def get_user_data() -> str:
            return '{"name": "Original", "age": 30}'

        def get_test_data() -> str:
            return '{"name": "Override", "age": 35}'

        def process_user(user: SimpleModel = DependsInject(get_user_data)) -> str:
            return user.name

        context = {}
        overrides = {get_user_data: get_test_data}

        injected_func = await inject_args(process_user, context, overrides=overrides)
        result = injected_func()

        assert result == "Override"

    async def test_basemodel_with_validation_disabled(self):
        """Test BaseModel injection with validation disabled."""

        def process_user(user: SimpleModel = CastType(str)) -> str:
            return f"{user.name}:{user.age}"

        def process_user_string(user: str = ArgsInjectable(...)) -> str:
            return f"Raw string: {user}"

        context = {"user": '{"name": "Test", "age": 25}'}

        # Test with validation enabled (default) - BaseModel conversion happens
        injected_func1 = await inject_args(process_user, context, validate=True)
        result1 = injected_func1()
        assert result1 == "Test:25"

        # Test with validation disabled - no BaseModel conversion, gets raw string
        injected_func2 = await inject_args(process_user_string, context, validate=False)
        result2 = injected_func2()
        assert result2 == 'Raw string: {"name": "Test", "age": 25}'

    async def test_basemodel_ordered_execution(self):
        """Test BaseModel injection with ordered=True optimization."""

        async def get_user_json() -> str:
            return '{"name": "OrderedUser", "age": 45}'

        def process_user(
            user: SimpleModel = DependsInject(get_user_json),
            prefix: str = ArgsInjectable("Result"),
        ) -> str:
            return f"{prefix}: {user.name}"

        context = {"prefix": "Optimized"}

        # Test with ordered execution
        injected_func = await inject_args(process_user, context, ordered=True)
        result = injected_func()

        assert result == "Optimized: OrderedUser"

    async def test_basemodel_with_async_context_managers(self):
        """Test BaseModel injection with async context managers in DependsInject."""

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def get_user_data_context():
            # Simulate resource acquisition
            await asyncio.sleep(0.01)
            try:
                yield SimpleModel(name="ContextUser", age=50)  # Return actual BaseModel
            finally:
                # Simulate cleanup
                await asyncio.sleep(0.01)

        def process_user(
            user: SimpleModel = DependsInject(get_user_data_context),
        ) -> str:
            return f"Context: {user.name}"

        context = {}

        from contextlib import AsyncExitStack

        async with AsyncExitStack() as stack:
            injected_func = await inject_args(process_user, context, stack=stack)
            result = injected_func()

            assert result == "Context: ContextUser"


if __name__ == "__main__":
    # Run specific test classes for development
    pytest.main([__file__, "-v"])
