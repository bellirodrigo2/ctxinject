from typing import Any, Callable, Optional, Protocol, Type, TypeVar, runtime_checkable


@runtime_checkable
class Iinjectable(Protocol):
    @property
    def default(self) -> Any: ...
    def validate(
        self, instance: Any, basetype: Type[Any]
    ) -> Any: ...  # pragma: no cover


class ICallableInjectable(Iinjectable, Protocol):
    @property
    def default(self) -> Callable[..., Any]: ...  # pragma: no cover


class Injectable(Iinjectable):
    def __init__(
        self,
        default: Any = ...,
        validator: Optional[Callable[..., Any]] = None,
        **meta: Any,
    ):
        self._default = default
        self._validator = validator
        self.meta = meta

    @property
    def default(self) -> Any:
        return self._default

    @property
    def has_validate(self) -> bool:
        return self._validator is not None

    def validate(self, instance: Any, basetype: Type[Any]) -> Any:
        self.meta["basetype"] = basetype
        return self._validator(instance, **self.meta)


class ArgsInjectable(Injectable):
    pass


class ModelFieldInject(ArgsInjectable):
    def __init__(
        self,
        model: Type[Any],
        field: Optional[str] = None,
        validator: Optional[Callable[..., Any]] = None,
        **meta: Any,
    ):
        super().__init__(default=..., validator=validator, **meta)
        self._model = model
        self.field = field

    @property
    def model(self) -> Type[Any]:
        return self._model


class CallableInjectable(Injectable, ICallableInjectable):
    def __init__(
        self,
        default: Callable[..., Any],
        validator: Optional[Callable[..., Any]] = None,
    ):
        super().__init__(default=default, validator=validator)


class DependsInject(CallableInjectable):
    pass


T = TypeVar("T")


class Constrained(Protocol[T]):
    def __call__(self, data: T, **kwargs: object) -> T: ...  # pragma: no cover


ConstrainedFactory = Callable[[type[Any]], Constrained[T]]


class ConstrArgInject(ArgsInjectable):
    def __init__(
        self,
        constrained_factory: ConstrainedFactory,
        default: Any = ...,
        validator: Optional[Callable[..., Any]] = None,
        **meta: Any,
    ):
        super().__init__(default, validator, **meta)
        self._constrained_factory = constrained_factory

    @property
    def has_validate(self) -> bool:
        return True

    def validate(self, instance: Any, basetype: Type[Any]) -> Any:
        if self._validator is not None:
            instance = self._validator(instance, **self.meta)
        constr = self._constrained_factory(basetype)
        value = constr(instance, **self.meta)
        return value
