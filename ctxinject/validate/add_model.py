from typemapping import VarTypeInfo
from typing_extensions import Any, Callable, Dict, Hashable, Optional, Protocol, Tuple


class AddModel(Protocol):
    """Protocol for custom model processors."""

    def __call__(
        self,
        arg: VarTypeInfo,
        arg_proc: Dict[Tuple[Hashable, Hashable], Callable[..., Any]],
    ) -> Optional[Callable[..., Any]]:
        """
        Attempt to add a validator for the argument.

        Args:
            arg: Function argument information
            arg_proc: Dictionary of argument processors

        Returns:
            Validator function if successfully processed, None otherwise
        """
        ...  # pragma: no cover
