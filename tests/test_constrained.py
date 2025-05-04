from functools import partial

import pytest

from ctxinject.constrained import (
    ConstrainedDatetime,
    ConstrainedList,
    ConstrainedNumber,
    ConstrainedStr,
    ConstrainedUUID,
    ValidationError,
    constrained_factory,
)


def test_constrained_ok() -> None:

    ConstrainedStr("foobar", min_length=2, max_length=10)
    ConstrainedStr("foobar", pattern=r"^[a-z]")
    ConstrainedNumber(45, gt=2, lt=100, multiple_of=5)
    ConstrainedNumber(10.2, gt=2.7, lt=100.99, multiple_of=5.1)

    ConstrainedList([1, 2, 3], int, min_items=1, max_items=10, gt=0, lt=5)
    ConstrainedList(
        ["1", "2", "3"], str, min_items=1, max_items=10, min_length=1, max_length=10
    )

    ConstrainedDatetime("22-12-2007")
    ConstrainedDatetime("22-12-07")
    ConstrainedUUID("3cd4d94e-61e9-4c90-bd39-9207a1fb7227")


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
        ConstrainedList([1, 2, 3], int, max_items=2)
    with pytest.raises(ValidationError):
        ConstrainedList([1, 2, 3], int, gt=3)
    with pytest.raises(ValidationError):
        ConstrainedList(["1", "2", "3"], int)
    with pytest.raises(ValidationError):
        ConstrainedList(["1", "2", "3"], str, min_items=1, max_items=2)
    with pytest.raises(ValidationError):
        ConstrainedList(["1", "2", "3"], str, min_length=2)

    with pytest.raises(ValidationError):
        ConstrainedDatetime("2023-13-02")

    with pytest.raises(ValidationError):
        ConstrainedUUID("Not A UUID")


def test_factory() -> None:

    assert constrained_factory(str) == ConstrainedStr
    assert constrained_factory(int) == ConstrainedNumber
    assert constrained_factory(float) == ConstrainedNumber

    constr_list = constrained_factory(list[str])
    assert isinstance(constr_list, partial)
    assert "basetype" in constr_list.keywords
    assert constr_list.keywords["basetype"] == str

    constr_int = constrained_factory(list[int])
    assert isinstance(constr_int, partial)
    assert "basetype" in constr_int.keywords
    assert constr_int.keywords["basetype"] == int
