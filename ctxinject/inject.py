import inspect
from functools import partial
from typing import Any, Callable, Dict, Iterable, Optional, Sequence, Type, Union

from typemapping import VarTypeInfo, get_func_args

from ctxinject.model import ArgsInjectable, CallableInjectable, ModelFieldInject


class UnresolvedInjectableError(Exception):
    """Raised when a dependency cannot be resolved in the injection context."""

    ...


def resolve_by_name(context: Dict[Union[str, type], Any], arg: str) -> Any:
    return context[arg]


def resolve_from_model(
    context: Dict[Union[str, type], Any], model: Type[Any], field: str
) -> Any:
    method = getattr(context[model], field)
    return method() if callable(method) else method


def resolve_by_type(context: Dict[Union[str, type], Any], bt: Type[Any]) -> Any:
    return context[bt]


def resolve_by_default(context: Dict[Union[str, type], Any], default_: Any) -> Any:
    return default_


def wrap_validate(
    context: Dict[Union[str, type], Any],
    func: Callable[..., Any],
    instance: ArgsInjectable,
    bt: Type[Any],
    name: str,
) -> Any:

    value = func(context)
    validated = instance.validate(value, bt)
    # if validated is None:
    # raise ValueError(f"Validation for {name} returned None")
    return validated


type TransformFunction = Callable[
    [Sequence[VarTypeInfo], Any],
    Sequence[VarTypeInfo],
]


async def resolve_mapped_ctx(
    input_ctx: Dict[Union[str, type], Any], mapped_ctx: Dict[str, Any]
) -> Dict[Any, Any]:
    results = {}
    for k, v in mapped_ctx.items():
        result = v(input_ctx)
        if inspect.isawaitable(result):
            result = await result
        results[k] = result
    return results


def map_ctx(
    args: Iterable[VarTypeInfo],
    context: Dict[Union[str, type], Any],
    allow_incomplete: bool,
    validate: bool = True,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
) -> Dict[str, Any]:

    ctx: dict[str, Any] = {}
    overrides = overrides or {}

    for arg in args:
        instance = arg.getinstance(ArgsInjectable)
        default_ = instance.default if instance else None
        bt = arg.basetype
        value = None

        # resolve depends
        if arg.hasinstance(CallableInjectable):
            callable_instance = arg.getinstance(CallableInjectable)
            dep_func = overrides.get(
                callable_instance.default, callable_instance.default
            )
            callable_instance._default = dep_func
            dep_args = get_func_args(dep_func)
            dep_ctx_map = map_ctx(
                dep_args, context, allow_incomplete, validate, overrides
            )

            async def resolver(actual_ctx, f=dep_func, ctx_map=dep_ctx_map) -> Any:
                sub_kwargs = await resolve_mapped_ctx(actual_ctx, ctx_map)
                if inspect.iscoroutinefunction(f):
                    return await f(**sub_kwargs)
                return f(**sub_kwargs)

            value = resolver

        # by name
        elif arg.name in context:
            value = partial(resolve_by_name, arg=arg.name)
        # by model field/method
        elif instance is not None:
            if isinstance(instance, ModelFieldInject):
                tgtmodel = instance.model
                tgt_field = instance.field or arg.name
                if tgtmodel in context:
                    value = partial(resolve_from_model, model=tgtmodel, field=tgt_field)
        # by type
        if value is None and bt is not None and bt in context:
            value = partial(resolve_by_type, bt=bt)
        # by default
        if value is None and default_ is not None and default_ is not Ellipsis:
            value = partial(resolve_by_default, default_=default_)

        if value is None and not allow_incomplete:
            raise UnresolvedInjectableError(
                f"Argument '{arg.name}' is incomplete or missing a valid injectable context."
            )
        if value is not None:
            if (
                validate
                and instance is not None
                and arg.basetype is not None
                and instance.has_validate
            ):
                value = partial(
                    wrap_validate,
                    func=value,
                    instance=instance,
                    bt=arg.basetype,
                    name=arg.name,
                )
            ctx[arg.name] = value
    return ctx


def get_mapped_ctx(
    func: Callable[..., Any],
    context: Dict[Union[str, type], Any],
    allow_incomplete: bool = True,
    validate: bool = True,
    # transform_func: Optional[Callable[[Callable[..., Any]], Callable[..., Any]]] = None,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
) -> Dict[str, Any]:
    # if transform_func is not None:
    # func = transform_func(func)

    funcargs = get_func_args(func)

    return map_ctx(funcargs, context, allow_incomplete, validate, overrides)


async def inject_args(
    func: Callable[..., Any],
    context: Dict[Union[str, type], Any],
    allow_incomplete: bool = True,
    validate: bool = True,
    # transform_func: Optional[Callable[[Callable[..., Any]], Callable[..., Any]]] = None,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
) -> partial[Any]:
    mapped_ctx = get_mapped_ctx(func, context, allow_incomplete, validate, overrides)
    resolved = await resolve_mapped_ctx(context, mapped_ctx)
    return partial(func, **resolved)
