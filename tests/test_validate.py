import json
import unittest
from datetime import date, datetime, time
from typing import Any, Dict, List
from uuid import UUID

import orjson
from typemapping import get_func_args

from ctxinject.model import ModelFieldInject
from ctxinject.validate import inject_validation


class TestValidation(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def test_validate_str(self) -> None:
        class Model:
            x: str

        def func(
            arg: str = ModelFieldInject(model=Model, field="x", min_length=6)
        ) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        self.assertEqual(modelinj.validate("helloworld", str), "helloworld")

        with self.assertRaises(ValueError):
            modelinj.validate("hello", str)

    def test_validate_int(self) -> None:
        class Model:
            x: int

        def func(arg: int = ModelFieldInject(model=Model, field="x", gt=6)) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        self.assertEqual(modelinj.validate(12, int), 12)

        with self.assertRaises(ValueError):
            modelinj.validate(4, int)

    def test_validate_float(self) -> None:
        class Model:
            x: float

        def func(arg: float = ModelFieldInject(model=Model, field="x", gt=6)) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        self.assertEqual(modelinj.validate(6.5, basetype=float), 6.5)

        with self.assertRaises(ValueError):
            modelinj.validate(5.5, basetype=float)

    def test_validate_list(self) -> None:
        class Model:
            x: List[str]

        def func(
            arg: List[str] = ModelFieldInject(model=Model, field="x", max_items=1)
        ) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        self.assertEqual(modelinj.validate(["foo"], basetype=list[str]), ["foo"])

        with self.assertRaises(ValueError):
            modelinj.validate(["foo", "bar"], basetype=list[str])

    def test_validate_dict(self) -> None:
        class Model:
            x: Dict[str, str]

        def func(
            arg: Dict[str, str] = ModelFieldInject(model=Model, field="x", max_items=1)
        ) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        self.assertEqual(
            modelinj.validate({"foo": "bar"}, basetype=Dict[str, str]), {"foo": "bar"}
        )

        with self.assertRaises(ValueError):
            modelinj.validate({"foo": "bar", "hello": "world"}, basetype=Dict[str, str])

    def test_validate_date(self) -> None:
        class Model:
            x: str

        def func(
            arg: date = ModelFieldInject(model=Model, field="x", from_=date(2024, 1, 1))
        ) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        self.assertEqual(
            modelinj.validate("2024-06-06", basetype=date), date(2024, 6, 6)
        )

        with self.assertRaises(ValueError):
            modelinj.validate("2023-06-06", basetype=date)

    def test_validate_time(self) -> None:
        class Model:
            x: str

        def func(
            arg: time = ModelFieldInject(model=Model, field="x", from_=time(2, 2, 2))
        ) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        self.assertEqual(modelinj.validate("03:03:03", basetype=time), time(3, 3, 3))

        with self.assertRaises(ValueError):
            modelinj.validate("01:01:01", basetype=time)

    def test_validate_datetime(self) -> None:
        class Model:
            x: str

        def func(
            arg: datetime = ModelFieldInject(
                model=Model, field="x", from_=datetime(2024, 1, 1)
            )
        ) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        self.assertEqual(
            modelinj.validate("2024-06-06", basetype=datetime), datetime(2024, 6, 6)
        )

        with self.assertRaises(ValueError):
            modelinj.validate("2023-06-06", basetype=datetime)

    def test_validate_uuid(self) -> None:
        class Model:
            x: str

        def func(arg: UUID = ModelFieldInject(model=Model, field="x")) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        modelinj.validate("94fa2f76-84c7-484e-95ee-5fc3fabbd9fb", basetype=UUID)
        with self.assertRaises(ValueError):
            modelinj.validate("NONUUID", basetype=UUID)

    def test_validate_json(self) -> None:
        class Model:
            x: str

        def func(
            arg: Dict[str, Any] = ModelFieldInject(
                model=Model,
                field="x",
            )
        ) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        data = {"foo": "bar"}
        self.assertEqual(
            modelinj.validate(json.dumps(data), basetype=Dict[str, Any]), data
        )

        with self.assertRaises(ValueError):
            modelinj.validate("no json", basetype=Dict[str, Any])

    def test_validate_bytesjson(self) -> None:
        class Model:
            x: bytes

        def func(
            arg: Dict[str, Any] = ModelFieldInject(
                model=Model,
                field="x",
            )
        ) -> None:
            return

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        self.assertFalse(modelinj.has_validate)
        inject_validation(func)
        self.assertTrue(modelinj.has_validate)
        data = {"foo": "bar"}
        self.assertEqual(
            modelinj.validate(orjson.dumps(data), basetype=Dict[str, Any]), data
        )

        with self.assertRaises(ValueError):
            modelinj.validate("no json", basetype=Dict[str, Any])
