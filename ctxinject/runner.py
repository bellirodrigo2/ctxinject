import functools
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    ContextManager,
    Dict,
    List,
    Optional,
    TypeVar,
)

from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")

try:
    import anyio

    to_thread = anyio.to_thread.run_sync

    exit_limiter = anyio.CapacityLimiter(1)

    async def close_cm(cm: ContextManager[Any], exc: Optional[Exception]) -> bool:
        type_exc = type(exc) if exc is not None else None
        return bool(
            await anyio.to_thread.run_sync(
                cm.__exit__, type_exc, exc, None, limiter=exit_limiter
            )
        )

    async def run_async_tasks(
        async_tasks: List[Any], async_keys: List[Any], results: Dict[str, Any]
    ) -> None:
        async def _store_result(results: Dict[str, Any], key: str, task: Any) -> None:
            results[key] = await task

        try:
            async with anyio.create_task_group() as tg:
                for key, task in zip(async_keys, async_tasks):
                    tg.start_soon(_store_result, results, key, task)
        except Exception as exc:
            if hasattr(exc, "exceptions"):
                for sub_exc in exc.exceptions:
                    raise sub_exc from None
            else:
                raise

except (ImportError, AttributeError):
    import asyncio
    import sys

    if sys.version_info >= (3, 9):
        to_thread = asyncio.to_thread
    else:

        async def to_thread(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
            loop = asyncio.get_running_loop()
            if kwargs:
                func = functools.partial(func, **kwargs)
            return await loop.run_in_executor(None, func, *args)

    _exit_semaphore = asyncio.Semaphore(1)

    async def close_cm(cm: ContextManager[Any], exc: Optional[Exception]) -> bool:
        type_exc = type(exc) if exc is not None else None
        async with _exit_semaphore:
            ok = bool(await to_thread(cm.__exit__, type_exc, exc, None))
            return ok

    async def run_async_tasks(
        async_tasks: List[Any], async_keys: List[Any], results: Dict[str, Any]
    ) -> None:
        try:
            resolved_values = await asyncio.gather(*async_tasks, return_exceptions=True)
            for key, resolved_value in zip(async_keys, resolved_values):
                if isinstance(resolved_value, Exception):
                    raise resolved_value
                results[key] = resolved_value
        except Exception:
            raise


async def run_in_threadpool(
    func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    if kwargs:
        func = functools.partial(func, **kwargs)
    return await to_thread(func, *args)


@asynccontextmanager
async def contextmanager_in_threadpool(
    cm: ContextManager[T],
) -> AsyncGenerator[T, None]:
    try:
        yield await run_in_threadpool(cm.__enter__)
    except Exception as e:
        ok = await close_cm(cm, e)
        if not ok:  # pragma: no branch
            raise e
    else:
        await close_cm(cm, None)
