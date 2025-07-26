from pydantic import BaseModel
from typemapping import VarTypeInfo, get_field_type
from typing_extensions import (
    Any,
    Callable,
    Dict,
    Hashable,
    Optional,
    Tuple,
    Type,
    Union,
)

from ctxinject.model import ModelFieldInject


def pydantic_add_model(
    arg: VarTypeInfo,
    arg_proc: Dict[Tuple[Hashable, Hashable], Callable[..., Any]],
) -> Optional[Callable[..., Any]]:
    """Pydantic JSON parsing processor."""
    from pydantic import BaseModel

    instance = arg.getinstance(ModelFieldInject)
    if instance is not None and arg.istype(BaseModel):
        fieldname = instance.field or arg.name
        modeltype = get_field_type(instance.model, fieldname)

        if modeltype in (str, bytes):
            key = (modeltype, arg.basetype)
            if key not in arg_proc:
                arg_proc[key] = parse_json_model
            return parse_json_model
    return None


def parse_json_model(
    json_str: Union[str, bytes], basetype: Type[BaseModel], **kwargs: Any
) -> Any:
    """Parse JSON to Pydantic model."""
    return basetype.model_validate_json(json_str)
