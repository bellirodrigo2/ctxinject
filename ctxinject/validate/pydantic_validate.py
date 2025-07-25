from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Type, Union

from pydantic import BaseModel
from typemapping import VarTypeInfo, get_field_type

from ctxinject.model import ModelFieldInject


def add_model(
    arg: VarTypeInfo,
    from_type: Iterable[Type[Any]],
    arg_proc: Dict[Tuple[Type[Any], Type[Any]], Callable[..., Any]],
) -> Optional[Callable[..., Any]]:
    model = get_model(arg, from_type)
    if model is not None and model not in arg_proc:
        arg_proc[model] = parse_json_model
        return parse_json_model
    return None


def get_model(
    arg: VarTypeInfo, from_type: Iterable[Type[Any]]
) -> Optional[Tuple[Type[Any], Type[BaseModel]]]:
    instance = arg.getinstance(ModelFieldInject)
    if instance is not None and arg.istype(BaseModel):
        fieldname = instance.field or arg.name
        modeltype = get_field_type(instance.model, fieldname)
        if modeltype in from_type:
            return (modeltype, arg.basetype)
    return None


def parse_json_model(
    json_str: Union[str, bytes], basetype: Type[BaseModel]
) -> BaseModel:
    return basetype.model_validate_json(json_str)
