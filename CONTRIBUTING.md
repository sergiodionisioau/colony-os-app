# Contributing to COE Kernel

Thank you for your interest in contributing to COE Kernel! This document provides guidelines and instructions for contributing.

## 🎯 Code of Conduct

This project and everyone participating in it is governed by our commitment to:
- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Prioritize security and reliability

## 🚀 Getting Started

### Development Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/coe-kernel.git
cd coe-kernel

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r coe-kernel/requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## 📝 Contribution Guidelines

### Reporting Bugs

When reporting bugs, please include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

Use the bug report template when creating an issue.

### Suggesting Features

Feature suggestions are welcome! Please:
- Check if the feature has already been suggested
- Provide clear use case and benefits
- Consider implementation complexity
- Be open to discussion

### Pull Requests

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

#### PR Requirements

- [ ] Code follows the style guidelines
- [ ] Tests pass (`pytest`)
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No secrets or credentials in code
- [ ] Security review completed for sensitive changes

### Code Style

We use the following tools:
- **Black**: Code formatting
- **Ruff**: Linting
- **MyPy**: Type checking
- **Bandit**: Security scanning

```bash
# Format code
black coe-kernel/

# Run linter
ruff coe-kernel/

# Type check
mypy coe-kernel/

# Security scan
bandit -r coe-kernel/
```

## 🏗️ Architecture Decisions

### Module System

When adding new modules:
1. Follow the module manifest specification
2. Include proper Ed25519 signatures
3. Add capability declarations
4. Document permissions required
5. Include cost profile estimates

### API Changes

When modifying the API:
1. Maintain backward compatibility when possible
2. Version the API endpoint if breaking changes
3. Update API documentation
4. Add tests for new endpoints

### Database Changes

When modifying the database schema:
1. Create migration scripts
2. Ensure backward compatibility
3. Test migration on sample data
4. Document changes

## 🔒 Security

Security is critical. Please:
- Never commit secrets or credentials
- Report security vulnerabilities privately
- Follow the principle of least privilege
- Validate all inputs
- Use parameterized queries

### Security Checklist

- [ ] No hardcoded credentials
- [ ] Input validation implemented
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF tokens where applicable
- [ ] Audit logging for sensitive operations

## 🧪 Testing

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
└── fixtures/      # Test data
```

### Writing Tests

```python
# Example test
def test_business_module_load():
    """Test that business module loads correctly."""
    loader = ModuleLoader()
    result = loader.load("business")
    assert result is True
    assert loader.get_module_instance("business") is not None
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=coe-kernel --cov-report=html

# Specific test
pytest tests/unit/test_module_loader.py -v

# Integration tests only
pytest tests/integration/ -v
```

## 📚 Documentation

- Update README.md for user-facing changes
- Update docs/ for technical changes
- Add docstrings to public APIs
- Include examples where helpful

## 🏷️ Versioning

We follow [Semantic Versioning](https://semver.org/):
- MAJOR: Incompatible API changes
- MINOR: Backward-compatible functionality
- PATCH: Backward-compatible bug fixes

## 🙋 Questions?

- Check existing issues and discussions
- Join our community chat
- Email: maintainers@coekernel.org

## 🎉 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

Thank you for contributing to COE Kernel!
