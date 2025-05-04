from datetime import datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import pytest

from ctxinject.mapfunction import get_func_args
from ctxinject.model import ArgsInjectable, DependsInject, UnInjectableError
from ctxinject.validate import (
    ConstrArgInject,
    Depends,
    check_all_injectables,
    check_all_typed,
    check_depends_types,
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


def test_check_all_typed() -> None:

    check_all_typed(func1_args)

    with pytest.raises(TypeError):
        check_all_typed(get_func_args(func2))


def test_depends_type() -> None:

    check_depends_types(func1_args)

    with pytest.raises(TypeError):
        check_depends_types(get_func_args(func3))

    with pytest.raises(TypeError):
        check_depends_types(get_func_args(func4))


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
