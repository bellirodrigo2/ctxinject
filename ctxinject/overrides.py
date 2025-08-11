"""
Dependency override management for ctxinject.

This module provides a clean, decoupled approach to dependency overrides
inspired by FastAPI's dependency system but adapted for ctxinject's architecture.
"""

from collections import ChainMap
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional


class Provider:
    """
    Dependency override provider for managing dependency substitutions.

    This class provides a clean interface for overriding dependencies
    in ctxinject, useful for testing and different deployment environments.

    Examples:
        Basic override:
        ```python
        provider = Provider()

        def real_database() -> Database:
            return ProductionDatabase()

        def test_database() -> Database:
            return TestDatabase()

        provider.override(real_database, test_database)
        ```

        Context manager for temporary overrides:
        ```python
        with provider.scope(real_database, test_database):
            # Inside this scope, real_database is replaced with test_database
            injected = await inject_args(my_function, {}, provider=provider)
        # Outside scope, original dependency is restored
        ```

        Multiple overrides:
        ```python
        provider.override_many({
            real_database: test_database,
            real_cache: test_cache,
            real_logger: test_logger,
        })
        ```
    """

    def __init__(self) -> None:
        """Initialize a new dependency provider."""
        self.dependency_overrides: Dict[Callable[..., Any], Callable[..., Any]] = {}

    def clear(self) -> None:
        """Clear all dependency overrides."""
        self.dependency_overrides.clear()

    def override(
        self,
        original: Callable[..., Any],
        replacement: Callable[..., Any],
    ) -> None:
        """
        Override a dependency function with a replacement.

        Args:
            original: The original dependency function to replace
            replacement: The replacement dependency function

        Example:
            ```python
            def prod_db() -> Database:
                return ProductionDatabase()

            def test_db() -> Database:
                return TestDatabase()

            provider.override(prod_db, test_db)
            ```
        """
        self.dependency_overrides[original] = replacement

    def override_many(
        self, overrides: Dict[Callable[..., Any], Callable[..., Any]]
    ) -> None:
        """
        Override multiple dependencies at once.

        Args:
            overrides: Dictionary mapping original functions to replacements

        Example:
            ```python
            provider.override_many({
                prod_db: test_db,
                prod_cache: test_cache,
                prod_logger: test_logger,
            })
            ```
        """
        self.dependency_overrides.update(overrides)

    def remove_override(self, original: Callable[..., Any]) -> bool:
        """
        Remove a specific override.

        Args:
            original: The original function to stop overriding

        Returns:
            True if override was removed, False if it didn't exist
        """
        return self.dependency_overrides.pop(original, None) is not None

    @contextmanager
    def scope(
        self,
        original: Callable[..., Any],
        replacement: Callable[..., Any],
    ) -> Iterator[None]:
        """
        Temporarily override a dependency within a context manager.

        Args:
            original: The original dependency function
            replacement: The replacement dependency function

        Example:
            ```python
            with provider.scope(prod_service, test_service):
                # prod_service is replaced with test_service here
                result = await inject_args(my_func, {}, provider=provider)
            # Original dependency restored here
            ```
        """
        self.dependency_overrides[original] = replacement
        try:
            yield
        finally:
            self.dependency_overrides.pop(original, None)

    @contextmanager
    def scope_many(
        self, overrides: Dict[Callable[..., Any], Callable[..., Any]]
    ) -> Iterator[None]:
        """
        Temporarily override multiple dependencies within a context manager.

        Args:
            overrides: Dictionary mapping original functions to replacements

        Example:
            ```python
            overrides = {
                prod_db: test_db,
                prod_cache: test_cache,
            }
            with provider.scope_many(overrides):
                # All overrides active here
                result = await inject_args(my_func, {}, provider=provider)
            # All overrides restored here
            ```
        """
        # Store original state to restore later
        original_keys = set(overrides.keys())
        original_values = {k: self.dependency_overrides.get(k) for k in original_keys}

        # Apply overrides
        self.dependency_overrides.update(overrides)

        try:
            yield
        finally:
            # Restore original state
            for key in original_keys:
                if original_values[key] is None:
                    self.dependency_overrides.pop(key, None)
                else:
                    self.dependency_overrides[key] = original_values[key]

    def get_override(
        self, original: Callable[..., Any]
    ) -> Optional[Callable[..., Any]]:
        """
        Get the override for a specific dependency, if any.

        Args:
            original: The original dependency function

        Returns:
            The replacement function, or None if no override exists
        """
        return self.dependency_overrides.get(original)

    def has_override(self, original: Callable[..., Any]) -> bool:
        """
        Check if a dependency has an override.

        Args:
            original: The original dependency function

        Returns:
            True if an override exists, False otherwise
        """
        return original in self.dependency_overrides

    def copy(self) -> "Provider":
        """
        Create a copy of this provider with the same overrides.

        Returns:
            A new Provider instance with copied overrides
        """
        new_provider = Provider()
        new_provider.dependency_overrides = self.dependency_overrides.copy()
        return new_provider

    def merge(self, other: "Provider") -> "Provider":
        """
        Merge this provider with another, returning a new provider.

        Args:
            other: Another provider to merge with

        Returns:
            A new Provider with overrides from both providers.
            Other provider's overrides take precedence for conflicts.
        """
        new_provider = Provider()
        new_provider.dependency_overrides = ChainMap(
            other.dependency_overrides, self.dependency_overrides
        )
        return new_provider

    def __len__(self) -> int:
        """Return the number of active overrides."""
        return len(self.dependency_overrides)

    def __bool__(self) -> bool:
        """Return True if there are any overrides."""
        return bool(self.dependency_overrides)

    def __contains__(self, dependency: Callable[..., Any]) -> bool:
        """Check if a dependency is overridden."""
        return dependency in self.dependency_overrides

    def __repr__(self) -> str:
        return f"Provider({len(self.dependency_overrides)} overrides)"


class GlobalProvider:
    """
    Global dependency provider for application-wide overrides.

    This provides a singleton-like interface for managing global
    dependency overrides while still allowing local providers.

    Example:
        ```python
        # Set up global test overrides
        global_provider.override(prod_db, test_db)

        # All inject_args calls will use global overrides unless
        # a local provider is specified
        injected = await inject_args(my_func, {})  # Uses global overrides

        # Local provider takes precedence
        local_provider = Provider()
        injected = await inject_args(my_func, {}, provider=local_provider)
        ```
    """

    def __init__(self) -> None:
        self._provider = Provider()

    def __getattr__(self, name: str) -> Any:
        """Delegate all attribute access to the internal provider."""
        return getattr(self._provider, name)

    def reset(self) -> None:
        """Reset the global provider to a clean state."""
        self._provider = Provider()


# Global instance for application-wide overrides
global_provider = GlobalProvider()


def resolve_overrides(
    local_provider: Optional[Provider] = None, use_global: bool = True
) -> Dict[Callable[..., Any], Callable[..., Any]]:
    """
    Resolve the final override mapping from global and local providers.

    Args:
        local_provider: Optional local provider
        use_global: Whether to include global overrides

    Returns:
        Combined override dictionary with local overrides taking precedence

    Example:
        ```python
        # In inject_args implementation:
        overrides = resolve_overrides(provider, use_global=True)
        dependency_func = overrides.get(original_func, original_func)
        ```
    """
    if not use_global and not local_provider:
        return {}

    if not use_global:
        return local_provider.dependency_overrides if local_provider else {}

    if not local_provider:
        return global_provider.dependency_overrides  # type: ignore

    # Merge with local taking precedence
    return dict(
        ChainMap(
            local_provider.dependency_overrides, global_provider.dependency_overrides
        )
    )
