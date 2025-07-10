from typemapping import VarTypeInfo, get_field_type, get_func_args
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


def check_all_typed(
    args: List[VarTypeInfo],
) -> List[str]:
    errors: List[str] = []
    for arg in args[:]:
        if arg.basetype is None:
            errors.append(error_msg(arg.name, "has no type definition"))
            args.remove(arg)
    return errors


def check_all_injectables(
    args: List[VarTypeInfo],
    modeltype: Iterable[type[Any]],
    generictype: Optional[type[Any]] = None,
) -> List[str]:

    def is_injectable(arg: VarTypeInfo, modeltype: Iterable[type[Any]]) -> bool:
        if arg.hasinstance(Injectable):
            return True
        for model in modeltype:
            if arg.istype(model):
                return True
            elif generictype is not None and arg.origin is generictype:
                if (
                    len(arg.args) > 0
                    and isinstance(arg.args[0], type)
                    and issubclass(arg.args[0], model)
                ):
                    return True
        return False

    errors: List[str] = []
    for arg in args[:]:
        if not is_injectable(arg, modeltype):
            errors.append(
                error_msg(arg.name, f"of type '{arg.basetype}' cannot be injected.")
            )
            args.remove(arg)
    return errors


def check_modefield_types(
    args: List[VarTypeInfo],
    allowed_models: Optional[List[type[Any]]] = None,
    type_cast: Optional[List[Tuple[type[Any], Type[Any]]]] = None,
) -> List[str]:
    errors: List[str] = []
    type_cast = type_cast or []
    for arg in args[:]:
        modelfield_inj = arg.getinstance(ModelFieldInject)
        if modelfield_inj is not None:
            if not isinstance(modelfield_inj.model, type):  # type: ignore
                errors.append(
                    error_msg(
                        arg.name,
                        f'ModelFieldInject "model" field should be a type, but "{modelfield_inj.model}" was found',
                    )
                )
                args.remove(arg)
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
                args.remove(arg)
                continue
            elif not arg.isequal(argtype):
                if (argtype, arg.basetype) not in type_cast:
                    errors.append(
                        error_msg(
                            arg.name,
                            f"has ModelFieldInject, but types does not match. Expected {argtype}, but found {arg.argtype}",
                        )
                    )
                    args.remove(arg)
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
                    args.remove(arg)
    return errors


def check_depends_types(
    args: Sequence[VarTypeInfo], tgttype: Type[DependsInject] = DependsInject
) -> List[str]:

    errors: List[str] = []
    deps: list[tuple[str, Optional[type[Any]], Any]] = [
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

        return_type = get_type_hints(dep_func).get("return")
        if get_origin(return_type) is Annotated:
            return_type = get_args(return_type)[0]
        if return_type is None:
            errors.append(
                error_msg(
                    arg_name,
                    f"Depends Return should a be type, but {return_type} was found.",
                )
            )
        elif not return_type == dep_type:
            errors.append(
                error_msg(
                    arg_name,
                    f'Depends function "{dep_func.__name__}" return type should be "{dep_type}", but "{return_type}" was found',
                )
            )
    return errors


def check_single_injectable(args: List[VarTypeInfo]) -> List[str]:

    errors: List[str] = []
    for arg in args[:]:
        if arg.extras is not None:
            injectables = [x for x in arg.extras if isinstance(x, Injectable)]
            if len(injectables) > 1:
                errors.append(
                    error_msg(
                        arg.name,
                        f"has multiple injectables: {[type(i).__name__ for i in injectables]}",
                    )
                )
                args.remove(arg)
    return errors


def func_signature_check(
    func: Callable[..., Any],
    modeltype: Optional[List[type[Any]]] = None,
    generictype: Optional[type[Any]] = None,
    bt_default_fallback: bool = True,
    type_cast: Optional[List[Tuple[type[Any], Type[Any]]]] = None,
) -> List[str]:

    modeltype = modeltype or []

    args: Sequence[VarTypeInfo] = get_func_args(
        func, bt_default_fallback=bt_default_fallback
    )
    all_errors: List[str] = []

    typed_errors = check_all_typed(args)
    all_errors.extend(typed_errors)

    inj_errors = check_all_injectables(args, modeltype, generictype)
    all_errors.extend(inj_errors)

    single_errors = check_single_injectable(args)
    all_errors.extend(single_errors)

    model_errors = check_modefield_types(args, modeltype, type_cast)
    all_errors.extend(model_errors)

    dep_errors = check_depends_types(args)
    all_errors.extend(dep_errors)

    return all_errors
