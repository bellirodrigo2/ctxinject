
from datetime import datetime
from typing import Any

import pytest
from ctxinject.inject import inject_args
from ctxinject.model import CastType, Validation


def name_validator(name: str, **kwargs: Any) -> str:
    if not name.isalpha():
        raise ValueError("Name must contain only alphabetic characters")
    return name


def positive_int_validator(value: int, **kwargs: Any) -> int:
    if value <= 0:
        raise ValueError("Value must be positive")
    return value


def email_validator(email: str, **kwargs: Any) -> str:
    if "@" not in email:
        raise ValueError("Invalid email format")
    return email.lower()


def length_validator(text: str, min_length: int = 3, **kwargs: Any) -> str:
    if len(text) < min_length:
        raise ValueError(f"Text must be at least {min_length} characters")
    return text


def func_basic(
    name: str = Validation(validator=name_validator),
    time: datetime = CastType(from_type=str)
) -> tuple:
    return name, type(time)


def func_multiple_validations(
    name: str = Validation(validator=name_validator),
    email: str = Validation(validator=email_validator),
    age: int = Validation(validator=positive_int_validator),
    bio: str = Validation(validator=length_validator, min_length=5)
) -> tuple:
    return name, email, age, bio


def func_only_cast(
    count: int = CastType(from_type=str),
    price: float = CastType(from_type=str)
) -> tuple:
    return count, price, type(count), type(price)


def int_cast_validator(value: str, **kwargs: Any) -> int:
    return int(value)


def float_cast_validator(value: str, **kwargs: Any) -> float:
    return float(value)


def func_only_cast_with_validators(
    count: int = Validation(validator=int_cast_validator),
    price: float = Validation(validator=float_cast_validator)
) -> tuple:
    return count, price, type(count), type(price)


def func_only_validation(
    username: str = Validation(validator=name_validator)
) -> str:
    return username


def func_mixed_dependencies(
    regular_param: str,
    name: str = Validation(validator=name_validator),
    timestamp: datetime = CastType(from_type=str)
) -> tuple:
    return name, timestamp, regular_param


# Success test cases
@pytest.mark.asyncio
async def test_validation_and_cast_success():
    ctx = {
        "name": "John",
        "time": "2023-10-01T12:00:00"
    }
    injected = await inject_args(func_basic, ctx)
    name, type_time = injected()
    assert name == "John"
    assert type_time == datetime


@pytest.mark.asyncio
async def test_multiple_validations_success():
    ctx = {
        "name": "Alice",
        "email": "ALICE@EXAMPLE.COM",
        "age": 25,
        "bio": "Software developer"
    }
    injected = await inject_args(func_multiple_validations, ctx)
    name, email, age, bio = injected()
    assert name == "Alice"
    assert email == "alice@example.com"  # Email should be lowercased
    assert age == 25
    assert bio == "Software developer"


@pytest.mark.asyncio
async def test_only_cast_success():
    ctx = {
        "count": "42",
        "price": "19.99"
    }
    injected = await inject_args(func_only_cast_with_validators, ctx)
    count, price, count_type, price_type = injected()
    # The validator should convert from str to int/float
    assert count == 42
    assert price == 19.99
    assert count_type is int
    assert price_type is float


@pytest.mark.asyncio
async def test_cast_type_basic():
    # Test that CastType at least doesn't break, even if no auto-casting
    ctx = {
        "count": "42",
        "price": "19.99"
    }
    injected = await inject_args(func_only_cast, ctx)
    count, price, count_type, price_type = injected()
    # Without explicit validators, values remain as strings
    assert count == "42"
    assert price == "19.99"
    assert count_type is str
    assert price_type is str


@pytest.mark.asyncio
async def test_only_validation_success():
    ctx = {"username": "validname"}
    injected = await inject_args(func_only_validation, ctx)
    result = injected()
    assert result == "validname"


@pytest.mark.asyncio
async def test_mixed_dependencies_success():
    ctx = {
        "name": "Bob",
        "timestamp": "2023-12-25T10:30:00",
        "regular_param": "test_value"
    }
    injected = await inject_args(func_mixed_dependencies, ctx)
    name, timestamp, regular_param = injected()
    assert name == "Bob"
    assert isinstance(timestamp, datetime)
    assert regular_param == "test_value"


# Validation failure test cases
@pytest.mark.asyncio
async def test_validation_failure_invalid_name():
    ctx = {
        "name": "John123",  # Contains numbers
        "time": "2023-10-01T12:00:00"
    }
    
    with pytest.raises(ValueError, match="Name must contain only alphabetic characters"):
        await inject_args(func_basic, ctx)


@pytest.mark.asyncio
async def test_validation_failure_negative_age():
    ctx = {
        "name": "Alice",
        "email": "alice@example.com",
        "age": -5,  # Negative age
        "bio": "Developer"
    }
    
    with pytest.raises(ValueError, match="Value must be positive"):
        await inject_args(func_multiple_validations, ctx)


@pytest.mark.asyncio
async def test_validation_failure_invalid_email():
    ctx = {
        "name": "Alice",
        "email": "invalid_email",  # No @ symbol
        "age": 25,
        "bio": "Developer"
    }
    
    with pytest.raises(ValueError, match="Invalid email format"):
        await inject_args(func_multiple_validations, ctx)


@pytest.mark.asyncio
async def test_validation_failure_short_bio():
    ctx = {
        "name": "Alice",
        "email": "alice@example.com",
        "age": 25,
        "bio": "Dev"  # Too short (< 5 chars)
    }
    
    with pytest.raises(ValueError, match="Text must be at least 5 characters"):
        await inject_args(func_multiple_validations, ctx)


# Type casting failure test cases
@pytest.mark.asyncio
async def test_cast_failure_invalid_int():
    ctx = {
        "count": "not_a_number",
        "price": "19.99"
    }
    
    with pytest.raises(ValueError):
        await inject_args(func_only_cast_with_validators, ctx)


@pytest.mark.asyncio
async def test_cast_failure_invalid_float():
    ctx = {
        "count": "42",
        "price": "not_a_float"
    }
    
    with pytest.raises(ValueError):
        await inject_args(func_only_cast_with_validators, ctx)


@pytest.mark.asyncio
async def test_cast_failure_invalid_datetime():
    ctx = {
        "name": "John",
        "time": "invalid_datetime_string"
    }
    
    with pytest.raises(Exception):  # Could be ValueError or other validation error
        await inject_args(func_basic, ctx)


# Edge cases
@pytest.mark.asyncio
async def test_empty_string_validation():
    ctx = {"username": ""}
    
    with pytest.raises(ValueError, match="Name must contain only alphabetic characters"):
        await inject_args(func_only_validation, ctx)


@pytest.mark.asyncio
async def test_zero_as_positive_validator():
    ctx = {
        "name": "Alice",
        "email": "alice@example.com",
        "age": 0,  # Zero should fail positive validation
        "bio": "Developer"
    }
    
    with pytest.raises(ValueError, match="Value must be positive"):
        await inject_args(func_multiple_validations, ctx)


@pytest.mark.asyncio
async def test_special_characters_in_name():
    test_cases = [
        "name-with-dash",
        "name with space",
        "name_with_underscore",
        "name@symbol",
        "123numbers"
    ]
    
    for invalid_name in test_cases:
        ctx = {"username": invalid_name}
        
        with pytest.raises(ValueError, match="Name must contain only alphabetic characters"):
            await inject_args(func_only_validation, ctx)


@pytest.mark.asyncio
async def test_boundary_values_cast():
    ctx = {
        "count": "0",
        "price": "0.0"
    }
    injected = await inject_args(func_only_cast_with_validators, ctx)
    count, price, count_type, price_type = injected()
    assert count == 0
    assert price == 0.0
    assert count_type is int
    assert price_type is float


@pytest.mark.asyncio
async def test_large_numbers_cast():
    ctx = {
        "count": "999999",
        "price": "123456.789"
    }
    injected = await inject_args(func_only_cast_with_validators, ctx)
    count, price, count_type, price_type = injected()
    assert count == 999999
    assert price == 123456.789
    assert count_type is int
    assert price_type is float


@pytest.mark.asyncio
async def test_whitespace_handling():
    ctx = {
        "count": "  42  ",  # With whitespace
        "price": " 19.99 "
    }
    injected = await inject_args(func_only_cast_with_validators, ctx)
    count, price, count_type, price_type = injected()
    assert count == 42
    assert price == 19.99
    assert count_type is int
    assert price_type is float


# Test validation with metadata
def metadata_validator(value: str, prefix: str = "", **kwargs: Any) -> str:
    return f"{prefix}{value}"


def func_with_metadata(
    text: str = Validation(validator=metadata_validator, prefix="Hello ")
) -> str:
    return text


@pytest.mark.asyncio
async def test_validation_with_metadata():
    ctx = {"text": "World"}
    injected = await inject_args(func_with_metadata, ctx)
    result = injected()
    assert result == "Hello World"