import asyncio
from contextlib import AsyncExitStack
from functools import partial
from typing import Any, Callable, Container, Dict, Iterable, Optional, Type, Union

from typemapping import VarTypeInfo, get_func_args, get_return_type

from ctxinject.model import (
    CallableInjectable,
    Injectable,
    ModelFieldInject,
    get_nested_field_type,
)
from ctxinject.resolvers import (
    BaseResolver,
    DefaultResolver,
    DependsResolver,
    ModelFieldResolver,
    NameResolver,
    TypeResolver,
    ValidateResolver,
)
from ctxinject.validation import get_validator


class UnresolvedInjectableError(Exception):
    """
    Raised when a dependency cannot be resolved in the injection context.

    This exception is thrown when:
    - A required argument has no corresponding value in the context
    - A type cannot be found in the context
    - A model field injection fails to resolve
    - allow_incomplete=False and some dependencies are missing
    """

    ...


async def resolve_mapped_ctx(
    input_ctx: Dict[Union[str, Type[Any]], Any],
    mapped_ctx: Dict[str, BaseResolver],
    stack: Optional[AsyncExitStack] = None,
) -> Dict[Any, Any]:
    """
    Resolve mapped context with optimal sync/async separation using type checking.

    This function efficiently resolves a pre-mapped context by:
    1. Separating sync and async resolvers using fast isinstance() checks
    2. Executing sync resolvers immediately
    3. Batching async resolvers for concurrent execution
    4. Preserving original exceptions without wrapping

    Args:
        input_ctx: The original injection context containing values and types
        mapped_ctx: Pre-mapped resolvers from get_mapped_ctx() or map_ctx()

    Returns:
        Dictionary with resolved argument names and their values

    Raises:
        Any exceptions from resolver execution are preserved and re-raised

    Example:
        ```python
        # Get mapped context for a function
        mapped = get_mapped_ctx(my_function, context)

        # Resolve all dependencies
        resolved = await resolve_mapped_ctx(context, mapped)

        # Now you can call the function with resolved args
        result = my_function(**resolved)
        ```

    Note:
        Uses isinstance() for fast O(1) type checking to separate sync and async resolvers.
        All async operations are executed concurrently for optimal performance.
    """
    if not mapped_ctx:
        return {}

    results = {}
    async_tasks = []
    async_keys = []

    # Single pass: separate sync and async using fast isinstance check
    for key, resolver in mapped_ctx.items():
        try:
            result = resolver(input_ctx, stack)

            if resolver.isasync:
                async_tasks.append(result)
                async_keys.append(key)
            else:
                results[key] = result

        except Exception:
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


def inject_validate(
    value: BaseResolver,
    instance: Optional[Injectable],
    from_type: Optional[Type[Any]],
    bt: Optional[Type[Any]],
) -> BaseResolver:
    if instance is not None:
        if not instance.has_validate:
            instance._validator = get_validator(from_type, bt)  # type: ignore
        if instance.has_validate:
            value = ValidateResolver(
                func=value,
                instance=instance,
                bt=bt,  # type: ignore
            )
    return value


def map_ctx(
    args: Iterable[VarTypeInfo],
    context: Container[Union[str, Type[Any]]],
    allow_incomplete: bool,
    validate: bool = True,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
    enable_async_model_field: bool = False,
) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {}
    overrides = overrides or {}

    for arg in args:
        instance = arg.getinstance(Injectable)
        default_ = instance.default if instance else None
        bt = arg.basetype
        from_type = arg.basetype
        value: Optional[BaseResolver] = None

        # resolve dependencies
        if isinstance(instance, CallableInjectable):

            # Apply override without mutating the original object
            dep_func = overrides.get(instance.default, instance.default)
            dep_args = get_func_args(dep_func)
            dep_ctx_map = map_ctx(
                args=dep_args,
                context=context,
                allow_incomplete=allow_incomplete,
                validate=validate,
                overrides=overrides,
                enable_async_model_field=enable_async_model_field,
            )
            value = DependsResolver(dep_func, dep_ctx_map, resolve_mapped_ctx)
            from_type = get_return_type(dep_func)
        # by name
        elif arg.name in context:
            value = NameResolver(
                arg_name=arg.name,
            )
        # by model field/method
        elif instance is not None:
            if isinstance(instance, ModelFieldInject):
                tgtmodel = instance.model
                tgt_field = instance.field or arg.name
                modeltype = get_nested_field_type(tgtmodel, tgt_field)
                if tgtmodel in context and (modeltype or enable_async_model_field):

                    from_type = modeltype
                    value = ModelFieldResolver(
                        model_type=tgtmodel,
                        field_name=tgt_field,
                        async_model_field=enable_async_model_field,
                    )
        # by type
        if value is None and bt is not None and bt in context:
            from_type = bt
            value = TypeResolver(target_type=bt)
        # by default
        if value is None and default_ is not None and default_ is not Ellipsis:
            from_type = type(default_)
            value = DefaultResolver(
                default_value=default_,
            )

        if value is None and not allow_incomplete:
            raise UnresolvedInjectableError(
                f"Argument '{arg.name}' is incomplete or missing a valid injectable context."
            )
        if value is not None:
            if validate:
                value = inject_validate(value, instance, from_type, bt)

            ctx[arg.name] = value

    return ctx


def get_mapped_ctx(
    func: Callable[..., Any],
    context: Container[Union[str, Type[Any]]],
    allow_incomplete: bool = True,
    validate: bool = True,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
    enable_async_model_field: bool = False,
) -> Dict[str, Any]:
    """
    Get mapped context with optimal resolver wrappers for a function.

    This function analyzes a function's signature and creates a mapping of
    parameter names to their corresponding resolvers based on the injection context.

    Args:
        func: The function to analyze and create resolvers for
        context: Injection context containing values, types, and model instances
        allow_incomplete: Whether to allow missing dependencies (default: True)
        validate: Whether to apply validation if defined (default: True)
        overrides: Optional mapping to override dependency functions

    Returns:
        Dictionary mapping parameter names to their resolvers

    Raises:
        UnresolvedInjectableError: When allow_incomplete=False and dependencies are missing

    Example:
        ```python
        def my_func(name: str, count: int = ArgsInjectable(42)):
            return f"{name}: {count}"

        context = {"name": "test", int: 100}
        mapped = get_mapped_ctx(my_func, context)

        # mapped contains resolvers for 'name' and 'count' parameters
        # You can then use resolve_mapped_ctx() to get actual values
        ```

    Note:
        This is typically used internally by inject_args(), but can be useful
        for advanced scenarios where you need to inspect or modify the resolution
        process before executing it.
    """
    funcargs = get_func_args(func)
    return map_ctx(
        args=funcargs,
        context=context,
        allow_incomplete=allow_incomplete,
        validate=validate,
        overrides=overrides,
        enable_async_model_field=enable_async_model_field,
    )


async def inject_args(
    func: Callable[..., Any],
    context: Union[Dict[Union[str, Type[Any]], Any], Any],
    allow_incomplete: bool = True,
    validate: bool = True,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
    stack: Optional[AsyncExitStack] = None,
    enable_async_model_field: bool = False,
) -> Callable[..., Any]:
    """
    Inject arguments into function with optimal performance using dependency injection.

    This is the main entry point for dependency injection. It analyzes a function's
    signature, resolves dependencies from the provided context, and returns a
    partially applied function with those dependencies injected.

    Args:
        func: The target function to inject dependencies into
        context: Dictionary containing injectable values:
            - By name: {"param_name": value}
            - By type: {SomeClass: instance}
            - Model instances for ModelFieldInject
        allow_incomplete: If True, allows missing dependencies (they remain as parameters).
                         If False, raises UnresolvedInjectableError for missing deps.
        validate: Whether to apply validation functions defined in injectable annotations
        overrides: Optional mapping to replace dependency functions with alternatives

    Returns:
        A functools.partial object with resolved dependencies pre-filled.
        The returned function has a reduced signature containing only unresolved parameters.

    Raises:
        UnresolvedInjectableError: When allow_incomplete=False and required dependencies
                                 cannot be resolved from context
        ValidationError: When validate=True and a validator rejects a value

    Examples:
        Basic injection by name and type:
        ```python
        from typing_extensions import Annotated
        from ctxinject.inject import inject_args
        from ctxinject.model import ArgsInjectable

        def greet(name: str, count: int = ArgsInjectable(1)):
            return f"Hello {name}! (x{count})"

        context = {"name": "Alice", int: 5}
        injected = await inject_args(greet, context)
        result = injected()  # "Hello Alice! (x5)"
        ```

        Dependency injection with validation:
        ```python
        def validate_positive(value: int, **kwargs) -> int:
            if value <= 0:
                raise ValueError("Must be positive")
            return value

        def process(count: int = ArgsInjectable(1, validate_positive)):
            return count * 2

        context = {"count": 5}
        injected = await inject_args(process, context)
        result = injected()  # 10
        ```

        Model field injection:
        ```python
        class Config:
            database_url: str = "sqlite:///app.db"
            debug: bool = True

        def connect(
            url: str = ModelFieldInject(Config, "database_url"),
            debug: bool = ModelFieldInject(Config, "debug")
        ):
            return f"Connecting to {url} (debug={debug})"

        config = Config()
        context = {Config: config}
        injected = await inject_args(connect, context)
        result = injected()  # "Connecting to sqlite:///app.db (debug=True)"
        ```

        Async dependency functions:
        ```python
        async def get_user_service() -> UserService:
            return await UserService.create()

        def handle_request(
            service: UserService = DependsInject(get_user_service)
        ):
            return service.get_current_user()

        context = {}  # Dependencies resolved automatically
        injected = await inject_args(handle_request, context)
        result = injected()
        ```

    Performance Notes:
        - Uses fast isinstance() checks to separate sync and async resolvers
        - Async dependencies are resolved concurrently for maximum performance
        - Supports chaining multiple injections on the same function
        - Name-based injection takes precedence over type-based injection
    """
    if not isinstance(context, dict):
        context = {type(context): context}
    context_list = list(context.keys())
    mapped_ctx = get_mapped_ctx(
        func=func,
        context=context_list,
        allow_incomplete=allow_incomplete,
        validate=validate,
        overrides=overrides,
        enable_async_model_field=enable_async_model_field,
    )
    resolved = await resolve_mapped_ctx(context, mapped_ctx, stack)
    return partial(func, **resolved)
