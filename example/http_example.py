import asyncio

import requests
from pydantic import BaseModel
from typing_extensions import (
    Annotated,
    Any,
    Callable,
    Dict,
    Mapping,
    Optional,
    Protocol,
)

from ctxinject.inject import get_mapped_ctx, inject_args, resolve_mapped_ctx
from ctxinject.model import DependsInject, ModelFieldInject


class PreparedRequest(Protocol):
    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes


class BodyModel(BaseModel):
    name: str
    email: str
    age: int


async def get_db() -> str:
    await asyncio.sleep(0.1)
    return "postgresql"


class FromRequest(ModelFieldInject):
    def __init__(
        self,
        field: Optional[str] = None,
        validator: Optional[Callable[..., Any]] = None,
        **meta: Any,
    ):
        super().__init__(PreparedRequest, field, validator, **meta)


def process_http(
    url: Annotated[str, FromRequest()],
    method: Annotated[str, FromRequest()],
    body: Annotated[BodyModel, FromRequest()],
    headers: Annotated[Dict[str, str], FromRequest()],
    db: str = DependsInject(get_db),
) -> Mapping[str, str]:
    return {
        "url": url,
        "method": method,
        "body": body,
        "headers": len(headers),
        "db": db,
    }


async def main() -> None:

    method = "POST"
    url = "https://api.example.com/user"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer you_token_here",
        "User-Agent": "MeuApp/1.0",
    }
    cookies = {"session_id": "abc123def456", "user_pref": "dark_mode"}
    data = {"name": "João Silva", "email": "joao@email.com", "age": 30}

    # create a real Requests request object
    req = requests.Request(
        method=method,
        url=url,
        headers=headers,
        cookies=cookies,
        json=data,
    )
    prepared_req: PreparedRequest = req.prepare()

    # this "input_ctx" object is required, since prepared_req is not a PreparedRequest object
    # if prepared_req where a PreparedRequest object (not a protocol),
    # it could be passed directly to inject_args function context arg,
    # but since requests.models.PreparedRequest is not typed, this patch is required
    input_ctx = {PreparedRequest: prepared_req}

    func = await inject_args(func=process_http, context=input_ctx)
    resp = func()
    assert resp["url"] == url
    assert resp["method"] == method
    assert isinstance(resp["body"], BaseModel)
    assert resp["headers"] == 5
    assert resp["db"] == "postgresql"

    mapped_ctx = get_mapped_ctx(func=process_http, context={PreparedRequest: None})
    kwargs = await resolve_mapped_ctx(input_ctx=input_ctx, mapped_ctx=mapped_ctx)
    resp = func(**kwargs)
    resp = func()
    assert resp["url"] == url
    assert resp["method"] == method
    assert isinstance(resp["body"], BaseModel)
    assert resp["headers"] == 5
    assert resp["db"] == "postgresql"

    def mocked_get_db() -> str:
        return "test"

    func = await inject_args(
        func=process_http, context=input_ctx, overrides={get_db: mocked_get_db}
    )
    resp = func()
    assert not resp["db"] == "postgresql"
    assert resp["db"] == "test"
    print("HTTP request processed!!!")


if __name__ == "__main__":
    asyncio.run(main())
