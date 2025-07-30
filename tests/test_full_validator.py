import copy
from pathlib import Path

import pytest

from ctxinject.inject import inject_args
from ctxinject.model import ArgsInjectable, DependsInject, ModelFieldInject


class MyModel:
    def __init__(self, name: str) -> None:
        self.name = name


def get_db() -> str:
    return "sqlite"


def func(
    byname: str = ArgsInjectable(min_length=3),
    bytype: Path = ArgsInjectable(min_length=3),
    bymodeltype: str = ModelFieldInject(MyModel, field="name", min_length=3),
    depends: str = DependsInject(get_db, min_length=3),
):
    pass


modeltest = MyModel("foobar")
ctx = {"byname": "thisisaname", Path: Path("./"), MyModel: modeltest}


@pytest.mark.asyncio
async def test_basic_ok() -> None:
    await inject_args(func, ctx, False, True)


@pytest.mark.asyncio
async def test_basic_break() -> None:

    ctx2 = copy.deepcopy(ctx)
    ctx2["byname"] = "a"
    with pytest.raises(ValueError):
        await inject_args(func, ctx2, False, True)

    ctx3 = copy.deepcopy(ctx)
    ctx3[MyModel] = MyModel(name="a")

    with pytest.raises(ValueError):
        await inject_args(func, ctx3, False, True)

    with pytest.raises(ValueError):
        await inject_args(func, ctx, False, True, {get_db: lambda: "s"})
