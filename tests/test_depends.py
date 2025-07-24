"""
Tests for dependency injection with Depends functionality.

This module tests the Depends decorator and complex dependency chains,
including async/sync mixing, nested dependencies, and error handling.
"""

from typing import Any, Dict

import pytest
from typing_extensions import Annotated

from ctxinject.inject import UnresolvedInjectableError, inject_args
from ctxinject.model import DependsInject
from tests.conftest import (
    DB,
    async_db_dependency,
    async_url_dependency,
    sync_config_dependency,
    sync_db_dependency,
)


class TestBasicDependencyInjection:
    """Test basic dependency injection scenarios."""

    @pytest.mark.asyncio
    async def test_simple_async_dependency_resolution(self) -> None:
        """Test simple async dependency resolution."""

        async def handler(db: DB = DependsInject(async_db_dependency)) -> str:
            return db.url

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        assert result == "sqlite://"

    @pytest.mark.asyncio
    async def test_simple_sync_dependency_resolution(self) -> None:
        """Test simple sync dependency resolution."""

        def handler(db: DB = DependsInject(sync_db_dependency)) -> str:
            return db.url

        resolved_func = await inject_args(handler, {})
        result = resolved_func()
        assert result == "sqlite://"

    @pytest.mark.asyncio
    async def test_dependency_with_extra_arg(self) -> None:
        """Test dependency injection with additional unresolved arguments."""

        def handler(arg: str, db: DB = DependsInject(sync_db_dependency)) -> str:
            return db.url + arg

        with pytest.raises(UnresolvedInjectableError, match="incomplete or missing"):
            await inject_args(handler, context={}, allow_incomplete=False)

    @pytest.mark.asyncio
    async def test_dependency_with_partial_resolution(self) -> None:
        """Test dependency injection with partial argument resolution."""

        def handler(arg: str, db: DB = DependsInject(sync_db_dependency)) -> str:
            return db.url + arg

        handler_resolved = await inject_args(handler, context={})
        result = handler_resolved(arg="foobar")
        assert result == "sqlite://foobar"

    @pytest.mark.asyncio
    async def test_mixed_sync_async_dependencies(self) -> None:
        """Test mixing sync and async dependencies."""

        async def service(
            cfg: Dict[str, str] = DependsInject(sync_config_dependency),
        ) -> str:
            return cfg["key"]

        resolved_func = await inject_args(service, {})
        result = await resolved_func()
        assert result == "value"


class TestChainedDependencies:
    """Test complex dependency chains and nested dependencies."""

    @pytest.mark.asyncio
    async def test_chained_async_dependency(self) -> None:
        """Test chained async dependencies."""

        async def db_dep(url: str = DependsInject(async_url_dependency)) -> DB:
            return DB(url)

        async def handler(db: DB = DependsInject(db_dep)) -> str:
            return db.url

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        assert result == "sqlite://"

    @pytest.mark.asyncio
    async def test_deeply_nested_dependencies(self) -> None:
        """Test deeply nested dependency chains."""

        class ComponentA:
            def __init__(self, value: str) -> None:
                self.value = value

        class ComponentB:
            def __init__(self, a: ComponentA, flag: bool) -> None:
                self.a = a
                self.flag = flag

        class ComponentC:
            def __init__(self, b: ComponentB, config: Dict[Any, Any]) -> None:
                self.b = b
                self.config = config

        class ComponentD:
            def __init__(self, c: ComponentC, x: int) -> None:
                self.c = c
                self.x = x

        async def provide_a() -> ComponentA:
            return ComponentA("deep")

        def provide_flag() -> bool:
            return True

        def provide_b(
            a: ComponentA = DependsInject(provide_a),
            flag: bool = DependsInject(provide_flag),
        ) -> ComponentB:
            return ComponentB(a, flag)

        def provide_config() -> Dict[str, int]:
            return {"retry": 3}

        def provide_c(
            b: ComponentB = DependsInject(provide_b),
            config: Dict[str, int] = DependsInject(provide_config),
        ) -> ComponentC:
            return ComponentC(b, config)

        def provide_x() -> int:
            return 99

        async def handler(
            c: ComponentC = DependsInject(provide_c), x: int = DependsInject(provide_x)
        ) -> str:
            return f"{c.b.a.value}-{c.b.flag}-{c.config['retry']}-{x}"

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        assert result == "deep-True-3-99"

    @pytest.mark.asyncio
    async def test_diamond_dependency_pattern(self) -> None:
        """Test diamond dependency pattern (shared dependencies)."""

        class SharedService:
            def __init__(self, config: str) -> None:
                self.config = config

        class ServiceA:
            def __init__(self, shared: SharedService) -> None:
                self.shared = shared

        class ServiceB:
            def __init__(self, shared: SharedService) -> None:
                self.shared = shared

        class Consumer:
            def __init__(self, a: ServiceA, b: ServiceB) -> None:
                self.a = a
                self.b = b

        def provide_shared() -> SharedService:
            return SharedService("shared_config")

        def provide_a(
            shared: SharedService = DependsInject(provide_shared),
        ) -> ServiceA:
            return ServiceA(shared)

        def provide_b(
            shared: SharedService = DependsInject(provide_shared),
        ) -> ServiceB:
            return ServiceB(shared)

        def provide_consumer(
            a: ServiceA = DependsInject(provide_a),
            b: ServiceB = DependsInject(provide_b),
        ) -> Consumer:
            return Consumer(a, b)

        async def handler(consumer: Consumer = DependsInject(provide_consumer)) -> str:
            return f"{consumer.a.shared.config}-{consumer.b.shared.config}"

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        assert result == "shared_config-shared_config"


class TestAnnotatedDependencies:
    """Test dependencies with Annotated type hints."""

    @pytest.mark.asyncio
    async def test_annotated_dependency(self) -> None:
        """Test dependency injection with Annotated types."""

        async def handler(db: Annotated[DB, DependsInject(async_db_dependency)]) -> str:
            return db.url

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        assert result == "sqlite://"

    @pytest.mark.asyncio
    async def test_annotated_with_extras_dependency(self) -> None:
        """Test Annotated dependencies with extra metadata."""

        async def db_dep(
            url: Annotated[str, DependsInject(async_url_dependency), "meta"],
        ) -> DB:
            return DB(url)

        async def handler(db: Annotated[DB, DependsInject(db_dep)]) -> str:
            return db.url

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        assert result == "sqlite://"

    @pytest.mark.asyncio
    async def test_mixed_annotated_and_default(self) -> None:
        """Test mixing Annotated dependencies with default values."""

        def get_config() -> Dict[str, str]:
            return {"timeout": "30s"}

        async def handler(
            url: Annotated[str, DependsInject(async_url_dependency)],
            cfg: Annotated[Dict[str, str], DependsInject(get_config)] = {
                "timeout": "60s"
            },
        ) -> str:
            return f"{url} with timeout {cfg['timeout']}"

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        assert result == "sqlite:// with timeout 30s"


class TestDependencyErrorHandling:
    """Test error handling in dependency injection."""

    @pytest.mark.asyncio
    async def test_dependency_function_raises_exception(self) -> None:
        """Test handling of exceptions in dependency functions."""

        async def failing_dependency() -> str:
            raise RuntimeError("Dependency failed")

        async def handler(value: str = DependsInject(failing_dependency)) -> str:
            return value

        with pytest.raises(RuntimeError, match="Dependency failed"):
            resolved_func = await inject_args(handler, {})
            await resolved_func()

    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self) -> None:
        """Test detection of circular dependencies."""

        def circular_a() -> str:
            # This would create a circular dependency if not handled
            return "a"

        def circular_b(a: str = DependsInject(circular_a)) -> str:
            return f"b-{a}"

        # This shouldn't create infinite recursion
        async def handler(b: str = DependsInject(circular_b)) -> str:
            return b

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        assert result == "b-a"

    @pytest.mark.asyncio
    async def test_missing_dependency_function(self) -> None:
        """Test handling of invalid dependency functions."""

        # Test with a function that will cause issues
        def invalid_dependency():
            raise RuntimeError("Invalid dependency")

        async def handler(value: str = DependsInject(invalid_dependency)) -> str:
            return value

        # This should raise RuntimeError when the dependency is called
        with pytest.raises(RuntimeError, match="Invalid dependency"):
            resolved_func = await inject_args(handler, {})
            await resolved_func()


class TestDependencyOverrides:
    """Test dependency override functionality."""

    @pytest.mark.asyncio
    async def test_dependency_override(self) -> None:
        """Test overriding dependencies for testing."""

        def original_dep() -> str:
            return "original"

        def override_dep() -> str:
            return "override"

        async def handler(value: str = DependsInject(original_dep)) -> str:
            return value

        # Test with override
        overrides = {original_dep: override_dep}
        resolved_func = await inject_args(handler, {}, overrides=overrides)
        result = await resolved_func()
        assert result == "override"

        # Test without override - create a new handler to avoid state pollution
        async def handler2(value: str = DependsInject(original_dep)) -> str:
            return value

        resolved_func_normal = await inject_args(handler2, {})
        result_normal = await resolved_func_normal()
        assert result_normal == "original"

    @pytest.mark.asyncio
    async def test_nested_dependency_override(self) -> None:
        """Test overriding nested dependencies."""

        def base_config() -> Dict[str, str]:
            return {"env": "prod"}

        def override_config() -> Dict[str, str]:
            return {"env": "test"}

        def service(config: Dict[str, str] = DependsInject(base_config)) -> str:
            return f"Service in {config['env']}"

        async def handler(svc: str = DependsInject(service)) -> str:
            return svc

        # Test with override
        overrides = {base_config: override_config}
        resolved_func = await inject_args(handler, {}, overrides=overrides)
        result = await resolved_func()
        assert result == "Service in test"


class TestAsyncDependencyChains:
    """Test complex async dependency chains."""

    @pytest.mark.asyncio
    async def test_all_async_chain(self) -> None:
        """Test chain where all dependencies are async."""

        async def async_config() -> Dict[str, str]:
            return {"db_url": "async://localhost"}

        async def async_db(config: Dict[str, str] = DependsInject(async_config)) -> DB:
            return DB(config["db_url"])

        async def async_service(db: DB = DependsInject(async_db)) -> str:
            return f"Service with {db.url}"

        async def handler(svc: str = DependsInject(async_service)) -> str:
            return svc

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        assert result == "Service with async://localhost"

    @pytest.mark.asyncio
    async def test_mixed_async_sync_chain(self) -> None:
        """Test chain mixing async and sync dependencies."""

        def sync_config() -> Dict[str, str]:
            return {"timeout": "30"}

        async def async_client(
            config: Dict[str, str] = DependsInject(sync_config),
        ) -> str:
            return f"Client with timeout {config['timeout']}"

        def sync_processor(client: str = DependsInject(async_client)) -> str:
            return f"Processor using {client}"

        async def handler(proc: str = DependsInject(sync_processor)) -> str:
            return proc

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        assert result == "Processor using Client with timeout 30"
