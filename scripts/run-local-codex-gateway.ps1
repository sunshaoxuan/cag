param(
    [int]$Port = 8000,
    [string]$CodexExecutable = ""
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendRoot = Join-Path $repositoryRoot "backend"
$pythonExecutable = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
    throw "Backend virtual environment is missing. Install backend development dependencies first."
}

if (-not $CodexExecutable) {
    $pluginExecutable = Join-Path $env:USERPROFILE ".codex\plugins\.plugin-appserver\codex.exe"
    if (Test-Path -LiteralPath $pluginExecutable -PathType Leaf) {
        $CodexExecutable = $pluginExecutable
    }
}

if (-not $CodexExecutable) {
    $codexCommand = Get-Command codex.exe -ErrorAction SilentlyContinue
    if ($null -ne $codexCommand -and (Test-Path -LiteralPath $codexCommand.Source)) {
        $CodexExecutable = $codexCommand.Source
    }
}

if (-not $CodexExecutable -or -not (Test-Path -LiteralPath $CodexExecutable -PathType Leaf)) {
    throw "A callable local Codex executable was not found."
}

$savedErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$loginOutput = & $CodexExecutable login status 2>&1
$loginExitCode = $LASTEXITCODE
$ErrorActionPreference = $savedErrorActionPreference
$loginStatus = $loginOutput | Out-String
if ($loginExitCode -ne 0 -or $loginStatus -notmatch "Logged in using ChatGPT") {
    throw "Local Codex is not authenticated through ChatGPT."
}

$env:AGENT_GATEWAY_RUNTIME_PROVIDER = "codex-app-server"
$env:AGENT_GATEWAY_CODEX_EXECUTABLE = $CodexExecutable
$env:AGENT_GATEWAY_PROJECTS_DIR = Join-Path $repositoryRoot "projects"
$env:AGENT_GATEWAY_WORKSPACE_ROOT = Join-Path $repositoryRoot "workspaces"
if (-not $env:AGENT_GATEWAY_SELF_IMPROVEMENT_ROOT) {
    $selfImprovementRoot = Join-Path (Split-Path $repositoryRoot -Parent) "codex-selfimp"
    if (Test-Path -LiteralPath $selfImprovementRoot -PathType Container) {
        $env:AGENT_GATEWAY_SELF_IMPROVEMENT_ROOT = $selfImprovementRoot
    }
}

Write-Host "Starting Agent Gateway with the local ChatGPT-authenticated Codex runtime."
Write-Host "Gateway: http://127.0.0.1:$Port"

Push-Location $backendRoot
try {
    & $pythonExecutable -m uvicorn app.main:app --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
