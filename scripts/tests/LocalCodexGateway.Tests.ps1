$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runScript = Join-Path $repositoryRoot "scripts\run-local-codex-gateway.ps1"
$manageScript = Join-Path $repositoryRoot "scripts\manage-local-codex-gateway-task.ps1"
$supervisorScript = Join-Path $repositoryRoot "scripts\supervise-local-codex-gateway.ps1"
$migrationScript = Join-Path $repositoryRoot "scripts\migrate-sqlite-to-pgvector.ps1"

Describe "Local Codex Gateway PowerShell scripts" {
    It "parses both entrypoint scripts without errors" {
        foreach ($scriptPath in @(
            $runScript,
            $manageScript,
            $supervisorScript,
            $migrationScript
        )) {
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

    It "requires PostgreSQL with pgvector for the managed runtime" {
        $content = Get-Content -Raw -LiteralPath $runScript
        $content | Should Match 'Database\(s\.database_url\)'
        $content | Should Match 'storage_status'
        $content | Should Match 'app\.migrations\.auto_cutover'
        $content | Should Match 'Redis\.from_url'
        $content | Should Match 'compose build frontend'
        $content | Should Match 'compose up -d --no-deps frontend'
        $content | Should Not Match 'sqlite\+pysqlite'
        $content | Should Not Match 'agent_gateway\.db'
    }

    It "keeps the old SQLite path inside the explicit migration tool" {
        $content = Get-Content -Raw -LiteralPath $migrationScript
        $content | Should Match 'agent_gateway\.db'
        $content | Should Match 'AGENT_GATEWAY_MIGRATION_TARGET_URL'
        $content | Should Match '\[switch\]\$Apply'
        $content | Should Match '\[switch\]\$ReplaceTarget'
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

    It "installs automatic startup and failure recovery" {
        $content = Get-Content -Raw -LiteralPath $manageScript
        $content | Should Match 'New-ScheduledTaskTrigger -AtStartup'
        $content | Should Match 'New-ScheduledTaskTrigger -AtLogOn'
        $content | Should Match '-RestartCount 999'
        $content | Should Match '-RestartInterval \(New-TimeSpan -Minutes 1\)'
        $content | Should Match '-MultipleInstances IgnoreNew'
        $content | Should Match 'supervise-local-codex-gateway\.ps1'
    }

    It "supervises health and rotates persistent logs" {
        $content = Get-Content -Raw -LiteralPath $supervisorScript
        $content | Should Match '/health/ready'
        $content | Should Match 'UnhealthyThreshold'
        $content | Should Match 'gateway\.restarting'
        $content | Should Match 'gateway-supervisor\.log'
        $content | Should Match 'retainedLogFiles = 5'
    }

    It "reports the persistent Gateway as running" {
        $status = & $manageScript status
        $status.GatewayState | Should Be "running"
        $status.AutoStart | Should Be $true
        $status.RestartCount | Should Be 999
    }

    It "starts idempotently while the Gateway is already healthy" {
        $result = & $manageScript start
        $result.GatewayState | Should Be "running"
        $result.Health | Should Be "ready"
        $result.AutoStart | Should Be $true
        $result.RestartCount | Should Be 999
    }
}
