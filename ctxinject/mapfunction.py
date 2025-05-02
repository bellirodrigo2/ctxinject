import inspect
import sys
from dataclasses import dataclass
from functools import partial
from typing import (
    Annotated,
    Any,
    Callable,
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
    has_default: bool = False
    extras: Optional[tuple[Any]] = None

    def istype(self, tgttype: type) -> bool:
        try:
            return self.basetype == tgttype or (issubclass(self.basetype, tgttype))
        except TypeError:
            return False

    def getinstance(self, tgttype: type[T]) -> Optional[T]:

        if self.extras is not None:
            founds = [e for e in self.extras if isinstance(e, tgttype)]
            if len(founds) > 0:
                return founds[0]
        if self.has_default and isinstance(self.default, tgttype):
            return self.default
        return None

    def hasinstance(self, tgttype: type) -> bool:
        return False if self.getinstance(tgttype) is None else True


def func_arg_factory(name: str, param: inspect.Parameter, annotation: type) -> FuncArg:
    has_default = param.default is not inspect._empty
    default = param.default if has_default else NO_DEFAULT
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
        name=name,
        argtype=argtype,
        basetype=basetype,
        default=default,
        extras=extras,
        has_default=has_default,
    )

    return arg


def get_func_args(func: Callable[..., Any]) -> Sequence[FuncArg]:
    partial_args = {}

    if isinstance(func, partial):
        partial_args = func.keywords or {}
        func = func.func

    sig = inspect.signature(func)
    # include_extras=True to preserve Annotated;
    # globalns to resolve forward refs like "User"
    hints = get_type_hints(
        func, globalns=vars(sys.modules[func.__module__]), include_extras=True
    )

    funcargs: list[FuncArg] = []

    for name, param in sig.parameters.items():
        if name in partial_args:
            continue  # already resolved by partial, ignore

        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue  # ignore *args e **kwargs

        annotation: type = hints.get(name, param.annotation)
        arg = func_arg_factory(name, param, annotation)
        funcargs.append(arg)
    return funcargs
