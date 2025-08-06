import asyncio
import inspect
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Callable, ContextManager, Dict, Type, Union

import anyio


class BaseResolver:
    """Base class for all synchronous resolvers."""

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Execute the resolver function."""
        raise NotImplementedError(
            "Subclasses must implement __call__"
        )  # pragma: no cover

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(...)"  # pragma: no cover


class AsyncResolver(BaseResolver):
    """Asynchronous resolver wrapper for optimal performance."""

    __slots__ = ("_func",)

    def __init__(self, func: Callable[..., Any]) -> None:
        """Initialize async resolver with a callable."""
        self._func = func

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Execute the async resolver function."""
        return self._func(context)


class FuncResolver(BaseResolver):
    """Synchronous resolver wrapper from function."""

    __slots__ = ("_func",)

    def __init__(self, func: Callable[[Dict[Any, Any]], Any]) -> None:
        """Initialize function resolver."""
        self._func = func

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Execute the wrapped function with context."""
        return self._func(context)


class NameResolver(BaseResolver):
    """Resolves by argument name from context."""

    __slots__ = ("_arg_name",)

    def __init__(self, arg_name: str) -> None:
        """Initialize name-based resolver."""
        self._arg_name = arg_name

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Resolve value by name from context."""
        return context[self._arg_name]


class TypeResolver(BaseResolver):
    """Resolves by type from context."""

    __slots__ = ("_target_type",)

    def __init__(self, target_type: Type[Any]) -> None:
        """Initialize type-based resolver."""
        self._target_type = target_type

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Resolve value by type from context."""
        return context[self._target_type]


class DefaultResolver(BaseResolver):
    """Resolver that returns a pre-configured default value."""

    __slots__ = ("_default_value",)

    def __init__(self, default_value: Any) -> None:
        """Initialize default value resolver."""
        self._default_value = default_value

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Return the pre-configured default value."""
        return self._default_value


class ModelFieldResolver(BaseResolver):
    """Resolver that extracts field/method from model instance in context."""

    __slots__ = ("_model_type", "_field_name")

    def __init__(self, model_type: Type[Any], field_name: str) -> None:
        """Initialize model field resolver."""
        self._model_type = model_type
        self._field_name = field_name

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Extract field or call method from model instance."""
        obj = context[self._model_type]
        fields = self._field_name.split(".")

        for field_name in fields:
            if obj is None:
                return None

            if not hasattr(obj, field_name):
                raise AttributeError(
                    f"'{type(obj).__name__}' object has no attribute '{field_name}'"
                )

            attr = getattr(obj, field_name)
            obj = attr() if callable(attr) else attr
        return obj


class SyncDependsResolver(BaseResolver):
    """Resolver for synchronous dependency functions."""

    __slots__ = ("_func", "_ctx_map")

    def __init__(self, func: Callable[..., Any], ctx_map: Dict[str, Any]) -> None:
        """Initialize sync dependency resolver."""
        self._func = func
        self._ctx_map = ctx_map

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """
        Resolve sync dependency.

        Note: This can't resolve the dependency fully since ctx_map might contain
        async resolvers. Should be called by ContextResolver.resolve().
        """
        raise RuntimeError(
            "SyncDependsResolver cannot be resolved independently. "
            "Use ContextResolver.resolve() instead."
        )

    def resolve_sync(self, resolved_ctx: Dict[str, Any]) -> Any:
        """
        Resolve sync dependency with already-resolved context.

        Args:
            resolved_ctx: Dictionary with all sub-dependencies already resolved

        Returns:
            Result of calling the dependency function
        """
        return self._func(**resolved_ctx)


class AsyncDependsResolver(AsyncResolver):
    """Resolver for asynchronous dependency functions."""

    __slots__ = ("_func", "_ctx_map")

    def __init__(self, func: Callable[..., Any], ctx_map: Dict[str, Any]) -> None:
        """Initialize async dependency resolver."""
        self._func = func
        self._ctx_map = ctx_map

    async def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """
        Resolve async dependency.

        Note: This can't resolve the dependency fully since ctx_map might contain
        other resolvers. Should be called by ContextResolver.resolve().
        """
        raise RuntimeError(
            "AsyncDependsResolver cannot be resolved independently. "
            "Use ContextResolver.resolve() instead."
        )

    async def resolve_async(self, resolved_ctx: Dict[str, Any]) -> Any:
        """
        Resolve async dependency with already-resolved context.

        Args:
            resolved_ctx: Dictionary with all sub-dependencies already resolved

        Returns:
            Result of calling the dependency function (awaited if coroutine)
        """
        if inspect.iscoroutinefunction(self._func):
            return await self._func(**resolved_ctx)
        else:
            # Function might return a coroutine even if not declared as async
            result = self._func(**resolved_ctx)
            if inspect.iscoroutine(result):
                return await result
            return result


# -----------------CM RESOLVERS---------------------


def is_gen_callable(call: Callable[..., Any]) -> bool:
    """Check if callable is a generator function or wrapped generator."""
    # Direct generator function
    if inspect.isgeneratorfunction(call):
        return True

    # Check __call__ method
    dunder_call = getattr(call, "__call__", None)
    if dunder_call and inspect.isgeneratorfunction(dunder_call):
        return True

    # Check if it's a contextmanager-wrapped function
    if hasattr(call, "__wrapped__"):
        return inspect.isgeneratorfunction(call.__wrapped__)

    # Check if it's a contextmanager instance
    if hasattr(call, "func"):  # contextmanager objects have .func attribute
        return inspect.isgeneratorfunction(call.func)

    return False


def is_async_gen_callable(call: Callable[..., Any]) -> bool:
    """Check if callable is an async generator function or wrapped async generator."""
    # Direct async generator function
    if inspect.isasyncgenfunction(call):
        return True

    # Check __call__ method
    dunder_call = getattr(call, "__call__", None)
    if dunder_call and inspect.isasyncgenfunction(dunder_call):
        return True

    # Check if it's an asynccontextmanager-wrapped function
    if hasattr(call, "__wrapped__"):
        return inspect.isasyncgenfunction(call.__wrapped__)

    # Check if it's an asynccontextmanager instance
    if hasattr(call, "func"):  # asynccontextmanager objects have .func attribute
        return inspect.isasyncgenfunction(call.func)

    return False


def is_contextmanager_callable(call: Callable[..., Any]) -> bool:
    """Check if callable returns a context manager (generator-based)."""
    return is_gen_callable(call)


def is_async_contextmanager_callable(call: Callable[..., Any]) -> bool:
    """Check if callable returns an async context manager."""
    return is_async_gen_callable(call)


@asynccontextmanager
async def contextmanager_in_threadpool(
    cm_func: Callable[..., Any], **kwargs: Any
) -> AsyncGenerator[Any, None]:
    """Execute sync context manager function in thread pool with proper cleanup."""

    resource_holder = {}
    exception_holder = {}

    def enter_context():
        """Run in thread: create CM and enter it."""
        try:
            # Call the context manager function to get the actual context manager
            cm = cm_func(**kwargs)
            # Enter the context manager
            resource = cm.__enter__()
            resource_holder["cm"] = cm
            resource_holder["resource"] = resource
        except Exception as e:
            exception_holder["enter_error"] = e

    def exit_context(exc_type, exc_val, exc_tb):
        """Run in thread: exit the context manager."""
        try:
            if "cm" in resource_holder:
                return resource_holder["cm"].__exit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            exception_holder["exit_error"] = e
            return False
        return False

    # Enter the context manager in thread pool
    await anyio.to_thread.run_sync(enter_context)

    if "enter_error" in exception_holder:
        raise exception_holder["enter_error"]

    try:
        yield resource_holder["resource"]
    except Exception as e:
        # Exit with exception info
        exit_limiter = anyio.CapacityLimiter(1)
        ok = await anyio.to_thread.run_sync(
            exit_context, type(e), e, e.__traceback__, limiter=exit_limiter
        )
        if "exit_error" in exception_holder:
            raise exception_holder["exit_error"]
        if not ok:
            raise e
    else:
        # Exit normally
        exit_limiter = anyio.CapacityLimiter(1)
        await anyio.to_thread.run_sync(
            exit_context, None, None, None, limiter=exit_limiter
        )
        if "exit_error" in exception_holder:
            raise exception_holder["exit_error"]


class SyncContextManagerResolver(BaseResolver):
    """Resolver for synchronous context managers."""

    __slots__ = ("_func", "_ctx_map")

    def __init__(self, func: Callable[..., Any], ctx_map: Dict[str, Any]) -> None:
        """Initialize sync context manager resolver."""
        self._func = func
        self._ctx_map = ctx_map

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """This should not be called directly - use resolve_with_stack instead."""
        raise RuntimeError(
            "SyncContextManagerResolver cannot be resolved without ExitStack. "
            "Use ContextResolver.resolve() instead."
        )

    def resolve_with_stack(
        self, context: Dict[Union[str, Type[Any]], Any], stack: ExitStack
    ) -> Any:
        """Resolve sync context manager using provided ExitStack."""
        # This would need sync version of resolve_mapped_ctx
        # For now, raise error indicating this needs implementation
        raise NotImplementedError(
            "Sync context manager resolution requires sync resolve_mapped_ctx implementation"
        )


class AsyncContextManagerResolver(AsyncResolver):
    """Resolver for asynchronous context managers."""

    __slots__ = ("_func", "_ctx_map", "_is_sync_cm")

    def __init__(
        self,
        func: Callable[..., Any],
        ctx_map: Dict[str, Any],
        is_sync_cm: bool = False,
    ) -> None:
        """
        Initialize async context manager resolver.

        Args:
            func: The context manager function
            ctx_map: Mapped context for resolving function dependencies
            is_sync_cm: Whether this is a sync CM being used in async context
        """
        # Don't call super().__init__ since we have different signature
        self._func = func
        self._ctx_map = ctx_map
        self._is_sync_cm = is_sync_cm

    async def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """This should not be called directly - use resolve_with_stack instead."""
        raise RuntimeError(
            "AsyncContextManagerResolver cannot be resolved without AsyncExitStack. "
            "Use ContextResolver.resolve() instead."
        )

    async def resolve_with_stack(
        self, context: Dict[Union[str, Type[Any]], Any], stack: AsyncExitStack
    ) -> Any:
        """Resolve async context manager using provided AsyncExitStack."""
        from ctxinject.inject import resolve_mapped_ctx

        # Resolve dependencies for the context manager function
        sub_kwargs = await resolve_mapped_ctx(context, self._ctx_map)

        if self._is_sync_cm:
            # Sync context manager in async context - use threadpool
            async_cm = contextmanager_in_threadpool(self._func, **sub_kwargs)
            return await stack.enter_async_context(async_cm)
        else:
            # Native async context manager
            # Call the function to get the actual async context manager
            async_cm = self._func(**sub_kwargs)
            return await stack.enter_async_context(async_cm)


# Factory functions for creating appropriate resolvers
def create_context_manager_resolver(
    func: Callable[..., Any], ctx_map: Dict[str, Any]
) -> Union[SyncContextManagerResolver, AsyncContextManagerResolver]:
    """
    Create appropriate context manager resolver based on function type.

    Args:
        func: The dependency function (should be a context manager)
        ctx_map: Mapped context for resolving function dependencies

    Returns:
        Appropriate resolver for the context manager type

    Raises:
        ValueError: If function is not a context manager
    """
    if is_async_gen_callable(func):
        return AsyncContextManagerResolver(func, ctx_map, is_sync_cm=False)
    elif is_gen_callable(func):
        # For now, we'll use async resolver even for sync CM for simplicity
        # This allows sync CM to work in async contexts via threadpool
        return AsyncContextManagerResolver(func, ctx_map, is_sync_cm=True)
    else:
        raise ValueError(
            f"Function {func} is not a context manager (not a generator function)"
        )


def detect_dependency_type(func: Callable[..., Any]) -> str:
    """
    Detect the type of dependency function.

    Returns:
        'async_context_manager', 'sync_context_manager', 'async_function', 'sync_function'
    """
    if is_async_gen_callable(func):
        return "async_context_manager"
    elif is_gen_callable(func):
        return "sync_context_manager"
    elif inspect.iscoroutinefunction(func):
        return "async_function"
    else:
        return "sync_function"


# -------------FACTORIES----------------


def create_dependency_resolver(
    func: Callable[..., Any], ctx_map: Dict[str, Any]
) -> Union[SyncDependsResolver, AsyncDependsResolver]:
    """
    Create appropriate dependency resolver based on function type.

    Args:
        func: The dependency function
        ctx_map: Mapped context for resolving function dependencies

    Returns:
        Appropriate resolver for the function type
    """
    if inspect.iscoroutinefunction(func):
        return AsyncDependsResolver(func, ctx_map)
    else:
        # For sync functions, we still need to check if they might return coroutines
        # or if their dependencies are async, so we use AsyncDependsResolver
        #
        # We could optimize this further by analyzing ctx_map to see if it contains
        # any async resolvers, but for simplicity, let's use async resolver
        # which can handle both cases
        return AsyncDependsResolver(func, ctx_map)


def detect_function_type(func: Callable[..., Any]) -> str:
    """
    Detect the type of function.

    Returns:
        'async_function' or 'sync_function'
    """
    if inspect.iscoroutinefunction(func):
        return "async_function"
    else:
        return "sync_function"


# Update to be used in map_ctx
def create_callable_resolver(
    func: Callable[..., Any], ctx_map: Dict[str, Any]
) -> Union[SyncDependsResolver, AsyncDependsResolver]:
    """
    Create the appropriate resolver for a CallableInjectable.

    This replaces the current single async resolver approach with
    specialized resolvers based on function type.
    """
    # Check if it's a context manager first
    if is_async_gen_callable(func):
        return create_context_manager_resolver(func, ctx_map)
    elif is_gen_callable(func):
        return create_context_manager_resolver(func, ctx_map)
    else:
        # Regular function - create dependency resolver
        return create_dependency_resolver(func, ctx_map)


# --------------------------CTXRESOLVER--------------------------


class ContextResolver:
    def __init__(self):
        self._sync_stack: Optional[ExitStack] = None
        self._async_stack: Optional[AsyncExitStack] = None

    async def resolve(
        self, input_ctx: Dict[Union[str, Type[Any]], Any], mapped_ctx: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve mapped context with automatic context manager lifecycle.

        Replacement for resolve_mapped_ctx() with CM support.
        """
        if not mapped_ctx:
            return {}

        # Categorize resolvers by type
        sync_resolvers = {}
        async_resolvers = {}
        sync_cm_resolvers = {}
        async_cm_resolvers = {}
        sync_depends_resolvers = {}
        async_depends_resolvers = {}

        # Import here to avoid circular imports
        from ctxinject.sync_async_dependency_resolvers import (
            AsyncDependsResolver,
            SyncDependsResolver,
        )

        for key, resolver in mapped_ctx.items():
            if isinstance(resolver, AsyncContextManagerResolver):
                async_cm_resolvers[key] = resolver
            elif isinstance(resolver, SyncContextManagerResolver):
                sync_cm_resolvers[key] = resolver
            elif isinstance(resolver, AsyncDependsResolver):
                async_depends_resolvers[key] = resolver
            elif isinstance(resolver, SyncDependsResolver):
                sync_depends_resolvers[key] = resolver
            elif isinstance(resolver, AsyncResolver):
                async_resolvers[key] = resolver
            else:
                sync_resolvers[key] = resolver

        return await self._resolve_optimized(
            input_ctx,
            sync_resolvers,
            async_resolvers,
            sync_cm_resolvers,
            async_cm_resolvers,
            sync_depends_resolvers,
            async_depends_resolvers,
        )

    async def _resolve_optimized(
        self,
        input_ctx: Dict[Union[str, Type[Any]], Any],
        sync_resolvers: Dict[str, Any],
        async_resolvers: Dict[str, Any],
        sync_cm_resolvers: Dict[str, Any],
        async_cm_resolvers: Dict[str, Any],
        sync_depends_resolvers: Dict[str, Any],
        async_depends_resolvers: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute resolvers in optimized order with proper lifecycle management.

        Order:
        1. Launch all async operations (regular + CM + depends) concurrently
        2. Execute sync operations (regular + depends) immediately
        3. Resolve sync CM dependencies if needed
        4. Await all async operations
        5. Return combined results

        Context managers are properly managed with ExitStack/AsyncExitStack.
        """
        results = {}

        # Initialize stacks for context managers
        async with AsyncExitStack() as async_stack:
            # Phase 1: Launch async operations (don't await yet)
            async_tasks = []
            async_keys = []

            # Launch regular async resolvers
            for key, resolver in async_resolvers.items():
                task = asyncio.create_task(resolver(input_ctx))
                async_tasks.append(task)
                async_keys.append(key)

            # Launch async context manager resolvers
            for key, resolver in async_cm_resolvers.items():
                task = asyncio.create_task(
                    resolver.resolve_with_stack(input_ctx, async_stack)
                )
                async_tasks.append(task)
                async_keys.append(key)

            # Phase 2: Execute sync operations immediately

            # Regular sync resolvers
            for key, resolver in sync_resolvers.items():
                try:
                    results[key] = resolver(input_ctx)
                except Exception:
                    # Cancel pending async tasks before re-raising
                    for task in async_tasks:
                        task.cancel()
                    raise

            # Sync context managers (if any - currently not implemented)
            if sync_cm_resolvers:
                # For now, raise error since sync CM resolution needs more work
                raise NotImplementedError(
                    "Sync context manager resolution not yet implemented. "
                    "Use async context managers or implement sync resolve_mapped_ctx."
                )

            # Dependency resolvers need special handling because they have sub-dependencies
            all_depends_resolvers = {
                **sync_depends_resolvers,
                **async_depends_resolvers,
            }

            if all_depends_resolvers:
                # Resolve all dependency sub-contexts first
                depends_resolved = await self._resolve_dependency_resolvers(
                    input_ctx, all_depends_resolvers, async_stack
                )

                # Add resolved dependencies to results
                results.update(depends_resolved)

            # Phase 3: Await all regular async operations
            if async_tasks:
                try:
                    async_results = await asyncio.gather(
                        *async_tasks, return_exceptions=True
                    )

                    # Process results and handle exceptions
                    for key, result in zip(async_keys, async_results):
                        if isinstance(result, Exception):
                            raise result
                        results[key] = result

                except Exception:
                    # Exception handling - async_stack will cleanup automatically
                    raise

        # async_stack cleanup happens automatically here
        return results

    async def _resolve_dependency_resolvers(
        self,
        input_ctx: Dict[Union[str, Type[Any]], Any],
        depends_resolvers: Dict[str, Any],
        async_stack: AsyncExitStack,
    ) -> Dict[str, Any]:
        """
        Resolve dependency resolvers by first resolving their sub-dependencies.

        This is a 2-phase process:
        1. Resolve all sub-dependencies for each dependency resolver
        2. Execute the dependency functions with resolved sub-dependencies
        """
        from ctxinject.inject import resolve_mapped_ctx

        results = {}
        async_depends_tasks = []
        async_depends_keys = []

        for key, resolver in depends_resolvers.items():
            # Resolve the sub-dependencies for this dependency resolver
            sub_resolved = await resolve_mapped_ctx(input_ctx, resolver._ctx_map)

            if isinstance(resolver, AsyncDependsResolver):
                # Launch async dependency resolution
                task = asyncio.create_task(resolver.resolve_async(sub_resolved))
                async_depends_tasks.append(task)
                async_depends_keys.append(key)
            elif isinstance(resolver, SyncDependsResolver):
                # Execute sync dependency immediately
                results[key] = resolver.resolve_sync(sub_resolved)

        # Await async dependency resolutions
        if async_depends_tasks:
            async_results = await asyncio.gather(
                *async_depends_tasks, return_exceptions=True
            )

            for key, result in zip(async_depends_keys, async_results):
                if isinstance(result, Exception):
                    raise result
                results[key] = result

        return results
