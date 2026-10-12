# Usage: .\scripts\dev.ps1 <up|down|migrate|seed|api|worker|web|test|all>
param([Parameter(Mandatory)][string]$Cmd)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. "$PSScriptRoot\env.ps1"
Set-Location $root

switch ($Cmd) {
  # Native Postgres 16 + pgvector (conda-forge) and portable Redis, all under D:\DevTools. No Docker/WSL
  # needed on this 7 GB laptop; infra/docker-compose.yml is the equivalent for CI/other machines.
  'up'      {
    $pg = 'D:\DevTools\pg16\Library\bin'
    & "$pg\pg_isready.exe" -h localhost -q
    if ($LASTEXITCODE -ne 0) {
      # Start-Process (no -Wait: that would wait on the long-lived server child too), then poll.
      Start-Process "$pg\pg_ctl.exe" -ArgumentList '-D', 'D:\DevTools\pgdata', '-l', 'D:\DevTools\pgdata\server.log', 'start' -WindowStyle Hidden
      foreach ($i in 1..30) { & "$pg\pg_isready.exe" -h localhost -q; if ($LASTEXITCODE -eq 0) { break }; Start-Sleep -Milliseconds 500 }
    }
    if (-not (Get-Process redis-server -ErrorAction SilentlyContinue)) {
      Start-Process D:\DevTools\redis\redis-server.exe -ArgumentList '--port', '6379', '--maxmemory', '128mb', '--save', '""', '--appendonly', 'no' -WindowStyle Hidden
    }
    & "$pg\pg_isready.exe" -h localhost; D:\DevTools\redis\redis-cli.exe ping
  }
  'down'    {
    & 'D:\DevTools\pg16\Library\bin\pg_ctl.exe' -D D:\DevTools\pgdata stop -m fast
    D:\DevTools\redis\redis-cli.exe shutdown nosave
  }
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
