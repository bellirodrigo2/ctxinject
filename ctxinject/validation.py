import json
import re
from datetime import date, datetime, time
from functools import lru_cache, partial
from uuid import UUID

import orjson
from dateutil.parser import ParserError
from dateutil.parser import parse as parsedate
from typemapping import defensive_issubclass, get_equivalent_origin
from typing_extensions import (
    Annotated,
    Any,
    Callable,
    Dict,
    Hashable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)


class ValidationError(ValueError):
    """Validation error for ctxinject validation functions."""

    pass


def ConstrainedStr(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    **_: Any,
) -> str:
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
    # raise ValueError("Value must be an integer or float")
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


def ConstrainedUUID(value: str, **_: Any) -> UUID:
    try:
        return UUID(value)
    except Exception:
        raise ValidationError(
            f'Arg value should be a valid UUID string. Found "{value}"'
        )


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
            raise ValidationError(f"Datetime value must be on or after {from_}")
        if to_ is not None and dt > to_:  # type: ignore
            raise ValidationError(f"Datetime value must be on or before {to_}")

        return dt

    except (ValidationError, ValueError, TypeError, ParserError) as e:
        raise ValidationError(
            f'Arg value should be a valid datetime string. Found "{value}" \n {e}'
        )


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
        return json.loads(value)  # type: ignore
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")


def constrained_bytejson(
    value: bytes,
    **kwargs: Any,
) -> Dict[str, Any]:
    try:
        return orjson.loads(value)  # type: ignore
    except orjson.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")


def base_constrained_list(
    value: List[Any],
    **kwargs: Any,
) -> List[Any]:
    min_length = kwargs.get("min_length", None)
    max_length = kwargs.get("max_length", None)
    length = len(value)
    if min_length is not None and length < min_length:
        raise ValidationError(
            f"List has {length} items, but should have at least {min_length}"
        )
    if max_length is not None and length > max_length:
        raise ValidationError(
            f"List has {length} items, but should have at most {max_length}"
        )
    return value


def base_constrained_dict(
    value: Dict[Any, Any],
    **kwargs: Any,
) -> Dict[Any, Any]:
    constrained_list(list(value.values()), **kwargs)
    return value


def constrained_uuid(  # type: ignore
    value: str,
    **kwargs: Any,
) -> UUID:
    return ConstrainedUUID(value, **kwargs)


arg_proc: Dict[Tuple[Hashable, Hashable], Callable[..., Any]] = {
    (str, date): constrained_date,
    (str, time): constrained_time,
    (str, datetime): constrained_datetime,
    (str, dict): constrained_json,
    (bytes, dict): constrained_bytejson,
}


InjectFunc = Callable[[Type[Any], Type[Any]], Optional[Callable[..., Any]]]


def extract_type(bt: Type[Any]) -> Type[Any]:
    """Extract the origin type from complex types."""
    if not isinstance(bt, type):
        return get_equivalent_origin(bt)
    return bt


def func_arg_validator(
    modeltype: Type[Any],
    argtype: Type[Any],
) -> Optional[Callable[..., Any]]:

    modeltype = extract_type(modeltype)
    argtype = extract_type(argtype)
    return arg_proc.get((modeltype, argtype), None)  # type: ignore


validators: List[InjectFunc] = [func_arg_validator]


def get_validator(
    modeltype: Type[Any], argtype: Type[Any]
) -> Optional[Callable[..., Any]]:
    for func in validators:
        validator = func(modeltype, argtype)
        if validator is not None:
            return validator
    return None


def validator_check(
    modeltype: Type[Any],
    basetype: Type[Any],
) -> bool:
    return bool(get_validator(modeltype, basetype))


try:
    from pydantic import (
        AnyUrl,
        BaseModel,
        EmailStr,
        Field,
        HttpUrl,
        IPvAnyAddress,
        StringConstraints,
        TypeAdapter,
    )
    from pydantic import ValidationError as PydanticValidationError

    @lru_cache(maxsize=256)
    def get_string_adapter(
        min_length: Optional[int],
        max_length: Optional[int],
        pattern: Optional[str],
    ) -> TypeAdapter[Any]:
        sc = StringConstraints(
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
        )
        AnnotatedStr = Annotated[str, sc]
        return TypeAdapter(AnnotatedStr)

    def constrained_str(value: str, **kwargs: Any) -> str:
        try:
            adapter = get_string_adapter(
                kwargs.get("min_length"),
                kwargs.get("max_length"),
                kwargs.get("pattern"),
            )
            return adapter.validate_python(value)  # type: ignore
        except PydanticValidationError as e:
            raise ValidationError(str(e))

    @lru_cache(maxsize=256)
    def get_number_adapter(
        gt: Optional[float],
        ge: Optional[float],
        lt: Optional[float],
        le: Optional[float],
        multiple_of: Optional[float],
    ) -> TypeAdapter[Any]:
        fi = Field(
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            multiple_of=multiple_of,
        )
        AnnotatedNum = Annotated[Union[int, float], fi]
        return TypeAdapter(AnnotatedNum)

    def constrained_num(value: Union[int, float], **kwargs: Any) -> Union[int, float]:
        try:
            adapter = get_number_adapter(
                kwargs.get("gt"),
                kwargs.get("ge"),
                kwargs.get("lt"),
                kwargs.get("le"),
                kwargs.get("multiple_of"),
            )
            return adapter.validate_python(value)  # type: ignore
        except PydanticValidationError as e:
            raise ValidationError(str(e))

    @lru_cache(maxsize=256)
    def get_list_adapter(
        min_length: Optional[int],
        max_length: Optional[int],
    ) -> TypeAdapter[Any]:
        fi = Field(min_length=min_length, max_length=max_length)
        AnnotatedList = Annotated[List[Any], fi]
        return TypeAdapter(AnnotatedList)

    def constrained_list(
        value: List[Any],
        **kwargs: Any,
    ) -> List[Any]:
        try:
            adapter = get_list_adapter(
                kwargs.get("min_length"),
                kwargs.get("max_length"),
            )
            return adapter.validate_python(value)  # type: ignore
        except PydanticValidationError as e:
            raise ValidationError(str(e))

    @lru_cache(maxsize=256)
    def get_dict_adapter(
        min_length: Optional[int],
        max_length: Optional[int],
    ) -> TypeAdapter[Any]:
        fi = Field(min_length=min_length, max_length=max_length)
        AnnotatedDict = Annotated[Dict[Any, Any], fi]
        return TypeAdapter(AnnotatedDict)

    def constrained_dict(
        value: Dict[Any, Any],
        **kwargs: Any,
    ) -> Dict[Any, Any]:
        try:
            adapter = get_dict_adapter(
                kwargs.get("min_length"),
                kwargs.get("max_length"),
            )
            return adapter.validate_python(value)  # type: ignore
        except PydanticValidationError as e:
            raise ValidationError(str(e))

    @lru_cache(maxsize=256)
    def get_str_type_adapter(btype: Type[Any]) -> TypeAdapter[Any]:
        return TypeAdapter(btype)

    def constrained_str_type(value: str, btype: Hashable, **kwargs: Any) -> Any:
        try:
            return get_str_type_adapter(btype).validate_python(value)
        except PydanticValidationError as e:
            raise ValidationError(str(e))

    constrained_uuid = partial(constrained_str_type, btype=UUID)
    constrained_email = partial(constrained_str_type, btype=EmailStr)
    constrained_http_url = partial(constrained_str_type, btype=HttpUrl)
    constrained_any_url = partial(constrained_str_type, btype=AnyUrl)
    constrained_ip_any = partial(constrained_str_type, btype=IPvAnyAddress)

    arg_proc.update(
        {
            (str, EmailStr): constrained_email,
            (str, HttpUrl): constrained_http_url,
            (str, AnyUrl): constrained_any_url,
            (str, IPvAnyAddress): constrained_ip_any,
        }
    )

    def get_pydantic_validator(
        modeltype: Type[Any],
        argtype: Type[Any],
    ) -> Optional[Callable[..., Any]]:

        if defensive_issubclass(argtype, BaseModel) and modeltype in (str, bytes):

            def parse_model(json_str: Union[str, bytes]):
                return parse_json_model(
                    json_str,
                    argtype,
                )

            return parse_model
        return None

    def parse_json_model(
        json_str: Union[str, bytes], basetype: Type[BaseModel], **kwargs: Any
    ) -> Any:
        """Parse JSON to Pydantic model."""
        try:
            return basetype.model_validate_json(json_str, **kwargs)
        except PydanticValidationError as e:
            raise ValidationError(str(e))

    validators.append(get_pydantic_validator)

except ImportError:

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

    constrained_list = base_constrained_list
    constrained_dict = base_constrained_dict


arg_proc.update(
    {
        (str, str): constrained_str,
        (int, int): constrained_num,
        (float, float): constrained_num,
        (list, list): constrained_list,
        (dict, dict): constrained_dict,
        (str, UUID): constrained_uuid,
    }
)
