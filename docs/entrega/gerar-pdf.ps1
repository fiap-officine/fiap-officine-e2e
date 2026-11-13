# Gera relatorio-fase4.pdf a partir de relatorio-fase4.html usando o Microsoft
# Edge (ou Google Chrome) em modo headless. Os diagramas Mermaid são renderizados
# no navegador, então é preciso internet (o mermaid.js vem do jsDelivr).
#
# Uso:  powershell -ExecutionPolicy Bypass -File docs/entrega/gerar-pdf.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$html = Join-Path $here "relatorio-fase4.html"
$pdf = Join-Path $here "relatorio-fase4.pdf"

$browser = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $browser) { throw "Microsoft Edge ou Google Chrome não encontrado." }

$profileDir = Join-Path $env:TEMP "officine-pdf-profile"
$uri = ([System.Uri]$html).AbsoluteUri
$args = @(
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
    "--user-data-dir=$profileDir", "--virtual-time-budget=20000",
    "--print-to-pdf=$pdf", $uri
)
$proc = Start-Process -FilePath $browser -ArgumentList $args -Wait -PassThru -WindowStyle Hidden
if ($proc.ExitCode -ne 0 -or -not (Test-Path $pdf)) { throw "Falha ao gerar o PDF (exit $($proc.ExitCode))." }
Write-Host "PDF gerado: $pdf"
