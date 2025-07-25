from typemapping import (
    VarTypeInfo,
    get_field_type,
    get_func_args,
    get_return_type,
    get_safe_type_hints,
    is_Annotated,
    is_equal_type,
    safe_issubclass,
)
from typing_extensions import (
    Annotated,
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    get_args,
    get_origin,
    get_type_hints,
)

from ctxinject.model import DependsInject, Injectable, ModelFieldInject


def error_msg(argname: str, msg: str) -> str:
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
    modeltype: Iterable[type[Any]],
    generictype: Optional[type[Any]] = None,
) -> List[str]:
    """Check that all arguments are injectable using typemapping."""

    def is_injectable(arg: VarTypeInfo, modeltype: Iterable[type[Any]]) -> bool:
        if arg.hasinstance(Injectable):
            return True
        for model in modeltype:
            # ✅ Use typemapping's robust type checking
            if arg.istype(model):
                return True
            elif generictype is not None and arg.origin is generictype:
                if len(arg.args) > 0 and isinstance(arg.args[0], type):
                    # ✅ Use typemapping's safe_issubclass
                    if safe_issubclass(arg.args[0], model):
                        return True
        return False

    errors: List[str] = []
    valid_args: List[VarTypeInfo] = []

    for arg in args:
        if not is_injectable(arg, modeltype):
            errors.append(
                error_msg(arg.name, f"of type '{arg.basetype}' cannot be injected.")
            )
        else:
            valid_args.append(arg)

    # Update args in-place
    args.clear()
    args.extend(valid_args)
    return errors


def check_modefield_types(
    args: List[VarTypeInfo],
    allowed_models: Optional[List[type[Any]]] = None,
    type_cast: Optional[List[Tuple[type[Any], Type[Any]]]] = None,
) -> List[str]:
    """Check model field injection types."""
    errors: List[str] = []
    valid_args: List[VarTypeInfo] = []
    type_cast = type_cast or []

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

            if allowed_models is not None:
                if len(allowed_models) == 0 or not any(
                    [
                        issubclass(modelfield_inj.model, model)
                        for model in allowed_models
                    ]
                ):
                    errors.append(
                        error_msg(
                            arg.name,
                            f"has ModelFieldInject but type is not allowed. Allowed: {[model.__name__ for model in allowed_models]}, Found: {arg.argtype}",
                        )
                    )
                    continue

            fieldname = modelfield_inj.field or arg.name
            argtype = get_field_type(modelfield_inj.model, fieldname)

            if argtype is None:
                errors.append(
                    error_msg(
                        arg.name,
                        f"Could not determine type of class '{modelfield_inj.model}', field '{fieldname}' ",
                    )
                )
                continue

            if (
                isinstance(arg.basetype, type)
                and isinstance(argtype, type)
                and safe_issubclass(
                    argtype, arg.basetype
                )  # ✅ Use typemapping's safe_issubclass
            ):
                valid_args.append(arg)
                continue

            # ✅ Use typemapping's robust type checking
            if not arg.istype(argtype):
                # Check both directions for type_cast
                if (argtype, arg.basetype) not in type_cast and (
                    arg.basetype,
                    argtype,
                ) not in type_cast:
                    errors.append(
                        error_msg(
                            arg.name,
                            f"has ModelFieldInject, but types does not match. Expected {argtype}, but found {arg.argtype}",
                        )
                    )
                    continue

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
    deps: list[tuple[str, Optional[type[Any]], Any]] = [
        (arg.name, arg.basetype, arg.getinstance(tgttype).default)
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

        # Try to get return type annotation using typemapping
        try:
            # ✅ Use typemapping's robust type hints resolution
            return_type = get_return_type(dep_func)

            # If typemapping couldn't determine it, try manual inspection
            if return_type is None:
                hints = get_safe_type_hints(dep_func)
                return_type = hints.get("return")

                # Handle Annotated return types
                if return_type is not None and is_Annotated(return_type):
                    return_type = get_args(return_type)[0]

        except Exception:
            # Fallback to basic get_type_hints
            try:
                return_type = get_type_hints(dep_func).get("return")
                if get_origin(return_type) is Annotated:
                    return_type = get_args(return_type)[0]
            except Exception:
                return_type = None

        # ✅ LAMBDA-FRIENDLY LOGIC (only for simple lambdas)
        if return_type is None:
            # No return type annotation found

            if func_name == "<lambda>":
                # Check if lambda has arguments
                try:
                    import inspect

                    sig = inspect.signature(dep_func)
                    has_args = len(sig.parameters) > 0
                except Exception:
                    has_args = True  # Assume complex if can't analyze

                if has_args:
                    # Lambda with arguments - require proper function with annotation
                    errors.append(
                        error_msg(
                            arg_name,
                            f"Lambda with arguments requires return type annotation. "
                            f"Use a named function: def func(arg) -> {dep_type.__name__ if dep_type else 'YourType'}: ...",
                        )
                    )
                    continue
                else:
                    # Simple lambda without arguments
                    if dep_type is not None and dep_type is not Any:
                        # We know what type is expected, assume lambda returns correct type
                        # This covers: arg: int = DependsInject(lambda: 42)
                        continue
                    else:
                        errors.append(
                            error_msg(
                                arg_name,
                                "Lambda dependency has no return type annotation and target type is unknown. "
                                "Add return type: lambda: value -> YourType, or use a named function.",
                            )
                        )
                        continue
            else:
                # Named function without annotation - be more strict
                if dep_type is not None:
                    errors.append(
                        error_msg(
                            arg_name,
                            "Depends Return should a be type, but None was found.",
                        )
                    )
                else:
                    errors.append(
                        error_msg(
                            arg_name,
                            "Depends Return should a be type, but None was found.",
                        )
                    )
                continue

        # ✅ TYPE COMPATIBILITY CHECK
        if not _types_compatible(return_type, dep_type):
            errors.append(
                error_msg(
                    arg_name,
                    f'Depends function "{func_name}" return type should be "{dep_type}", but "{return_type}" was found',
                )
            )

    return errors


def _types_compatible(return_type: Any, expected_type: Any) -> bool:
    """Check if return type is compatible with expected type using typemapping."""
    if return_type is None or expected_type is None:
        return return_type == expected_type

    # ✅ Use typemapping's robust type equality check
    if is_equal_type(return_type, expected_type):
        return True

    # ✅ Use typemapping's safe subclass relationship check
    if safe_issubclass(return_type, expected_type):
        return True

    # Handle Annotated types using typemapping
    if is_Annotated(expected_type):
        expected_args = get_args(expected_type)
        if expected_args:
            return _types_compatible(return_type, expected_args[0])

    if is_Annotated(return_type):
        return_args = get_args(return_type)
        if return_args:
            return _types_compatible(return_args[0], expected_type)

    # Handle Union/Optional types
    from typing import Union

    if get_origin(expected_type) is Union:
        union_args = get_args(expected_type)
        # For Optional[X], accept X
        if len(union_args) == 2 and type(None) in union_args:
            non_none_type = next(arg for arg in union_args if arg is not type(None))
            return _types_compatible(return_type, non_none_type)
        # For general Union, check if return_type matches any
        return any(_types_compatible(return_type, arg) for arg in union_args)

    return False


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
    modeltype: Optional[List[type[Any]]] = None,
    generictype: Optional[type[Any]] = None,
    bt_default_fallback: bool = True,
    type_cast: Optional[List[Tuple[Type[Any], Type[Any]]]] = None,
) -> List[str]:
    """
    Check function signature for injection compatibility.

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
    except Exception as e:
        return [f"Could not analyze function signature: {e}"]

    # Convert to list for in-place modification
    args_list = list(args)
    all_errors: List[str] = []

    # Run all checks, each may filter the args list
    typed_errors = check_all_typed(args_list)
    all_errors.extend(typed_errors)

    inj_errors = check_all_injectables(args_list, modeltype, generictype)
    all_errors.extend(inj_errors)

    single_errors = check_single_injectable(args_list)
    all_errors.extend(single_errors)

    model_errors = check_modefield_types(args_list, modeltype, type_cast)
    all_errors.extend(model_errors)

    # ✅ LAMBDA-FRIENDLY dependency check
    dep_errors = check_depends_types(args_list)
    all_errors.extend(dep_errors)

    return all_errors
