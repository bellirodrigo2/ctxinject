import json
from datetime import date, datetime, time
from uuid import UUID

import orjson
from typemapping import get_field_type, get_func_args
from typing_extensions import (
    Any,
    Callable,
    Dict,
    List,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_origin,
)

from ctxinject.constrained import (
    ConstrainedDatetime,
    ConstrainedNumber,
    ConstrainedStr,
    ConstrainedUUID,
)
from ctxinject.model import ModelFieldInject


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

    min_items = kwargs.get("min_items", None)
    max_items = kwargs.get("max_items", None)

    if min_items is not None and len(value) < min_items:
        raise ValueError(...)
    if max_items is not None and len(value) > max_items:
        raise ValueError(...)
    return value


def constrained_dict(
    value: Dict[Any, Any],
    **kwargs: Any,
) -> Dict[Any, Any]:

    constrained_list(list(value.values()), **kwargs)

    return value


def _constrained_datetime(
    value: str,
    which: Union[datetime, date, time],
    **kwargs: Any,
) -> Union[datetime, date, time]:

    fmt = kwargs.get("fmt", None)
    from_ = kwargs.get("from_", None)
    to_ = kwargs.get("to_", None)
    return ConstrainedDatetime(value, from_, to_, which, fmt)


def constrained_date(
    value: str,
    **kwargs: Any,
) -> date:
    return _constrained_datetime(value, date, **kwargs)


def constrained_time(
    value: str,
    **kwargs: Any,
) -> time:
    return _constrained_datetime(value, time, **kwargs)


def constrained_datetime(
    value: str,
    **kwargs: Any,
) -> datetime:
    return _constrained_datetime(value, datetime, **kwargs)


def constrained_uuid(
    value: str,
    **kwargs: Any,
) -> UUID:
    return ConstrainedUUID(value, **kwargs)


def constrained_json(
    value: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    # try:
    return json.loads(value)
    # except json.JSONDecodeError as e:
    # raise ValueError(str(e))


def constrained_bytejson(
    value: bytes,
    **kwargs: Any,
) -> Dict[str, Any]:
    return orjson.loads(value)


def return_only(
    t: Any,
    **kwargs: Any,
) -> Any:
    return t


arg_proc: Dict[Tuple[type[Any], Type[Any]], Callable[..., Any]] = {
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


def extract_type(bt: Type[Any]) -> Type[Any]:
    if not isinstance(bt, type):
        return get_origin(bt)
    return bt


T = TypeVar("T")


def inject_validation(
    func: Callable[..., Any],
    argproc: Dict[Tuple[type[Any], Type[Any]], Callable[..., Any]] = arg_proc,
    extracttype: Callable[[type[T]], Type[T]] = extract_type,
) -> None:

    args = get_func_args(func)

    for arg in args:
        instance = arg.getinstance(ModelFieldInject)
        if instance is None:
            continue
        fieldname = instance.field or arg.name
        modeltype = get_field_type(instance.model, fieldname)
        argtype = arg.basetype

        if modeltype is None or argtype is None:
            continue

        modeltype = extracttype(modeltype)
        argtype = extracttype(argtype)
        validator = argproc.get((modeltype, argtype), None)
        if validator is not None and instance._validator is None:
            instance._validator = validator

        # da pra tentar aqui baseado em subclass
