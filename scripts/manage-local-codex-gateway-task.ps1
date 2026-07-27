param(
    [ValidateSet("start", "stop", "status", "uninstall")]
    [string]$Action = "start",
    [int]$Port = 8000,
    [string]$TaskName = "CAG Local Codex Gateway"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$gatewayScript = Join-Path $PSScriptRoot "run-local-codex-gateway.ps1"
$powerShellExecutable = (
    Get-Process -Id $PID
).Path

function Get-GatewayTask {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
}

function Get-GatewayListener {
    Get-NetTCPConnection `
        -LocalAddress "127.0.0.1" `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Stop-GatewayListener {
    $listener = Get-GatewayListener
    if ($null -eq $listener) {
        return
    }

    $listenerProcess = Get-CimInstance `
        -ClassName Win32_Process `
        -Filter "ProcessId = $($listener.OwningProcess)"
    if (
        $null -eq $listenerProcess -or
        $listenerProcess.CommandLine -notmatch "uvicorn\s+app\.main:app"
    ) {
        throw (
            "Port $Port is owned by an unexpected process. " +
            "Refusing to stop PID $($listener.OwningProcess)."
        )
    }

    Stop-Process -Id $listener.OwningProcess -Force
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 250
        if ($null -eq (Get-GatewayListener)) {
            return
        }
    }
    throw "Agent Gateway did not release port $Port."
}

function Wait-GatewayReady {
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod `
                -Uri "http://127.0.0.1:$Port/health/ready" `
                -TimeoutSec 2
            if ($health.status -eq "ready") {
                return $health
            }
        }
        catch {
            continue
        }
    }
    throw "Agent Gateway did not become ready on port $Port."
}

if ($Action -eq "status") {
    $task = Get-GatewayTask
    if ($null -eq $task) {
        Write-Output "not-installed"
        exit 1
    }
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
    $listener = Get-GatewayListener
    $gatewayState = if ($null -eq $listener) { "stopped" } else { "running" }
    [pscustomobject]@{
        TaskName = $TaskName
        GatewayState = $gatewayState
        TaskState = $task.State
        LastRunTime = $taskInfo.LastRunTime
        LastTaskResult = $taskInfo.LastTaskResult
    }
    exit 0
}

if ($Action -eq "stop") {
    $task = Get-GatewayTask
    if ($null -eq $task) {
        Write-Output "not-installed"
        exit 0
    }
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Stop-GatewayListener
    Write-Output "stopped"
    exit 0
}

if ($Action -eq "uninstall") {
    $task = Get-GatewayTask
    if ($null -eq $task) {
        Write-Output "not-installed"
        exit 0
    }
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Stop-GatewayListener
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Output "uninstalled"
    exit 0
}

$existingTask = Get-GatewayTask
$existingListener = Get-GatewayListener
if ($null -ne $existingListener) {
    if ($null -eq $existingTask) {
        throw (
            "Agent Gateway is already listening on port $Port without the " +
            "managed background task."
        )
    }
    $health = Wait-GatewayReady
    [pscustomobject]@{
        TaskName = $TaskName
        GatewayState = "running"
        TaskState = $existingTask.State
        Gateway = "http://127.0.0.1:$Port"
        Health = $health.status
        Version = $health.version
    }
    exit 0
}

$arguments = @(
    "-NoProfile"
    "-ExecutionPolicy"
    "Bypass"
    "-File"
    "`"$gatewayScript`""
    "-Port"
    $Port
) -join " "
$taskAction = New-ScheduledTaskAction `
    -Execute $powerShellExecutable `
    -Argument $arguments `
    -WorkingDirectory $repositoryRoot
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited
$taskSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $taskAction `
    -Principal $taskPrincipal `
    -Settings $taskSettings `
    -Description "Runs CAG with the local ChatGPT-authenticated Codex app-server." `
    -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
$health = Wait-GatewayReady

[pscustomobject]@{
    TaskName = $TaskName
    GatewayState = "running"
    TaskState = (Get-GatewayTask).State
    Gateway = "http://127.0.0.1:$Port"
    Health = $health.status
    Version = $health.version
}
