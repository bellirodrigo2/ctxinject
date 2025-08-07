import functools
import inspect
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, ContextManager, TypeVar

import anyio
from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


def is_any_gen_callable(
    call: Callable[..., Any], inspect_func: Callable[[Callable[..., Any]], bool]
) -> bool:
    if inspect_func(call):
        return True
    dunder_call = getattr(call, "__call__", None)
    if dunder_call and inspect_func(dunder_call):
        return True
    wrapped = getattr(call, "__wrapped__", None)
    if wrapped and inspect_func(wrapped):
        return True
    return False


def is_async_gen_callable(call: Callable[..., Any]) -> bool:
    return is_any_gen_callable(call, inspect.isasyncgenfunction)


def is_gen_callable(call: Callable[..., Any]) -> bool:
    return is_any_gen_callable(call, inspect.isgeneratorfunction)


def is_generator(call: Callable[..., Any]) -> bool:
    return is_async_gen_callable(call) or is_gen_callable(call)


async def run_in_threadpool(
    func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    if kwargs:
        func = functools.partial(func, **kwargs)
    return await anyio.to_thread.run_sync(func, *args)


@asynccontextmanager
async def contextmanager_in_threadpool(
    cm: ContextManager[T],
) -> AsyncGenerator[T, None]:
    exit_limiter = anyio.CapacityLimiter(1)
    try:
        yield await run_in_threadpool(cm.__enter__)
    except Exception as e:
        ok = bool(
            await anyio.to_thread.run_sync(
                cm.__exit__, type(e), e, None, limiter=exit_limiter
            )
        )
        if not ok:  # pragma: no branch
            raise e
    else:
        await anyio.to_thread.run_sync(
            cm.__exit__, None, None, None, limiter=exit_limiter
        )
