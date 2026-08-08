param(
    [int]$Port = 8000,
    [string]$CodexExecutable = ""
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendRoot = Join-Path $repositoryRoot "backend"
$pythonExecutable = Join-Path $backendRoot ".venv\Scripts\python.exe"

function Stop-OwnedProcessTree {
    param(
        [Parameter(Mandatory)]
        [int]$RootProcessId
    )

    $children = @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ParentProcessId -eq $RootProcessId }
    )
    foreach ($child in $children) {
        Stop-OwnedProcessTree -RootProcessId $child.ProcessId
    }
    $process = Get-Process -Id $RootProcessId -ErrorAction SilentlyContinue
    if ($null -ne $process) {
        Stop-Process -Id $RootProcessId -Force
    }
}

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
$authMode = $null
if ($loginExitCode -eq 0 -and $loginStatus -match "Logged in using ChatGPT") {
    $authMode = "ChatGPT"
}
elseif ($loginExitCode -eq 0 -and $loginStatus -match "Logged in using an API key") {
    $authMode = "API key"
}
else {
    throw "Local Codex is not authenticated through ChatGPT or an API key."
}

$env:AGENT_GATEWAY_RUNTIME_PROVIDER = "codex-app-server"
$env:AGENT_GATEWAY_CODEX_EXECUTABLE = $CodexExecutable
$env:AGENT_GATEWAY_CODEX_REQUIRE_CHATGPT_AUTH = "false"
$env:AGENT_GATEWAY_PROJECTS_DIR = Join-Path $repositoryRoot "projects"
$env:AGENT_GATEWAY_WORKSPACE_ROOT = Join-Path $repositoryRoot "workspaces"
if (-not $env:AGENT_GATEWAY_SELF_IMPROVEMENT_ROOT) {
    $selfImprovementRoot = Join-Path (Split-Path $repositoryRoot -Parent) "codex-selfimp"
    if (Test-Path -LiteralPath $selfImprovementRoot -PathType Container) {
        $env:AGENT_GATEWAY_SELF_IMPROVEMENT_ROOT = $selfImprovementRoot
    }
}
if (-not $env:AGENT_GATEWAY_KNOWLEDGE_ENABLED) {
    $env:AGENT_GATEWAY_KNOWLEDGE_ENABLED = "true"
}
if (-not $env:AGENT_GATEWAY_OLLAMA_BASE_URL) {
    $env:AGENT_GATEWAY_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
}
if (-not $env:AGENT_GATEWAY_KNOWLEDGE_ALLOWED_ROOTS) {
    $env:AGENT_GATEWAY_KNOWLEDGE_ALLOWED_ROOTS = (
        Split-Path $repositoryRoot -Parent
    )
}

Write-Host "Starting One Agent Gateway with the local Codex runtime authenticated through $authMode."
Write-Host "Gateway listener: http://0.0.0.0:$Port"
Write-Host "Local access: http://127.0.0.1:$Port"

$dockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
if ($null -ne $dockerCommand) {
    Push-Location $repositoryRoot
    try {
        & $dockerCommand.Source compose up -d postgres redis
        if ($LASTEXITCODE -ne 0) {
            throw "PostgreSQL and Redis startup failed."
        }
    }
    finally {
        Pop-Location
    }
}

Push-Location $backendRoot
try {
    $databaseReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        & $pythonExecutable -c (
            "from app.config import get_settings; " +
            "from app.database import Database; " +
            "s=get_settings(); " +
            "d=Database(s.database_url); " +
            "d.is_ready(); " +
            "print(d.storage_status()); " +
            "d.dispose()"
        )
        if ($LASTEXITCODE -eq 0) {
            $databaseReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $databaseReady) {
        throw "PostgreSQL with pgvector did not become ready."
    }
    & $pythonExecutable -m app.migrations.legacy_baseline
    if ($LASTEXITCODE -ne 0) {
        throw "One Agent Gateway legacy database baseline failed."
    }
    & $pythonExecutable -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "One Agent Gateway database migration failed."
    }
    & $pythonExecutable -m app.migrations.auto_cutover
    if ($LASTEXITCODE -ne 0) {
        throw "Legacy SQLite cutover did not complete safely."
    }
    & $pythonExecutable -c (
        "from redis import Redis; " +
        "from app.config import get_settings; " +
        "client=Redis.from_url(get_settings().redis_url); " +
        "assert client.ping(); client.close()"
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Redis did not become ready."
    }
    if ($null -ne $dockerCommand) {
        Push-Location $repositoryRoot
        try {
            & $dockerCommand.Source compose build frontend
            if ($LASTEXITCODE -ne 0) {
                throw "One Agent Gateway management UI build failed."
            }
            & $dockerCommand.Source compose up -d --no-deps frontend
            if ($LASTEXITCODE -ne 0) {
                throw "One Agent Gateway management UI refresh failed."
            }
        }
        finally {
            Pop-Location
        }
    }
    $runtimeLogDirectory = Join-Path $repositoryRoot "workspaces\.gateway\logs"
    New-Item -ItemType Directory -Path $runtimeLogDirectory -Force | Out-Null
    $workerOutput = Join-Path $runtimeLogDirectory "gateway-worker.out.log"
    $workerError = Join-Path $runtimeLogDirectory "gateway-worker.err.log"
    $apiOutput = Join-Path $runtimeLogDirectory "gateway-api.out.log"
    $apiError = Join-Path $runtimeLogDirectory "gateway-api.err.log"

    $env:AGENT_GATEWAY_PROCESS_ROLE = "worker"
    $workerProcess = Start-Process `
        -FilePath $pythonExecutable `
        -ArgumentList @("-m", "app.worker") `
        -WorkingDirectory $backendRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $workerOutput `
        -RedirectStandardError $workerError `
        -PassThru
    $env:AGENT_GATEWAY_PROCESS_ROLE = "api"
    $apiProcess = Start-Process `
        -FilePath $pythonExecutable `
        -ArgumentList @(
            "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", $Port
        ) `
        -WorkingDirectory $backendRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $apiOutput `
        -RedirectStandardError $apiError `
        -PassThru
    try {
        while (-not $workerProcess.HasExited -and -not $apiProcess.HasExited) {
            Start-Sleep -Seconds 1
        }
        if ($workerProcess.HasExited) {
            throw "Knowledge worker exited with code $($workerProcess.ExitCode)."
        }
        throw "Gateway API exited with code $($apiProcess.ExitCode)."
    }
    finally {
        foreach ($process in @($workerProcess, $apiProcess)) {
            if ($null -ne $process) {
                Stop-OwnedProcessTree -RootProcessId $process.Id
                $process.Dispose()
            }
        }
    }
}
finally {
    Pop-Location
}
