from typing import (
    Annotated,
    Any,
    Callable,
    Iterable,
    Optional,
    Sequence,
    get_args,
    get_origin,
    get_type_hints,
)

from ctxinject.mapfunction import FuncArg, get_func_args
from ctxinject.model import (
    DependsInject,
    Injectable,
    InvalidInjectableDefinition,
    InvalidModelFieldType,
    ModelFieldInject,
    UnInjectableError,
)


def check_all_typed(
    args: Sequence[FuncArg],
) -> None:
    for arg in args:
        if arg.basetype is None:
            raise TypeError(f'Arg "{arg.name}" has no type definition')


def check_all_injectables(
    args: Sequence[FuncArg],
    modeltype: Iterable[type[Any]],
) -> None:

    def is_injectable(arg: FuncArg, modeltype: Iterable[type[Any]]) -> bool:
        if arg.hasinstance(Injectable):
            return True
        for model in modeltype:
            if arg.istype(model):
                return True
        return False

    for arg in args:
        if not is_injectable(arg, modeltype):
            raise UnInjectableError(arg.name, arg.argtype)


def check_modefield_types(
    args: Sequence[FuncArg],
) -> None:
    for arg in args:
        modelfield_inj = arg.getinstance(ModelFieldInject)
        if modelfield_inj is not None:
            if not isinstance(modelfield_inj.model, type):  # type: ignore
                raise InvalidInjectableDefinition(
                    f'ModelFieldInject "model" field should be a type, but {type(modelfield_inj.model)} found'
                )
            field_types = get_type_hints(modelfield_inj.model)
            argtype = field_types.get(arg.name, None)
            if argtype is None or not arg.istype(argtype):
                raise InvalidModelFieldType(f'Argument "{arg.name}" ')


def check_depends_types(
    args: Sequence[FuncArg], tgttype: type[DependsInject] = DependsInject
) -> None:

    deps: list[tuple[str, Optional[type[Any]], Any]] = [
        (arg.name, arg.basetype, arg.getinstance(tgttype).default)  # type: ignore
        for arg in args
        if arg.hasinstance(tgttype)
    ]
    for arg_name, dep_type, dep_func in deps:

        if not callable(dep_func):
            raise TypeError(f"Depends value should be a callable. Found '{dep_func}'.")

        return_type = get_type_hints(dep_func).get("return")
        if get_origin(return_type) is Annotated:
            return_type = get_args(return_type)[0]
        if return_type is None or not isinstance(return_type, type):
            raise TypeError(
                f"Depends Return Type should a be type, but {return_type} was found."
            )
        if dep_type is None or not isinstance(dep_type, type):  # type: ignore
            raise TypeError(
                f"Arg '{arg_name}' type from Depends should a be type, but {return_type} was found."
            )
        if not issubclass(return_type, dep_type):
            raise TypeError(
                f"Depends function {dep_func} return type should be a subclass of {dep_type}, but {return_type} was found"
            )


def check_single_injectable(args: Sequence[FuncArg]) -> None:
    for arg in args:
        if arg.extras is not None:
            injectables = [x for x in arg.extras if isinstance(x, Injectable)]
            if len(injectables) > 1:
                raise TypeError(
                    f"Argument '{arg.name}' has multiple injectables: {[type(i).__name__ for i in injectables]}"
                )


def func_signature_validation(
    func: Callable[..., Any],
    modeltype: Iterable[type[Any]],
) -> None:

    args: Sequence[FuncArg] = get_func_args(func)

    check_all_typed(args)

    check_all_injectables(args, modeltype)

    check_modefield_types(args)

    check_depends_types(args)

    check_single_injectable(args)
