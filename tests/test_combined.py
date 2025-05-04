from dataclasses import dataclass

import pytest

from ctxinject.inject import resolve
from ctxinject.model import (
    ArgsInjectable,
    Depends,
    ModelFieldInject,
    UnresolvedInjectableError,
)


class User(str): ...


@dataclass
class Settings:
    debug: bool
    timeout: int


# Função no segundo nível de dependência
def sub_dep(
    uid: int = ArgsInjectable(...),  # resolve por nome
    timeout: int = ModelFieldInject(
        Settings, field="timeout"
    ),  # resolve por model.field
) -> str:
    return f"{uid}-{timeout}"


# Função no primeiro nível de dependência
def mid_dep(
    name: User,  # resolve por tipo
    uid: int = Depends(sub_dep),  # resolve via Depends
    debug: bool = Depends(lambda debug: not debug),  #  resolve por nome
) -> str:
    return f"{name}-{uid}-{debug}"


# Handler principal, com múltiplas fontes de contexto
async def handler(
    name: User,  # por tipo
    id: int = ArgsInjectable(),  # por nome
    to: int = ModelFieldInject(Settings, field="timeout"),  # por model + field fallback
    combined: str = Depends(mid_dep),  # nível 1
    extra: str = Depends(lambda: "static"),  # independente do contexto
) -> str:
    return f"{name}|{id}|{to}|{combined}|{extra}"


@pytest.mark.asyncio
async def test_mixed_injectables() -> None:
    # Contexto fornecido
    context = {
        "id": 42,  # para ArgsInjectable
        "uid": 99,
        "debug": False,
        User: "Alice",  # para name (por tipo)
        Settings: Settings(debug=True, timeout=30),  # para ModelFieldInject e debug
    }

    result = await resolve(handler, context=context, overrides={})
    assert result == "Alice|42|30|Alice-99-False|static"


@pytest.mark.asyncio
async def test_mixed_injectables_missing_ctx() -> None:
    # Contexto fornecido
    context = {
        "id": 42,  # para ArgsInjectable
        "debug": False,
        User: "Alice",  # para name (por tipo)
        Settings: Settings(debug=True, timeout=30),  # para ModelFieldInject e debug
    }

    with pytest.raises(UnresolvedInjectableError):
        await resolve(handler, context=context, overrides={})
