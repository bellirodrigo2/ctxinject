from typing import Any, Callable, Optional, Protocol, TypeVar, runtime_checkable


@runtime_checkable
class Iinjectable(Protocol):
    @property
    def default(self) -> Any: ...
    def validate(self, instance: Any, basetype: type[Any]) -> Any: ...


class ICallableInjectable(Iinjectable, Protocol):
    @property
    def default(self) -> Callable[..., Any]:  # Espera um Callable como default
        ...


class Injectable(Iinjectable):
    def __init__(self, default: Any = ..., **meta: Any):
        self._default = default
        self.meta = meta

    @property
    def default(self) -> Any:
        return self._default

    def validate(self, instance: Any, basetype: type[Any]) -> Any:
        return instance


class ArgsInjectable(Injectable):
    pass


class ModelFieldInject(ArgsInjectable):
    def __init__(
        self,
        model: type[Any],
        field: Optional[str] = None,
        **meta: Any,
    ):
        super().__init__(..., **meta)
        self.model = model
        self.field = field


class CallableInjectable(Injectable, ICallableInjectable):
    def __init__(self, default: Callable[..., Any]):
        super().__init__(default)


class DependsInject(CallableInjectable):
    pass


T = TypeVar("T")


class Constrained(Protocol[T]):
    def __call__(self, data: T, **kwargs: object) -> T: ...


ConstrainedFactory = Callable[[type[Any]], Constrained[T]]


class ConstrArgInject(ArgsInjectable):
    def __init__(
        self,
        constrained_factory: ConstrainedFactory,
        default: Any = ...,
        custom_validator: Optional[Callable[[Any], Any]] = None,
        **meta: Any,
    ):
        self._default = default
        self.meta = meta
        self._custom_validator = custom_validator
        self._constrained_factory = constrained_factory

    def validate(self, instance: Any, basetype: type[Any]) -> None:
        if self._custom_validator is not None:
            instance = self._custom_validator(instance)
        constr = self._constrained_factory(basetype)
        value = constr(instance, **self.meta)
        return value


class Depends(DependsInject):
    pass
