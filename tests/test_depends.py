import pytest

from ctxinject.dependencies import DependencyRegistry  # ou onde estiver seu arquivo
from ctxinject.model import Depends


# Um contexto básico e modelo fictício
class DB:
    def __init__(self, url: str):
        self.url = url


@pytest.mark.asyncio
async def test_simple_dependency_resolution() -> None:
    async def db_dep() -> DB:
        return DB("sqlite://")

    async def handler(db: DB = Depends(db_dep)):
        return db.url

    registry = DependencyRegistry()
    result = await registry.resolve(handler, context={}, modeltype=[DB])
    assert result == "sqlite://"


# falta fazer os mesmo tests com annotated


@pytest.mark.asyncio
async def test_chained_dependency() -> None:
    async def get_url() -> str:
        return "sqlite://"

    async def db_dep(url: str = Depends(get_url)) -> DB:
        return DB(url)

    async def handler(db: DB = Depends(db_dep)) -> str:
        return db.url

    registry = DependencyRegistry()
    result = await registry.resolve(handler, context={}, modeltype=[DB])
    assert result == "sqlite://"


@pytest.mark.asyncio
async def test_mixed_sync_async() -> None:
    def get_config() -> dict[str, str]:
        return {"key": "value"}

    async def service(cfg: dict[str, str] = Depends(get_config)) -> str:
        return cfg["key"]

    registry = DependencyRegistry()
    result = await registry.resolve(service, context={}, modeltype=[])
    assert result == "value"
