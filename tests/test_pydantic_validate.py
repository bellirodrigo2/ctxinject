from typing import Any, Dict

import pytest
from pydantic import AnyUrl, BaseModel, EmailStr, HttpUrl, IPvAnyAddress
from typemapping import get_func_args

from ctxinject.model import ModelFieldInject
from ctxinject.validate import inject_validation
from ctxinject.validate.pydantic_argproc import arg_proc as pydantic_arg_proc


class UserModel(BaseModel):
    name: str
    age: int


class ProductModel(BaseModel):
    title: str
    price: float
    in_stock: bool


def test_validate_email() -> None:
    """Test email validation"""

    class Model:
        email: str

    def func(arg: EmailStr = ModelFieldInject(model=Model, field="email")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=pydantic_arg_proc)
    assert modelinj.has_validate

    # Valid email
    result = modelinj.validate("user@example.com", basetype=EmailStr)
    assert str(result) == "user@example.com"

    # Invalid email
    with pytest.raises(ValueError):
        modelinj.validate("not-an-email", basetype=EmailStr)


def test_validate_http_url() -> None:
    """Test HTTP URL validation"""

    class Model:
        website: str

    def func(arg: HttpUrl = ModelFieldInject(model=Model, field="website")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=pydantic_arg_proc)
    assert modelinj.has_validate

    # Valid HTTP URL
    result = modelinj.validate("https://example.com", basetype=HttpUrl)
    assert str(result) == "https://example.com/"

    # Valid HTTP URL
    result = modelinj.validate("http://localhost:8080", basetype=HttpUrl)
    assert str(result) == "http://localhost:8080/"

    # Invalid URL (not HTTP/HTTPS)
    with pytest.raises(ValueError):
        modelinj.validate("ftp://example.com", basetype=HttpUrl)


def test_validate_any_url() -> None:
    """Test any URL validation"""

    class Model:
        link: str

    def func(
        arg2: int = ModelFieldInject(model=Model, field="link"),
        arg: AnyUrl = ModelFieldInject(model=Model, field="link"),
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[1].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=pydantic_arg_proc)
    assert modelinj.has_validate

    # Valid URLs
    result = modelinj.validate("https://example.com", basetype=AnyUrl)
    assert str(result) == "https://example.com/"

    result = modelinj.validate("ftp://files.example.com", basetype=AnyUrl)
    assert str(result) == "ftp://files.example.com/"

    # Invalid URL
    with pytest.raises(ValueError):
        modelinj.validate("not-a-url", basetype=AnyUrl)


def test_validate_ip_address() -> None:
    """Test IP address validation"""

    class Model:
        server_ip: str

    def func(
        arg: IPvAnyAddress = ModelFieldInject(model=Model, field="server_ip")
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    inject_validation(func, argproc=pydantic_arg_proc)
    assert modelinj.has_validate

    # Valid IPv4
    result = modelinj.validate("192.168.1.1", basetype=IPvAnyAddress)
    assert str(result) == "192.168.1.1"

    # Valid IPv6
    result = modelinj.validate("2001:db8::1", basetype=IPvAnyAddress)
    assert str(result) == "2001:db8::1"

    # Invalid IP
    with pytest.raises(ValueError):
        modelinj.validate("999.999.999.999", basetype=IPvAnyAddress)


def test_add_model_str_to_user() -> None:
    """Test add_model functionality with str to UserModel"""

    class Model:
        user_data: str

    def func(arg: UserModel = ModelFieldInject(model=Model, field="user_data")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    # Use a copy of arg_proc without the (str, UserModel) mapping to force add_model
    test_arg_proc = pydantic_arg_proc.copy()
    # Ensure (str, UserModel) is not in the mapping
    if (str, UserModel) in test_arg_proc:
        del test_arg_proc[(str, UserModel)]

    # This should trigger add_model since (str, UserModel) is not in arg_proc
    inject_validation(func, argproc=test_arg_proc)
    assert modelinj.has_validate

    # Test with valid JSON string - this is what matters, the validator should work
    user_json = '{"name": "Alice", "age": 30}'
    result = modelinj.validate(user_json, basetype=UserModel)
    assert isinstance(result, UserModel)
    assert result.name == "Alice"
    assert result.age == 30

    # Test with invalid JSON
    with pytest.raises(ValueError):
        modelinj.validate("invalid json", basetype=UserModel)

    # Test with valid JSON but invalid model data
    with pytest.raises(ValueError):
        modelinj.validate('{"name": "Bob"}', basetype=UserModel)  # missing age


def test_add_model_str_to_product() -> None:
    """Test add_model functionality with str to ProductModel"""

    class Model:
        product_info: str

    def func(
        arg: ProductModel = ModelFieldInject(model=Model, field="product_info")
    ) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    # Use a copy without ProductModel mapping
    test_arg_proc = pydantic_arg_proc.copy()
    if (str, ProductModel) in test_arg_proc:
        del test_arg_proc[(str, ProductModel)]

    inject_validation(func, argproc=test_arg_proc)
    assert modelinj.has_validate

    # Verify add_model added the mapping to arg_proc
    assert (str, ProductModel) in test_arg_proc

    # Test with valid JSON string
    product_json = '{"title": "Laptop", "price": 999.99, "in_stock": true}'
    result = modelinj.validate(product_json, basetype=ProductModel)
    assert isinstance(result, ProductModel)
    assert result.title == "Laptop"
    assert result.price == 999.99
    assert result.in_stock is True

    # Test with invalid model data
    with pytest.raises(ValueError):
        modelinj.validate(
            '{"title": "Mouse", "price": "not_a_number"}', basetype=ProductModel
        )


def test_add_model_bytes_to_user() -> None:
    """Test add_model functionality with bytes to UserModel"""

    class Model:
        user_data: bytes

    def func(arg: UserModel = ModelFieldInject(model=Model, field="user_data")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    # Use a copy without bytes mapping
    test_arg_proc = pydantic_arg_proc.copy()
    if (bytes, UserModel) in test_arg_proc:
        del test_arg_proc[(bytes, UserModel)]

    inject_validation(func, argproc=test_arg_proc)
    assert modelinj.has_validate

    # Verify add_model added the mapping to arg_proc
    assert (bytes, UserModel) in test_arg_proc

    # Test with valid JSON bytes
    user_json = b'{"name": "Charlie", "age": 25}'
    result = modelinj.validate(user_json, basetype=UserModel)
    assert isinstance(result, UserModel)
    assert result.name == "Charlie"
    assert result.age == 25

    # Test with invalid JSON bytes
    with pytest.raises(ValueError):
        modelinj.validate(b"invalid json", basetype=UserModel)


def test_multiple_models_different_keys() -> None:
    """Test that different models get different keys in arg_proc"""

    class Model1:
        user: str
        product: str

    def func1(
        user_arg: UserModel = ModelFieldInject(model=Model1, field="user"),
        product_arg: ProductModel = ModelFieldInject(model=Model1, field="product"),
    ) -> None:
        return

    args = get_func_args(func1)
    user_modelinj = args[0].getinstance(ModelFieldInject)
    product_modelinj = args[1].getinstance(ModelFieldInject)

    # Before injection
    assert not user_modelinj.has_validate
    assert not product_modelinj.has_validate

    inject_validation(func1, argproc=pydantic_arg_proc)

    # After injection - both should have validators
    assert user_modelinj.has_validate
    assert product_modelinj.has_validate

    # Test that they work independently
    user_json = '{"name": "Dave", "age": 35}'
    user_result = user_modelinj.validate(user_json, basetype=UserModel)
    assert user_result.name == "Dave"

    product_json = '{"title": "Keyboard", "price": 79.99, "in_stock": false}'
    product_result = product_modelinj.validate(product_json, basetype=ProductModel)
    assert product_result.title == "Keyboard"


def test_arg_proc_gets_updated() -> None:
    """Test that arg_proc dictionary gets updated with new models"""
    # Start with empty arg_proc to guarantee add_model runs
    test_arg_proc = {}

    class Model:
        custom_data: str

    class CustomModel(BaseModel):
        id: int
        name: str

    def func(
        arg: CustomModel = ModelFieldInject(model=Model, field="custom_data")
    ) -> None:
        return

    # Before injection - should be empty
    assert (str, CustomModel) not in test_arg_proc

    inject_validation(func, argproc=test_arg_proc)

    # After injection - should contain the new model mapping
    assert (str, CustomModel) in test_arg_proc

    # Test that the validator works
    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert modelinj.has_validate

    custom_json = '{"id": 123, "name": "test"}'
    result = modelinj.validate(custom_json, basetype=CustomModel)
    assert isinstance(result, CustomModel)
    assert result.id == 123
    assert result.name == "test"


def test_add_model_not_called_when_validator_exists() -> None:
    """Test that add_model is not called when validator already exists"""
    from unittest.mock import patch

    from ctxinject.validate.pydantic_validate import add_model

    class Model:
        data: str

    # Use a mapping that already has str -> dict
    test_arg_proc = {(str, dict): lambda x, **kwargs: {"mock": "data"}}

    def func(arg: Dict[Any, Any] = ModelFieldInject(model=Model, field="data")) -> None:
        return

    with patch(
        "ctxinject.validate.pydantic_validate.add_model", wraps=add_model
    ) as mock_add_model:
        inject_validation(func, argproc=test_arg_proc)
        # add_model should not be called since validator exists
        mock_add_model.assert_not_called()


def test_add_model_with_pydantic_validator_false() -> None:
    """Test that add_model is not called when PYDANTIC_VALIDATOR is False"""
    from unittest.mock import patch

    class Model:
        user_data: str

    def func(arg: UserModel = ModelFieldInject(model=Model, field="user_data")) -> None:
        return

    test_arg_proc = {}  # Empty to ensure no validator exists

    # Mock PYDANTIC_VALIDATOR to be False
    with patch("ctxinject.validate.inject_validation.PYDANTIC_VALIDATOR", False):
        inject_validation(func, argproc=test_arg_proc)

        # Should not add any validators when PYDANTIC_VALIDATOR is False
        assert len(test_arg_proc) == 0

        args = get_func_args(func)
        modelinj = args[0].getinstance(ModelFieldInject)
        # Should not have validator since add_model wasn't called
        assert not modelinj.has_validate


def test_add_model_directly() -> None:
    """Test add_model function directly"""
    from ctxinject.validate.pydantic_validate import add_model

    test_arg_proc = {}

    class Model:
        user_data: str

    def func(arg: UserModel = ModelFieldInject(model=Model, field="user_data")) -> None:
        return

    args = get_func_args(func)
    arg = args[0]

    # Before calling add_model
    assert (str, UserModel) not in test_arg_proc

    # Call add_model directly
    result = add_model(arg, (str, bytes), test_arg_proc)

    # Should return the validator function
    assert result is not None
    assert callable(result)

    # Should have added the mapping to arg_proc
    assert (str, UserModel) in test_arg_proc

    # Test the returned validator
    user_json = '{"name": "Direct", "age": 40}'
    validated_user = result(user_json, UserModel)
    assert isinstance(validated_user, UserModel)
    assert validated_user.name == "Direct"
    assert validated_user.age == 40


def test_add_model_does_not_duplicate() -> None:
    """Test that add_model doesn't duplicate entries if called multiple times"""
    from ctxinject.validate.pydantic_validate import add_model

    test_arg_proc = {}

    class Model:
        user_data: str

    def func(arg: UserModel = ModelFieldInject(model=Model, field="user_data")) -> None:
        return

    args = get_func_args(func)
    arg = args[0]

    # Call add_model twice
    result1 = add_model(arg, (str, bytes), test_arg_proc)
    result2 = add_model(arg, (str, bytes), test_arg_proc)

    # Both should return the same function
    assert result1 is result2

    # Should only have one entry
    assert len([k for k in test_arg_proc.keys() if k[1] == UserModel]) == 1
