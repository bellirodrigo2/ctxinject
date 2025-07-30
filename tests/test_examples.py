import pytest

from example.api_example import main as api_main
from example.http_example import main as http_main


@pytest.mark.asyncio
async def test_http() -> None:
    await http_main()


@pytest.mark.asyncio
async def test_api() -> None:
    await api_main()
