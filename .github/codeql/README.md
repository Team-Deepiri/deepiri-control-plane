# CodeQL Setup for deepiri-platform repository

This folder contains the CodeQL configuration for repository-level security scanning.

## What each file does

- `.github/workflows/codeql.yml`
  - Defines when scans run and how GitHub Actions executes CodeQL.
- `.github/codeql/codeql-config.yml`
  - Defines what folders to include and ignore during analysis.

## Workflow breakdown (`.github/workflows/codeql.yml`)

### `name: CodeQL`
The display name in the Actions tab.

### `on.push.branches`
```yaml
on:
  push:
    branches: [main, dev]
```
Runs scans only when code is pushed to `main` or `dev`.

### `permissions`
```yaml
permissions:
  actions: read
  contents: read
  security-events: write
```
Uses least-privilege permissions. `security-events: write` is required so CodeQL can upload findings.

### `strategy.matrix.language`
```yaml
language: [javascript-typescript, python]
```
Runs one analysis job per coding language, in parallel(independently, at the same time).

### Checkout step
```yaml
with:
  fetch-depth: 0
```
- `fetch-depth: 0` keeps full git history (safe default for analysis and troubleshooting).
- Submodules are **not** checked out. Each submodule will have its own CodeQL workflow in its own `.github/workflows/` folder for independent scanning.

### Initialize CodeQL
```yaml
uses: github/codeql-action/init@v3
```
Starts the CodeQL engine and loads `.github/codeql/codeql-config.yml`.

### Autobuild
```yaml
uses: github/codeql-action/autobuild@v3
```
Attempts automatic build/setup for compiled projects.

### Analyze
```yaml
uses: github/codeql-action/analyze@v3
```
Executes queries and uploads results to GitHub Security.

## Config breakdown (`.github/codeql/codeql-config.yml`)

### `paths`
Folders that are included in scanning.

### `paths-ignore`
Generated, vendored, and environment files that are excluded to reduce noise and run time.

## Best practices

1. Keep trigger scope intentional:
   - Use branch filters (`main`, `dev`) to control cost and noise.

2. Keep language list explicit:
   - Only include languages with meaningful source code.

3. Keep `paths` focused:
   - Include actively maintained production code first.

4. Exclude generated/vendor artifacts:
   - Keep `node_modules`, build outputs, caches, and minified files in `paths-ignore`.

5. Pin to stable major action versions:
   - `@v3` is the current stable major for CodeQL actions.

6. Review alerts regularly:
   - Triage high/critical findings first and suppress only with documented reasoning.

## How to do maintenece
As more code and files are added it is necessary to update the codeql.yml and codeql-config.yml as needed. Below are common examples.

### Add a new language
Edit matrix in `.github/workflows/codeql.yml`:
```yaml
language: [javascript-typescript, python, go]
```

### Include a new top-level package
Add it in `.github/codeql/codeql-config.yml` under `paths`.

### Exclude another generated folder
Add a glob to `paths-ignore`, for example:
```yaml
- '**/generated/**'
```
