"""
Complete usage examples for ctxinject library.

This file demonstrates all the main user APIs with practical examples.
"""

import asyncio
import os
import sys
import time
from functools import partial
from typing import Any, Dict, List

from typing_extensions import Annotated

# Add the parent directory to Python path to import local ctxinject
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ctxinject.inject import get_mapped_ctx, inject_args, resolve_mapped_ctx
from ctxinject.model import ArgsInjectable, DependsInject, ModelFieldInject
from ctxinject.sigcheck import func_signature_check

# =============================================================================
# 1. ArgsInjectable - Basic argument injection with defaults and validation
# =============================================================================


def validate_positive(value: int, **kwargs: Any) -> int:
    """Example validator that ensures value is positive."""
    if value < 0:
        raise ValueError(f"Value {value} must be positive")
    return value


def validate_non_empty(value: str, **kwargs: Any) -> str:
    """Example validator that ensures string is not empty."""
    if not value.strip():
        raise ValueError("String cannot be empty")
    return value.strip()


# Example function using ArgsInjectable
def process_order(
    # Required parameter (no default)
    customer_id: Annotated[str, ArgsInjectable(...)],
    # Optional with default value
    quantity: Annotated[int, ArgsInjectable(1)],
    # With validation
    price: Annotated[float, ArgsInjectable(0.0, validate_positive)],
    # String with validation
    product_name: Annotated[str, ArgsInjectable("Default Product", validate_non_empty)],
) -> Dict[Any, Any]:
    """Process an order with injected dependencies."""
    total = quantity * price
    return {
        "customer": customer_id,
        "product": product_name,
        "quantity": quantity,
        "price": price,
        "total": total,
    }


# =============================================================================
# 2. ModelFieldInject - Extract values from model instances
# =============================================================================


class DatabaseConfig:
    """Example configuration model."""

    # Type annotations are required for ModelFieldInject to work
    host: str
    port: int
    database: str
    ssl_enabled: bool

    def __init__(self) -> None:
        self.host = "localhost"
        self.port = 5432
        self.database = "myapp"
        self.ssl_enabled = True

    @property
    def connection_string(self) -> str:
        """Property that will be called by ModelFieldInject."""
        protocol = "postgresql+ssl" if self.ssl_enabled else "postgresql"
        return f"{protocol}://{self.host}:{self.port}/{self.database}"

    def get_timeout(self) -> int:
        """Method that will be called by ModelFieldInject."""
        return 30


class UserService:
    """Example service model."""

    current_user_id: str
    is_admin: bool

    def __init__(self, user_id: str = "admin"):
        self.current_user_id = user_id
        self.is_admin = user_id == "admin"

    def get_permissions(self) -> List[str]:
        """Method returning user permissions."""
        return ["read", "write"] if self.is_admin else ["read"]


# Example function using ModelFieldInject
def connect_database(
    # Extract field by name
    host: Annotated[str, ModelFieldInject(DatabaseConfig, "host")],
    port: Annotated[int, ModelFieldInject(DatabaseConfig, "port")],
    # Extract using property (will be called)
    conn_str: Annotated[str, ModelFieldInject(DatabaseConfig, "connection_string")],
    # Extract using method (will be called)
    timeout: Annotated[int, ModelFieldInject(DatabaseConfig, "get_timeout")],
    # Field name defaults to parameter name if not specified
    database: Annotated[str, ModelFieldInject(DatabaseConfig, "database")],
) -> str:
    """Connect to database using configuration from model."""
    return f"Connected to {conn_str} (timeout: {timeout}s, host: {host}, port: {port}, db: {database})"


# =============================================================================
# 3. DependsInject - Function dependencies with recursive resolution
# =============================================================================


# Simple dependency functions
def get_current_timestamp() -> float:
    """Simple dependency returning current time."""
    return time.time()


async def get_database_connection() -> str:
    """Async dependency simulating database connection."""
    await asyncio.sleep(0.1)  # Simulate async work
    return "db_connection_123"


def get_api_config() -> Dict[Any, Any]:
    """Dependency returning configuration."""
    return {
        "api_key": "secret_key_123",
        "base_url": "https://api.example.com",
        "timeout": 30,
    }


# Dependencies with their own dependencies
def create_auth_header(config: Dict[Any, Any] = DependsInject(get_api_config)) -> str:  # type: ignore
    """Dependency that depends on another dependency."""
    return f"Bearer {config['api_key']}"


async def create_http_client(
    config: Dict[Any, Any] = DependsInject(get_api_config),  # type: ignore
    auth_header: str = DependsInject(create_auth_header),  # type: ignore
) -> Dict[Any, Any]:
    """Async dependency with multiple sub-dependencies."""
    await asyncio.sleep(0.05)  # Simulate async work
    return {
        "base_url": config["base_url"],
        "headers": {"Authorization": auth_header},
        "timeout": config["timeout"],
    }


# Example function using DependsInject
def make_api_request(
    endpoint: str,
    # Simple dependency
    timestamp: Annotated[float, DependsInject(get_current_timestamp)],
    # Async dependency
    db_conn: Annotated[str, DependsInject(get_database_connection)],
    # Dependency with sub-dependencies
    http_client: Annotated[Dict[Any, Any], DependsInject(create_http_client)],
    # Simple lambda dependency (no args, known return type)
    request_id: Annotated[str, DependsInject(lambda: f"req_{int(time.time())}")],
) -> Dict[Any, Any]:
    """Make API request with injected dependencies."""
    return {
        "endpoint": endpoint,
        "request_id": request_id,
        "timestamp": timestamp,
        "db_connection": db_conn,
        "client_config": http_client,
    }


# =============================================================================
# 4. inject_args - Main injection function
# =============================================================================


async def example_inject_args() -> None:
    """Demonstrate inject_args usage with different scenarios."""

    print("=== ArgsInjectable Examples ===")

    # Context for ArgsInjectable
    order_context: Dict[Any, Any] = {
        "customer_id": "CUST123",
        "quantity": 5,
        "price": 29.99,
        "product_name": "Premium Widget",
    }

    # Inject by name
    injected_order: partial[Any] = await inject_args(process_order, order_context)
    result = injected_order()
    print(f"Order result: {result}")

    # Inject by type
    type_context: Dict[Any, Any] = {
        str: "CUST456",  # Will be used for customer_id
        int: 3,  # Will be used for quantity
        float: 19.99,  # Will be used for price
        # product_name will use default
    }

    injected_order_by_type: partial[Any] = await inject_args(
        process_order, type_context
    )
    result_by_type = injected_order_by_type()
    print(f"Order by type: {result_by_type}")

    print("\n=== ModelFieldInject Examples ===")

    # Context for ModelFieldInject
    db_config = DatabaseConfig()
    model_context: Dict[Any, Any] = {DatabaseConfig: db_config}

    injected_db: partial[Any] = await inject_args(connect_database, model_context)
    db_result = injected_db()
    print(f"Database connection: {db_result}")

    print("\n=== DependsInject Examples ===")

    # Context for DependsInject (can be empty - dependencies auto-resolve)
    depends_context: Dict[Any, Any] = {}

    injected_api = await inject_args(make_api_request, depends_context)
    api_result = injected_api("/users/profile")
    print(f"API request: {api_result}")

    print("\n=== Mixed Dependencies ===")

    # Function combining all injection types
    def complex_operation(
        # ArgsInjectable
        operation_id: Annotated[str, ArgsInjectable(...)],
        retry_count: Annotated[int, ArgsInjectable(3)],
        # ModelFieldInject
        user_perms: Annotated[
            List[str], ModelFieldInject(UserService, "get_permissions")
        ],
        # DependsInject
        timestamp: Annotated[float, DependsInject(get_current_timestamp)],
        db_conn: Annotated[str, DependsInject(get_database_connection)],
    ) -> Dict[Any, Any]:
        return {
            "operation_id": operation_id,
            "retry_count": retry_count,
            "user_permissions": user_perms,
            "timestamp": timestamp,
            "database": db_conn,
        }

    # Mixed context
    user_service = UserService("admin")
    mixed_context: Dict[Any, Any] = {
        "operation_id": "OP789",
        "retry_count": 5,
        UserService: user_service,
    }

    injected_complex = await inject_args(complex_operation, mixed_context)
    complex_result = injected_complex()
    print(f"Complex operation: {complex_result}")


# =============================================================================
# 5. get_mapped_ctx and resolve_mapped_ctx - Advanced usage
# =============================================================================


async def example_advanced_resolution() -> None:
    """Demonstrate advanced resolution techniques."""

    print("\n=== Advanced Resolution Examples ===")

    # Get mapped context without resolving
    context: Dict[Any, Any] = {"customer_id": "CUST999", "quantity": 10, float: 49.99}

    mapped = get_mapped_ctx(process_order, context, allow_incomplete=True)
    print(f"Mapped resolvers: {list(mapped.keys())}")

    # Resolve manually
    resolved = await resolve_mapped_ctx(context, mapped)
    print(f"Resolved values: {resolved}")

    # Use resolved values
    result = process_order(**resolved)
    print(f"Manual resolution result: {result}")

    # Demonstrate incomplete resolution
    incomplete_context: Dict[Any, Any] = {
        "customer_id": "CUST000"
    }  # Missing other params

    try:
        # This will fail with allow_incomplete=False
        await inject_args(process_order, incomplete_context, allow_incomplete=False)
    except Exception as e:
        print(f"Expected error with incomplete context: {e}")

    # This will succeed with allow_incomplete=True
    partial_injected = await inject_args(
        func=process_order, context=incomplete_context, allow_incomplete=True
    )
    # Call with remaining required parameters
    partial_result = partial_injected(quantity=2, price=15.50)
    print(f"Partial injection result: {partial_result}")


# =============================================================================
# 6. func_signature_check - Validation
# =============================================================================


def example_signature_validation() -> None:
    """Demonstrate function signature validation."""

    print("\n=== Signature Validation Examples ===")

    # Valid function
    def valid_func(
        name: Annotated[str, ArgsInjectable(...)],
        count: Annotated[int, ArgsInjectable(42)],
    ) -> str:
        return f"{name}: {count}"

    errors = func_signature_check(valid_func)
    print(f"Valid function errors: {errors}")  # Should be empty

    # Invalid function - missing type annotations
    def invalid_func(untyped_param, count: int = ArgsInjectable(1)) -> str:  # type: ignore
        return f"test: {count}"

    errors = func_signature_check(invalid_func)
    print(f"Invalid function errors: {errors}")

    # Function with model types
    def model_func(
        config: DatabaseConfig,  # Valid because DatabaseConfig in modeltype
        timeout: Annotated[int, ModelFieldInject(DatabaseConfig, "get_timeout")],
    ) -> str:
        return "test"

    errors = func_signature_check(model_func, modeltype=[DatabaseConfig])
    print(f"Model function errors: {errors}")

    # Function with dependency issues
    def bad_deps_func(
        value: Annotated[
            str, DependsInject(lambda x: x)
        ],  # Lambda with args, no return type
    ) -> str:
        return value

    errors = func_signature_check(bad_deps_func)
    print(f"Bad dependencies errors: {errors}")


# =============================================================================
# Main example runner
# =============================================================================


async def main() -> None:
    """Run all examples."""
    print("CTXInject Library - Complete Usage Examples")
    print("=" * 50)

    await example_inject_args()
    await example_advanced_resolution()
    example_signature_validation()

    print("\n" + "=" * 50)
    print("All examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
