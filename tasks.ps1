# Wrapper PowerShell dos alvos padronizados. Logica em tasks.py (fonte unica).
# Uso: .\tasks.ps1 <alvo> [args...]
#   (setup | clean | test | run-pipeline | lint | format | map | help |
#    sync | import-nintendo <csv> | serve)
# Compativel com Windows PowerShell 5.1 e PowerShell 7+.
param(
    [Parameter(Position = 0)][string]$Target = "help",
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)][string[]]$Rest
)

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { Write-Error "Python nao encontrado no PATH."; exit 1 }

& $py.Source (Join-Path $PSScriptRoot "tasks.py") $Target @Rest
exit $LASTEXITCODE
