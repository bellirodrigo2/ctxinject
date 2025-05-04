from typing import Any, Callable, Iterable, Optional, Sequence, get_type_hints

from ctxinject.constrained import constrained_factory
from ctxinject.mapfunction import FuncArg, get_func_args
from ctxinject.model import (
    ArgsInjectable,
    DependsInject,
    Injectable,
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
        return_type = get_type_hints(dep_func).get("return")
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


def func_signature_validation(
    func: Callable[..., Any],
    modeltype: Iterable[type[Any]],
) -> None:

    args: Sequence[FuncArg] = get_func_args(func)

    check_all_typed(args)

    check_all_injectables(args, modeltype)

    check_modefield_types(args)

    check_depends_types(args)


class ConstrArgInject(ArgsInjectable):
    def __init__(
        self,
        default: Any = ...,
        custom_validator: Optional[Callable[[Any], Any]] = None,
        **meta: Any,
    ):
        self._default = default
        self.meta = meta
        self._custom_validator = custom_validator

    def validate(self, instance: Any, basetype: type[Any]) -> None:
        if self._custom_validator is not None:
            instance = self._custom_validator(instance)
        constr = constrained_factory(basetype)
        value = constr(instance, **self.meta)
        return value


class Depends(DependsInject):
    pass
    # def validate(self, instance: Any, basetype: type[Any]) -> Any:

    #     if not callable(instance):
    #         raise TypeError(f"Depends value should be a callable. Found '{instance}'.")
    #     return_type = get_type_hints(instance).get("return")

    #     if not isinstance(basetype, type):  # type: ignore
    #         raise TypeError(
    #             f"Depends Base Type should a be type, but {type(basetype)} was found."
    #         )

    #     if not return_type or not isinstance(return_type, type):
    #         raise TypeError(
    #             f"Depends Return Type should a be type, but {type(basetype)} was found."
    #         )

    #     if not issubclass(basetype, return_type):
    #         raise TypeError(
    #             f'Depends Function "{instance.__name__}" returns a "{return_type}", but function signature expects a {basetype}'
    #         )
    #     return instance
