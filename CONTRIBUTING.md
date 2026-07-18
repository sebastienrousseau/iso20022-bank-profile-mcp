# Contributing to iso20022-bank-profile-mcp

Thank you for your interest in contributing to iso20022-bank-profile-mcp.
This guide covers the development workflow and standards.

`iso20022-bank-profile-mcp` is the bank clearing-profile Model Context
Protocol (MCP) server of the **ISO 20022 MCP Suite** — a fully local,
closed-world server that manages, validates, and serves the bank-specific
clearing profiles / rule packs that sit beyond structural XSD validation. It
is a sibling of `iso20022-readiness-suite-mcp`, which can consume the profiles
this server serves. This repository owns the profile catalogue, the rule
mini-language, the profile/rule-pack validator, and the payload linter.

## Development Setup

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation)
- Git with SSH commit signing configured
- (Optional) [`uv`](https://docs.astral.sh/uv/) — used by `make pip-compile`.

### Setup

```bash
# Clone and install
git clone git@github.com:sebastienrousseau/iso20022-bank-profile-mcp.git
cd iso20022-bank-profile-mcp
poetry install

# Verify
poetry run pytest tests/ -q
```

> **Note:** the server is fully local and closed-world — every tool computes
> from the bundled clearing-profile data with no network calls and no
> sub-servers, so the test suite runs with nothing else installed.

### On macOS

```bash
brew install python@3.12 poetry
```

### On Linux (Debian/Ubuntu)

```bash
sudo apt install python3 python3-pip
pip install poetry
```

### On WSL

```bash
sudo apt install python3 python3-pip
pip install poetry
# Ensure ~/.local/bin is in PATH
```

## Workflow

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
3. **Make changes** — follow the coding standards below
4. **Run tests**:
   ```bash
   poetry run pytest tests/ -v
   ```
5. **Run linters**:
   ```bash
   poetry run ruff check iso20022_bank_profile_mcp/
   poetry run mypy iso20022_bank_profile_mcp/
   poetry run black --check iso20022_bank_profile_mcp/ tests/
   ```
6. **Sign and commit**:
   ```bash
   git commit -S -m "feat: add my feature"
   ```
7. **Push** and open a pull request

## Commit Signing (Required)

All commits **must** be signed with SSH or GPG.

### SSH Signing

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519
git config --global commit.gpgsign true
```

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add a new clearing profile
fix: return an error payload instead of raising on a malformed definition
docs: update README with the MCP client config
test: cover the validate_profile_definition tool
refactor: simplify the profile engine
```

## Coding Standards

- **Line length:** 79 characters (enforced by Black + Ruff)
- **Type hints:** Required on all public functions (mypy strict)
- **Docstrings:** Required on all public classes and functions (interrogate
  at 100%)
- **Tests:** Every new tool or change must include tests
- **Error convention:** tools return an `{"error": ...}` payload rather than
  raising into the MCP client transport

## Testing

```bash
# Full suite (100% line + branch coverage gate)
poetry run pytest tests/ -v

# Single file
poetry run pytest tests/test_server.py -v
```

## Pull Request Checklist

- [ ] All tests pass (`poetry run pytest`)
- [ ] Linters pass (`ruff check`, `mypy`, `black --check`)
- [ ] Commits are signed
- [ ] PR title follows conventional commit format
- [ ] New features include tests and documentation

## License

By contributing, you agree that your contributions will be licensed under
the [Apache License 2.0](LICENSE).
