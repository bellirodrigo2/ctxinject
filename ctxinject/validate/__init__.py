"""
Automatic validation and type conversion for dependency injection.

This module provides automatic type conversion and validation capabilities
for ModelFieldInject parameters, enabling seamless conversion between
different types (e.g., string configuration values to integers, UUIDs, etc.).

Key Features:
- Automatic type conversion based on type annotations
- Pydantic model validation from JSON strings
- Extensible converter system
- Zero-configuration setup for common conversions

Main APIs:
- inject_validation(): Set up automatic validators for a function
- arg_proc: Dictionary of available type converters

Examples:
    Basic usage:
    ```python
    from ctxinject.validate import inject_validation

    # Define function with ModelFieldInject parameters
    def my_function(
        port: Annotated[int, ModelFieldInject(Config, "port_str")]
    ):
        return port * 2

    # Set up automatic string-to-int conversion
    errors = inject_validation(my_function)
    if not errors:
        print("Validation configured successfully!")
    ```

    With Pydantic models:
    ```python
    from pydantic import BaseModel
    from ctxinject.validate import inject_validation

    class UserModel(BaseModel):
        name: str
        age: int

    def process_user(
        user: Annotated[UserModel, ModelFieldInject(Config, "user_json")]
    ):
        return user.name

    # Automatically sets up JSON parsing
    inject_validation(process_user)
    ```
"""

__all__ = ["inject_validation", "arg_proc"]
from ctxinject.validate.inject_validation import arg_proc, inject_validation
