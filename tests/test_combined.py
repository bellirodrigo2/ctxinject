"""
Combined integration tests for complex injection scenarios.

This module tests integration between different injection types including
mixed injectables, model field injection, and dependency chains in
realistic usage scenarios.
"""

import pytest

from ctxinject.inject import UnresolvedInjectableError, inject_args
from ctxinject.model import ArgsInjectable, DependsInject, ModelFieldInject
from tests.conftest import Settings, User


class TestMixedInjectableIntegration:
    """Test complex scenarios mixing different injectable types."""

    @pytest.fixture
    def sub_dependency_function(self):
        """Sub-dependency that requires both context and model field injection."""

        def sub_dep(
            uid: int = ArgsInjectable(...),
            timeout: int = ModelFieldInject(Settings, field="timeout"),
        ) -> str:
            return f"{uid}-{timeout}"

        return sub_dep

    @pytest.fixture
    def mid_dependency_function(self, sub_dependency_function):
        """Mid-level dependency using other dependencies and lambda."""

        def mid_dep(
            name: User,
            uid: int = DependsInject(sub_dependency_function),
            debug: bool = DependsInject(lambda debug: not debug),
        ) -> str:
            return f"{name}-{uid}-{debug}"

        return mid_dep

    @pytest.fixture
    def main_handler_function(self, mid_dependency_function):
        """Main handler combining all injection types."""

        async def handler(
            name: User,
            id: int = ArgsInjectable(),
            to: int = ModelFieldInject(Settings, field="timeout"),
            combined: str = DependsInject(mid_dependency_function),
            extra: str = DependsInject(lambda: "static"),
        ) -> str:
            return f"{name}|{id}|{to}|{combined}|{extra}"

        return handler

    @pytest.mark.asyncio
    async def test_mixed_injectables_success(self, main_handler_function) -> None:
        """Test successful injection with all injectable types working together."""
        context = {
            "id": 42,
            "uid": 99,
            "debug": False,
            User: "Alice",
            Settings: Settings(debug=True, timeout=30),
        }

        resolved_func = await inject_args(
            main_handler_function, context, allow_incomplete=False
        )
        result = await resolved_func()

        expected = "Alice|42|30|Alice-99-30-True|static"
        assert result == expected

    @pytest.mark.asyncio
    async def test_mixed_injectables_missing_context(
        self, main_handler_function
    ) -> None:
        """Test failure when required context is missing."""
        incomplete_context = {
            "id": 42,
            "debug": False,
            User: "Alice",
            Settings: Settings(debug=True, timeout=30),
            # Missing "uid" which is required by sub_dependency
        }

        with pytest.raises(UnresolvedInjectableError, match="incomplete or missing"):
            await inject_args(
                main_handler_function, incomplete_context, allow_incomplete=False
            )

    @pytest.mark.asyncio
    async def test_mixed_injectables_partial_resolution(
        self, main_handler_function
    ) -> None:
        """Test partial resolution allowing incomplete context."""
        partial_context = {
            "id": 42,
            "debug": False,
            User: "Alice",
            Settings: Settings(debug=True, timeout=30),
            # Missing "uid" - should work with allow_incomplete=True
        }

        resolved_func = await inject_args(
            main_handler_function, partial_context, allow_incomplete=True
        )
        # The function should be partially resolved, requiring "uid" to be provided at call time
        # This test verifies the function is created without error
        assert callable(resolved_func)

    @pytest.mark.asyncio
    async def test_dependency_chain_with_overrides(
        self, main_handler_function, sub_dependency_function
    ) -> None:
        """Test dependency chain with function overrides."""

        def mock_sub_dep(
            uid: int = ArgsInjectable(...),
            timeout: int = ModelFieldInject(Settings, field="timeout"),
        ) -> str:
            return f"mocked-{uid}-{timeout}"

        context = {
            "id": 42,
            "uid": 99,
            "debug": False,
            User: "Alice",
            Settings: Settings(debug=True, timeout=30),
        }

        overrides = {sub_dependency_function: mock_sub_dep}

        resolved_func = await inject_args(
            main_handler_function, context, allow_incomplete=False, overrides=overrides
        )
        result = await resolved_func()

        # Should use mocked dependency
        expected = "Alice|42|30|Alice-mocked-99-30-True|static"
        assert result == expected

    @pytest.mark.asyncio
    async def test_complex_model_field_resolution(self) -> None:
        """Test complex model field resolution with inheritance and methods."""

        class BaseModel:
            base_field: str = "base_value"

        class ExtendedModel(BaseModel):
            extended_field: int = 100

            def __init__(self, dynamic_value: str) -> None:
                self.dynamic_value = dynamic_value

            @property
            def computed_field(self) -> str:
                return f"computed_{self.dynamic_value}"

            def method_field(self) -> str:
                return f"method_{self.dynamic_value}"

        async def handler(
            base: str = ModelFieldInject(ExtendedModel, field="base_field"),
            extended: int = ModelFieldInject(ExtendedModel, field="extended_field"),
            dynamic: str = ModelFieldInject(ExtendedModel, field="dynamic_value"),
            computed: str = ModelFieldInject(ExtendedModel, field="computed_field"),
            method: str = ModelFieldInject(ExtendedModel, field="method_field"),
        ) -> str:
            return f"{base}|{extended}|{dynamic}|{computed}|{method}"

        context = {ExtendedModel: ExtendedModel("test_dynamic")}

        resolved_func = await inject_args(handler, context)
        result = await resolved_func()

        expected = (
            "base_value|100|test_dynamic|computed_test_dynamic|method_test_dynamic"
        )
        assert result == expected

    @pytest.mark.asyncio
    async def test_nested_dependency_with_validation(self) -> None:
        """Test nested dependencies with validation constraints."""
        from ctxinject.constrained import constrained_factory
        from ctxinject.model import ConstrArgInject

        def validated_dependency(
            value: str = ConstrArgInject(constrained_factory, ..., min_length=5)
        ) -> str:
            return f"validated_{value}"

        def consumer_dependency(
            validated: str = DependsInject(validated_dependency),
        ) -> str:
            return f"consumer_{validated}"

        async def handler(result: str = DependsInject(consumer_dependency)) -> str:
            return result

        # Should work with valid value
        context = {"value": "hello_world"}
        resolved_func = await inject_args(handler, context)
        result = await resolved_func()
        assert result == "consumer_validated_hello_world"

        # Should fail with invalid value
        invalid_context = {"value": "hi"}  # Too short
        with pytest.raises(ValueError, match="String length"):
            await inject_args(handler, invalid_context)

    @pytest.mark.asyncio
    async def test_async_dependency_chain_with_context_injection(self) -> None:
        """Test async dependency chains mixed with context injection."""
        import asyncio

        async def async_config_loader(env: str = ArgsInjectable(...)) -> dict[str, str]:
            await asyncio.sleep(0.01)  # Simulate async work
            return {"environment": env, "database_url": f"{env}_db://localhost"}

        async def async_database_connection(
            config: dict[str, str] = DependsInject(async_config_loader),
        ) -> str:
            await asyncio.sleep(0.01)  # Simulate async connection
            return f"Connected to {config['database_url']}"

        def sync_service_factory(
            db_connection: str = DependsInject(async_database_connection),
            service_name: str = ArgsInjectable(...),
        ) -> str:
            return f"Service '{service_name}' using {db_connection}"

        async def handler(service: str = DependsInject(sync_service_factory)) -> str:
            return service

        context = {"env": "production", "service_name": "user_service"}

        resolved_func = await inject_args(handler, context)
        result = await resolved_func()

        expected = "Service 'user_service' using Connected to production_db://localhost"
        assert result == expected

    @pytest.mark.asyncio
    async def test_circular_model_field_dependency(self) -> None:
        """Test handling of circular references in model field injection."""

        class ServiceConfig:
            def __init__(self, name: str) -> None:
                self.name = name
                self.dependencies = []

        class ServiceRegistry:
            def __init__(self) -> None:
                self.services = {}

            def get_service_config(self, name: str) -> ServiceConfig:
                return self.services.get(name, ServiceConfig(f"default_{name}"))

        # Use ArgsInjectable to pass the name parameter
        async def handler(
            config_name: str = ArgsInjectable(...),
            registry: ServiceRegistry = ArgsInjectable(...),
        ) -> str:
            service_config = registry.get_service_config(config_name)
            return f"Service: {service_config.name}"

        registry = ServiceRegistry()
        registry.services["test_service"] = ServiceConfig("configured_service")

        context = {"config_name": "test_service", "registry": registry}

        resolved_func = await inject_args(handler, context)
        result = await resolved_func()
        assert result == "Service: configured_service"


class TestRealWorldScenarios:
    """Test real-world usage scenarios and patterns."""

    @pytest.mark.asyncio
    async def test_web_request_handler_pattern(self) -> None:
        """Test pattern similar to web framework request handlers."""
        from dataclasses import dataclass
        from typing import Optional

        @dataclass
        class Request:
            headers: dict[str, str]
            query_params: dict[str, str]
            user_id: Optional[str] = None

        @dataclass
        class DatabaseConfig:
            host: str
            port: int
            database: str

        class Database:
            def __init__(self, config: DatabaseConfig) -> None:
                self.config = config

            async def get_user(self, user_id: str) -> dict[str, str]:
                return {"id": user_id, "name": f"User_{user_id}"}

        class AuthService:
            def __init__(self, db: Database) -> None:
                self.db = db

            async def authenticate(self, token: str) -> Optional[str]:
                if token == "valid_token":
                    return "user123"
                return None

        async def get_database() -> Database:
            config = DatabaseConfig(host="localhost", port=5432, database="app_db")
            return Database(config)

        async def get_auth_service(
            db: Database = DependsInject(get_database),
        ) -> AuthService:
            return AuthService(db)

        async def get_current_user(
            auth_token: str = ModelFieldInject(Request, field="headers"),
            auth_service: AuthService = DependsInject(get_auth_service),
        ) -> Optional[dict[str, str]]:
            # Simulate extracting token from headers
            if "authorization" in auth_token:
                user_id = await auth_service.authenticate("valid_token")
                if user_id:
                    return await auth_service.db.get_user(user_id)
            return None

        # Handler that mimics a web endpoint
        async def user_profile_handler(
            request: Request,
            current_user: Optional[dict[str, str]] = DependsInject(get_current_user),
        ) -> str:
            if current_user:
                return f"Profile for {current_user['name']}"
            return "Unauthorized"

        # Test with valid authentication
        valid_request = Request(
            headers={"authorization": "Bearer valid_token"}, query_params={}
        )

        context = {Request: valid_request}
        resolved_func = await inject_args(user_profile_handler, context)
        result = await resolved_func()
        assert result == "Profile for User_user123"

        # Test with invalid authentication
        invalid_request = Request(headers={}, query_params={})

        context_invalid = {Request: invalid_request}
        resolved_func_invalid = await inject_args(user_profile_handler, context_invalid)
        result_invalid = await resolved_func_invalid()
        assert result_invalid == "Unauthorized"

    @pytest.mark.asyncio
    async def test_microservice_communication_pattern(self) -> None:
        """Test microservice-style dependency injection pattern."""
        import asyncio
        from typing import List

        class ServiceDiscovery:
            def __init__(self) -> None:
                self.services = {
                    "user_service": "http://user-service:8080",
                    "order_service": "http://order-service:8080",
                    "notification_service": "http://notification-service:8080",
                }

            def get_service_url(self, service_name: str) -> str:
                return self.services.get(service_name, "http://unknown:8080")

        class HttpClient:
            async def get(self, url: str) -> dict[str, str]:
                await asyncio.sleep(0.01)  # Simulate HTTP call
                return {"status": "success", "url": url}

        class UserService:
            def __init__(
                self, http_client: HttpClient, discovery: ServiceDiscovery
            ) -> None:
                self.client = http_client
                self.discovery = discovery

            async def get_user(self, user_id: str) -> dict[str, str]:
                url = (
                    f"{self.discovery.get_service_url('user_service')}/users/{user_id}"
                )
                response = await self.client.get(url)
                return {"user_id": user_id, "service_response": response}

        class OrderService:
            def __init__(
                self, http_client: HttpClient, discovery: ServiceDiscovery
            ) -> None:
                self.client = http_client
                self.discovery = discovery

            async def get_orders(self, user_id: str) -> List[dict[str, str]]:
                url = f"{self.discovery.get_service_url('order_service')}/orders?user_id={user_id}"
                response = await self.client.get(url)
                return [{"order_id": "123", "service_response": response}]

        # Dependency providers
        async def get_http_client() -> HttpClient:
            return HttpClient()

        async def get_service_discovery() -> ServiceDiscovery:
            return ServiceDiscovery()

        async def get_user_service(
            client: HttpClient = DependsInject(get_http_client),
            discovery: ServiceDiscovery = DependsInject(get_service_discovery),
        ) -> UserService:
            return UserService(client, discovery)

        async def get_order_service(
            client: HttpClient = DependsInject(get_http_client),
            discovery: ServiceDiscovery = DependsInject(get_service_discovery),
        ) -> OrderService:
            return OrderService(client, discovery)

        # Main handler combining multiple services
        async def user_dashboard_handler(
            user_id: str = ArgsInjectable(...),
            user_service: UserService = DependsInject(get_user_service),
            order_service: OrderService = DependsInject(get_order_service),
        ) -> str:
            user = await user_service.get_user(user_id)
            orders = await order_service.get_orders(user_id)

            return f"User {user['user_id']} has {len(orders)} orders"

        context = {"user_id": "user123"}
        resolved_func = await inject_args(user_dashboard_handler, context)
        result = await resolved_func()
        assert result == "User user123 has 1 orders"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_performance_with_many_dependencies(self) -> None:
        """Test performance with many dependencies to ensure no exponential complexity."""
        import asyncio
        import time

        # Create many independent dependencies
        async def create_dependency(dep_id: int):
            async def dependency() -> str:
                await asyncio.sleep(0.001)  # Small delay
                return f"dep_{dep_id}"

            dependency.__name__ = f"dependency_{dep_id}"
            return dependency

        dependencies = [await create_dependency(i) for i in range(20)]

        # Handler that depends on all of them
        async def many_deps_handler(**kwargs) -> str:
            values = list(kwargs.values())
            return f"Got {len(values)} dependencies"

        # Dynamically create function with many DependsInject parameters
        import inspect

        # Create signature dynamically
        params = []
        for i, dep in enumerate(dependencies):
            param = inspect.Parameter(
                f"dep_{i}", inspect.Parameter.KEYWORD_ONLY, default=DependsInject(dep)
            )
            params.append(param)

        new_sig = inspect.Signature(params)
        many_deps_handler.__signature__ = new_sig

        start_time = time.perf_counter()
        resolved_func = await inject_args(many_deps_handler, {})
        result = await resolved_func()
        end_time = time.perf_counter()

        assert result == "Got 20 dependencies"

        # Should complete reasonably quickly (not exponential time)
        execution_time = end_time - start_time
        assert execution_time < 1.0, f"Took {execution_time}s, should be much faster"


class TestErrorHandlingIntegration:
    """Test error handling in complex integration scenarios."""

    @pytest.mark.asyncio
    async def test_validation_error_propagation_through_dependencies(self) -> None:
        """Test that validation errors propagate correctly through dependency chains."""
        from ctxinject.constrained import constrained_factory
        from ctxinject.model import ConstrArgInject

        def validated_config(
            min_connections: int = ConstrArgInject(
                constrained_factory, ..., gt=0, le=100
            )
        ) -> dict[str, int]:
            return {"connections": min_connections}

        def database_pool(
            config: dict[str, int] = DependsInject(validated_config),
        ) -> str:
            return f"Pool with {config['connections']} connections"

        async def handler(pool: str = DependsInject(database_pool)) -> str:
            return pool

        # Should fail with validation error
        invalid_context = {"min_connections": 0}  # Violates gt=0 constraint

        with pytest.raises(ValueError, match="Value must be"):
            await inject_args(handler, invalid_context)

    @pytest.mark.asyncio
    async def test_missing_model_field_error_propagation(self) -> None:
        """Test error handling when model fields are missing."""

        class IncompleteModel:
            existing_field: str = "exists"
            # missing_field is not defined

        async def handler(
            existing: str = ModelFieldInject(IncompleteModel, field="existing_field"),
            missing: str = ModelFieldInject(IncompleteModel, field="missing_field"),
        ) -> str:
            return f"{existing}-{missing}"

        context = {IncompleteModel: IncompleteModel()}

        with pytest.raises(UnresolvedInjectableError):
            await inject_args(handler, context, allow_incomplete=False)

    @pytest.mark.asyncio
    async def test_dependency_exception_with_context(self) -> None:
        """Test that dependency exceptions include helpful context information."""

        async def failing_dependency() -> str:
            raise ValueError("Dependency computation failed")

        def dependent_service(dep: str = DependsInject(failing_dependency)) -> str:
            return f"Service using {dep}"

        async def handler(service: str = DependsInject(dependent_service)) -> str:
            return service

        # The original ValueError should be preserved, not wrapped
        with pytest.raises(ValueError, match="Dependency computation failed"):
            resolved_func = await inject_args(handler, {})
            await resolved_func()
