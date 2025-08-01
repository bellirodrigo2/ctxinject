from typing import Any, Callable, Optional, Protocol, Type, runtime_checkable


@runtime_checkable
class Iinjectable(Protocol):
    """Protocol defining the interface for injectable dependencies."""

    @property
    def default(self) -> Any:
        """Get the default value for this injectable."""
        ...  # pragma: no cover

    def validate(self, instance: Any, basetype: Type[Any]) -> Any:
        """Validate and potentially transform an instance."""
        ...  # pragma: no cover


class Injectable(Iinjectable):
    """Base injectable dependency with optional validation."""

    def __init__(
        self,
        default: Any = ...,
        validator: Optional[Callable[..., Any]] = None,
        **meta: Any,
    ):
        """
        Initialize an injectable dependency.

        Args:
            default: Default value (use ... for required dependencies)
            validator: Optional validation function
            **meta: Additional metadata passed to validator
        """
        self._default = default
        self._validator = validator
        self.meta = meta

    @property
    def default(self) -> Any:
        """Get the default value for this injectable."""
        return self._default

    @property
    def has_validate(self) -> bool:
        """Check if this injectable has a validator function."""
        return self._validator is not None

    def validate(self, instance: Any, basetype: Type[Any]) -> Any:
        """
        Validate an instance using the configured validator.

        Args:
            instance: The value to validate
            basetype: The expected type

        Returns:
            The validated (and possibly transformed) value
        """
        self.meta["basetype"] = basetype
        if self.has_validate:  # pragma: no cover
            return self._validator(instance, **self.meta)  # type: ignore


class ArgsInjectable(Injectable):
    """
    Injectable for function arguments with optional default values and validation.

    This is the primary injectable annotation for function parameters. It supports:
    - Default values (including required parameters with ...)
    - Custom validation functions
    - Metadata for advanced use cases

    Examples:
        Basic usage with default:
        ```python
        def func(count: int = ArgsInjectable(42)):
            return count * 2
        ```

        Required parameter (no default):
        ```python
        def func(name: str = ArgsInjectable(...)):
            return f"Hello {name}"
        ```

        With validation:
        ```python
        def validate_positive(value: int, **kwargs) -> int:
            if value <= 0:
                raise ValueError("Must be positive")
            return value

        def func(count: int = ArgsInjectable(1, validate_positive)):
            return count
        ```

        Using Annotated syntax (recommended):
        ```python
        from typing_extensions import Annotated

        def func(
            name: Annotated[str, ArgsInjectable(...)],
            count: Annotated[int, ArgsInjectable(42)]
        ):
            return f"{name}: {count}"
        ```
    """

    pass


class ModelFieldInject(ArgsInjectable):
    """
    Injectable that extracts values from model instance fields or methods.

    This injectable allows you to inject values from attributes or method calls
    of model instances that are available in the injection context.

    The injection will:
    1. Look for an instance of the specified model type in the context
    2. Extract the field value or call the method on that instance
    3. Inject the result into the function parameter

    Args:
        model: The model class type to extract from
        field: Optional field name (defaults to parameter name)
        validator: Optional validation function
        **meta: Additional metadata

    Examples:
        Basic field extraction:
        ```python
        class Config:
            database_url: str = "sqlite:///app.db"
            api_key: str = "secret"

        def connect(
            url: str = ModelFieldInject(Config, "database_url"),
            key: str = ModelFieldInject(Config, "api_key")
        ):
            return f"Connect to {url} with {key}"

        config = Config()
        context = {Config: config}
        injected = await inject_args(connect, context)
        result = injected()  # Uses config values
        ```

        Method call injection:
        ```python
        class UserService:
            def get_current_user_id(self) -> str:
                return "user123"

            @property
            def is_authenticated(self) -> bool:
                return True

        def handle_request(
            user_id: str = ModelFieldInject(UserService, "get_current_user_id"),
            authenticated: bool = ModelFieldInject(UserService, "is_authenticated")
        ):
            return f"User {user_id}, auth: {authenticated}"

        service = UserService()
        context = {UserService: service}
        injected = await inject_args(handle_request, context)
        result = injected()  # Calls methods on service
        ```

        Using Annotated syntax:
        ```python
        from typing_extensions import Annotated

        def func(
            url: Annotated[str, ModelFieldInject(Config, "database_url")],
            debug: Annotated[bool, ModelFieldInject(Config)]  # Uses param name
        ):
            return f"URL: {url}, Debug: {debug}"
        ```

    Note:
        - If field is None, the parameter name is used as the field name
        - Both attributes and methods (including properties) are supported
        - Methods are called automatically, attributes are accessed directly
        - The model instance must be available in the injection context
    """

    def __init__(
        self,
        model: Type[Any],
        field: Optional[str] = None,
        validator: Optional[Callable[..., Any]] = None,
        **meta: Any,
    ):
        """
        Initialize model field injection.

        Args:
            model: The model class to extract values from
            field: Field/method name (defaults to parameter name if None)
            validator: Optional validation function
            **meta: Additional metadata
        """
        super().__init__(default=..., validator=validator, **meta)
        self._model = model
        self.field = field

    @property
    def model(self) -> Type[Any]:
        """Get the model type for this injection."""
        return self._model


class CallableInjectable(Injectable):
    """Injectable for callable dependencies (functions, lambdas, etc.)."""

    def __init__(
        self,
        default: Callable[..., Any],
        validator: Optional[Callable[..., Any]] = None,
        **meta: Any,
    ):
        """
        Initialize callable injectable.

        Args:
            default: The callable dependency
            validator: Optional validation function
        """
        super().__init__(default=default, validator=validator, **meta)


class DependsInject(CallableInjectable):
    """
    Injectable for function dependencies that need to be called to provide values.

    This is used when you need to inject the result of calling another function.
    The dependency function can be sync or async, and can itself have injectable
    parameters that will be resolved recursively.

    The dependency resolution process:
    1. Analyzes the dependency function's signature
    2. Resolves its parameters from the injection context
    3. Calls the function (awaiting if async)
    4. Injects the result into the target parameter

    Examples:
        Simple dependency function:
        ```python
        def get_database_url() -> str:
            return "postgresql://localhost/mydb"

        def connect(url: str = DependsInject(get_database_url)):
            return f"Connecting to {url}"

        context = {}  # No additional context needed
        injected = await inject_args(connect, context)
        result = injected()  # "Connecting to postgresql://localhost/mydb"
        ```

        Dependency with its own dependencies:
        ```python
        def get_config() -> dict:
            return {"host": "localhost", "port": 5432}

        def create_db_url(config: dict = DependsInject(get_config)) -> str:
            return f"postgresql://{config['host']}:{config['port']}/mydb"

        def connect(url: str = DependsInject(create_db_url)):
            return f"Connecting to {url}"

        context = {}
        injected = await inject_args(connect, context)
        result = injected()
        ```

        Async dependency:
        ```python
        async def get_user_service() -> UserService:
            service = UserService()
            await service.initialize()
            return service

        def handle_request(service: UserService = DependsInject(get_user_service)):
            return service.get_current_user()

        context = {}
        injected = await inject_args(handle_request, context)
        result = injected()
        ```

        Lambda dependency (simple cases):
        ```python
        def process(timestamp: float = DependsInject(lambda: time.time())):
            return f"Processed at {timestamp}"
        ```

        Using Annotated syntax:
        ```python
        from typing_extensions import Annotated

        def func(
            service: Annotated[UserService, DependsInject(get_user_service)]
        ):
            return service.get_data()
        ```

    Note:
        - Dependency functions should have proper return type annotations
        - Lambdas without arguments are supported for simple cases
        - Async dependency functions are automatically awaited
        - Dependencies can have their own dependencies (recursive resolution)
        - All dependency resolution happens concurrently for performance
    """

    pass
