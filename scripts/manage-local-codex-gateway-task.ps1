param(
    [ValidateSet("start", "stop", "status", "uninstall")]
    [string]$Action = "start",
    [int]$Port = 8000,
    [string]$TaskName = "CAG Local Codex Gateway"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$supervisorScript = Join-Path $PSScriptRoot "supervise-local-codex-gateway.ps1"
$powerShellExecutable = (Get-Process -Id $PID).Path
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

function Get-GatewayTask {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
}

function Get-GatewayListener {
    Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Test-GatewayListenerIsAllInterfaces {
    param(
        [Parameter(Mandatory)]
        $Listener
    )

    $Listener.LocalAddress -in @("0.0.0.0", "::")
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
    throw "One Agent Gateway did not release port $Port."
}

function Wait-GatewayReady {
    for ($attempt = 0; $attempt -lt 900; $attempt++) {
        Start-Sleep -Seconds 1
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
    throw "One Agent Gateway did not become ready on port $Port."
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
        ListenAddress = if ($null -eq $listener) {
            $null
        }
        else {
            "$($listener.LocalAddress):$Port"
        }
        SupervisorState = $task.State
        AutoStart = @($task.Triggers).Count -gt 0
        RestartCount = $task.Settings.RestartCount
        RestartInterval = $task.Settings.RestartInterval
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

$existingListener = Get-GatewayListener
if (
    $null -ne $existingListener -and
    -not (Test-GatewayListenerIsAllInterfaces -Listener $existingListener)
) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Stop-GatewayListener
}

$arguments = @(
    "-NoProfile"
    "-ExecutionPolicy"
    "Bypass"
    "-File"
    "`"$supervisorScript`""
    "-Port"
    $Port
) -join " "
$taskAction = New-ScheduledTaskAction `
    -Execute $powerShellExecutable `
    -Argument $arguments `
    -WorkingDirectory $repositoryRoot
$startupTrigger = New-ScheduledTaskTrigger -AtStartup
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $currentIdentity
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId $currentIdentity `
    -LogonType Interactive `
    -RunLevel Limited
$taskSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew `
    -WakeToRun

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $taskAction `
    -Trigger @($startupTrigger, $logonTrigger) `
    -Principal $taskPrincipal `
    -Settings $taskSettings `
    -Description (
        "Keeps One Agent Gateway running with automatic startup, health " +
        "supervision and delayed recovery."
    ) `
    -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
$health = Wait-GatewayReady
$listener = Get-GatewayListener
if (
    $null -eq $listener -or
    -not (Test-GatewayListenerIsAllInterfaces -Listener $listener)
) {
    throw "One Agent Gateway is ready but is not listening on all interfaces."
}

[pscustomobject]@{
    TaskName = $TaskName
    GatewayState = "running"
    ListenAddress = "$($listener.LocalAddress):$Port"
    SupervisorState = (Get-GatewayTask).State
    AutoStart = $true
    RestartCount = (Get-GatewayTask).Settings.RestartCount
    Gateway = "http://127.0.0.1:$Port"
    Health = $health.status
    Version = $health.version
}
