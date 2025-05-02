from typing import Annotated, Any, Callable, Mapping, Optional, Sequence, Union

from ctxinject.mapfunction import NO_DEFAULT, FuncArg, get_func_args
from tests.conftest import MyClass


def test_istype_invalid_basetype() -> None:
    arg = FuncArg("x", argtype=None, basetype="notatype", default=None)
    assert arg.istype(int) is False


def test_funcarg_mt(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    mt = get_func_args(funcsmap["mt"])
    assert mt == []


def test_funcarg_simple(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    simple = get_func_args(funcsmap["simple"])
    assert len(simple) == 2
    assert simple[0].name == "arg1"
    assert simple[0].argtype is str
    assert simple[0].basetype is str
    assert simple[0].default == NO_DEFAULT
    assert simple[0].extras is None
    assert simple[0].istype(str)
    assert not simple[0].istype(int)

    assert simple[1].name == "arg2"
    assert simple[1].argtype is int
    assert simple[1].basetype is int
    assert simple[1].default == NO_DEFAULT
    assert simple[1].extras is None
    assert simple[1].istype(int)
    assert not simple[1].istype(str)


def test_funcarg_def(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    def_: Sequence[FuncArg] = get_func_args(funcsmap["def"])
    assert len(def_) == 4
    assert def_[0].name == "arg1"
    assert def_[0].argtype is str
    assert def_[0].basetype is str
    assert def_[0].default == "foobar"
    assert def_[0].extras is None
    assert def_[0].istype(str)
    assert not def_[0].istype(int)

    assert def_[1].name == "arg2"
    assert def_[1].argtype is int
    assert def_[1].basetype is int
    assert def_[1].default == 12
    assert def_[1].extras is None
    assert def_[1].istype(int)
    assert not def_[1].istype(str)

    assert def_[2].name == "arg3"
    assert def_[2].argtype is bool
    assert def_[2].basetype is bool
    assert def_[2].default is True
    assert def_[2].extras is None
    assert def_[2].istype(bool)
    assert not def_[2].istype(str)

    assert def_[3].name == "arg4"
    assert def_[3].argtype is None
    assert def_[3].basetype is None
    assert def_[3].default is None
    assert def_[3].extras is None
    assert not def_[3].istype(str)


def test_funcarg_ann(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    ann: Sequence[FuncArg] = get_func_args(funcsmap["ann"])
    assert len(ann) == 4

    assert ann[0].name == "arg1"
    assert ann[0].argtype == Annotated[str, "meta1"]
    assert ann[0].basetype is str
    assert ann[0].default == NO_DEFAULT
    assert ann[0].extras == ("meta1",)
    assert ann[0].istype(str) is True
    assert ann[0].istype(int) is False
    assert ann[0].hasinstance(str)
    assert ann[0].getinstance(str) == "meta1"

    assert ann[1].name == "arg2"
    assert ann[1].argtype is Annotated[int, "meta1", 2]
    assert ann[1].basetype is int
    assert ann[1].default == NO_DEFAULT
    assert ann[1].extras == ("meta1", 2)
    assert ann[1].istype(int)
    assert not ann[1].istype(str)
    assert ann[1].hasinstance(tgttype=str)
    assert ann[1].hasinstance(tgttype=int)
    assert ann[1].getinstance(str) == "meta1"
    assert ann[1].getinstance(int) == 2

    assert ann[2].name == "arg3"
    assert ann[2].argtype is Annotated[list[str], "meta1", 2, True]
    assert ann[2].basetype == list[str]
    assert ann[2].default == NO_DEFAULT
    assert ann[2].extras == ("meta1", 2, True)
    assert ann[2].istype(list[str])
    assert not ann[2].istype(str)
    assert ann[2].hasinstance(str)
    assert ann[2].hasinstance(int)
    assert ann[2].hasinstance(bool)
    assert ann[2].getinstance(str) == "meta1"
    assert ann[2].getinstance(int) == 2
    assert ann[2].getinstance(bool)

    assert ann[3].name == "arg4"
    assert ann[3].argtype is Annotated[dict[str, Any], "meta1", 2, True]
    assert ann[3].basetype == dict[str, Any]
    assert ann[3].default == {"foo": "bar"}
    assert ann[3].extras == ("meta1", 2, True)
    assert ann[3].istype(dict[str, Any])
    assert not ann[3].istype(str)
    assert ann[3].hasinstance(str)
    assert ann[3].hasinstance(int)
    assert ann[3].hasinstance(bool)
    assert ann[3].getinstance(str) == "meta1"
    assert ann[3].getinstance(int) == 2
    assert ann[3].getinstance(bool)


def test_funcarg_mix(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    mix: Sequence[FuncArg] = get_func_args(funcsmap["mix"])
    assert len(mix) == 4

    assert mix[0].name == "arg1"
    assert mix[0].argtype is None
    assert mix[0].basetype is None
    assert mix[0].default is NO_DEFAULT
    assert mix[0].extras is None
    assert not mix[0].istype(str)
    assert not mix[0].istype(int)
    assert not mix[0].hasinstance(str)

    assert mix[0].getinstance(str) is None

    assert mix[1].name == "arg2"
    assert mix[1].argtype is Annotated[str, "meta1"]
    assert mix[1].basetype is str
    assert mix[1].default == NO_DEFAULT
    assert mix[1].extras == ("meta1",)
    assert mix[1].istype(str)
    assert not mix[1].istype(int)
    assert mix[1].hasinstance(str)
    assert not mix[1].hasinstance(int)
    assert mix[1].getinstance(str) == "meta1"

    assert mix[1].getinstance(int) is None

    assert mix[2].name == "arg3"
    assert mix[2].argtype is str
    assert mix[2].basetype is str
    assert mix[2].default == NO_DEFAULT
    assert mix[2].extras is None
    assert mix[2].istype(str)
    assert not mix[2].istype(int)
    assert not mix[2].hasinstance(str)
    assert not mix[2].hasinstance(int)

    assert mix[2].getinstance(str) is None
    assert mix[2].getinstance(int) is None

    assert mix[3].name == "arg4"
    assert mix[3].argtype is str
    assert mix[3].basetype is str
    assert mix[3].default == "foobar"
    assert mix[3].extras is None
    assert mix[3].istype(str)
    assert not mix[3].istype(int)
    assert mix[3].hasinstance(str)
    assert not mix[3].hasinstance(int)
    assert mix[3].getinstance(str) == "foobar"

    assert mix[3].getinstance(int) is None


def test_annotated_none(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    args = get_func_args(funcsmap["annotated_none"])
    assert len(args) == 2
    assert args[0].name == "arg1"
    assert args[0].basetype == Optional[str]
    assert args[0].extras == ("meta",)
    assert args[1].default is None
    assert args[1].hasinstance(int) is False


def test_union(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    args = get_func_args(funcsmap["union"])
    assert len(args) == 2
    assert args[0].argtype == Union[int, str]
    assert args[0].default == NO_DEFAULT
    assert args[1].default is None
    assert args[1].basetype == Optional[float]
    assert args[1].argtype == Optional[float]


def test_varargs(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    args = get_func_args(funcsmap["varargs"])
    assert len(args) == 0


def test_kwonly(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    args = get_func_args(funcsmap["kwonly"])
    assert len(args) == 2
    assert args[0].name == "arg1"
    assert args[0].default == NO_DEFAULT
    assert args[1].default == "default"


def test_forward(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    args = get_func_args(funcsmap["forward"])
    assert len(args) == 1
    assert args[0].name == "arg"
    assert args[0].basetype == MyClass


def test_none_default(funcsmap: Mapping[str, Callable[..., Any]]) -> None:
    args = get_func_args(funcsmap["none_default"])
    assert len(args) == 1
    assert args[0].name == "arg"
    assert args[0].default is None
    assert args[0].basetype == Optional[str]
    assert args[0].argtype == Optional[str]


def test_arg_without_type_or_default() -> None:
    def func(x):
        return x

    args = get_func_args(func)
    assert args[0].argtype is None
    assert args[0].default is NO_DEFAULT


def test_default_ellipsis() -> None:
    def func(x: str = ...) -> str:  # noqa
        return x

    args = get_func_args(func)
    assert args[0].default is Ellipsis


def test_star_args_handling() -> None:
    def func(a: str, *args, **kwargs):
        return a

    args = get_func_args(func)
    assert len(args) == 1  # *args/**kwargs devem ser ignorados


class NotDefinedType: ...


def test_forward_ref_resolved() -> None:
    def f(x: "NotDefinedType") -> None: ...

    args = get_func_args(f)
    assert args[0].basetype is NotDefinedType
