from functools import partial
from typing import Annotated, Any, Union

import pytest

from ctxinject.exceptions import UnresolvedInjectableError
from ctxinject.inject import inject_args
from ctxinject.mapfunction import get_func_args
from ctxinject.model import (
    ArgsInjectable,
    Injectable,
    ModelFieldInject,
    ModelMethodInject,
)


# mocks simples
class NoValidation(Injectable):
    pass


class No42(ArgsInjectable):
    def __init__(self, default: Any) -> None:
        super().__init__(default)

    def validate(self, instance: Any, basetype: type[Any]) -> None:
        if instance == 42:
            raise ValueError
        return instance


class MyModel(int): ...


class MyModelField:
    def __init__(self, e: str, f: float) -> None:
        self.e = e
        self.f = f


# ---------- ADICIONADO: Mock de Model com Método ----------
class MyModelMethod:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def get_value(self) -> str:
        return f"{self.prefix}_value"

    def other_method(self) -> str:
        return f"{self.prefix}_other"


# função-alvo com ModelFieldInject
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


# ---------- ADICIONADO: função-alvo com ModelMethodInject ----------
def injfunc_method(
    x: Annotated[str, ArgsInjectable(...)],
    y: str = ModelMethodInject(model=MyModelMethod, method="get_value"),  # type: ignore
    z: str = ModelMethodInject(model=MyModelMethod, method="other_method"),  # type: ignore
) -> tuple[str, str, str]:
    return x, y, z


# ---------- TESTES EXISTENTES ----------


def test_inject_by_name() -> None:
    ctx: dict[Union[str, type], Any] = {
        "a": "hello",
        "b": "world",
        "c": 123,
        "e": "foobar",
        "h": 0.1,
    }
    injected = inject_args(injfunc, ctx)
    assert isinstance(injected, partial)
    res = injected()
    assert res == ("hello", "world", 123, 44, "foobar", 3.14, True, 0.1)


def test_inject_by_type() -> None:
    ctx: dict[Union[str, type], Any] = {
        str: "typed!",
        int: 43,
        MyModel: 100,
        MyModelField: MyModelField(e="foobar", f=2.2),
    }
    injected = inject_args(injfunc, ctx)
    res = injected(a="X")
    assert res == ("X", "typed!", 100, 43, "foobar", 3.14, True, 2.2)


def test_inject_default_used() -> None:
    ctx = {"a": "A", "c": 100, "e": "hello", "h": 0.12}  # 'b' and 'd' will be  default
    injected = inject_args(injfunc, ctx)
    assert injected() == (
        "A",
        "abc",  # default
        100,
        44,  # default
        "hello",
        3.14,
        True,
        0.12,
    )


def test_inject_changed_func() -> None:
    deps = get_func_args(injfunc)
    ctx = {"a": "foobar", "b": "helloworld"}
    resolfunc = inject_args(func=injfunc, context=ctx, allow_incomplete=True)
    args = get_func_args(resolfunc)
    assert args != deps


def test_inject_chained() -> None:
    deps = get_func_args(injfunc)
    ctx = {"a": "foobar"}
    resolfunc = inject_args(injfunc, ctx, True)
    args = get_func_args(resolfunc)
    assert args != deps

    ctx2 = {"c": 2}
    resolfunc2 = inject_args(resolfunc, ctx2, True)
    args2 = get_func_args(resolfunc2)
    assert args != args2


def test_inject_name_over_type() -> None:
    ctx = {
        "b": "by_name",
        str: "by_type",  # deveria ignorar, pois 'b' está por nome
        "a": "ok",
        "c": 1,
        "e": "x",
        "h": 0.0,
    }
    injected = inject_args(injfunc, ctx, [MyModel])
    res = injected()
    assert res[1] == "by_name"  # name should have preference


def test_annotated_multiple_extras() -> None:
    def func(a: Annotated[int, No42(44), NoValidation()]) -> int:
        return a

    args = get_func_args(func)
    arg = args[0]
    assert isinstance(arg.getinstance(ArgsInjectable), No42)
    assert isinstance(arg.getinstance(NoValidation), NoValidation)


def test_missing_required_arg() -> None:
    def func(a: Annotated[str, ArgsInjectable(...)]) -> str:
        return a

    with pytest.raises(UnresolvedInjectableError):
        inject_args(func, {}, False)


# ---------- TESTES NOVOS: ModelMethodInject ----------


def test_model_method_inject_basic() -> None:
    ctx = {"x": "test_input", MyModelMethod: MyModelMethod(prefix="basic")}
    injected = inject_args(injfunc_method, ctx)
    res = injected()
    assert res == ("test_input", "basic_value", "basic_other")


def test_model_method_inject_name_overrides() -> None:
    ctx = {
        "x": "override_test",
        "y": "by_name_y",
        "z": "by_name_z",
        MyModelMethod: MyModelMethod(prefix="should_not_use"),
    }
    injected = inject_args(injfunc_method, ctx)
    res = injected()
    assert res == ("override_test", "by_name_y", "by_name_z")


def test_model_method_inject_missing_model() -> None:
    ctx = {
        "x": "fail_case"
        # MyModelMethod está faltando
    }
    with pytest.raises(UnresolvedInjectableError):
        inject_args(injfunc_method, ctx, allow_incomplete=False)
