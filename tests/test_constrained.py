import unittest
from datetime import datetime
from enum import Enum
from functools import partial
from typing import Annotated, Any, Dict
from uuid import UUID

from ctxinject.constrained import (
    ConstrainedDatetime,
    ConstrainedEnum,
    ConstrainedItems,
    ConstrainedNumber,
    ConstrainedStr,
    ConstrainedUUID,
    constrained_factory,
)
from ctxinject.inject import inject_args
from ctxinject.model import ConstrArgInject


class MyEnum(Enum):
    VALID = 0
    INVALID = 1


class Enum2(Enum):
    FOO = 0
    BAR = 1


class TestConstrained(unittest.IsolatedAsyncioTestCase):

    def test_constrained_ok(self) -> None:
        ConstrainedStr("foobar", min_length=2, max_length=10)
        ConstrainedStr("foobar", pattern=r"^[a-z]")
        ConstrainedNumber(45, gt=2, lt=100, multiple_of=5)
        ConstrainedNumber(10.2, gt=2.7, lt=100.99, multiple_of=5.1)
        ConstrainedItems([1, 2, 3], [int], min_items=1, max_items=10, gt=0, lt=5)
        ConstrainedItems(
            ["1", "2", "3"],
            [str],
            min_items=1,
            max_items=10,
            min_length=1,
            max_length=10,
        )
        ConstrainedItems(
            {"foo": "bar"}, [str], min_items=0, max_items=2, min_length=1, max_length=10
        )
        ConstrainedDatetime("22-12-2007")
        ConstrainedDatetime("22-12-07")
        ConstrainedUUID("3cd4d94e-61e9-4c90-bd39-9207a1fb7227")
        ConstrainedEnum(MyEnum.VALID, MyEnum)
        ConstrainedEnum(Enum2.FOO, Enum2)

    def test_constrained_fail(self) -> None:
        with self.assertRaises(ValueError):
            ConstrainedStr("foobar", min_length=2, max_length=3)
        with self.assertRaises(ValueError):
            ConstrainedStr("FooBar", pattern=r"^[a-z]")
        with self.assertRaises(ValueError):
            ConstrainedNumber(45, gt=2, lt=10, multiple_of=5)
        with self.assertRaises(ValueError):
            ConstrainedNumber(45, ge=52)
        with self.assertRaises(ValueError):
            ConstrainedNumber(45, le=5)
        with self.assertRaises(ValueError):
            ConstrainedNumber(45, multiple_of=2)
        with self.assertRaises(ValueError):
            ConstrainedNumber(10.2, gt=2.7, lt=10.09, multiple_of=5.1)
        with self.assertRaises(ValueError):
            ConstrainedItems([1, 2, 3], [int], max_items=2)
        with self.assertRaises(ValueError):
            ConstrainedItems([1, 2, 3], [int], gt=3)
        with self.assertRaises(ValueError):
            ConstrainedItems(["1", "2", "3"], [str], min_items=1, max_items=2)
        with self.assertRaises(ValueError):
            ConstrainedItems(["1", "2", "3"], [str], min_items=10)
        with self.assertRaises(ValueError):
            ConstrainedItems(["1", "2", "3"], [str], min_length=2)
        with self.assertRaises(ValueError):
            ConstrainedItems(
                {"foo": "b"}, [str, str], min_items=0, max_items=2, max_length=2
            )
        with self.assertRaises(ValueError):
            ConstrainedItems(
                {"f": "bar"},
                [str, str],
                values_check={"max_length": 2},
                min_items=0,
                max_items=2,
                max_length=2,
            )
        with self.assertRaises(ValueError):
            ConstrainedItems(
                {"f": "bar"},
                [str, str],
                values_check={"max_length": 2},
                min_items=0,
                max_items=2,
                max_length=2,
            )

        with self.assertRaises(ValueError):
            ConstrainedDatetime("2023-13-02")
        with self.assertRaises(ValueError):
            ConstrainedUUID("Not A UUID")
        with self.assertRaises(ValueError):
            ConstrainedEnum(Enum2.BAR, MyEnum)
        with self.assertRaises(ValueError):
            ConstrainedEnum(MyEnum.VALID, Enum2)

    def test_factory(self) -> None:
        self.assertEqual(constrained_factory(str), ConstrainedStr)
        self.assertEqual(constrained_factory(int), ConstrainedNumber)
        self.assertEqual(constrained_factory(float), ConstrainedNumber)

        constr_list = constrained_factory(list[str])
        self.assertIsInstance(constr_list, partial)
        self.assertIn("basetype", constr_list.keywords)
        self.assertEqual(constr_list.keywords["basetype"][0], str)
        constr_list(["foo", "bar"])

        with self.assertRaises(ValueError):
            constr_list(["1", "2", "3"], min_length=2)

        constr_listint = constrained_factory(list[int])
        constr_listint([40, 45])
        with self.assertRaises(ValueError):
            constr_listint([40, 45], gt=42)

        constr_dict = constrained_factory(dict[str, str])
        constr_dict({"foo": "bar"})

        constr_enum = constrained_factory(MyEnum)
        constr_enum(MyEnum.INVALID)

        with self.assertRaises(ValueError):
            constr_enum(0)

        constr_date = constrained_factory(datetime)
        self.assertIsInstance(constr_date, partial)

        constr_uuid = constrained_factory(UUID)
        self.assertEqual(constr_uuid, ConstrainedUUID)

        factory = constrained_factory(Annotated[list[int], "whatever"])
        self.assertIsInstance(factory, partial)
        self.assertEqual(factory.keywords["basetype"][0], int)

    def test_constrained_factory_fallback(self) -> None:
        class Unsupported:
            pass

        factory = constrained_factory(Unsupported)
        self.assertTrue(callable(factory))
        self.assertEqual(factory("any"), "any")

    def test_constrained_str_none_allowed_fallback(self) -> None:
        result = ConstrainedStr("abc", min_length=2)
        self.assertEqual(result, "abc")

    def func(
        self,
        arg1: Annotated[UUID, 123, ConstrArgInject(constrained_factory, ...)],
        arg2: Annotated[datetime, ConstrArgInject(constrained_factory, ...)],
        arg3: str = ConstrArgInject(constrained_factory, ..., min_length=3),
        arg4: MyEnum = ConstrArgInject(constrained_factory, ...),
        arg5: list[str] = ConstrArgInject(constrained_factory, ..., max_length=5),
    ) -> None:
        return None

    async def test_full_constrained(self) -> None:
        ctx: dict[str, Any] = {
            "arg1": "3cd4d94e-61e9-4c90-bd39-9207a1fb7227",
            "arg2": "22-12-07",
            "arg3": "foobar",
            "arg4": MyEnum.INVALID,
            "arg5": ["hello"],
        }
        await inject_args(self.func, ctx)

    async def test_full_constrained_fail_uuid(self) -> None:
        ctx: dict[str, Any] = {
            "arg1": "NotUUID",
            "arg2": "22-12-07",
            "arg3": "foobar",
            "arg4": MyEnum.INVALID,
            "arg5": ["hello"],
        }
        with self.assertRaises(ValueError):
            await inject_args(self.func, ctx)

    async def test_full_constrained_fail_datetime(self) -> None:
        ctx: dict[str, Any] = {
            "arg1": "3cd4d94e-61e9-4c90-bd39-9207a1fb7227",
            "arg2": "99-15-07",
            "arg3": "foobar",
            "arg4": MyEnum.INVALID,
            "arg5": ["hello"],
        }
        with self.assertRaises(ValueError):
            await inject_args(self.func, ctx)

    def test_constrained_items_set_tuple(self) -> None:
        ConstrainedItems({1, 2}, [int], min_items=1, max_items=3, gt=0)
        with self.assertRaises(ValueError):
            ConstrainedItems((1, 2, 3, 4), [int], max_items=3)

    def test_constrained_datetime_custom_format(self) -> None:
        may_1_24 = "2024-05-01"
        self.assertEqual(ConstrainedDatetime(may_1_24), datetime(2024, 5, 1))
        self.assertEqual(
            ConstrainedDatetime(may_1_24, fmt="%Y-%m-%d"), datetime(2024, 5, 1)
        )
        with self.assertRaises(ValueError):
            ConstrainedDatetime("01/05/2024", fmt="%Y-%m-%d")

        with self.assertRaises(ValueError):
            ConstrainedDatetime("01/05/2024", from_=datetime(2025, 1, 1))

        with self.assertRaises(ValueError):
            ConstrainedDatetime("01/05/2024", to_=datetime(2023, 1, 1))

    def test_custom(self) -> None:

        def validator(instance: Any, **kwrags: Any) -> None:
            raise ValueError

        arg = ConstrArgInject(constrained_factory, validator=validator)

        with self.assertRaises(ValueError):
            arg.validate("hello", str)
