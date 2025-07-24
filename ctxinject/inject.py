import asyncio
import inspect
from functools import partial
from typing import Any, Callable, Dict, Iterable, Optional, Sequence, Type, Union

from typemapping import VarTypeInfo, get_field_type, get_func_args

from ctxinject.model import ArgsInjectable, CallableInjectable, ModelFieldInject


class UnresolvedInjectableError(Exception):
    """Raised when a dependency cannot be resolved in the injection context."""

    ...


class SyncResolver:
    """Synchronous resolver wrapper for optimal performance."""

    __slots__ = ("_func",)

    def __init__(self, func: Callable[[Dict[Any, Any]], Any]) -> None:
        self._func = func

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        return self._func(context)


class AsyncResolver:
    """Asynchronous resolver wrapper for optimal performance."""

    __slots__ = ("_func",)

    def __init__(self, func: Callable[[Dict], Any]) -> None:
        self._func = func

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        return self._func(context)


def resolve_by_name(context: Dict[Union[str, Type[Any]], Any], arg: str) -> Any:
    return context[arg]


def resolve_from_model(
    context: Dict[Union[str, Type[Any]], Any], model: Type[Any], field: str
) -> Any:
    method = getattr(context[model], field)
    return method() if callable(method) else method


def resolve_by_type(context: Dict[Union[str, Type[Any]], Any], bt: Type[Any]) -> Any:
    return context[bt]


def resolve_by_default(context: Dict[Union[str, Type[Any]], Any], default_: Any) -> Any:
    return default_


def wrap_validate_sync(
    context: Dict[Union[str, Type[Any]], Any],
    func: Callable[..., Any],
    instance: Any,  # Can be ArgsInjectable or CallableInjectable
    bt: Type[Any],
    name: str,
) -> Any:
    """Sync validation wrapper - validates immediately."""
    value = func(context)
    validated = instance.validate(value, bt)
    return validated


async def wrap_validate_async(
    context: Dict[Union[str, Type[Any]], Any],
    func: Callable[..., Any],
    instance: Any,  # Can be ArgsInjectable or CallableInjectable
    bt: Type[Any],
    name: str,
) -> Any:
    """Async validation wrapper - awaits value before validation."""
    value = await func(context)
    validated = instance.validate(value, bt)  # Validator always sync
    return validated


async def resolve_mapped_ctx(
    input_ctx: Dict[Union[str, Type[Any]], Any], mapped_ctx: Dict[str, Any]
) -> Dict[Any, Any]:
    """
    Resolve mapped context with optimal sync/async separation using type checking.

    Uses isinstance() for fast O(1) type checking to separate sync and async resolvers.
    """
    if not mapped_ctx:
        return {}

    results = {}
    async_tasks = []
    async_keys = []

    # Single pass: separate sync and async using fast isinstance check
    for key, resolver in mapped_ctx.items():
        try:
            if isinstance(resolver, AsyncResolver):
                # Async resolver - add to concurrent batch
                task = resolver(input_ctx)
                async_tasks.append(task)
                async_keys.append(key)
            else:
                # Sync resolver (SyncResolver or legacy partial) - execute immediately
                results[key] = resolver(input_ctx)

        except Exception:
            # Re-raise original exception to preserve error semantics
            raise

    # Resolve all async tasks concurrently (if any)
    if async_tasks:
        try:
            resolved_values = await asyncio.gather(*async_tasks, return_exceptions=True)

            # Process async results and handle exceptions
            for key, resolved_value in zip(async_keys, resolved_values):
                if isinstance(resolved_value, Exception):
                    # Re-raise original exception to preserve error semantics
                    raise resolved_value
                results[key] = resolved_value

        except Exception:
            # Preserve original exception without wrapping
            raise

    return results


def map_ctx(
    args: Iterable[VarTypeInfo],
    context: Dict[Union[str, Type[Any]], Any],
    allow_incomplete: bool,
    validate: bool = True,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
) -> Dict[str, Any]:
    """
    Map context arguments to resolvers using optimal resolver wrappers.
    """
    ctx: Dict[str, Any] = {}
    overrides = overrides or {}

    for arg in args:
        instance = arg.getinstance(ArgsInjectable)
        default_ = instance.default if instance else None
        bt = arg.basetype
        value = None

        # resolve dependencies
        if arg.hasinstance(CallableInjectable):
            callable_instance = arg.getinstance(CallableInjectable)

            # Apply override without mutating the original object
            dep_func = overrides.get(
                callable_instance.default, callable_instance.default
            )
            # ✅ FIXED: Do NOT mutate callable_instance._default

            dep_args = get_func_args(dep_func)
            dep_ctx_map = map_ctx(
                dep_args, context, allow_incomplete, validate, overrides
            )

            async def resolver(actual_ctx, f=dep_func, ctx_map=dep_ctx_map) -> Any:
                sub_kwargs = await resolve_mapped_ctx(actual_ctx, ctx_map)
                if inspect.iscoroutinefunction(f):
                    return await f(**sub_kwargs)
                else:
                    # f can be a normal function or lambda that returns coroutine
                    result = f(**sub_kwargs)
                    # Check if the result is a coroutine
                    if inspect.iscoroutine(result):
                        return await result
                    return result

            # Wrap dependency resolver as AsyncResolver for fast type checking
            value = AsyncResolver(resolver)

        # by name
        elif arg.name in context:
            value = SyncResolver(partial(resolve_by_name, arg=arg.name))
        # by model field/method
        elif instance is not None:
            if isinstance(instance, ModelFieldInject):
                tgtmodel = instance.model
                tgt_field = instance.field or arg.name
                if tgtmodel in context and get_field_type(tgtmodel, tgt_field):
                    value = SyncResolver(
                        partial(resolve_from_model, model=tgtmodel, field=tgt_field)
                    )
        # by type
        if value is None and bt is not None and bt in context:
            value = SyncResolver(partial(resolve_by_type, bt=bt))
        # by default
        if value is None and default_ is not None and default_ is not Ellipsis:
            value = SyncResolver(partial(resolve_by_default, default_=default_))

        if value is None and not allow_incomplete:
            raise UnresolvedInjectableError(
                f"Argument '{arg.name}' is incomplete or missing a valid injectable context."
            )

        if value is not None:
            # Check BOTH ArgsInjectable AND CallableInjectable for validation
            args_instance = arg.getinstance(ArgsInjectable)
            callable_instance = arg.getinstance(CallableInjectable)

            # Choose which instance to use for validation
            validation_instance = (
                args_instance if args_instance is not None else callable_instance
            )

            if (
                validate
                and validation_instance is not None
                and arg.basetype is not None
                and validation_instance.has_validate
            ):
                # Use type-specific validation wrapper
                if isinstance(value, AsyncResolver):
                    validated_func = partial(
                        wrap_validate_async,
                        func=value._func,
                        instance=validation_instance,
                        bt=arg.basetype,
                        name=arg.name,
                    )
                    value = AsyncResolver(validated_func)
                else:  # SyncResolver or legacy partial
                    # Handle both SyncResolver and legacy partials
                    underlying_func = value._func if hasattr(value, "_func") else value
                    validated_func = partial(
                        wrap_validate_sync,
                        func=underlying_func,
                        instance=validation_instance,
                        bt=arg.basetype,
                        name=arg.name,
                    )
                    value = SyncResolver(validated_func)

            ctx[arg.name] = value

    return ctx


def get_mapped_ctx(
    func: Callable[..., Any],
    context: Dict[Union[str, Type[Any]], Any],
    allow_incomplete: bool = True,
    validate: bool = True,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
) -> Dict[str, Any]:
    """Get mapped context with optimal resolver wrappers."""
    funcargs = get_func_args(func)
    return map_ctx(funcargs, context, allow_incomplete, validate, overrides)


async def inject_args(
    func: Callable[..., Any],
    context: Dict[Union[str, Type[Any]], Any],
    allow_incomplete: bool = True,
    validate: bool = True,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
) -> partial[Any]:
    """
    Inject arguments into function with optimal performance.

    Uses fast isinstance() checks to separate sync and async resolvers for
    maximum performance in the critical path.
    """
    mapped_ctx = get_mapped_ctx(func, context, allow_incomplete, validate, overrides)
    resolved = await resolve_mapped_ctx(context, mapped_ctx)
    return partial(func, **resolved)
