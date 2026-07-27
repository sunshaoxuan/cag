param(
    [switch]$Apply,
    [switch]$Rollback
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backupRoot = Join-Path $repositoryRoot ".codex-tmp\ollama-migration"
$inspectPath = Join-Path $backupRoot "ollama-container-inspect.json"
$volumeName = "ollama"
$containerName = "ollama"

docker volume inspect $volumeName | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Required Docker volume '$volumeName' was not found."
}

$models = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 10
$modelNames = @($models.models | ForEach-Object { $_.name })
$requiredModels = @("qwen3-embedding:8b", "qwen3:14b")
$missingModels = @($requiredModels | Where-Object { $_ -notin $modelNames })

Write-Host "Ollama volume: $volumeName"
Write-Host "Installed models: $($modelNames -join ', ')"
if ($missingModels.Count -gt 0) {
    Write-Host "Models to pull: $($missingModels -join ', ')"
}
Write-Host "Target listener: 127.0.0.1:11434"
Write-Host "Target image: ollama/ollama:0.23.3"

if ($Rollback) {
    if (-not (Test-Path -LiteralPath $inspectPath)) {
        throw "Rollback metadata was not found at $inspectPath."
    }
    docker compose --profile knowledge -f (Join-Path $repositoryRoot "docker-compose.yml") stop ollama
    docker compose --profile knowledge -f (Join-Path $repositoryRoot "docker-compose.yml") rm -f ollama
    docker run -d --name $containerName --restart unless-stopped --gpus all `
        -p 11434:11434 -v "${volumeName}:/root/.ollama" ollama/ollama:latest
    Write-Host "Ollama rollback container restored with the preserved model volume."
    exit 0
}

if (-not $Apply) {
    Write-Host "Preflight complete. Re-run with -Apply to migrate the container."
    exit 0
}

New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
$existing = docker inspect $containerName 2>$null
if ($LASTEXITCODE -eq 0) {
    Set-Content -LiteralPath $inspectPath -Value $existing -Encoding utf8
    docker stop $containerName | Out-Null
    docker rm $containerName | Out-Null
}

docker compose --profile knowledge -f (Join-Path $repositoryRoot "docker-compose.yml") up -d ollama
foreach ($model in $missingModels) {
    docker exec ollama ollama pull $model
}
$status = $null
for ($attempt = 1; $attempt -le 15; $attempt += 1) {
    try {
        $status = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 5
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}
if ($null -eq $status) {
    throw "Managed Ollama did not become ready within 15 seconds."
}
Write-Host "Managed Ollama is ready. Version: $($status.version)"
