# 🚀 ctxinject
A powerful, FastAPI-inspired dependency injection library for Python with async support, strong typing, and flexible injection strategies.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/bellirodrigo2/ctxinject/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/bellirodrigo2/ctxinject/actions)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)

## ✨ Key Features

- 🚀 **FastAPI-style dependency injection** - Familiar `Depends()` pattern
- 🏗️ **Model field injection** - Direct access to model fields and methods in function signatures
- 🔒 **Strongly typed** - Full type safety with automatic validation
- ⚡ **Async/Sync support** - Works with both synchronous and asynchronous functions
- 🎯 **Multiple injection strategies** - By type, name, model fields, or dependencies
- ✅ **Automatic validation** - Built-in Pydantic integration and custom validators
- 🧪 **Test-friendly** - Easy dependency overriding for testing
- 🐍 **Python 3.8+** - Modern Python support
- 📊 **100% test coverage** - Production-ready reliability

## 🚀 Quick Start

Here's a practical HTTP request processing example:

```python
import asyncio
from typing import cast
import requests
from pydantic import BaseModel
from typing_extensions import Annotated, Dict, Mapping, Optional, Protocol

from ctxinject.inject import inject_args
from ctxinject.model import DependsInject, ModelFieldInject


class PreparedRequest(Protocol):
    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes


class BodyModel(BaseModel):
    name: str
    email: str
    age: int


# Async dependency function
async def get_db() -> str:
    await asyncio.sleep(0.1)
    return "postgresql"


# Custom model field injector
class FromRequest(ModelFieldInject):
    def __init__(self, field: Optional[str] = None, **kwargs):
        super().__init__(PreparedRequest, field, **kwargs)


# Function with multiple injection strategies
def process_http(
    url: Annotated[str, FromRequest()],  # Extract from model field
    method: Annotated[str, FromRequest()],  # Extract from model field
    body: Annotated[BodyModel, FromRequest()],  # Extract and validate
    headers: Annotated[Dict[str, str], FromRequest()],  # Extract from model field
    db: str = DependsInject(get_db),  # Async dependency
) -> Mapping[str, str]:
    return {
        "url": url,
        "method": method,
        "body": body.name,  # Pydantic model automatically validated
        "headers": len(headers),
        "db": db,
    }


async def main():
    # Create a prepared request
    req = requests.Request(
        method="POST",
        url="https://api.example.com/user",
        headers={"Content-Type": "application/json"},
        json={"name": "João Silva", "email": "joao@email.com", "age": 30}
    )
    prepared_req = cast(PreparedRequest, req.prepare())
    
    # Inject dependencies
    context = {PreparedRequest: prepared_req}
    injected_func = await inject_args(process_http, context)
    
    # Call with all dependencies resolved
    result = injected_func()
    print(result)  # All dependencies automatically injected!

    def mocked_get_db()->str:
        return 'test'

    injected_func = await inject_args(process_http, context, {get_db: mocked_get_db})
    result = injected_func() # get_db mocked!

if __name__ == "__main__":
    asyncio.run(main())
```

## 📦 Installation

```bash
pip install ctxinject
```

For Pydantic validation support:
```bash
pip install ctxinject[pydantic]
```

## 📖 Usage Guide

### 1. Basic Dependency Injection

```python
from ctxinject.inject import inject_args
from ctxinject.model import ArgsInjectable

def greet(
    name: str,
    count: int = ArgsInjectable(5)    # Optional with default
):
    return f"Hello {name}! (x{count})"

# Inject by name and type
context = {"name": "Alice"}
injected = await inject_args(greet, context)
result = injected()  # "Hello Alice! (x5)"
```

### 2. FastAPI-style Dependencies

```python
from ctxinject.model import DependsInject

def get_database_url() -> str:
    return "postgresql://localhost/mydb"

async def get_user_service() -> UserService:
    service = UserService()
    await service.initialize()
    return service

def process_request(
    db_url: str = DependsInject(get_database_url),
    user_service: UserService = DependsInject(get_user_service)
):
    return f"Processing with {db_url}"

# Dependencies resolved automatically
injected = await inject_args(process_request, {})
result = injected()
```

### 3. Model Field Injection

```python
from ctxinject.model import ModelFieldInject

class Config:
    database_url: str = "sqlite:///app.db"
    debug: bool = True
    
    def get_secret_key(self) -> str:
        return "super-secret-key"

def initialize_app(
    db_url: str = ModelFieldInject(Config, "database_url"),
    debug: bool = ModelFieldInject(Config, "debug"),
    secret: str = ModelFieldInject(Config, "get_secret_key")  # Method call
):
    return f"App: {db_url}, debug={debug}, secret={secret}"

config = Config()
context = {Config: config}
injected = await inject_args(initialize_app, context)
result = injected()
```

### 4. Validation and Type Conversion

```python
from typing_extensions import Annotated
from ctxinject.model import ArgsInjectable

def validate_positive(value: int, **kwargs) -> int:
    if value <= 0:
        raise ValueError("Must be positive")
    return value

def process_data(
    count: Annotated[int, ArgsInjectable(1, validate_positive)],
    email: str = ArgsInjectable(...),  # Automatic email validation if Pydantic available
):
    return f"Processing {count} items for {email}"

context = {"count": 5, "email": "user@example.com"}
injected = await inject_args(process_data, context)
result = injected()
```

### 5. Partial Injection (Mixed Arguments)

```python
def process_user_data(
    user_id: str,  # Not injected - will remain as parameter
    db_url: str = DependsInject(get_database_url),
    config: Config = ModelFieldInject(Config)
):
    return f"Processing user {user_id} with {db_url}"

# Only some arguments are injected
context = {Config: config_instance}
injected = await inject_args(process_user_data, context, allow_incomplete=True)

# user_id still needs to be provided
result = injected("user123")  # "Processing user user123 with postgresql://..."
```

### 6. Function Signature Validation

Validate function signatures at bootstrap time to catch injection issues early. Unlike runtime errors, `func_signature_check()` returns all validation errors at once, giving you a complete overview of what needs to be fixed.

```python
from ctxinject.sigcheck import func_signature_check

def validate_at_startup():
    # Check if function can be fully injected at bootstrap time
    errors = func_signature_check(process_request, modeltype=[Config])
    
    if errors:
        print("Function cannot be fully injected:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Function is ready for injection!")

# Run validation before your app starts
validate_at_startup()
```

### 7. Testing with Overrides

```python
# Original dependency
async def get_real_service() -> str:
    return "production-service"

def business_logic(service: str = DependsInject(get_real_service)):
    return f"Using {service}"

# Test with mock
async def get_mock_service() -> str:
    return "mock-service"

# Override for testing
injected = await inject_args(
    business_logic, 
    context={},
    overrides={get_real_service: get_mock_service}
)
result = injected()  # "Using mock-service"
```

## 🎯 Injection Strategies

| Strategy | Description | Example |
|----------|-------------|---------|
| **By Name** | Match parameter name to context key | `{"param_name": value}` |
| **By Type** | Match parameter type to context type | `{MyClass: instance}` |
| **Model Field** | Extract field/method from model instance | `ModelFieldInject(Config, "field")` |
| **Dependency** | Call function to resolve value | `DependsInject(get_value)` |
| **Default** | Use default value from injectable | `ArgsInjectable(42)` |

## 🔧 Advanced Features

### Async Optimization
- Concurrent resolution of async dependencies
- Fast isinstance() checks for sync/async separation
- Optimal performance with minimal overhead

### Type Safety
- Full type checking with mypy support
- Runtime type validation
- Generic type support

### Extensible Validation
- Built-in Pydantic integration
- Custom validator functions
- Constraint validation (min/max, patterns, etc.)

## 🏗️ Architecture

ctxinject uses a resolver-based architecture:

1. **Analysis Phase**: Function signature is analyzed to identify injectable parameters
2. **Mapping Phase**: Parameters are mapped to appropriate resolvers based on injection strategy
3. **Resolution Phase**: Resolvers are executed (sync immediately, async concurrently)
4. **Injection Phase**: Resolved values are injected into the function

This design ensures optimal performance and flexibility.

## 🤝 Contributing

Contributions are welcome! Please check out our contributing guidelines and make sure all tests pass:

```bash
pytest --cov=ctxinject --cov-report=html
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Projects

- [FastAPI](https://fastapi.tiangolo.com/) - The inspiration for the dependency injection pattern
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Validation and serialization library

---

**ctxinject** - Powerful dependency injection for modern Python applications!