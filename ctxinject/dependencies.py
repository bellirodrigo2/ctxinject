import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Union

from ctxinject.inject import inject
from ctxinject.mapfunction import get_func_args
from ctxinject.model import Depends, ICallableInjectable


async def _resolve_func(partial_fn: Callable[..., Any]) -> Any:
    result = partial_fn()
    return await result if inspect.isawaitable(result) else result


@dataclass
class DependencyRegistry:
    tgttype: type[ICallableInjectable] = Depends
    container: MutableMapping[Callable[..., Any], Callable[..., Any]] = field(
        default_factory=dict[Callable[..., Any], Callable[..., Any]]
    )

    async def resolve(
        self,
        func: Callable[..., Any],
        context: Mapping[Union[str, type], Any],
        modeltype: Iterable[type[Any]],
    ) -> Any:

        depfunc = self.container.get(func, func)
        injdepfunc = inject(depfunc, context, modeltype, allow_incomplete=True)
        argsfunc = get_func_args(injdepfunc)
        deps = [
            (arg.name, arg.getinstance(self.tgttype).default)  # type: ignore
            for arg in argsfunc
            if arg.hasinstance(self.tgttype)
        ]
        if not deps:
            return await _resolve_func(injdepfunc)
        dep_ctx: dict[Union[str, type], Any] = {}
        for name, dep in deps:
            dep_ctx[name] = await self.resolve(dep, context, modeltype)
        resolved = inject(injdepfunc, dep_ctx, modeltype, allow_incomplete=True)

        return await _resolve_func(resolved)
