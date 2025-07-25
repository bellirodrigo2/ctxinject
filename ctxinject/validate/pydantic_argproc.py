from datetime import date, datetime, time
from functools import lru_cache, partial
from uuid import UUID

from pydantic import (
    AnyUrl,
    DirectoryPath,
    EmailStr,
    Field,
    FilePath,
    HttpUrl,
    IPvAnyAddress,
    StringConstraints,
    TypeAdapter,
)
from typing_extensions import (
    Annotated,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from ctxinject.validate.common_validators import (
    constrained_bytejson,
    constrained_date,
    constrained_datetime,
    constrained_json,
    constrained_time,
)

# ——— STR ——————————————————————————————————————————————————————————————


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
    adapter = get_string_adapter(
        kwargs.get("min_length"),
        kwargs.get("max_length"),
        kwargs.get("pattern"),
    )
    return adapter.validate_python(value)


# ——— NUM ——————————————————————————————————————————————————————————————


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
    adapter = get_number_adapter(
        kwargs.get("gt"),
        kwargs.get("ge"),
        kwargs.get("lt"),
        kwargs.get("le"),
        kwargs.get("multiple_of"),
    )
    return adapter.validate_python(value)


# ——— LIST ——————————————————————————————————————————————————————————————


@lru_cache(maxsize=256)
def get_list_adapter(
    item_type: Type[Any],
    min_length: Optional[int],
    max_length: Optional[int],
) -> TypeAdapter[Any]:
    fi = Field(min_length=min_length, max_length=max_length)
    AnnotatedList = Annotated[List[item_type], fi]
    return TypeAdapter(AnnotatedList)


def constrained_list(
    value: List[Any],
    **kwargs: Any,
) -> List[Any]:
    adapter = get_list_adapter(
        kwargs.get("item_type", Any),
        kwargs.get("min_length"),
        kwargs.get("max_length"),
    )
    return adapter.validate_python(value)


# ——— DICT ——————————————————————————————————————————————————————————————


@lru_cache(maxsize=256)
def get_dict_adapter(
    key_type: Type[Any],
    value_type: Type[Any],
    min_length: Optional[int],
    max_length: Optional[int],
) -> TypeAdapter[Any]:
    fi = Field(min_length=min_length, max_length=max_length)
    AnnotatedDict = Annotated[Dict[key_type, value_type], fi]
    return TypeAdapter(AnnotatedDict)


def constrained_dict(
    value: Dict[Any, Any],
    **kwargs: Any,
) -> Dict[Any, Any]:
    adapter = get_dict_adapter(
        kwargs.get("key_type", Any),
        kwargs.get("value_type", Any),
        kwargs.get("min_length"),
        kwargs.get("max_length"),
    )
    return adapter.validate_python(value)


@lru_cache(maxsize=256)
def get_str_type_adapter(btype: Type[Any]) -> TypeAdapter[UUID]:
    return TypeAdapter(btype)


def constrained_str_type(value: str, btype: Type[Any], **kwargs: Any) -> UUID:
    return get_str_type_adapter(btype).validate_python(value)


constrained_uuid = partial(constrained_str_type, btype=UUID)
constrained_email = partial(constrained_str_type, btype=EmailStr)
constrained_http_url = partial(constrained_str_type, btype=HttpUrl)
constrained_any_url = partial(constrained_str_type, btype=AnyUrl)
constrained_ip_any = partial(constrained_str_type, btype=IPvAnyAddress)
constrained_directory_path = partial(constrained_str_type, btype=DirectoryPath)
constrained_file_path = partial(constrained_str_type, btype=FilePath)
# ——— FINAL MAPPING————————————————————————————————————————————————

arg_proc: Dict[Tuple[type, Type[Any]], Callable[..., Any]] = {
    (str, str): constrained_str,
    (int, int): constrained_num,
    (float, float): constrained_num,
    (list, list): constrained_list,
    (dict, dict): constrained_dict,
    (str, date): constrained_date,
    (str, time): constrained_time,
    (str, datetime): constrained_datetime,
    (str, dict): constrained_json,
    (bytes, dict): constrained_bytejson,
    (str, UUID): constrained_uuid,
    (str, EmailStr): constrained_email,
    (str, HttpUrl): constrained_http_url,
    (str, AnyUrl): constrained_any_url,
    (str, IPvAnyAddress): constrained_ip_any,
    (str, DirectoryPath): constrained_directory_path,
    (str, FilePath): constrained_file_path,
}
