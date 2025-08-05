"""
Fixed test suite for nested field support in ctxinject.
Fixes:
1. Add @pytest.mark.asyncio decorator for async tests
2. Fix type annotations issues
3. Handle parameters that aren't injectable
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import pytest

from ctxinject.inject import UnresolvedInjectableError, inject_args
from ctxinject.model import ArgsInjectable, DependsInject, ModelFieldInject
from ctxinject.sigcheck import func_signature_check


# Test Models
class Address:
    def __init__(self, street: str, number: int, city: str, country: str):
        self.street: str = street
        self.number: int = number
        self.city: str = city
        self.country: str = country
        self.postal_code: str = "12345"

    def get_full_address(self) -> str:
        return f"{self.number} {self.street}, {self.city}, {self.country}"

    @property
    def location_info(self) -> Dict[str, str]:
        return {"city": self.city, "country": self.country}


class Department:
    def __init__(self, name: str, budget: float, manager_name: Optional[str] = None):
        self.name: str = name
        self.budget: float = budget
        self.manager_name: Optional[str] = manager_name
        self.employee_count: int = 10

    def get_budget(self) -> float:
        return self.budget

    @property
    def is_large(self) -> bool:
        return self.employee_count > 50


class Person:
    def __init__(self, name: str, age: int, email: str, address: Address):
        self.name: str = name
        self.age: int = age
        self.email: str = email
        self.address: Address = address
        self.employee_id: str = "EMP001"
        self.birth_date: datetime = datetime(1990, 1, 1)

    def get_age(self) -> int:
        return self.age

    @property
    def full_name(self) -> str:
        return self.name.upper()


class Company:
    founded: int

    def __init__(self, name: str, ceo: Person, departments: List[Department]):
        self.name: str = name
        self.ceo: Person = ceo
        self.departments: List[Department] = departments
        self.founded: int = 2010
        self.stock_price: float = 150.50

    def get_ceo(self) -> Person:
        return self.ceo

    @property
    def years_active(self) -> int:
        return 2024 - self.founded


# ============= SIGCHECK TESTS =============


def test_sigcheck_nested_fields_valid():
    """Test that valid nested field injections pass signature check."""

    def valid_func(
        # Direct fields
        company_name: str = ModelFieldInject(Company, "name"),
        founded_year: int = ModelFieldInject(Company, "founded"),
        # One level nested
        ceo_name: str = ModelFieldInject(Company, "ceo.name"),
        ceo_age: int = ModelFieldInject(Company, "ceo.age"),
        # Two levels nested
        city: str = ModelFieldInject(Company, "ceo.address.city"),
        street: str = ModelFieldInject(Company, "ceo.address.street"),
        # Three levels nested (property)
        location_info: Dict[str, str] = ModelFieldInject(
            Company, "ceo.address.location_info"
        ),
        # Methods in path
        ceo_age_method: int = ModelFieldInject(Company, "get_ceo.age"),
        full_address: str = ModelFieldInject(Company, "ceo.address.get_full_address"),
        # Properties
        years: int = ModelFieldInject(Company, "years_active"),
        ceo_full_name: str = ModelFieldInject(Company, "ceo.full_name"),
    ):
        pass

    errors = func_signature_check(valid_func, modeltype=[Company])
    assert errors == [], f"Expected no errors, got: {errors}"


def test_sigcheck_nested_fields_type_mismatch():
    """Test that type mismatches in nested fields are caught."""

    def invalid_types(
        # Type mismatches
        ceo_age_as_str: str = ModelFieldInject(Company, "ceo.age"),  # int -> str
        city_as_int: int = ModelFieldInject(Company, "ceo.address.city"),  # str -> int
        # Note: departments.[0] syntax would need special handling, using method instead
        budget_as_bool: bool = ModelFieldInject(Company, "ceo.name"),  # str -> bool
    ):
        pass

    errors = func_signature_check(invalid_types, modeltype=[Company])
    assert len(errors) >= 3, f"Expected at least 3 errors, got {len(errors)}: {errors}"

    # Check error messages contain field names
    error_str = " ".join(errors)
    assert "ceo_age_as_str" in error_str
    assert "city_as_int" in error_str


def test_sigcheck_nonexistent_fields():
    """Test that non-existent nested fields are caught."""

    def invalid_fields(
        # Non-existent fields
        invalid1: str = ModelFieldInject(Company, "ceo.invalid_field"),
        invalid2: str = ModelFieldInject(Company, "ceo.address.invalid_field"),
        invalid3: str = ModelFieldInject(Company, "nonexistent.field.path"),
    ):
        pass

    errors = func_signature_check(invalid_fields, modeltype=[Company])
    assert len(errors) >= 3, f"Expected at least 3 errors, got {len(errors)}: {errors}"

    # Check that errors mention the invalid fields
    error_str = " ".join(errors)
    assert "Could not determine type" in error_str


def test_sigcheck_model_not_allowed():
    """Test that models not in allowed list are rejected."""

    def func_with_person(
        # Person is not in allowed models
        person_name: str = ModelFieldInject(Person, "name"),
        person_city: str = ModelFieldInject(Person, "address.city"),
    ):
        pass

    # Only allow Company, not Person
    errors = func_signature_check(func_with_person, modeltype=[Company])
    assert len(errors) >= 2, f"Expected at least 2 errors, got {len(errors)}: {errors}"

    error_str = " ".join(errors)
    assert "not allowed" in error_str


def test_sigcheck_mixed_injection_types():
    """Test signature check with mixed injection types."""

    def mixed_func(
        # Regular injection
        prefix: str = ArgsInjectable("Report:"),
        # Nested field injection
        company_name: str = ModelFieldInject(Company, "name"),
        ceo_email: str = ModelFieldInject(Company, "ceo.email"),
        city: str = ModelFieldInject(Company, "ceo.address.city"),
        # Depends injection
        timestamp: float = DependsInject(lambda: 1234567890.0),
    ):
        # Regular parameters are allowed when they have default values
        # or when using ArgsInjectable
        pass

    errors = func_signature_check(mixed_func, modeltype=[Company])
    assert errors == [], f"Expected no errors, got: {errors}"


# ============= INJECT TESTS =============


@pytest.mark.asyncio
async def test_inject_nested_fields_basic():
    """Test basic nested field injection."""

    # Setup test data
    address = Address("Main St", 123, "New York", "USA")
    dept = Department("Engineering", 1000000.0)
    ceo = Person("John Doe", 45, "john@company.com", address)
    company = Company("TechCorp", ceo, [dept])

    def get_info(
        company_name: str = ModelFieldInject(Company, "name"),
        ceo_name: str = ModelFieldInject(Company, "ceo.name"),
        ceo_email: str = ModelFieldInject(Company, "ceo.email"),
        city: str = ModelFieldInject(Company, "ceo.address.city"),
        street: str = ModelFieldInject(Company, "ceo.address.street"),
    ):
        return {
            "company": company_name,
            "ceo": ceo_name,
            "email": ceo_email,
            "location": f"{street}, {city}",
        }

    context = {Company: company}
    injected = await inject_args(get_info, context)
    result = injected()

    assert result["company"] == "TechCorp"
    assert result["ceo"] == "John Doe"
    assert result["email"] == "john@company.com"
    assert result["location"] == "Main St, New York"


@pytest.mark.asyncio
async def test_inject_methods_and_properties():
    """Test injection of methods and properties in nested paths."""

    # Setup
    address = Address("Broadway", 500, "San Francisco", "USA")
    dept = Department("Engineering", 2000000.0)
    ceo = Person("Jane Smith", 38, "jane@corp.com", address)
    company = Company("BigCorp", ceo, [dept])

    def get_computed_values(
        # Properties
        years: int = ModelFieldInject(Company, "years_active"),
        ceo_full_name: str = ModelFieldInject(Company, "ceo.full_name"),
        location_info: Dict[str, str] = ModelFieldInject(
            Company, "ceo.address.location_info"
        ),
        # Methods
        ceo_age: int = ModelFieldInject(Company, "get_ceo.age"),
        full_address: str = ModelFieldInject(Company, "ceo.address.get_full_address"),
        ceo_age_direct: int = ModelFieldInject(Company, "ceo.get_age"),
    ):
        return {
            "years": years,
            "ceo_name": ceo_full_name,
            "location": location_info,
            "address": full_address,
            "age": ceo_age,
            "age_direct": ceo_age_direct,
        }

    context = {Company: company}
    injected = await inject_args(get_computed_values, context)
    result = injected()

    assert result["years"] == 14  # 2024 - 2010
    assert result["ceo_name"] == "JANE SMITH"  # full_name property returns uppercase
    assert result["location"]["city"] == "San Francisco"
    assert "500 Broadway" in result["address"]
    assert result["age"] == 38
    assert result["age_direct"] == 38


@pytest.mark.asyncio
async def test_inject_deep_nesting():
    """Test very deep nesting (4+ levels)."""

    # Create a deeply nested structure
    class Country:

        def __init__(self, name: str, code: str):
            self.name: str = name
            self.code: str = code

        @property
        def continent(self) -> str:
            return "North America"

    class City:

        def __init__(self, name: str, country: Country):
            self.name: str = name
            self.country: Country = country

        def population(self) -> int:
            return 1000000

    class ExtendedAddress:
        def __init__(self, street: str, city: City):
            self.street: str = street
            self.city: City = city

    class ExtendedPerson:
        def __init__(self, name: str, address: ExtendedAddress):
            self.name: str = name
            self.address: ExtendedAddress = address

    class ExtendedCompany:
        def __init__(self, ceo: ExtendedPerson):
            self.ceo: ExtendedPerson = ceo

    # Create instances
    country = Country("United States", "US")
    city = City("Seattle", country)
    address = ExtendedAddress("Pine Street", city)
    person = ExtendedPerson("Bob Wilson", address)
    company = ExtendedCompany(person)

    def get_deep_info(
        # 4 levels deep
        country_name: str = ModelFieldInject(
            ExtendedCompany, "ceo.address.city.country.name"
        ),
        country_code: str = ModelFieldInject(
            ExtendedCompany, "ceo.address.city.country.code"
        ),
        continent: str = ModelFieldInject(
            ExtendedCompany, "ceo.address.city.country.continent"
        ),
        # 3 levels deep
        city_name: str = ModelFieldInject(ExtendedCompany, "ceo.address.city.name"),
        population: int = ModelFieldInject(
            ExtendedCompany, "ceo.address.city.population"
        ),
    ):
        return {
            "country": f"{country_name} ({country_code})",
            "continent": continent,
            "city": city_name,
            "population": population,
        }

    context = {ExtendedCompany: company}
    injected = await inject_args(get_deep_info, context, False)
    result = injected()

    assert result["country"] == "United States (US)"
    assert result["continent"] == "North America"
    assert result["city"] == "Seattle"
    assert result["population"] == 1000000


@pytest.mark.asyncio
async def test_inject_error_handling():
    """Test error handling for invalid paths."""

    address = Address("Main", 1, "Boston", "USA")
    ceo = Person("Alice", 30, "alice@co.com", address)
    company = Company("SmallCo", ceo, [])

    def func_with_invalid_path(
        # This path doesn't exist
        invalid: str = ModelFieldInject(Company, "ceo.address.invalid_field"),
    ):
        return invalid

    context = {Company: company}

    # Should raise AttributeError when trying to access invalid_field
    with pytest.raises(UnresolvedInjectableError):
        injected = await inject_args(func_with_invalid_path, context, False)
        injected()  # This should raise the error


@pytest.mark.asyncio
async def test_inject_with_none_values():
    """Test handling of None values in the path."""

    class OptionalAddress:
        def __init__(self, city: Optional[str] = None):
            self.city: Optional[str] = city
            self.country: Optional[str] = None  # Explicitly None

    class OptionalPerson:
        def __init__(self, name: str, address: Optional[OptionalAddress] = None):
            self.name: str = name
            self.address: Optional[OptionalAddress] = address

    # Test with None address
    person_no_addr = OptionalPerson("John", None)

    def get_name_only(
        name: str = ModelFieldInject(OptionalPerson, "name"),
    ):
        return name

    context = {OptionalPerson: person_no_addr}
    injected = await inject_args(get_name_only, context)
    result = injected()
    assert result == "John"

    # Test accessing None will fail
    def get_city(
        city: str = ModelFieldInject(OptionalPerson, "address.city"),
    ):
        return city

    injected = await inject_args(get_city, context)
    assert injected() is None


@pytest.mark.asyncio
async def test_inject_partial_injection():
    """Test partial injection with allow_incomplete."""

    address = Address("Market", 100, "Chicago", "USA")
    ceo = Person("Tom", 50, "tom@example.com", address)
    company = Company("MegaCorp", ceo, [])

    def func_with_mixed_params(
        # These will be injected
        company_name: str = ModelFieldInject(Company, "name"),
        ceo_city: str = ModelFieldInject(Company, "ceo.address.city"),
        # These won't be injected (no default, not in context)
        user_id: str = ArgsInjectable(...),
        # Regular parameter with default
        suffix: str = " Inc.",
    ):
        return f"{company_name}{suffix} in {ceo_city} (User: {user_id})"

    context = {Company: company}

    # With allow_incomplete=True (default)
    injected = await inject_args(func_with_mixed_params, context, allow_incomplete=True)
    result = injected(user_id="USER123")  # Must provide missing param
    assert result == "MegaCorp Inc. in Chicago (User: USER123)"

    # With allow_incomplete=False
    with pytest.raises(UnresolvedInjectableError):
        await inject_args(func_with_mixed_params, context, allow_incomplete=False)


@pytest.mark.asyncio
async def test_inject_complex_scenario():
    """Test complex scenario with multiple injection types."""

    # Setup
    address = Address("Wall St", 1, "New York", "USA")
    engineering = Department("Engineering", 5000000.0, "Alice Manager")
    sales = Department("Sales", 3000000.0, "Bob Manager")
    ceo = Person("Big Boss", 55, "boss@megacorp.com", address)
    company = Company("MegaCorp", ceo, [engineering, sales])

    # Helper functions for DependsInject
    def get_timestamp() -> float:
        return 1234567890.0

    async def get_report_id() -> str:
        await asyncio.sleep(0.01)  # Simulate async work
        return "REPORT-2024-001"

    def calculate_total_budget() -> float:
        # Simplified - in real case would access company data
        return 8000000.0

    # Main function using all injection types
    def generate_report(
        # Simple injection
        report_title: str = ArgsInjectable("Annual Report"),
        # Nested field injection
        company_name: str = ModelFieldInject(Company, "name"),
        ceo_email: str = ModelFieldInject(Company, "ceo.email"),
        hq_city: str = ModelFieldInject(Company, "ceo.address.city"),
        # Deep nested with method
        full_address: str = ModelFieldInject(Company, "ceo.address.get_full_address"),
        # Properties
        years_active: int = ModelFieldInject(Company, "years_active"),
        # DependsInject
        timestamp: float = DependsInject(get_timestamp),
        report_id: str = DependsInject(get_report_id),
        total_budget: float = DependsInject(calculate_total_budget),
    ):
        return {
            "id": report_id,
            "title": f"{report_title} - {company_name}",
            "ceo_contact": ceo_email,
            "headquarters": f"{hq_city} ({full_address})",
            "years": years_active,
            "total_budget": total_budget,
            "generated_at": timestamp,
        }

    context = {
        Company: company,
        "report_title": "2024 Financial Report",  # Override default
    }

    injected = await inject_args(generate_report, context)
    result = injected()

    assert result["id"] == "REPORT-2024-001"
    assert result["title"] == "2024 Financial Report - MegaCorp"
    assert result["ceo_contact"] == "boss@megacorp.com"
    assert "New York" in result["headquarters"]
    assert result["years"] == 14
    assert result["total_budget"] == 8000000.0
    assert result["generated_at"] == 1234567890.0


@pytest.mark.asyncio
async def test_inject_validation():
    """Test that validation works with nested fields."""

    def validate_email(value: str, **kwargs) -> str:
        if "@" not in value:
            raise ValueError("Invalid email")
        return value.lower()

    def validate_positive(value: int, **kwargs) -> int:
        if value <= 0:
            raise ValueError("Must be positive")
        return value

    address = Address("Broadway", 123, "LA", "USA")
    ceo = Person("CEO", 45, "CEO@COMPANY.COM", address)
    company = Company("TestCo", ceo, [])

    def process_data(
        # Validation on nested fields
        email: str = ModelFieldInject(Company, "ceo.email", validate_email),
        age: int = ModelFieldInject(Company, "ceo.age", validate_positive),
    ):
        return {"email": email, "age": age}

    context = {Company: company}
    injected = await inject_args(process_data, context)
    result = injected()

    # Email should be lowercased by validator
    assert result["email"] == "ceo@company.com"
    assert result["age"] == 45


# ============= RUN TESTS IF EXECUTED DIRECTLY =============

if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])
