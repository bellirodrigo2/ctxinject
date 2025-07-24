import json
from datetime import date, datetime, time
from typing import Any, Dict, List
from uuid import UUID

import orjson
import pytest
from typemapping import get_func_args

from ctxinject.model import ModelFieldInject
from ctxinject.validate import inject_validation


def test_validate_str() -> None:
    class Model:
        x: str

    def func(arg: str = ModelFieldInject(model=Model, field="x", min_length=6)) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate
    inject_validation(func)
    assert modelinj.has_validate
    assert modelinj.validate("helloworld", str) == "helloworld"

    with pytest.raises(ValueError):
        modelinj.validate("hello", str)


def test_validate_int() -> None:
    class Model:
        x: int

    def func(arg: int = ModelFieldInject(model=Model, field="x", gt=6)) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate
    inject_validation(func)
    assert modelinj.has_validate
    assert modelinj.validate(12, int) == 12

    with pytest.raises(ValueError):
        modelinj.validate(4, int)


def test_validate_float() -> None:
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
    inject_validation(func)
    assert modelinj.has_validate
    assert modelinj.validate(6.5, basetype=float) == 6.5

    with pytest.raises(ValueError):
        modelinj.validate(5.5, basetype=float)


def test_validate_list() -> None:
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
    inject_validation(func)
    assert modelinj.has_validate
    assert modelinj.validate(["foo"], basetype=List[str]) == ["foo"]

    with pytest.raises(ValueError):
        modelinj.validate(["foo", "bar", "hello"], basetype=List[str])

    with pytest.raises(ValueError):
        modelinj.validate([], basetype=List[str])


def test_validate_dict() -> None:
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
    inject_validation(func)
    assert modelinj.has_validate
    assert modelinj.validate({"foo": "bar"}, basetype=Dict[str, str]) == {"foo": "bar"}

    with pytest.raises(ValueError):
        modelinj.validate(
            {"foo": "bar", "hello": "world", "a": "b"}, basetype=Dict[str, str]
        )

    with pytest.raises(ValueError):
        modelinj.validate({}, basetype=Dict[str, str])


def test_validate_date() -> None:
    class Model:
        x: str

    def func(
        arg: date = ModelFieldInject(model=Model, field="x", start=date(2024, 1, 1))
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate
    inject_validation(func)
    assert modelinj.has_validate
    assert modelinj.validate("2024-06-06", basetype=date) == date(2024, 6, 6)

    with pytest.raises(ValueError):
        modelinj.validate("2023-06-06", basetype=date)


def test_validate_time() -> None:
    class Model:
        x: str

    def func(
        arg: time = ModelFieldInject(model=Model, field="x", start=time(2, 2, 2))
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate
    inject_validation(func)
    assert modelinj.has_validate
    assert modelinj.validate("03:03:03", basetype=time) == time(3, 3, 3)

    with pytest.raises(ValueError):
        modelinj.validate("01:01:01", basetype=time)


def test_validate_datetime() -> None:
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
    inject_validation(func)
    assert modelinj.has_validate
    assert modelinj.validate("2024-06-06", basetype=datetime) == datetime(2024, 6, 6)

    with pytest.raises(ValueError):
        modelinj.validate("2023-06-06", basetype=datetime)


def test_validate_uuid() -> None:
    class Model:
        x: str

    def func(arg: UUID = ModelFieldInject(model=Model, field="x")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate
    inject_validation(func)
    assert modelinj.has_validate
    modelinj.validate("94fa2f76-84c7-484e-95ee-5fc3fabbd9fb", basetype=UUID)

    with pytest.raises(ValueError):
        modelinj.validate("NONUUID", basetype=UUID)


def test_validate_json() -> None:
    class Model:
        x: str

    def func(arg: Dict[str, Any] = ModelFieldInject(model=Model, field="x")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate
    inject_validation(func)
    assert modelinj.has_validate
    data = {"foo": "bar"}
    assert modelinj.validate(json.dumps(data), basetype=Dict[str, Any]) == data

    with pytest.raises(ValueError):
        modelinj.validate("no json", basetype=Dict[str, Any])


def test_validate_bytesjson() -> None:
    class Model:
        x: bytes

    def func(arg: Dict[str, Any] = ModelFieldInject(model=Model, field="x")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate
    inject_validation(func)
    assert modelinj.has_validate
    data = {"foo": "bar"}
    assert modelinj.validate(orjson.dumps(data), basetype=Dict[str, Any]) == data

    with pytest.raises(ValueError):
        modelinj.validate("no json", basetype=Dict[str, Any])
