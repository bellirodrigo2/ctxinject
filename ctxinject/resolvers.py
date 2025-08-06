import inspect
from typing import Any, Callable, Dict, Type, Union

from ctxinject.model import Injectable


class BaseResolver:
    """Base class for all synchronous resolvers."""

    __slots__ = "isasync"

    def __init__(self, isasync: bool = False) -> None:
        """Initialize the base resolver."""
        self.isasync = isasync

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Execute the resolver function."""
        raise NotImplementedError(
            "Subclasses must implement __call__"
        )  # pragma: no cover

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(...)"  # pragma: no cover


class FuncResolver(BaseResolver):
    """Synchronous resolver wrapper from function."""

    __slots__ = "_func"

    def __init__(self, func: Callable[[Dict[Any, Any]], Any], isasync: bool) -> None:
        """Initialize function resolver."""
        self._func = func
        super().__init__(isasync)

    def __call__(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Execute the wrapped function with context."""
        return self._func(context)


class ValidateResolver(FuncResolver):
    __slots__ = ("_func_inner", "_instance", "_bt")

    def __init__(
        self,
        func: BaseResolver,
        instance: Injectable,
        bt: Type[Any],
    ) -> None:
        self._func_inner = func
        self._instance = instance
        self._bt = bt

        if True:
            call_func = (
                self._wrap_validate_async if func.isasync else self._wrap_validate_sync
            )
        else:
            call_func = self._func_inner
        super().__init__(call_func, func.isasync)

    def _wrap_validate_sync(
        self,
        context: Dict[Union[str, Type[Any]], Any],
    ) -> Any:
        """Sync validation wrapper - validates immediately."""
        value = self._func_inner(context)
        validated = self._instance.validate(value, self._bt)
        return validated

    async def _wrap_validate_async(
        self,
        context: Dict[Union[str, Type[Any]], Any],
    ) -> Any:
        """Async validation wrapper - awaits value before validation."""
        value = await self._func_inner(context)
        validated = self._instance.validate(value, self._bt)  # Validator always sync
        return validated


class NameResolver(FuncResolver):
    """Resolves by argument name from context."""

    __slots__ = ("_arg_name",)

    def __init__(self, arg_name: str) -> None:
        """Initialize name-based resolver."""
        self._arg_name = arg_name
        super().__init__(self._resolve_by_name, False)

    def _resolve_by_name(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Resolve value by name from context."""
        return context[self._arg_name]


class TypeResolver(FuncResolver):
    """Resolves by type from context."""

    __slots__ = ("_target_type",)

    def __init__(self, target_type: Type[Any]) -> None:
        """Initialize type-based resolver."""
        self._target_type = target_type
        super().__init__(self._resolve_by_type, False)

    def _resolve_by_type(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Resolve value by type from context."""
        return context[self._target_type]


class DefaultResolver(FuncResolver):
    """Resolver that returns a pre-configured default value."""

    __slots__ = ("_default_value",)

    def __init__(self, default_value: Any) -> None:
        """Initialize default value resolver."""
        self._default_value = default_value
        super().__init__(self._return_default, False)

    def _return_default(self, _: Dict[Union[str, Type[Any]], Any]) -> Any:
        """Return the pre-configured default value."""
        return self._default_value


class ModelFieldResolver(FuncResolver):
    """Resolver that extracts field/method from model instance in context."""

    __slots__ = ("_model_type", "_field_name")

    def __init__(self, model_type: Type[Any], field_name: str) -> None:
        """Initialize model field resolver."""
        self._model_type = model_type
        self._field_name = field_name
        super().__init__(self._extract_field, False)

    def _extract_field(self, context: Dict[Union[str, Type[Any]], Any]) -> Any:
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


class DependsResolver(FuncResolver):
    """Resolver for async dependencies using a callable."""

    __slots__ = ("_func_inner", "_ctx_map", "_resolve_mapped_ctx")

    def __init__(
        self,
        func_inner: Callable[..., Any],
        ctx_map: Dict[Any, Any],
        resolve_mapped_ctx: Callable[..., Any],
    ) -> None:
        self._func_inner = func_inner
        self._ctx_map = ctx_map
        self._resolve_mapped_ctx = resolve_mapped_ctx
        super().__init__(self._resolve_dependency, True)

    async def _resolve_dependency(
        self, context: Dict[Union[str, Type[Any]], Any]
    ) -> Any:
        sub_kwargs = await self._resolve_mapped_ctx(context, self._ctx_map)
        func = self._func_inner
        result = func(**sub_kwargs)
        if inspect.iscoroutinefunction(func) or inspect.iscoroutine(result):
            return await result
        return result
