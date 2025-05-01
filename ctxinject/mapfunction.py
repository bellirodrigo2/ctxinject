import inspect
from dataclasses import dataclass
from functools import partial
from typing import (
    Annotated,
    Any,
    Callable,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)


class _NoDefault:
    def __repr__(self) -> str:
        return "NO_DEFAULT"

    def __str__(self) -> str:
        return "NO_DEFAULT"


NO_DEFAULT = _NoDefault()

T = TypeVar("T")


@dataclass(frozen=True)
class FuncArg:
    name: str
    argtype: Optional[type]
    basetype: Optional[type]
    default: Optional[Any]
    extras: Optional[tuple[Any]] = None

    def istype(self, tgttype: type) -> bool:
        return self.basetype == tgttype or (
            self.basetype is not None and issubclass(self.basetype, tgttype)
        )

    def _has_default(self) -> bool:
        return self.default is not NO_DEFAULT

    def getinstance(self, tgttype: type[T]) -> Optional[T]:
        if self._has_default() and isinstance(self.default, tgttype):
            return self.default
        if self.extras is not None:
            founds = [e for e in self.extras if isinstance(e, tgttype)]
            if len(founds) > 0:
                return founds[0]
        return None

    def hasinstance(self, tgttype: type) -> bool:
        return False if self.getinstance(tgttype) is None else True


def func_arg_factory(name: str, param: inspect.Parameter, annotation: type) -> FuncArg:
    default = param.default if param.default is not inspect._empty else NO_DEFAULT  # type: ignore
    argtype = (
        annotation
        if annotation is not inspect._empty  # type: ignore
        else (type(default) if default not in [NO_DEFAULT, None] else None)
    )
    basetype = argtype
    extras = None
    if get_origin(annotation) is Annotated:
        basetype, *extras_ = get_args(annotation)
        extras = tuple(extras_)
    arg = FuncArg(
        name=name, argtype=argtype, basetype=basetype, default=default, extras=extras
    )

    return arg


def get_func_args(func: Callable[..., Any]) -> Sequence[FuncArg]:
    partial_args = {}
    if isinstance(func, partial):
        partial_args = func.keywords or {}
        func = func.func

    sig = inspect.signature(func)
    hints = get_type_hints(func, include_extras=True)
    funcargs: list[FuncArg] = []

    for name, param in sig.parameters.items():
        if name in partial_args:
            continue  # já foi resolvido via partial, ignora
        annotation: type = hints.get(name, param.annotation)
        arg = func_arg_factory(name, param, annotation)
        funcargs.append(arg)
    return funcargs
