
param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "python"
}

if ($Clean) {
    Write-Host "==> Limpiando salidas anteriores..." -ForegroundColor Yellow
    $dataDir = Join-Path $projectRoot "data"
    $reportDir = Join-Path $projectRoot "reportes"

    if (Test-Path $dataDir) {
        Get-ChildItem -Path $dataDir -Filter "*.parquet" | Remove-Item -Force
        Get-ChildItem -Path $dataDir -Filter "duplicados_encontrados.json" | Remove-Item -Force
        Get-ChildItem -Path $dataDir -Filter "metadatos_ingesta.json" | Remove-Item -Force
    }

    Get-ChildItem -Path $projectRoot -Filter "scorecard_*.json" | Remove-Item -Force

    # Nota: se conservan los reportes HTML para trazabilidad.
}

Write-Host "==> Ejecutando pipeline completo..." -ForegroundColor Cyan
& $pythonExe "pipeline.py"
Read-Host "Presiona Enter para continuar al siguiente paso"

Write-Host "==> Generando reporte HTML..." -ForegroundColor Cyan
& $pythonExe "reporte_html.py"
Read-Host "Presiona Enter para abrir el reporte"

$reportDir = Join-Path $projectRoot "reportes"
if (-not (Test-Path $reportDir)) {
    throw "No se encontro la carpeta 'reportes'."
}

$ultimoReporte = Get-ChildItem -Path $reportDir -Filter "reporte_integridad_*.html" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $ultimoReporte) {
    throw "No se encontro ningun reporte HTML para abrir."
}

Write-Host "==> Abriendo reporte: $($ultimoReporte.FullName)" -ForegroundColor Green
Start-Process $ultimoReporte.FullName
