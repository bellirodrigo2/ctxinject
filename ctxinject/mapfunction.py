import inspect
from dataclasses import dataclass
from functools import partial
from typing import (Annotated, Any, Callable, Mapping, Optional, Sequence,
                    get_args, get_origin, get_type_hints)


class _NoDefault:
    def __repr__(self):
        return "NO_DEFAULT"

    def __str__(self):
        return "NO_DEFAULT"


NO_DEFAULT = _NoDefault()


@dataclass
class FuncArg:
    name: str
    argtype: Optional[type]
    basetype: Optional[type]
    default: Optional[Any]
    extras: Optional[Sequence[Any]] = None

    def istype(self, tgttype: type) -> bool:
        return self.basetype == tgttype or (
            self.basetype is not None and issubclass(self.basetype, tgttype)
        )

    def getinstance(self, tgttype: type) -> Any:
        if self.default is not None and isinstance(self.default, tgttype):
            return self.default
        if self.extras is not None:
            founds = [e for e in self.extras if isinstance(e, tgttype)]
            if len(founds) > 0:
                return founds[0]
        raise TypeError(
            f"Could not find instance of type {tgttype} in default or extras"
        )

    def hasinstance(self, tgttype: type):
        if self.default is not None and isinstance(self.default, tgttype):
            return True
        if self.extras is not None:
            founds = [e for e in self.extras if isinstance(e, tgttype)]
            if len(founds) > 0:
                return True
        return False


def resolve_func_arg(
    hints: Mapping[str, Any], name: str, param: inspect.Parameter
) -> FuncArg:
    annotation: type = hints.get(name, param.annotation)
    default = param.default if param.default is not inspect._empty else NO_DEFAULT  # type: ignore
    argtype = (
        annotation
        if annotation is not inspect._empty  # type: ignore
        else (type(default) if default not in [NO_DEFAULT, None] else None)
    )
    basetype = argtype
    arg = FuncArg(name=name, argtype=argtype, basetype=basetype, default=default)
    if get_origin(annotation) is Annotated:
        base_type, *extras = get_args(annotation)
        arg.basetype = base_type
        arg.extras = extras
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
        arg = resolve_func_arg(hints, name, param)
        funcargs.append(arg)
    return funcargs
