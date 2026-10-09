# Dot-source in any shell: `. .\scripts\env.ps1`
# Keeps every tool, cache and temp file on D: (C: is near-full).
$env:Path = "D:\DevTools\fnm\aliases\default;D:\DevTools\uv-tools\bin;D:\DevTools\npm-global;$env:Path"
$env:TEMP = 'D:\.tmp'; $env:TMP = 'D:\.tmp'
$env:UV_CACHE_DIR = 'D:\.cache\uv'
$env:UV_PYTHON_INSTALL_DIR = 'D:\DevTools\uv-python'
$env:HF_HOME = 'D:\.cache\huggingface'
$env:PIP_CACHE_DIR = 'D:\.cache\pip'
$env:npm_config_cache = 'D:\.cache\npm'
$env:PLAYWRIGHT_BROWSERS_PATH = 'D:\DevTools\ms-playwright'
$env:PRE_COMMIT_HOME = 'D:\.cache\pre-commit'
$env:NEXT_TELEMETRY_DISABLED = '1'
$dockerBin = 'D:\DevTools\Docker\resources\bin'
if (Test-Path $dockerBin) { $env:Path = "$dockerBin;$env:Path" }
