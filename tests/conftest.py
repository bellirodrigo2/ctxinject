"""
Pytest configuration and shared fixtures for ctxinject tests.

This module provides common fixtures and test utilities used across
all test modules. It includes sample models, enums, and helper functions
to reduce code duplication.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple

import pytest
from typing_extensions import Annotated

from ctxinject.model import ArgsInjectable, ModelFieldInject

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


# Sample enums used across multiple test modules
class MyEnum(Enum):
    """Sample enum for testing constraint validation."""

    VALID = 0
    INVALID = 1


class SecondaryEnum(Enum):
    """Secondary enum for testing enum conflicts."""

    FOO = 0
    BAR = 1


# Sample models used across multiple test modules
class User(str):
    """User type for testing type-based injection."""

    pass


@dataclass
class Settings:
    """Settings model for testing model field injection."""

    debug: bool
    timeout: int


class DB:
    """Database connection mock for testing dependency injection."""

    def __init__(self, url: str) -> None:
        self.url = url


class MyModel(int):
    """Custom model type for testing."""

    pass


class MyModelField:
    """Model with field attributes for testing field injection."""

    def __init__(self, e: str, f: float) -> None:
        self.e = e
        self.f = f


class MyModelMethod:
    """Model with methods for testing method injection."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def get_value(self) -> str:
        return f"{self.prefix}_value"

    def other_method(self) -> str:
        return f"{self.prefix}_other"


# Sample validation classes
class NoValidation(ArgsInjectable):
    """Injectable that performs no validation."""

    pass


class No42(ArgsInjectable):
    """Injectable that rejects the value 42."""

    def __init__(self, default: Any) -> None:
        super().__init__(default)
        # Set up a proper validator function to enable validation
        self._validator = self._validate_not_42

    @property
    def has_validate(self) -> bool:
        return True

    def _validate_not_42(self, instance: Any, **kwargs: Any) -> Any:
        if instance == 42:
            raise ValueError("Value 42 is not allowed")
        return instance

    def validate(self, instance: Any, basetype: Any) -> Any:
        return self._validate_not_42(instance)


# Fixtures for common test data
@pytest.fixture
def sample_uuid() -> str:
    """Provides a valid UUID string for testing."""
    return "3cd4d94e-61e9-4c90-bd39-9207a1fb7227"


@pytest.fixture
def invalid_uuid() -> str:
    """Provides an invalid UUID string for testing."""
    return "NotUUID"


@pytest.fixture
def sample_datetime_str() -> str:
    """Provides a valid datetime string for testing."""
    return "22-12-07"


@pytest.fixture
def invalid_datetime_str() -> str:
    """Provides an invalid datetime string for testing."""
    return "99-15-07"


@pytest.fixture
def basic_context() -> Dict[str, Any]:
    """Provides a basic injection context for testing."""
    return {
        "id": 42,
        "uid": 99,
        "debug": False,
        "name": "Alice",
        User: "Alice",
        Settings: Settings(debug=True, timeout=30),
    }


@pytest.fixture
def model_field_instance() -> MyModelField:
    """Provides a MyModelField instance for testing."""
    return MyModelField(e="foobar", f=2.2)


@pytest.fixture
def model_method_instance() -> MyModelMethod:
    """Provides a MyModelMethod instance for testing."""
    return MyModelMethod(prefix="basic")

# Sample dependency functions for testing
async def async_db_dependency() -> DB:
    """Async dependency that returns a DB instance."""
    await asyncio.sleep(0.001)  # Simulate async work
    return DB("sqlite://")


def sync_db_dependency() -> DB:
    """Sync dependency that returns a DB instance."""
    return DB("sqlite://")


async def async_url_dependency() -> str:
    """Async dependency that returns a URL."""
    await asyncio.sleep(0.001)
    return "sqlite://"


def sync_config_dependency() -> Dict[str, str]:
    """Sync dependency that returns configuration."""
    return {"key": "value", "timeout": "30s"}


def get_db_annotated() -> Annotated[str, "db_test"]:
    """Dependency function with annotated return type."""
    return "sqlite://"


# Sample functions with various injection patterns
def sample_injected_function(
    a: Annotated[str, ArgsInjectable(...)],
    c: MyModel,
    b: str = ArgsInjectable("abc"),
    d: int = No42(44),
    e: str = ModelFieldInject(model=MyModelField),
    f: float = 3.14,
    g: bool = True,
    h: float = ModelFieldInject(model=MyModelField, field="f"),
) -> Tuple[str, str, MyModel, int, str, float, bool, float]:
    """Sample function with various injection types for testing."""
    return a, b, c, d, e, f, g, h


def sample_method_injection_function(
    x: Annotated[str, ArgsInjectable(...)],
    y: str = ModelFieldInject(model=MyModelMethod, field="get_value"),
    z: str = ModelFieldInject(model=MyModelMethod, field="other_method"),
) -> Tuple[str, str, str]:
    """Sample function with method injection for testing."""
    return x, y, z


# Utility functions for tests
def create_slow_async_dependency(name: str, delay: float = 0.1):
    """Factory function to create async dependencies with specific delays."""

    async def dependency() -> str:
        await asyncio.sleep(delay)
        return f"dependency_{name}"

    dependency.__name__ = f"slow_dep_{name}"
    return dependency


def create_tracked_dependency(name: str, execution_log: List[str], delay: float = 0.05):
    """Factory function to create dependencies that track execution order."""

    async def dependency() -> str:
        execution_log.append(f"{name}_start")
        await asyncio.sleep(delay)
        execution_log.append(f"{name}_end")
        return f"result_{name}"

    dependency.__name__ = f"tracked_dep_{name}"
    return dependency


# Pytest markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.async_test = pytest.mark.asyncio
pytest.mark.slow = pytest.mark.slow
pytest.mark.performance = pytest.mark.performance


# Test data collections
VALID_CONSTRAINT_TEST_DATA = [
    ("string", "foobar", {"min_length": 2, "max_length": 10}),
    ("string_pattern", "foobar", {"pattern": r"^[a-z]+$"}),
    ("number_int", 45, {"gt": 2, "lt": 100, "multiple_of": 5}),
    ("number_float", 10.2, {"gt": 2.7, "lt": 100.99, "multiple_of": 5.1}),
    ("datetime_basic", "22-12-2007", {}),
    ("datetime_short", "22-12-07", {}),
    ("uuid_valid", "3cd4d94e-61e9-4c90-bd39-9207a1fb7227", {}),
    ("enum_valid", MyEnum.VALID, {"baseenum": MyEnum}),
]

INVALID_CONSTRAINT_TEST_DATA = [
    ("string_too_long", "foobar", {"min_length": 2, "max_length": 3}),
    ("string_pattern_fail", "FooBar", {"pattern": r"^[a-z]+$"}),
    ("number_out_of_range", 45, {"gt": 2, "lt": 10}),
    ("number_not_multiple", 45, {"multiple_of": 2}),
    ("datetime_invalid", "2023-13-02", {}),
    ("uuid_invalid", "Not A UUID", {}),
    ("enum_wrong_type", SecondaryEnum.BAR, {"baseenum": MyEnum}),
]
