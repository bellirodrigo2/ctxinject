import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, MutableMapping

from ctxinject.inject import inject
from ctxinject.model import ICallableInjectable


@dataclass
class DependencyRegistry:
    tgttype: type[ICallableInjectable]
    container: MutableMapping[Callable[..., Any], Callable[..., Any]] = field(
        default_factory=dict[Callable[..., Any], Callable[..., Any]]
    )

    async def resolve(
        self,
        func: Callable[..., Any],
        arg_context: Mapping[str, Any],
        type_context: Mapping[type, Any],
        raise_on_missing: bool,
        validate_default: bool,
    ) -> Any:

        depfunc = self.container.get(func, func)

    #     # injdepfunc = inject(depfunc, arg_context, raise_on_missing, validate_default)

    #     injectables_map: MutableMapping[str, Any] = map_types(depfunc, self.tgttype)

    #     if not injectables_map:
    #         # Final step: injeta e executa (async ou sync)
    #         resolvedfunc = inject(
    #             depfunc, arg_context, raise_on_missing, validate_default
    #         )
    #         return self._call_function(resolvedfunc)

    #     else:
    #         for k, v in list(injectables_map.items()):
    #             depfunc = v.default
    #             resolved = await self.resolve(
    #                 depfunc, arg_context, raise_on_missing, validate_default
    #             )
    #             injectables_map[k] = resolved
    #         kwargs: dict[Any, Any] = {**arg_context, **injectables_map}

    #         resolvedfunc = inject(depfunc, kwargs, raise_on_missing, validate_default)
    #         return self._call_function(resolvedfunc)

    # async def _call_function(self, resolvedfunc: Callable[..., Any]):
    #     return (
    #         await resolvedfunc()
    #         if inspect.iscoroutinefunction(resolvedfunc)
    #         else resolvedfunc()
    #     )
