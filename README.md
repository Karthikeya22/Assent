# Assent

Prior authorization, argued with evidence. See [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [FRONTEND.md](FRONTEND.md) and [BUILD_PLAN.md](BUILD_PLAN.md).

Synthetic data only. No PHI.

## Dev quickstart (Windows, PowerShell)

```powershell
. .\scripts\env.ps1          # routes all tools/caches to D:
Copy-Item .env.example .env  # then fill in OPENAI_API_KEY
uv sync --all-packages
pnpm install
.\scripts\dev.ps1 all        # postgres+redis, migrate, seed, api, worker, web
```

Log in at http://localhost:3000/login as `coordinator@assent.dev` / `assent-dev`.

| Command | What it does |
|---|---|
| `.\scripts\dev.ps1 up` / `down` | Postgres 16 + pgvector and Redis 7 (Docker) |
| `.\scripts\dev.ps1 migrate` | Alembic upgrade head |
| `.\scripts\dev.ps1 seed` | Demo org + one user per role |
| `.\scripts\dev.ps1 test` | pytest + vitest |
| `pnpm gen:api` | Regenerate the typed API client from FastAPI's OpenAPI |
