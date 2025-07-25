# ruff: noqa
# mypy: ignore-errors
"""
Complete usage examples for ctxinject.validate module.

This demonstrates automatic type conversion and validation for ModelFieldInject.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

from typing_extensions import Annotated

# Add the parent directory to Python path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ctxinject.inject import inject_args
from ctxinject.model import ModelFieldInject
from ctxinject.validate import inject_validation

try:
    from pydantic import BaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None


# =============================================================================
# 1. Basic Type Conversion - String to Numeric Types
# =============================================================================


class DatabaseConfig:
    """Configuration with string values that need conversion."""

    # All values stored as strings (common in config files)
    host: str
    port_str: str
    timeout_str: str
    ssl_enabled_str: str
    max_connections_str: str

    def __init__(self):
        self.host = "localhost"
        self.port_str = "5432"
        self.timeout_str = "30"
        self.ssl_enabled_str = "true"
        self.max_connections_str = "100"


def connect_database(
    host: Annotated[
        str, ModelFieldInject(DatabaseConfig, "host")
    ],  # No conversion needed
    port: Annotated[int, ModelFieldInject(DatabaseConfig, "port_str")],  # str -> int
    timeout: Annotated[
        int, ModelFieldInject(DatabaseConfig, "timeout_str")
    ],  # str -> int
    ssl_enabled: Annotated[
        bool, ModelFieldInject(DatabaseConfig, "ssl_enabled_str")
    ],  # str -> bool
    max_conn: Annotated[
        int, ModelFieldInject(DatabaseConfig, "max_connections_str")
    ],  # str -> int
) -> dict:
    """Connect to database with automatic type conversion."""
    return {
        "host": host,
        "port": port,
        "timeout": timeout,
        "ssl_enabled": ssl_enabled,
        "max_connections": max_conn,
        "port_type": type(port).__name__,
        "ssl_type": type(ssl_enabled).__name__,
    }


# =============================================================================
# 2. Advanced Type Conversion - UUIDs, Dates, etc.
# =============================================================================


class UserConfig:
    """Configuration with complex types as strings."""

    user_id_str: str
    created_at_str: str
    updated_at_str: str

    def __init__(self):
        self.user_id_str = "123e4567-e89b-12d3-a456-426614174000"
        self.created_at_str = "2023-12-25T10:30:00"
        self.updated_at_str = "2023-12-25T15:45:30"


def process_user_data(
    user_id: Annotated[
        UUID, ModelFieldInject(UserConfig, "user_id_str")
    ],  # str -> UUID
    created_at: Annotated[
        datetime, ModelFieldInject(UserConfig, "created_at_str")
    ],  # str -> datetime
    updated_at: Annotated[
        datetime, ModelFieldInject(UserConfig, "updated_at_str")
    ],  # str -> datetime
) -> dict:
    """Process user data with automatic type conversion."""
    return {
        "user_id": str(user_id),
        "user_id_type": type(user_id).__name__,
        "created_at": created_at.isoformat(),
        "created_at_type": type(created_at).__name__,
        "time_diff": (updated_at - created_at).total_seconds(),
    }


# =============================================================================
# 3. Pydantic Model Validation (if available)
# =============================================================================

if PYDANTIC_AVAILABLE:

    class UserModel(BaseModel):
        """Pydantic model for user data."""

        name: str
        age: int
        email: str
        is_active: bool = True

    class ProductModel(BaseModel):
        """Pydantic model for product data."""

        id: int
        name: str
        price: float
        tags: list[str] = []

    class ApiConfig:
        """Configuration with JSON strings."""

        user_json: str
        product_json: str

        def __init__(self):
            self.user_json = (
                '{"name": "Alice", "age": 30, "email": "alice@example.com"}'
            )
            self.product_json = '{"id": 123, "name": "Widget", "price": 29.99, "tags": ["electronics", "gadget"]}'

    def process_api_data(
        user: Annotated[
            UserModel, ModelFieldInject(ApiConfig, "user_json")
        ],  # JSON -> UserModel
        product: Annotated[
            ProductModel, ModelFieldInject(ApiConfig, "product_json")
        ],  # JSON -> ProductModel
    ) -> dict:
        """Process API data with automatic JSON parsing."""
        return {
            "user_name": user.name,
            "user_age": user.age,
            "user_email": user.email,
            "product_name": product.name,
            "product_price": product.price,
            "product_tags": product.tags,
            "user_model_type": type(user).__name__,
            "product_model_type": type(product).__name__,
        }


# =============================================================================
# 4. Error Handling Examples
# =============================================================================


class InvalidConfig:
    """Configuration that will cause validation errors."""

    # Missing type annotation - will cause error
    field_without_annotation = "value"

    def __init__(self):
        pass


def function_with_validation_errors(
    # This will cause an error - can't determine field type
    param1: Annotated[int, ModelFieldInject(InvalidConfig, "field_without_annotation")],
    # This will also cause an error - field doesn't exist
    param2: Annotated[str, ModelFieldInject(DatabaseConfig, "nonexistent_field")],
) -> str:
    """Function that will have validation setup errors."""
    return f"{param1}, {param2}"


# =============================================================================
# 5. Demo Functions
# =============================================================================


async def demo_basic_conversion():
    """Demonstrate basic type conversion."""
    print("=== Basic Type Conversion Demo ===")

    # Set up automatic validation
    errors = inject_validation(connect_database)
    if errors:
        print(f"Validation setup errors: {errors}")
        return
    else:
        print("✅ Automatic type conversion configured!")

    # Test the conversion
    config = DatabaseConfig()
    context = {DatabaseConfig: config}

    print("Original config values (all strings):")
    print(f"  port_str: '{config.port_str}' (type: {type(config.port_str).__name__})")
    print(
        f"  ssl_enabled_str: '{config.ssl_enabled_str}' (type: {type(config.ssl_enabled_str).__name__})"
    )

    injected = await inject_args(connect_database, context)
    result = injected()

    print("\nAfter automatic conversion:")
    print(f"  port: {result['port']} (type: {result['port_type']})")
    print(f"  ssl_enabled: {result['ssl_enabled']} (type: {result['ssl_type']})")
    print(f"  Full result: {result}")


async def demo_advanced_conversion():
    """Demonstrate advanced type conversion."""
    print("\n=== Advanced Type Conversion Demo ===")

    errors = inject_validation(process_user_data)
    if errors:
        print(f"Validation setup errors: {errors}")
        return
    else:
        print("✅ Advanced type conversion configured!")

    config = UserConfig()
    context = {UserConfig: config}

    print("Original config values:")
    print(f"  user_id_str: '{config.user_id_str}' (string)")
    print(f"  created_at_str: '{config.created_at_str}' (string)")

    injected = await inject_args(process_user_data, context)
    result = injected()

    print("\nAfter conversion:")
    print(f"  user_id: {result['user_id']} (type: {result['user_id_type']})")
    print(f"  created_at: {result['created_at']} (type: {result['created_at_type']})")
    print(f"  time_diff: {result['time_diff']} seconds")


async def demo_pydantic_validation():
    """Demonstrate Pydantic model validation."""
    if not PYDANTIC_AVAILABLE:
        print("\n=== Pydantic Demo ===")
        print("❌ Pydantic not available, skipping demo")
        return

    print("\n=== Pydantic Model Validation Demo ===")

    errors = inject_validation(process_api_data)
    if errors:
        print(f"Validation setup errors: {errors}")
        return
    else:
        print("✅ Pydantic JSON parsing configured!")

    config = ApiConfig()
    context = {ApiConfig: config}

    print("Original JSON strings:")
    print(f"  user_json: {config.user_json}")
    print(f"  product_json: {config.product_json}")

    injected = await inject_args(process_api_data, context)
    result = injected()

    print("\nAfter JSON parsing:")
    print(f"  user_name: {result['user_name']} (from {result['user_model_type']})")
    print(
        f"  product_name: {result['product_name']} (from {result['product_model_type']})"
    )
    print(f"  product_tags: {result['product_tags']}")


def demo_validation_errors():
    """Demonstrate validation setup errors."""
    print("\n=== Validation Error Handling Demo ===")

    errors = inject_validation(function_with_validation_errors)

    if errors:
        print("❌ Expected validation setup errors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    else:
        print("✅ No errors (unexpected)")


# =============================================================================
# Main Demo
# =============================================================================


async def main():
    """Run all validation demos."""
    print("CTXInject Validation System - Complete Demo")
    print("=" * 60)

    await demo_basic_conversion()
    await demo_advanced_conversion()
    await demo_pydantic_validation()
    demo_validation_errors()

    print("\n" + "=" * 60)
    print("🎉 All validation demos completed!")

    if PYDANTIC_AVAILABLE:
        print("✅ Pydantic integration available")
    else:
        print("📦 Install Pydantic for additional JSON validation features")


if __name__ == "__main__":
    asyncio.run(main())
