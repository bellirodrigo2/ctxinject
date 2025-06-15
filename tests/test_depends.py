import unittest
from typing import Annotated, Any

from ctxinject.inject import UnresolvedInjectableError, inject_args
from ctxinject.model import DependsInject


class DB:
    def __init__(self, url: str):
        self.url = url


class TestCtxInject(unittest.IsolatedAsyncioTestCase):

    async def test_simple_dependency_resolution(self) -> None:
        async def db_dep() -> DB:
            return DB("sqlite://")

        async def handler(db: DB = DependsInject(db_dep)) -> str:
            return db.url

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        self.assertEqual(result, "sqlite://")

    async def test_simple_dependency_extra_arg(self) -> None:
        def db_dep() -> DB:
            return DB("sqlite://")

        def handler(arg: str, db: DB = DependsInject(db_dep)) -> str:
            return db.url

        with self.assertRaises(UnresolvedInjectableError):
            await inject_args(handler, context={}, overrides={}, allow_incomplete=False)

    async def test_simple_dependency_extra_arg_inject(self) -> None:
        def db_dep() -> DB:
            return DB("sqlite://")

        def handler(arg: str, db: DB = DependsInject(db_dep)) -> str:
            return db.url + arg

        handler_resolved = await inject_args(handler, context={})
        res = handler_resolved(arg="foobar")
        self.assertEqual(res, "sqlite://foobar")

    async def test_chained_dependency(self) -> None:
        async def get_url() -> str:
            return "sqlite://"

        async def db_dep(url: str = DependsInject(get_url)) -> DB:
            return DB(url)

        async def handler(db: DB = DependsInject(db_dep)) -> str:
            return db.url

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        self.assertEqual(result, "sqlite://")

    async def test_mixed_sync_async(self) -> None:
        def get_config() -> dict[str, str]:
            return {"key": "value"}

        async def service(cfg: dict[str, str] = DependsInject(get_config)) -> str:
            return cfg["key"]

        resolved_func = await inject_args(service, {})
        result = await resolved_func()
        self.assertEqual(result, "value")

    async def test_annotated_dependency(self) -> None:
        async def db_dep() -> DB:
            return DB("sqlite://")

        async def handler(db: Annotated[DB, DependsInject(db_dep)]) -> str:
            return db.url

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        self.assertEqual(result, "sqlite://")

    async def test_annotated_with_extras_dependency(self) -> None:
        async def get_url() -> str:
            return "sqlite://"

        async def db_dep(url: Annotated[str, DependsInject(get_url), "meta"]) -> DB:
            return DB(url)

        async def handler(db: Annotated[DB, DependsInject(db_dep)]) -> str:
            return db.url

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        self.assertEqual(result, "sqlite://")

    async def test_mixed_annotated_and_default(self) -> None:
        async def get_url() -> str:
            return "sqlite://"

        def get_config() -> dict[str, str]:
            return {"timeout": "30s"}

        async def handler(
            url: Annotated[str, DependsInject(get_url)],
            cfg: Annotated[dict[str, str], DependsInject(get_config)] = {
                "timeout": "60s"
            },
        ) -> str:
            return f"{url} with timeout {cfg['timeout']}"

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        self.assertEqual(result, "sqlite:// with timeout 30s")

    async def test_deeply_nested_dependencies(self) -> None:
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

        async def provide_a() -> A:
            return A("deep")

        def provide_flag() -> bool:
            return True

        def provide_b(
            a: A = DependsInject(provide_a), flag: bool = DependsInject(provide_flag)
        ) -> B:
            return B(a, flag)

        def provide_config() -> dict:
            return {"retry": 3}

        def provide_c(
            b: B = DependsInject(provide_b),
            config: dict = DependsInject(provide_config),
        ) -> C:
            return C(b, config)

        def provide_x() -> int:
            return 99

        async def handler(
            c: C = DependsInject(provide_c), x: int = DependsInject(provide_x)
        ) -> str:
            return f"{c.b.a.value}-{c.b.flag}-{c.config['retry']}-{x}"

        resolved_func = await inject_args(handler, {})
        result = await resolved_func()
        self.assertEqual(result, "deep-True-3-99")


if __name__ == "__main__":
    unittest.main()
