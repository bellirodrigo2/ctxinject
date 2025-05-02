from functools import partial
from typing import Any, Callable, Iterable, Mapping, Sequence, Union

from ctxinject.mapfunction import FuncArg, get_func_args
from ctxinject.model import ArgsInjectable, ModelFieldInject


def get_required_args(
    arglist: Sequence[FuncArg], modeltype: Iterable[type[Any]]
) -> Iterable[FuncArg]:

    ctxrequired: set[FuncArg] = set()
    for arg in arglist:
        if arg.hasinstance(ArgsInjectable):
            ctxrequired.add(arg)
        else:
            for model in modeltype:
                if arg.istype(model):
                    ctxrequired.add(arg)

    return ctxrequired


def resolve_ctx(
    args: Iterable[FuncArg], context: Mapping[Union[str, type], Any]
) -> Mapping[str, Any]:
    ctx: dict[str, Any] = {}

    for arg in args:
        instance = arg.getinstance(ArgsInjectable)

        if arg.name in context:  # by name
            ctx[arg.name] = context[arg.name]

        elif instance is not None and isinstance(
            instance, ModelFieldInject
        ):  # by model field
            tgtmodel = instance.model
            tgt_field = instance.field or arg.name
            if tgtmodel in context:
                ctx[arg.name] = getattr(context[tgtmodel], tgt_field)

        elif arg.basetype is not None and arg.basetype in context:  # by type
            ctx[arg.name] = context[arg.basetype]

        elif instance is not None and instance.default is not Ellipsis:  # by default
            ctx[arg.name] = instance.default
    return ctx


def validate_context(context: Mapping[Union[str, type], Any]) -> None: ...


def inject(
    func: Callable[..., Any],
    context: Mapping[Union[str, type], Any],
    modeltype: Iterable[type[Any]],
    validate_ctx: bool = False,
) -> partial[Any]:

    if validate_ctx:
        validate_context(context)

    funcargs = get_func_args(func)
    required_args = get_required_args(funcargs, modeltype)
    ctx = resolve_ctx(required_args, context)

    return partial(func, **ctx)
