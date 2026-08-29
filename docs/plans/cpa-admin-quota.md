# CPA Channels, Cached Quotas, And Admin Console

```yaml
status: complete
current_milestone: M26
last_completed_milestone: M26
next_action: 0.3.2 已发布；部署时拉取 ghcr.io/haoyang7/quotahub:0.3.2
last_updated: 2026-08-19
branch: release/0.3.2
head: 12dfd4bb5cd3c2dc846afcbc434892bb634062eb
changed_files:
  - README.md
  - backend/app/analytics.py
  - backend/app/cpa_queue.py
  - backend/app/cpa_quota.py
  - backend/app/cpamp_quota.py
  - backend/app/db.py
  - backend/app/logging_config.py
  - backend/app/main.py
  - backend/app/quota_sync.py
  - backend/app/schemas.py
  - backend/tests/test_api_cpa.py
  - backend/tests/test_cpa_queue.py
  - backend/tests/test_cpa_sync.py
  - backend/tests/test_cpamp_quota.py
  - backend/tests/test_db.py
  - backend/tests/test_quota_snapshots.py
  - frontend/src/contexts/QuotaContext.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/quota-cache.ts
  - frontend/src/pages/AccountsPage.tsx
  - frontend/src/pages/AdminLoginPage.tsx
  - frontend/src/pages/DashboardPage.tsx
  - frontend/src/pages/OverviewPage.tsx
  - backend/app/version.py
  - backend/pyproject.toml
  - backend/uv.lock
  - frontend/package.json
  - backend/tests/test_api_cpa.py
  - docs/plans/cpa-admin-quota.md
focused_tests:
  - "M26 CPA endpoint-removal API regression: 7 passed"
  - "M26 full backend suite: 163 passed"
  - "M26 strict TypeScript/Vite build: passed, 1763 modules transformed"
  - "M25 endpoint-generation regression: 3 passed"
  - "M25 unified CPA/CPAMP/database regression: 72 passed"
  - "M22 controlled Docker/browser acceptance: fresh bootstrap, admin auth, CPA wrong-key recovery/exclusive queue, CPAMP query/fallback, public cache-only refresh, persistence, logout, and mobile layout passed"
  - "M20 warm-cache post-pop lease-loss regression: 1 passed"
  - "M20 complete CPA queue regression: 24 passed"
  - "M20 application confirmation dialogs, keyboard focus, responsive layout, and CPA exclusive request smoke: passed"
  - "M19 CPA queue identity, atomic persistence, stale/recovery/logging, CPAMP fallback, and legacy migration regression: 92 passed"
  - "M18 CPAMP identity/ordering, CPA queue mapping, and database migration regression: 53 passed"
  - "M18 legacy CPAMP identity-column migration: 1 passed"
  - "M17 snapshot integrity, CPAMP identity/staleness, and API scheduling regression: 42 passed"
  - "M16 final CPA JSON-string queue and CPAMP discovery/fallback regression: 25 passed"
  - "M13 resumed frontend strict TypeScript/Vite build after four-tab integration: passed"
  - "M13-M15 native CPA queue, CPAMP, migration, API, scheduler, logging, and UI focused regression: 62 passed"
  - "M16 queue poll timestamp regression: 13 passed"
  - "M13 0.3.1 baseline backend: 112 passed, no warnings"
  - "M8 review baseline: 25 passed, 1 Starlette/httpx deprecation warning"
  - "baseline backend: 21 passed, 1 pre-existing time-window failure"
  - "M1 security/database: 13 passed"
  - "M2 authentication/authorization: 15 passed"
  - "M3 snapshots/scheduler/public zero-network APIs: 5 passed"
  - "M4 CPA parser/CRUD/encryption/scheduler: 18 passed"
  - "M5 backend full suite after cross-stack integration: 56 passed"
  - "M6 CPA plaintext-key migration regression: 8 passed"
  - "M7 security/database/HMAC remediation: 37 passed"
  - "M7 leases/scheduler/selective triggers: 21 passed"
  - "M7 public DTO/config contract: 15 passed"
  - "M7 resume public/config regression: 12 passed"
  - "M8 review fixes and logging bundle: 41 passed, 1 Starlette/httpx deprecation warning"
  - "M8 final logging/auth/scheduler hardening: 17 passed, 1 Starlette/httpx deprecation warning"
  - "M9 dependency/runtime regression: 14 passed, no warnings"
  - "M10 passive CPA, migration, API, and usage regression: 43 passed, no warnings"
  - "M11 review-fix baseline: 51 passed, no warnings"
  - "M11 database, secrets, and usage synchronization regression: 26 passed, no warnings"
  - "M11 CPA parsing and collection regression: 33 passed, no warnings"
  - "M11 administrator API regression: 8 passed, no warnings"
  - "M11 snapshots and safe logging regression: 15 passed, no warnings"
  - "M12 backend regression and dependency audit: 112 passed, no known vulnerabilities"
full_verification:
  - "M26 backend full suite: 163 passed; frontend strict build: passed"
  - "M26 version, compileall, diff, staged path, and credential-pattern scans: passed"
  - "M26 Docker build: passed, quotahub:0.3.2-rc sha256:1231283a976d127ad01d95b01c3ac4cf8b55d4ba59c3753a18277f0ad8e5a2f8"
  - "M26 Docker runtime smoke: /api/health passed and OpenAPI reported version 0.3.2"
  - "M26 local Trivy scan not run: trivy CLI is not installed; remote CI gate remains required"
  - "M25 final backend suite: 162 passed, no warnings"
  - "M25 strict TypeScript/Vite build: passed, 1763 modules transformed"
  - "M25 Python compileall, version check, and git diff check: passed"
  - "M25 Docker build: passed, quotahub:0.3.1-rc sha256:ccfb0d57b5d8c96a2ff5b43eb7802c49c0630ed44e1afb172831b96eacbf3bdf"
  - "M25 Trivy 0.73.0 fixable MEDIUM/HIGH/CRITICAL gate: zero findings"
  - "M25 controlled browser acceptance: single CPA tab, mutually exclusive sources, endpoint validation, exclusivity reconfirmation, no native alert/confirm, accessibility labels/tooltips, and 390x844 layout passed"
  - "M25 SQLite and application-log sentinel scans: no raw fixture identity, auth_index, keys, IP, User-Agent, queue-private fields, or plaintext credentials; configured CPA/CPAMP keys are fernet:v1 ciphertext"
  - "M25 Gitleaks exact tracked-diff scan: no leaks found"
  - "M25 GitNexus compare: 511 changed symbols, 153 affected flows, 34 indexed files; expected cumulative CRITICAL release scope"
  - "M22 real QuotaHub container with isolated protocol-faithful CPA/CPAMP stub: passed; no real upstream credentials or ChatGPT requests used"
  - "M22 privacy checks: public DTO, SQLite, and application logs contain no raw fixture identity, auth_index, management key, queue private fields, or internal channel IDs"
  - "M22 recovery: container restart retained session, settings, and quota snapshots; all three schedulers restarted with a new owner and no duplicate upstream sync"
  - "M21 final backend suite: 154 passed, no warnings"
  - "M21 strict TypeScript/Vite build: passed, 1763 modules transformed"
  - "M21 pip-audit and pnpm audit: no known vulnerabilities"
  - "M21 Docker build/runtime smoke: passed, sha256:9081ed37b73c4f807f29bf5d738dac8efc5090c27b1c351167753067c4d40946"
  - "M21 Trivy 0.73.0 fixable MEDIUM/HIGH/CRITICAL gate: zero findings"
  - "M21 UV/source packages and release notes: contents, exclusions, blank Secrets, image owner, and deployment guidance passed"
  - "M21 Gitleaks 8.28.0 release-package scan: no leaks found"
  - "M21 Gitleaks 8.28.0 staged diff scan: no leaks found, approximately 261 KB scanned"
  - "M21 GitNexus compare: 419 indexed symbols, 82 affected flows, 33 product files; expected cumulative CRITICAL release scope"
  - "M21 git diff check: passed"
  - "M20 final backend suite: 154 passed, no warnings"
  - "M20 GitNexus compare: 232 changed symbols, 82 affected flows, 28 indexed product files; cumulative CRITICAL release scope"
  - "M20 strict TypeScript/Vite build and git diff check: passed"
  - "M19 final backend suite: 154 passed, no warnings"
  - "M19 final strict TypeScript/Vite build and version check: passed"
  - "M19 pip-audit and pnpm audit: no known vulnerabilities"
  - "M19 Docker build: passed, sha256:ea3fb5446d1b38c984acbd68de46091422f194827a496a8b304f0d1618b5d685"
  - "M19 Trivy 0.73.0 fixable MEDIUM/HIGH/CRITICAL gate: zero findings"
  - "M19 UV/source packages: expected README, blank-secret .env.example, and compiled SPA present; forbidden local/data paths absent"
  - "M19 Gitleaks 8.28.0 release-package scan: no leaks found"
  - "M19 git diff check: passed"
  - "M19 GitNexus compare: 230 changed symbols, 151 affected flows, 28 indexed files; complete and cumulative CRITICAL release scope"
  - "M18 final backend suite: 148 passed, no warnings"
  - "M18 final strict TypeScript/Vite build: passed"
  - "M18 git diff check and credential/artifact scan: passed; documented placeholders only"
  - "M18 GitNexus compare: 210 changed symbols, 146 affected flows, 28 indexed files; complete and cumulative CRITICAL release scope"
  - "M17 final backend suite: 140 passed, no warnings"
  - "M17 final strict TypeScript/Vite build: passed"
  - "M17 git diff check: passed"
  - "M17 GitNexus compare: 183 changed symbols, 77 affected flows, 28 indexed files; cumulative CRITICAL release scope"
  - "M16 final backend suite after review fixes: 131 passed, no warnings"
  - "M16 final strict TypeScript/Vite build after review fixes: passed"
  - "M16 final pip-audit and pnpm audit: no known vulnerabilities"
  - "M16 final Docker build: passed, sha256:70080a0ce46721856b3a6dfe13625885f094be5729a7ddec0d1219892ffc7624"
  - "M16 final Trivy 0.73.0 fixable MEDIUM/HIGH/CRITICAL gate: zero findings"
  - "M16 final runtime smoke: health passed, version 0.3.1, local +08:00 log timestamps, no access log/raw client IP"
  - "M16 final UV/source archives and release notes: contents, blank Secrets, compiled SPA, CPA/CPAMP modules, image owner, and forbidden-path checks passed"
  - "M16 final GitNexus compare: 180 changed symbols, 78 affected flows, 28 indexed files; cumulative CRITICAL release scope"
  - "M16 final candidate scan: 32 product files, zero credential-pattern findings; local instructions/plans and browser artifacts excluded"
  - "M13 0.3.1 baseline strict TypeScript/Vite build: passed"
  - "M16 backend pre-delivery full suite: 126 passed"
  - "M16 strict TypeScript/Vite build: passed"
  - "M16 pip-audit and pnpm audit: no known vulnerabilities"
  - "M16 Docker build after Debian security upgrade: passed, sha256:7cebf349e94fb2e47e12f8f3f8ced74f09f7b17cc38b4edb5ca6219e4d8ad4e5"
  - "M16 Trivy 0.73.0 fixable MEDIUM/HIGH/CRITICAL gate: zero findings"
  - "M16 Playwright: four tabs, CPA exclusive confirmation/reconfirmation, CPAMP windows/source, public overview/quota, and 390px layout passed"
  - "baseline frontend build: passed"
  - "M5 strict TypeScript/Vite build: passed"
  - "M5 Playwright smoke: public navigation, admin login, CPA create, settings, usage, 390px layout passed"
  - "M6 backend full suite: 57 passed, 1 Starlette/httpx deprecation warning"
  - "M6 strict TypeScript/Vite build: passed"
  - "M7 strict TypeScript/Vite build after DTO/cache/settings changes: passed"
  - "M7 release notes rendered and UV/source package contents verified"
  - "M7 final backend suite: 69 passed, 1 Starlette/httpx deprecation warning"
  - "M7 final strict TypeScript/Vite build after cache write-back: passed"
  - "M7 Docker build: passed, sha256:b9c5f58b26f9a934df4133ecedd5612dea41a8023693a3db3a7a5ff1c6224700"
  - "M7 Playwright: settings dirty/save/failure-draft states and 390x844 layout passed"
  - "M7 final diff, secret, public-ID, SQLite, archive, browser-artifact, and generated-file scans: passed"
  - "M6 Docker build: passed, sha256:c31bc87837b404e9392b9eb096d38e65b50c2223800b44cc50ba7abc3380ebc9"
  - "M6 diff, secret, account-sample, SQLite, Playwright-artifact, and generated-file scans: passed"
  - "M8 final backend suite: 83 passed, 1 Starlette/httpx deprecation warning"
  - "M8 final strict TypeScript/Vite build: passed"
  - "M8 Playwright: CPA Pro 20x/windows rendering and edit-after-disable regression passed"
  - "M8 final Docker build: passed, sha256:6b4dce44379fb67d1b61c18245b87574f98c113e148b13ae880beeba61568e5a"
  - "M8 Uvicorn runtime smoke: health request passed with no access log or raw client IP"
  - "M8 final diff, logging-contract, secret, account-sample, SQLite, archive, browser-artifact, and generated-file scans: passed"
  - "M9 final backend suite: 83 passed, no warnings"
  - "M9 final strict TypeScript/Vite build: passed"
  - "M9 pip-audit 2.9.0: no known vulnerabilities"
  - "M9 pnpm audit, including production-only audit: no known vulnerabilities"
  - "M9 Docker build: passed, sha256:ae037ed01f24d4e1e6ed862deb1368022f085215be353d82c8e65fbef1c78c60"
  - "M9 Trivy 0.73.0 fixable MEDIUM/HIGH/CRITICAL gate: zero findings"
  - "M9 Trivy informational scan: 83 Debian findings without fixed versions (60 MEDIUM, 19 HIGH, 4 CRITICAL); application packages and uv binaries have zero findings"
  - "M9 runtime smoke: health passed, no access log/raw client IP, no startup dependency synchronization, Node, node_modules, or development packages"
  - "M9 workflow YAML, shell syntax, diff formatting, release packages, secret, SQLite, archive, browser-artifact, and generated-file scans: passed"
  - "M10 final backend suite: 94 passed, no warnings"
  - "M10 final strict TypeScript/Vite build: passed"
  - "M10 Docker build: passed, sha256:17943ef9a718138acc5100829af96fe00a06fa17ba6005491e2c920b140519ec"
  - "M10 Playwright public quota: CPA URL hidden and reset countdown derived dynamically from reset_at"
  - "M10 Playwright administrator account detail: usage tab performed local GET only and did not POST usage/sync on mount"
  - "M10 version/tag check, workflow YAML, shell syntax, diff formatting, UV/source packages, blank Secret, repository artifact, and secret scans: passed"
  - "M10 GitNexus compare review: 334 changed symbols and 113 affected flows; cumulative risk CRITICAL because the implementation spans authentication, persistence, schedulers, APIs, and frontend contracts"
  - "M11 final backend suite: 112 passed, no warnings"
  - "M11 strict TypeScript/Vite production build: passed"
  - "M11 Python compileall and git diff formatting checks: passed"
  - "M11 Docker build: passed, sha256:cd73508a629512fd2354b83ab49668b85ade13586a4661f18ab1a4908809b9ee"
  - "M11 container health smoke: passed with no Uvicorn access log or raw client IP"
  - "M11 UV/source packages: generated, extracted, version/blank-Secret/SPA contents verified, and forbidden-path scan passed"
  - "M11 final changed-file, package-content, credential-pattern, account-sample, SQLite, archive, browser-artifact, bytecode, and generated-file scans: passed"
  - "M11 staged GitNexus review: 658 changed symbols and 135 affected flows across 63 candidate files; cumulative risk CRITICAL because the complete 0.3.0 delivery spans authentication, encrypted migrations, schedulers, APIs, and frontend contracts"
  - "M12 no-cache Docker build: passed, sha256:50a130eb0d96050ec20364c85491eec53d1198a779a984249d0a09621c71d8f5"
  - "M12 Trivy 0.73.0 fixable MEDIUM/HIGH/CRITICAL gate: zero findings"
  - "M12 runtime filesystem/import/health smoke: passed without global pip or ensurepip"
  - "M12 frontend audit and strict TypeScript/Vite build: passed, no known vulnerabilities"
  - "M12 actionlint 1.7.12, diff formatting, credential-pattern scan, and GitNexus review: passed; risk LOW with no affected application flows"
  - "M12 fork Pull Request CI run 31768110172: backend, frontend, container build, and Trivy all passed"
blockers: []
```

This document is the source of truth for the implementation and handoff. It must
never contain administrator tokens, Fernet keys, cookies, real account identifiers,
or captured private upstream responses.

## Resume Protocol

1. Read `AGENTS.md` and this document completely.
2. Run `git status --short` and `git rev-parse HEAD`.
3. Compare the worktree with `changed_files` and the latest Handoff Log. Preserve
   unrelated user changes, including the existing untracked `AGENTS.md`.
4. Re-run the last focused test before continuing `next_action`.
5. Keep at most one milestone `in_progress`.
6. Before stopping, update the YAML status and append a Handoff Log entry with
   behavior completed, files changed, exact verification, blockers, and the next
   executable command.

## Decisions

- Anonymous users can only view `/` overview and `/quota` account quotas.
- Management, CPA channels, usage logs, and settings are in `/admin/login`,
  `/admin/accounts`, `/admin/usage`, and `/admin/settings`.
- One high-entropy `QUOTAHUB_ADMIN_TOKEN` is required; it must have at least 32
  characters and is never stored in SQLite. Missing or invalid configuration
  prevents startup.
- Login creates an opaque browser-session cookie (`HttpOnly`, `SameSite=Strict`),
  stores only its hash, and enforces a server-side 24-hour hard expiry. State-
  changing requests require a CSRF cookie and matching `X-CSRF-Token` header.
- Login failures are limited to five attempts per source IP in fifteen minutes.
- `QUOTAHUB_COOKIE_SECURE` controls the Secure cookie flag. CORS is same-origin,
  not permissive credentialed CORS.
- `QUOTAHUB_ENCRYPTION_KEY` must be a valid `Fernet.generate_key()` key. Missing,
  invalid, or unusable keys prevent startup.
- CPA management keys, OpenCode auth cookies, and Ollama session cookies use
  versioned `fernet:v1:` ciphertext. Existing plaintext values are migrated in one
  verified transaction; failure rolls the migration back.
- CPA, OpenCode, and Ollama quota pages read SQLite snapshots only. Browser refresh
  never calls an upstream quota endpoint.
- OpenCode and Ollama use service-level collection intervals. CPA uses per-channel
  intervals. Defaults are 1,800 seconds; the server minimum is 300 seconds.
- Only the newest snapshot is retained. Failed attempts retain the last successful
  value and mark it stale. Disabled sources stop collection, disappear publicly,
  and retain snapshots until deletion.
- No manual upstream refresh API exists. Create, credential change, and re-enable
  enqueue one immediate background collection.
- Native CPA quota collection never calls ChatGPT. It discovers accounts through
  `/v0/management/auth-files` and consumes only the destructive HTTP
  `/v0/management/usage-queue` after an explicit administrator confirmation that
  QuotaHub is the only HTTP consumer and that no RESP subscriber exists.
- CPA disable, URL change, management-key change, or disable/re-enable clears the
  exclusive confirmation. Queue consumption remains off until it is confirmed
  again; existing historical `active_api` snapshots remain readable only.
- CPAMP is a separate channel type. It reads persisted quota snapshots through
  `/v0/management/quota-snapshots/query` and falls back to read-only monitoring
  header snapshots only on 404/405. It never calls `/api-call` or ChatGPT.

> **Superseded by `docs/plans/realtime-quota-and-refresh.md` (2026-08-28).** The two
> decisions above are now historical: a synchronous manual-refresh admin API was
> added (OpenCode/Ollama/CPA), and `cpamp_snapshot` now reads CPA's in-memory
> `quota.signals` from `/auth-files` as the primary source, with
> `quota-snapshots/query` and `header-snapshots` demoted to compatibility
> fallbacks. The `/api-call` and ChatGPT `wham/usage` exclusion still stands. See
> the newer plan for the plan-arbitration (`plan_observed_at`), auth-files signal
> parser, and masked account-workbench details. This file's history is preserved
> unchanged.

## Security And Persistence

- Public APIs are `/api/public/*` and `/api/health`; administrator APIs are under
  `/api/admin/*`. FastAPI dependencies enforce authorization; React guards only
  redirect unauthenticated pages.
- Session records store token hash, created/expiry/last-used timestamps. Expired
  sessions are cleaned during authentication and startup.
- Existing secret columns store ciphertext after migration. Legacy `config.json`
  values are encrypted before database insertion; operators remove the legacy file
  after successful import.
- Snapshot tables store normalized windows, success/stale flags, sanitized errors,
  timestamps, and public IDs. CPA rows are keyed by channel and a Fernet-derived
  account HMAC; raw file names and auth indexes never leave collection memory.
- CPA rows retain historical quota-source metadata and now record queue status,
  exclusive-confirmation time, last real queue poll, last event, and controlled
  error codes. CPAMP rows record the read-only snapshot source and source time.
  These fields contain no upstream identity material.
- Database initialization and migrations are idempotent for existing SQLite files.

## Collection

- The ordinary quota scheduler owns OpenCode, Ollama, CPA account discovery, and
  CPAMP snapshot synchronization. A separate CPA queue scheduler polls every 15
  seconds. Both use SQLite leases plus in-process locks and stop starting requests
  after lease loss.
- Next due time is based on the completed attempt. Failures wait the full interval.
- Native CPA protocol:
  1. Discover enabled Codex accounts through `/v0/management/auth-files` at the
     configured channel interval.
  2. Before queue consumption, check `/v0/management/usage-statistics-enabled`.
  3. Only for enabled, explicitly confirmed channels, pop up to 100 events from
     `/v0/management/usage-queue`; process at most ten batches per cycle.
  4. Whitelist `provider=codex`, `auth_index`, timestamp, and `x-codex-*` response
     headers in memory. Already-popped batches finish safe persistence after lease
     loss, but are discarded if the channel was deleted, disabled, or revised.
- CPAMP protocol:
  1. Discover Codex accounts through `/v0/management/auth-files` when available.
  2. Query `/v0/management/quota-snapshots/query` in batches of at most 200.
  3. On 404/405, read
     `/v0/management/monitoring/header-snapshots?days=30&limit=5000`; when account
     discovery is unavailable, build the one-run memory mapping from snapshot
     identity fields.
- Parse primary/secondary windows, used percentage, reset time, reset-after seconds,
  and duration. 401/403 is authentication failure, never zero quota.
- Plans map `free -> Free`, `plus -> Plus`, `prolite/pro-lite/pro_lite/5x -> Pro 5x`,
  `pro/20x -> Pro 20x`; unknown values display `未知套餐`.
- Account display uses email, then account, then ChatGPT account ID. Email becomes
  `a***@example.com`; other identifiers retain safe edge characters. Raw identifiers
  exist only during one collection and are never persisted or returned.
- Per-account failures are isolated. Channel authentication failures stop the
  channel and preserve old snapshots.

## API Contracts

Public:

- `GET /api/public/quota`: grouped OpenCode, Ollama, and CPA snapshots.
- `GET /api/public/overview`: overview computed from snapshots.
- `GET /api/public/analytics/opencode/daily` and `/models`: local aggregates.
- Public payloads include display names, masked CPA accounts, plans, windows,
  stale/error state, and timestamps, but no internal IDs, credentials, or mutation
  controls. Old quota paths remain snapshot-only deprecated aliases for one release.

Administrator:

- `/api/admin/auth/{login,session,logout}`.
- `/api/admin/accounts/opencode/*`: CRUD, tests, cached quota, usage, sync/backfill.
- `/api/admin/accounts/ollama/*`: CRUD and cached quota.
- `/api/admin/cpa/channels/*`: multi-channel CRUD plus explicit
  `/channels/{id}/usage-queue` enable/disable. Create requires a key; an empty
  update key preserves ciphertext. Responses never expose key, mask, or configured
  flag.
- `/api/admin/cpamp/channels/*`: independent CPAMP CRUD with the same encrypted-key
  and partial-update contract.
- `/api/admin/config` and `/api/admin/usage/*` are protected.
- Unauthenticated legacy management routes are removed.

## Frontend

- Public layout shows overview, quota, and a management icon.
- Admin layout shows account management, usage, settings, return-to-public, logout.
- Accounts has OpenCode, Ollama, native CPA, and CPAMP tabs. Every provider has a
  direct enabled switch; channel mutations share record-level pending locks.
- CPA cards show masked account, Free/Plus/Pro plan, quota windows, stale/error
  state, and last successful update.
- Public polling reloads cached APIs every 60 seconds and never triggers collection.

## Milestones

- **M0 Documentation/baseline:** create this file, record HEAD/worktree, run
  unchanged backend tests and frontend build.
- **M1 Security/migration:** environment validation, Fernet helpers, plaintext
  migration, session persistence, focused database/encryption tests.
- **M2 Admin boundary:** login/logout/CSRF/rate limit, protected routers, public/admin
  contract and authorization matrix.
- **M3 Snapshots:** OpenCode/Ollama snapshot tables, scheduler, cached public APIs,
  settings migration, zero-network public request tests.
- **M4 CPA backend:** channel CRUD, encrypted keys, discovery, usage parser, masking,
  plan mapping, failure isolation, and per-channel scheduling.
- **M5 Frontend:** public/admin layouts, login, protected routes, tabs, switches,
  settings, grouped CPA quota cards.
- **M6 Delivery:** README/Docker updates, full tests, frontend build, Docker build,
  diff/security scan, and final handoff.
- **M7 Review remediation and 0.3.0 delivery:** harden deployment secrets and
  release artifacts, migrate deterministic CPA fingerprints to keyed HMAC,
  invalidate sessions on administrator-token rotation, persist login throttling,
  add SQLite scheduler leases and task-failure isolation, narrow immediate quota
  triggers, replace settings autosave, migrate public caches/IDs, and deliver the
  corrected `ghcr.io/haoyang7/quotahub` 0.3.0 release inputs.
- **M8 Review fixes and operational logging:** propagate scheduler lease loss
  through multi-request collectors, correct CPA plan parsing and console bootstrap,
  make login throttling atomic, fix administrator quota/forms, centralize versioning,
  and add secret-safe application and scheduler event logs.
- **M9 Dependency and container security remediation:** patch React Router,
  PostCSS, and NanoID advisories, add Starlette's supported `httpx2` test backend,
  move build/CI to a supported Node LTS, replace the vulnerable Bookworm runtime
  base, and require clean application and final-image vulnerability scans.
- **M10 Passive CPA snapshots and final review remediation:** prefer CPA-Manager-
  Plus response-header snapshots with strict account matching, retain a fixed
  twelve-hour active fallback, add source/observation/throttle migrations, and fix
  the remaining usage lease, legacy disabled import, public CPA URL, dynamic reset
  countdown, account-detail auto-fetch, and release-version validation findings.
- **M11 Final review and release-candidate hardening:** add collection revisions,
  guarded writes, stable CPA identity migration, secure plaintext cleanup, safe
  error codes, complete regression verification, and prepare the 0.3.0 candidate.
- **M12 CI and container remediation:** remove unused vulnerable pip-vendored
  components from the final runtime image, keep the Trivy gate enabled, make CI
  permissions explicit, resolve action-runtime deprecations where safely
  verifiable, and restore a green candidate workflow before release.
- **M13 Native CPA queue and migration:** add queue state columns and idempotent
  upgrade defaults, remove all active/header native CPA collection, implement
  exclusive confirmation, queue parsing, batching, leases, and privacy tests.
- **M14 CPAMP read-only snapshots:** add independent encrypted CPAMP channels and
  snapshot tables, query batching, header fallback, stale/batch isolation, public
  DTOs, and multi-channel scheduler coverage.
- **M15 Four-provider frontend and operations:** add four administrator tabs,
  independent pending locks, exclusive confirmation/reconfirmation, CPAMP source
  rendering, public overview/quota sections, local log time zones, and deployment
  documentation.
- **M16 0.3.1 delivery:** align versions and packages, run full backend/frontend,
  browser, Docker, audit and Trivy verification, review the complete GitNexus
  impact, scan secrets/artifacts, and write the final resumable handoff.
- **M17 Post-review data integrity fixes:** preserve quota-derived plans during
  discovery, migrate CPAMP identities to subject-aware HMACs, bound Header
  Snapshot freshness, and avoid polling when a repeated key schedules no sync.
- **M18 Identity continuity and ordering hardening:** complete CPAMP locator/subject
  migration, reject historical replacement snapshots, preserve equal-observation
  recovery semantics, and refresh native CPA mappings before destructive pops.
- **M19 Release-blocking queue and fallback remediation:** add native CPA
  locator/subject acceptance barriers, transactional popped-batch persistence with
  bounded retry, authoritative CPAMP Header fallback filtering, queue-driven stale
  state, configured-frequency account discovery, and quiet idle queue logging.

Only one milestone may be `in_progress`; each milestone is complete only after its
focused tests pass and this document is updated.

## Verification

- Test fresh/legacy/repeated migrations, wrong keys, cascade deletion, disabled
  snapshots, and absence of plaintext secrets.
- Test missing environment values, login throttling, session expiry/logout, cookie
  flags, CSRF, and anonymous `401/403` management responses.
- Test multi-channel discovery, plans, windows, masking, auth short-circuit,
  account isolation, stale snapshots, and scheduler single-flight behavior.
- Patch network clients to fail if invoked by public quota/overview requests.
- Run `cd backend && uv run python -m pytest -q`.
- Run `cd frontend && corepack pnpm@10.33.0 build`.
- Run `docker build .` when runtime inputs change.
- Scan final diff/database for secrets, local state, generated files, and unexpected
  lockfile changes.

## Handoff Log

### 2026-08-11 - M0 started

- Created the implementation and handoff document.
- No application code has been changed yet.
- Preserved the existing untracked `AGENTS.md`.
- Next command: run baseline backend tests and frontend build, then record HEAD and
  results in the YAML status block.

### 2026-08-11 - M0 completed

- Baseline HEAD: `fd0dd87e15df9b56d28c6d188ce7b302509fc80c`.
- Baseline frontend TypeScript/Vite build passed.
- Baseline backend result: 21 passed, 1 failed. The existing
  `test_list_all_usage_records_and_daily_stats` fixture uses the fixed date
  `2026-07-09`, which is outside its rolling 30-day query window on 2026-08-11.
  This pre-existing time-sensitive test must use a current UTC-derived date before
  final verification.
- M1 is now in progress.
- Next command: add the Fernet dependency and implement environment/secret helpers
  with focused migration tests.

### 2026-08-11 - M1 completed

- Added strict administrator-token and Fernet-key validation.
- Added randomized versioned Fernet encryption for OpenCode and Ollama credentials,
  including idempotent verified migration of legacy plaintext rows.
- Added hashed administrator session persistence and expiry cleanup.
- Updated the time-window database test to derive its fixture date from current UTC.
- Focused result: 13 passed.
- Next command: implement authentication endpoints and protect all management APIs,
  then run the authorization matrix.

### 2026-08-11 - M2 completed

- Added token login, opaque hashed sessions, browser-session cookies, CSRF checks,
  logout, expiry handling, and login throttling.
- Moved account, configuration, and all-usage management APIs under `/api/admin`;
  anonymous legacy management paths are no longer available.
- Removed permissive credentialed CORS.
- Focused result: 15 passed.
- Next command: add provider snapshot persistence and convert all public quota and
  overview routes to zero-network database reads.

### 2026-08-11 - M3 completed

- Added latest-snapshot persistence for OpenCode and Ollama, including stable
  public IDs, failure preservation, stale state, disabled-account filtering, and
  cascade deletion through account foreign keys.
- Added one serial quota scheduler with provider intervals, account pacing,
  immediate wakeups after account/config changes, and no overlapping collection.
- Converted public quota, overview, and compatibility quota routes to SQLite-only
  reads. Added public daily analytics aliases.
- Added service-level quota collection settings with a 1,800-second default and
  300-second server minimum, including legacy refresh-setting migration.
- Focused result: 5 passed. Full backend result at this point: 34 passed.
- Next command: add CPA channel/snapshot tables and the sanitized CLIProxyAPI
  collector/parser, then add authenticated CRUD and scheduler tests.

### 2026-08-11 - M4 completed

- Added multi-channel CPA persistence with encrypted management keys, per-channel
  intervals, enable/disable state, sync state, cascade deletion, and retained
  latest account snapshots.
- Added fixed CLIProxyAPI discovery and proxy-call clients, flexible sanitized
  quota parsing, plan mapping, account masking, disabled-account filtering,
  per-account failure isolation, and channel-authentication short circuiting.
- Raw account identifiers and auth indexes are collection-memory only; SQLite
  stores masked display names, random public IDs, and an internal one-way matching
  fingerprint that is never exposed by an API.
- Added authenticated/CSRF-protected CPA CRUD. Management API responses do not
  expose the key, a key mask, or a configured flag.
- Focused result: 18 passed.
- Next command: split public/admin React routing and add the CPA management tab,
  switches, grouped quota cards, and cached-only public polling.

### 2026-08-11 - M5 completed

- Public UI now contains only overview and quota pages plus a management icon.
  Public polling reads `/api/public/quota` every 60 seconds.
- Added administrator session context, login page, guarded admin layout, logout,
  account/usage/settings routes, and automatic CSRF headers on admin writes.
- Added direct enable switches for OpenCode, Ollama, and CPA; added CPA channel
  create/edit/delete forms and grouped masked account summaries.
- Added public CPA cards with plan, windows, stale/error state, and last-success
  time. Settings now control backend collection intervals rather than browser
  upstream refreshes.
- Strict TypeScript/Vite build passed. Playwright smoke covered anonymous pages,
  login, CPA creation without key disclosure, settings, usage, and a 390x844
  mobile viewport. Temporary browser artifacts and database were removed.
- Full backend result at this point: 56 passed.
- Next command: update deployment/upgrade documentation and examples, run Docker
  build plus final tests/security scans, then mark the plan complete.

### 2026-08-11 - M6 completed

- Completed deployment, environment-variable, backup, upgrade, HTTPS-cookie, and
  CPA `allow-remote` documentation in README and examples.
- Added a CPA legacy-plaintext management-key migration regression covering two
  consecutive bootstrap runs, ciphertext persistence, and successful decryption.
- Full backend verification passed: 57 tests. The only warning is the existing
  Starlette TestClient/httpx deprecation notice.
- Strict TypeScript/Vite production build passed.
- Docker build passed with image
  `sha256:c31bc87837b404e9392b9eb096d38e65b50c2223800b44cc50ba7abc3380ebc9`.
- Final diff formatting and whole-source scans found no Fernet-shaped keys, real
  CPA account samples, SQLite files, `.playwright-cli` directories, or tracked
  generated artifacts. Sanitized account fixtures use only `example.com`.
- The user's existing untracked `AGENTS.md` remains unmodified and untracked. No
  files were staged or committed.
- Known issue: the upstream Starlette/httpx deprecation warning remains; it does
  not affect the passing suite.
- Next command for review: `git status --short`.

### 2026-08-11 - README scope adjustment

- Restored the original introduction, acknowledgements, deployment comparison,
  Release/UV/source instructions, and technology-stack wording.
- Kept only the documentation required by the implemented behavior: mandatory
  administrator/encryption variables, HTTPS cookies, administrator entry point,
  CPA multi-channel configuration, low-frequency cached collection, migration
  safety, and the current public/admin API paths.
- README now differs from the baseline by 62 insertions and 16 deletions instead
  of a broad rewrite. No application code changed in this adjustment.
- Documentation diff formatting passed. No tests were rerun for this docs-only
  adjustment; the preceding M6 verification remains current.
- The user's untracked `AGENTS.md` remains untouched. No files were staged or
  committed.
- Next command for review: `git diff -- README.md`.

### 2026-08-11 - README final direction

- At the user's request, restored the newer task-oriented README because its
  administrator, encryption, CPA, collection, and upgrade guidance is more direct.
- Added [QuotaHub](https://github.com/lvmiao233/QuotaHub) to acknowledgements as
  the upstream project, while retaining the LinuxDo and opencode-cc credits.
- This entry supersedes the preceding README scope adjustment as the final chosen
  documentation direction. No application code changed.
- README diff formatting passed. Tests were not rerun for this docs-only change;
  the completed M6 verification remains current.
- No files were staged or committed, and the user's untracked `AGENTS.md` remains
  untouched.
- Next command for review: `git diff -- README.md`.

### 2026-08-11 - M7 started after review

- Reopened the completed plan after a full scheme and code review found release,
  scheduler, low-frequency collection, upgrade-cache, and security-hardening gaps.
- Locked the remediation decisions: SQLite leases for quota and usage schedulers,
  HMAC CPA fingerprints with legacy SHA compatibility, immediate session
  invalidation after administrator-token rotation, explicit settings save, version
  0.3.0, blank Secret examples, and `ghcr.io/haoyang7/quotahub` release images.
- Review verification before implementation: backend 57 passed with one existing
  Starlette/httpx deprecation warning; strict TypeScript/Vite build passed.
- Context7 documentation lookup was attempted as required but its configured
  monthly quota was exhausted; repository lockfiles and tests remain authoritative.
- No files were staged or committed. The existing untracked `AGENTS.md` remains
  untouched.
- Next command: implement focused security/database migrations and tests.

### 2026-08-11 - M7 security and migration checkpoint

- Added idempotent `security_state`, `admin_login_attempts`, and
  `scheduler_leases` tables and stable quota-snapshot backfill for legacy OpenCode
  and Ollama accounts.
- Administrator token fingerprints now use a Fernet-derived, domain-separated
  HMAC. First upgrade or token rotation transactionally revokes all administrator
  sessions; unchanged-token restarts preserve them.
- Login throttling now shares SQLite across clients and stores only a
  domain-separated source-IP HMAC. Successful login clears persisted failures.
- CPA account matching now uses `hmac:v1:` fingerprints and atomically upgrades
  legacy SHA-256 snapshot keys while preserving public IDs and quota data.
- Focused verification: 37 passed; only the existing Starlette/httpx deprecation
  warning remains.
- Next command: implement SQLite lease acquisition/renewal/release and scheduler
  fault/TOCTOU tests.

### 2026-08-11 - M7 scheduler and low-frequency checkpoint

- Added atomic SQLite lease acquisition, 30-second heartbeat renewal, 120-second
  expiry takeover, owner-checked release, and a per-process owner regenerated
  after fork. Quota collection and automatic usage synchronization use separate
  lease names plus existing in-process locks.
- Scheduler loops now isolate top-level and per-job failures and stop starting new
  requests after lease loss. Automatic usage synchronization checks each account's
  `last_sync_at + interval` instead of resynchronizing on task restart.
- OpenCode, Ollama, CPA, and usage collection reread source configuration after
  network responses. Deleted, disabled, or credential-changed sources discard old
  results and remain due.
- Account/channel routes now force immediate collection only for enabled creates,
  credential/URL/workspace changes, and re-enable transitions. Display/name
  changes retain the last-attempt timestamp; CPA interval changes only re-evaluate
  normal due time.
- Configuration writes are normalized and compared before persistence. Only real
  usage settings changes restart the usage task, and only real quota settings
  changes wake quota collection.
- Focused verification: 21 passed; only the existing Starlette/httpx deprecation
  warning remains.
- Next command: replace settings autosave and migrate public DTO/cache keys to
  `public_id`-only contracts.

### 2026-08-11 - M7 frontend and public-contract checkpoint

- Split public quota types from administrator quota responses. Public OpenCode and
  Ollama accounts require stable `public_id`; Overview now returns `public_id`
  rather than nullable internal account IDs.
- Removed public-card workspace fields, internal-ID React keys, and public-page
  navigation to administrator account details.
- Upgraded localStorage to the `quotahub:v2:cache:` namespace. First access removes
  legacy cache keys, and quota cache reads/writes rebuild data through an explicit
  field whitelist so internal IDs cannot survive in anonymous state.
- Replaced settings autosave with one explicit save action. It validates all
  numeric bounds, disables controls while saving, submits only changed quota or
  usage sections, and retains drafts after failures.
- Focused backend public/config contract verification: 15 passed. Strict
  TypeScript/Vite production build passed.
- Next command: align release workflows, package contents, examples, image owner,
  and all version declarations to 0.3.0.

### 2026-08-11 - M7 release-input checkpoint

- Aligned backend package, FastAPI, frontend package, CPA user agent, and lockfile
  project metadata to 0.3.0.
- Set README, Compose, workflow, and rendered release notes to
  `ghcr.io/haoyang7/quotahub`. The workflow now passes its resolved image address
  into the release-notes script instead of relying on a second hardcoded owner.
- Left both required Secret values blank in `.env.example`. Docker, UV, Windows,
  and source release instructions all include administrator token, Fernet key,
  and HTTPS-cookie configuration.
- Added README and `.env.example` to the UV package and `.env.example` to the
  source package. Both archives contain `frontend/dist`; packaging now excludes
  Python bytecode caches and `.DS_Store` files.
- Rendered 0.3.0 release notes successfully and generated/inspected both archives
  in temporary directories. README now distinguishes Git clone builds from
  Release archives and documents single-instance 0.3.0 migration before scale-out.
- Next command: run the complete backend suite and strict frontend build, followed
  by Docker build, browser smoke, and final secret/artifact scans.

### 2026-08-11 21:28 CST - M7 completed

- Completed the 0.3.0 review remediation across security migrations, keyed CPA
  fingerprints, persistent login throttling, cross-process scheduler leases,
  stale-result rejection, low-frequency due checks, public DTO/cache isolation,
  explicit settings saves, release inputs, packages, and deployment guidance.
- Final backend verification passed: 69 tests. The only warning is the existing
  Starlette TestClient/httpx deprecation notice.
- Final strict TypeScript/Vite build passed. Docker build passed with image
  `sha256:b9c5f58b26f9a934df4133ecedd5612dea41a8023693a3db3a7a5ff1c6224700`.
- Playwright verified that a settings change enables save, successful save disables
  it, a simulated 500 response retains the draft and retry action, and the
  390x844 layout has no horizontal overflow or overlapping controls.
- Rendered release notes use only `ghcr.io/haoyang7/quotahub:0.3.0`; UV and source
  archives contain the required README, blank-secret example, and compiled SPA.
- Final scans passed for diff formatting, secret-shaped values, non-example account
  samples, public internal IDs, SQLite files, release archives, browser state,
  bytecode, and tracked generated output. Verification processes and temporary
  directories were stopped and removed.
- No files were staged or committed. The existing untracked `AGENTS.md` remains
  unmodified and must be excluded from any later commit.
- Known issue: the upstream Starlette/httpx deprecation warning remains and does
  not affect the passing suite.
- Next command: `git status --short`.

### 2026-08-11 - M8 started after second review

- Reopened the implementation after review confirmed seven remaining defects:
  lease loss was not propagated within CPA account and usage-page loops, CPA plan
  parsing preferred the OAuth account kind, login throttling was non-atomic, the
  console entry point read an uninitialized database, administrator CPA cards did
  not render quota windows, edit forms could restore stale enabled flags, and the
  CPA user agent still reported `QuotaHub/0.3`.
- Logging audit confirmed that scheduler lease failures, collection cycles,
  per-account outcomes, authentication short circuits, discarded stale results,
  and loop recovery were silent. Uvicorn access logs do not cover these events.
- Locked the M8 log contract: CPA-style single-line text on stdout, UTC timestamps,
  fixed event names and allowlisted key/value fields, `INFO` default with
  `QUOTAHUB_LOG_LEVEL`, full keyed HMAC for login sources, and no raw credentials,
  account identifiers, upstream bodies, or free-form exception messages.
- Review baseline passed: 25 focused scheduler, authentication, CPA parser, and
  CPA collection tests; only the existing Starlette/httpx deprecation warning
  remains. The untracked `AGENTS.md` is unchanged.
- Next command: implement the centralized safe logger and focused logging tests.

### 2026-08-12 00:18 CST - M8 completed

- Completed lease-loss propagation through CPA account requests and usage pages,
  corrected CPA plan precedence, made login throttling atomic, bootstrapped the
  console entry point before reading settings, rendered administrator CPA quota
  windows, narrowed edit payloads, and centralized the 0.3.0 version.
- Added secret-safe UTC application logs for administrator actions, scheduler
  leases, actual collection cycles, per-account results, authentication short
  circuits, discarded stale results, and loop recovery. Both event names and
  fields are allowlisted; exception messages and unsupported values are never
  echoed by validation errors.
- Disabled `uvicorn.access` to prevent raw client IP logging. A real local Uvicorn
  health request produced no access-log line while startup, scheduler lifecycle,
  and shutdown logs remained available.
- Final focused verification passed: 17 logging, authentication, and scheduler
  tests. Final backend verification passed: 83 tests. The only warning is the
  existing Starlette TestClient/httpx deprecation notice.
- Strict TypeScript/Vite build passed. Docker build passed with image
  `sha256:6b4dce44379fb67d1b61c18245b87574f98c113e148b13ae880beeba61568e5a`.
  The earlier M8 Playwright run verified CPA Pro 20x/window rendering and that
  saving an already-open edit form cannot restore a concurrently disabled channel.
- Final checks passed for diff formatting, log call/event/field consistency,
  blank required Secret examples, Fernet-shaped values, non-example account data,
  SQLite/archive/browser artifacts, and tracked generated output. Temporary
  runtime data and Python bytecode caches were removed.
- No files were staged or committed. The user's existing untracked `AGENTS.md`
  remains unchanged and must be excluded from any later commit.
- Known issue: the upstream Starlette/httpx deprecation warning remains and does
  not affect the passing suite.
- Next command: `git status --short`.

### 2026-08-12 - M9 started after dependency audit

- Reopened the plan after live `pip-audit`, `pnpm audit`, and Trivy scans.
- Python application dependencies had no known vulnerability. The frontend lock
  contained one production React Router advisory plus four build-only PostCSS and
  NanoID advisories. The final Bookworm image contained 52 fixable medium-or-higher
  findings, including four critical and fourteen high findings.
- Confirmed the application uses regular browser routing rather than the affected
  experimental React Router RSC APIs, and confirmed Node/PostCSS/NanoID do not enter
  the final runtime image. Patches are still required to keep the supply chain clean.
- Selected minimal remediations: React Router 7.18.2, PostCSS 8.5.26, Node 24 LTS,
  UV Python 3.13 Trixie slim, and the Starlette-supported `httpx2` test backend.
  Live Trivy comparison reported zero fixable medium-or-higher findings for both
  the Trixie slim and Alpine UV alternatives; Trixie preserves glibc compatibility.
- Context7 lookup was attempted but its monthly quota remains exhausted. Version
  selection uses live registries, security advisories, lockfiles, and scanner data.
- No files were staged or committed. The untracked `AGENTS.md` remains untouched.
- Next command: update manifests and regenerate both lockfiles.

### 2026-08-12 20:56 CST - M9 completed

- Patched React Router to 7.18.2, PostCSS to 8.5.26, and the locked NanoID
  transitive dependency to 3.3.18. Added the Starlette-supported `httpx2` 2.10.0
  development backend; the complete backend suite now emits no deprecation
  warnings.
- Moved frontend builds and workflows to Node 24 and the runtime image from
  Bookworm to UV Python 3.13 Trixie slim. CI and Release now run pinned
  `pip-audit` and pnpm audits, then scan the actual final candidate image with
  Trivy before publication.
- Corrected the Trivy Action reference to `aquasecurity/trivy-action@v0.36.0`.
  Release builds one local candidate, scans it, and explicitly pushes only the
  version, `latest`, and source-tag aliases to `ghcr.io/haoyang7/quotahub`.
- Runtime smoke testing found that plain `uv run` after `uv sync --no-dev` could
  synchronize the default development group again at application startup. Docker,
  Unix, and Windows launchers now execute the already-synchronized virtual
  environment's Uvicorn directly, preventing startup downloads and development
  dependencies from entering a production installation.
- Final backend verification passed: 83 tests with no warnings. Strict
  TypeScript/Vite production build passed. `pip-audit 2.9.0`, full pnpm audit, and
  production-only pnpm audit reported no known dependency vulnerabilities.
- Final Docker build passed with image
  `sha256:ae037ed01f24d4e1e6ed862deb1368022f085215be353d82c8e65fbef1c78c60`.
  Trivy 0.73.0 reported zero fixable medium, high, or critical findings for Debian,
  Python packages, and the UV binaries. A separate informational scan found 83
  Debian findings without available fixed versions: 60 medium, 19 high, and four
  critical. No application-package or UV-binary findings were present.
- A fresh container returned `{"status":"ok"}` from `/api/health`, emitted no
  access-log line or raw client IP, performed no dependency download or install,
  and contained no Node, npm, pnpm, `node_modules`, `pytest`, or `httpx2` runtime
  artifacts. The temporary container was stopped and removed.
- Workflow YAML parsing, shell syntax, diff formatting, UV/source archive contents,
  blank Secret examples, Trivy secret scanning, credential-pattern scanning, and
  SQLite/archive/browser/bytecode/generated-artifact scans passed. Temporary
  release archives and Python bytecode caches were removed.
- Context7 documentation lookup was retried as required but its monthly quota is
  still exhausted; current CLI output, lockfiles, registry/audit results, scanner
  data, and executable runtime verification were used as the fallback evidence.
- No files were staged or committed. The user's existing untracked `AGENTS.md`
  remains unmodified and must be excluded from any later commit.
- Next command: `git status --short`.

### 2026-08-12 - Production-style functional acceptance

- Ran an isolated production-image acceptance environment against a sanitized
  local CLIProxyAPI-compatible mock. No real OpenCode, Ollama, CPA account, or
  credential was used.
- Administrator API checks passed for anonymous rejection, login cookies, CSRF,
  settings updates, OpenCode/Ollama CRUD and masking, two CPA channel creation,
  URL normalization, empty-key preservation, enable/disable behavior, and public
  DTO isolation.
- The two CPA channels each discovered four accounts. Free, Plus, Pro 5x, and
  Pro 20x mapping, masked identifiers, five-hour and weekly windows, reset times,
  serial pacing, and disabled-channel public hiding all rendered correctly.
- Browser acceptance passed for anonymous overview/quota pages, administrator
  redirects and login, three-provider enable switches, CPA cached windows,
  explicit settings dirty/save/persistence behavior, two usage records and the
  account filter, OpenCode cached quota details, logout, and protected-route
  redirection.
- Public refresh was confirmed snapshot-only: the mock request baseline remained
  exactly 75 requests before and after clicking refresh. At 390x844 the document
  had `scrollWidth == clientWidth == 390`, with no horizontal overflow.
- Runtime log scanning found no raw email, `auth_index`, Bearer value, Cookie or
  Set-Cookie value, raw loopback/container IP, traceback, or unexpected ERROR.
  Scheduler cycles and logout were observable. Warnings were limited to expected
  OpenCode synchronization failures caused by the intentionally fake credential.
- Final verification repeated successfully: backend `83 passed in 1.71s`; strict
  TypeScript/Vite production build passed. The isolated browser, containers,
  Docker network, temporary scripts/data, and `.playwright-cli` output were
  removed. No business code was changed during this acceptance pass.
- Limit: real upstream OpenCode and Ollama login/quota compatibility remains
  unverified because acceptance deliberately did not use real credentials.
- Next command: `git status --short`.

### 2026-08-13 - M10 started after passive-snapshot review

- Reopened the completed plan after comparing CPA-Manager-Plus monitoring storage
  with QuotaHub's active-only CPA collector. The current collector discovers every
  account and calls ChatGPT `wham/usage` on every channel interval; this is more
  frequent and riskier than necessary when Manager Server already has response-
  header quota observations.
- Locked the hybrid contract: one account-discovery request and one header-snapshot
  request per due channel, latest high-confidence file-name plus auth-index match,
  no global `items[0]` shortcut, and an unconfigurable twelve-hour per-account
  active fallback that throttles both successes and failures.
- Header snapshot 404/405 is a supported capability downgrade. Other passive
  failures preserve discovery and do not cause rapid active retries. Relative reset
  values are anchored to the upstream observation timestamp.
- Added the remaining review findings to M10: administrator usage actions must
  share the usage lease, account details must not fetch upstream on mount, legacy
  disabled flags must survive import, public CPA payloads must omit channel URLs,
  reset countdowns must advance from `reset_at`, and release tags must match all
  three application version declarations.
- GitNexus impact analysis found LOW risk for the primary symbols. CPA collection
  affects `collect_due_quotas`, `quota_sync_loop`, and lifespan; usage backfill has
  one direct administrator route consumer. No HIGH or CRITICAL impact was found.
- No business source was changed before this checkpoint. Existing uncommitted work
  and the user's untracked `AGENTS.md` remain untouched.
- Next command: add focused migration and passive CPA parser/collector tests, then
  implement the database and collection changes.

### 2026-08-14 - M10 completed

- Implemented passive-first CPA quota collection. Each due channel performs one
  account discovery and one 30-day header-snapshot request, selects only the newest
  strict auth-file-name plus `auth_index` match, and never assigns a channel's
  first item to an unrelated account.
- Added parsing for header quota windows, `window_minutes`, millisecond reset
  timestamps, observation-anchored relative resets, passive capability downgrade,
  source/observation persistence, and a fixed per-account twelve-hour active
  fallback throttle covering success, failure, and interrupted requests.
- Completed the remaining review remediations: administrator usage sync/backfill
  share the SQLite lease, account-detail mount reads local usage only, legacy
  disabled states survive import, public CPA responses omit channel URLs, quota
  countdowns derive from `reset_at`, and release tags are checked against all
  application version declarations.
- Updated README to describe the passive header-snapshot endpoint, strict account
  matching, and twelve-hour active fallback. No credentials, upstream captures,
  raw account identities, file names, or `auth_index` values were added.
- Focused regression passed: 43 tests. Final backend verification passed: 94 tests
  with no warnings. Strict TypeScript/Vite production build passed.
- Docker build passed with image
  `sha256:17943ef9a718138acc5100829af96fe00a06fa17ba6005491e2c920b140519ec`.
  Version/tag validation passed for `v0.3.0` and rejected a mismatched tag.
- Playwright verified that the public CPA URL is hidden, reset countdowns advance
  from `reset_at`, and opening the administrator usage tab issues only the local
  usage GET; it does not POST `usage/sync` until the explicit action is selected.
  The two console errors observed before login were the expected anonymous 401
  session probes.
- Generated both 0.3.0 release archives in a temporary directory and verified the
  README, blank-secret example, VERSION, and compiled SPA contents. Workflow YAML,
  shell syntax, diff formatting, repository artifact, and secret scans passed.
- Refreshed GitNexus and ran compare review against `master`: 334 changed symbols
  across 42 tracked files affect 113 flows and produce a cumulative CRITICAL risk
  classification because the full uncommitted delivery spans authentication,
  encrypted migrations, database integrity, schedulers, APIs, and public/admin UI.
  The complete test, browser, package, Docker, audit, and security evidence above
  is therefore required before any release.
- Closed the browser and Uvicorn processes, removed the local M10 image, and moved
  the temporary smoke database, seed script, packages, and browser artifacts to
  `~/.Trash/quotahub-m10-cleanup-20260814` so they remain recoverable.
- No files were staged or committed. The user's existing untracked `AGENTS.md`,
  `.claude/`, and `CLAUDE.md` remain untouched and must be excluded from any later
  commit unless the user explicitly requests otherwise.
- Next command: `git status --short && git diff --check`.

### 2026-08-14 - M11 started after second design and code review

- Reopened delivery after review found three release blockers: CPA identity was
  derived only from path-stable `auth_index`, collection validation and database
  writes were not atomic across configuration updates, and Fernet migration left
  recoverable plaintext bytes in SQLite pages.
- Additional fixes in scope are controlled API/database errors, OpenCode workspace
  invalidation after Cookie changes, an explicit passive-snapshot freshness window
  with future-clock tolerance, deterministic plan priority, and active-response
  plan propagation.
- GitNexus reports HIGH impact for `sync_usage_incremental`, `_ensure_workspace`,
  and `ensure_bootstrapped`; affected paths include automatic usage collection,
  administrator sync/backfill, lifespan startup, login, and configuration status.
  CPA collection is MEDIUM and the remaining primary symbols are LOW.
- Baseline regression passed: 51 tests covering CPA parsing/collection, secrets,
  quota API, usage synchronization, and logging. No source files were changed
  before this checkpoint; the user's untracked `AGENTS.md`, `.claude/`, and
  `CLAUDE.md` remain excluded.
- Next command: implement idempotent `collection_revision` columns and guarded
  SQLite writes, then run the focused database and synchronization tests.

### 2026-08-14 - M11 completed

- Added idempotent `collection_revision` migrations for OpenCode, Ollama, and CPA.
  Collection-related credential, workspace, URL, key, and enabled-state changes
  increment the revision; display-only changes do not force an upstream request.
- Protected usage pages, workspace caching, OpenCode/Ollama snapshots, CPA
  discovery, account snapshots, and channel completion with `BEGIN IMMEDIATE`
  conditional writes. Results are discarded when the source was deleted,
  disabled, revised, or its scheduler lease was lost while a request was running.
- Upgraded CPA account identity to a domain-separated HMAC over `auth_index` plus
  the stable account subject. Legacy SHA/HMAC identities migrate without losing
  the prior `public_id`, while replacing the account behind one `auth_index`
  creates a new public identity and cannot inherit quota or fallback throttling.
- Corrected deterministic plan precedence and propagated plans and windows from
  active usage responses. Passive monitoring remains the preferred source, with
  a six-hour freshness window, five-minute future-clock tolerance, and the fixed
  twelve-hour active fallback when no acceptable passive observation exists.
- Hardened plaintext credential migration with SQLite secure deletion, WAL
  truncation, and vacuuming after verified encrypted rewrites. Regression tests
  confirmed that database, WAL, and journal files do not retain plaintext.
- Replaced free-form CPA, database, and API exception persistence/serialization
  with fixed safe error codes. Cookie/workspace changes now invalidate cached
  OpenCode workspace resolution before the next scheduled collection.
- Focused verification passed in four groups: 26 database/secrets/usage tests,
  33 CPA parser/collector tests, eight administrator API tests, and 15 snapshot/
  logging tests. Final backend verification passed with 112 tests and no warnings;
  the strict TypeScript/Vite production build also passed.
- Docker build and container health smoke passed with image
  `sha256:cd73508a629512fd2354b83ab49668b85ade13586a4661f18ab1a4908809b9ee`.
  The health request emitted no Uvicorn access log or raw client IP. The temporary
  `quotahub:m11-review` image was removed after verification.
- Generated and extracted both 0.3.0 UV/source archives. README, blank required
  Secret values, VERSION, and compiled SPA contents were verified; forbidden path,
  credential-pattern, account-sample, SQLite, archive, browser-artifact, bytecode,
  and generated-file scans passed. Temporary packages and Python caches were moved
  recoverably to `/Users/yanghao/.Trash/quotahub-m11-final-20260814-0937`.
- GitNexus was refreshed to 1,700 symbols, 5,857 relationships, and 146 flows.
  The final staged review reported 658 changed symbols and 135 affected flows
  across 63 candidate files with cumulative `CRITICAL` risk because the full 0.3.0 delivery
  crosses authentication, encrypted migration, persistence, schedulers, API
  contracts, and both public and administrator UIs. High-risk collection paths are
  covered by revision/lease boundary tests and the complete regression suite.
- No files were staged or committed. The user's existing untracked `AGENTS.md`,
  `CLAUDE.md`, and `.claude/` remain untouched and must be excluded from a future
  commit unless the user explicitly requests otherwise.
- Next command: `git status --short && git diff --check`.

### 2026-08-14 - 0.3.0 release candidate prepared

- Created local candidate branch `codex/release-0.3.0` from
  `fd0dd87e15df9b56d28c6d188ce7b302509fc80c`.
- Consolidated the completed M1-M11 implementation, tests, release workflows,
  documentation, and packaging changes into the candidate commit. The commit
  author is `yanghao <haoyoung7@gmail.com>`.
- Kept the user's local `AGENTS.md`, `CLAUDE.md`, and `.claude/` files outside the
  candidate commit. No database, credential, release archive, browser artifact,
  Python cache, or generated local state is included.
- Final staged GitNexus review covered all 63 candidate files and reported 658
  changed symbols, 135 affected flows, and cumulative `CRITICAL` scope risk. This
  is the expected full-release classification and is backed by the M11 focused,
  complete, browser, package, container, migration, and security verification.
- The exact candidate SHA is intentionally obtained from `git rev-parse HEAD`
  after checkout; embedding a commit's own SHA in its tracked contents is not
  self-consistent.
- Next command: `git push -u origin codex/release-0.3.0`, then create a Pull
  Request to `master` and wait for the `test`, `frontend`, and `container` jobs.

### 2026-08-14 - M12 started after candidate CI failure

- Candidate commit `cfe6d9f612d1c504cce4e73e45cb5cdd6203a836` was pushed to
  `codex/release-0.3.0`; the fork-local Pull Request runs the repository CI.
- Backend and frontend jobs passed. Container Job `94661915622` failed only at
  the Trivy 0.73.0 fixable MEDIUM/HIGH/CRITICAL gate.
- The raw report shows `msgpack 1.1.2` and `setuptools 70.3.0`, with fixed
  versions `1.2.1` and `83.0.0`. They are declared by the global pip 26.2.1
  vendored CycloneDX file, not by QuotaHub's application lockfile or virtual
  environment. Installing a newer standalone setuptools package would not repair
  the vendored components.
- Final runtime inspection confirmed QuotaHub starts from its pre-synchronized
  virtual environment and does not require global pip or `ensurepip`. The selected
  remediation is to remove those unused installer artifacts from the final image,
  keep the vulnerability threshold unchanged, then rebuild, scan, and smoke-test.
- GitNexus reports LOW risk for the Dockerfile and no application execution-flow
  dependency. Workflow files are not indexed as application symbols; their scope
  is limited to CI and tag release behavior. Context7 was attempted as required
  but its monthly quota remains exhausted.
- Preserved the existing untracked `AGENTS.md`, `CLAUDE.md`, and `.claude/`.
- Next command: patch the Docker runtime layer, then build and inspect the final
  filesystem before rerunning Trivy 0.73.0.

### 2026-08-14 - M12 local verification checkpoint

- Removed global pip executables, pip package metadata, and `ensurepip` from the
  final runtime filesystem after the application virtual environment is fully
  synchronized. The application environment and standalone UV binaries remain.
- Upgraded repository Actions to their current Node 24 major lines: Checkout 7,
  Setup Node 7, Setup UV 10, pnpm Setup 6, Docker Buildx 4, Docker Build/Push 7,
  Docker Login 4, and GitHub Release 3. Added explicit `contents: read` permission
  to ordinary CI; tag release retains explicit `contents: write` and
  `packages: write` with the automatic `GITHUB_TOKEN`.
- A pull-through, no-cache Docker build passed with image
  `sha256:50a130eb0d96050ec20364c85491eec53d1198a779a984249d0a09621c71d8f5`.
  Final-filesystem checks confirmed that global pip and `ensurepip` are absent,
  while FastAPI, Uvicorn, and Cryptography import from the application virtual
  environment.
- Trivy 0.73.0 passed the unchanged fixable MEDIUM/HIGH/CRITICAL gate with zero
  findings. A fresh container returned a healthy API response and started the two
  schedulers without exposing a raw client address.
- Full backend verification passed with 112 tests; pip-audit found no known
  vulnerabilities. The frontend audit found no known vulnerabilities and the
  strict TypeScript/Vite build passed. Actionlint 1.7.12 and `git diff --check`
  passed.
- GitNexus change review reports four files, two documentation sections, no
  affected application flows, and LOW risk. A focused credential-pattern scan
  found only the expected automatic `${{ secrets.GITHUB_TOKEN }}` workflow use.
- The untracked `AGENTS.md`, `CLAUDE.md`, and `.claude/` remain untouched and must
  stay outside the commit.
- Next command: stage only the four M12 files, commit, push the candidate branch,
  and wait for the fork-local Pull Request CI.

### 2026-08-14 - M12 remote action-reference correction

- Candidate CI run `31767826058` confirmed Checkout 7, pnpm Setup 6, and Setup
  Node 7 on the frontend job; its audit and strict build passed.
- The backend job failed before checkout because `astral-sh/setup-uv` publishes
  release `v10.0.0` without a movable `v10` tag. The container job was skipped by
  its dependency and did not evaluate the Docker remediation.
- Queried the official Git references for every upgraded Action. All selected
  major tags exist except Setup UV, which is now pinned to its published
  `v10.0.0` tag in both CI and Release workflows.
- This correction changes only Action resolution; no application, dependency,
  image, permission, or secret behavior changed.
- Next command: validate and push the exact Setup UV tag correction, then wait for
  all three CI jobs.

### 2026-08-14 - M12 completed

- Fork-local Pull Request CI run `31768110172` passed at candidate head
  `93441acbb99aef856774622ac8dae09bbeff98d1`.
- Backend completed version validation, frozen dependency installation,
  pip-audit, and all 112 tests using Checkout 7 and Setup UV `v10.0.0`.
- Frontend completed frozen installation, dependency audit, and strict
  TypeScript/Vite build using Checkout 7, pnpm Setup 6, and Setup Node 7.
- Container completed Buildx 4, Build/Push 7, and the unchanged Trivy 0.73.0
  fixable MEDIUM/HIGH/CRITICAL gate with zero findings. No CVE suppression or
  reduced severity threshold was introduced.
- CI uses explicit read-only repository contents permission. Release continues to
  use only GitHub's automatic `GITHUB_TOKEN` with explicit contents/package write
  permissions; no personal access token or QuotaHub runtime secret is required.
- M12 is complete. The remaining decision is repository maintenance: merge the
  fork-local Pull Request when desired, then create the `v0.3.0` tag only after
  confirming the release timing.
- The untracked `AGENTS.md`, `CLAUDE.md`, and `.claude/` remain outside every
  commit.
- Next command: `gh pr checks 1 --repo haoyang7/QuotaHub`.

### 2026-08-14 - M12 final CI and handoff normalization

- The M12 completion-document commit `d36c2e7f44bdb2e66788d989bfd1435cd6cfb681`
  passed fork Pull Request CI run `31768274921`; backend, frontend, container
  build, and Trivy were all green at the branch head.
- The status-block `head` field is intentionally `null`: a tracked document
  cannot embed the SHA of the commit that contains that same SHA without becoming
  self-inconsistent. On resume, obtain the authoritative value with
  `git rev-parse HEAD` and compare it with the branch and latest CI instead.
- Temporary M12 Docker images, smoke containers, and the dedicated Trivy cache
  volume were removed. Repository-local user instruction files remain untracked.
- Next command: `git status --short --branch && gh pr checks 1 --repo haoyang7/QuotaHub`.

### 2026-08-14 - Candidate identity and branch rebuilt

- Closed fork-local Pull Request #1 and removed the obsolete remote
  `codex/release-0.3.0` branch. The corresponding local branch was then deleted
  after preserving its candidate commit by SHA.
- Recreated the complete 0.3.0 candidate as one squash commit on
  `codex/0.3.0`, based on `origin/master`; historical handoff entries retain the
  old branch names because they describe completed events.
- Set the repository-local Git identity to
  `haoyang7 <847923197@qq.com>`. The authenticated GitHub account is `haoyang7`;
  the final pushed commit must also be checked through GitHub's commit API before
  the replacement fork-local Pull Request is accepted.
- The replacement Pull Request must target only `haoyang7/QuotaHub:master`, never
  the upstream `lvmiao233/QuotaHub` repository.
- The untracked `AGENTS.md`, `CLAUDE.md`, and `.claude/` remain untouched and
  outside the candidate commit.
- Next command after the replacement Pull Request exists:
  `gh pr checks --repo haoyang7/QuotaHub --watch`.

### 2026-08-14 - Release branch rebuilt without implementation plan

- Removed the obsolete local and remote `codex/0.3.0` branch and created
  `release/0.3.0` from `origin/master`.
- Rebuilt the 0.3.0 application candidate as a single squash change while
  explicitly excluding `docs/plans/cpa-admin-quota.md` from the index. This file
  remains available only as local, untracked handoff material.
- Repository-local Git identity remains `haoyang7 <847923197@qq.com>`. The new
  commit must have both local author/committer identities and GitHub author/
  committer mappings equal to `haoyang7`; `99nav` and `52chatai` are prohibited.
- The local `AGENTS.md`, `CLAUDE.md`, and `.claude/` also remain untracked and
  outside the release commit.
- Next command: run staged GitNexus and secret checks, commit once, push
  `release/0.3.0`, then verify the GitHub commit mapping.

### 2026-08-14 - Release branch pushed and identity verified

- Created and pushed commit
  `8d26f06d93c4ac997c257c5d9a5295fada6fda12` on `release/0.3.0`.
- Local Git metadata and GitHub's commit API both report author and committer as
  `haoyang7 <847923197@qq.com>`; neither `99nav` nor `52chatai` appears in the
  release-only commit range.
- Verified through the remote Git tree API that
  `docs/plans/cpa-admin-quota.md` is absent. It remains local and untracked,
  together with `AGENTS.md`, `CLAUDE.md`, and `.claude/`.
- Backend verification passed with 112 tests. The strict TypeScript/Vite build
  passed. The rebuilt product tree is identical to the previously verified
  candidate apart from excluding this handoff document.
- CI does not run for a direct push to `release/0.3.0`; the workflow listens to
  pushes on `master`/`main` and all Pull Requests. A fork-local Pull Request is
  therefore required to obtain new `test`, `frontend`, and `container` results.
- Next command if a fork-local Pull Request is approved:
  `gh pr create --repo haoyang7/QuotaHub --base master --head release/0.3.0`.

### 2026-08-14 - v0.3.0 released

- Created annotated tag `v0.3.0` with tagger
  `haoyang7 <847923197@qq.com>` on merged `master` commit
  `3800c06d3672c1cc09b7de4cda361e6f6ef94510` and pushed it to the fork.
- Release workflow run `31789141946` completed successfully in 1m52s: version
  validation, frontend build/audit, backend tests/audit, package generation,
  Docker build, Trivy gate, GHCR push, and GitHub Release creation all passed.
- Published `ghcr.io/haoyang7/quotahub:0.3.0`, `:v0.3.0`, and `:latest`; all
  three resolve to digest
  `sha256:4cd50696c85f4c92ca4ddd1d7ec60fd725dac5333bceaa3a2c9a70e89d217e21`.
- GitHub Release `v0.3.0` is public and contains the UV archive, source archive,
  and `SHA256SUMS`.
- This handoff document and the local instruction files remain untracked and were
  not included in the tag or release artifacts.
- Next command for a deployment host:
  `docker pull ghcr.io/haoyang7/quotahub:0.3.0`.

### 2026-08-15 - M13 started for QuotaHub 0.3.1

- Reopened the local handoff plan for the approved 0.3.1 implementation.
- Locked native CPA quota collection to the destructive HTTP
  `/v0/management/usage-queue` path only. Queue consumption requires an explicit
  administrator confirmation that QuotaHub is the only HTTP consumer and that no
  RESP usage subscriber exists; disabling or changing credentials invalidates the
  confirmation.
- Removed active ChatGPT quota fallback from the target design. Existing historical
  `active_api` snapshots remain readable but no new `/api-call` request may be
  issued by QuotaHub.
- Added a separate CPAMP channel target that reads CPAMP's persisted
  `/v0/management/quota-snapshots/query` endpoint and uses monitoring header
  snapshots only as a non-destructive compatibility fallback.
- GitNexus pre-change review reports MEDIUM risk for `collect_cpa_channel` (19
  impacted symbols and the quota scheduler/lifespan flows) and LOW risk for the
  administrator route, lifespan, database bootstrap, and CPA form. No HIGH or
  CRITICAL symbol risk was found before implementation.
- Preserved the local untracked `.claude/`, `AGENTS.md`, `CLAUDE.md`, and `docs/`;
  none may enter the release commit.
- Next command: run the complete backend test suite and strict frontend build as
  the 0.3.1 baseline.

### 2026-08-15 - M13 baseline completed

- Baseline backend verification passed: 112 tests with no warnings.
- Baseline strict TypeScript/Vite production build passed.
- No tracked source changes existed before implementation; the only worktree
  entries remain the intentionally local untracked instruction and handoff files.
- Next command: add focused database migration and native CPA queue protocol tests,
  then implement the migration and queue parser/client.

### 2026-08-16 - M13 resumed implementation checkpoint

- Resumed from `master` at `3800c06d3672c1cc09b7de4cda361e6f6ef94510` with the
  existing uncommitted 0.3.1 backend and frontend implementation intact.
- Re-read `AGENTS.md` and this complete handoff document, confirmed the GitNexus
  index matches the current HEAD, and preserved the local untracked `.claude/`,
  `AGENTS.md`, `CLAUDE.md`, and `docs/` paths outside release scope.
- The current four-tab administrator frontend passes strict TypeScript and Vite
  production build. Review found remaining focused work in CPAMP overview/stale
  semantics, queue popped-batch isolation, channel pending locks, and mobile tabs.
- Next command: run GitNexus upstream impact for the affected symbols, add focused
  regression tests, and patch the reviewed paths.

### 2026-08-16 01:56 CST - M16 completed

- Completed the 0.3.1 implementation and final review. Native CPA now discovers
  accounts only through `auth-files` and obtains quota exclusively from the
  explicitly confirmed destructive HTTP `usage-queue`; tracked application source
  contains no `/api-call` or ChatGPT `wham/usage` request.
- Corrected compatibility with CPA queue responses whose array elements are JSON-
  encoded strings. The parser performs one safe JSON decode, still accepts only an
  object, and never logs the raw item or parse error text.
- Corrected CPAMP discovery fallback semantics. A successful empty `auth-files`
  result now represents an empty current account set and cannot resurrect removed
  accounts from 30-day historical headers. When discovery fails and Header
  Snapshot has no usable identities, the last successful quota remains visible and
  becomes stale instead of being hidden.
- Focused native CPA/CPAMP regression passed: 25 tests. Final backend verification
  passed: 131 tests with no warnings. Strict TypeScript/Vite production build,
  pip-audit, pnpm audit, version/tag validation, release archive validation, and
  release-note rendering all passed.
- Docker build passed with image
  `sha256:70080a0ce46721856b3a6dfe13625885f094be5729a7ddec0d1219892ffc7624`.
  Trivy 0.73.0 found zero fixable MEDIUM/HIGH/CRITICAL vulnerabilities. A fresh
  container returned a healthy API response, reported version 0.3.1, used local
  `+08:00` application timestamps, and emitted no health-request access log or raw
  client IP.
- GitNexus compare reports 180 changed symbols and 78 affected flows across 28
  indexed files with cumulative CRITICAL scope because the release spans migrations,
  schedulers, APIs, and public/admin UI. The complete regression, package, runtime,
  audit, and scanner evidence above is therefore required for release.
- Candidate scanning covered 32 product files and found no credential-shaped
  values, databases, private keys, or forbidden local paths. `AGENTS.md`,
  `CLAUDE.md`, `.claude/`, and `docs/` remain local and untracked. Generated browser,
  package-check, smoke-container, volume, Trivy-cache, and candidate-image artifacts
  were removed or moved recoverably to
  `/Users/yanghao/.Trash/quotahub-031-final-20260816-015548`.
- M16 is complete. No files are staged or committed.
- Next command: `git status --short && git diff --check`; after explicit approval,
  create `release/0.3.1` and stage only the product candidate files.

### 2026-08-17 - M17 started

- Reopened the local handoff after the 0.3.1 release-readiness review found three
  snapshot data-integrity issues and one administrator polling issue.
- GitNexus reports LOW symbol-level risk for the backend persistence, CPAMP parser,
  collector, and route changes; the shared administrator channel DTO has MEDIUM
  impact through the account-management page. The cumulative release remains
  CRITICAL because it spans persistence, schedulers, APIs, and frontend contracts.
- Local-only `.claude/`, `AGENTS.md`, `CLAUDE.md`, and `docs/` remain excluded from
  release scope.
- Next command: patch the four reviewed paths and run the focused CPA/CPAMP/API
  regression tests.

### 2026-08-17 - M17 completed

- Prevented periodic CPA and CPAMP account discovery from overwriting a plan
  obtained from a successful quota snapshot. Discovery may still fill an unknown
  plan before the first successful quota result.
- Upgraded CPAMP discovery identities to a subject-aware, domain-separated HMAC.
  The first discovery migrates the legacy file/index fingerprint in place and
  preserves its `public_id` and quota; replacing the account behind the same file
  position now produces a new identity without inheriting the old quota.
- Header Snapshot fallback now treats observations older than six hours or more
  than five minutes in the future as stale even when no reset timestamp exists.
- CPA and CPAMP update responses now expose the ephemeral administrator-only
  `sync_scheduled` result. The UI waits for a new collection only when the backend
  actually scheduled one, so resubmitting an unchanged management key no longer
  causes a 30-second polling delay. List and detail responses do not expose this
  field.
- Focused regression passed: 42 tests. Final backend verification passed: 140
  tests with no warnings. Strict TypeScript/Vite production build and
  `git diff --check` passed.
- GitNexus compare reports 183 changed symbols and 77 affected flows across 28
  indexed files. The cumulative 0.3.1 release remains CRITICAL in scope because it
  spans migrations, schedulers, API contracts, and public/admin UI; no additional
  unexpected execution flow was found in M17.
- Local-only `.claude/`, `AGENTS.md`, `CLAUDE.md`, and `docs/` remain untracked and
  must not be included in the release commit.
- Next command: `git status --short && git diff --check`; after explicit approval,
  create the 0.3.1 candidate branch and stage only product files.

### 2026-08-17 20:26 CST - M18 completed

- Fixed CPAMP identity continuity with domain-separated locator and subject HMACs.
  A subject replacement behind the same CPAMP file/index receives a new identity
  and an observation-time barrier, so historical query results cannot populate the
  replacement account. Discovery-failure Header Snapshot fallback now maps back to
  the current HMAC identity and preserves its stable `public_id`; a mismatched
  `account_snapshot` HMAC is rejected.
- Changed CPA and CPAMP snapshot ordering to distinguish strictly older and equal
  observations. Strictly older data no longer advances `last_success_at` or clears
  `stale`; an equal observation may still clear discovery staleness.
- Native CPA queue collection now forces one local `/auth-files` refresh at the
  start of every execution cycle. An empty account mapping records
  `degraded/account_mapping_empty` and returns before the destructive
  `/usage-queue` pop; all batches in that cycle reuse the freshly loaded mapping.
- Added idempotent CPAMP snapshot migrations for `locator_hash`, `subject_hash`,
  and `accept_observed_after`, including an actual legacy-table upgrade test that
  preserves the existing `public_id` and data.
- Focused regression passed: 53 tests. Final backend verification passed: 148 tests
  with no warnings. Strict TypeScript/Vite production build and `git diff --check`
  passed. Credential scanning found only documented placeholder values; no database,
  private-key, or credential artifact was found in the repository tree.
- Final GitNexus comparison is complete (not partial or truncated): 210 changed
  symbols and 146 affected flows across 28 indexed files. The cumulative candidate
  remains CRITICAL because 0.3.1 spans migrations, schedulers, APIs, and frontend.
- Local-only `.claude/`, `AGENTS.md`, `CLAUDE.md`, and `docs/` remain untracked and
  must not be included in the release commit. No files were staged or committed.
- Next command: `git status --short && git diff --check`; after explicit approval,
  create the 0.3.1 candidate branch and stage only product files.

### 2026-08-17 - M19 started after release-readiness review

- Reopened the local handoff after review found two release blockers: native CPA
  events are still joined to the current account by `auth_index` without an
  identity acceptance barrier, and CPAMP Header fallback can recreate accounts
  outside a successfully discovered current account list.
- Additional corrections in scope are atomic/retried persistence after destructive
  queue pops, queue-failure stale propagation, removal of discovery-driven false
  staleness, honoring the configured CPA discovery interval while idle, and moving
  empty 15-second queue cycle logs to DEBUG.
- GitNexus reports HIGH upstream impact for the native CPA channel queue collector,
  MEDIUM impact for CPAMP parser/collector paths, and cumulative CRITICAL release
  scope. The local-only `.claude/`, `AGENTS.md`, `CLAUDE.md`, and `docs/` paths
  remain excluded from release scope.
- Fresh review baseline passed: 59 focused CPA/CPAMP/database tests, 148 complete
  backend tests, strict TypeScript/Vite build, and `git diff --check`.
- Next command: implement the CPA identity schema/migration and popped-batch write
  path, then run the focused database and queue regressions.

### 2026-08-17 21:15 CST - M19 completed

- Native CPA discovery now stores domain-separated locator and subject HMACs. An
  account replacement behind the same `auth_index` receives a new stable
  `public_id` and an observation acceptance barrier, so an older queue event cannot
  populate the replacement snapshot.
- Destructively popped queue batches are written in one SQLite transaction with
  bounded `0.05/0.1/0.2s` lock retries. A post-pop identity refresh failure safely
  discards the whole batch, records the discarded count, and never persists the
  private exception detail.
- Empty queue cycles reuse the account mapping for the configured CPA discovery
  interval and emit completion events only at DEBUG. Authentication, disabled
  statistics, unsupported queue, and degraded states immediately mark existing
  successful quota snapshots stale without deleting their last windows.
- A genuinely processed queue event now clears the channel-level stale flag again;
  an empty poll deliberately leaves it stale until fresh quota evidence arrives.
- CPA discovery no longer marks a valid quota stale merely because account
  discovery ran. CPAMP Header fallback accepts ephemeral accounts only when
  `/auth-files` itself failed; a successful current account list is authoritative
  and historical accounts outside it remain hidden.
- Added real legacy CPA identity-column migration coverage, transient SQLite lock
  recovery, queue fault staleness, quiet idle polling, and CPAMP historical-account
  filtering regressions. Focused verification passed with 92 tests; the complete
  backend passed with 154 tests and no warnings. Strict TypeScript/Vite build,
  version consistency, and `git diff --check` passed.
- Backend and frontend dependency audits report no known vulnerabilities. Docker
  image `quotahub:0.3.1-m19` built successfully; Trivy 0.73.0 reports zero fixable
  MEDIUM/HIGH/CRITICAL findings. UV/source package contents passed forbidden-path
  checks, and Gitleaks 8.28.0 found no leaks in either release package.
- Final GitNexus comparison reports 230 changed symbols and 151 affected flows
  across 28 indexed files. The cumulative release scope remains CRITICAL because
  0.3.1 spans migrations, background schedulers, public/admin APIs, and frontend;
  no new unresolved finding was identified by M19 verification.
- Local-only `.claude/`, `AGENTS.md`, `CLAUDE.md`, and `docs/` remain untracked and
  must not be staged or committed. No files were staged or committed.
- Next command: `git status --short && git diff --check`; after explicit approval,
  create the 0.3.1 candidate branch and stage only product files.

### 2026-08-17 22:18 CST - M20 confirmation dialog completed

- Replaced all five browser-native account-management confirmations with one
  application `alertdialog`: OpenCode, Ollama, CPA, and CPAMP deletion plus CPA
  exclusive HTTP usage queue confirmation. No `window.alert` or `window.confirm`
  remains under `frontend/src`.
- The CPA confirmation states that QuotaHub cannot detect competing consumers,
  lists the HTTP/RESP/old-instance exclusivity checks, and explains destructive
  queue pop semantics. Delete actions use a distinct danger treatment.
- The dialog defaults focus to Cancel, traps Tab/Shift+Tab, supports Escape and
  backdrop cancellation while idle, restores prior focus, locks dismissal during
  requests, retains API failures in the open dialog, and constrains/scrolls content
  on short mobile viewports.
- Playwright verified the administrator flow at 390x844 and 390x568: no horizontal
  overflow, Cancel default focus, focus containment, Escape cancellation, danger
  presentation, successful close, and the exact CPA request body
  `{"enabled":true,"confirm_exclusive":true}`. The temporary test channel and
  test runtime data were removed.
- Strict TypeScript/Vite build passed (1,763 modules), and `git diff --check`
  passed. GitNexus reports LOW impact for `ConfirmationDialog` (one direct caller,
  `AccountsPage`) and LOW upstream impact for `AccountsPage`. The cumulative 0.3.1
  worktree remains CRITICAL in scope because it spans 28 indexed product files.
- Release remains blocked by the post-pop lease-loss path in
  `backend/app/cpa_queue.py`: a destructive queue batch can be discarded before a
  warm-cache forced account-mapping refresh. The next command is
  `cd backend && uv run python -m pytest tests/test_cpa_queue.py -q` after adding a
  regression that loses the lease immediately after `_pop_usage_queue` returns.

### 2026-08-17 23:18 CST - M20 post-pop lease-loss blocker fixed

- Confirmed the missed branch is the warm account-cache path: the first mapping
  load leaves `mapping_refreshed=false`, a non-empty destructive pop loses the
  lease, and the old post-pop guard interrupted before the required forced identity
  refresh and transactional snapshot write.
- Removed only that post-pop lease rejection. Once events have been popped, the
  collector now completes the forced current-account refresh, collection-revision
  guard, and atomic batch persistence. The existing guard at the start of the next
  batch still stops another `/usage-queue` request after lease loss.
- Converted the previous cold-cache regression into a true warm-cache scenario.
  It fails on the old code, asserts two account loads (including `force=true`),
  verifies exactly one destructive queue request, confirms a successful persisted
  usage-queue snapshot, and scans SQLite for the private fixture sentinels.
- Focused reproduction failed before the patch and passed afterward. The complete
  CPA queue file passed with 24 tests; the full backend suite passed with 154 tests
  and no warnings after a frozen dependency sync. `git diff --check` passed.
- GitNexus reports MEDIUM upstream impact for the collector (one production direct
  caller, the queue loop/lifespan chain, and focused tests). The cumulative 0.3.1
  comparison remains CRITICAL because it spans 232 symbols and 82 flows across 28
  indexed product files; no additional API, schema, or frontend flow was added by
  this fix.
- The local-only `.claude/`, `AGENTS.md`, `CLAUDE.md`, and `docs/` paths remain
  excluded from release scope. No files were staged or committed.
- Next command: `git status --short && git diff --check`; then perform one final
  0.3.1 release review before creating the candidate branch.

### 2026-08-17 23:35 CST - M21 final release review passed

- Re-ran the complete 0.3.1 release gate from the current worktree. The backend
  passed 154 tests without warnings; strict TypeScript/Vite production build
  passed with 1,763 modules; version consistency reports `0.3.1`.
- Backend `pip-audit` and frontend `pnpm audit` report no known vulnerabilities.
  Docker image `quotahub:0.3.1-final-review` built and passed runtime health and
  version smoke checks. Trivy 0.73.0 reports zero fixable
  MEDIUM/HIGH/CRITICAL findings for the image.
- UV and source packages contain the CPA queue, CPAMP integration, compiled SPA,
  README, and blank-secret example configuration while excluding local agent
  instructions, plans, runtime data, and generated developer state. Gitleaks
  8.28.0 found no leaks in either package.
- Corrected one release-note wording inconsistency: Windows source instructions
  now describe two required Secrets plus optional Cookie and log-timezone settings.
  Rendered notes reference only `ghcr.io/haoyang7/quotahub:0.3.1`.
- `git diff --check` passed. Local-only `.claude/`, `AGENTS.md`, `CLAUDE.md`, and
  `docs/` remain untracked and must not enter the release commit.
- Next command: `git switch -c release/0.3.1`, stage only the 28 modified and five
  newly added product files, then run GitNexus `detect_changes` before committing.

### 2026-08-17 23:36 CST - M21 release candidate committed

- Created `release/0.3.1` from `master` at
  `3800c06d3672c1cc09b7de4cda361e6f6ef94510` and committed 33 product files as
  `9f37faac6613b8c4753879c79dc187fae40b0ccf` with subject
  `feat: release QuotaHub 0.3.1`.
- Author and committer are both `haoyang7 <847923197@qq.com>`; neither commit
  metadata nor the committed tree contains `99nav` or `52chatai`.
- GitNexus final comparison reports 419 indexed changed symbols and 82 affected
  flows across the 33 product files. The expected cumulative risk is CRITICAL due
  to database migrations, background schedulers, API contracts, and frontend
  integration; no out-of-scope file or unexpected subsystem was added.
- Gitleaks 8.28.0 scanned the staged diff (approximately 261 KB) and found no
  leaks. The committed tree contains no local instructions/plans, runtime data,
  database, private-key, or generated frontend dependency paths.
- The working tree now contains only the deliberately untracked local `.claude/`,
  `AGENTS.md`, `CLAUDE.md`, and `docs/` paths. Nothing has been pushed.
- Next command after user approval: `git push -u origin release/0.3.1`.

### 2026-08-18 00:02 CST - M22 controlled runtime acceptance completed

- Built commit `9f37faac6613b8c4753879c79dc187fae40b0ccf` as a fresh Docker
  image and ran QuotaHub against an isolated named volume. Health, version,
  administrator login, public/admin routing, settings persistence, logout, and
  graceful container restart all passed.
- Used an isolated, protocol-faithful CPA/CPAMP stub on a private Docker network.
  It used only sanitized fixture identities and never contacted ChatGPT or any
  real upstream. No existing user database, credential, or queue was touched.
- CPA wrong-key creation produced a controlled authentication failure and zero
  queue calls. Updating only the key immediately rediscovered one masked account.
  The destructive queue remained untouched until the explicit exclusivity dialog
  was confirmed, then one event produced Pro 5x primary/secondary windows.
- Disabling the CPA channel cleared its exclusivity confirmation and stopped queue
  consumption. Re-enabling retained the last snapshot but returned to
  `awaiting_confirmation`, as required.
- CPAMP primary snapshot query and 404-to-Header-Snapshot fallback both completed
  through the real scheduler and rendered Pro 20x windows. Public refresh actions
  made zero additional upstream calls.
- Public DTOs exposed only masked account labels and stable public IDs. SQLite
  stored all three management keys as `fernet:v1:` ciphertext and contained none
  of the raw fixture email, account file, auth index, key, client IP, User-Agent,
  or queue private fields. Application logs passed the same sentinel scan.
- Playwright verified desktop behavior and 390x568 mobile layouts with no page-level
  horizontal overflow. The confirmation dialog defaulted focus to Cancel and
  clearly described HTTP/RESP exclusivity and destructive pop semantics.
- Container restart retained the administrator session, changed settings, one CPA
  snapshot, and two CPAMP snapshots. All three schedulers restarted with a new
  owner and did not repeat an upstream sync. Logout invalidated the session and
  anonymous administrator API access returned 401.
- Two non-blocking accessibility observations remain: login/password fields are
  not wrapped in semantic HTML forms (Enter is handled explicitly), and account
  edit/delete icon buttons have no accessible names or tooltips. Neither affected
  this acceptance flow, but the icon labeling should be corrected before or after
  the release according to the desired accessibility bar.
- Removed the acceptance containers, volume, network, image, and browser session.
  Browser artifacts were moved to the macOS Trash. Product files and commit
  `9f37faa` were not modified; local-only instruction and plan paths remain
  untracked.
- Next command remains `git push -u origin release/0.3.1` unless the accessibility
  polish is intentionally added as a follow-up release-candidate commit.

### 2026-08-18 10:45 CST - M23 accessibility polish completed

- Wrapped the administrator token input and actions in a semantic HTML `form`.
  Enter now uses the form submit event rather than an input-specific key handler;
  Login is explicitly a submit button and the public-page action is explicitly a
  non-submit button.
- Added object-specific accessible names and native `title` tooltips to all eight
  OpenCode, Ollama, CPA, and CPAMP edit/delete icon buttons. Decorative Pencil and
  Trash icons are hidden from the accessibility tree.
- Strict TypeScript/Vite production build passed with 1,763 modules and
  `git diff --check` passed.
- An isolated local runtime and Playwright verified Enter-to-login, one login
  `form`, the token input's form association, and matching `aria-label`/`title`
  values on all eight buttons. Only synthetic local accounts and disabled local
  channels were used; no real upstream was contacted.
- Browser artifacts were moved to
  `/Users/yanghao/.Trash/QuotaHub-playwright-accessibility-20260818`. The isolated
  server is stopped and the browser session is closed.
- Local-only `.claude/`, `AGENTS.md`, `CLAUDE.md`, and `docs/` remain excluded
  from release scope.
- GitNexus staged detection reported exactly two changed components and three
  expected frontend flows at MEDIUM risk. Committed only the two product files as
  `f74f2fd` with subject `fix: improve management accessibility`.
- Next command: `git push origin release/0.3.1`; after the candidate is merged,
  create and push the `v0.3.1` tag from the verified merge commit.

### 2026-08-18 - M23 accessibility commit withdrawn

- Per user request, removed commit `f74f2fd5cd8d65e3d3051ed60bb70b0f54eb91b7`
  from the local `release/0.3.1` branch with a non-destructive mixed reset.
- The two accessibility file changes remain unstaged in the worktree so they can
  be reapplied or folded into the unified CPA channel change; no hard reset was
  used and no user files were deleted.
- The branch HEAD is back at `9f37faac6613b8c4753879c79dc187fae40b0ccf`.

### 2026-08-18 - M24 unified CPA/CPAMP design review in progress

- Current implementation has duplicate independent entities and pages:
  `cpa_channels` + `cpa_quota_snapshots` consume native CPA queue events, while
  `cpamp_channels` + `cpamp_quota_snapshots` query CPAMP persisted snapshots.
  Both duplicate URL, encrypted management key, enabled state, interval, revision,
  account identity, and snapshot lifecycle.
- Proposed product model: one `cpa_channels` record per deployed CPA endpoint and
  one shared account/snapshot identity set. A channel chooses a quota source mode:
  `native_queue`, `cpamp_snapshot`, or `unconfigured`; `native_queue` additionally
  requires the existing explicit HTTP/RESP exclusivity confirmation. CPAMP is a
  deployment capability/source mode of that same endpoint, not a second channel.
- CPAMP mode must never consume the destructive native queue. Native queue mode
  must never call CPAMP snapshot endpoints. The selected mode is mutually
  exclusive per channel and changing URL/key, disabling, or changing mode clears
  queue confirmation and invalidates in-flight writes.
- The migration must merge old CPAMP rows into matching CPA rows by normalized URL
  and management-key fingerprint, preserve stable public IDs and newest successful
  snapshots, and require an explicit conflict review when one URL has different
  keys or multiple CPAMP rows. Automatic destructive guessing is not acceptable.
- The public/admin DTO should expose one `source_mode` and one account list per
  channel. The frontend should replace separate CPA/CPAMP tabs with one CPA tab,
  a deployment/source selector, and conditional queue confirmation/status. Legacy
  endpoints can remain read-only aliases during one migration window.
- Open decisions before implementation: whether a channel may retain both native
  and CPAMP snapshots for historical comparison (recommended: retain internally,
  expose only selected source), and whether a CPAMP endpoint can switch to native
  queue without re-entering the exclusivity confirmation (recommended: always
  require confirmation).

### 2026-08-18 - M25 unified CPA channel implementation started

- Approved one logical `cpa_channels` entity with mutually exclusive `none`,
  `native_queue`, and `cpamp_snapshot` quota sources. A channel may retain both
  encrypted endpoint configurations, but only the selected source may perform
  network requests.
- Confirmed there is no production CPAMP data requiring automatic matching or an
  administrator merge workflow. Defensive candidate-schema migration must convert
  unexpected CPAMP rows into independent unified channels without guessing.
- GitNexus reports HIGH upstream impact for
  `collect_cpa_usage_queue_channel`: 14 direct dependents across the queue loop,
  application lifespan, and ten focused tests. Post-pop persistence and the
  pre-next-request source guard are release-critical invariants.
- Preserved the unstaged accessibility changes in `AccountsPage.tsx` and
  `AdminLoginPage.tsx`; local `.claude/`, `AGENTS.md`, `CLAUDE.md`, and `docs/`
  remain excluded from the release candidate.
- Next command: add unified-channel database migration tests, then implement the
  canonical channel/account/snapshot schema transactionally.

### 2026-08-19 16:39 CST - M25 unified CPA channel ready for candidate commit

- Replaced the separate CPA and CPAMP product entities with one logical CPA
  channel and mutually exclusive `none`, `native_queue`, and `cpamp_snapshot`
  quota sources. Only the selected endpoint can issue network requests.
- Added transactional, idempotent migration for unified channels, accounts, and
  source/endpoint-generation snapshot keys. Unexpected candidate CPAMP rows are
  converted to independent unified channels without guessing a relationship.
- Preserved already-popped native queue batches under their original generation,
  including warm-cache lease-loss, source-switch, disable, and endpoint-change
  paths. Future requests stop after the current source/revision is invalidated.
- Fixed the final release blocker where replacing a CPAMP endpoint could expose a
  future-dated old-generation snapshot and reject the new endpoint's result.
  Focused endpoint-generation tests passed (3 tests); the combined CPA, CPAMP,
  and database regression passed (72 tests).
- Full backend verification passed with 162 tests and no warnings. Strict
  TypeScript/Vite production build passed with 1,763 modules. Python compileall,
  version consistency, and `git diff --check` passed.
- Docker image `quotahub:0.3.1-rc` built as
  `sha256:ccfb0d57b5d8c96a2ff5b43eb7802c49c0630ed44e1afb172831b96eacbf3bdf`.
  Trivy 0.73.0 reported zero fixable MEDIUM/HIGH/CRITICAL findings across Debian,
  Python packages, and uv binaries.
- Controlled browser acceptance passed for the single CPA tab, three source
  modes, exclusive confirmation/reconfirmation, endpoint validation, custom
  confirmation dialogs, accessible edit/delete actions, and 390x844 layout.
  No browser `alert` or `confirm` is used.
- Exact tracked-diff Gitleaks scan found no leaks. SQLite and application logs
  contained none of the sanitized raw identity, `auth_index`, key, IP,
  User-Agent, or queue-private sentinels; configured CPA/CPAMP keys were stored as
  `fernet:v1:` ciphertext.
- GitNexus comparison with `master` reports 511 changed symbols, 153 affected
  flows, and 34 indexed files at cumulative CRITICAL risk. This is expected for
  the complete database, scheduler, destructive queue, API, and frontend
  migration; focused regressions cover the release-critical paths.
- Local-only `.claude/`, `.playwright-cli/`, `AGENTS.md`, `CLAUDE.md`, and
  `docs/` remain outside release scope.
- Next command: explicitly stage the 23 product files listed in the status block,
  run `git diff --cached --name-only`, verify the staged diff with GitNexus, then
  create the 0.3.1 candidate commit as `haoyang7 <847923197@qq.com>`.
- Staged exactly those 23 product files; local instructions, plans, browser
  artifacts, runtime data, databases, and generated output were absent. Staged
  GitNexus detection reported 266 changed symbols and 101 affected flows at the
  expected cumulative CRITICAL risk, and `git diff --cached --check` passed.
- Created commit `652f87ed533bb34141e28d44f9e786d15d4d22bc` with subject
  `feat: unify CPA quota sources`. Author and committer are both
  `haoyang7 <847923197@qq.com>`.
- Next command: `git push origin release/0.3.1`; merge and verify GitHub CI before
  creating the `v0.3.1` tag.

### 2026-08-19 - M25 candidate history squashed

- Per user request, replaced local candidate commits `9f37faa` and `652f87e`
  with one commit relative to `master`; file contents and the 34-file release
  diff are unchanged.
- Before recommitting, `git diff --cached --check` passed and the staged file
  list excluded local instructions, plans, runtime data, databases, and generated
  output. GitNexus reported the same cumulative 511 changed symbols, 153 affected
  flows, 34 indexed files, and CRITICAL release scope already reviewed above.
- New commit: `76a95ade5cb7623b89e34fec598636dc30609530`, subject
  `feat: release QuotaHub 0.3.1`. Author and committer are both
  `haoyang7 <847923197@qq.com>`.
- The remote has no `release/0.3.1` branch, so no force push is required.
- Next command: `git push -u origin release/0.3.1`; merge into the repository's
  own `master`, verify CI, and only then create `v0.3.1` from the merge commit.

### 2026-08-19 - M25 GitHub release-flow verification passed

- Pushed single-commit branch `release/0.3.1` to the user's own fork
  `haoyang7/QuotaHub`; remote SHA matched local candidate `76a95ad`.
- Created PR #2 against the fork's `master`. Pull-request CI run
  `32261864846` passed all jobs: frontend dependency audit/build, backend version
  check/dependency audit/full tests, Docker Buildx image build, and Trivy
  MEDIUM/HIGH/CRITICAL gate.
- Rebase-merged PR #2 without an extra merge commit. Remote `master` is now
  `6fd6f14d73b439c33f30a3a2021eb9aa49ce777c`, with parent `3800c06`; author is
  `haoyang7 <847923197@qq.com>` and committer is the same GitHub account identity
  `Hao Yang <847923197@qq.com>`. No 99nav or 52chatai identity is present.
- The merged commit tree is `a303ef6f7f8f8175832e55909a8ee58fa4753dbc`,
  exactly matching candidate `76a95ad`; rebase changed no product content.
- Default-branch push CI run `32262168816` also passed frontend, backend,
  Docker Buildx, and Trivy jobs. This verifies both the PR gate and post-merge
  default-branch gate.
- Candidate branch remains available. No `v0.3.1` tag or GitHub Release exists,
  and the tag-triggered Release workflow has not been started.
- Next command after explicit release approval: fetch `origin/master`, create
  annotated tag `v0.3.1` at `6fd6f14d73b439c33f30a3a2021eb9aa49ce777c`,
  push only that tag, then monitor the Release workflow through package, image,
  vulnerability-scan, GHCR push, and GitHub Release publication.

### 2026-08-19 - QuotaHub 0.3.1 released

- Created annotated tag object `a39c597fffec680ed4cb1b8f32c3c32ebd2a57d2`
  as `haoyang7 <847923197@qq.com>`. It resolves to verified `master` commit
  `6fd6f14d73b439c33f30a3a2021eb9aa49ce777c` and tree `a303ef6`.
- Pushed only `refs/tags/v0.3.1`. Release workflow run `32262688406` completed
  successfully in 1m31s, including version validation, frontend audit/build,
  backend audit/tests, UV/source packaging, Docker Buildx, Trivy gate, GHCR push,
  release-note rendering, and GitHub Release publication.
- Published non-draft, non-prerelease GitHub Release:
  `https://github.com/haoyang7/QuotaHub/releases/tag/v0.3.1`.
- Release assets are present and uploaded: source ZIP, UV ZIP, and
  `SHA256SUMS`. The checksum file matches GitHub's asset digests:
  source `2499c3d04696ec84c4d41e8608bba93a65fdfdbc4ed44779d176185a8fa4f19b`,
  UV `7daff043c08a92969717d4e832becc5beda256519a3aa71607a483dc23168dca`.
- Public OCI manifest inspection confirms `ghcr.io/haoyang7/quotahub:0.3.1`,
  `:v0.3.1`, and `:latest` all resolve to
  `sha256:0b8ab4ab60597796302911eba5e8688aeb9d3eab9e9bd339d8d1879dd2b983bc`.
- The active `gh` token lacks `read:packages`, so the GitHub Packages REST list
  endpoint returned 403; public OCI manifest verification succeeded and the
  Release workflow's authenticated image-push step passed. No token change is
  required for this release.

### 2026-08-19 - M26 0.3.2 patch committed

- Fixed CPA endpoint removal after switching a channel to CPAMP snapshots. The
  native `management_key` column remains `NOT NULL` and now stores the explicit
  empty-endpoint state as `""`; CPAMP's nullable key behavior is unchanged.
- Removed the stale two-column overview wrapper so the single unified CPA card
  uses the full desktop row.
- Added an API regression covering a populated native key, source switch, and
  explicit `cpa_endpoint: null` removal. The test confirms HTTP 200, hidden URL,
  and empty-string persistence without exposing credentials.
- Bumped backend, frontend, UV lock metadata, README upgrade guidance, and
  application `User-Agent` version source to 0.3.2.
- Verification: backend `163 passed`; strict frontend build passed with 1,763
  modules; version, compile, diff, staged-path, and credential-pattern checks
  passed. Docker build passed after OrbStack was started; local Trivy was not run
  because the CLI is not installed.
- Commit: `12dfd4bb5cd3c2dc846afcbc434892bb634062eb`, authored and committed as
  `haoyang7 <847923197@qq.com>` on `release/0.3.2`.
- Next command: start OrbStack, run `docker build -t quotahub:0.3.2-rc .`, then
  push the branch and wait for CI before creating `v0.3.2`.

### 2026-08-19 - M26 branch pushed and merged

- Pushed `release/0.3.2` to the user's `haoyang7/QuotaHub` repository and opened
  fork-local Pull Request #3 against `master`; no upstream repository was touched.
- Pull Request CI run `32267212440` passed backend tests/audit, frontend
  audit/build, Docker Buildx, and the Trivy MEDIUM/HIGH/CRITICAL gate.
- Rebase-merged PR #3. Remote `master` is now
  `9e8103b3e1cca51addbf9a750777d7afda537b00`; its tree exactly matches candidate
  commit `12dfd4b`, so GitHub changed commit metadata but not product contents.
- The merged commit author maps to `haoyang7 <847923197@qq.com>` and no prohibited
  contributor identity is present.
- Default-branch push CI run `32267371579` also passed backend, frontend, Docker,
  and Trivy jobs. No `v0.3.2` tag has been created yet.
- Next command after release approval: create annotated tag `v0.3.2` at
  `9e8103b3e1cca51addbf9a750777d7afda537b00`, push only that tag, and monitor the
  Release workflow through asset and GHCR publication.

### 2026-08-19 - QuotaHub 0.3.2 released

- Created and pushed annotated tag `v0.3.2` as
  `haoyang7 <847923197@qq.com>`. Tag object `cfd0dc41d6e8907880ffd0ca7509d78aaf8df715`
  resolves to verified `master` commit
  `9e8103b3e1cca51addbf9a750777d7afda537b00`.
- Release workflow run `32268594953` completed successfully in 1m39s, including
  version checks, frontend and backend verification, release packages, Docker
  build, Trivy gate, GHCR push, release notes, and GitHub Release publication.
- Published Release: `https://github.com/haoyang7/QuotaHub/releases/tag/v0.3.2`.
  Downloaded source and UV archives both passed the published `SHA256SUMS`.
- Public OCI inspection confirms `0.3.2`, `v0.3.2`, and `latest` all resolve to
  digest `sha256:76ca4ce04047af25a8fa8a2602897c6e8172316ee3b8711ddd388e872339918c`.
- Local instruction and handoff paths remain untracked and absent from the tag.
