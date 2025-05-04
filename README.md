
# `ctx_inject` Library

`ctx_inject` is a Python dependency injection library that provides utilities for managing the injection of arguments and dependencies into functions and classes. It leverages Python's type hints and inspect module to resolve and inject dependencies at runtime.

## Features

- **Dependency Injection**: Automatically resolve function arguments from a context, enabling clean and flexible dependency injection patterns.
- **Support for Annotations**: Works with Python's type annotations, allowing for rich type-checking.
- **Custom Validators**: Allows custom validation for injected values.
- **Model-based Injection**: Supports injecting values from models (e.g., database models) into functions based on the field names.

## Installation

You can install the `ctx_inject` library via `pip`:

```bash
pip install ctx_inject
```

## Usage

### 1. **Injecting Function Arguments**

You can inject arguments into functions using the `inject_args` function.

```python
from ctx_inject import inject_args

def my_function(a: int, b: str):
    return f"Received {a} and {b}"

# Create a context with dependencies
context = {
    'a': 5,
    'b': 'Hello'
}

# Inject arguments into the function
injected_function = inject_args(my_function, context)

# Call the function with the injected arguments
result = injected_function()
print(result)  # Output: Received 5 and Hello
```

### 2. **Using Custom Injectables**

You can define custom injectables by implementing the `Injectable` class or its subclasses.

```python
from ctx_inject import Injectable

class MyInjectable(Injectable):
    def __init__(self, default_value):
        super().__init__(default_value)

    def validate(self, instance, basetype):
        return instance  # Custom validation can be added here

# Creating an injectable
injectable = MyInjectable(42)

# Usage in a context
context = {
    'my_injectable': injectable
}
```

### 3. **Injecting Dependencies with `Depends`**

Dependencies can be injected dynamically into functions using `DependsInject`.

```python
from ctx_inject import DependsInject, inject_args

def get_service(name: str) -> str:
    return f"Service: {name}"

# Creating a context with dependencies
context = {
    'service_name': 'MyService'
}

# Defining the injected function
injected_function = inject_args(get_service, context)

# The injected function will use the provided context for dependencies
result = injected_function()
print(result)  # Output: Service: MyService
```

## Classes and Functions

### `Injectable`
Base class for defining injectable values.

- **`default`**: The default value that will be injected.
- **`validate`**: Used to validate the injected value.

### `ArgsInjectable`
Subclass of `Injectable` used for argument injection.

### `CallableInjectable`
Injectable that expects a callable as its default.

### `DependsInject`
Subclass of `CallableInjectable` used for dependency injection.

### `ModelFieldInject`
An injectable class that injects fields from models (e.g., database models).

### `inject_args(func, context)`
Injects arguments into the given function based on the provided context.

### `resolve_ctx(args, context, allow_incomplete)`
Resolves the context for the provided function arguments.

### `func_arg_factory(name, param, annotation)`
Factory function to create `FuncArg` objects for function parameters.

## Error Handling

The library defines several exceptions for error handling:

- **`UnresolvedInjectableError`**: Raised when a dependency cannot be resolved.
- **`UnInjectableError`**: Raised when a function argument cannot be injected.
- **`ValidationError`**: Raised when a validation fails for injected values.
- **`InvalidInjectableDefinition`**: Raised when an injectable is incorrectly defined.

## Validation Functions

The library provides a set of validation functions for constraining argument values:

- **`ConstrainedStr`**: Validate string values.
- **`ConstrainedNumber`**: Validate numeric values.
- **`ConstrainedDatetime`**: Validate datetime values.
- **`ConstrainedUUID`**: Validate UUID values.
- **`ConstrainedEnum`**: Validate Enum values.
- **`ConstrainedItems`**: Validate items in a collection (list, tuple, set, etc.).

### Example Usage of Constrained Values

```python
from ctx_inject import ConstrainedStr, ValidationError

def my_function(name: str):
    return f"Hello, {name}"

# Using constrained string validation
context = {
    'name': ConstrainedStr('John', min_length=3)
}

# Injecting arguments with validation
injected_function = inject_args(my_function, context)
result = injected_function()
print(result)  # Output: Hello, John
```

## Contributing

Feel free to contribute to the `ctx_inject` library! You can submit bug reports, feature requests, or pull requests.

1. Fork the repository.
2. Create a new branch for your changes.
3. Write tests for your changes.
4. Submit a pull request.

## License

`ctx_inject` is released under the MIT License. See [LICENSE](LICENSE) for more information.
