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

One-time machine setup (already done on the dev laptop, everything on D:): Postgres 16 + pgvector via
`micromamba create -p D:\DevTools\pg16 -c conda-forge postgresql=16 pgvector`, `initdb -D D:\DevTools\pgdata -U assent`,
portable Redis in `D:\DevTools\redis`, Node 22 via fnm in `D:\DevTools\fnm`, Python 3.12 via `uv python install`.

Log in at http://localhost:3000/login as `coordinator@assent.dev` / `assent-dev`.

| Command | What it does |
|---|---|
| `.\scripts\dev.ps1 up` / `down` | Postgres 16 + pgvector and Redis, run natively from `D:\DevTools` (no Docker/WSL; `infra/docker-compose.yml` is the equivalent elsewhere) |
| `.\scripts\dev.ps1 migrate` | Alembic upgrade head |
| `.\scripts\dev.ps1 seed` | Demo org + one user per role |
| `.\scripts\dev.ps1 test` | pytest + vitest |
| `pnpm gen:api` | Regenerate the typed API client from FastAPI's OpenAPI |

### Policies, data and the agent

| Command | What it does |
|---|---|
| `uv run python -m assent_agents.policy.ingest L39240 L39015 L36920` | Pull LCD snapshots from the CMS Coverage API into `data/policies/` |
| `uv run python -m assent_api.policy_load` | Load snapshots + gold criteria trees into the DB (approved) |
| `uv run python -m assent_agents.policy.compile_cli L39240 15` | Compile an LCD with the LLM and score it against its gold tree (needs `OPENAI_API_KEY`) |
| `.\scripts\synthea.ps1` | Generate the Synthea background population (JDK + jar on D:) |
| `uv run python -m assent_evals.synth.build --n 50 --notes llm` | Build the ESI benchmark (fact sheets, notes, FHIR bundles); `--notes template` needs no key |
| `uv run python -m assent_evals.load esi` | Load benchmark gold into `eval_cases` |
| `uv run python -m assent_evals.run_case esi-001 --llm oracle` | Run one case end to end and print cited verdicts |
| `uv run python -m assent_evals.bench --split dev --llm oracle\|openai` | Score the pipeline against gold; results in `data/bench/results/` |
| `uv run python -m assent_evals.record_fixture esi-001` | Record a run's event stream to `data/fixtures/` for offline replay |

`--llm oracle` is a perfect reviewer that only sees what retrieval shows it. It measures everything except the LLM (retrieval recall, de-identification, citation verification) and needs no API key. `--llm openai` records every call to `data/fixtures/cassettes/`, so re-runs are free. Worker runs use `AGENT_LLM` in `.env` (`openai`, or `oracle` for benchmark patients).
