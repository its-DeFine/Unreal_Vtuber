# Consolidated Test Suite

This directory contains all tests for the Docker VTuber project, consolidated from various locations throughout the repository.

## Test Structure

```
tests/
├── core/                    # Core system tests
│   ├── autogen/            # AutoGen system tests (20 files)
│   └── graphflow/          # GraphFlow system tests (10 files)
│       ├── unit/           # Unit tests (5 files)
│       └── integration/    # Integration tests (1 file)
├── avatar/                 # Avatar and VTuber tests
│   └── orchestrator/       # Orchestrator tests (7 files)
├── decide/                 # Decision system tests (22 files)
│   └── integration/        # Integration tests (16 files)
├── integration/            # Cross-component integration tests
├── unit/                   # Unit tests
├── system/                 # System-level tests
├── legacy/                 # Legacy tests preserved for reference
└── pytest.ini             # Pytest configuration
```

## Test Categories

### By Type
- **Integration Tests**: 45 files - Tests that verify component interactions
- **Unit Tests**: 16 files - Tests for individual components/functions
- **Scripts**: 8 files - Test scripts and utilities
- **System Tests**: 1 file - End-to-end system tests
- **E2E Tests**: 1 file - End-to-end workflow tests

### By Component
- **Core/AutoGen**: 20 files - AutoGen system tests
- **Core/GraphFlow**: 10 files - GraphFlow stimuli system tests
- **Avatar/Orchestrator**: 7 files - VTuber orchestrator tests
- **Decide**: 22 files - Decision system tests
- **Main Directory**: 6 files - General integration tests

## Test Statistics

- **Total Files**: 71
- **Total Test Functions**: 350
- **Large Files** (>500 lines): 12 files
- **Files with Network Calls**: 34 files
- **Files with Performance Tests**: 32 files
- **Files with Delays**: 31 files
- **Files Requiring Server**: 29 files

## Technology Usage

- **AsyncIO**: 55 files - Asynchronous testing
- **AutoGen**: 43 files - AutoGen framework tests
- **Cognee**: 27 files - Cognee integration tests
- **Mock**: 19 files - Mock/stub testing
- **AIOHTTP**: 16 files - HTTP client tests
- **Container**: 15 files - Container integration tests
- **Docker**: 12 files - Docker-related tests
- **Pytest**: 11 files - Pytest framework tests
- **Orchestrator**: 12 files - Orchestrator tests
- **GraphFlow**: 9 files - GraphFlow system tests

## Import Path Updates

The pytest configuration has been updated to work from the consolidated location:
- `pythonpath = ../app` - Points to the application code
- Coverage reports target `../app` directory
- Test discovery runs from the tests directory

## Known Import Issues

Some tests may have import issues that need manual fixing:
- GraphFlow tests importing from `src.*` paths
- System2 integration tests with relative imports
- Context service tests with path dependencies

## Running Tests

```bash
# Run all tests
cd /home/geo/directories/autonomy/docker-vtuber/tests
pytest

# Run specific categories
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only
pytest -m "not slow"              # Exclude slow tests
pytest -m "requires_api_key"      # API key required tests

# Run by component
pytest core/autogen/              # AutoGen tests
pytest core/graphflow/            # GraphFlow tests
pytest avatar/orchestrator/       # Orchestrator tests
pytest decide/                    # Decision system tests
```

## Test Markers

- `unit`: Unit tests
- `integration`: Integration tests
- `e2e`: End-to-end tests
- `system`: System tests
- `slow`: Slow tests
- `requires_api_key`: Tests requiring API keys
- `legacy`: Legacy tests
- `performance`: Performance tests
- `autogen`: AutoGen system tests
- `graphflow`: GraphFlow system tests
- `orchestrator`: Orchestrator tests
- `decide`: Decision system tests

## Moved From

Tests were consolidated from these locations:
- `/home/geo/directories/autonomy/docker-vtuber/app/tests/` → `/home/geo/directories/autonomy/docker-vtuber/tests/`
- `/home/geo/directories/autonomy/docker-vtuber/app/CORE/autogen-agent/tests/` → `/home/geo/directories/autonomy/docker-vtuber/tests/core/autogen/`
- `/home/geo/directories/autonomy/docker-vtuber/app/CORE/graphflow-stimuli-system/tests/` → `/home/geo/directories/autonomy/docker-vtuber/tests/core/graphflow/`
- `/home/geo/directories/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/orchestrator/legacy/tests/` → `/home/geo/directories/autonomy/docker-vtuber/tests/avatar/orchestrator/`
- `/home/geo/directories/autonomy/decide/tests/` → `/home/geo/directories/autonomy/docker-vtuber/tests/decide/`

## Coverage Configuration

- **Target**: `../app` directory
- **Minimum Coverage**: 60%
- **Reports**: Terminal, HTML, XML
- **HTML Output**: `htmlcov/` directory

## Next Steps

1. **Fix Import Issues**: Update imports in files with `src.*` paths
2. **Add Test Markers**: Add appropriate markers to test functions
3. **Optimize Large Files**: Consider splitting files >500 lines
4. **Update Documentation**: Add docstrings to test functions
5. **CI/CD Integration**: Configure continuous integration