import unittest
from collections.abc import AsyncIterator
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from typemapping import get_func_args

from ctxinject.model import (
    ArgsInjectable,
    ConstrArgInject,
    Depends,
    DependsInject,
    Injectable,
    ModelFieldInject,
)
from ctxinject.sigcheck import (
    check_all_injectables,
    check_all_typed,
    check_depends_types,
    check_modefield_types,
    check_single_injectable,
    func_signature_check,
)


class MyEnum(Enum):
    VALID = 0
    INVALID = 1


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


def func3(arg1: Annotated[int, Depends(get_db)]) -> None:
    pass


def get_db2() -> None:
    pass


def func4(arg1: Annotated[str, Depends(get_db2)]) -> None:
    pass


def func5(arg: str = Depends(...)) -> str:
    return ""


def dep() -> int:
    pass


def func6(x: str = Depends(dep)) -> None:
    pass


class TestSigCheck(unittest.TestCase):

    def test_check_all_typed(self) -> None:
        errors = check_all_typed(func1_args)
        self.assertEqual(errors, [])
        errors = check_all_typed(get_func_args(func2))
        self.assertEqual(errors, ['Argument "arg2" error: has no type definition'])

    def test_check_all_injectable(self) -> None:
        errors = check_all_injectables(func1_args, [])
        self.assertEqual(errors, [])

        class MyPath(Path):
            pass

        def func2_inner(
            arg1: Annotated[UUID, 123, ConstrArgInject(...)],
            arg2: Annotated[datetime, ConstrArgInject(...)],
            arg3: Path,
            arg4: MyPath,
            arg5: AsyncIterator[MyPath],
            extra: AsyncIterator[Path],
            argn: datetime = ArgsInjectable(...),
            dep: Any = DependsInject(get_db),
        ) -> None:
            pass

        errors = check_all_injectables(
            get_func_args(func2_inner), [Path], AsyncIterator
        )
        self.assertEqual(errors, [])

        errors = check_all_injectables(get_func_args(func2_inner), [])
        self.assertEqual(len(errors), 4)
        self.assertTrue(all(["cannot be injected" in err for err in errors]))

    def test_model_field_ok(self) -> None:
        class Model:
            x: int

            def __init__(self, y: str) -> None:
                self.y = y

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
        ) -> None:
            pass

        errors = check_modefield_types(get_func_args(func))
        self.assertEqual(len(errors), 0)

    def test_model_field_type_mismatch(self) -> None:
        class Model:
            x: int

        def func(y: Annotated[int, ModelFieldInject(model=Model)]) -> None:
            pass

        errors = check_modefield_types(get_func_args(func))
        self.assertEqual(len(errors), 1)
        self.assertTrue(
            all(["but types does not match. Expected" in err for err in errors])
        )

    def test_model_field_not_allowed(self) -> None:
        class Model:
            x: int

        def func(x: Annotated[int, ModelFieldInject(model=Model)]) -> None:
            pass

        errors = check_modefield_types(get_func_args(func), [Model])
        self.assertEqual(len(errors), 0)

        errors = check_modefield_types(get_func_args(func), [])
        self.assertEqual(len(errors), 1)
        self.assertTrue(
            all(
                [
                    "has ModelFieldInject but type is not allowed. Allowed:" in err
                    for err in errors
                ]
            )
        )
        errors = check_modefield_types(get_func_args(func), [str, int])
        self.assertEqual(len(errors), 1)
        self.assertTrue(
            all(
                [
                    "has ModelFieldInject but type is not allowed. Allowed:" in err
                    for err in errors
                ]
            )
        )

    def test_invalid_modelfield(self) -> None:
        def func(a: Annotated[str, ModelFieldInject(model=123)]) -> str:
            return a

        errors = check_modefield_types(get_func_args(func))
        self.assertEqual(len(errors), 1)
        self.assertTrue(all([" field should be a type, but" in err for err in errors]))

    def test_model_field_none(self) -> None:

        def func_model_none(none_model: str = ModelFieldInject(None)) -> None:
            pass

        errors = check_modefield_types(get_func_args(func_model_none))
        self.assertEqual(len(errors), 1)

    def test_depends_type(self) -> None:
        self.assertEqual(len(check_depends_types(func1_args)), 0)

        for f in [func3, func4, func5, func6]:
            errors = check_depends_types(get_func_args(f))
            self.assertEqual(len(errors), 1)
            self.assertTrue(all(["Depends" in err for err in errors]))

    def test_multiple_injectables_error(self) -> None:
        class MyInject1(ArgsInjectable):
            pass

        class MyInject2(ArgsInjectable):
            pass

        def func(x: Annotated[str, MyInject1(...), MyInject2(...)]) -> None:
            pass

        errors = check_single_injectable(get_func_args(func))
        self.assertEqual(len(errors), 1)
        self.assertTrue(all(["has multiple injectables" in err for err in errors]))

    def test_func_signature_check_success(self) -> None:
        def valid_func(
            arg1: Annotated[UUID, 123, ConstrArgInject(...)],
            arg2: Annotated[datetime, ConstrArgInject(...)],
            arg3: str = ConstrArgInject(..., min_length=3),
            arg4: MyEnum = ConstrArgInject(...),
            arg5: list[str] = ConstrArgInject(..., max_length=5),
        ) -> None:
            return None

        # Should pass without exception
        self.assertEqual(len(func_signature_check(valid_func, [])), 0)

    def test_func_signature_check_untyped(self) -> None:
        def untyped_func(arg1, arg2: int) -> None:
            pass

        errors = func_signature_check(untyped_func, [])
        self.assertEqual(len(errors), 2)

    def test_func_signature_check_uninjectable(self) -> None:
        def uninjectable_func(arg1: Path) -> None:
            pass

        errors = func_signature_check(uninjectable_func, [])
        self.assertEqual(len(errors), 1)
        self.assertTrue(all(["cannot be injected" in err for err in errors]))

    def test_func_signature_check_invalid_model(self) -> None:
        def invalid_model_field_func(
            arg: Annotated[str, ModelFieldInject(model=123)],
        ) -> None:
            pass

        errors = func_signature_check(invalid_model_field_func, [])
        self.assertEqual(len(errors), 1)
        self.assertTrue(all([" field should be a type, but" in err for err in errors]))

    def test_func_signature_check_bad_depends(self) -> None:
        def get_dep():
            return "value"

        def bad_dep_func(arg: Annotated[str, Depends(get_dep)]) -> None:
            pass

        errors = func_signature_check(bad_dep_func, [])
        self.assertEqual(len(errors), 1)
        self.assertTrue(
            all(["Depends Return should a be type, but " in err for err in errors])
        )

    def test_func_signature_check_conflicting_injectables(self) -> None:
        def bad_multiple_inject_func(
            arg: Annotated[str, ConstrArgInject(...), ModelFieldInject(model=str)],
        ) -> None:
            pass

        errors = func_signature_check(bad_multiple_inject_func, [])
        self.assertEqual(len(errors), 1)
        self.assertTrue(all(["has multiple injectables:" in err for err in errors]))

    def test_multiple_error(self) -> None:
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
            arg7: str = Depends("foobar"),
            arg8=Depends(dep1),
            arg9: str = Depends(dep1),
            arg10: str = Depends(dep2),
        ) -> None:
            return

        errors = func_signature_check(multiple_bad, [], bt_default_fallback=False)
        self.assertEqual(len(errors), 10)

    def test_model_cast1(self) -> None:
        class Model:
            x: str

        def func(arg: datetime = ModelFieldInject(model=Model, field="x")) -> int:
            return 42

        errors = check_modefield_types(get_func_args(func), type_cast=[(str, datetime)])
        self.assertEqual(len(errors), 0)

    def test_model_cast1(self) -> None:

        class Model:
            x: str

        def func(arg: UUID = ModelFieldInject(model=Model, field="x")) -> int:
            return 42

        errors = check_modefield_types(get_func_args(func), type_cast=[(str, UUID)])
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
