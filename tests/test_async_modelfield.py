import asyncio
from typing import Dict, Optional

import pytest

from ctxinject.inject import inject_args
from ctxinject.model import ModelFieldInject


class Database:
    def __init__(self, name: str):
        self.name = name
        self.connection_count = 5

    async def get_status(self) -> str:
        await asyncio.sleep(0.01)
        return "connected"

    def get_name(self) -> str:
        return self.name


class UserService:
    def __init__(self, db: Database, cache_enabled: bool = True):
        self.db = db
        self.cache_enabled = cache_enabled
        self.user_count = 100

    async def get_user_count(self) -> int:
        await asyncio.sleep(0.01)
        return self.user_count

    def is_cache_enabled(self) -> bool:
        return self.cache_enabled


class AppConfig:
    def __init__(self, service: UserService):
        self.service = service
        self.app_name = "TestApp"
        self.version = "1.0.0"

    @property
    def display_name(self) -> str:
        return f"{self.app_name} v{self.version}"

    async def get_health_status(self) -> Dict[str, str]:
        await asyncio.sleep(0.01)
        db_status = await self.service.db.get_status()
        return {"app": "healthy", "db": db_status}


@pytest.mark.asyncio
async def test_mixed_sync_async_fields():
    db = Database("main_db")
    service = UserService(db)
    config = AppConfig(service)

    def get_app_info(
        # sync fields
        app_name: str = ModelFieldInject(
            AppConfig,
            "app_name",
        ),
        version: str = ModelFieldInject(
            AppConfig,
            "version",
        ),
        display: str = ModelFieldInject(
            AppConfig,
            "display_name",
        ),
        # nested sync fields
        db_name: str = ModelFieldInject(
            AppConfig,
            "service.db.name",
        ),
        cache_enabled: bool = ModelFieldInject(
            AppConfig,
            "service.cache_enabled",
        ),
        # nested sync methods
        cache_status: bool = ModelFieldInject(
            AppConfig,
            "service.is_cache_enabled",
        ),
        db_name_method: str = ModelFieldInject(
            AppConfig,
            "service.db.get_name",
        ),
    ):
        return {
            "app": f"{display} ({app_name})",
            "version": version,
            "db": db_name,
            "cache": cache_enabled,
            "cache_method": cache_status,
            "db_method": db_name_method,
        }

    context = {AppConfig: config}
    injected = await inject_args(get_app_info, context, enable_async_model_field=True)
    result = injected()

    assert result["app"] == "TestApp v1.0.0 (TestApp)"
    assert result["version"] == "1.0.0"
    assert result["db"] == "main_db"
    assert result["cache"] is True
    assert result["cache_method"] is True
    assert result["db_method"] == "main_db"


@pytest.mark.asyncio
async def test_mixed_async_fields():
    db = Database("async_db")
    service = UserService(db, False)
    config = AppConfig(service)

    def get_async_info(
        # sync fields mixed with async methods
        app_name: str = ModelFieldInject(
            AppConfig,
            "app_name",
        ),
        # async methods at different levels
        db_status: str = ModelFieldInject(
            AppConfig,
            "service.db.get_status",
        ),
        user_count: int = ModelFieldInject(
            AppConfig,
            "service.get_user_count",
        ),
        health: Dict[str, str] = ModelFieldInject(
            AppConfig,
            "get_health_status",
        ),
        # sync methods mixed in
        cache_enabled: bool = ModelFieldInject(
            AppConfig,
            "service.is_cache_enabled",
        ),
    ):
        return {
            "app": app_name,
            "db_status": db_status,
            "users": user_count,
            "health": health,
            "cache": cache_enabled,
        }

    context = {AppConfig: config}
    injected = await inject_args(get_async_info, context, enable_async_model_field=True)
    result = injected()

    assert result["app"] == "TestApp"
    assert result["db_status"] == "connected"
    assert result["users"] == 100
    assert result["health"]["app"] == "healthy"
    assert result["health"]["db"] == "connected"
    assert result["cache"] is False


@pytest.mark.asyncio
async def test_deep_async_nesting():
    db = Database("deep_db")
    service = UserService(db)
    config = AppConfig(service)

    def get_deep_async(
        # deep nested async method
        nested_db_status: str = ModelFieldInject(
            AppConfig,
            "service.db.get_status",
        ),
        # mix with sync
        app_version: str = ModelFieldInject(
            AppConfig,
            "version",
        ),
        # multiple async
        user_count: int = ModelFieldInject(
            AppConfig,
            "service.get_user_count",
        ),
        health_check: Dict[str, str] = ModelFieldInject(
            AppConfig,
            "get_health_status",
        ),
    ):
        return {
            "deep_status": nested_db_status,
            "version": app_version,
            "users": user_count,
            "health": health_check,
        }

    context = {AppConfig: config}
    injected = await inject_args(get_deep_async, context, enable_async_model_field=True)
    result = injected()

    assert result["deep_status"] == "connected"
    assert result["version"] == "1.0.0"
    assert result["users"] == 100
    assert result["health"]["db"] == "connected"


@pytest.mark.asyncio
async def test_async_with_none_values():
    class OptionalService:
        def __init__(self, db: Optional[Database] = None):
            self.db = db

        async def get_db_status(self) -> Optional[str]:
            if self.db:
                return await self.db.get_status()
            return None

    class OptionalConfig:
        def __init__(self, service: Optional[OptionalService] = None):
            self.service = service
            self.name = "optional_app"

    # Test with None service
    config_none = OptionalConfig(None)

    def get_with_none(
        name: str = ModelFieldInject(
            OptionalConfig,
            "name",
        ),
        status: Optional[str] = ModelFieldInject(
            OptionalConfig,
            "service.get_db_status",
        ),
    ):
        return {"name": name, "status": status}

    context = {OptionalConfig: config_none}
    injected = await inject_args(get_with_none, context, enable_async_model_field=True)
    result = injected()

    assert result["name"] == "optional_app"
    assert result["status"] is None  # None propagated through async path


@pytest.mark.asyncio
async def test_error_handling_async():
    class FailingService:
        async def failing_method(self) -> str:
            raise ValueError("Async method failed")

    class ErrorConfig:
        def __init__(self):
            self.service = FailingService()

    def get_failing_data(
        result: str = ModelFieldInject(
            ErrorConfig,
            "service.failing_method",
        ),
    ):
        return result

    config = ErrorConfig()
    context = {ErrorConfig: config}

    with pytest.raises(ValueError, match="Async method failed"):
        await inject_args(get_failing_data, context, enable_async_model_field=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
