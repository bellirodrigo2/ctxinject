# Contributing to ctxinject

Thank you for your interest in contributing to ctxinject! This document provides guidelines and information for contributors.

## 🚀 Quick Start

### Development Setup

1. **Fork and clone the repository:**
```bash
git clone https://github.com/yourusername/ctxinject.git
cd ctxinject
```

2. **Create a virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install development dependencies:**
```bash
pip install -e ".[dev]"
```

4. **Install pre-commit hooks (optional but recommended):**
```bash
pre-commit install
```

5. **Run tests to ensure everything is working:**
```bash
pytest
```

## 🛠️ Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=ctxinject

# Run specific test file
pytest tests/test_inject.py

# Run tests for specific Python version (with tox)
tox -e py312

# Run all tox environments
tox
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
black ctxinject tests
isort ctxinject tests

# Lint code
ruff check ctxinject tests

# Type checking
mypy ctxinject

# Run all quality checks at once
tox -e lint

# Auto-format code
tox -e format
```

### Testing Your Changes

1. **Write tests** for any new functionality
2. **Ensure all tests pass** across supported Python versions
3. **Add type hints** to all new code
4. **Update documentation** if needed

## 📝 Contributing Guidelines

### Code Style

- **Follow PEP 8** with line length of 88 characters (Black default)
- **Use type hints** for all functions and methods
- **Write descriptive variable names** and function names
- **Add docstrings** for public functions and classes using Google style

Example:
```python
async def inject_dependency(
    func: Callable[..., Any],
    context: Dict[str, Any],
    validate: bool = True
) -> partial[Any]:
    """
    Inject dependencies into a function.
    
    Args:
        func: The function to inject dependencies into
        context: Context containing dependency values
        validate: Whether to validate injected values
        
    Returns:
        A partial function with dependencies injected
        
    Raises:
        UnresolvedInjectableError: If required dependency cannot be resolved
    """
    # Implementation here
```

### Commit Messages

Use clear, descriptive commit messages:

```bash
# Good
git commit -m "Add support for async validators in DependsInject"
git commit -m "Fix circular dependency detection in map_ctx"
git commit -m "Update README with validation examples"

# Avoid
git commit -m "fix bug"
git commit -m "update stuff"
git commit -m "wip"
```

### Pull Request Process

1. **Create a feature branch:**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes** following the guidelines above

3. **Test thoroughly:**
```bash
pytest
tox -e lint
```

4. **Update documentation** if needed

5. **Submit a pull request** with:
   - Clear description of changes
   - Reference to any related issues
   - Screenshots/examples if applicable

## 🐛 Bug Reports

When reporting bugs, please include:

- **Python version** and operating system
- **ctxinject version**
- **Minimal code example** that reproduces the issue
- **Full error traceback**
- **Expected vs actual behavior**

Use this template:

```markdown
## Bug Description
Brief description of the issue

## Environment
- Python: 3.11.0
- ctxinject: 0.1.1
- OS: Ubuntu 22.04

## Reproduction Code
```python
# Minimal example that reproduces the issue
```

## Error Message
```
Full traceback here
```

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened
```

## 💡 Feature Requests

For feature requests, please:

1. **Search existing issues** to avoid duplicates
2. **Describe the use case** clearly
3. **Provide examples** of how the feature would be used
4. **Consider backwards compatibility**

## 🧪 Testing Guidelines

### Test Structure

- Tests are in the `tests/` directory
- Test files follow the pattern `test_*.py`
- Test classes start with `Test`
- Test methods start with `test_`

### Writing Good Tests

```python
import pytest
from ctxinject import inject_args, DependsInject

class TestDependencyInjection:
    """Test dependency injection functionality."""
    
    @pytest.mark.asyncio
    async def test_simple_dependency_injection(self) -> None:
        """Test basic dependency injection works correctly."""
        # Arrange
        def get_value() -> str:
            return "test_value"
            
        async def handler(value: str = DependsInject(get_value)) -> str:
            return value
        
        # Act
        injected = await inject_args(handler, {})
        result = await injected()
        
        # Assert
        assert result == "test_value"
    
    @pytest.mark.asyncio
    async def test_missing_dependency_raises_error(self) -> None:
        """Test that missing dependencies raise appropriate error."""
        async def handler(missing: str) -> str:
            return missing
        
        with pytest.raises(UnresolvedInjectableError):
            await inject_args(handler, {}, allow_incomplete=False)
```

### Test Categories

Use markers to categorize tests:

```python
@pytest.mark.slow
def test_performance_benchmark():
    """Slow performance test."""
    pass

@pytest.mark.integration
def test_full_workflow():
    """Integration test."""
    pass
```

### Async Testing

For async functions, use `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_async_dependency():
    """Test async dependency resolution."""
    async def async_dep() -> str:
        return "async_result"
    
    async def handler(value: str = DependsInject(async_dep)) -> str:
        return value
    
    injected = await inject_args(handler, {})
    result = await injected()
    assert result == "async_result"
```

## 📚 Documentation

### Updating Documentation

- **README.md**: Update examples if adding new features
- **Docstrings**: Add/update for all public APIs
- **Type hints**: Required for all new code
- **Examples**: Add practical examples for new features

### Documentation Style

- Use **Google-style docstrings**
- Include **type hints** in function signatures
- Provide **practical examples** in docstrings
- Keep explanations **clear and concise**

## 🔄 Release Process

(For maintainers)

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with new features/fixes
3. **Create release tag:**
```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```
4. **GitHub Actions** will automatically build and publish to PyPI

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: [bellirodrigo@gmail.com] for private matters

## 🎯 Areas for Contribution

We welcome contributions in these areas:

### High Priority
- **Performance optimizations**
- **Additional constraint validators**
- **Better error messages**
- **Documentation improvements**

### Medium Priority
- **Examples and tutorials**
- **Integration with other frameworks**
- **Developer tooling improvements**

### Low Priority
- **Code style improvements**
- **Test coverage improvements**
- **Minor feature additions**

## 🏆 Recognition

Contributors will be acknowledged in:
- **README.md** contributors section
- **CHANGELOG.md** release notes
- **GitHub contributors** page

Thank you for contributing to ctxinject! 🚀