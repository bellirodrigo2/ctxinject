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
    func_signature_validation,
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


def valid_func(
    arg1: Annotated[UUID, 123, ConstrArgInject(...)],
    arg2: Annotated[datetime, ConstrArgInject(...)],
    arg3: str = ConstrArgInject(..., min_length=3),
    arg4: MyEnum = ConstrArgInject(...),
    arg5: list[str] = ConstrArgInject(..., max_length=5),
) -> None:
    return None


def test_func_signature_validation_success() -> None:
    # Deve passar sem exceção
    func_signature_validation(valid_func, [])


def untyped_func(arg1, arg2: int) -> None:
    pass


def test_func_signature_validation_untyped() -> None:
    with pytest.raises(TypeError):
        func_signature_validation(untyped_func, [])


def uninjectable_func(arg1: Path) -> None:
    pass


def test_func_signature_validation_uninjectable() -> None:
    with pytest.raises(UnInjectableError):
        func_signature_validation(uninjectable_func, [])


def invalid_model_field_func(arg: Annotated[str, ModelFieldInject(model=123)]) -> None:
    pass


def test_func_signature_validation_invalid_model() -> None:
    with pytest.raises(InvalidInjectableDefinition):
        func_signature_validation(invalid_model_field_func, [])


def get_dep():
    return "value"


def bad_dep_func(arg: Annotated[str, Depends(get_dep)]) -> None:
    pass


def test_func_signature_validation_bad_depends() -> None:
    with pytest.raises(TypeError):
        func_signature_validation(bad_dep_func, [])


def bad_multiple_inject_func(
    arg: Annotated[str, ConstrArgInject(...), ModelFieldInject(model=str)],
) -> None:
    pass


def test_func_signature_validation_conflicting_injectables() -> None:
    with pytest.raises(Exception):  # Substituir pela exceção certa, se houver
        func_signature_validation(bad_multiple_inject_func, [])
