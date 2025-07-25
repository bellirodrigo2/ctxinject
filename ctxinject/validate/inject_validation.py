from typing import Any, Callable, Dict, Hashable, List, Tuple, TypeVar, get_origin

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


def extract_type(bt: Hashable) -> Hashable:
    """Extract the origin type from complex types."""
    if not isinstance(bt, type):
        return get_origin(bt)
    return bt


def inject_validation(
    func: Callable[..., Any],
    argproc: Dict[Tuple[Hashable, Hashable], Callable[..., Any]] = arg_proc,
    extracttype: Callable[[Hashable], Hashable] = extract_type,
) -> List[str]:
    """
    Automatically inject type conversion validators for ModelFieldInject parameters.

    This function analyzes a function's signature and automatically adds type conversion
    validators to ModelFieldInject parameters based on type mismatches between the
    model field type and the function parameter type.

    The validation system supports:
    - Automatic type conversion between compatible types (e.g., str to int, str to UUID)
    - Pydantic model validation from JSON strings
    - Custom validator processors through argproc mapping
    - Standard library type conversions

    Args:
        func: The function to analyze and inject validators for
        argproc: Dictionary mapping (source_type, target_type) to converter functions
        extracttype: Function to extract origin type from complex types

    Returns:
        List of error messages for parameters that couldn't be processed.
        Empty list means all ModelFieldInject parameters were successfully configured.

    Examples:
        Basic type conversion setup:
        ```python
        from typing_extensions import Annotated
        from ctxinject.model import ModelFieldInject
        from ctxinject.validate import inject_validation

        class DatabaseConfig:
            connection_string: str  # String in config
            port: str              # String in config
            timeout: str           # String in config

            def __init__(self):
                self.connection_string = "postgresql://localhost:5432/mydb"
                self.port = "5432"
                self.timeout = "30"

        def connect_database(
            # Automatic conversion from str to int
            port: Annotated[int, ModelFieldInject(DatabaseConfig, "port")],

            # Automatic conversion from str to int
            timeout: Annotated[int, ModelFieldInject(DatabaseConfig, "timeout")],

            # No conversion needed (str to str)
            conn_str: Annotated[str, ModelFieldInject(DatabaseConfig, "connection_string")]
        ):
            return f"Connect to port {port} with timeout {timeout}"

        # Setup automatic validation
        errors = inject_validation(connect_database)
        if errors:
            print(f"Validation setup errors: {errors}")
        else:
            print("Automatic type conversion configured!")

        # Now inject_args will automatically convert string values to integers
        config = DatabaseConfig()
        context = {DatabaseConfig: config}
        injected = await inject_args(connect_database, context)
        result = injected()  # port="5432" -> 5432, timeout="30" -> 30
        ```

        Advanced usage with custom converters:
        ```python
        from uuid import UUID
        from datetime import datetime

        class UserConfig:
            user_id_str: str           # "123e4567-e89b-12d3-a456-426614174000"
            created_at_str: str        # "2023-12-25T10:30:00"
            is_active_str: str         # "true" or "false"

        def process_user(
            user_id: Annotated[UUID, ModelFieldInject(UserConfig, "user_id_str")],
            created_at: Annotated[datetime, ModelFieldInject(UserConfig, "created_at_str")],
            is_active: Annotated[bool, ModelFieldInject(UserConfig, "is_active_str")]
        ):
            return {"id": user_id, "created": created_at, "active": is_active}

        # This will automatically set up converters for:
        # str -> UUID, str -> datetime, str -> bool
        errors = inject_validation(process_user)
        print(f"Setup errors: {errors}")  # Should be empty if converters exist
        ```

        With Pydantic models (automatic JSON parsing):
        ```python
        from pydantic import BaseModel

        class UserModel(BaseModel):
            name: str
            age: int
            email: str

        class ApiConfig:
            user_data_json: str  # JSON string from config file

            def __init__(self):
                self.user_data_json = '{"name": "Alice", "age": 30, "email": "alice@example.com"}'

        def process_user_data(
            # Automatic JSON parsing to Pydantic model
            user: Annotated[UserModel, ModelFieldInject(ApiConfig, "user_data_json")]
        ):
            return f"Processing user {user.name}, age {user.age}"

        # If Pydantic is available, this sets up automatic JSON parsing
        errors = inject_validation(process_user_data)

        config = ApiConfig()
        context = {ApiConfig: config}
        injected = await inject_args(process_user_data, context)
        result = injected()  # JSON string automatically parsed to UserModel
        ```

        Error handling:
        ```python
        class InvalidConfig:
            # Missing type annotation
            some_field = "value"

        def bad_function(
            # This will cause an error - can't determine field type
            param: Annotated[int, ModelFieldInject(InvalidConfig, "some_field")]
        ):
            return param

        errors = inject_validation(bad_function)
        print(errors)  # ['At arg: param, Cannot determine field type: some_field, at model: InvalidConfig']
        ```

    Note:
        - Only processes ModelFieldInject parameters that don't already have validators
        - Requires model fields to have proper type annotations
        - Uses Pydantic validation if available, falls back to standard converters
        - Type conversion is based on the argproc mapping (extensible)
        - Automatically handles common conversions: str->int, str->float, str->bool, etc.

    Common Type Conversions Supported:
        - str -> int, float, bool, UUID, datetime
        - bytes -> str (decode)
        - JSON strings -> Pydantic models (if Pydantic available)
        - Custom conversions via argproc parameter

    Performance:
        - Only analyzes function once during setup
        - Validation happens during injection, not function definition
        - Minimal runtime overhead after setup

    Integration:
        Call inject_validation() once after defining your functions but before
        using inject_args(). This sets up the automatic type conversion validators.
    """
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
                validator = add_model(arg, (str, bytes), argproc)  # type: ignore
            if validator is not None:
                instance._validator = validator
        except Exception as e:
            errors.append(f"Error processing {arg.name}: {e}")
    return errors
