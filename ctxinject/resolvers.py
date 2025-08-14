import inspect
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from typing import Any, Callable, Dict, Optional, Type, Union

from ctxinject.model import Injectable, is_async_gen_callable, is_gen_callable
from ctxinject.runner import contextmanager_in_threadpool, run_in_threadpool


class BaseResolver:
    """Base class for all synchronous resolvers."""

    __slots__ = ("isasync", "order")

    def __init__(self, order: int, isasync: bool = False) -> None:
        self.isasync = isasync
        self.order = order

    def __call__(self, context: Dict[Union[str, Type[Any]], Any], *args: Any) -> Any:
        raise NotImplementedError()  # pragma: no cover

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(...)"  # pragma: no cover


class FuncResolver(BaseResolver):
    """Synchronous resolver wrapper from function."""

    __slots__ = "_func"

    def __init__(
        self, func: Callable[[Dict[Any, Any]], Any], isasync: bool, order: int = 0
    ) -> None:
        self._func = func
        super().__init__(
            order,
            isasync,
        )

    def __call__(self, context: Dict[Union[str, Type[Any]], Any], *args: Any) -> Any:
        return self._func(context, *args)


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

        call_func = (
            self._wrap_validate_async if func.isasync else self._wrap_validate_sync
        )
        super().__init__(call_func, func.isasync, order=func.order)

    def _wrap_validate_sync(
        self, context: Dict[Union[str, Type[Any]], Any], *args: Any
    ) -> Any:
        value = self._func_inner(context)
        validated = self._instance.validate(value, self._bt)
        return validated

    async def _wrap_validate_async(
        self, context: Dict[Union[str, Type[Any]], Any], *args: Any
    ) -> Any:
        value = await self._func_inner(context)
        validated = self._instance.validate(value, self._bt)
        return validated


class NameResolver(FuncResolver):
    """Resolves by argument name from context."""

    __slots__ = ("_arg_name",)

    def __init__(self, arg_name: str) -> None:
        self._arg_name = arg_name
        super().__init__(self._resolve_by_name, False)

    def _resolve_by_name(
        self, context: Dict[Union[str, Type[Any]], Any], *args: Any
    ) -> Any:
        return context[self._arg_name]


class TypeResolver(FuncResolver):
    """Resolves by type from context."""

    __slots__ = ("_target_type",)

    def __init__(self, target_type: Type[Any]) -> None:
        self._target_type = target_type
        super().__init__(self._resolve_by_type, False)

    def _resolve_by_type(
        self, context: Dict[Union[str, Type[Any]], Any], *args: Any
    ) -> Any:
        return context[self._target_type]


class DefaultResolver(FuncResolver):
    """Resolver that returns a pre-configured default value."""

    __slots__ = ("_default_value",)

    def __init__(self, default_value: Any) -> None:
        self._default_value = default_value
        super().__init__(self._return_default, False)

    def _return_default(self, _: Dict[Union[str, Type[Any]], Any]) -> Any:
        return self._default_value


class ModelFieldResolver(FuncResolver):
    """Resolver that extracts field/method from model instance in context."""

    __slots__ = ("_model_type", "_field_name")

    def __init__(
        self, model_type: Type[Any], field_name: str, async_model_field: bool
    ) -> None:
        self._model_type = model_type
        self._field_name = field_name
        if async_model_field:
            func = self._extract_field_async
        elif '.' not in field_name:
            func = self._extract_field_single
        else:
            func = self._extract_field

        super().__init__(func, async_model_field)

    async def _extract_field_async(
        self, context: Dict[Union[str, Type[Any]], Any], *args: Any
    ) -> Any:
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
            if callable(attr):
                obj = attr()
                if inspect.isawaitable(obj):
                    obj = await obj
            else:
                obj = attr
        return obj

    def _extract_field_single(self, context: Dict[Union[str, Type[Any]], Any], *args: Any) -> Any:
        attr = getattr(context[self._model_type], self._field_name)
        return attr() if callable(attr) else attr

    def _extract_field(
        self, context: Dict[Union[str, Type[Any]], Any], *args: Any
    ) -> Any:
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

    __slots__ = (
        "_func_inner",
        "_run_func",
        "_ctx_map",
        "_resolve_mapped_ctx",
        "_is_cm",
        "_cached_cm_func",
        "_run_func_is_async",
    )

    def __init__(
        self,
        func_inner: Callable[..., Any],
        ctx_map: Dict[Any, Any],
        resolve_mapped_ctx: Callable[..., Any],
        order: int,
    ) -> None:
        self._func_inner = func_inner
        if is_async_gen_callable(func_inner):
            self._run_func = self._resolve_async_cm
            self._is_cm = True
            self._run_func_is_async = False
        elif is_gen_callable(func_inner):
            self._run_func = self._resolve_sync_cm
            self._is_cm = True
            self._run_func_is_async = False
        else:
            self._run_func = func_inner
            self._is_cm = False
            self._run_func_is_async = inspect.iscoroutinefunction(func_inner)

        self._ctx_map = ctx_map
        self._resolve_mapped_ctx = resolve_mapped_ctx
        self._cached_cm_func: Optional[Callable[..., Any]] = None
        super().__init__(func=self._resolve_dependency, isasync=True, order=order)

    async def _resolve_dependency(
        self,
        context: Dict[Union[str, Type[Any]], Any],
        stack: Optional[AsyncExitStack] = None,
    ) -> Any:
        sub_kwargs = await self._resolve_mapped_ctx(context, self._ctx_map)
        func = self._run_func
        if not self._run_func_is_async and not self._is_cm:
            result = run_in_threadpool(func, **sub_kwargs)
        else:
            result = func(**sub_kwargs)
        if inspect.iscoroutine(result):
            result = await result
        if self._is_cm:
            return await self._run_on_stack(result, stack)
        return result

    def _resolve_sync_cm(self, **kwargs: Any) -> Any:
        if self._cached_cm_func is None:
            test_result = self._func_inner(**kwargs)
            if hasattr(test_result, "__enter__"):
                self._cached_cm_func = self._func_inner  # decorated already
            else:
                test_result.close()  # clear
                self._cached_cm_func = contextmanager(self._func_inner)  # decorate

        return contextmanager_in_threadpool(self._cached_cm_func(**kwargs))  # type: ignore

    async def _resolve_async_cm(self, **kwargs: Any) -> Any:
        if self._cached_cm_func is None:
            test_result = self._func_inner(**kwargs)
            if hasattr(test_result, "__aenter__"):
                self._cached_cm_func = self._func_inner
            else:
                await test_result.aclose()
                self._cached_cm_func = asynccontextmanager(self._func_inner)

        return self._cached_cm_func(**kwargs)  # type: ignore

    async def _run_on_stack(
        self,
        cm: Any,
        stack: Optional[AsyncExitStack],
    ) -> Any:
        if stack is None:
            raise RuntimeError(
                "Context manager Resolver requires an AsyncExitStack"
            ) from None
        return await stack.enter_async_context(cm)
