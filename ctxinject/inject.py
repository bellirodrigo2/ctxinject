import inspect
from functools import partial
from typing import Any, Callable, Iterable, Mapping, Union

from ctxinject.constrained import ValidationError
from ctxinject.mapfunction import FuncArg, get_func_args
from ctxinject.model import (
    ArgsInjectable,
    CallableInjectable,
    ICallableInjectable,
    ModelFieldInject,
    UnresolvedInjectableError,
)


def resolve_ctx(
    args: Iterable[FuncArg],
    context: Mapping[Union[str, type], Any],
    allow_incomplete: bool,
) -> Mapping[str, Any]:
    ctx: dict[str, Any] = {}

    for arg in args:
        instance = arg.getinstance(ArgsInjectable)
        default_ = instance.default if instance else None
        bt = arg.basetype
        value = None

        if arg.name in context:  # by name
            value = context[arg.name]

        elif instance is not None and isinstance(
            instance, ModelFieldInject
        ):  # by model field

            tgtmodel = instance.model
            tgt_field = instance.field or arg.name
            if tgtmodel in context:
                value = getattr(context[tgtmodel], tgt_field)

        elif bt is not None and bt in context:  # by type
            value = context[bt]

        elif default_ is not None and default_ is not Ellipsis:  # by default
            value = default_
        elif not allow_incomplete:
            raise UnresolvedInjectableError(
                f"Argument '{arg.name}' is incomplete or missing a valid injectable context."
            )
        if value is not None:
            if instance is not None and arg.basetype is not None:
                validated = instance.validate(value, arg.basetype)
                if validated is None:
                    raise ValidationError(f"Validation for {arg.name} returned None")
                value = validated
            ctx[arg.name] = value
    return ctx


def inject_args(
    func: Callable[..., Any],
    context: Mapping[Union[str, type], Any],
    allow_incomplete: bool = True,
) -> partial[Any]:
    funcargs = get_func_args(func)
    ctx = resolve_ctx(funcargs, context, allow_incomplete)

    return partial(func, **ctx)


async def inject_dependencies(
    func: Callable[..., Any],
    context: Mapping[Union[str, type], Any],
    # modeltype: Iterable[type[Any]],
    overrides: Mapping[Callable[..., Any], Callable[..., Any]],
    tgttype: type[ICallableInjectable] = CallableInjectable,
) -> Callable[..., Any]:
    depfunc = overrides.get(func, func)
    argsfunc = get_func_args(depfunc)
    deps: list[tuple[str, Any]] = [
        (arg.name, arg.getinstance(tgttype).default)  # type: ignore
        for arg in argsfunc
        if arg.hasinstance(tgttype)
    ]
    if not deps:
        return depfunc
    dep_ctx: dict[Union[str, type], Any] = {}
    for name, dep in deps:
        dep_ctx[name] = await resolve(dep, context, overrides, tgttype)
    resolved = inject_args(depfunc, dep_ctx, allow_incomplete=True)
    return resolved


async def resolve(
    func: Callable[..., Any],
    context: Mapping[Union[str, type], Any],
    # modeltype: Iterable[type[Any]],
    overrides: Mapping[Callable[..., Any], Callable[..., Any]],
    tgttype: type[ICallableInjectable] = CallableInjectable,
) -> Any:
    depfunc = overrides.get(func, func)
    injdepfunc = inject_args(depfunc, context, allow_incomplete=True)
    resolved_func = await inject_dependencies(injdepfunc, context, overrides, tgttype)
    args = get_func_args(resolved_func)
    if args:
        raise UnresolvedInjectableError(
            f"Arguments unresolved in '{func.__name__}': {[a.name for a in args]}"
        )

    async def _run(partial_fn: Callable[..., Any]) -> Any:
        result = partial_fn()
        return await result if inspect.isawaitable(result) else result

    return await _run(resolved_func)
