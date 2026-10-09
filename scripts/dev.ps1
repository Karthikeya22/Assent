# Usage: .\scripts\dev.ps1 <up|down|migrate|seed|api|worker|web|test|all>
param([Parameter(Mandatory)][string]$Cmd)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot\env.ps1"
Set-Location $root

switch ($Cmd) {
  'up'      { docker compose -f infra/docker-compose.yml up -d --wait }
  'down'    { docker compose -f infra/docker-compose.yml down }
  'migrate' { uv run --directory apps/api alembic upgrade head }
  'seed'    { uv run python -m assent_api.seed }
  'api'     { uv run uvicorn assent_api.main:app --reload --port 8000 }
  'worker'  { uv run arq assent_worker.main.WorkerSettings }
  'web'     { pnpm --filter web dev }
  'test'    { uv run pytest; pnpm --filter web test }
  'all'     {
    & $PSCommandPath up; & $PSCommandPath migrate; & $PSCommandPath seed
    Start-Process pwsh -ArgumentList '-NoExit', '-File', $PSCommandPath, 'api'
    Start-Process pwsh -ArgumentList '-NoExit', '-File', $PSCommandPath, 'worker'
    & $PSCommandPath web
  }
  default   { throw "unknown command: $Cmd" }
}
