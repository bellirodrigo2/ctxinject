from typing import Any, Callable, Iterable, Optional, Sequence, get_type_hints

from ctxinject.constrained import constrained_factory
from ctxinject.mapfunction import FuncArg, get_func_args
from ctxinject.model import (
    ArgsInjectable,
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
    args: Sequence[FuncArg],
) -> None: ...


def func_signature_validation(
    func: Callable[..., Any],
    modeltype: Iterable[type[Any]],
) -> None:

    args: Sequence[FuncArg] = get_func_args(func)

    check_all_typed(args)

    check_all_injectables(args, modeltype)

    check_modefield_types(args)

    check_depends_types(args)


class ConstrainedArgInj(ArgsInjectable):
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
        value = constr(instance)
        return value
