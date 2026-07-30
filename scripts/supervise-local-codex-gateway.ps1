param(
    [int]$Port = 8000,
    [ValidateRange(5, 300)]
    [int]$CheckIntervalSeconds = 15,
    [ValidateRange(5, 600)]
    [int]$RestartDelaySeconds = 30,
    [ValidateRange(2, 20)]
    [int]$UnhealthyThreshold = 4
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$gatewayScript = Join-Path $PSScriptRoot "run-local-codex-gateway.ps1"
$powerShellExecutable = (Get-Process -Id $PID).Path
$logDirectory = Join-Path $repositoryRoot "workspaces\.gateway\logs"
$logPath = Join-Path $logDirectory "gateway-supervisor.log"
$maximumLogBytes = 10MB
$retainedLogFiles = 5

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

function Rotate-SupervisorLog {
    if (
        -not (Test-Path -LiteralPath $logPath -PathType Leaf) -or
        (Get-Item -LiteralPath $logPath).Length -lt $maximumLogBytes
    ) {
        return
    }

    $oldestLog = "$logPath.$retainedLogFiles"
    if (Test-Path -LiteralPath $oldestLog -PathType Leaf) {
        Remove-Item -LiteralPath $oldestLog -Force
    }
    for ($index = $retainedLogFiles - 1; $index -ge 1; $index--) {
        $source = "$logPath.$index"
        if (Test-Path -LiteralPath $source -PathType Leaf) {
            Move-Item -LiteralPath $source -Destination "$logPath.$($index + 1)"
        }
    }
    Move-Item -LiteralPath $logPath -Destination "$logPath.1"
}

function Write-SupervisorLog {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Rotate-SupervisorLog
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffK"
    Add-Content `
        -LiteralPath $logPath `
        -Value "$timestamp $Message" `
        -Encoding utf8
}

function Get-GatewayListener {
    Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Get-ListenerProcess {
    param(
        [Parameter(Mandatory)]
        $Listener
    )

    Get-CimInstance `
        -ClassName Win32_Process `
        -Filter "ProcessId = $($Listener.OwningProcess)" `
        -ErrorAction SilentlyContinue
}

function Test-GatewayProcess {
    param(
        [Parameter(Mandatory)]
        $Process
    )

    (
        $null -ne $Process -and
        $Process.CommandLine -match "uvicorn\s+app\.main:app" -and
        $Process.CommandLine -match "--port\s+$Port(?:\s|$)"
    )
}

function Test-GatewayReady {
    try {
        $health = Invoke-RestMethod `
            -Uri "http://127.0.0.1:$Port/health/ready" `
            -TimeoutSec 5
        $health.status -eq "ready"
    }
    catch {
        $false
    }
}

$consecutiveUnhealthyChecks = 0
$lastReportedState = ""
$launcherProcess = $null
Write-SupervisorLog (
    "supervisor.started port=$Port check_interval_seconds=" +
    "$CheckIntervalSeconds restart_delay_seconds=$RestartDelaySeconds"
)

while ($true) {
    $listener = Get-GatewayListener
    if ($null -eq $listener) {
        $consecutiveUnhealthyChecks = 0
        if (
            $null -ne $launcherProcess -and
            -not $launcherProcess.HasExited
        ) {
            Start-Sleep -Seconds $CheckIntervalSeconds
            continue
        }
        if (
            $null -ne $launcherProcess -and
            $launcherProcess.HasExited
        ) {
            Write-SupervisorLog (
                "gateway.launcher_exited exit_code=$($launcherProcess.ExitCode)"
            )
            $launcherProcess.Dispose()
            $launcherProcess = $null
        }
        if ($lastReportedState -ne "starting") {
            Write-SupervisorLog "gateway.starting reason=no_listener"
            $lastReportedState = "starting"
        }
        try {
            $launcherProcess = Start-Process `
                -FilePath $powerShellExecutable `
                -ArgumentList @(
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "`"$gatewayScript`"",
                    "-Port",
                    $Port
                ) `
                -WorkingDirectory $repositoryRoot `
                -WindowStyle Hidden `
                -PassThru
            Write-SupervisorLog (
                "gateway.launcher_started pid=$($launcherProcess.Id)"
            )
        }
        catch {
            $safeError = $_.Exception.Message.Replace(
                [Environment]::NewLine,
                " "
            )
            Write-SupervisorLog "gateway.start_failed error=$safeError"
        }
        Start-Sleep -Seconds $CheckIntervalSeconds
        continue
    }

    $listenerProcess = Get-ListenerProcess -Listener $listener
    $expectedAddress = $listener.LocalAddress -in @("0.0.0.0", "::")
    $expectedProcess = Test-GatewayProcess -Process $listenerProcess
    if (-not $expectedAddress -or -not $expectedProcess) {
        $consecutiveUnhealthyChecks = 0
        if ($lastReportedState -ne "unexpected_listener") {
            Write-SupervisorLog (
                "gateway.unexpected_listener address=$($listener.LocalAddress) " +
                "pid=$($listener.OwningProcess)"
            )
            $lastReportedState = "unexpected_listener"
        }
        Start-Sleep -Seconds $CheckIntervalSeconds
        continue
    }

    if (Test-GatewayReady) {
        $consecutiveUnhealthyChecks = 0
        if ($lastReportedState -ne "ready") {
            Write-SupervisorLog (
                "gateway.ready address=$($listener.LocalAddress) " +
                "pid=$($listener.OwningProcess)"
            )
            $lastReportedState = "ready"
        }
        Start-Sleep -Seconds $CheckIntervalSeconds
        continue
    }

    $consecutiveUnhealthyChecks++
    if ($lastReportedState -ne "unhealthy") {
        Write-SupervisorLog (
            "gateway.unhealthy pid=$($listener.OwningProcess) " +
            "threshold=$UnhealthyThreshold"
        )
        $lastReportedState = "unhealthy"
    }
    if ($consecutiveUnhealthyChecks -ge $UnhealthyThreshold) {
        Write-SupervisorLog (
            "gateway.restarting pid=$($listener.OwningProcess) " +
            "reason=health_threshold"
        )
        Stop-Process -Id $listener.OwningProcess -Force
        if (
            $null -ne $launcherProcess -and
            -not $launcherProcess.HasExited
        ) {
            Stop-Process -Id $launcherProcess.Id -Force
            $launcherProcess.WaitForExit()
        }
        if ($null -ne $launcherProcess) {
            $launcherProcess.Dispose()
            $launcherProcess = $null
        }
        $consecutiveUnhealthyChecks = 0
        $lastReportedState = "restarting"
        Start-Sleep -Seconds $RestartDelaySeconds
        continue
    }
    Start-Sleep -Seconds $CheckIntervalSeconds
}
