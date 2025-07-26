import asyncio
import inspect
from functools import partial
from typing import Any, Callable, Dict, Iterable, Optional, Type, Union

from typemapping import VarTypeInfo, get_field_type, get_func_args

from ctxinject.model import ArgsInjectable, CallableInjectable, ModelFieldInject


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


class AsyncResolver:
    """Asynchronous resolver wrapper for optimal performance."""

    __slots__ = ("_func",)

    def __init__(self, func: Callable[..., Any]) -> None:
        """Initialize async resolver with a callable."""
        self._func = func

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Execute the async resolver function."""
        return self._func(context)


class BaseSyncResolver:
    """Base class for all synchronous resolvers."""

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Execute the resolver function."""
        raise NotImplementedError(
            "Subclasses must implement __call__"
        )  # pragma: no cover

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(...)"  # pragma: no cover


class FuncResolver(BaseSyncResolver):
    """Synchronous resolver wrapper from function."""

    __slots__ = ("_func",)

    def __init__(self, func: Callable[[Dict[Any, Any]], Any]) -> None:
        """Initialize function resolver."""
        self._func = func

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Execute the wrapped function with context."""
        return self._func(context)


class NameResolver(BaseSyncResolver):
    """Resolves by argument name from context."""

    __slots__ = ("_arg_name",)

    def __init__(self, arg_name: str) -> None:
        """Initialize name-based resolver."""
        self._arg_name = arg_name

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Resolve value by name from context."""
        return context[self._arg_name]


class TypeResolver(BaseSyncResolver):
    """Resolves by type from context."""

    __slots__ = ("_target_type",)

    def __init__(self, target_type: Type[Any]) -> None:
        """Initialize type-based resolver."""
        self._target_type = target_type

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Resolve value by type from context."""
        return context[self._target_type]


class DefaultResolver(BaseSyncResolver):
    """Resolver that returns a pre-configured default value."""

    __slots__ = ("_default_value",)

    def __init__(self, default_value: Any) -> None:
        """Initialize default value resolver."""
        self._default_value = default_value

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Return the pre-configured default value."""
        return self._default_value


class ModelFieldResolver(BaseSyncResolver):
    """Resolver that extracts field/method from model instance in context."""

    __slots__ = ("_model_type", "_field_name")

    def __init__(self, model_type: Type[Any], field_name: str) -> None:
        """Initialize model field resolver."""
        self._model_type = model_type
        self._field_name = field_name

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Extract field or call method from model instance."""
        method = getattr(context[self._model_type], self._field_name)
        return method() if callable(method) else method


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

    Internal function that analyzes function arguments and creates appropriate
    resolvers for each parameter based on the injection context.
    """
    ctx: Dict[str, Any] = {}
    overrides = overrides or {}

    for arg in args:
        instance = arg.getinstance(ArgsInjectable)
        default_ = instance.default if instance else None
        bt = arg.basetype
        value: Union[BaseSyncResolver, AsyncResolver, None] = None

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

            async def resolver(
                actual_ctx: Dict[Any, Any],
                f: Callable[..., Any] = dep_func,
                ctx_map: Dict[Any, Any] = dep_ctx_map,
            ) -> Any:
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
            value = NameResolver(arg_name=arg.name)
        # by model field/method
        elif instance is not None:
            if isinstance(instance, ModelFieldInject):
                tgtmodel = instance.model
                tgt_field = instance.field or arg.name
                if tgtmodel in context and get_field_type(tgtmodel, tgt_field):
                    value = ModelFieldResolver(
                        model_type=tgtmodel, field_name=tgt_field
                    )
        # by type
        if value is None and bt is not None and bt in context:
            value = TypeResolver(target_type=bt)
        # by default
        if value is None and default_ is not None and default_ is not Ellipsis:
            value = DefaultResolver(default_value=default_)

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
                else:
                    validated_func = partial(
                        wrap_validate_sync,
                        func=value,
                        instance=validation_instance,
                        bt=arg.basetype,
                        name=arg.name,
                    )
                    value = FuncResolver(validated_func)

            ctx[arg.name] = value

    return ctx


def get_mapped_ctx(
    func: Callable[..., Any],
    context: Dict[Union[str, Type[Any]], Any],
    allow_incomplete: bool = True,
    validate: bool = True,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
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
    return map_ctx(funcargs, context, allow_incomplete, validate, overrides)


async def inject_args(
    func: Callable[..., Any],
    context: Dict[Union[str, Type[Any]], Any],
    allow_incomplete: bool = True,
    validate: bool = True,
    overrides: Optional[Dict[Callable[..., Any], Callable[..., Any]]] = None,
) -> partial[Any]:
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
    mapped_ctx = get_mapped_ctx(func, context, allow_incomplete, validate, overrides)
    resolved = await resolve_mapped_ctx(context, mapped_ctx)
    return partial(func, **resolved)
