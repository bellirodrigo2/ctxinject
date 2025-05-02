from typing import Any, Callable, Optional, Protocol, runtime_checkable


@runtime_checkable
class Iinjectable(Protocol):
    @property
    def default(self) -> Any: ...
    def validate(self, instance: Any) -> None: ...


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

    def validate(self, instance: Any) -> None:
        pass


class ArgsInjectable(Injectable):
    pass


class ArgNameInjec(ArgsInjectable):
    pass


class ModelFieldInject(ArgsInjectable):
    def __init__(self, model: type[Any], field: Optional[str] = None, **meta: Any):
        if model is None or not isinstance(model, type):  # type: ignore
            raise InvalidInjectableDefinition(
                f'ModelFieldInject "model" field should be a type, but {type(model)} found'
            )
        self.model = model
        self.field = field
        super().__init__(..., **meta)


class InvalidInjectableDefinition(Exception):
    """Raised when an injectable is incorrectly defined (e.g., wrong model type)."""


class CallableInjectable(Injectable, ICallableInjectable):
    def __init__(self, default: Callable[..., Any]):
        super().__init__(default)


class Depends(CallableInjectable):
    pass


class UnresolvedInjectableError(Exception):
    """Raised when a dependency cannot be resolved in the injection context."""

    def __init__(self, argname: str):
        super().__init__(
            f"Argument '{argname}' is incomplete or missing a valid injectable context."
        )
        self.argname = argname
