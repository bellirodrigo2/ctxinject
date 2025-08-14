from collections import defaultdict
from contextlib import AsyncExitStack
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Container,
    Dict,
    Iterable,
    Optional,
    Type,
    Union,
)

from typemapping import VarTypeInfo, get_func_args, get_return_type

if TYPE_CHECKING:
    from ctxinject.overrides import Provider

from ctxinject.model import CallableInjectable, Injectable, ModelFieldInject
from ctxinject.resolvers import (
    BaseResolver,
    DefaultResolver,
    DependsResolver,
    ModelFieldResolver,
    NameResolver,
    TypeResolver,
    ValidateResolver,
)
from ctxinject.runner import run_async_tasks
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
    Resolve mapped context with sync/async separation (legacy version).

    This is the standard resolution function that maintains backward compatibility.
    For optimized resolution with pre-computed ordering, use resolve_mapped_ctx_ordered().

    This function efficiently resolves a pre-mapped context by:
    1. Separating sync and async resolvers using isinstance() checks
    2. Executing sync resolvers immediately
    3. Batching async resolvers for concurrent execution
    4. Preserving original exceptions without wrapping

    Args:
        input_ctx: The original injection context containing values and types
        mapped_ctx: Pre-mapped resolvers from get_mapped_ctx()
        stack: Optional AsyncExitStack for context manager support

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
        Uses isinstance() for O(1) type checking to separate sync and async resolvers.
        All async operations are executed concurrently without ordering guarantees.
        For ordered async execution, use resolve_mapped_ctx_ordered() instead.
    """
    if not mapped_ctx:
        return {}

    results = {}
    # async_resolvers = []
    async_keys = []
    async_tasks = []

    for key, resolver in mapped_ctx.items():
        try:
            result = resolver(input_ctx, stack)
            results[key] = result
            if resolver.isasync:
                # async_resolvers.append((key, resolver.order, result))
                async_keys.append(key)
                async_tasks.append(result)

        except Exception:
            raise

    # if async_resolvers:
    if async_tasks:
        # if len(async_resolvers) == 1:
        if len(async_tasks) == 1:
            # key, _, task = async_resolvers[0]
            key, task = async_keys[0], async_tasks[0]
            results[key] = await task
        else:
            await run_async_tasks(
                async_tasks=async_tasks, async_keys=async_keys, results=results
            )
            # await run_async_resolvers_ordered(async_resolvers, results)

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
    resolve_mapped_ctx_: Optional[Callable[..., Any]] = None,
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

            dep_func = overrides.get(instance.default, instance.default)
            dep_args = get_func_args(dep_func)
            dep_ctx_map = map_ctx(
                args=dep_args,
                context=context,
                allow_incomplete=allow_incomplete,
                validate=validate,
                overrides=overrides,
                enable_async_model_field=enable_async_model_field,
                resolve_mapped_ctx_=resolve_mapped_ctx_,
            )
            value = DependsResolver(
                dep_func,
                dep_ctx_map,
                resolve_mapped_ctx_ or resolve_mapped_ctx,
                instance.order,
            )
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
                modeltype = instance.get_nested_field_type(tgt_field)
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
    resolve_mapped_ctx: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """
    Get mapped context with resolver wrappers for a function (standard version).

    This function analyzes a function's signature and creates a mapping of
    parameter names to their corresponding resolvers based on the injection context.
    For optimized pre-computed ordering, use get_mapped_ctx_ordered().

    Args:
        func: The function to analyze and create resolvers for
        context: Injection context containing values, types, and model instances
        allow_incomplete: Whether to allow missing dependencies (default: True)
        validate: Whether to apply validation if defined (default: True)
        overrides: Optional mapping to override dependency functions
        enable_async_model_field: Whether to enable async model field injection
        resolve_mapped_ctx: Optional custom resolver function for recursive dependencies

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
        process before executing it. For maximum performance with pre-computed
        ordering, consider using the ordered variants.
    """
    funcargs = get_func_args(func)
    return map_ctx(
        args=funcargs,
        context=context,
        allow_incomplete=allow_incomplete,
        validate=validate,
        overrides=overrides,
        enable_async_model_field=enable_async_model_field,
        resolve_mapped_ctx_=resolve_mapped_ctx,
    )


async def inject_args(
    func: Callable[..., Any],
    context: Union[Dict[Union[str, Type[Any]], Any], Any],
    allow_incomplete: bool = True,
    validate: bool = True,
    overrides: Optional[
        Union[Dict[Callable[..., Any], Callable[..., Any]], "Provider"]
    ] = None,
    use_global_provider: bool = False,
    stack: Optional[AsyncExitStack] = None,
    enable_async_model_field: bool = False,
    ordered: bool = False,
) -> Callable[..., Any]:
    """
    Inject arguments into function with dependency injection and optional ordering optimization.

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
        overrides: Dependency overrides - can be:
                  - Dict mapping original functions to replacements (legacy)
                  - Provider instance for advanced override management
        use_global_provider: Whether to use the global provider for overrides
        stack: Optional AsyncExitStack for context managers
        enable_async_model_field: Whether to enable async model field injection
        ordered: If True, uses optimized execution with pre-computed sync/async separation
                and order-based batching for maximum performance (default: False)

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

        Optimized injection with ordering:
        ```python
        # Use ordered=True for maximum performance
        injected = await inject_args(greet, context, ordered=True)
        result = injected()  # Same result, optimized execution
        ```

        Async dependency functions with ordering:
        ```python
        async def get_user_service() -> UserService:
            return await UserService.create()

        def handle_request(
            service: UserService = DependsInject(get_user_service, order=1)
        ):
            return service.get_current_user()

        context = {}  # Dependencies resolved automatically
        injected = await inject_args(handle_request, context, ordered=True)
        result = injected()
        ```

    Performance Notes:
        - Standard mode: Uses isinstance() checks to separate sync and async resolvers
        - Ordered mode (ordered=True): Pre-computes sync/async separation and ordering
          for maximum runtime performance, eliminates isinstance checks
        - Async dependencies are resolved concurrently for maximum performance
        - Supports chaining multiple injections on the same function
        - Name-based injection takes precedence over type-based injection
        - Recursive dependencies automatically use the same execution strategy
    """
    # Resolve final overrides from provider or legacy parameter
    from ctxinject.overrides import Provider, resolve_overrides

    if overrides is None or isinstance(overrides, Provider):
        # No overrides provided, just use global if enabled
        resolved_overrides = resolve_overrides(
            local_provider=None, use_global=use_global_provider
        )
    elif isinstance(overrides, dict):
        # Legacy dict format - convert to resolved format
        global_overrides = (
            resolve_overrides(local_provider=None, use_global=use_global_provider)
            if use_global_provider
            else {}
        )
        resolved_overrides = {**global_overrides, **overrides}
    else:
        raise TypeError(f"overrides must be Dict or Provider, got {type(overrides)}")

    if not isinstance(context, dict):
        context = {type(context): context}
    context_list = list(context.keys())

    get_mapped_ctx_ = get_mapped_ctx_ordered if ordered else get_mapped_ctx
    resolve_mapped_ctx_ = resolve_mapped_ctx_ordered if ordered else resolve_mapped_ctx

    mapped_ctx = get_mapped_ctx_(
        func=func,
        context=context_list,
        allow_incomplete=allow_incomplete,
        validate=validate,
        overrides=resolved_overrides,
        enable_async_model_field=enable_async_model_field,
        resolve_mapped_ctx=resolve_mapped_ctx_,
    )
    resolved = await resolve_mapped_ctx_(context, mapped_ctx, stack)
    return partial(func, **resolved)


class OrderedMappedCtx:
    """
    Pre-computed execution plan with optimized sync/async separation and ordering.

    This class holds a pre-processed version of mapped context that eliminates
    runtime overhead by separating sync and async resolvers at creation time
    and pre-sorting async resolvers by their execution order.

    Attributes:
        sync_resolvers: Dict of sync resolvers that can be executed immediately
        async_order_batches: Dict of async resolvers grouped by order for batch execution
        has_async: Boolean flag to quickly check if async resolution is needed

    Performance Benefits:
        - Eliminates runtime isinstance() checks
        - Eliminates runtime sorting and grouping operations
        - Enables direct execution without type inspection
        - Optimizes async batch execution by pre-computed ordering
    """

    def __init__(
        self,
        sync_resolvers: Dict[str, BaseResolver],
        async_order_batches: Dict[int, Dict[str, BaseResolver]],
        has_async: bool = None,
    ) -> None:
        self.sync_resolvers = sync_resolvers
        self.async_order_batches = async_order_batches
        self.has_async = (
            has_async if has_async is not None else bool(async_order_batches)
        )

    @classmethod
    def from_mapped_ctx(cls, mapped_ctx: Dict[str, BaseResolver]) -> "OrderedMappedCtx":
        sync_resolvers = {}
        async_batches = defaultdict(dict)

        for key, resolver in mapped_ctx.items():
            if resolver.isasync:
                tgt_dict = async_batches[resolver.order]
            else:
                tgt_dict = sync_resolvers
            tgt_dict[key] = resolver

        sorted_async_batches = dict(sorted(async_batches.items()))

        return cls(
            sync_resolvers=sync_resolvers,
            async_order_batches=sorted_async_batches,
            has_async=bool(async_batches),
        )


def get_mapped_ctx_ordered(
    func: Callable[..., Any],
    context: Container[Union[str, Type[Any]]],
    allow_incomplete: bool = True,
    validate: bool = True,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
    enable_async_model_field: bool = False,
    resolve_mapped_ctx: Optional[Callable[..., Any]] = None,
) -> OrderedMappedCtx:
    """
    Get mapped context with pre-computed ordering optimization.

    This function creates an OrderedMappedCtx with pre-separated sync and async
    resolvers, eliminating runtime type checking and sorting for maximum performance.

    Args:
        func: The function to analyze and create resolvers for
        context: Injection context containing values, types, and model instances
        allow_incomplete: Whether to allow missing dependencies (default: True)
        validate: Whether to apply validation if defined (default: True)
        overrides: Optional mapping to override dependency functions
        enable_async_model_field: Whether to enable async model field injection
        resolve_mapped_ctx: Optional custom resolver function for recursive dependencies

    Returns:
        OrderedMappedCtx with pre-computed sync/async separation and ordering

    Raises:
        UnresolvedInjectableError: When allow_incomplete=False and dependencies are missing

    Example:
        ```python
        def my_func(name: str, count: int = ArgsInjectable(42)):
            return f"{name}: {count}"

        context = {"name": "test", int: 100}
        ordered_ctx = get_mapped_ctx_ordered(my_func, context)

        # Use with resolve_mapped_ctx_ordered for optimized execution
        resolved = await resolve_mapped_ctx_ordered(context, ordered_ctx)
        ```

    Note:
        This is used internally by inject_args(ordered=True) for maximum performance.
        The returned OrderedMappedCtx pre-computes execution structure to eliminate
        runtime overhead during resolution.
    """
    mapped_ctx = get_mapped_ctx(
        func=func,
        context=context,
        allow_incomplete=allow_incomplete,
        validate=validate,
        overrides=overrides,
        enable_async_model_field=enable_async_model_field,
        resolve_mapped_ctx=resolve_mapped_ctx_ordered,
    )
    return OrderedMappedCtx.from_mapped_ctx(mapped_ctx)


async def resolve_mapped_ctx_ordered(
    input_ctx: Dict[Union[str, Type[Any]], Any],
    mapped_ctx: OrderedMappedCtx,
    stack: Optional[AsyncExitStack] = None,
) -> Dict[Any, Any]:
    """
    Resolve OrderedMappedCtx with maximum performance optimization.

    This function resolves dependencies using a pre-computed execution plan that
    eliminates runtime isinstance checks, sorting, and grouping operations.

    Performance optimizations:
    - No runtime isinstance() checks (resolvers pre-categorized)
    - No runtime sorting or grouping (async batches pre-ordered)
    - Direct execution of sync resolvers without type checking
    - Order-based batch execution of async resolvers

    Args:
        input_ctx: The original injection context containing values and types
        mapped_ctx: Pre-computed OrderedMappedCtx from get_mapped_ctx_ordered()
        stack: Optional AsyncExitStack for context manager support

    Returns:
        Dictionary with resolved argument names and their values

    Raises:
        Any exceptions from resolver execution are preserved and re-raised

    Example:
        ```python
        # Get optimized mapped context
        ordered_ctx = get_mapped_ctx_ordered(my_function, context)

        # Resolve with maximum performance
        resolved = await resolve_mapped_ctx_ordered(context, ordered_ctx)

        # Use resolved values
        result = my_function(**resolved)
        ```

    Note:
        This is used internally by inject_args(ordered=True). The OrderedMappedCtx
        must be created by get_mapped_ctx_ordered() to ensure proper pre-computation.
        For standard resolution, use resolve_mapped_ctx() instead.
    """

    if not mapped_ctx:
        return {}

    results = {}

    for key, resolver in mapped_ctx.sync_resolvers.items():
        try:
            result = resolver(input_ctx, stack)
            results[key] = result
        except Exception:
            raise
    for async_mapped_ctx in mapped_ctx.async_order_batches.values():

        keys = async_mapped_ctx.keys()
        async_tasks = [
            resolver(input_ctx, stack) for resolver in async_mapped_ctx.values()
        ]
        await run_async_tasks(
            async_tasks=async_tasks, async_keys=list(keys), results=results
        )
    return results
