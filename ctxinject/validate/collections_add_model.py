from collections.abc import Iterable, Mapping, MutableMapping, Sequence

from typemapping import VarTypeInfo, get_field_type
from typing_extensions import (
    Any,
    Callable,
    Dict,
    Hashable,
    List,
    Optional,
    Tuple,
    Type,
    get_args,
    get_origin,
)

from ctxinject.model import ModelFieldInject


def collections_add_model(
    arg: VarTypeInfo,
    arg_proc: Dict[Tuple[Hashable, Hashable], Callable[..., Any]],
) -> Optional[Callable[..., Any]]:
    """Collections processor for compatible collection types."""
    model = get_collections_model(arg)
    if model is None:
        return None
    if model not in arg_proc:
        arg1, arg2 = model
        if not arg1 == arg2:
            arg_proc[model] = None
    return None


def get_collections_model(arg: VarTypeInfo) -> Optional[Tuple[Hashable, Hashable]]:
    """Check if argument represents a valid collections conversion."""
    instance = arg.getinstance(ModelFieldInject)
    if instance is None:
        return None

    fieldname = instance.field or arg.name
    modeltype = get_field_type(instance.model, fieldname)
    if modeltype is None:
        return None

    modelorigin = get_origin(modeltype)
    if modelorigin is None:
        return None
    # Compatible collection groups
    mapping_types: Iterable[Type[Any]] = {Mapping, MutableMapping, Dict, dict}
    sequence_types: Iterable[Type[Any]] = {List, list, Sequence, Iterable}

    for group in [mapping_types, sequence_types]:
        if arg.origin in group and modelorigin in group:
            if arg.args == get_args(modeltype):
                return (modeltype, arg.basetype)

    return None
