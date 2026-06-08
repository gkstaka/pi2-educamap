# Para o projeto EducaMap (banco PostGIS + Streamlit) via Docker.
# Uso: clique com o botão direito > "Executar com PowerShell" ou rode `.\stop.ps1` num terminal.

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot
Write-Host "Parando os containers do EducaMap..."
docker compose down

Write-Host "Containers parados."
