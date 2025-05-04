import pytest

from ctxinject.inject import inject_dependencies, resolve  # ou onde estiver seu arquivo
from ctxinject.model import Depends, UnresolvedInjectableError


# Um contexto básico e modelo fictício
class DB:
    def __init__(self, url: str):
        self.url = url


@pytest.mark.asyncio
async def test_simple_dependency_resolution() -> None:
    async def db_dep() -> DB:
        return DB("sqlite://")

    async def handler(db: DB = Depends(db_dep)) -> str:
        return db.url

    result = await resolve(handler, context={}, overrides={})
    assert result == "sqlite://"


async def test_simple_dependency_extra_arg() -> None:
    def db_dep() -> DB:
        return DB("sqlite://")

    def handler(arg: str, db: DB = Depends(db_dep)) -> str:
        return db.url

    with pytest.raises(UnresolvedInjectableError):
        await resolve(handler, context={}, overrides={})


async def test_simple_dependency_extra_arg_inject() -> None:
    def db_dep() -> DB:
        return DB("sqlite://")

    def handler(arg: str, db: DB = Depends(db_dep)) -> str:
        return db.url + arg

    handler_resolved = await inject_dependencies(handler, context={}, overrides={})
    res = handler_resolved(arg="foobar")
    assert res == "sqlite://foobar"


@pytest.mark.asyncio
async def test_chained_dependency() -> None:
    async def get_url() -> str:
        return "sqlite://"

    async def db_dep(url: str = Depends(get_url)) -> DB:
        return DB(url)

    async def handler(db: DB = Depends(db_dep)) -> str:
        return db.url

    result = await resolve(handler, context={}, overrides={})
    assert result == "sqlite://"


@pytest.mark.asyncio
async def test_mixed_sync_async() -> None:
    def get_config() -> dict[str, str]:
        return {"key": "value"}

    async def service(cfg: dict[str, str] = Depends(get_config)) -> str:
        return cfg["key"]

    result = await resolve(service, context={}, overrides={})
    assert result == "value"


from typing import Annotated, Any


@pytest.mark.asyncio
async def test_annotated_dependency() -> None:
    async def db_dep() -> DB:
        return DB("sqlite://")

    async def handler(db: Annotated[DB, Depends(db_dep)]) -> str:
        return db.url

    result = await resolve(handler, context={}, overrides={})
    assert result == "sqlite://"


@pytest.mark.asyncio
async def test_annotated_with_extras_dependency() -> None:
    async def get_url() -> str:
        return "sqlite://"

    async def db_dep(url: Annotated[str, Depends(get_url), "meta"]) -> DB:
        return DB(url)

    async def handler(db: Annotated[DB, Depends(db_dep)]) -> str:
        return db.url

    result = await resolve(handler, context={}, overrides={})
    assert result == "sqlite://"


@pytest.mark.asyncio
async def test_mixed_annotated_and_default() -> None:
    async def get_url() -> str:
        return "sqlite://"

    def get_config() -> dict[str, str]:
        return {"timeout": "30s"}

    async def handler(
        url: Annotated[str, Depends(get_url)],
        cfg: Annotated[dict[str, str], Depends(get_config)] = {"timeout": "60s"},
    ) -> str:
        return f"{url} with timeout {cfg['timeout']}"

    result = await resolve(handler, context={}, overrides={})
    assert result == "sqlite:// with timeout 30s"


class A:
    def __init__(self, value: str):
        self.value = value


class B:
    def __init__(self, a: A, flag: bool):
        self.a = a
        self.flag = flag


class C:
    def __init__(self, b: B, config: dict[Any, Any]):
        self.b = b
        self.config = config


class D:
    def __init__(self, c: C, x: int):
        self.c = c
        self.x = x


@pytest.mark.asyncio
async def test_deeply_nested_dependencies() -> None:
    async def provide_a() -> A:
        return A("deep")

    def provide_flag() -> bool:
        return True

    def provide_b(a: A = Depends(provide_a), flag: bool = Depends(provide_flag)) -> B:
        return B(a, flag)

    def provide_config() -> dict:
        return {"retry": 3}

    def provide_c(
        b: B = Depends(provide_b), config: dict = Depends(provide_config)
    ) -> C:
        return C(b, config)

    def provide_x() -> int:
        return 99

    async def handler(c: C = Depends(provide_c), x: int = Depends(provide_x)) -> str:
        return f"{c.b.a.value}-{c.b.flag}-{c.config['retry']}-{x}"

    result = await resolve(handler, context={}, overrides={})
    assert result == "deep-True-3-99"
