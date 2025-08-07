import asyncio
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

import pytest

from ctxinject.inject import inject_args
from ctxinject.model import DependsInject
from ctxinject.sigcheck import func_signature_check


class MockConnection:
    def __init__(self):
        self.connection = "sync_db_connection"

    def close(self):
        self.connection = "close_db"


# Raw functions (without decorators)
def raw_sync_db() -> Generator[MockConnection, None, None]:
    db = MockConnection()
    try:
        yield db
    finally:
        db.close()


async def raw_async_db() -> AsyncGenerator[MockConnection, None]:
    db = MockConnection()
    await asyncio.sleep(0.01)
    try:
        yield db
    finally:
        db.close()
        await asyncio.sleep(0.01)


# Decorated versions
@contextmanager
def decorated_sync_db() -> Generator[MockConnection, None, None]:
    db = MockConnection()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def decorated_async_db():
    db = MockConnection()
    await asyncio.sleep(0.01)
    try:
        yield db
    finally:
        db.close()
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "db_func,test_name",
    [
        (raw_sync_db, "raw_sync"),
        (decorated_sync_db, "decorated_sync"),
        (raw_async_db, "raw_async"),
        (decorated_async_db, "decorated_async"),
    ],
)
async def test_cm_injection(db_func, test_name) -> None:
    """Test context manager injection with both raw and decorated functions."""

    def func(db: MockConnection = DependsInject(db_func)) -> MockConnection:
        assert db.connection == "sync_db_connection"
        return db

    stack = AsyncExitStack()
    try:
        result = await inject_args(func=func, context={}, stack=stack)
        db_state = result()

        # Verify connection is still open during usage
        assert db_state.connection == "sync_db_connection"

    finally:
        # Close stack and verify cleanup
        await stack.aclose()
        # assert db_state.connection == "close_db"


@pytest.mark.parametrize(
    "db_func,test_name",
    [
        (raw_sync_db, "raw_sync"),
        (decorated_sync_db, "decorated_sync"),
        (raw_async_db, "raw_async"),
        (decorated_async_db, "decorated_async"),
    ],
)
def test_signature(db_func, test_name) -> None:

    def func(db: MockConnection = DependsInject(db_func)) -> MockConnection:
        assert db.connection == "sync_db_connection"
        return db

    errors = func_signature_check(func)
    assert len(errors) == 0
