[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
$packageId = "UB-Mannheim.TesseractOCR"
$tesseractRoot = "C:\Program Files\Tesseract-OCR"
$executable = Join-Path $tesseractRoot "tesseract.exe"
$languageFile = Join-Path $tesseractRoot "tessdata\jpn.traineddata"
$languageRevision = "87416418657359cb625c412a48b6e1d6d41c29bd"
$languageHash = "1F5DE9236D2E85F5FDF4B3C500F2D4926F8D9449F28F5394472D9E8D83B91B4D"
$languageUri = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/$languageRevision/jpn.traineddata"

if (-not (Test-Path -LiteralPath $executable)) {
    winget install --exact --id $packageId `
        --accept-package-agreements --accept-source-agreements `
        --silent --disable-interactivity
}
if (-not (Test-Path -LiteralPath $executable)) {
    throw "Tesseract installation did not create the expected executable."
}

$downloadRequired = -not (Test-Path -LiteralPath $languageFile)
if (-not $downloadRequired) {
    $downloadRequired = (Get-FileHash -LiteralPath $languageFile -Algorithm SHA256).Hash -ne $languageHash
}
if ($downloadRequired) {
    Invoke-WebRequest -Uri $languageUri -OutFile $languageFile
}
if ((Get-FileHash -LiteralPath $languageFile -Algorithm SHA256).Hash -ne $languageHash) {
    throw "Japanese OCR language data hash is invalid."
}

$environmentPath = Join-Path $RepositoryRoot "backend\.env.local"
if (-not (Test-Path -LiteralPath $environmentPath)) {
    New-Item -ItemType File -Path $environmentPath -Force | Out-Null
}
$values = [ordered]@{
    AGENT_GATEWAY_KNOWLEDGE_OCR_ENABLED = "true"
    AGENT_GATEWAY_KNOWLEDGE_OCR_EXECUTABLE = $executable
    AGENT_GATEWAY_KNOWLEDGE_OCR_LANGUAGES = "jpn+eng"
}
$lines = @(Get-Content -LiteralPath $environmentPath)
foreach ($item in $values.GetEnumerator()) {
    $pattern = "^$([regex]::Escape($item.Key))="
    $replacement = "$($item.Key)=$($item.Value)"
    $matched = $false
    $lines = @($lines | ForEach-Object {
        if ($_ -match $pattern) {
            $matched = $true
            $replacement
        } else {
            $_
        }
    })
    if (-not $matched) {
        $lines += $replacement
    }
}
Set-Content -LiteralPath $environmentPath -Value $lines -Encoding utf8

$languages = & $executable --list-langs 2>&1
if ($LASTEXITCODE -ne 0 -or $languages -notcontains "jpn" -or $languages -notcontains "eng") {
    throw "Tesseract Japanese and English language verification failed."
}
& $executable --version | Select-Object -First 1
Write-Output "OCR_RUNTIME_READY"
