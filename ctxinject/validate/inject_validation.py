from typemapping import get_field_type, get_func_args
from typing_extensions import (
    Any,
    Callable,
    Dict,
    Hashable,
    List,
    Optional,
    Tuple,
    get_origin,
)

from ctxinject.model import ModelFieldInject
from ctxinject.validate.add_model import AddModel


def extract_type(bt: Hashable) -> Hashable:
    """Extract the origin type from complex types."""
    if not isinstance(bt, type):
        return get_origin(bt)
    return bt


def inject_validation(
    func: Callable[..., Any],
    argproc: Dict[Tuple[Hashable, Hashable], Callable[..., Any]],
    extracttype: Callable[[Hashable], Hashable] = extract_type,
    add_model: Optional[List[AddModel]] = None,
) -> List[str]:
    """Core inject_validation with list of processors."""
    args = get_func_args(func)
    errors: List[str] = []

    processors = add_model or []
    for arg in args:
        instance = arg.getinstance(ModelFieldInject)
        if instance is None:
            continue

        if instance._validator is not None:
            continue

        fieldname = instance.field or arg.name
        modeltype = get_field_type(instance.model, fieldname)
        argtype = arg.basetype

        if modeltype is None:
            errors.append(
                f"At arg: {arg.name}, Cannot determine field type: {fieldname}, at model: {instance.model.__name__}"
            )
            continue
        if argtype is None:
            errors.append(f"No type annotation for {arg.name}")
            continue
        try:
            modeltype = extracttype(modeltype)
            argtype = extracttype(argtype)
            validator = argproc.get((modeltype, argtype), None)

            # Try processors in order until one works
            if validator is None:
                for processor in processors:
                    validator = processor(arg, argproc)
                    if validator is not None:
                        break

            if validator is not None:
                instance._validator = validator

        except Exception as e:
            errors.append(f"Error processing {arg.name}: {e}")
    return errors
