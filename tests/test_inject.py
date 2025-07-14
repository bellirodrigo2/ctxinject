import unittest
from functools import partial

from typemapping import get_func_args
from typing_extensions import Annotated, Any, Type, Union

from ctxinject.inject import UnresolvedInjectableError, inject_args
from ctxinject.model import ArgsInjectable, Injectable, ModelFieldInject


class NoValidation(Injectable):
    pass


class No42(ArgsInjectable):
    def __init__(self, default: Any) -> None:
        super().__init__(default)

    def validate(self, instance: Any, basetype: Type[Any]) -> None:
        if instance == 42:
            raise ValueError
        return instance


class MyModel(int): ...


class MyModelField:
    def __init__(self, e: str, f: float) -> None:
        self.e = e
        self.f = f


class MyModelMethod:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def get_value(self) -> str:
        return f"{self.prefix}_value"

    def other_method(self) -> str:
        return f"{self.prefix}_other"


def injfunc(
    a: Annotated[str, ArgsInjectable(...)],
    c: MyModel,
    b: str = ArgsInjectable("abc"),  # type: ignore
    d: int = No42(44),  # type: ignore
    e: str = ModelFieldInject(model=MyModelField),  # type: ignore
    f: float = 3.14,
    g: bool = True,
    h: float = ModelFieldInject(model=MyModelField, field="f"),  # type: ignore
) -> tuple[str, str, MyModel, int, str, float, bool, float]:
    return a, b, c, d, e, f, g, h


def injfunc_method(
    x: Annotated[str, ArgsInjectable(...)],
    y: str = ModelFieldInject(model=MyModelMethod, field="get_value"),  # type: ignore
    z: str = ModelFieldInject(model=MyModelMethod, field="other_method"),  # type: ignore
) -> tuple[str, str, str]:
    return x, y, z


class TestInjectArgs(unittest.IsolatedAsyncioTestCase):

    async def test_inject_by_name(self) -> None:
        ctx: dict[Union[str, type], Any] = {
            "a": "hello",
            "b": "world",
            "c": 123,
            "e": "foobar",
            "h": 0.1,
        }
        injected = await inject_args(injfunc, ctx)
        self.assertIsInstance(injected, partial)
        res = injected()
        self.assertEqual(res, ("hello", "world", 123, 44, "foobar", 3.14, True, 0.1))

    async def test_inject_by_type(self) -> None:
        ctx: dict[Union[str, type], Any] = {
            str: "typed!",
            int: 43,
            MyModel: 100,
            MyModelField: MyModelField(e="foobar", f=2.2),
        }
        injected = await inject_args(injfunc, ctx)
        res = injected(a="X")
        self.assertEqual(res, ("X", "typed!", 100, 43, "foobar", 3.14, True, 2.2))

    async def test_inject_default_used(self) -> None:
        ctx = {
            "a": "A",
            "c": 100,
            "e": "hello",
            "h": 0.12,
        }  # 'b' and 'd' will be default
        injected = await inject_args(injfunc, ctx)
        self.assertEqual(
            injected(),
            (
                "A",
                "abc",  # default
                100,
                44,  # default
                "hello",
                3.14,
                True,
                0.12,
            ),
        )

    async def test_inject_changed_func(self) -> None:
        deps = get_func_args(injfunc)
        ctx = {"a": "foobar", "b": "helloworld"}
        resolfunc = await inject_args(func=injfunc, context=ctx, allow_incomplete=True)
        args = get_func_args(resolfunc)
        self.assertNotEqual(args, deps)

    async def test_inject_chained(self) -> None:
        deps = get_func_args(injfunc)
        ctx = {"a": "foobar"}
        resolfunc = await inject_args(injfunc, ctx, True)
        args = get_func_args(resolfunc)
        self.assertNotEqual(args, deps)

        ctx2 = {"c": 2}
        resolfunc2 = await inject_args(resolfunc, ctx2, True)
        args2 = get_func_args(resolfunc2)
        self.assertNotEqual(args, args2)

    async def test_inject_name_over_type(self) -> None:
        ctx = {
            "b": "by_name",
            str: "by_type",  # should ignore since 'b' is provided by name
            "a": "ok",
            "c": 1,
            "e": "x",
            "h": 0.0,
        }
        injected = await inject_args(injfunc, ctx, [MyModel])
        res = injected()
        self.assertEqual(res[1], "by_name")

    def test_annotated_multiple_extras(self) -> None:
        def func(a: Annotated[int, No42(44), NoValidation()]) -> int:
            return a

        args = get_func_args(func)
        arg = args[0]
        self.assertIsInstance(arg.getinstance(ArgsInjectable), No42)
        self.assertIsInstance(arg.getinstance(NoValidation), NoValidation)

    async def test_missing_required_arg(self) -> None:
        def func(a: Annotated[str, ArgsInjectable(...)]) -> str:
            return a

        with self.assertRaises(UnresolvedInjectableError):
            await inject_args(func, {}, False)

    async def test_model_method_inject_basic(self) -> None:
        ctx = {"x": "test_input", MyModelMethod: MyModelMethod(prefix="basic")}
        injected = await inject_args(injfunc_method, ctx)
        res = injected()
        self.assertEqual(res, ("test_input", "basic_value", "basic_other"))

    async def test_model_method_inject_name_overrides(self) -> None:
        ctx = {
            "x": "override_test",
            "y": "by_name_y",
            "z": "by_name_z",
            MyModelMethod: MyModelMethod(prefix="should_not_use"),
        }
        injected = await inject_args(injfunc_method, ctx)
        res = injected()
        self.assertEqual(res, ("override_test", "by_name_y", "by_name_z"))

    async def test_model_method_inject_missing_model(self) -> None:
        ctx = {
            "x": "fail_case"
            # Missing MyModelMethod
        }
        with self.assertRaises(UnresolvedInjectableError):
            await inject_args(injfunc_method, ctx, allow_incomplete=False)


if __name__ == "__main__":
    unittest.main()
