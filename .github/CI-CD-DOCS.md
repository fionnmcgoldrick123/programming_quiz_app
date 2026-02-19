# CI/CD Pipeline Documentation

## Overview

This project uses **GitHub Actions** for continuous integration and continuous deployment. The pipeline automatically runs on every push and pull request to the `main` and `develop` branches.

## Pipeline Structure

The CI/CD pipeline consists of four parallel jobs:

### 1. Frontend CI
- **Technology**: React + TypeScript + Vite
- **Node Version**: 20.x
- **Steps**:
  - Install dependencies with `npm ci`
  - Run ESLint code quality checks
  - Perform TypeScript type checking
  - Build the production bundle
  - Upload build artifacts (retained for 7 days)

### 2. Backend CI
- **Technology**: FastAPI (Python 3.11)
- **Steps**:
  - Install dependencies from `requirements.txt`
  - Install development tools (Black, Flake8)
  - Run Black formatter check for code style
  - Run Flake8 linting for code quality
  - Validate Python syntax compilation

### 3. Classifier Model CI
- **Technology**: Python 3.11
- **Steps**:
  - Install dependencies from `requirements.txt`
  - Run Flake8 linting
  - Validate Python syntax compilation

### 4. CI Success Summary
- **Purpose**: Consolidates all job results
- **Runs**: Only if all previous jobs succeed
- **Output**: Success confirmation message

## Local Development

### Frontend Linting
```bash
cd frontend
npm run lint
npx tsc --noEmit  # Type checking
npm run build     # Production build
```

### Backend Linting
```bash
cd backend
pip install -r requirements-dev.txt

# Format code with Black
black .

# Check formatting without changes
black --check .

# Run Flake8 linter
flake8 .
```

## Configuration Files

### Backend Linting Configuration
- **`.flake8`**: Flake8 configuration
  - Max line length: 127 characters
  - Excludes: `__pycache__`, `.git`, `.vscode`, `venv`, `env`
  - Ignores: E203, W503, E501

- **`pyproject.toml`**: Black formatter configuration
  - Line length: 127 characters
  - Target Python version: 3.11

## Workflow Triggers

The pipeline runs on:
- **Push** to `main` or `develop` branches
- **Pull requests** targeting `main` or `develop` branches

## Artifacts

Build artifacts from the frontend are uploaded and retained for 7 days. You can download them from the Actions tab in GitHub.

## Adding Tests

To add tests to the pipeline:

### Frontend Tests
Add to `frontend/package.json`:
```json
"scripts": {
  "test": "vitest"
}
```

Then add to the workflow:
```yaml
- name: Run tests
  run: npm test
```

### Backend Tests
Create test files in `backend/tests/` using pytest:

```python
# tests/test_main.py
def test_example():
    assert 1 + 1 == 2
```

Install pytest:
```bash
pip install -r requirements-dev.txt
```

Add to workflow:
```yaml
- name: Run tests
  run: pytest
```

## Continuous Deployment

Currently, the pipeline only performs CI (testing and validation). To add CD:

1. **Deploy to staging/production**
2. **Docker build and push**
3. **Cloud deployment** (AWS, Azure, GCP, etc.)

These features can be added as needed for your deployment strategy.

## Status Badge

Add this to your README.md to show build status:

```markdown
![CI/CD Pipeline](https://github.com/<username>/<repo>/workflows/CI/CD%20Pipeline/badge.svg)
```

## Troubleshooting

### Frontend Build Fails
- Check `package-lock.json` is committed
- Ensure all dependencies are in `package.json`
- Verify TypeScript configuration

### Backend Linting Fails
- Run `black .` locally to format code
- Fix Flake8 warnings locally before pushing
- Check `.flake8` configuration for rules

### Cache Issues
- Delete `.github/workflows` cache in Actions settings
- Workflow will rebuild cache on next run
