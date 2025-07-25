from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Type, Union

from pydantic import BaseModel
from typemapping import VarTypeInfo, get_field_type

from ctxinject.model import ModelFieldInject


def add_model(
    arg: VarTypeInfo,
    from_type: Iterable[Type[Any]],
    arg_proc: Dict[Tuple[Type[Any], Type[Any]], Callable[..., Any]],
) -> Optional[Callable[..., Any]]:
    """
    Add Pydantic model validation for ModelFieldInject parameters.

    This function creates automatic JSON parsing validators for Pydantic models
    when the source field is a string or bytes type. It's used internally by
    inject_validation() to handle Pydantic model conversions.

    Args:
        arg: The function argument info to process
        from_type: Iterable of source types to convert from (typically str, bytes)
        arg_proc: Dictionary to add the validator to

    Returns:
        The parsing function if a Pydantic model conversion was set up, None otherwise

    Note:
        This is an internal function used by inject_validation(). Users typically
        don't need to call this directly.
    """
    model = get_model(arg, from_type)
    if model is None:
        return None
    if model not in arg_proc:
        arg_proc[model] = parse_json_model
    return parse_json_model


def get_model(
    arg: VarTypeInfo, from_type: Iterable[Type[Any]]
) -> Optional[Tuple[Type[Any], Type[BaseModel]]]:
    """
    Check if an argument represents a Pydantic model conversion scenario.

    This function determines if a ModelFieldInject parameter can be automatically
    converted from a source type (like str) to a Pydantic model.

    Args:
        arg: The function argument info to check
        from_type: Iterable of source types to convert from

    Returns:
        Tuple of (source_type, target_model_type) if conversion is possible, None otherwise

    Note:
        Internal function used by add_model(). Users don't typically call this directly.
    """
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
    """
    Parse JSON string or bytes into a Pydantic model instance.

    This function is used as a validator to automatically convert JSON strings
    from model fields into Pydantic model instances. It's automatically assigned
    by inject_validation() when appropriate.

    Args:
        json_str: JSON string or bytes to parse
        basetype: The Pydantic model class to parse into

    Returns:
        Instance of the Pydantic model

    Raises:
        ValidationError: If the JSON is invalid or doesn't match the model schema

    Example:
        This function is typically used automatically by inject_validation():
        ```python
        from pydantic import BaseModel

        class User(BaseModel):
            name: str
            age: int

        class Config:
            user_json: str

            def __init__(self):
                self.user_json = '{"name": "Alice", "age": 30}'

        def process_user(
            user: Annotated[User, ModelFieldInject(Config, "user_json")]
        ):
            return f"Hello {user.name}, age {user.age}"

        # inject_validation() automatically sets up parse_json_model
        # to convert the JSON string to a User instance
        inject_validation(process_user)

        config = Config()
        context = {Config: config}
        injected = await inject_args(process_user, context)
        result = injected()  # JSON automatically parsed to User model
        ```

    Note:
        - Uses Pydantic's model_validate_json() for robust JSON parsing
        - Handles both str and bytes input
        - Provides detailed validation errors if JSON doesn't match schema
        - Automatically assigned by inject_validation(), rarely called directly
    """
    return basetype.model_validate_json(json_str)
