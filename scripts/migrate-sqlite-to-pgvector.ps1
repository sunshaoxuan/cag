param(
    [string]$Source = "",
    [string]$OutputDirectory = "",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendRoot = Join-Path $repositoryRoot "backend"
$pythonExecutable = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
    throw "Backend virtual environment is missing."
}

if (-not $Source) {
    $Source = Join-Path (
        Join-Path $repositoryRoot "workspaces\.gateway"
    ) "agent_gateway.db"
}
$Source = (Resolve-Path -LiteralPath $Source).Path

if (-not $OutputDirectory) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDirectory = Join-Path (
        Join-Path $repositoryRoot "backups\knowledge-migrations"
    ) $timestamp
}

if (-not $env:AGENT_GATEWAY_MIGRATION_TARGET_URL) {
    if ($env:AGENT_GATEWAY_DATABASE_URL) {
        $env:AGENT_GATEWAY_MIGRATION_TARGET_URL = (
            $env:AGENT_GATEWAY_DATABASE_URL
        )
    }
    else {
        throw (
            "Set AGENT_GATEWAY_MIGRATION_TARGET_URL to the target " +
            "PostgreSQL pgvector database."
        )
    }
}

Push-Location $backendRoot
try {
    if ($Apply) {
        $savedDatabaseUrl = $env:AGENT_GATEWAY_DATABASE_URL
        $env:AGENT_GATEWAY_DATABASE_URL = (
            $env:AGENT_GATEWAY_MIGRATION_TARGET_URL
        )
        try {
            & $pythonExecutable -m alembic upgrade head
            if ($LASTEXITCODE -ne 0) {
                throw "Target PostgreSQL schema migration failed."
            }
        }
        finally {
            $env:AGENT_GATEWAY_DATABASE_URL = $savedDatabaseUrl
        }
    }

    $arguments = @(
        "-m",
        "app.migrations.sqlite_to_pgvector",
        "--source",
        $Source,
        "--output-dir",
        $OutputDirectory
    )
    if ($Apply) {
        $arguments += "--apply"
    }
    & $pythonExecutable @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "SQLite to PostgreSQL pgvector migration failed."
    }
}
finally {
    Pop-Location
}
