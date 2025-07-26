"""
Automatic validation and type conversion for dependency injection.
"""

__all__ = ["inject_validation", "arg_proc"]

from typing import Any, Callable, Dict, Hashable, List, Optional, Tuple

from ctxinject.validate.add_model import AddModel
from ctxinject.validate.collections_add_model import collections_add_model

# Build default processors list
try:
    from ctxinject.validate.pydantic_add_model import pydantic_add_model

    default_add_models = [pydantic_add_model]
    default_add_models.append(pydantic_add_model)
except ImportError:
    default_add_models = []

default_add_models.append(collections_add_model)

# Import arg_proc (try Pydantic first, fallback to std)
try:
    from ctxinject.validate.pydantic_argproc import arg_proc
except ImportError:
    from ctxinject.validate.std_argproc import arg_proc

# Main inject_validation function
from ctxinject.validate.inject_validation import extract_type  # noqa: E402
from ctxinject.validate.inject_validation import (  # noqa: E402
    inject_validation as core_inject_validation,
)


def inject_validation(
    func: Callable[..., Any],
    argproc: Dict[Tuple[Hashable, Hashable], Callable[..., Any]],
    extracttype: Callable[[Hashable], Hashable] = extract_type,
    add_model: Optional[List[AddModel]] = None,
) -> List[str]:
    """
    Automatic validation setup with default processors.

    Default processors: [collections_add_model, pydantic_add_model (if available)]
    """
    processors = add_model or []
    processors.extend(default_add_models)
    processors = list(set(processors))
    return core_inject_validation(func, argproc, extracttype, processors)
