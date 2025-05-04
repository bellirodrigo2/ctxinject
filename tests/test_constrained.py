from datetime import datetime
from enum import Enum
from functools import partial
from typing import Annotated, Any
from uuid import UUID

import pytest

from ctxinject.constrained import (
    ConstrainedDatetime,
    ConstrainedEnum,
    ConstrainedItems,
    ConstrainedNumber,
    ConstrainedStr,
    ConstrainedUUID,
    ValidationError,
    constrained_factory,
)
from ctxinject.inject import inject_args
from ctxinject.validate import ConstrArgInject


class MyEnum(Enum):
    VALID = 0
    INVALID = 1


class Enum2(Enum):
    FOO = 0
    BAR = 1


def test_constrained_ok() -> None:

    ConstrainedStr("foobar", min_length=2, max_length=10)
    ConstrainedStr("foobar", pattern=r"^[a-z]")
    ConstrainedNumber(45, gt=2, lt=100, multiple_of=5)
    ConstrainedNumber(10.2, gt=2.7, lt=100.99, multiple_of=5.1)

    ConstrainedItems([1, 2, 3], [int], min_items=1, max_items=10, gt=0, lt=5)
    ConstrainedItems(
        ["1", "2", "3"], [str], min_items=1, max_items=10, min_length=1, max_length=10
    )
    ConstrainedItems(
        {"foo": "bar"}, [str], min_items=0, max_items=2, min_length=1, max_length=10
    )
    ConstrainedDatetime("22-12-2007")
    ConstrainedDatetime("22-12-07")
    ConstrainedUUID("3cd4d94e-61e9-4c90-bd39-9207a1fb7227")

    ConstrainedEnum(MyEnum.VALID, MyEnum)
    ConstrainedEnum(Enum2.FOO, Enum2)


def test_constrained_fail() -> None:

    with pytest.raises(ValidationError):
        ConstrainedStr("foobar", min_length=2, max_length=3)
    with pytest.raises(ValidationError):
        ConstrainedStr("FooBar", pattern=r"^[a-z]")
    with pytest.raises(ValidationError):
        ConstrainedNumber(45, gt=2, lt=10, multiple_of=5)
    with pytest.raises(ValidationError):
        ConstrainedNumber(45, multiple_of=2)
    with pytest.raises(ValidationError):
        ConstrainedNumber(10.2, gt=2.7, lt=10.09, multiple_of=5.1)
    with pytest.raises(ValidationError):
        ConstrainedItems([1, 2, 3], [int], max_items=2)
    with pytest.raises(ValidationError):
        ConstrainedItems([1, 2, 3], [int], gt=3)
    with pytest.raises(ValidationError):
        ConstrainedItems(["1", "2", "3"], [str], min_items=1, max_items=2)
    with pytest.raises(ValidationError):
        ConstrainedItems(["1", "2", "3"], [str], min_length=2)

    with pytest.raises(ValidationError):
        ConstrainedItems(
            {"foo": "b"},
            [str, str],
            min_items=0,
            max_items=2,
            max_length=2,
        )

    with pytest.raises(ValidationError):
        ConstrainedItems(
            {"f": "bar"},
            [str, str],
            values_check={"max_length": 2},
            min_items=0,
            max_items=2,
            max_length=2,
        )
    with pytest.raises(ValidationError):
        ConstrainedDatetime("2023-13-02")

    with pytest.raises(ValidationError):
        ConstrainedUUID("Not A UUID")

    with pytest.raises(ValidationError):
        ConstrainedEnum(Enum2.BAR, MyEnum)

    with pytest.raises(ValidationError):
        ConstrainedEnum(MyEnum.VALID, Enum2)


def test_factory() -> None:

    assert constrained_factory(str) == ConstrainedStr
    assert constrained_factory(int) == ConstrainedNumber
    assert constrained_factory(float) == ConstrainedNumber

    constr_list = constrained_factory(list[str])
    assert isinstance(constr_list, partial)
    assert "basetype" in constr_list.keywords
    assert constr_list.keywords["basetype"][0] == str
    constr_list(["foo", "bar"])

    with pytest.raises(ValidationError):
        constr_list(["1", "2", "3"], min_length=2)

    constr_listint = constrained_factory(list[int])
    assert isinstance(constr_listint, partial)
    assert "basetype" in constr_listint.keywords
    assert constr_listint.keywords["basetype"][0] == int
    constr_listint([40, 45])
    with pytest.raises(ValidationError):
        constr_listint([40, 45], gt=42)

    constr_dict = constrained_factory(dict[str, str])
    assert isinstance(constr_dict, partial)
    assert "basetype" in constr_dict.keywords
    assert constr_dict.keywords["basetype"][0] == str
    assert constr_dict.keywords["basetype"][1] == str
    constr_dict({"foo": "bar"})

    constr_enum = constrained_factory(MyEnum)
    assert isinstance(constr_enum, partial)
    assert "baseenum" in constr_enum.keywords
    assert constr_enum.keywords["baseenum"] == MyEnum
    constr_enum(MyEnum.INVALID)

    with pytest.raises(ValidationError):
        constr_enum(0)

    constr_date = constrained_factory(datetime)
    assert isinstance(constr_date, partial)
    assert "which" in constr_date.keywords
    assert constr_date.keywords["which"] == datetime

    constr_uuid = constrained_factory(UUID)
    assert constr_uuid == ConstrainedUUID

    factory = constrained_factory(Annotated[list[int], "whatever"])
    assert isinstance(factory, partial)
    assert factory.keywords["basetype"][0] == int


def test_constrained_factory_fallback() -> None:
    class Unsupported:
        pass

    factory = constrained_factory(Unsupported)
    assert callable(factory)
    assert factory("any") == "any"  # just returns the value


def test_constrained_str_none_allowed_fallback() -> None:
    result = ConstrainedStr("abc", min_length=2)
    assert result == "abc"


def func(
    arg1: Annotated[UUID, 123, ConstrArgInject(...)],
    arg2: Annotated[datetime, ConstrArgInject(...)],
    arg3: str = ConstrArgInject(..., min_length=3),
    arg4: MyEnum = ConstrArgInject(...),
    arg5: list[str] = ConstrArgInject(..., max_length=5),
) -> None:
    return None


def test_full_constrained() -> None:
    ctx: dict[str, Any] = {
        "arg1": "3cd4d94e-61e9-4c90-bd39-9207a1fb7227",
        "arg2": "22-12-07",
        "arg3": "foobar",
        "arg4": MyEnum.INVALID,
        "arg5": ["hello"],
    }
    inject_args(func, ctx)


def test_full_constrained_fail_uuid() -> None:
    ctx: dict[str, Any] = {
        "arg1": "NotUUID",
        "arg2": "22-12-07",
        "arg3": "foobar",
        "arg4": MyEnum.INVALID,
        "arg5": ["hello"],
    }
    with pytest.raises(ValidationError):
        inject_args(func, ctx)


def test_full_constrained_fail_datetime() -> None:
    ctx: dict[str, Any] = {
        "arg1": "3cd4d94e-61e9-4c90-bd39-9207a1fb7227",
        "arg2": "99-15-07",
        "arg3": "foobar",
        "arg4": MyEnum.INVALID,
        "arg5": ["hello"],
    }
    with pytest.raises(ValidationError):
        inject_args(func, ctx)


def test_constrained_items_set_tuple() -> None:
    ConstrainedItems({1, 2}, [int], min_items=1, max_items=3, gt=0)

    with pytest.raises(ValidationError):
        ConstrainedItems((1, 2, 3, 4), [int], max_items=3)


def test_constrained_datetime_custom_format() -> None:
    assert ConstrainedDatetime("2024-05-01", fmt="%Y-%m-%d") == datetime(2024, 5, 1)

    with pytest.raises(ValidationError):
        ConstrainedDatetime("01/05/2024", fmt="%Y-%m-%d")
