"""
ctxinject - Advanced dependency injection framework with MyPy support.

This package provides a powerful and type-safe dependency injection system
with the following features:

- Type-safe dependency injection with generic support
- Async/await support with optimal performance
- Custom Injectable subclasses for domain-specific injection
- Validation and type conversion
- MyPy plugin for static type checking
- Model field injection from class instances
- Function dependency injection with recursive resolution

Key Components:
- Injectable: Base class for all injectable dependencies
- ArgsInjectable: Standard injectable for function arguments
- DependsInject: Injectable for function dependencies
- ModelFieldInject: Injectable for extracting model field values
- inject_args: Main injection function

Examples:
    Basic usage:
    ```python
    from ctxinject import inject_args, ArgsInjectable, DependsInject

    def process(name: str = ArgsInjectable(...), count: int = ArgsInjectable(42)):
        return f"{name}: {count}"

    async def get_service() -> str:
        return "database"

    def handle(service: str = DependsInject(get_service)):
        return f"Using {service}"

    context = {"name": "test"}
    injected = await inject_args(process, context)
    result = injected()  # "test: 42"
    ```

    With custom injectables:
    ```python
    class FromRequest(Injectable[str]):
        def __init__(self, field: str):
            super().__init__(default=...)
            self.field = field

    def handler(method: str = FromRequest("method")):
        return f"Method: {method}"
    ```
"""

# Core injection functionality
from .inject import (
    UnresolvedInjectableError,
    get_mapped_ctx,
    inject_args,
    resolve_mapped_ctx,
)

# Injectable model classes
from .model import (
    ArgsInjectable,
    CallableInjectable,
    DependsInject,
    Injectable,
    ModelFieldInject,
)

# Signature checking utilities
from .sigcheck import func_signature_check

# Validation utilities
from .validation import get_validator

__all__ = [
    # Main injection functions
    "inject_args",
    "get_mapped_ctx",
    "resolve_mapped_ctx",
    # Injectable classes
    "Injectable",
    "ArgsInjectable",
    "CallableInjectable",
    "DependsInject",
    "ModelFieldInject",
    # Utilities
    "get_validator",
    "func_signature_check",
    # Exceptions
    "UnresolvedInjectableError",
    # Plugin availability flag
]
