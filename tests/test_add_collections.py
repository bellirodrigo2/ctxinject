from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Type

import pytest

from ctxinject.model import ModelFieldInject
from ctxinject.validate.collections_add_model import collections_add_model
from ctxinject.validate.inject_validation import inject_validation


@pytest.fixture
def model() -> Type[Any]:
    class Model:
        def init(
            self,
            a: Dict[str, str],
            b: Mapping[str, str],
            c: MutableMapping[str, str],
            d: List[str],
            e: Sequence[str],
            f: Iterable[str],
        ) -> None:
            pass

    return Model


def test_mapping() -> None:

    class Model:
        def __init__(
            self,
            a: Dict[str, str],
            b: Mapping[str, str],
            c: MutableMapping[str, str],
        ) -> None:
            pass

    def func(
        a: Mapping[str, str] = ModelFieldInject(Model),
        a1: MutableMapping[str, str] = ModelFieldInject(Model, field="a"),
        a2: Dict[str, str] = ModelFieldInject(Model, field="a"),
        b: Mapping[str, str] = ModelFieldInject(Model),
        b1: MutableMapping[str, str] = ModelFieldInject(Model, field="b"),
        b2: Dict[str, str] = ModelFieldInject(Model, field="b"),
        c: Mapping[str, str] = ModelFieldInject(Model),
        c1: MutableMapping[str, str] = ModelFieldInject(Model, field="c"),
        c2: Dict[str, str] = ModelFieldInject(Model, field="c"),
    ) -> None: ...

    argsproc = {}
    inject_validation(func=func, argproc=argsproc, add_model=[collections_add_model])
    assert len(argsproc) == 6


def test_list() -> None:

    class Model:
        def __init__(
            self,
            a: List[str],
            b: Sequence[str],
            c: Iterable[str],
        ) -> None:
            pass

    def func(
        a: List[str] = ModelFieldInject(Model),
        a1: Sequence[str] = ModelFieldInject(Model, field="a"),
        a2: Iterable[str] = ModelFieldInject(Model, field="a"),
        b: List[str] = ModelFieldInject(Model),
        b1: Sequence[str] = ModelFieldInject(Model, field="b"),
        b2: Iterable[str] = ModelFieldInject(Model, field="b"),
        c: List[str] = ModelFieldInject(Model),
        c1: Sequence[str] = ModelFieldInject(Model, field="c"),
        c2: Iterable[str] = ModelFieldInject(Model, field="c"),
    ): ...

    argsproc = {}
    inject_validation(func=func, argproc=argsproc, add_model=[collections_add_model])
    assert len(argsproc) == 6
