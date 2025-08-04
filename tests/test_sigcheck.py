import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict as Dict_t
from typing import List as List_t
from uuid import UUID

from typemapping import get_func_args
from typing_extensions import Annotated, Any, AsyncIterator, Dict, List

from ctxinject.model import ArgsInjectable, DependsInject, Injectable, ModelFieldInject
from ctxinject.sigcheck import (
    check_all_injectables,
    check_all_typed,
    check_depends_types,
    check_modefield_types,
    check_single_injectable,
    func_signature_check,
)
from ctxinject.validation import validator_check

TEST_TYPE = sys.version_info >= (3, 9)


class MyEnum(Enum):
    VALID = 0
    INVALID = 1


def get_db() -> Annotated[str, "db_test"]:
    return "sqlite://"


def func1(
    arg1: Annotated[UUID, 123, ArgsInjectable(...)],
    arg2: Annotated[datetime, ArgsInjectable(...)],
    dep1: Annotated[str, DependsInject(get_db)],
    arg3: str = ArgsInjectable(..., min_length=3),
    arg4: MyEnum = ArgsInjectable(...),
    arg5: List[str] = ArgsInjectable(..., max_length=5),
    dep2: str = DependsInject(get_db),
) -> Annotated[str, "foobar"]:
    return "None"


func1_args = get_func_args(func1)


def func2(arg1: str, arg2) -> Annotated[str, "teste"]:
    return "None"


def func3(arg1: Annotated[int, DependsInject(get_db)]) -> None:
    pass


def get_db2() -> None:
    pass


def func4(arg1: Annotated[str, DependsInject(get_db2)]) -> None:
    pass


def func5(arg: str = DependsInject(...)) -> str:
    return ""


def dep() -> Annotated[int, 123]:
    pass


def func6(x: str = DependsInject(dep)) -> None:
    pass


def test_check_all_typed() -> None:
    assert check_all_typed(func1_args) == []
    assert check_all_typed(get_func_args(func2)) == [
        'Argument "arg2" error: has no type definition'
    ]


def test_check_all_injectable() -> None:
    assert check_all_injectables(func1_args, []) == []

    class MyPath(Path):
        pass

    def func2_inner(
        arg1: Annotated[UUID, 123, ArgsInjectable(...)],
        arg2: Annotated[datetime, ArgsInjectable(...)],
        arg3: Path,
        arg4: MyPath,
        arg5: AsyncIterator[MyPath],
        extra: AsyncIterator[Path],
        argn: datetime = ArgsInjectable(...),
        dep: str = DependsInject(get_db),
    ) -> None:
        pass

    assert (
        check_all_injectables(
            get_func_args(func2_inner),
            [Path, AsyncIterator[Path]],
        )
        == []
    )

    assert func_signature_check(func2_inner, [Path, AsyncIterator[Path]]) == []

    errors = check_all_injectables(get_func_args(func2_inner), [])
    assert len(errors) == 4
    assert all("cannot be injected" in e for e in errors)


def test_model_field_ok() -> None:
    class Base: ...

    class Derived(Base): ...

    class Model:
        x: int
        a: List_t[str]
        b: Dict_t[str, str]
        d: Derived

        def __init__(self, y: str, c: Enum) -> None:
            self.y = y
            self.c = c

        @property
        def w(self) -> bool:
            return True

        def z(self) -> int:
            return 42

    def func(
        x: int = ModelFieldInject(Model),
        y: str = ModelFieldInject(Model),
        z: int = ModelFieldInject(Model),
        w: bool = ModelFieldInject(Model),
        a: List_t[str] = ModelFieldInject(Model),
        b: Dict_t[str, str] = ModelFieldInject(Model),
        c: Enum = ModelFieldInject(Model),
        f: Dict[str, str] = ModelFieldInject(Model, field="b"),
        d: Base = ModelFieldInject(Model),
        h: Derived = ModelFieldInject(Model, field="d"),
    ) -> None:
        pass

    assert check_modefield_types(get_func_args(func)) == []

    if TEST_TYPE:

        def func_2(b: Dict_t[str, str] = ModelFieldInject(Model)) -> None:
            pass

        assert check_modefield_types(get_func_args(func_2)) == []


def test_model_field_type_error() -> None:
    class Model:
        x: Dict_t[str, str]

    def func(x: Annotated[int, ModelFieldInject(model=Model)]) -> None:
        pass

    assert len(check_modefield_types(get_func_args(func))) == 1


def test_model_field_type_mismatch() -> None:
    class Model:
        x: int

    def func(y: Annotated[int, ModelFieldInject(model=Model)]) -> None:
        pass

    errors = check_modefield_types(get_func_args(func), allowed_models=[Model])
    assert len(errors) == 1
    assert all("Could not determine type of class " in e for e in errors)


def test_model_field_not_allowed() -> None:
    class Model:
        x: int

    def func(x: Annotated[int, ModelFieldInject(model=Model)]) -> None:
        pass

    assert check_modefield_types(get_func_args(func), [Model]) == []

    errors = check_modefield_types(get_func_args(func), [])
    assert len(errors) == 1
    assert all(
        "has ModelFieldInject but type is not allowed. Allowed:" in e for e in errors
    )

    errors = check_modefield_types(get_func_args(func), [str, int])
    assert len(errors) == 1


def test_invalid_modelfield() -> None:
    def func(a: Annotated[str, ModelFieldInject(model=123)]) -> str:
        return a

    errors = check_modefield_types(get_func_args(func))
    assert len(errors) == 1
    assert all(" field should be a type, but" in e for e in errors)


def test_model_field_none() -> None:
    def func_model_none(none_model: str = ModelFieldInject(None)) -> None:
        pass

    errors = check_modefield_types(get_func_args(func_model_none))
    assert len(errors) == 1


def test_depends_type() -> None:
    assert len(check_depends_types(func1_args)) == 0

    for f in [func3, func4, func5, func6]:
        errors = check_depends_types(get_func_args(f))
        assert len(errors) == 1
        assert all("Depends" in e for e in errors)


def test_multiple_injectables_error() -> None:
    class MyInject1(ArgsInjectable):
        pass

    class MyInject2(ArgsInjectable):
        pass

    def func(x: Annotated[str, MyInject1(...), MyInject2(...)]) -> None:
        pass

    errors = check_single_injectable(get_func_args(func))
    assert len(errors) == 1
    assert all("has multiple injectables" in e for e in errors)


def test_func_signature_check_success() -> None:
    def valid_func(
        arg1: Annotated[UUID, 123, ArgsInjectable(...)],
        arg2: Annotated[datetime, ArgsInjectable(...)],
        arg3: str = ArgsInjectable(..., min_length=3),
        arg4: MyEnum = ArgsInjectable(...),
        arg5: List[str] = ArgsInjectable(..., max_length=5),
    ) -> None:
        pass

    assert func_signature_check(valid_func, []) == []


def test_func_signature_check_untyped() -> None:
    def untyped_func(arg1, arg2: int) -> None:
        pass

    errors = func_signature_check(untyped_func, [])
    assert len(errors) == 2


def test_func_signature_check_uninjectable() -> None:
    def uninjectable_func(arg1: Path) -> None:
        pass

    errors = func_signature_check(uninjectable_func, [])
    assert len(errors) == 1
    assert all("cannot be injected" in e for e in errors)


def test_func_signature_check_invalid_model() -> None:
    def invalid_model_field_func(
        arg: Annotated[str, ModelFieldInject(model=123)],
    ) -> None:
        pass

    errors = func_signature_check(invalid_model_field_func, [])
    assert len(errors) == 1
    assert all(" field should be a type, but" in e for e in errors)


def test_func_signature_check_bad_depends() -> None:
    def get_dep():
        return "value"

    def bad_dep_func(arg: Annotated[str, DependsInject(get_dep)]) -> None:
        pass

    errors = func_signature_check(bad_dep_func, [])
    assert len(errors) == 1
    assert all("Depends Return should a be type, but " in e for e in errors)


def test_func_signature_check_conflicting_injectables() -> None:
    def bad_multiple_inject_func(
        arg: Annotated[str, ArgsInjectable(...), ModelFieldInject(model=str)],
    ) -> None:
        pass

    errors = func_signature_check(bad_multiple_inject_func, [])
    assert len(errors) == 1
    assert all("has multiple injectables:" in e for e in errors)


def test_multiple_error() -> None:
    class MyType:
        def __init__(self, x: str) -> None:
            self.x = x

    def dep1() -> None:
        pass

    def dep2() -> int:
        pass

    def multiple_bad(
        arg1,
        arg2: str,
        arg3: Annotated[str, Injectable(), Injectable()],
        arg4: str = ModelFieldInject(model="foobar"),
        arg5: bool = ModelFieldInject(model=MyType, field="x"),
        arg6: Path = ModelFieldInject(model=Path, field="is_dir"),
        arg7: str = DependsInject("foobar"),
        arg8=DependsInject(dep1),
        arg9: str = DependsInject(dep1),
        arg10: str = DependsInject(dep2),
    ) -> None:
        return

    errors = func_signature_check(multiple_bad, [], bt_default_fallback=False)
    assert len(errors) == 10


def test_model_cast1() -> None:
    class Model:
        x: str

    def func(arg: datetime = ModelFieldInject(model=Model, field="x")) -> int:
        return 42

    errors = check_modefield_types(get_func_args(func), arg_predicate=[validator_check])
    assert errors == []


def test_byname() -> None:
    class Model:
        x: str

    def func(
        byname: str, arg: datetime = ModelFieldInject(model=Model, field="x")
    ) -> int:
        return 42

    errors = check_all_injectables(get_func_args(func), [Model], [])
    assert len(errors) == 1

    errors = check_all_injectables(get_func_args(func), [Model], ["byname"])
    assert errors == []
