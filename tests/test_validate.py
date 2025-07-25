import json
from datetime import date, datetime, time
from typing import Any, Dict, List
from uuid import UUID

import orjson
import pytest
from typemapping import get_func_args

from ctxinject.model import ModelFieldInject
from ctxinject.validate import inject_validation
from ctxinject.validate.pydantic_argproc import arg_proc as pydantic_arg_proc
from ctxinject.validate.std_argproc import arg_proc as std_arg_proc


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_str(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: str

    def func(arg: str = ModelFieldInject(model=Model, field="x", min_length=6)) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    assert modelinj.validate("helloworld", str) == "helloworld"

    with pytest.raises(ValueError):
        modelinj.validate("hello", str)


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_int(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: int

    def func(arg: int = ModelFieldInject(model=Model, field="x", gt=6)) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    assert modelinj.validate(12, int) == 12

    with pytest.raises(ValueError):
        modelinj.validate(4, int)


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_float(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: float

    def func(
        hello=ModelFieldInject(str),
        arg: float = ModelFieldInject(model=Model, field="x", gt=6),
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[1].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    assert modelinj.validate(6.5, basetype=float) == 6.5

    with pytest.raises(ValueError):
        modelinj.validate(5.5, basetype=float)


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_list(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: List[str]

    def func(
        arg: List[str] = ModelFieldInject(
            model=Model, field="x", min_length=1, max_length=2
        )
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    assert modelinj.validate(["foo"], basetype=List[str]) == ["foo"]

    with pytest.raises(ValueError):
        modelinj.validate(["foo", "bar", "hello"], basetype=List[str])

    with pytest.raises(ValueError):
        modelinj.validate([], basetype=List[str])


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_dict(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: Dict[str, str]

    def func(
        arg_zero: str,
        arg: Dict[str, str] = ModelFieldInject(
            model=Model, field="x", min_length=1, max_length=2
        ),
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[1].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    assert modelinj.validate({"foo": "bar"}, basetype=Dict[str, str]) == {"foo": "bar"}

    with pytest.raises(ValueError):
        modelinj.validate(
            {"foo": "bar", "hello": "world", "a": "b"}, basetype=Dict[str, str]
        )

    with pytest.raises(ValueError):
        modelinj.validate({}, basetype=Dict[str, str])


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_date(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: str

    def func(
        arg: date = ModelFieldInject(model=Model, field="x", start=date(2024, 1, 1))
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    assert modelinj.validate("2024-06-06", basetype=date) == date(2024, 6, 6)

    with pytest.raises(ValueError):
        modelinj.validate("2023-06-06", basetype=date)


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_time(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: str

    def func(
        arg: time = ModelFieldInject(model=Model, field="x", start=time(2, 2, 2))
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    assert modelinj.validate("03:03:03", basetype=time) == time(3, 3, 3)

    with pytest.raises(ValueError):
        modelinj.validate("01:01:01", basetype=time)


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_datetime(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: str

    def func(
        arg: datetime = ModelFieldInject(
            model=Model, field="x", start=datetime(2024, 1, 1)
        )
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    assert modelinj.validate("2024-06-06", basetype=datetime) == datetime(2024, 6, 6)

    with pytest.raises(ValueError):
        modelinj.validate("2023-06-06", basetype=datetime)


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_uuid(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: str

    def func(arg: UUID = ModelFieldInject(model=Model, field="x")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    modelinj.validate("94fa2f76-84c7-484e-95ee-5fc3fabbd9fb", basetype=UUID)

    with pytest.raises(ValueError):
        modelinj.validate("NONUUID", basetype=UUID)


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_json(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: str

    def func(arg: Dict[str, Any] = ModelFieldInject(model=Model, field="x")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    data = {"foo": "bar"}
    assert modelinj.validate(json.dumps(data), basetype=Dict[str, Any]) == data

    with pytest.raises(ValueError):
        modelinj.validate("no json", basetype=Dict[str, Any])


@pytest.mark.parametrize("use_pydantic", [True, False])
def test_validate_bytesjson(use_pydantic: bool) -> None:
    arg_proc = pydantic_arg_proc if use_pydantic else std_arg_proc

    class Model:
        x: bytes

    def func(arg: Dict[str, Any] = ModelFieldInject(model=Model, field="x")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=arg_proc)
    assert modelinj.has_validate
    data = {"foo": "bar"}
    assert modelinj.validate(orjson.dumps(data), basetype=Dict[str, Any]) == data

    with pytest.raises(ValueError):
        modelinj.validate("no json", basetype=Dict[str, Any])
