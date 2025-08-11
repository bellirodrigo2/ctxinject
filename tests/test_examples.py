from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_api_example() -> None:
    from example.api_example import main

    with patch("builtins.print"):
        await main()


@pytest.mark.asyncio
async def test_http_example() -> None:
    from example.http_example import main

    with patch("builtins.print"):
        await main()


@pytest.mark.asyncio
async def test_override_example() -> None:
    from example.override_example import main

    with patch("builtins.print"):
        await main()
