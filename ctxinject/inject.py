from functools import partial
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Union

from ctxinject.mapfunction import FuncArg, get_func_args
from ctxinject.model import (ArgNameBasedInjectable, ArgsInjectable,
                             Injectable, TypeBasedInjectable)


def resolve_val(
    key: str,
    arg: FuncArg,
    context: Mapping[Union[str, type], Any],
    raise_on_missing: bool,
    tgttype: type = Injectable,
    # modeltype:type
) -> Optional[Any]:

    # Falta para modeltype...type BaseModel
    # duas funçoes resolve val

    value = None
    instance: Injectable = arg.getinstance(tgttype)  # Para injectable
    if key in context:
        value = context[key]
    elif type(instance) in context:  # Para injectable
        value = context[type(instance)]
    elif instance.default is not Ellipsis:  # Para injectable
        value = instance.default
    elif raise_on_missing:
        raise RuntimeError(f"Missing injectable for '{key}'")
    if value is not None:
        instance.validate(value)
    return value


def inner_inject(
    args: dict[str, FuncArg],
    context: Mapping[Union[str, type], Any],
    raise_on_missing: bool,
    tgttype: type = Injectable,
):
    resolved: dict[str, Any] = {}

    # usar essa inner_inject
    # tem que injetar modelos...comp basemodel

    # aqui, baseado no funcarg...tem que decidir se resolve por model ou injectable

    for key, arg in args.items():
        value = resolve_val(key, arg, context, raise_on_missing, tgttype)
        if value is not None:
            resolved[key] = value
    return resolved


def inject(
    func: Callable[..., Any],
    context: Mapping[Union[str, type], Any],
    raise_on_missing: bool,
    tgttype: type = Injectable,
):

    args: dict[str, FuncArg] = {
        arg.name: arg for arg in get_func_args(func) if arg.hasinstance(tgttype)
    }
    resolved: dict[str, Any] = inner_inject(args, context, raise_on_missing, tgttype)
    return partial(func, **resolved)


def get_required_args(arglist: Sequence[FuncArg], modeltype: type) -> Iterable[FuncArg]:

    if not isinstance(modeltype, type):  # type: ignore
        raise TypeError(
            f'ModelType must be a type. Arg passed "{modeltype}" is not a type'
        )

    ctxrequired: set[FuncArg] = set()

    for arg in arglist:
        if arg.hasinstance(ArgNameBasedInjectable):
            ctxrequired.add(arg)
        elif arg.hasinstance(TypeBasedInjectable):
            ctxrequired.add(arg)
        elif arg.istype(modeltype):
            ctxrequired.add(arg)

    return ctxrequired


def resolve_ctx(
    args: Iterable[FuncArg], context: Mapping[Union[str, type], Any]
) -> Mapping[str, Any]:
    ctx: dict[str, Any] = {}
    for arg in args:
        if arg.name in context:
            ctx[arg.name] = context[arg.name]
        elif arg.basetype and arg.basetype in context:
            ctx[arg.name] = context[arg.basetype]
        else:  # resolve by default
            instance = arg.getinstance(ArgsInjectable)
            if instance and instance.default is not Ellipsis:
                ctx[arg.name] = instance.default
    return ctx


def inject2(
    func: Callable[..., Any], context: Mapping[Union[str, type], Any], modeltype: type
):

    funcargs = get_func_args(func)

    required_args = get_required_args(funcargs, modeltype)

    ctx = resolve_ctx(required_args, context)

    return partial(func, **ctx)
