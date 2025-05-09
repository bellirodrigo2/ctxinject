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
    def __init__(self, model: type[Any], field: Optional[str] = None, **meta: Any):
        self.model = model
        self.field = field
        super().__init__(..., **meta)


class InvalidModelFieldType(Exception):
    """Raised when an model field injectable has the wrong type."""


class InvalidInjectableDefinition(Exception):
    """Raised when an injectable is incorrectly defined (e.g., wrong model type)."""


class CallableInjectable(Injectable, ICallableInjectable):
    def __init__(self, default: Callable[..., Any]):
        super().__init__(default)


class DependsInject(CallableInjectable):
    pass


class UnresolvedInjectableError(Exception):
    """Raised when a dependency cannot be resolved in the injection context."""

    ...


class UnInjectableError(Exception):
    """Raised when a function argument cannot be injected."""

    def __init__(self, argname: str, argtype: Optional[type[Any]]):
        super().__init__(
            f"Argument '{argname}' of type '{argtype}' cannot be injected."
        )
        self.argname = argname
        self.argtype = argtype



T = TypeVar('T')

class Constrained(Protocol[T]):
    def __call__(self, data: T, **kwargs: object) -> T: ...

ConstrainedFactory = Callable[[type[Any]],Constrained[T]]

class ConstrArgInject(ArgsInjectable):
    def __init__(
        self,
        constrained_factory:ConstrainedFactory,
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
