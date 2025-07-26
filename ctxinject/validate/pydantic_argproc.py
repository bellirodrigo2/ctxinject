import copy
from functools import lru_cache, partial
from uuid import UUID

from pydantic import (
    AnyUrl,
    EmailStr,
    Field,
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
    Hashable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from ctxinject.validate.common_validators import common_arg_proc

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
    adapter = get_list_adapter(
        kwargs.get("min_length"),
        kwargs.get("max_length"),
    )
    return adapter.validate_python(value)


# ——— DICT ——————————————————————————————————————————————————————————————


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
    adapter = get_dict_adapter(
        kwargs.get("min_length"),
        kwargs.get("max_length"),
    )
    return adapter.validate_python(value)


@lru_cache(maxsize=256)
def get_str_type_adapter(btype: Type[Any]) -> TypeAdapter[Any]:
    return TypeAdapter(btype)


def constrained_str_type(value: str, btype: Hashable, **kwargs: Any) -> Any:
    return get_str_type_adapter(btype).validate_python(value)


constrained_uuid = partial(constrained_str_type, btype=UUID)
constrained_email = partial(constrained_str_type, btype=EmailStr)
constrained_http_url = partial(constrained_str_type, btype=HttpUrl)
constrained_any_url = partial(constrained_str_type, btype=AnyUrl)
constrained_ip_any = partial(constrained_str_type, btype=IPvAnyAddress)
# ——— FINAL MAPPING————————————————————————————————————————————————

copied_argproc = copy.deepcopy(common_arg_proc)
arg_proc_pydantic: Dict[Tuple[Hashable, Hashable], Callable[..., Any]] = {
    (str, str): constrained_str,
    (int, int): constrained_num,
    (float, float): constrained_num,
    (list, list): constrained_list,
    (dict, dict): constrained_dict,
    (str, UUID): constrained_uuid,
    (str, EmailStr): constrained_email,
    (str, HttpUrl): constrained_http_url,
    (str, AnyUrl): constrained_any_url,
    (str, IPvAnyAddress): constrained_ip_any,
}
arg_proc = {**copied_argproc, **arg_proc_pydantic}
