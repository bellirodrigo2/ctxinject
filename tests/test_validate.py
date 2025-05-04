from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Callable
from uuid import UUID

import pytest

from ctxinject.mapfunction import get_func_args
from ctxinject.model import (
    ArgsInjectable,
    DependsInject,
    InvalidInjectableDefinition,
    InvalidModelFieldType,
    ModelFieldInject,
    UnInjectableError,
)
from ctxinject.validate import (
    ConstrArgInject,
    Depends,
    check_all_injectables,
    check_all_typed,
    check_depends_types,
    check_modefield_types,
)
from tests.test_constrained import MyEnum


def get_db() -> str:
    return "sqlite://"


def func1(
    arg1: Annotated[UUID, 123, ConstrArgInject(...)],
    arg2: Annotated[datetime, ConstrArgInject(...)],
    dep1: Annotated[str, Depends(get_db)],
    arg3: str = ConstrArgInject(..., min_length=3),
    arg4: MyEnum = ConstrArgInject(...),
    arg5: list[str] = ConstrArgInject(..., max_length=5),
    dep2: str = Depends(get_db),
) -> None:
    return None


func1_args = get_func_args(func1)


def func2(arg1: str, arg2) -> None:
    return None


def func3(arg1: Annotated[int, Depends(get_db)]) -> None: ...


def get_db2() -> None: ...


def func4(arg1: Annotated[str, Depends(get_db2)]) -> None: ...


def func5(arg: str = Depends(...)) -> str:
    return ""


def dep() -> int: ...
def func6(x: str = Depends(dep)) -> None: ...


def test_check_all_typed() -> None:

    check_all_typed(func1_args)

    with pytest.raises(TypeError):
        check_all_typed(get_func_args(func2))


def test_check_all_injectable() -> None:

    check_all_injectables(func1_args, [])

    def func2(
        arg1: Annotated[UUID, 123, ConstrArgInject(...)],
        arg2: Annotated[datetime, ConstrArgInject(...)],
        arg3: Path,
        argn: datetime = ArgsInjectable(...),
        dep: Any = DependsInject(get_db),
    ) -> None: ...

    check_all_injectables(get_func_args(func2), [Path])

    with pytest.raises(UnInjectableError):
        check_all_injectables(get_func_args(func2), [])


def test_model_field_type_mismatch() -> None:
    class Model:
        x: int

    def func(y: Annotated[int, ModelFieldInject(model=Model)]) -> None: ...

    with pytest.raises(InvalidModelFieldType):
        check_modefield_types(get_func_args(func))


def test_invalid_modelfield() -> None:

    def func(a: Annotated[str, ModelFieldInject(model=123)]) -> str:
        return a

    with pytest.raises(InvalidInjectableDefinition):
        check_modefield_types(get_func_args(func))


@pytest.mark.parametrize(
    "func",
    [
        lambda: func3,
        lambda: func4,
        lambda: func5,
        lambda: func6,
    ],
)
def test_depends_type(func: Callable[..., Any]) -> None:

    check_depends_types(func1_args)

    with pytest.raises(TypeError):
        check_depends_types(get_func_args(func()))


def test_multiple_injectables_error() -> None:
    class MyInject1(ArgsInjectable): ...

    class MyInject2(ArgsInjectable): ...

    def func(x: Annotated[str, MyInject1(...), MyInject2(...)]) -> None: ...

    from ctxinject.validate import check_single_injectable

    with pytest.raises(TypeError, match="multiple injectables"):
        check_single_injectable(get_func_args(func))
