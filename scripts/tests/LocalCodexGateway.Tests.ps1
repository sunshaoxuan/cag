$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runScript = Join-Path $repositoryRoot "scripts\run-local-codex-gateway.ps1"
$manageScript = Join-Path $repositoryRoot "scripts\manage-local-codex-gateway-task.ps1"

Describe "Local Codex Gateway PowerShell scripts" {
    It "parses both entrypoint scripts without errors" {
        foreach ($scriptPath in @($runScript, $manageScript)) {
            $tokens = $null
            $errors = $null
            [System.Management.Automation.Language.Parser]::ParseFile(
                $scriptPath,
                [ref]$tokens,
                [ref]$errors
            ) | Out-Null
            $errors.Count | Should Be 0
        }
    }

    It "uses the ignored workspace state directory by default" {
        $content = Get-Content -Raw -LiteralPath $runScript
        $content | Should Match 'workspaces\\\.gateway'
        $content | Should Match 'AGENT_GATEWAY_DATABASE_URL'
    }

    It "binds the Gateway to every IPv4 interface" {
        $content = Get-Content -Raw -LiteralPath $runScript
        $content | Should Match '--host 0\.0\.0\.0'
        $content | Should Not Match '--host 127\.0\.0\.1'
    }

    It "detects the listener by port and requires an all-interface address" {
        $content = Get-Content -Raw -LiteralPath $manageScript
        $content | Should Match 'Get-NetTCPConnection'
        $content | Should Match 'LocalAddress -in @\("0\.0\.0\.0", "::"\)'
        $content | Should Not Match '-LocalAddress "127\.0\.0\.1"'
    }

    It "reports the persistent Gateway as running" {
        $status = & $manageScript status
        $status.GatewayState | Should Be "running"
    }

    It "starts idempotently while the Gateway is already healthy" {
        $result = & $manageScript start
        $result.GatewayState | Should Be "running"
        $result.Health | Should Be "ready"
    }
}
