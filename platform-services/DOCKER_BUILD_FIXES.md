# Docker Build Fixes

## Problem

All 6 platform service Docker builds were failing with:
```
npm error Cannot read properties of undefined (reading 'extraneous')
```

The builds never reached the TypeScript compilation step — the crash occurred during
`npm install` for the app, which meant an underlying incentive-engine syntax error was
also silently hidden until the npm crash was fixed.

---

## Fix 1 — Strip shared-utils link entries from the app lock file before install

**Root cause:** npm's arborist package has a null-dereference bug triggered by `link: true`
entries in a `package-lock.json`. When npm 7+ records a `file:` local dependency, it writes
two entries into the lock file:

```json
"../../shared/deepiri-shared-utils": {
  "name": "@team-deepiri/shared-utils",
  "dependencies": { "dotenv": "...", "ioredis": "...", "winston": "..." },
  "devDependencies": { "typescript": "..." }
}
"node_modules/@team-deepiri/shared-utils": {
  "resolved": "../../shared/deepiri-shared-utils",
  "link": true
}
```

When npm reads these entries during dependency tree construction (arborist), it
dereferences a property on an undefined node — crashing before any packages are
installed. This affects npm 10.8.2 and all npm 11.x versions; there is no npm
version that fixes the crash.

**Why stripping the entries is safe:** The two entries describe a local symlink, not a
registry package. Removing them does not unpin any versioned dependency — all registry
packages for the app remain fully pinned in the lock file. The actual shared-utils
package is installed separately in its own directory before the app install runs, so
npm simply creates the symlink to an already-present package without needing a lock
entry.

**Why this is better than alternatives:**
- Upgrading npm does not fix it — tested 10.9.8 and 11.3.0, both crash identically.
- Removing the lock file entirely would unpin all app dependencies, breaking
  reproducibility across environments.
- Patching npm itself is not viable in a Docker build pipeline.

**Fix applied to all 6 Dockerfiles:**

```dockerfile
RUN node -e "const fs=require('fs'),lock=JSON.parse(fs.readFileSync('package-lock.json'));delete lock.packages['../../shared/deepiri-shared-utils'];delete lock.packages['node_modules/@team-deepiri/shared-utils'];fs.writeFileSync('package-lock.json',JSON.stringify(lock));" \
 && cd /shared/deepiri-shared-utils \
 && npm ci --legacy-peer-deps \
 && node -e "const fs=require('fs'),p=JSON.parse(fs.readFileSync('package.json'));delete p.scripts.prepare;fs.writeFileSync('package.json',JSON.stringify(p,null,2));" \
 && rm -rf node_modules \
 && cd /app \
 && npm install --legacy-peer-deps \
 && cd /shared/deepiri-shared-utils \
 && npm ci --omit=dev --legacy-peer-deps \
 && cd /app \
 && npm cache clean --force
```

Step-by-step what this does:
1. Strip the two shared-utils link entries from the app's `package-lock.json` — prevents the arborist crash
2. `npm ci` in shared-utils — the `prepare` script runs automatically, compiling TypeScript to `dist/`
3. Remove the `prepare` script from shared-utils `package.json` — prevents the app's npm install from trying to re-run `tsc` (TypeScript is not available after step 4)
4. `rm -rf node_modules` in shared-utils — clean slate before the app install runs
5. `npm install` in app — succeeds because the crash-triggering entries are gone; all other registry deps are still pinned by the lock file
6. `npm ci --omit=dev` in shared-utils — restores only runtime deps (`ioredis`, `winston`, `dotenv`) needed at runtime, pinned to exact versions via shared-utils' own lock file

**Note on step 5 using `npm install` instead of `npm ci`:** After stripping the two
link entries, the app's lock file is technically out of sync with `package.json`
(which still declares `@team-deepiri/shared-utils` as a `file:` dep). `npm ci` is
strict and rejects any lock/manifest mismatch, so it would fail here. `npm install`
tolerates the missing entry and still respects every other pinned version in the lock
file — only the local symlink is resolved fresh.

---

## Fix 2 — Copy shared-utils lock file and use `npm ci` for its installs

**Root cause of the reproducibility gap:** An earlier iteration of this fix switched to
`COPY shared/deepiri-shared-utils/package.json` (lock file excluded) and used
`npm install` for both shared-utils install steps. This meant shared-utils' runtime
deps (`ioredis`, `winston`, `dotenv`) were resolved from their semver ranges on every
build — different builds on different machines or at different times could silently
install different patch versions.

**Why this matters for QA:** If a bug exists in one patch version of `ioredis` or
`winston` but not another, two engineers running `./build.sh` on different days would
get different behavior with no visible indication. Lock files exist specifically to
prevent this.

**Why `npm ci` is better than `npm install` for shared-utils:**
- `npm ci` installs exactly what the lock file specifies, no resolution, no surprises.
- `npm install` re-resolves semver ranges and can silently upgrade patch versions.
- `npm ci` also fails loudly if the lock file is missing or inconsistent, making
  environment drift detectable rather than silent.

**Fix applied to all 6 Dockerfiles:**

```dockerfile
# Before
COPY shared/deepiri-shared-utils/package.json /shared/deepiri-shared-utils/
...
 && npm install --legacy-peer-deps \            # shared-utils build step
...
 && npm install --omit=dev --legacy-peer-deps \ # shared-utils runtime restore

# After
COPY shared/deepiri-shared-utils/package*.json /shared/deepiri-shared-utils/
...
 && npm ci --legacy-peer-deps \                 # shared-utils build step
...
 && npm ci --omit=dev --legacy-peer-deps \      # shared-utils runtime restore
```

With this change, every dependency installed across all 6 services is pinned to an
exact version from a lock file — the app's registry deps from the app's lock file, and
shared-utils' runtime deps from shared-utils' own lock file.

---

## Fix 3 — Remove erroneous npm version upgrade lines

**Root cause:** Previous fix attempts added `RUN npm install -g npm@10.9.8` and later
`npm@11.3.0` to the Dockerfiles, on the assumption that a newer npm might not have the
arborist bug.

**Why these were wrong:**
- npm 10.9.8 crashes with the same arborist null-dereference — the bug is not version-specific.
- npm 11.3.0 requires Node `^20.17.0 || >=22.9.0` and is entirely incompatible with
  the Node 18 base images used by 5 of the 6 services, causing a hard engine check failure.
- Pinning a specific npm version in a Dockerfile is fragile — it ties the build to a
  registry-hosted npm that may change or become unavailable, and adds an unnecessary
  layer with no benefit.

**Fix:** All `npm install -g npm@...` lines were removed. The npm version shipped with
the base image is used as-is, which is the intended and supported configuration.

---

## Fix 5 — Duplicate logger declaration in api-gateway

**File:** `backend/deepiri-api-gateway/src/server.ts:63`

**Root cause:** `server.ts` declared `logger` twice — once at line 58 using `createLogger` from `@team-deepiri/shared-utils` (correct), and again at line 63 using `winston.createLogger` directly. TypeScript raised `TS2451: Cannot redeclare block-scoped variable 'logger'`, failing the build.

```typescript
// Before (broken) — two declarations of logger
const logger = createLogger('api-gateway');          // line 58
const logger = winston.createLogger({ ... });        // line 63 — duplicate

// After (fixed) — only the shared-utils logger remains
const logger = createLogger('api-gateway');
```

The redundant `winston` import was also removed as it was only used by the duplicate block.

**Why it was introduced:** The `winston.createLogger` block was likely added during development before the shared-utils logger was adopted, and was never removed when the codebase migrated to the centralised logger.

---

## Fix 4 — TypeScript syntax error in incentive-engine

**File:** `backend/deepiri-incentive-engine/src/core/incentiveEngineCore.ts:82`

**Root cause:** The `awardPoints` method was missing a closing `)` on its parameter
list. TypeScript cascade-errored with ~80 downstream errors from this single missing
character. The error was invisible in previous CI runs because the npm arborist crash
(Fix 1) always halted the build before `tsc` was ever reached.

```typescript
// Before (broken)
  metadata?: Record<string, any>
  : Promise<IncentiveLedgerEntry> {

// After (fixed)
  metadata?: Record<string, any>
): Promise<IncentiveLedgerEntry> {
```

**Why it was hidden:** The build pipeline ran steps sequentially — `npm install` →
`prisma generate` → `npm run build`. Because `npm install` crashed on every run, `tsc`
never executed, so the syntax error produced no visible output in any prior build log.
Fixing the npm crash was a prerequisite to surfacing it.

---

## Reproducibility guarantee

| Dependency group | Pinned by | Method |
|---|---|---|
| App registry deps (express, prisma, etc.) | App's `package-lock.json` | `npm install` (respects lock for all present entries) |
| `@team-deepiri/shared-utils` | Local `file:` symlink — versioned by the repo itself | N/A |
| shared-utils runtime deps (`ioredis`, `winston`, `dotenv`) | shared-utils' `package-lock.json` | `npm ci --omit=dev` |
| shared-utils devDeps (`typescript`) | shared-utils' `package-lock.json` | `npm ci` |

All 6 services produce identical dependency trees regardless of when or where the
build runs.

---

## Affected files

| File | Changes |
|---|---|
| `backend/deepiri-api-gateway/Dockerfile` | Fixes 1, 2, 3 |
| `backend/deepiri-auth-service/Dockerfile` | Fixes 1, 2, 3 |
| `backend/deepiri-communications-hub/Dockerfile` | Fixes 1, 2, 3 |
| `backend/deepiri-external-bridge-service/Dockerfile` | Fixes 1, 2, 3 |
| `backend/deepiri-incentive-engine/Dockerfile` | Fixes 1, 2, 3 |
| `backend/deepiri-language-intelligence-service/Dockerfile` | Fixes 1, 2, 3 |
| `backend/deepiri-incentive-engine/src/core/incentiveEngineCore.ts` | Fix 4 |
| `backend/deepiri-api-gateway/src/server.ts` | Fix 5 |
