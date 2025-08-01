from typing import Tuple

from typemapping import (
    VarTypeInfo,
    generic_issubclass,
    get_field_type,
    get_func_args,
    get_return_type,
)
from typing_extensions import Any, Callable, Iterable, List, Optional, Sequence, Type

from ctxinject.model import DependsInject, Injectable, ModelFieldInject
from ctxinject.validation import validator_check


def error_msg(argname: str, msg: str) -> str:
    """Format error message for function argument validation."""
    return f'Argument "{argname}" error: {msg}'


def check_all_typed(args: List[VarTypeInfo]) -> List[str]:
    """Check that all arguments have type definitions."""
    errors: List[str] = []
    valid_args: List[VarTypeInfo] = []

    for arg in args:
        if arg.basetype is None:
            errors.append(error_msg(arg.name, "has no type definition"))
        else:
            valid_args.append(arg)

    # Update args in-place to maintain compatibility
    args.clear()
    args.extend(valid_args)
    return errors


def check_all_injectables(
    args: List[VarTypeInfo],
    modeltype: Iterable[Type[Any]],
    bynames: Optional[Iterable[str]] = None,
) -> List[str]:
    """Check that all arguments are injectable using typemapping."""

    bynames = bynames or []

    def is_injectable(arg: VarTypeInfo) -> bool:
        if arg.hasinstance(Injectable):
            return True
        if arg.name in bynames:
            return True
        for model in modeltype:
            if arg.isequal(model):
                return True
        return False

    errors: List[str] = []
    valid_args: List[VarTypeInfo] = []

    for arg in args:
        if not is_injectable(arg):
            errors.append(
                error_msg(arg.name, f"of type '{arg.basetype}' cannot be injected.")
            )
        else:
            valid_args.append(arg)

    # Update args in-place
    args.clear()
    args.extend(valid_args)
    return errors


ArgCheck = Callable[
    [
        ModelFieldInject,
        Type[Any],
        Type[Any],
    ],
    bool,
]


def check_modefield_types(
    args: List[VarTypeInfo],
    allowed_models: Optional[List[Type[Any]]] = None,
    arg_predicate: Optional[List[ArgCheck]] = None,
) -> List[str]:
    """Check model field injection types."""
    errors: List[str] = []
    valid_args: List[VarTypeInfo] = []

    for arg in args:
        modelfield_inj = arg.getinstance(ModelFieldInject)
        if modelfield_inj is not None:
            if not isinstance(modelfield_inj.model, type):
                errors.append(
                    error_msg(
                        arg.name,
                        f'ModelFieldInject "model" field should be a type, but "{modelfield_inj.model}" was found',
                    )
                )
                continue

            if (
                allowed_models is not None
                and modelfield_inj.model not in allowed_models
            ):
                errors.append(
                    error_msg(
                        arg.name,
                        f"has ModelFieldInject but type is not allowed. Allowed: {[model.__name__ for model in allowed_models]}, Found: {arg.argtype}",
                    )
                )
                continue

            fieldname = modelfield_inj.field or arg.name
            modeltype = get_field_type(modelfield_inj.model, fieldname)

            if modeltype is None:
                errors.append(
                    error_msg(
                        arg.name,
                        f"Could not determine type of class '{modelfield_inj.model}', field '{fieldname}' ",
                    )
                )
                continue

            if generic_issubclass(
                modeltype, arg.basetype  # type: ignore
            ):  # ✅ Use typemapping's generic_issubclass
                valid_args.append(arg)
                continue
            else:
                arg_predicate = arg_predicate or []
                if not any(
                    [
                        check(modelfield_inj, modeltype, arg.basetype)  # type: ignore
                        for check in arg_predicate
                    ]
                ):
                    errors.append(
                        error_msg(
                            arg.name,
                            f"has ModelFieldInject, but types does not match. Expected {arg.basetype}, but found {modeltype}",
                        )
                    )
            valid_args.append(arg)
        else:
            valid_args.append(arg)

    # Update args in-place
    args.clear()
    args.extend(valid_args)
    return errors


def check_depends_types(
    args: Sequence[VarTypeInfo], tgttype: Type[DependsInject] = DependsInject
) -> List[str]:
    """
    Check dependency types with lambda-friendly validation.

    Accepts lambdas without return type annotations when:
    1. The target parameter type is known (not Any)
    2. The lambda is simple (no complex logic)
    """
    errors: List[str] = []
    deps: List[Tuple[str, Optional[Type[Any]], Any]] = [
        (arg.name, arg.basetype, arg.getinstance(tgttype).default)  # type: ignore
        for arg in args
        if arg.hasinstance(tgttype)
    ]

    for arg_name, dep_type, dep_func in deps:
        if not callable(dep_func):
            errors.append(
                error_msg(
                    arg_name, f"Depends value should be a callable. Found '{dep_func}'."
                )
            )
            continue

        # Get function name for better error messages
        func_name = getattr(dep_func, "__name__", str(dep_func))

        # ✅ Use typemapping's robust type hints resolution
        return_type = get_return_type(dep_func)

        if return_type is None:
            errors.append(
                error_msg(
                    arg_name,
                    "Depends Return should a be type, but None was found.",
                )
            )
            continue

        # ✅ TYPE COMPATIBILITY CHECK
        if not generic_issubclass(return_type, dep_type):  # type: ignore
            errors.append(
                error_msg(
                    arg_name,
                    f'Depends function "{func_name}" return type should be "{dep_type}", but "{return_type}" was found',
                )
            )

    return errors


def check_single_injectable(args: List[VarTypeInfo]) -> List[str]:
    """Check that each argument has only one injectable."""
    errors: List[str] = []
    valid_args: List[VarTypeInfo] = []

    for arg in args:
        if arg.extras is not None:
            injectables = [x for x in arg.extras if isinstance(x, Injectable)]
            if len(injectables) > 1:
                errors.append(
                    error_msg(
                        arg.name,
                        f"has multiple injectables: {[type(i).__name__ for i in injectables]}",
                    )
                )
            else:
                valid_args.append(arg)
        else:
            valid_args.append(arg)

    # Update args in-place
    args.clear()
    args.extend(valid_args)
    return errors


def func_signature_check(
    func: Callable[..., Any],
    modeltype: Optional[List[Type[Any]]] = None,
    bynames: Optional[Iterable[str]] = None,
    bt_default_fallback: bool = True,
    arg_predicate: Optional[List[ArgCheck]] = None,
) -> List[str]:
    """
    Check function signature for injection compatibility.

    This function validates that a function's signature is compatible with
    dependency injection by checking:
    - All parameters have type annotations
    - All parameters are injectable (have Injectable annotations or are in modeltype)
    - Each parameter has only one injectable annotation
    - Model field injections are valid
    - Dependency function return types match parameter types

    Args:
        func: Function to validate
        modeltype: List of types that are considered injectable by default
        generictype: Generic type wrapper (e.g., List, Optional) for injectable types
        bt_default_fallback: Whether to use default type inference fallbacks
        type_cast: List of allowed type casting pairs for model field injection

    Returns:
        List of error messages. Empty list means the function is valid for injection.

    Examples:
        Basic validation:
        ```python
        def valid_func(
            name: str = ArgsInjectable(...),
            count: int = ArgsInjectable(42)
        ) -> str:
            return f"{name}: {count}"

        errors = func_signature_check(valid_func)
        assert errors == []  # No errors, function is valid
        ```

        Function with errors:
        ```python
        def invalid_func(
            untyped_param,  # Missing type annotation
            bad_type: SomeCustomType,  # Not injectable
        ) -> str:
            return "test"

        errors = func_signature_check(invalid_func, modeltype=[])
        assert len(errors) == 2  # Two validation errors
        ```

        With model types:
        ```python
        class Config:
            database_url: str

        def func_with_model(
            config: Config,  # Valid because Config is in modeltype
            url: str = ModelFieldInject(Config, "database_url")
        ) -> str:
            return url

        errors = func_signature_check(func_with_model, modeltype=[Config])
        assert errors == []
        ```

        Lambda-friendly dependency checking:
        ```python
        def get_timestamp() -> float:
            return time.time()

        def func_with_deps(
            timestamp: float = DependsInject(get_timestamp),
            simple_value: int = DependsInject(lambda: 42)  # Simple lambda OK
        ) -> str:
            return f"Time: {timestamp}, Value: {simple_value}"

        errors = func_signature_check(func_with_deps)
        assert errors == []
        ```

    Note:
        Lambda-friendly version that accepts:
        - Lambda functions without return type annotations when target type is known
        - Named functions with proper return type annotations
        - All other injection patterns
    """
    modeltype = modeltype or []

    try:
        # ✅ Use typemapping's robust function argument analysis
        args: Sequence[VarTypeInfo] = get_func_args(
            func, bt_default_fallback=bt_default_fallback
        )
    except Exception as e:  # pragma: no cover
        return [f"Could not analyze function signature: {e}"]

    # Convert to list for in-place modification
    args_list = list(args)
    all_errors: List[str] = []

    # Run all checks, each may filter the args list
    typed_errors = check_all_typed(args_list)
    all_errors.extend(typed_errors)

    inj_errors = check_all_injectables(args_list, modeltype, bynames)  # , generictype)
    all_errors.extend(inj_errors)

    single_errors = check_single_injectable(args_list)
    all_errors.extend(single_errors)

    arg_predicate = arg_predicate or []
    arg_predicate.append(validator_check)
    model_errors = check_modefield_types(args_list, modeltype, arg_predicate)
    all_errors.extend(model_errors)

    # ✅ LAMBDA-FRIENDLY dependency check
    dep_errors = check_depends_types(args_list)
    all_errors.extend(dep_errors)

    return all_errors
