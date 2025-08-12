from typing import Iterable
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict as Dict_t, Tuple
from typing import List as List_t
from uuid import UUID

from typemapping import get_func_args
from typing_extensions import Annotated, AsyncIterator, Dict, List

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

    errors = check_all_injectables(get_func_args(func), [Model], {})
    assert len(errors) == 1

    errors = check_all_injectables(get_func_args(func), [Model], {"byname":str})
    assert errors == []


def test_byname_extended() -> None:
    def func(
        byname: str,
        list_arg:List[str],
        iter_arg: Iterable[str],
        time:datetime
    ) -> int:
        return 42
    types_map = {
        "byname": str,
        "list_arg": List[str],
        "iter_arg": Tuple[str],
        "time":str
    }
    errors = check_all_injectables(get_func_args(func), [], types_map,[validator_check])
    assert errors == []

def test_nested_depends_valid() -> None:
    """Test recursive dependency checking with valid nested dependencies."""
    
    def inner_dep() -> str:
        return "inner"
    
    def middle_dep(dep: str = DependsInject(inner_dep)) -> int:
        return 42
    
    def outer_func(value: int = DependsInject(middle_dep)) -> str:
        return str(value)
    
    errors = func_signature_check(outer_func)
    assert errors == []


def test_nested_depends_invalid_inner() -> None:
    """Test recursive dependency checking catches errors in nested dependencies."""
    
    def bad_inner_dep():  # No return type
        return "inner"
    
    def middle_dep(dep: str = DependsInject(bad_inner_dep)) -> int:
        return 42
    
    def outer_func(value: int = DependsInject(middle_dep)) -> str:
        return str(value)
    
    errors = func_signature_check(outer_func)
    assert len(errors) == 1
    assert "Nested Depends Error" in errors[0]
    assert "Depends Return should a be type" in errors[0]


def test_nested_depends_type_mismatch() -> None:
    """Test recursive dependency checking catches type mismatches in nested deps."""
    
    def inner_dep() -> int:  # Returns int
        return 42
    
    def middle_dep(dep: str = DependsInject(inner_dep)) -> str:  # Expects str
        return "test"
    
    def outer_func(value: str = DependsInject(middle_dep)) -> str:
        return value
    
    errors = func_signature_check(outer_func)
    assert len(errors) == 1
    assert "Nested Depends Error" in errors[0]
    # Check that the type mismatch error is reported somewhere in the nested error
    assert 'return type should be "<class \'str\'>"' in errors[0] and '"<class \'int\'>"' in errors[0]


def test_deeply_nested_depends() -> None:
    """Test recursive checking works for multiple levels of nesting."""
    
    def level3_dep() -> str:
        return "level3"
    
    def level2_dep(dep3: str = DependsInject(level3_dep)) -> int:
        return len(dep3)
    
    def level1_dep(dep2: int = DependsInject(level2_dep)) -> bool:
        return dep2 > 0
    
    def root_func(dep1: bool = DependsInject(level1_dep)) -> str:
        return str(dep1)
    
    errors = func_signature_check(root_func)
    assert errors == []


def test_deeply_nested_depends_with_error() -> None:
    """Test recursive checking catches errors deep in the dependency chain."""
    
    def level3_dep():  # Missing return type
        return "level3"
    
    def level2_dep(dep3: str = DependsInject(level3_dep)) -> int:
        return len(dep3)
    
    def level1_dep(dep2: int = DependsInject(level2_dep)) -> bool:
        return dep2 > 0
    
    def root_func(dep1: bool = DependsInject(level1_dep)) -> str:
        return str(dep1)
    
    errors = func_signature_check(root_func)
    assert len(errors) == 1
    assert "Nested Depends Error" in errors[0]


def test_nested_depends_with_mixed_valid_invalid() -> None:
    """Test function with multiple nested deps where some are valid, some invalid."""
    
    def valid_dep() -> str:
        return "valid"
    
    def invalid_dep():  # No return type
        return "invalid"
    
    def middle_dep1(dep: str = DependsInject(valid_dep)) -> int:
        return 1
    
    def middle_dep2(dep: str = DependsInject(invalid_dep)) -> int:
        return 2
    
    def outer_func(
        val1: int = DependsInject(middle_dep1),
        val2: int = DependsInject(middle_dep2)
    ) -> str:
        return str(val1 + val2)
    
    errors = func_signature_check(outer_func)
    assert len(errors) == 1
    assert "val2" in errors[0]
    assert "Nested Depends Error" in errors[0]


def test_nested_depends_with_model_injection() -> None:
    """Test nested dependencies that use model field injection."""
    
    class Config:
        database_url: str = "sqlite://test.db"
    
    def get_config_value(url: str = ModelFieldInject(Config, "database_url")) -> str:
        return url
    
    def create_connection(config: str = DependsInject(get_config_value)) -> bool:
        return True
    
    def service_func(connected: bool = DependsInject(create_connection)) -> str:
        return "connected" if connected else "disconnected"
    
    errors = func_signature_check(service_func, modeltype=[Config])
    assert errors == [], f"Expected no errors but got: {errors}"


def test_nested_depends_with_invalid_model_injection() -> None:
    """Test nested dependencies with invalid model field injection."""
    
    class Config:
        database_url: str = "sqlite://test.db"
    
    def get_bad_config(url: int = ModelFieldInject(Config, "database_url")) -> int:  # Type mismatch
        return 42
    
    def create_connection(config: int = DependsInject(get_bad_config)) -> bool:
        return True
    
    def service_func(connected: bool = DependsInject(create_connection)) -> str:
        return "connected" if connected else "disconnected"
    
    errors = func_signature_check(service_func, modeltype=[Config])
    assert len(errors) == 1
    assert "Nested Depends Error" in errors[0]
    assert "types does not match" in errors[0]


def test_nested_depends_multiple_errors_in_chain() -> None:
    """Test that all errors in a nested dependency chain are reported."""
    
    def bad_dep1():  # No return type
        return "test"
    
    def bad_dep2(untyped_param) -> str:  # Untyped parameter
        return "test"
    
    def middle_dep1(dep: str = DependsInject(bad_dep1)) -> int:
        return 1
    
    def middle_dep2(dep: str = DependsInject(bad_dep2)) -> int:
        return 2
    
    def outer_func(
        val1: int = DependsInject(middle_dep1),
        val2: int = DependsInject(middle_dep2)
    ) -> str:
        return str(val1 + val2)
    
    errors = func_signature_check(outer_func)
    assert len(errors) == 2
    assert all("Nested Depends Error" in error for error in errors)


def test_check_depends_types_direct() -> None:
    """Test check_depends_types function directly (now only handles type validation)."""
    
    def valid_dep() -> str:
        return "test"
    
    def invalid_return_type() -> int:  # Returns int but param expects str
        return 42
    
    def no_return_type():  # No return type annotation
        return "test"
    
    def test_func(
        valid_param: str = DependsInject(valid_dep),
        type_mismatch_param: str = DependsInject(invalid_return_type), 
        no_type_param: str = DependsInject(no_return_type)
    ) -> None:
        pass
    
    args = get_func_args(test_func)
    
    # Test check_depends_types directly - it now only handles type validation
    errors = check_depends_types(args)
    
    assert len(errors) == 2  # Should have 2 errors: type mismatch + no return type
    
    # Check for type mismatch error
    type_errors = [err for err in errors if "type_mismatch_param" in err]
    assert len(type_errors) == 1
    assert 'return type should be' in type_errors[0]
    
    # Check for no return type error  
    no_type_errors = [err for err in errors if "no_type_param" in err]
    assert len(no_type_errors) == 1
    assert "Depends Return should a be type, but None was found" in no_type_errors[0]


def test_check_circular_dependencies_direct() -> None:
    """Test check_circular_dependencies function directly."""
    
    def circular_a(b_val: str = DependsInject(lambda: None)) -> str:
        return b_val
    
    def circular_b(a_val: str = DependsInject(circular_a)) -> str:
        return a_val
    
    # Create circular reference
    circular_a.__defaults__ = (DependsInject(circular_b),)
    
    def test_func(value: str = DependsInject(circular_a)) -> None:
        pass
    
    args = get_func_args(test_func)
    
    # Import the function to test it directly
    from ctxinject.sigcheck import check_circular_dependencies
    errors = check_circular_dependencies(args)
    
    assert len(errors) >= 1
    assert any("Circular dependency detected" in err for err in errors)


def test_circular_dependency_detection() -> None:
    """Test detection of circular dependencies between functions."""
    
    # Create circular dependency: A -> B -> A
    def dep_a(b_val: str = DependsInject(lambda: None)) -> str:  # Will be set to dep_b
        return b_val
    
    def dep_b(a_val: str = DependsInject(dep_a)) -> str:
        return a_val
    
    # Manually create the circular reference
    dep_a.__defaults__ = (DependsInject(dep_b),)
    
    def test_func(value: str = DependsInject(dep_a)) -> None:
        pass
    
    errors = func_signature_check(test_func)
    assert len(errors) >= 1
    assert any("Circular dependency detected" in error for error in errors)


def test_self_circular_dependency() -> None:
    """Test detection of self-referencing function."""
    
    def self_dep(self_val: str = DependsInject(lambda: None)) -> str:
        return self_val
    
    # Make it depend on itself
    self_dep.__defaults__ = (DependsInject(self_dep),)
    
    def test_func(value: str = DependsInject(self_dep)) -> None:
        pass
    
    errors = func_signature_check(test_func)
    assert len(errors) >= 1
    assert any("Circular dependency detected" in error for error in errors)


def test_three_way_circular_dependency() -> None:
    """Test detection of A -> B -> C -> A circular dependency."""
    
    def func_a(c_val: str = DependsInject(lambda: None)) -> str:
        return c_val
    
    def func_b(a_val: str = DependsInject(func_a)) -> str:
        return a_val
    
    def func_c(b_val: str = DependsInject(func_b)) -> str:
        return b_val
    
    # Create circular reference
    func_a.__defaults__ = (DependsInject(func_c),)
    
    def test_func(value: str = DependsInject(func_a)) -> None:
        pass
    
    errors = func_signature_check(test_func)
    assert len(errors) >= 1
    assert any("Circular dependency detected" in error for error in errors)


def test_deep_circular_dependency() -> None:
    """Test detection of deep circular dependencies."""
    
    def level_1(val: str = DependsInject(lambda: None)) -> str:
        return val
    
    def level_2(l1_val: str = DependsInject(level_1)) -> str:
        return l1_val
    
    def level_3(l2_val: str = DependsInject(level_2)) -> str:
        return l2_val
    
    def level_4(l3_val: str = DependsInject(level_3)) -> str:
        return l3_val
    
    def level_5(l4_val: str = DependsInject(level_4)) -> str:
        return l4_val
    
    # Create circular reference at the end of a long chain
    level_1.__defaults__ = (DependsInject(level_5),)
    
    def test_func(value: str = DependsInject(level_1)) -> None:
        pass
    
    errors = func_signature_check(test_func)
    assert len(errors) >= 1
    assert any("Circular dependency detected" in error for error in errors)


def test_multiple_params_one_circular() -> None:
    """Test function with multiple parameters where only one has circular dependency."""
    
    def valid_dep() -> int:
        return 42
    
    def circular_a(b_val: str = DependsInject(lambda: None)) -> str:
        return b_val
    
    def circular_b(a_val: str = DependsInject(circular_a)) -> str:
        return a_val
    
    circular_a.__defaults__ = (DependsInject(circular_b),)
    
    def test_func(
        valid_param: int = DependsInject(valid_dep),
        circular_param: str = DependsInject(circular_a)
    ) -> None:
        pass
    
    errors = func_signature_check(test_func)
    assert len(errors) >= 1
    circular_errors = [err for err in errors if "circular_param" in err and "Circular dependency detected" in err]
    assert len(circular_errors) >= 1


def test_shared_dependency_no_false_positive() -> None:
    """Test that shared dependencies don't cause false circular detection."""
    
    def shared_service() -> str:
        return "shared"
    
    def service_a(shared: str = DependsInject(shared_service)) -> str:
        return f"A:{shared}"
    
    def service_b(shared: str = DependsInject(shared_service)) -> str:
        return f"B:{shared}"
    
    def test_func(
        a_val: str = DependsInject(service_a),
        b_val: str = DependsInject(service_b)
    ) -> None:
        pass
    
    # This should NOT have any circular dependency errors
    errors = func_signature_check(test_func)
    circular_errors = [err for err in errors if "Circular dependency detected" in err]
    assert len(circular_errors) == 0, f"False positive circular detection: {circular_errors}"


def test_diamond_dependency_pattern() -> None:
    """Test diamond dependency pattern (should be valid, no false positive)."""
    
    def base_service() -> str:
        return "base"
    
    def left_service(base: str = DependsInject(base_service)) -> str:
        return f"left:{base}"
    
    def right_service(base: str = DependsInject(base_service)) -> str:
        return f"right:{base}"
    
    def top_service(
        left: str = DependsInject(left_service),
        right: str = DependsInject(right_service)
    ) -> str:
        return f"{left}+{right}"
    
    def test_func(result: str = DependsInject(top_service)) -> None:
        pass
    
    # Diamond pattern should be valid - no circular errors
    errors = func_signature_check(test_func)
    circular_errors = [err for err in errors if "Circular dependency detected" in err]
    assert len(circular_errors) == 0, f"False positive in diamond pattern: {circular_errors}"
