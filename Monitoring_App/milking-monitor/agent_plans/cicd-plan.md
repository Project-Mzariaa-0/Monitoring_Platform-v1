# CI/CD Pipeline Implementation Plan

## Overview
Set up GitHub Actions CI/CD pipeline with full quality gates for both the Next.js web app and FastAPI inference service.

## What we're building

```
.github/workflows/ci.yml
├── Job 1: web-checks (Node 22)
│   ├── Install dependencies
│   ├── TypeScript check (tsc --noEmit)
│   ├── ESLint (next lint)
│   ├── Build (next build)
│   └── Vitest tests
│
├── Job 2: inference-checks (Python 3.12)
│   ├── Install dependencies
│   ├── Ruff lint
│   ├── Pytest tests
│   └── FastAPI smoke test (TestClient)
│
└── Job 3: integration-checks (needs both above)
    └── Docker compose smoke test
```

## Files to create/modify

### New files
| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Main CI pipeline |
| `apps/web/package.json` | Add `typecheck` and `test` scripts |
| `apps/web/vitest.config.ts` | Vitest configuration |
| `apps/web/lib/__tests__/constants.test.ts` | Smoke tests for shared lib |
| `apps/inference-service/pyproject.toml` | Python project config with pytest settings |
| `apps/inference-service/requirements-dev.txt` | Dev dependencies (pytest, ruff, httpx) |
| `apps/inference-service/tests/conftest.py` | Shared pytest fixtures |
| `apps/inference-service/tests/unit/test_task_state_machine.py` | State machine tests |
| `apps/inference-service/tests/unit/test_roi_splitter.py` | ROI splitter tests |
| `apps/inference-service/tests/api/test_health.py` | FastAPI endpoint tests |

### Modified files
| File | Change |
|------|--------|
| `apps/web/package.json` | Add `typecheck`, `test`, `test:ci` scripts |
| `apps/inference-service/requirements.txt` | Keep clean (runtime only), dev deps in requirements-dev.txt |

## Pipeline details

### Trigger
- On `push` to `main` and `dev` branches
- On `pull_request` to `main`

### web-checks job
```yaml
- Setup Node 22
- npm ci (with cache)
- npx tsc --noEmit          # Typecheck
- npx next lint              # ESLint
- npx next build             # Build verification
- npx vitest run             # Unit tests
```

### inference-checks job
```yaml
- Setup Python 3.12
- pip install -r requirements.txt -r requirements-dev.txt
- ruff check src/            # Linting
- pytest tests/ -v           # All tests
```

### integration-checks job
```yaml
- docker compose up -d       # Start all services
- curl localhost:3000        # Web app responds
- curl localhost:8001        # Inference service responds
- docker compose down        # Cleanup
```

## Test infrastructure setup

### Vitest (Next.js)
- Install `vitest`, `@vitejs/plugin-react`
- Config with path aliases matching tsconfig
- Basic smoke tests for `lib/constants.ts` and `lib/security/sanitize.ts`

### Pytest (FastAPI)
- `pyproject.toml` with pytest config
- `conftest.py` with FastAPI TestClient fixture
- Unit tests for `TaskStateMachine` and `roi_splitter`
- API test for `GET /` health endpoint

## Environment variables for CI
- `DATABASE_URL`: Use SQLite for CI (no PostgreSQL needed for unit tests)
- `AUTH_SECRET`: Test secret
- `INFERENCE_SERVICE_TOKEN`: Test token

## Estimated time
~15 minutes to implement all files.
