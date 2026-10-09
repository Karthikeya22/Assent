# Phase 0: Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A monorepo where `infra up → migrate → seed → api + worker + web` gives a logged-in coordinator an empty worklist, with CI green.

**Architecture:** uv workspace (Python 3.12) for `apps/api`, `apps/worker` and `packages/*`. pnpm + Turborepo for `apps/web` (Next.js 15). Postgres 16 + pgvector and Redis 7 run in Docker. Everything else is in-process (see the master plan's deviations table).

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2.0 async (asyncpg), Alembic, pgvector, PyJWT, passlib/bcrypt → (replaced by `hashlib.scrypt`, stdlib), arq, pytest. Next.js 15, React 19, Tailwind v4, Auth.js v5, openapi-typescript/openapi-fetch, Storybook 8, Vitest.

**Spec:** `ARCHITECTURE.md` §2–§5 and §9, `FRONTEND.md` §2, §3, §4, §6.1, §8, `BUILD_PLAN.md` §1 and §2 (Phase 0). Master plan: `C:\Users\karth\.claude\plans\okay-lets-start-the-abundant-marshmallow.md`.

## Global Constraints
- Python 3.12, `mypy --strict`, ruff. Node 22 LTS (`.nvmrc`), pnpm 10, TS strict.
- Nothing installs to C:. All caches and tools go to D: (env vars already set). Repo at `D:\Projects\assent`.
- All API routes under `/api/v1`, JWT bearer. Roles: `coordinator | clinician | policy_admin | auditor`.
- Every query is org-scoped. The audit log is append-only and hash-chained: `hash = sha256(prev_hash + canonical_json(row))`.
- Embedding dimension comes from settings (`EMBED_DIM=384`), never hard-coded.
- The design tokens are exactly the values in FRONTEND.md §2.1 (light + dark), fonts Instrument Serif / Geist Sans / Geist Mono.
- Banned UI: purple except `--adversary`, gradients, glassmorphism, emoji icons.

## Review Focus
1. **An expired or tampered JWT** → 401, never a 500 and never a silent pass. Test in Task 4.
2. **A cross-org read** (user of org A requests data from org B) → empty or 404. Test in Task 4 (`org_scope` helper).
3. **Audit chain tamper** (one row's `after_json` edited in the DB) → `verify_chain()` reports the first bad row id. Test in Task 3.
4. **The DB or Redis is down** → `/healthz` returns 503 with which dependency failed, not a hang. Test in Task 4 (via monkeypatched ping).
5. **A wrong role** (clinician calls a policy_admin route) → 403. Test in Task 4.

---

### Task 1: Monorepo skeleton + tooling
**Files:** `pyproject.toml` (workspace root + ruff/mypy/pytest config), `apps/{api,worker}/pyproject.toml`, `packages/{agents,retrieval,fhir,phi,evals}/pyproject.toml` + `src/assent_<name>/__init__.py`, `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `.nvmrc`, `.gitignore`, `.gitattributes`, `.env.example`, `.pre-commit-config.yaml`, `scripts/env.ps1`, `scripts/dev.ps1`, `README.md`, `data/{synthea,policies,fixtures}/.gitkeep`.
**Produces:** `uv sync` works. Import names `assent_api`, `assent_worker`, `assent_agents`, `assent_retrieval`, `assent_fhir`, `assent_phi`, `assent_evals`.
- [ ] Write files. `uv sync --all-packages` → success.
- [ ] `uv run ruff check . && uv run mypy` → clean.
- [ ] Commit `chore: monorepo skeleton`.

### Task 2: Lean infra
**Files:** `infra/docker-compose.yml` (pg16+pgvector:5432, redis:6379, healthchecks, named volumes), `infra/docker-compose.full.yml` (the documented full stack, for later), `infra/litellm.yaml` (tiers reasoning/fast/adversary, OpenAI placeholders).
- [ ] `docker compose -f infra/docker-compose.yml config` validates (and `up -d` → healthy once Docker is installed).
- [ ] Commit `chore(infra): lean compose + litellm tiers`.

### Task 3: DB models, migration, audit chain
**Files:** `apps/api/src/assent_api/{settings.py,db.py}`, `apps/api/src/assent_api/models/*.py` (all ARCHITECTURE §4 tables), `apps/api/alembic.ini`, `apps/api/migrations/{env.py,versions/0001_initial.py}`, `apps/api/src/assent_api/services/audit.py`, test `apps/api/tests/test_audit.py`.
**Interfaces:** `audit.append(session, *, actor_id, action, entity, entity_id, before, after) -> AuditLog`, `audit.verify_chain(session) -> UUID | None` (first bad row id, or None). Pure helper `audit.row_hash(prev_hash: str, row: dict) -> str`.
- [ ] Failing tests: the chain of 3 appends verifies. Mutating row 2's `after_json` → `verify_chain` returns row 2's id. `row_hash` is deterministic regardless of dict key order.
- [ ] Implement. Migration: `CREATE EXTENSION IF NOT EXISTS vector`, all tables, HNSW on `chart_chunks.embedding` (`vector_cosine_ops`), GIN on `tsv`, plus a trigger that makes `audit_log` insert-only (it rejects UPDATE/DELETE).
- [ ] `alembic upgrade head` against Docker PG. Tests pass. Commit `feat(api): schema + hash-chained audit log`.

### Task 4: FastAPI app, auth, RBAC, healthz, cases list
**Files:** `apps/api/src/assent_api/{main.py,security.py,deps.py}`, `routers/{health.py,auth.py,cases.py}`, `schemas/{auth.py,cases.py,common.py}`, `seed.py`, tests `tests/{test_security.py,test_health.py,test_cases.py}`.
**Interfaces:** `create_app() -> FastAPI`. `security.hash_password/verify_password` (stdlib scrypt), `security.create_access_token(user_id, org_id, role, ttl_min=15) -> str`, `security.decode_token(str) -> TokenClaims` (raises `InvalidToken`). Deps `current_user`, `require_role(*roles)`. Routes `POST /api/v1/auth/token` `{email,password}` → `{access_token, token_type, expires_in, user}`, `GET /healthz`, `GET /api/v1/cases?cursor=&limit=` → `{items: [], next_cursor: null}`.
- [ ] Failing tests for the Review Focus items 1, 2, 4 and 5, plus a token round-trip.
- [ ] Implement. `uv run python -m assent_api.seed` creates the org "Demo Health" plus 4 users (`<role>@assent.dev` / `assent-dev`).
- [ ] Tests pass. Commit `feat(api): auth, rbac, healthz, cases list`.

### Task 5: Worker
**Files:** `apps/worker/src/assent_worker/main.py` (`WorkerSettings`, `ping` job), test `apps/worker/tests/test_ping.py` (calls the job function directly).
- [ ] Test, implement, `uv run arq assent_worker.main.WorkerSettings` logs the ping. Commit.

### Task 6: Web app shell
**Files:** `apps/web/` (Next 15 + Tailwind v4), `styles/globals.css` (tokens), `app/layout.tsx` (fonts), `app/(marketing)/page.tsx` (placeholder), `app/login/page.tsx`, `app/(app)/app/{layout.tsx,page.tsx,worklist/page.tsx}`, `auth.ts` + `app/api/auth/[...nextauth]/route.ts`, `middleware.ts`, `components/shell/{AppShell,RailNav,TopBar}.tsx`, `components/ui/{MonoChip,VerdictChip}.tsx`, `lib/api/{client.ts,schema.d.ts}`, `lib/motion/tokens.ts`, `.storybook/*`, stories, a `VerdictChip` vitest.
**Interfaces:** `VerdictChip({verdict: 'met'|'not_met'|'insufficient'})` renders a glyph (✓ / ✕ / ○) plus text. `api` = `createClient<paths>({baseUrl: process.env.API_URL})`.
- [ ] Vitest: VerdictChip shows a glyph plus a text label for each verdict (accessibility: never color alone).
- [ ] `pnpm --filter web build` passes. `pnpm gen:api` against a running API produces `schema.d.ts`.
- [ ] Manual: log in as the coordinator, redirect to `/app/worklist`, empty state. Check dark mode.
- [ ] Commit `feat(web): tokens, auth, app shell, empty worklist`.

### Task 7: CI
**Files:** `.github/workflows/ci.yml`: a python job (pg service container `pgvector/pgvector:pg16`, `uv sync`, ruff, mypy, alembic upgrade, pytest) and a web job (pnpm, lint, typecheck, vitest, build, OpenAPI drift check: `python -m assent_api.export_openapi` then `openapi-typescript` then `git diff --exit-code`).
- [ ] Workflow lints (`actionlint` if it's available). Commit `ci: python + web pipelines`.

## Exit check
The master plan's Verification 1–8.
