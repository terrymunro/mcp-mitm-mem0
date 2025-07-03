# Dependencies Guide

**Last Updated:** 2024-12-19

## Overview

This document covers the dependency management strategy for MCP MITM Mem0, including core dependencies, development tools, and maintenance practices.

## Package Manager

The project uses **uv** as the primary package manager, with configuration managed through `pyproject.toml`.

### Why uv?

- **Fast**: Significantly faster than pip for dependency resolution and installation
- **Modern**: Full support for PEP 621 (pyproject.toml) and modern Python packaging
- **Reliable**: Deterministic dependency resolution with lock files
- **Compatible**: Works with existing pip/Poetry workflows

### Installation

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

## Core Dependencies

### Runtime Dependencies

Defined in `pyproject.toml` under `[project]` dependencies:

```toml
[project]
name = "mcp-mitm-mem0"
requires-python = ">=3.12"
dependencies = [
    "mcp",           # Model Context Protocol SDK
    "mem0ai",        # Mem0 SaaS client library
    "mitmproxy",     # HTTP/HTTPS proxy for interception
    "pydantic",      # Data validation and settings management
    "pydantic-settings",  # Environment-based configuration
    "structlog",     # Structured logging
]
```

#### Dependency Analysis

| Package | Version Requirement | Purpose | Critical |
|---------|-------------------|---------|----------|
| `mcp` | Latest | MCP protocol implementation | Yes |
| `mem0ai` | Latest | Mem0 SaaS API client | Yes |
| `mitmproxy` | Latest | HTTPS traffic interception | Yes |
| `pydantic` | >=2.0 | Configuration and data validation | Yes |
| `pydantic-settings` | Latest | Environment variable management | Yes |
| `structlog` | Latest | Structured logging for operations | No |

### Development Dependencies

Defined in `pyproject.toml` under `[dependency-groups]`:

```toml
[dependency-groups]
lint = [
    "basedpyright",  # Type checker
    "pylint",        # Code quality linter
    "ruff",          # Fast Python linter and formatter
]
test = [
    "pytest",       # Testing framework
    "pytest-asyncio",  # Async testing support
    "pytest-cov",   # Coverage reporting
]
```

#### Development Tools Analysis

| Tool | Purpose | Configuration File | Required |
|------|---------|-------------------|----------|
| `ruff` | Linting and formatting | `ruff_defaults.toml`, `pyproject.toml` | Yes |
| `basedpyright` | Type checking | `pyproject.toml` | Yes |
| `pytest` | Unit and integration testing | `pyproject.toml` | Yes |
| `pytest-asyncio` | Async test support | Auto-configured | Yes |
| `pylint` | Additional code quality checks | Default config | No |

## Python Version Requirements

### Minimum Version

- **Python 3.12+** is required (`requires-python = ">=3.12"`)

### Version Compatibility

```bash
# Check Python version
python --version

# Supported versions
✅ Python 3.12.x
✅ Python 3.13.x
❌ Python 3.11.x (not supported)
❌ Python 3.10.x (not supported)
```

### Python 3.12+ Features Used

- **Improved type hints**: Better generic type support
- **Performance improvements**: Faster startup and execution
- **AsyncIO enhancements**: Better async/await performance
- **Structured pattern matching**: Used in configuration parsing

## Dependency Installation

### Production Installation

```bash
# Install only runtime dependencies
uv sync --only-production

# Or with explicit dependency resolution
uv install --only-production
```

### Development Installation

```bash
# Install all dependencies (runtime + development)
uv sync

# Install specific dependency groups
uv sync --group lint
uv sync --group test
```

### Frozen Installation

```bash
# Install exact versions from lock file
uv sync --frozen

# Useful for production deployments
uv install --frozen
```

## Dependency Updates

### Update Strategy

1. **Security Updates**: Apply immediately
2. **Minor Updates**: Monthly review cycle
3. **Major Updates**: Quarterly evaluation with testing

### Update Commands

```bash
# Check for outdated packages
uv outdated

# Update all dependencies
uv sync --upgrade

# Update specific package
uv add package_name@latest

# Update with constraints
uv add "mem0ai>=1.0,<2.0"
```

### Update Testing

```bash
# Test after updates
uv run pytest
uv run ruff check
uv run ruff format --check
```

## Dependency Security

### Security Scanning

```bash
# Using pip-audit (install separately)
pip install pip-audit
pip-audit --requirements pyproject.toml

# Using safety (alternative)
pip install safety
safety check --json
```

### Vulnerability Response

1. **Immediate Assessment**: Evaluate vulnerability impact
2. **Update Planning**: Plan update strategy
3. **Testing**: Comprehensive testing before deployment
4. **Deployment**: Apply updates with rollback plan

## Platform-Specific Dependencies

### Operating System Compatibility

| OS | Status | Notes |
|----|--------|-------|
| **Linux** | ✅ Fully Supported | Primary development platform |
| **macOS** | ✅ Fully Supported | Certificate installation differs |
| **Windows** | ⚠️ Limited Testing | May require additional setup |

### Platform-Specific Issues

#### macOS
- **Certificate Installation**: Requires `security` command
- **Proxy Configuration**: System-level proxy settings

#### Linux
- **Certificate Installation**: Requires `update-ca-certificates`
- **Service Management**: systemd service files provided

#### Windows
- **Certificate Installation**: Manual import via certlm.msc
- **Service Management**: Manual service management

## Optional Dependencies

### Extras

Currently no optional extras are defined, but future versions may include:

```toml
[project.optional-dependencies]
monitoring = ["prometheus-client", "statsd"]
debug = ["icecream", "rich"]
```

### Installation with Extras

```bash
# Future: Install with monitoring
uv install ".[monitoring]"

# Future: Install with all extras
uv install ".[monitoring,debug]"
```

## Dependency Conflicts

### Known Conflicts

No known conflicts with current dependency set.

### Conflict Resolution

```bash
# Diagnose conflicts
uv tree

# Check specific package dependencies
uv show mem0ai

# Resolve with constraints
uv add "conflicting-package<2.0"
```

## Lock File Management

### Lock File Location

- **uv.lock**: Contains exact versions and hashes for reproducible builds

### Lock File Operations

```bash
# Generate/update lock file
uv lock

# Install from lock file
uv sync --frozen

# Verify lock file integrity
uv lock --check
```

### Version Control

```bash
# Include in version control
git add uv.lock
git commit -m "Update dependency lock file"

# .gitignore patterns (already configured)
__pycache__/
*.pyc
.venv/
```

## Troubleshooting

### Common Issues

1. **Python Version Mismatch**:
   ```bash
   # Error: Python 3.11 not supported
   # Solution: Upgrade to Python 3.12+
   pyenv install 3.12.0
   pyenv local 3.12.0
   ```

2. **uv Not Found**:
   ```bash
   # Solution: Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc
   ```

3. **SSL/Certificate Issues**:
   ```bash
   # Solution: Update certificates
   pip install --upgrade certifi
   # Or use uv with trusted hosts
   uv install --trusted-host pypi.org
   ```

4. **Memory Service Connection**:
   ```bash
   # Check Mem0 API key
   echo $MEM0_API_KEY
   # Test connection
   python -c "from mem0 import MemoryClient; MemoryClient(api_key='$MEM0_API_KEY')"
   ```

### Debug Information

```bash
# Environment information
uv info

# Dependency tree
uv tree

# Package information
uv show mcp

# Environment validation
uv run python -c "import sys; print(f'Python {sys.version}')"
```

## Maintenance

### Regular Tasks

#### Weekly
- [ ] Check for security advisories
- [ ] Review dependency update notifications

#### Monthly
- [ ] Update non-critical dependencies
- [ ] Run full test suite with updates
- [ ] Review dependency tree for conflicts

#### Quarterly
- [ ] Evaluate major version updates
- [ ] Review dependency necessity
- [ ] Performance impact assessment
- [ ] Security audit of dependencies

### Maintenance Scripts

```bash
#!/bin/bash
# dependency_maintenance.sh

echo "=== Dependency Maintenance ==="

# Check for outdated packages
echo "Checking for outdated packages..."
uv outdated

# Security check (requires pip-audit)
echo "Running security scan..."
pip-audit --requirements pyproject.toml

# Dependency tree analysis
echo "Analyzing dependency tree..."
uv tree

# Test environment
echo "Testing current environment..."
uv run pytest --quick

echo "Maintenance check complete!"
```

## Best Practices

### Development Workflow

1. **Always use lock files** for reproducible builds
2. **Pin major versions** for stability
3. **Test after updates** before committing
4. **Document breaking changes** in dependency updates

### Production Deployment

1. **Use frozen installs** (`uv sync --frozen`)
2. **Separate dev dependencies** (production installs only)
3. **Security scanning** in CI/CD pipeline
4. **Rollback strategy** for dependency issues

### Dependency Selection

1. **Minimize dependencies** - only add what's necessary
2. **Choose maintained packages** - active development and support
3. **Consider alternatives** - evaluate multiple options
4. **Security first** - prioritize packages with good security practices

## Dependency Roadmap

### Short Term (Next Release)
- Evaluate Mem0 API client alternatives
- Add optional monitoring dependencies
- Improve development tooling

### Medium Term (6 months)
- Migrate to newer MCP protocol versions
- Evaluate mitmproxy alternatives
- Add performance monitoring dependencies

### Long Term (1 year)
- Consider dependency consolidation
- Evaluate Python 3.13+ specific features
- Review entire dependency stack for optimization 