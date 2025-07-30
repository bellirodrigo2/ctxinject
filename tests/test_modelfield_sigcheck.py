from dataclasses import dataclass
from typing import (
    Any,
    Container,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Sequence,
    Type,
)

import pytest
from typemapping import get_func_args

from ctxinject.model import ModelFieldInject
from ctxinject.sigcheck import check_modefield_types


class Init:
    def __init__(self, name: str, names: List[str]) -> None:
        self.name = name
        self.names = names


class InitDerived(Init):
    def __init__(self, name: str, names: List[str], names_dict: Dict[str, str]) -> None:
        super().__init__(name, names)
        self.names_dict = names_dict


class Model:
    name: str
    names: List[str]


class DerivedModel(Model):
    names_dict: Dict[str, str]


@dataclass
class Dataclass:
    name: str
    names: List[str]


@dataclass
class DerivedDataClass(Dataclass):
    names_dict: Dict[str, str]


@pytest.mark.parametrize(
    "cls, derived_cls",
    [(Init, InitDerived), (Model, DerivedModel), (Dataclass, DerivedDataClass)],
)
def test_(cls: Type[Any], derived_cls: Type[Any]) -> None:
    def func(
        arg1: str = ModelFieldInject(cls, field="name"),
        arg2: List[str] = ModelFieldInject(cls, field="names"),
        arg3: Dict[str, str] = ModelFieldInject(derived_cls, field="names_dict"),
        arg4: Sequence[str] = ModelFieldInject(cls, field="names"),
        arg5: Iterable[str] = ModelFieldInject(cls, field="names"),
        arg6: Container[str] = ModelFieldInject(cls, field="names"),
        arg8: Mapping[str, str] = ModelFieldInject(derived_cls, field="names_dict"),
        arg9: MutableMapping[str, str] = ModelFieldInject(
            derived_cls, field="names_dict"
        ),
    ) -> None: ...

    args = get_func_args(func)
    errors = check_modefield_types(args)
    assert errors == []
