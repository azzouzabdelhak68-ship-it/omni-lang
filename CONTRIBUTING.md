# Contributing to OmniScript

Thank you for your interest in contributing! This guide covers the development workflow, quality gates, and how to submit changes.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for runtime tests)
- Git

### Installation

```bash
git clone https://github.com/azzouzabdelhak68-ship-it/omni-lang.git
cd omni-lang
pip install -e ".[dev]"
```

Verify the installation:

```bash
omni --help
python -m pytest tests/ -q
```

## Project Structure

```
omni-lang/
├── omni_compiler/        # Compiler pipeline (lexer, parser, checker, emitters)
│   ├── cli.py           # CLI entry point
│   ├── emitter.py       # JS emitter
│   ├── c_emitter.py     # C emitter
│   ├── wasm_emitter.py  # WASM emitter
│   ├── checker.py       # Type/effect checker
│   ├── parser.py        # Parser
│   ├── lexer.py         # Lexer
│   └── ...
├── omnisys/             # JS runtime (OMNISYS standard library)
├── packages/            # Python reference implementations of OMNISYS modules
├── simulation_engine/   # Actor/ECS runtime (JS)
├── tests/               # Main test suite
├── docs/                # Documentation
└── examples/            # Example programs
```

## Running Tests

### Core Test Suite

```bash
# Run all tests
python -m pytest tests/ -q

# Run with coverage
python -m pytest tests/ --cov=omni_compiler --cov-branch --cov-fail-under=90

# Run specific test file
python -m pytest tests/test_emitter.py -v

# Run with keyword filter
python -m pytest tests/ -k "emitter" -v
```

### Package Tests (OMNISYS modules)

```bash
# Run all package tests (requires --import-mode=importlib due to duplicate test filenames)
python -m pytest packages/ --import-mode=importlib -q

# Run specific package tests
python -m pytest packages/omnisys-pkg/tests/ -v
```

### Mutation Testing

```bash
python -m mutmut run
python -m mutmut results
```

Mutation score must stay ≥ 80%.

## Quality Gates

All PRs must pass these gates (enforced in CI):

| Gate | Command | Threshold |
|------|---------|-----------|
| Lint | `ruff check .` | No errors |
| Format | `ruff format --check .` | No changes |
| Type Check | `mypy omni_compiler/` | Strict mode |
| Security | `bandit -r omni_compiler/` | No high/medium |
| Unit Tests | `pytest tests/` | All pass |
| Coverage | `pytest --cov=omni_compiler --cov-branch` | ≥ 90% branch |
| Package Tests | `pytest packages/ --import-mode=importlib` | All pass |
| Mutation Testing | `mutmut run` | ≥ 80% score |
| Conformance | `pytest tests/conformance/` | All pass |
| Performance | `python scripts/check_performance.py` | Check ≤ 200ms, Build ≤ 500ms |
| Docs | `python scripts/verify-docs.py && python scripts/gen-index.py --check` | No errors |

Run all gates locally:

```bash
# Quick check (lint + type + tests)
ruff check . && mypy omni_compiler/ && python -m pytest tests/ -q

# Full check (may take several minutes)
python -m pytest tests/ packages/ --import-mode=importlib -q && python -m mutmut run
```

## Code Style

- **Line length:** 100 chars
- **Quotes:** Single quotes (enforced by Ruff)
- **Imports:** Sorted (stdlib → third-party → local)
- **Type hints:** Required on all public functions (strict mypy)
- **Docstrings:** Google-style for public APIs

## Submitting Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write tests for new functionality
- Update documentation if needed
- Keep commits focused and atomic

### 3. Run Quality Gates

```bash
ruff check .
ruff format --check .
mypy omni_compiler/
python -m pytest tests/ -q
python -m pytest packages/ --import-mode=importlib -q
```

### 4. Commit

```bash
git add .
git commit -m "feat: brief description of change

Longer explanation if needed.
Closes #issue-number"
```

### 5. Push and Open PR

```bash
git push origin feature/your-feature-name
```

Open a Pull Request on GitHub with:
- Clear title and description
- Reference to related issues
- Screenshots for UI changes

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `refactor:` — Code restructuring
- `perf:` — Performance improvement
- `test:` — Test additions/changes
- `chore:` — Maintenance (deps, CI, etc.)

Example:
```
feat(emitter): add JSON escaping for string literals

Prevents XSS by using json.dumps() for all emitted string segments.
Fixes CVE-2024-xxxxx.
```

## Architecture Overview

### Compiler Pipeline

```
Source (.omni)
    │
    ▼
Lexer (tokenize) → tokens
    │
    ▼
Parser (parse) → AST
    │
    ▼
Checker (analyze) → SymbolTable + Effects
    │
    ▼
MIR (to_mir) → MIRModule
    │
    ├──▶ JS Emitter (emit_js) → HTML/JS
    ├──▶ C Emitter (emit_c) → .c/.h
    ├──▶ WASM Emitter (emit_wasm) → .wat/.wasm
    └──▶ Rust Emitter (emit_rust) → .rs
```

### Key Concepts

- **Capabilities/Effects:** Static tracking of side effects (I/O, timers, etc.)
- **MIR (Mid-level IR):** Target-agnostic representation
- **OMNISYS:** Portable standard library (JS + Python reference)
- **Actor Runtime:** Deterministic distributed systems (`sim.actor.*`)

## Adding a New OMNISYS Module

1. Add JS implementation in `omnisys/<name>.js`
2. Add Python reference in `packages/omnisys-<name>/src/omnisys_<name>/`
3. Add tests in `packages/omnisys-<name>/tests/`
4. Register in `omni_compiler/omnisys_registry.py`
5. Run conformance tests: `python -m pytest packages/omnisys-<name>/tests/`

## Adding a New Compiler Target

1. Create `omni_compiler/<target>_emitter.py`
2. Implement `emit_<target>(mir: MIRModule) -> str`
3. Add to CLI in `omni_compiler/cli.py`
4. Add conformance tests in `tests/test_<target>_emitter.py`

## Documentation

- **User docs:** `docs/language/` (tutorial, spec)
- **Architecture:** `docs/architecture/`
- **Module docs:** `docs/omnisys/<name>/README.md`
- **API reference:** Generated from source (`scripts/gen-index.py`)

Regenerate docs index:

```bash
python scripts/gen-index.py
python scripts/verify-docs.py
```

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues/PRs before submitting
- For questions, use GitHub Discussions

## License

OmniScript is MIT licensed. By contributing, you agree to license your contributions under MIT.