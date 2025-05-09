import re
from datetime import date, datetime, time
from enum import Enum
from functools import partial
from typing import (
    Annotated,
    Any,
    Callable,
    Mapping,
    Optional,
    Sequence,
    Union,
    get_args,
    get_origin,
)
from uuid import UUID

from dateutil.parser import parse

from ctxinject.exceptions import ValidationError

def ConstrainedStr(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    **_: Any,
) -> str:
    # if not isinstance(value, str):  # type: ignore
    # raise ValidationError("Value must be a string")
    if min_length is not None and not (min_length <= len(value)):
        raise ValidationError(f"String length must be minimun {min_length}")
    if max_length is not None and not (len(value) <= max_length):
        raise ValidationError(f"String length must be maximun {max_length}")

    if pattern and not re.match(pattern, value):
        raise ValidationError(f"String does not match pattern: {pattern}")

    return value


def ConstrainedNumber(
    value: Union[int, float],
    gt: Optional[Union[int, float]] = None,
    ge: Optional[Union[int, float]] = None,
    lt: Optional[Union[int, float]] = None,
    le: Optional[Union[int, float]] = None,
    multiple_of: Optional[Union[int, float]] = None,
    **_: Any,
) -> Union[int, float]:
    # if not isinstance(value, int) and not isinstance(value, float):  # type: ignore
    # raise ValidationError("Value must be an integer or float")

    if gt is not None and not value > gt:
        raise ValidationError(f"Value must be > {gt}")
    if ge is not None and not value >= ge:
        raise ValidationError(f"Value must be >= {ge}")
    if lt is not None and not value < lt:
        raise ValidationError(f"Value must be < {lt}")
    if le is not None and not value <= le:
        raise ValidationError(f"Value must be <= {le}")
    if multiple_of is not None and value % multiple_of != 0:
        raise ValidationError(f"Value must be a multiple of {multiple_of}")

    return value


def ConstrainedItems(
    value: Sequence[Any],
    basetype: tuple[type[Any], ...],
    values_check: Optional[Mapping[str, Any]] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    **kwargs: Any,
) -> list[Any]:
    # if not isinstance(value, list) and not isinstance(value, tuple) and not isinstance(value, set):  # type: ignore
    # raise ValidationError("Value must be a List, Tuple or Set")

    if min_items is not None and len(value) < min_items:
        raise ValidationError(...)
    if max_items is not None and len(value) > max_items:
        raise ValidationError(...)

    v = value
    if isinstance(value, dict):
        v = list(value.keys())

    constrained = constrained_factory(basetype[0])
    for item in v:
        constrained(item, **kwargs)
    if isinstance(value, dict) and values_check is not None:
        constrained = constrained_factory(basetype[1])
        for item in value.values():
            constrained(item, **kwargs)

    return value


def ConstrainedDatetime(
    value: str,
    which: type[Any] = datetime,
    fmt: Optional[str] = None,
    **_: Any,
) -> Union[datetime, date, time]:
    try:
        if fmt is not None:
            dt: datetime = datetime.strptime(value, fmt)
        else:
            dt = parse(value)

        if which == date:
            return dt.date()
        if which == time:
            return dt.time()
        return dt

    except Exception:
        raise ValidationError(
            f'Arg value should be a valid datetime string. Found "{value}"'
        )


def ConstrainedUUID(value: str, **_: Any) -> UUID:
    try:
        return UUID(value)
    except Exception:
        raise ValidationError(
            f'Arg value should be a valid UUID string. Found "{value}"'
        )


def ConstrainedEnum(value: Any, baseenum: type[Enum], **_: Any) -> Enum:
    if not isinstance(value, baseenum):
        raise ValidationError(
            f'Arg should be of type "{baseenum}", but "{type(value)}" was found'
        )

    return value


def constrained_factory(basetype: type[Any]) -> Callable[..., Any]:
    if isinstance(basetype, type):  # type: ignore
        if issubclass(basetype, str):
            return ConstrainedStr
        if issubclass(basetype, int) or issubclass(basetype, float):
            return ConstrainedNumber
        if (
            issubclass(basetype, datetime)
            or issubclass(basetype, date)
            or issubclass(basetype, time)
        ):
            return partial(ConstrainedDatetime, which=basetype)
        if issubclass(basetype, UUID):
            return ConstrainedUUID
        if issubclass(basetype, Enum):

            return partial(ConstrainedEnum, baseenum=basetype)
    else:
        origin = get_origin(basetype)
        args = get_args(basetype)
        if origin is Annotated:
            origin = get_origin(args[0])
            args = get_args(args[0])
        if origin is list or origin is tuple or origin is set or origin is dict:
            return partial(ConstrainedItems, basetype=args)

    def return_only(value: Any, **kwargs: Any) -> Any:
        return value

    return return_only
