from typing import Any, Callable, Dict, List, Tuple, Type, TypeVar, get_origin

from typemapping import get_field_type, get_func_args

from ctxinject.model import ModelFieldInject

T = TypeVar("T")

try:
    from ctxinject.validate.pydantic_argproc import arg_proc
    from ctxinject.validate.pydantic_validate import add_model

    PYDANTIC_VALIDATOR = True
except ImportError:  # pragma: no cover
    from ctxinject.validate.std_argproc import arg_proc

    PYDANTIC_VALIDATOR = False


def extract_type(bt: Type[Any]) -> Type[Any]:
    if not isinstance(bt, type):
        return get_origin(bt)
    return bt


def inject_validation(
    func: Callable[..., Any],
    argproc: Dict[Tuple[type[Any], Type[Any]], Callable[..., Any]] = arg_proc,
    extracttype: Callable[[type[T]], Type[T]] = extract_type,
) -> List[str]:

    args = get_func_args(func)
    errors: List[str] = []
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
            if validator is None and PYDANTIC_VALIDATOR:
                validator = add_model(arg, (str, bytes), arg_proc)
            if validator is not None:
                instance._validator = validator
        except Exception as e:
            errors.append(f"Error processing {arg.name}: {e}")
    return errors
