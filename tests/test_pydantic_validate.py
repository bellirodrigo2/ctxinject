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
        notvalid: int

    def func(
        arg: EmailStr = ModelFieldInject(model=Model, field="email"),
    ) -> None:
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
        notvalid: int

    def func(
        arg: UserModel = ModelFieldInject(model=Model, field="user_data"),
        notvalid: UserModel = ModelFieldInject(model=Model),
    ) -> None:
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

    class Model:
        data: str

    # Use a mapping that already has str -> dict
    test_arg_proc = {(str, dict): lambda x, **kwargs: {"mock": "data"}}

    def func(arg: Dict[Any, Any] = ModelFieldInject(model=Model, field="data")) -> None:
        return

    with patch(
        "ctxinject.validate.pydantic_add_model.pydantic_add_model"
    ) as mock_add_model:
        inject_validation(func, argproc=test_arg_proc)
        # add_model should not be called since validator exists in arg_proc
        mock_add_model.assert_not_called()


def test_custom_add_model_chaining() -> None:
    """Test that custom add_model works with default processors"""

    class Model:
        user_data: str
        custom_data: str

    class CustomType:
        def __init__(self, value: str):
            self.value = value

    def custom_add_model(arg, arg_proc):
        """Custom processor that handles CustomType conversions"""
        instance = arg.getinstance(ModelFieldInject)
        if instance and arg.basetype == CustomType:
            fieldname = instance.field or arg.name
            from typemapping import get_field_type

            modeltype = get_field_type(instance.model, fieldname)
            if modeltype is str:

                def str_to_custom(value: str, basetype=CustomType, **kwargs):
                    return basetype(value)

                key = (str, CustomType)
                arg_proc[key] = str_to_custom
                return str_to_custom
        return None

    def func(
        user_arg: UserModel = ModelFieldInject(model=Model, field="user_data"),
        custom_arg: CustomType = ModelFieldInject(model=Model, field="custom_data"),
    ) -> None:
        return

    args = get_func_args(func)
    user_modelinj = args[0].getinstance(ModelFieldInject)
    custom_modelinj = args[1].getinstance(ModelFieldInject)

    # Before injection
    assert not user_modelinj.has_validate
    assert not custom_modelinj.has_validate

    test_arg_proc = {}
    # Pass custom processor as list
    inject_validation(func, argproc=test_arg_proc, add_model=[custom_add_model])

    # After injection - both should have validators
    assert user_modelinj.has_validate  # From pydantic in default list
    assert custom_modelinj.has_validate  # From custom processor

    # Test custom processor worked
    custom_result = custom_modelinj.validate("test_value", basetype=CustomType)
    assert isinstance(custom_result, CustomType)
    assert custom_result.value == "test_value"

    # Test pydantic processor worked
    user_json = '{"name": "Test", "age": 25}'
    user_result = user_modelinj.validate(user_json, basetype=UserModel)
    assert isinstance(user_result, UserModel)
    assert user_result.name == "Test"


def test_add_model_directly() -> None:
    """Test add_model function directly"""
    from ctxinject.validate.pydantic_add_model import pydantic_add_model

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
    result = pydantic_add_model(arg, test_arg_proc)

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
    from ctxinject.validate.pydantic_add_model import pydantic_add_model

    test_arg_proc = {}

    class Model:
        user_data: str

    def func(arg: UserModel = ModelFieldInject(model=Model, field="user_data")) -> None:
        return

    args = get_func_args(func)
    arg = args[0]

    # Call add_model twice
    result1 = pydantic_add_model(arg, test_arg_proc)
    result2 = pydantic_add_model(arg, test_arg_proc)

    # Both should return the same function
    assert result1 is result2

    # Should only have one entry
    assert len([k for k in test_arg_proc.keys() if k[1] == UserModel]) == 1


def test_custom_add_model_only() -> None:
    """Test using only custom add_model without default processors"""
    from ctxinject.validate.inject_validation import (
        inject_validation as core_inject_validation,
    )

    class Model:
        data: str

    class SpecialType:
        def __init__(self, value: str):
            self.value = value.upper()

    def special_add_model(arg, arg_proc):
        """Custom processor for SpecialType"""
        instance = arg.getinstance(ModelFieldInject)
        if instance and arg.basetype == SpecialType:

            def str_to_special(value: str, basetype=SpecialType, **kwargs):
                return basetype(value)

            key = (str, SpecialType)
            arg_proc[key] = str_to_special
            return str_to_special
        return None

    def func(arg: SpecialType = ModelFieldInject(model=Model, field="data")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)
    assert not modelinj.has_validate

    test_arg_proc = {}
    # Use core inject_validation with only our custom processor
    core_inject_validation(func, argproc=test_arg_proc, add_model=[special_add_model])
    assert modelinj.has_validate

    # Test custom processor
    result = modelinj.validate("hello", basetype=SpecialType)
    assert isinstance(result, SpecialType)
    assert result.value == "HELLO"


def test_collections_add_model() -> None:
    """Test collections add_model functionality"""
    from collections.abc import Mapping, Sequence
    from typing import Dict, List

    class Model:
        mapping_field: Dict[str, str]
        list_field: List[str]

    def func(
        # Dict to Mapping conversion
        map_arg: Mapping[str, str] = ModelFieldInject(Model, "mapping_field"),
        # List to Sequence conversion
        seq_arg: Sequence[str] = ModelFieldInject(Model, "list_field"),
    ) -> None:
        return

    args = get_func_args(func)
    map_modelinj = args[0].getinstance(ModelFieldInject)
    seq_modelinj = args[1].getinstance(ModelFieldInject)

    assert not map_modelinj.has_validate
    assert not seq_modelinj.has_validate

    test_arg_proc = {}
    inject_validation(func, argproc=test_arg_proc)
    assert len(test_arg_proc) == 2


def test_default_processors_order() -> None:
    """Test that default processors are applied in correct order"""

    class Model:
        data: str

    class CustomModel(BaseModel):
        value: str

    def custom_add_model(arg, arg_proc):
        """Custom processor that processes everything as string"""
        instance = arg.getinstance(ModelFieldInject)
        if instance:
            # This should NOT override Pydantic processing
            return None

    def func(arg: CustomModel = ModelFieldInject(model=Model, field="data")) -> None:
        return

    args = get_func_args(func)
    modelinj = args[0].getinstance(ModelFieldInject)

    test_arg_proc = {}
    # Custom processor first, then defaults (collections, pydantic)
    inject_validation(func, argproc=test_arg_proc, add_model=[custom_add_model])

    assert modelinj.has_validate

    # Should use Pydantic processing since custom returned None
    json_data = '{"value": "test"}'
    result = modelinj.validate(json_data, basetype=CustomModel)
    assert isinstance(result, CustomModel)
    assert result.value == "test"
