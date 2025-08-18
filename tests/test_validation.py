import sys
from datetime import date, datetime, time
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from dateutil.parser import ParserError

from ctxinject.model import ModelFieldInject

# Import all functions and classes from validation.py
from ctxinject.validation import (
    ConstrainedDatetime,
    ConstrainedNumber,
    ConstrainedStr,
    ConstrainedUUID,
    ValidationError,
    arg_proc,
    base_constrained_dict,
    base_constrained_list,
    constrained_bytejson,
    constrained_date,
    constrained_datetime,
    constrained_dict,
    constrained_json,
    constrained_list,
    constrained_num,
    constrained_str,
    constrained_time,
    constrained_uuid,
    extract_type,
    func_arg_validator,
    get_validator,
    validator_check,
    validators,
)


class TestConstrainedStr:
    """Test ConstrainedStr function."""

    def test_valid_string(self):
        assert ConstrainedStr("hello") == "hello"

    def test_min_length_valid(self):
        assert ConstrainedStr("hello", min_length=3) == "hello"

    def test_min_length_invalid(self):
        with pytest.raises(ValidationError, match="String length must be minimun 5"):
            ConstrainedStr("hi", min_length=5)

    def test_max_length_valid(self):
        assert ConstrainedStr("hello", max_length=10) == "hello"

    def test_max_length_invalid(self):
        with pytest.raises(ValidationError, match="String length must be maximun 3"):
            ConstrainedStr("hello", max_length=3)

    def test_pattern_valid(self):
        assert ConstrainedStr("hello123", pattern=r"^hello\d+$") == "hello123"

    def test_pattern_invalid(self):
        with pytest.raises(ValidationError, match="String does not match pattern"):
            ConstrainedStr("hello", pattern=r"^\d+$")

    def test_all_constraints(self):
        result = ConstrainedStr(
            "hello123", min_length=5, max_length=10, pattern=r"^hello\d+$"
        )
        assert result == "hello123"


class TestConstrainedNumber:
    """Test ConstrainedNumber function."""

    def test_valid_int(self):
        assert ConstrainedNumber(5) == 5

    def test_valid_float(self):
        assert ConstrainedNumber(5.5) == 5.5

    def test_gt_valid(self):
        assert ConstrainedNumber(10, gt=5) == 10

    def test_gt_invalid(self):
        with pytest.raises(ValidationError, match="Value must be > 10"):
            ConstrainedNumber(10, gt=10)

    def test_ge_valid(self):
        assert ConstrainedNumber(10, ge=10) == 10

    def test_ge_invalid(self):
        with pytest.raises(ValidationError, match="Value must be >= 10"):
            ConstrainedNumber(9, ge=10)

    def test_lt_valid(self):
        assert ConstrainedNumber(5, lt=10) == 5

    def test_lt_invalid(self):
        with pytest.raises(ValidationError, match="Value must be < 10"):
            ConstrainedNumber(10, lt=10)

    def test_le_valid(self):
        assert ConstrainedNumber(10, le=10) == 10

    def test_le_invalid(self):
        with pytest.raises(ValidationError, match="Value must be <= 10"):
            ConstrainedNumber(11, le=10)

    def test_multiple_of_valid(self):
        assert ConstrainedNumber(15, multiple_of=5) == 15

    def test_multiple_of_invalid(self):
        with pytest.raises(ValidationError, match="Value must be a multiple of 5"):
            ConstrainedNumber(13, multiple_of=5)

    def test_all_constraints(self):
        result = ConstrainedNumber(15, gt=10, lt=20, multiple_of=5)
        assert result == 15


class TestConstrainedUUID:
    """Test ConstrainedUUID function."""

    def test_valid_uuid(self):
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = ConstrainedUUID(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_invalid_uuid(self):
        with pytest.raises(
            ValidationError, match="Arg value should be a valid UUID string"
        ):
            ConstrainedUUID("not-a-uuid")


class TestConstrainedDatetime:
    """Test ConstrainedDatetime function."""

    def test_valid_datetime_with_format(self):
        result = ConstrainedDatetime("2023-01-15 10:30:00", fmt="%Y-%m-%d %H:%M:%S")
        assert isinstance(result, datetime)
        assert result.year == 2023

    def test_valid_datetime_without_format(self):
        result = ConstrainedDatetime("2023-01-15")
        assert isinstance(result, datetime)

    def test_date_type(self):
        result = ConstrainedDatetime("2023-01-15", which=date)
        assert isinstance(result, date)
        assert not isinstance(result, datetime)

    def test_time_type(self):
        result = ConstrainedDatetime("10:30:00", which=time)
        assert isinstance(result, time)

    def test_from_constraint_valid(self):
        min_date = datetime(2023, 1, 1)
        result = ConstrainedDatetime("2023-06-15", from_=min_date)
        assert result >= min_date

    def test_from_constraint_invalid(self):
        min_date = datetime(2023, 1, 1)
        with pytest.raises(ValidationError, match="Datetime value must be on or after"):
            ConstrainedDatetime("2022-06-15", from_=min_date)

    def test_to_constraint_valid(self):
        max_date = datetime(2023, 12, 31)
        result = ConstrainedDatetime("2023-06-15", to_=max_date)
        assert result <= max_date

    def test_to_constraint_invalid(self):
        max_date = datetime(2023, 12, 31)
        with pytest.raises(
            ValidationError, match="Datetime value must be on or before"
        ):
            ConstrainedDatetime("2024-06-15", to_=max_date)

    def test_invalid_datetime_string(self):
        with pytest.raises(
            ValidationError, match="Arg value should be a valid datetime string"
        ):
            ConstrainedDatetime("not-a-date")

    def test_invalid_format(self):
        with pytest.raises(
            ValidationError, match="Arg value should be a valid datetime string"
        ):
            ConstrainedDatetime("2023-01-15", fmt="%d/%m/%Y")


class TestConstrainedWrappers:
    """Test the wrapper functions for datetime constraints."""

    def test_constrained_date(self):
        result = constrained_date("2023-01-15")
        assert isinstance(result, date)
        assert result.year == 2023

    def test_constrained_time(self):
        result = constrained_time("10:30:00")
        assert isinstance(result, time)
        assert result.hour == 10

    def test_constrained_datetime(self):
        result = constrained_datetime("2023-01-15 10:30:00")
        assert isinstance(result, datetime)


class TestConstrainedJson:
    """Test JSON constraint functions."""

    def test_constrained_json_valid(self):
        result = constrained_json('{"key": "value", "number": 42}')
        assert result == {"key": "value", "number": 42}

    def test_constrained_json_invalid(self):
        with pytest.raises(ValidationError, match="Invalid JSON"):
            constrained_json("not-json")

    def test_constrained_bytejson_valid(self):
        result = constrained_bytejson(b'{"key": "value", "number": 42}')
        assert result == {"key": "value", "number": 42}

    def test_constrained_bytejson_invalid(self):
        with pytest.raises(ValidationError, match="Invalid JSON"):
            constrained_bytejson(b"not-json")


class TestExtractType:
    """Test extract_type function."""

    def test_extract_regular_type(self):
        assert extract_type(str) is str
        assert extract_type(int) is int


class TestFuncArgValidator:
    """Test func_arg_validator function."""

    def test_known_conversions(self):
        assert func_arg_validator(str, date) == constrained_date
        assert func_arg_validator(str, time) == constrained_time
        assert func_arg_validator(str, datetime) == constrained_datetime
        assert func_arg_validator(str, dict) == constrained_json
        assert func_arg_validator(bytes, dict) == constrained_bytejson

    def test_unknown_conversion(self):
        assert func_arg_validator(str, int) is None
        assert func_arg_validator(int, str) is None


class TestGetValidator:
    """Test get_validator function."""

    def test_get_existing_validator(self):
        validator = get_validator(str, date)
        assert validator == constrained_date

    def test_get_none_validator(self):
        validator = get_validator(list, set)
        assert validator is None


class TestValidatorCheck:
    """Test validator_check function."""

    def test_has_validate_true(self):
        mock_inj = MagicMock(spec=ModelFieldInject)
        mock_inj.has_validate = True
        assert validator_check(str, date) is True

    def test_has_validate_false_with_validator(self):
        mock_inj = MagicMock(spec=ModelFieldInject)
        mock_inj.has_validate = False
        # When has_validate is False but a validator exists, returns True
        assert validator_check(str, date) is True

    def test_both_conditions_false(self):
        # To get False, we need has_validate=True AND no validator exists
        mock_inj = MagicMock(spec=ModelFieldInject)
        mock_inj.has_validate = True
        # This should return False because has_validate=True but no validator for list->set
        result = get_validator(list, set)
        if result is None:
            # The logic is: if not has_validate or bool(get_validator(...))
            # With has_validate=True and no validator, returns False
            assert validator_check(list, set) is False


class TestNonPydanticFallbacks:
    """Test the non-Pydantic fallback implementations."""

    def test_constrained_str_fallback(self):
        result = ConstrainedStr("hello", min_length=3, max_length=10)
        assert result == "hello"

        with pytest.raises(ValidationError):
            ConstrainedStr("hi", min_length=3)

    def test_constrained_num_fallback(self):
        result = ConstrainedNumber(15, gt=10, lt=20)
        assert result == 15

        with pytest.raises(ValidationError):
            ConstrainedNumber(5, gt=10)

    def test_constrained_list_fallback(self):
        result = base_constrained_list([1, 2, 3], min_length=2, max_length=5)
        assert result == [1, 2, 3]

        with pytest.raises(ValidationError, match="should have at least 5"):
            base_constrained_list([1, 2], min_length=5)

        with pytest.raises(ValidationError, match="should have at most 2"):
            base_constrained_list([1, 2, 3], max_length=2)

    def test_constrained_dict_fallback(self):
        result = base_constrained_dict({"a": 1, "b": 2}, min_length=1, max_length=3)
        assert result == {"a": 1, "b": 2}

        with pytest.raises(ValidationError):
            base_constrained_dict({"a": 1}, min_length=3)

    def test_constrained_uuid_fallback(self):
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = ConstrainedUUID(uuid_str)
        assert isinstance(result, UUID)


class TestPydanticIntegration:
    """Test Pydantic integration when available."""

    def test_pydantic_imports(self):
        """Test that Pydantic-specific imports work."""
        try:
            # If we get here, Pydantic is installed
            from ctxinject.validation import constrained_email

            assert constrained_email is not None
        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_string_validation(self):
        """Test Pydantic string validation with constraints."""
        try:
            result = constrained_str(
                "hello", min_length=3, max_length=10, pattern=r"^h.*"
            )
            assert result == "hello"

            # Test invalid cases
            with pytest.raises(Exception):  # Pydantic validation error
                constrained_str("hi", min_length=3)

            with pytest.raises(Exception):
                constrained_str("hello world", max_length=5)

            with pytest.raises(Exception):
                constrained_str("world", pattern=r"^h.*")
        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_number_validation(self):
        """Test Pydantic number validation."""
        try:
            result = constrained_num(15, gt=10, lt=20, multiple_of=5)
            assert result == 15

            with pytest.raises(Exception):
                constrained_num(5, gt=10)

            with pytest.raises(Exception):
                constrained_num(25, lt=20)
        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_list_validation(self):
        """Test Pydantic list validation."""
        try:
            result = constrained_list([1, 2, 3], min_length=2, max_length=5)
            assert result == [1, 2, 3]

            with pytest.raises(Exception):
                constrained_list([1], min_length=2)

            with pytest.raises(Exception):
                constrained_list([1, 2, 3, 4, 5, 6], max_length=5)
        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_dict_validation(self):
        """Test Pydantic dict validation."""
        try:
            result = constrained_dict({"a": 1, "b": 2}, min_length=1, max_length=3)
            assert result == {"a": 1, "b": 2}

            with pytest.raises(Exception):
                constrained_dict({}, min_length=1)

            with pytest.raises(Exception):
                constrained_dict({"a": 1, "b": 2, "c": 3, "d": 4}, max_length=3)
        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_email_validation(self):
        """Test Pydantic email validation."""
        try:
            from ctxinject.validation import constrained_email

            result = constrained_email("test@example.com")
            assert result == "test@example.com"

            with pytest.raises(Exception):  # Pydantic validation error
                constrained_email("not-an-email")

            with pytest.raises(Exception):
                constrained_email("@example.com")

            with pytest.raises(Exception):
                constrained_email("test@")
        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_url_validation(self):
        """Test Pydantic URL validation."""
        try:
            from ctxinject.validation import constrained_any_url, constrained_http_url

            # HTTP URL validation
            result = constrained_http_url("https://example.com")
            assert str(result) == "https://example.com/"

            with pytest.raises(Exception):
                constrained_http_url("not-a-url")

            with pytest.raises(Exception):
                constrained_http_url("ftp://example.com")  # Not HTTP/HTTPS

            # Any URL validation
            result = constrained_any_url("ftp://example.com")
            assert "example.com" in str(result)

        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_ip_validation(self):
        """Test Pydantic IP address validation."""
        try:
            from ctxinject.validation import constrained_ip_any

            # Valid IPv4
            result = constrained_ip_any("192.168.1.1")
            assert str(result) == "192.168.1.1"

            # Valid IPv6
            result = constrained_ip_any("2001:db8::8a2e:370:7334")
            assert "2001" in str(result)

            with pytest.raises(Exception):
                constrained_ip_any("not-an-ip")

            with pytest.raises(Exception):
                constrained_ip_any("999.999.999.999")  # Invalid IP
        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_uuid_validation(self):
        """Test Pydantic UUID validation."""
        try:
            uuid_str = "550e8400-e29b-41d4-a716-446655440000"
            result = constrained_uuid(uuid_str)
            assert isinstance(result, UUID)
            assert str(result) == uuid_str

            with pytest.raises(Exception):
                constrained_uuid("not-a-uuid")
        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_model_parsing(self):
        """Test Pydantic model JSON parsing."""
        try:
            from pydantic import BaseModel

            from ctxinject.validation import parse_json_model

            class TestModel(BaseModel):
                name: str
                age: int
                email: str = "default@example.com"

            # Test valid JSON parsing
            result = parse_json_model('{"name": "John", "age": 30}', TestModel)
            assert result.name == "John"
            assert result.age == 30
            assert result.email == "default@example.com"

            # Test with all fields
            result = parse_json_model(
                '{"name": "Jane", "age": 25, "email": "jane@example.com"}', TestModel
            )
            assert result.email == "jane@example.com"

            # Test bytes input
            result = parse_json_model(b'{"name": "Bob", "age": 40}', TestModel)
            assert result.name == "Bob"

            # Test invalid JSON
            with pytest.raises(Exception):
                parse_json_model("not-json", TestModel)

            # Test missing required field
            with pytest.raises(Exception):
                parse_json_model('{"age": 30}', TestModel)  # Missing 'name'

            # Test invalid type
            with pytest.raises(Exception):
                parse_json_model('{"name": "John", "age": "thirty"}', TestModel)

        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_get_pydantic_validator(self):
        """Test the get_pydantic_validator function."""
        try:
            from pydantic import BaseModel

            from ctxinject.validation import get_pydantic_validator

            class TestModel(BaseModel):
                value: str

            class NotABaseModel:
                value: str

            # Should return parse_json_model for BaseModel with str/bytes
            validator = get_pydantic_validator(str, TestModel)
            assert validator is not None
            # assert validator == parse_json_model

            validator = get_pydantic_validator(bytes, TestModel)
            assert validator is not None
            # assert validator == parse_json_model

            # Should return None for non-BaseModel (line 353 test)
            validator = get_pydantic_validator(str, dict)
            assert validator is None

            validator = get_pydantic_validator(str, NotABaseModel)
            assert validator is None

            # Should return None for BaseModel with wrong source type
            validator = get_pydantic_validator(int, TestModel)
            assert validator is None

            validator = get_pydantic_validator(list, TestModel)
            assert validator is None

        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_in_arg_proc(self):
        """Test that Pydantic validators are registered in arg_proc."""
        try:
            from pydantic import AnyUrl, EmailStr, HttpUrl, IPvAnyAddress

            from ctxinject.validation import arg_proc

            # Check that Pydantic types are registered
            assert (str, EmailStr) in arg_proc
            assert (str, HttpUrl) in arg_proc
            assert (str, AnyUrl) in arg_proc
            assert (str, IPvAnyAddress) in arg_proc

        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_validator_in_validators_list(self):
        """Test that get_pydantic_validator is in validators list."""
        try:
            from ctxinject.validation import get_pydantic_validator, validators

            assert get_pydantic_validator in validators

        except ImportError:
            pytest.skip("Pydantic not installed")

    def test_pydantic_caching(self):
        """Test that Pydantic adapters are cached properly."""
        try:
            from ctxinject.validation import get_number_adapter, get_string_adapter

            # Test string adapter caching
            adapter1 = get_string_adapter(3, 10, "^test")
            adapter2 = get_string_adapter(3, 10, "^test")
            assert adapter1 is adapter2  # Same object due to caching

            # Different parameters should return different adapter
            adapter3 = get_string_adapter(4, 10, "^test")
            assert adapter1 is not adapter3

            # Test number adapter caching
            num_adapter1 = get_number_adapter(0, None, 100, None, 5)
            num_adapter2 = get_number_adapter(0, None, 100, None, 5)
            assert num_adapter1 is num_adapter2

        except ImportError:
            pytest.skip("Pydantic not installed")


class TestArgProcRegistry:
    """Test the arg_proc registry."""

    def test_basic_conversions_registered(self):
        assert (str, date) in arg_proc
        assert (str, time) in arg_proc
        assert (str, datetime) in arg_proc
        assert (str, dict) in arg_proc
        assert (bytes, dict) in arg_proc
        assert (str, str) in arg_proc
        assert (int, int) in arg_proc
        assert (float, float) in arg_proc
        assert (list, list) in arg_proc
        assert (dict, dict) in arg_proc
        assert (str, UUID) in arg_proc

    def test_apply_conversions(self):
        # Test each registered conversion
        assert arg_proc[(str, date)]("2023-01-15") == date(2023, 1, 15)
        assert arg_proc[(str, dict)]('{"key": "value"}') == {"key": "value"}
        assert arg_proc[(str, str)]("hello", min_length=3) == "hello"
        assert arg_proc[(int, int)](5, gt=0) == 5


class TestValidatorsRegistry:
    """Test the validators registry."""

    def test_validators_list_populated(self):
        assert len(validators) >= 1
        assert func_arg_validator in validators


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_constrained_datetime_parser_error(self):
        # Force a ParserError by mocking parsedate
        with patch(
            "ctxinject.validation.parsedate", side_effect=ParserError("Parse error")
        ):
            with pytest.raises(
                ValidationError, match="Arg value should be a valid datetime string"
            ):
                ConstrainedDatetime("any-string", fmt=None)

    def test_constrained_datetime_type_error(self):
        # Since ConstrainedDatetime has a fallback to parsedate,
        # we need to test a case where both strptime and parsedate fail
        with pytest.raises(
            ValidationError, match="Arg value should be a valid datetime string"
        ):
            # This will fail in strptime due to bad format, then fail in parsedate
            ConstrainedDatetime("not-a-valid-date-at-all-###", fmt="%Y-%m-%d")

    def test_constrained_datetime_strptime_type_error(self):
        # Test TypeError in strptime (e.g., fmt is not a string)
        # This will raise TypeError in strptime, then try parsedate
        with patch(
            "ctxinject.validation.parsedate", side_effect=ParserError("Parse error")
        ):
            with pytest.raises(
                ValidationError, match="Arg value should be a valid datetime string"
            ):
                # Pass an integer as fmt to trigger TypeError in strptime
                ConstrainedDatetime("2023-01-15", fmt=123)

    def test_extract_type_non_type(self):
        # Test with mock object that has get_origin
        mock_type = MagicMock()
        mock_type.__class__ = MagicMock()
        mock_type.__class__.__name__ = "GenericAlias"

        with patch("ctxinject.validation.get_equivalent_origin", return_value=list):
            result = extract_type(mock_type)
            assert result is list


# Integration tests
class TestIntegration:
    """Integration tests combining multiple components."""

    def test_validator_pipeline(self):
        # Test complete validator pipeline
        validator = get_validator(str, datetime)
        assert validator is not None

        result = validator("2023-01-15 10:30:00")
        assert isinstance(result, datetime)

    def test_model_field_inject_validation(self):
        # Should return True because str->date has a validator
        assert validator_check(str, date) is True

        # Now has_validate is True, and if no validator exists for list->set, it should return False
        assert validator_check(list, set) is False

        # Test with has_validate = True and existing validator
        assert validator_check(str, date) is True


class TestImportFallbackSimple:
    """Simple test for ImportError fallback using subprocess."""

    def test_fallback_with_subprocess(self):
        """Test the ImportError fallback by running code in a subprocess without pydantic."""
        import subprocess

        # Python code to run in subprocess
        test_code = """
import sys
# Block pydantic import
sys.modules['pydantic'] = None

# Now import validation - should use fallback
try:
    import ctxinject.validation as val
    
    # Test that fallback functions work
    assert val.constrained_str("test", min_length=2) == "test"
    assert val.constrained_num(5, gt=0) == 5
    assert val.constrained_list([1, 2], min_length=1) == [1, 2]
    
    # Verify no Pydantic stuff
    assert not hasattr(val, 'IS_PYDANTIC_V2')
    assert len(val.validators) == 1
    
    print("FALLBACK_SUCCESS")
except Exception as e:
    print(f"FALLBACK_ERROR: {e}")
    sys.exit(1)
"""

        # Run in subprocess
        result = subprocess.run(
            [sys.executable, "-c", test_code],
            capture_output=True,
            text=True,
            cwd=".",  # Make sure we're in the right directory
        )

        # Check the subprocess succeeded
        assert (
            "FALLBACK_SUCCESS" in result.stdout
        ), f"Subprocess failed: {result.stderr}"
        assert result.returncode == 0


# Run with: pytest test_validation.py -v --cov=ctxinject.validation --cov-report=term-missing


class TestImportFallback:
    """Test the ImportError fallback when Pydantic is not available."""

    def test_import_error_fallback(self):
        """Test the except ImportError block (lines 357-409)."""
        from unittest.mock import patch

        # Save original state
        validation_module = sys.modules.get("ctxinject.validation")

        try:
            # Remove validation module to force reimport
            if "ctxinject.validation" in sys.modules:
                del sys.modules["ctxinject.validation"]

            # Mock the pydantic import to raise ImportError
            with patch.dict("sys.modules", {"pydantic": None}):
                # This will trigger the ImportError when trying to import from pydantic
                import ctxinject.validation as val_fallback

                # The fallback implementations should be defined
                # These use the Constrained* functions that are defined outside try/except
                assert hasattr(val_fallback, "constrained_str")
                assert hasattr(val_fallback, "constrained_num")
                assert hasattr(val_fallback, "constrained_list")
                assert hasattr(val_fallback, "constrained_dict")
                assert hasattr(val_fallback, "constrained_uuid")

                # Pydantic-specific items should NOT exist
                assert not hasattr(val_fallback, "get_string_adapter")
                assert not hasattr(val_fallback, "get_number_adapter")
                assert not hasattr(val_fallback, "constrained_email")
                assert not hasattr(val_fallback, "IS_PYDANTIC_V2")

                # Test the fallback functions (they use the same Constrained* functions)
                result = val_fallback.constrained_str(
                    "hello", min_length=3, max_length=10
                )
                assert result == "hello"

                result = val_fallback.constrained_num(15, gt=10, lt=20)
                assert result == 15

                result = val_fallback.constrained_list([1, 2, 3], min_length=2)
                assert result == [1, 2, 3]
                with pytest.raises(val_fallback.ValidationError):
                    result = val_fallback.constrained_list([1], min_length=2)
                with pytest.raises(val_fallback.ValidationError):
                    result = val_fallback.constrained_list([1, 2, 3], max_length=2)

                result = val_fallback.constrained_dict({"a": 1, "b": 2}, max_length=3)
                assert result == {"a": 1, "b": 2}

                uuid_str = "550e8400-e29b-41d4-a716-446655440000"
                result = val_fallback.constrained_uuid(uuid_str)
                assert str(result) == uuid_str

                # Check arg_proc doesn't have Pydantic types
                assert (str, str) in val_fallback.arg_proc
                assert (int, int) in val_fallback.arg_proc
                assert (
                    len(
                        [
                            k
                            for k in val_fallback.arg_proc.keys()
                            if "EmailStr" in str(k)
                        ]
                    )
                    == 0
                )

                # Check validators list only has func_arg_validator
                assert len(val_fallback.validators) == 1
                assert val_fallback.func_arg_validator in val_fallback.validators

        finally:
            # Restore original module
            if validation_module:
                sys.modules["ctxinject.validation"] = validation_module

    def test_pydantic_import_line_coverage(self):
        """Additional test to ensure line 353 coverage."""
        try:
            from pydantic import BaseModel

            from ctxinject.validation import get_pydantic_validator

            # Create a class that is NOT a BaseModel to test line 353
            class NotBaseModel:
                def __init__(self):
                    self.value = "test"

            class ActualModel(BaseModel):
                value: str

            # This should hit line 353 and return None (not a BaseModel)
            result = get_pydantic_validator(str, NotBaseModel)
            assert result is None

            # This should pass the check and return parse_json_model
            result = get_pydantic_validator(str, ActualModel)
            assert result is not None

            # Also test with primitive types to ensure line 353 is hit
            result = get_pydantic_validator(str, str)
            assert result is None

            result = get_pydantic_validator(str, int)
            assert result is None

        except ImportError:
            pytest.skip("Pydantic not installed")
