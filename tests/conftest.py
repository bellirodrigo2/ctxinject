from typing import Annotated, Any, Callable, Mapping, Optional, Union

import pytest

from ctxinject.model import Injectable


def func_mt() -> None:
    pass


def func_simple(arg1: str, arg2: int) -> None:
    pass


def func_def(arg1: str = "foobar", arg2: int = 12, arg3=True, arg4=None) -> None:  # type: ignore
    pass


def func_ann(
    arg1: Annotated[str, "meta1"],
    arg2: Annotated[int, "meta1", 2],
    arg3: Annotated[list[str], "meta1", 2, True],
    arg4: Annotated[dict[str, Any], "meta1", 2, True] = {"foo": "bar"},
) -> None:
    pass


def func_mix(arg1, arg2: Annotated[str, "meta1"], arg3: str, arg4="foobar") -> None:
    pass


@pytest.fixture
def funcsmap() -> Mapping[str, Callable[..., Any]]:

    funcs_map: dict[str, Callable[..., Any]] = {
        "mt": func_mt,
        "simple": func_simple,
        "def": func_def,
        "ann": func_ann,
        "mix": func_mix,
    }

    return funcs_map


def func_annotated_none(
    arg1: Annotated[Optional[str], "meta"],
    arg2: Annotated[Optional[int], "meta2"] = None,
) -> None:
    pass


def func_union(
    arg1: Union[int, str],
    arg2: Optional[float] = None,
) -> None:
    pass


def func_varargs(*args: int, **kwargs: str) -> None:
    pass


def func_kwonly(*, arg1: int, arg2: str = "default") -> None:
    pass


class MyClass:
    pass


def func_forward(arg: "MyClass") -> None:
    pass


def func_none_default(arg: Optional[str] = None) -> None:
    pass


@pytest.fixture
def funcsmap_extended() -> Mapping[str, Callable[..., Any]]:
    return {
        "annotated_none": func_annotated_none,
        "union": func_union,
        "varargs": func_varargs,
        "kwonly": func_kwonly,
        "forward": func_forward,
        "none_default": func_none_default,
    }


# ----------- INJECT


def inj_func(
    arg: str, arg_ann: Annotated[str, Injectable(...)], arg_dep: str = Injectable(...)  # type: ignore
):
    pass


@pytest.fixture
def injfunc():
    return inj_func
