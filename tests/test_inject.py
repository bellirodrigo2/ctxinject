from functools import partial
from typing import Annotated, Any, Union

import pytest

from ctxinject.inject import inject
from ctxinject.mapfunction import get_func_args
from ctxinject.model import ArgsInjectable, Injectable, ModelFieldInject


# mocks simples
class NoValidation(Injectable):
    pass


class No42(ArgsInjectable):
    def __init__(self, default: Any) -> None:
        super().__init__(default)

    def validate(self, instance: Any) -> None:
        if instance == 42:
            raise ValueError


class MyModel(int): ...


class MyModelField:
    def __init__(self, e: str, f: float) -> None:
        self.e = e
        self.f = f


# função-alvo
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


def test_inject_by_name() -> None:
    ctx: dict[Union[str, type], Any] = {
        "a": "hello",
        "b": "world",
        "c": 123,
        "e": "foobar",
        "h": 0.1,
    }
    injected = inject(injfunc, ctx, [MyModel])

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
    injected = inject(injfunc, ctx, [MyModel])
    res = injected(a="X")
    assert res == ("X", "typed!", 100, 43, "foobar", 3.14, True, 2.2)


def test_inject_default_used() -> None:
    ctx = {"a": "A", "c": 100, "e": "hello", "h": 0.12}  # 'b' and 'd' will be  default
    injected = inject(injfunc, ctx, [MyModel])
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


def test_model_validation() -> None:
    ctx = {}
    with pytest.raises(TypeError):
        inject(injfunc, ctx, [MyModel, 123], True)


def test_inject_changed_func() -> None:

    deps = get_func_args(injfunc)
    ctx = {"a": "foobar", "b": "helloworld"}
    resolfunc = inject(injfunc, ctx, [MyModel])
    args = get_func_args(resolfunc)
    assert args != deps


def test_inject_chained() -> None:

    deps = get_func_args(injfunc)
    ctx = {"a": "foobar"}
    resolfunc = inject(injfunc, ctx, [])
    args = get_func_args(resolfunc)
    assert args != deps

    # print([a.name for a in deps])
    # print([a.name for a in args])

    ctx2 = {"c": 2}
    resolfunc2 = inject(resolfunc, ctx2, [])
    args2 = get_func_args(resolfunc2)
    # assert args != args2
    # print([a.name for a in args2])
