
from typing import Any, Optional


class ValidationError(Exception):
    pass

class InvalidModelFieldType(Exception):
    """Raised when an model field injectable has the wrong type."""


class InvalidInjectableDefinition(Exception):
    """Raised when an injectable is incorrectly defined (e.g., wrong model type)."""


class UnresolvedInjectableError(Exception):
    """Raised when a dependency cannot be resolved in the injection context."""
    ...


class UnInjectableError(Exception):
    """Raised when a function argument cannot be injected."""

    def __init__(self, argname: str, argtype: Optional[type[Any]]):
        super().__init__(
            f"Argument '{argname}' of type '{argtype}' cannot be injected."
        )
        self.argname = argname
        self.argtype = argtype
