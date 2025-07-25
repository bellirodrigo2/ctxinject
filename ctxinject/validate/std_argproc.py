from datetime import date, datetime, time
from typing import Hashable
from uuid import UUID

from typing_extensions import Any, Callable, Dict, List, Tuple, Union

from ctxinject.constrained import ConstrainedNumber, ConstrainedStr, ConstrainedUUID
from ctxinject.validate.common_validators import (
    constrained_bytejson,
    constrained_date,
    constrained_datetime,
    constrained_json,
    constrained_time,
)


def constrained_str(value: str, **kwargs: Any) -> str:

    min_length = kwargs.get("min_length", None)
    max_length = kwargs.get("max_length", None)
    pattern = kwargs.get("pattern", None)

    return ConstrainedStr(value, min_length, max_length, pattern)


def constrained_num(value: Union[int, float], **kwargs: Any) -> Union[int, float]:

    gt = kwargs.get("gt", None)
    ge = kwargs.get("ge", None)
    lt = kwargs.get("lt", None)
    le = kwargs.get("le", None)
    multiple_of = kwargs.get("multiple_of", None)

    return ConstrainedNumber(value, gt, ge, lt, le, multiple_of)


def constrained_list(
    value: List[Any],
    **kwargs: Any,
) -> List[Any]:

    min_length = kwargs.get("min_length", None)
    max_length = kwargs.get("max_length", None)
    length = len(value)

    if min_length is not None and length < min_length:
        raise ValueError(
            f"List has {length} items, but should have at least {min_length}"  # ✅ FIXED
        )
    if max_length is not None and length > max_length:
        raise ValueError(
            f"List has {length} items, but should have at most {max_length}"  # ✅ FIXED
        )
    return value


def constrained_dict(
    value: Dict[Any, Any],
    **kwargs: Any,
) -> Dict[Any, Any]:

    constrained_list(list(value.values()), **kwargs)

    return value


def constrained_uuid(
    value: str,
    **kwargs: Any,
) -> UUID:
    return ConstrainedUUID(value, **kwargs)


def return_only(
    t: Any,
    **kwargs: Any,
) -> Any:
    return t


arg_proc: Dict[Tuple[Hashable, Hashable], Callable[..., Any]] = {
    (str, str): constrained_str,
    (int, int): constrained_num,
    (float, float): constrained_num,
    (list, list): constrained_list,
    (dict, dict): constrained_dict,
    (str, date): constrained_date,
    (str, time): constrained_time,
    (str, datetime): constrained_datetime,
    (str, UUID): constrained_uuid,
    (str, dict): constrained_json,
    (bytes, dict): constrained_bytejson,
}
