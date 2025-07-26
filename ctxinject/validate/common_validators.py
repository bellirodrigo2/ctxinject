import json
from datetime import date, datetime, time

import orjson
from typing_extensions import Any, Callable, Dict, Hashable, Tuple, Type, Union

from ctxinject.constrained import ConstrainedDatetime


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


common_arg_proc: Dict[Tuple[Hashable, Hashable], Callable[..., Any]] = {
    (str, date): constrained_date,
    (str, time): constrained_time,
    (str, datetime): constrained_datetime,
    (str, dict): constrained_json,
    (bytes, dict): constrained_bytejson,
}
