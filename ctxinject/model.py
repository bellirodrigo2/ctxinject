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
            raise ValueError(
                f'ModelFieldInject "model" field should be a type, but {type(model)} found'
            )
        self.model = model
        self.field = field
        super().__init__(..., **meta)


class CallableInjectable(Injectable, ICallableInjectable):
    def __init__(self, default: Callable[..., Any]):
        super().__init__(default)


class Depends(CallableInjectable):
    pass
