# ruff: noqa
# mypy: ignore-errors
"""
Enhanced HTTP Request Processing with ctxinject

This example demonstrates how to use ctxinject for building a robust HTTP request processing
system with dependency injection, similar to FastAPI but with more flexibility for custom
request handling patterns.

Key Features Demonstrated:
- HTTP request context extraction
- Authentication and authorization injection
- Database and cache service injection
- Request validation and transformation
- Error handling and logging
- Testing with dependency overrides
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import uuid4

import requests
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Annotated

from ctxinject.inject import inject_args
from ctxinject.model import ArgsInjectable, DependsInject, ModelFieldInject

# =============================================================================
# HTTP Request Models and Protocols
# =============================================================================


@runtime_checkable
class HTTPRequest(Protocol):
    """Protocol defining the interface for HTTP request objects."""

    method: str
    url: str
    headers: Dict[str, str]
    body: bytes

    def get_header(self, name: str) -> Optional[str]:
        """Get header value by name (case-insensitive)."""
        ...


class UserCreateRequest(BaseModel):
    """Pydantic model for user creation requests."""

    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., regex=r"^[^@]+@[^@]+\.[^@]+$")
    age: int = Field(..., ge=18, le=120)
    roles: List[str] = Field(default_factory=list)

    @field_validator("email")
    def validate_email_domain(cls, v):
        """Custom validation for email domain."""
        if not v.endswith((".com", ".org", ".net")):
            raise ValueError("Email must end with .com, .org, or .net")
        return v.lower()


class APIResponse(BaseModel):
    """Standard API response format."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str = ""
    request_id: str
    timestamp: datetime
    processing_time_ms: float


# =============================================================================
# Application Configuration and Services
# =============================================================================


class DatabaseConfig:
    """Database configuration with connection details."""

    # Type annotations required for ModelFieldInject
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int
    timeout: int

    def __init__(self):
        self.host = "localhost"
        self.port = 5432
        self.database = "app_db"
        self.username = "app_user"
        self.password = "secure_password"
        self.pool_size = 10
        self.timeout = 30

    @property
    def connection_string(self) -> str:
        """Generate database connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    def get_pool_config(self) -> Dict[str, Any]:
        """Get connection pool configuration."""
        return {
            "min_connections": 1,
            "max_connections": self.pool_size,
            "timeout": self.timeout,
        }


class AuthConfig:
    """Authentication and authorization configuration."""

    jwt_secret: str
    token_expiry_hours: int
    admin_roles: List[str]

    def __init__(self):
        self.jwt_secret = "your-super-secret-jwt-key"
        self.token_expiry_hours = 24
        self.admin_roles = ["admin", "superuser"]

    def is_admin_role(self, role: str) -> bool:
        """Check if role has admin privileges."""
        return role in self.admin_roles


# =============================================================================
# Service Layer Dependencies
# =============================================================================


async def get_database_service() -> "DatabaseService":
    """Create and initialize database service."""
    # Simulate async database connection setup
    await asyncio.sleep(0.01)
    return DatabaseService()


async def get_cache_service() -> "CacheService":
    """Create and initialize cache service."""
    await asyncio.sleep(0.005)
    return CacheService()


async def get_logger_service() -> "LoggerService":
    """Create and initialize logging service."""
    return LoggerService()


def get_request_id() -> str:
    """Generate unique request ID."""
    return str(uuid4())


def get_current_timestamp() -> datetime:
    """Get current timestamp."""
    return datetime.utcnow()


class DatabaseService:
    """Mock database service for demonstration."""

    def __init__(self):
        self.connected = True
        self.users_db = {}  # Mock user storage

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user record."""
        await asyncio.sleep(0.02)  # Simulate DB operation
        user_id = len(self.users_db) + 1
        user_record = {
            "id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            **user_data,
        }
        self.users_db[user_id] = user_record
        return user_record

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        await asyncio.sleep(0.01)
        return self.users_db.get(user_id)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        await asyncio.sleep(0.015)
        for user in self.users_db.values():
            if user.get("email") == email:
                return user
        return None


class CacheService:
    """Mock cache service for demonstration."""

    def __init__(self):
        self.cache = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        await asyncio.sleep(0.001)
        return self.cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        await asyncio.sleep(0.001)
        self.cache[key] = value
        return True

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        await asyncio.sleep(0.001)
        return self.cache.pop(key, None) is not None


class LoggerService:
    """Mock logging service for demonstration."""

    async def log_request(
        self, request_id: str, method: str, url: str, user_id: Optional[int] = None
    ) -> None:
        """Log HTTP request details."""
        print(f"[{request_id}] {method} {url} - User: {user_id}")

    async def log_response(
        self, request_id: str, status_code: int, processing_time: float
    ) -> None:
        """Log HTTP response details."""
        print(f"[{request_id}] Response: {status_code} - Time: {processing_time:.2f}ms")

    async def log_error(self, request_id: str, error: str) -> None:
        """Log error details."""
        print(f"[{request_id}] ERROR: {error}")


# =============================================================================
# Custom Injectable for HTTP Request Context
# =============================================================================


class FromRequest(ModelFieldInject):
    """Custom injectable that extracts values from HTTP request objects.

    This demonstrates how to create domain-specific injectable types
    that work with your application's request/response cycle.
    """

    def __init__(
        self,
        field: Optional[str] = None,
        validator: Optional[Any] = None,
        **meta: Any,
    ):
        super().__init__(HTTPRequest, field, validator, **meta)


# =============================================================================
# Authentication and Authorization Dependencies
# =============================================================================


async def authenticate_user(
    # Extract auth token from request headers
    auth_header: Annotated[Optional[str], FromRequest("headers")],
    cache: Annotated["CacheService", DependsInject(get_cache_service)],
    request_id: Annotated[str, DependsInject(get_request_id)],
) -> Optional[Dict[str, Any]]:
    """Authenticate user from request headers."""
    if not auth_header:
        return None

    # Extract Bearer token
    if not auth_header.get("Authorization", "").startswith("Bearer "):
        return None

    token = auth_header["Authorization"][7:]  # Remove "Bearer " prefix

    # Check cache for user session
    user_data = await cache.get(f"session:{token}")
    if user_data:
        return user_data

    # Mock JWT validation (in real app, use proper JWT library)
    if token == "valid_admin_token":
        user_data = {
            "user_id": 1,
            "email": "admin@example.com",
            "roles": ["admin"],
            "authenticated_at": datetime.utcnow().isoformat(),
        }
        await cache.set(f"session:{token}", user_data, ttl=3600)
        return user_data

    return None


def validate_admin_access(
    user: Annotated[Optional[Dict[str, Any]], DependsInject(authenticate_user)],
    auth_config: Annotated[AuthConfig, ArgsInjectable(AuthConfig())],
    request_id: Annotated[str, DependsInject(get_request_id)],
) -> Dict[str, Any]:
    """Validate that user has admin access."""
    if not user:
        raise ValueError(f"[{request_id}] Authentication required")

    user_roles = user.get("roles", [])
    has_admin = any(auth_config.is_admin_role(role) for role in user_roles)

    if not has_admin:
        raise ValueError(f"[{request_id}] Admin access required")

    return user


# =============================================================================
# HTTP Request Handlers with Dependency Injection
# =============================================================================


async def create_user_handler(
    # Request context injection
    url: Annotated[str, FromRequest()],
    method: Annotated[str, FromRequest()],
    request_body: Annotated[UserCreateRequest, FromRequest("body")],
    headers: Annotated[Dict[str, str], FromRequest()],
    # Service dependencies
    db: Annotated[DatabaseService, DependsInject(get_database_service)],
    cache: Annotated[CacheService, DependsInject(get_cache_service)],
    logger: Annotated[LoggerService, DependsInject(get_logger_service)],
    # Configuration injection
    db_config: Annotated[str, ModelFieldInject(DatabaseConfig, "connection_string")],
    # Authentication (optional for this endpoint)
    current_user: Annotated[Optional[Dict[str, Any]], DependsInject(authenticate_user)],
    # Request metadata
    request_id: Annotated[str, DependsInject(get_request_id)],
    timestamp: Annotated[datetime, DependsInject(get_current_timestamp)],
) -> APIResponse:
    """Create a new user with full dependency injection."""

    start_time = time.time()

    try:
        # Log incoming request
        user_id = current_user.get("user_id") if current_user else None
        await logger.log_request(request_id, method, url, user_id)

        # Check if user already exists
        existing_user = await db.get_user_by_email(request_body.email)
        if existing_user:
            raise ValueError(f"User with email {request_body.email} already exists")

        # Create new user
        user_data = request_body.dict()
        new_user = await db.create_user(user_data)

        # Cache user data
        await cache.set(f"user:{new_user['id']}", new_user, ttl=1800)

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000

        # Log successful response
        await logger.log_response(request_id, 201, processing_time)

        return APIResponse(
            success=True,
            data={"user": new_user},
            message="User created successfully",
            request_id=request_id,
            timestamp=timestamp,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        # Log error
        await logger.log_error(request_id, str(e))

        processing_time = (time.time() - start_time) * 1000

        return APIResponse(
            success=False,
            message=str(e),
            request_id=request_id,
            timestamp=timestamp,
            processing_time_ms=processing_time,
        )


async def get_user_handler(
    # Request context
    user_id: Annotated[int, ArgsInjectable(...)],  # From URL path
    # Service dependencies
    db: Annotated[DatabaseService, DependsInject(get_database_service)],
    cache: Annotated[CacheService, DependsInject(get_cache_service)],
    logger: Annotated[LoggerService, DependsInject(get_logger_service)],
    # Authentication required
    current_user: Annotated[Dict[str, Any], DependsInject(authenticate_user)],
    # Request metadata
    request_id: Annotated[str, DependsInject(get_request_id)],
    timestamp: Annotated[datetime, DependsInject(get_current_timestamp)],
) -> APIResponse:
    """Get user by ID with authentication required."""

    start_time = time.time()

    try:
        # Check cache first
        cached_user = await cache.get(f"user:{user_id}")
        if cached_user:
            processing_time = (time.time() - start_time) * 1000

            return APIResponse(
                success=True,
                data={"user": cached_user, "from_cache": True},
                message="User retrieved from cache",
                request_id=request_id,
                timestamp=timestamp,
                processing_time_ms=processing_time,
            )

        # Get from database
        user = await db.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Update cache
        await cache.set(f"user:{user_id}", user, ttl=1800)

        processing_time = (time.time() - start_time) * 1000

        return APIResponse(
            success=True,
            data={"user": user, "from_cache": False},
            message="User retrieved successfully",
            request_id=request_id,
            timestamp=timestamp,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        await logger.log_error(request_id, str(e))
        processing_time = (time.time() - start_time) * 1000

        return APIResponse(
            success=False,
            message=str(e),
            request_id=request_id,
            timestamp=timestamp,
            processing_time_ms=processing_time,
        )


async def admin_dashboard_handler(
    # Admin authentication required
    admin_user: Annotated[Dict[str, Any], DependsInject(validate_admin_access)],
    # Service dependencies
    db: Annotated[DatabaseService, DependsInject(get_database_service)],
    logger: Annotated[LoggerService, DependsInject(get_logger_service)],
    # Configuration
    auth_config: Annotated[List[str], ModelFieldInject(AuthConfig, "admin_roles")],
    # Request metadata
    request_id: Annotated[str, DependsInject(get_request_id)],
    timestamp: Annotated[datetime, DependsInject(get_current_timestamp)],
) -> APIResponse:
    """Admin-only dashboard with role-based access control."""

    start_time = time.time()

    try:
        # Get dashboard data (mock)
        dashboard_data = {
            "total_users": len(db.users_db),
            "admin_user": admin_user["email"],
            "admin_roles": auth_config,
            "last_login": admin_user.get("authenticated_at"),
        }

        processing_time = (time.time() - start_time) * 1000

        return APIResponse(
            success=True,
            data={"dashboard": dashboard_data},
            message="Dashboard data retrieved",
            request_id=request_id,
            timestamp=timestamp,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        await logger.log_error(request_id, str(e))
        processing_time = (time.time() - start_time) * 1000

        return APIResponse(
            success=False,
            message=str(e),
            request_id=request_id,
            timestamp=timestamp,
            processing_time_ms=processing_time,
        )


# =============================================================================
# Demo Application and Testing
# =============================================================================


async def simulate_http_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    body_data: Optional[Dict[str, Any]] = None,
) -> HTTPRequest:
    """Simulate an HTTP request object."""

    # Create actual request using requests library
    if body_data:
        req = requests.Request(method=method, url=url, headers=headers, json=body_data)
    else:
        req = requests.Request(method=method, url=url, headers=headers)

    prepared = req.prepare()

    # Return prepared request (implements HTTPRequest protocol)
    return prepared


async def demo_user_creation():
    """Demonstrate user creation with dependency injection."""
    print("🚀 Demo: Creating User with Dependency Injection")
    print("=" * 60)

    # Simulate HTTP POST request
    request_data = {
        "name": "João Silva",
        "email": "joao@example.com",
        "age": 28,
        "roles": ["user"],
    }

    headers = {"Content-Type": "application/json", "User-Agent": "Demo-Client/1.0"}

    http_request = await simulate_http_request(
        "POST", "https://api.example.com/users", headers, request_data
    )

    # Create injection context
    context = {
        HTTPRequest: http_request,
        DatabaseConfig: DatabaseConfig(),
        AuthConfig: AuthConfig(),
    }

    # Inject dependencies and execute handler
    injected_handler = await inject_args(create_user_handler, context)
    response = await injected_handler()

    print(f"✅ Response: {response.dict()}")
    print(f"⏱️  Processing time: {response.processing_time_ms:.2f}ms")
    print(f"🆔 Request ID: {response.request_id}")


async def demo_authenticated_request():
    """Demonstrate authenticated request with admin access."""
    print("\n🔐 Demo: Authenticated Admin Request")
    print("=" * 60)

    headers = {
        "Authorization": "Bearer valid_admin_token",
        "Content-Type": "application/json",
    }

    http_request = await simulate_http_request(
        "GET", "https://api.example.com/admin/dashboard", headers
    )

    context = {HTTPRequest: http_request, AuthConfig: AuthConfig()}

    # Inject dependencies and execute admin handler
    injected_handler = await inject_args(admin_dashboard_handler, context)
    response = await injected_handler()

    print(f"✅ Admin Response: {response.dict()}")


async def demo_dependency_override_testing():
    """Demonstrate testing with dependency overrides."""
    print("\n🧪 Demo: Testing with Dependency Overrides")
    print("=" * 60)

    # Mock services for testing
    class MockDatabaseService:
        def __init__(self):
            self.users_db = {
                1: {"id": 1, "email": "test@example.com", "name": "Test User"}
            }

        async def get_user(self, user_id: int):
            return self.users_db.get(user_id)

    class MockCacheService:
        async def get(self, key: str):
            return None  # Always miss cache for testing

    # Override functions
    def get_mock_database():
        return MockDatabaseService()

    def get_mock_cache():
        return MockCacheService()

    # Define overrides
    overrides = {
        get_database_service: get_mock_database,
        get_cache_service: get_mock_cache,
    }

    # Create context
    headers = {"Authorization": "Bearer valid_admin_token"}
    http_request = await simulate_http_request(
        "GET", "https://api.example.com/users/1", headers
    )

    context = {HTTPRequest: http_request, "user_id": 1}

    # Test with overrides
    injected_handler = await inject_args(get_user_handler, context, overrides=overrides)
    response = await injected_handler()

    print(f"🧪 Test Response: {response.dict()}")
    print("✅ Successfully used mock services in test")


async def main():
    """Run all HTTP processing demos."""
    print("🌐 Advanced HTTP Request Processing with ctxinject")
    print("=" * 80)
    print("Demonstrating professional-grade dependency injection patterns")
    print("for HTTP request handling, authentication, and service orchestration.\n")

    await demo_user_creation()
    await demo_authenticated_request()
    await demo_dependency_override_testing()

    print("\n" + "=" * 80)
    print("✨ All HTTP processing demos completed successfully!")
    print("This demonstrates how ctxinject enables clean, testable,")
    print("and maintainable HTTP request processing architectures.")


if __name__ == "__main__":
    asyncio.run(main())
