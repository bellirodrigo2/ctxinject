from typing import Any, Callable, Protocol, runtime_checkable


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


class ArgNameBasedInjectable(ArgsInjectable):
    pass


class TypeBasedInjectable(ArgsInjectable):
    pass


class CallableInjectable(Injectable, ICallableInjectable):
    def __init__(self, default: Callable[..., Any], **meta: Any):
        super().__init__(default, **meta)


class Depends(CallableInjectable):
    pass


if __name__ == "__main__":

    dep = Depends(lambda: "foobar")
    args = ArgNameBasedInjectable(...)

    assert isinstance(dep, CallableInjectable)
    assert not isinstance(dep, ArgNameBasedInjectable)

    assert isinstance(args, ArgNameBasedInjectable)
    assert not isinstance(args, CallableInjectable)
