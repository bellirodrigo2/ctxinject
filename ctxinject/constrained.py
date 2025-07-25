import re
from datetime import date, datetime, time
from enum import Enum
from functools import partial
from uuid import UUID

from dateutil.parser import ParserError
from dateutil.parser import parse as parsedate
from typing_extensions import (
    Annotated,
    Any,
    Callable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)


def ConstrainedStr(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    **_: Any,
) -> str:
    if min_length is not None and not (min_length <= len(value)):
        raise ValueError(f"String length must be minimun {min_length}")
    if max_length is not None and not (len(value) <= max_length):
        raise ValueError(f"String length must be maximun {max_length}")

    if pattern and not re.match(pattern, value):
        raise ValueError(f"String does not match pattern: {pattern}")

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
    # raise ValueError("Value must be an integer or float")
    if gt is not None and not value > gt:
        raise ValueError(f"Value must be > {gt}")
    if ge is not None and not value >= ge:
        raise ValueError(f"Value must be >= {ge}")
    if lt is not None and not value < lt:
        raise ValueError(f"Value must be < {lt}")
    if le is not None and not value <= le:
        raise ValueError(f"Value must be <= {le}")
    if multiple_of is not None and value % multiple_of != 0:
        raise ValueError(f"Value must be a multiple of {multiple_of}")

    return value


def ConstrainedItems(
    value: Sequence[Any],
    basetype: Tuple[Type[Any], ...],
    values_check: Optional[Mapping[str, Any]] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    **kwargs: Any,
) -> Sequence[Any]:

    length = len(value)
    if min_items is not None and length < min_items:
        raise ValueError(
            f"Sequence must have at least {min_items} items. Found {length}"
        )
    if max_items is not None and length > max_items:
        raise ValueError(
            f"Sequence must have at most {max_items} items. Found {length}"
        )

    v = value
    if isinstance(value, dict):
        v = list(value.keys())  # type: ignore

    constrained = constrained_factory(basetype[0])
    for item in v:
        constrained(item, **kwargs)
    if isinstance(value, dict) and values_check is not None:
        constrained = constrained_factory(basetype[1])
        for item in value.values():
            constrained(item, **values_check)

    return value


def ConstrainedDatetime(
    value: str,
    from_: Optional[Union[datetime, date, time]] = None,
    to_: Optional[Union[datetime, date, time]] = None,
    which: Type[Union[datetime, date, time]] = datetime,
    fmt: Optional[str] = None,
    **_: Any,
) -> Union[datetime, date, time]:
    try:
        try:
            dt: datetime = datetime.strptime(value, fmt)  # type: ignore
        except TypeError:
            dt = parsedate(value)

        if which == date:
            dt = dt.date()  # type: ignore
        elif which == time:
            dt = dt.time()  # type: ignore

        # the lines below can raise Valueerror
        if from_ is not None and dt < from_:  # type: ignore
            raise ValueError(f"Datetime value must be on or after {from_}")
        if to_ is not None and dt > to_:  # type: ignore
            raise ValueError(f"Datetime value must be on or before {to_}")

        return dt

    except (ValueError, TypeError, ParserError) as e:
        raise ValueError(
            f'Arg value should be a valid datetime string. Found "{value}" \n {e}'
        )


def ConstrainedUUID(value: str, **_: Any) -> UUID:
    try:
        return UUID(value)
    except Exception:
        raise ValueError(f'Arg value should be a valid UUID string. Found "{value}"')


def ConstrainedEnum(value: Any, baseenum: Type[Enum], **_: Any) -> Enum:
    if not isinstance(value, baseenum):
        raise ValueError(
            f'Arg should be of type "{baseenum}", but "{type(value)}" was found'
        )

    return value


def constrained_factory(basetype: Type[Any]) -> Callable[..., Any]:
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
