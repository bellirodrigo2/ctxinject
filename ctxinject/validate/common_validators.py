import json
from datetime import date, datetime, time
from uuid import UUID

import orjson
from typing_extensions import Any, Dict, Type, Union

from ctxinject.constrained import ConstrainedDatetime, ConstrainedUUID


def _constrained_datetime(
    value: str,
    which: Type[Union[datetime, date, time]],
    **kwargs: Any,
) -> Union[datetime, date, time]:

    fmt = kwargs.get("fmt", None)
    start = kwargs.get("start", None)
    end = kwargs.get("end", None)
    return ConstrainedDatetime(value, start, end, which, fmt)


def constrained_date(
    value: str,
    **kwargs: Any,
) -> date:
    return _constrained_datetime(value, date, **kwargs)  # type: ignore


def constrained_time(
    value: str,
    **kwargs: Any,
) -> time:
    return _constrained_datetime(value, time, **kwargs)  # type: ignore


def constrained_datetime(
    value: str,
    **kwargs: Any,
) -> datetime:
    return _constrained_datetime(value, datetime, **kwargs)  # type: ignore


def constrained_uuid(
    value: str,
    **kwargs: Any,
) -> UUID:
    return ConstrainedUUID(value, **kwargs)


def constrained_json(
    value: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")  # ✅ FIXED


def constrained_bytejson(
    value: bytes,
    **kwargs: Any,
) -> Dict[str, Any]:
    try:
        return orjson.loads(value)
    except orjson.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")  # ✅ FIXED (consistency)
