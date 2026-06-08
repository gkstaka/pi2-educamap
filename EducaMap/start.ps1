# Sobe o projeto EducaMap (banco PostGIS + Streamlit) via Docker.
# Uso: clique com o botão direito > "Executar com PowerShell" ou rode `.\start.ps1` num terminal.

$ErrorActionPreference = "Stop"

# 1. Garante que o Docker Desktop está rodando
$dockerRunning = $false
try {
    docker info | Out-Null
    $dockerRunning = $true
} catch {
    $dockerRunning = $false
}

if (-not $dockerRunning) {
    Write-Host "Docker Desktop não está rodando. Iniciando..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

    Write-Host "Aguardando o Docker ficar pronto..."
    $tentativas = 0
    do {
        Start-Sleep -Seconds 5
        $tentativas++
        try {
            docker info | Out-Null
            $dockerRunning = $true
        } catch {
            $dockerRunning = $false
        }
    } while (-not $dockerRunning -and $tentativas -lt 36)

    if (-not $dockerRunning) {
        Write-Error "Docker não ficou pronto a tempo. Abra o Docker Desktop manualmente e rode este script novamente."
        exit 1
    }
}

Write-Host "Docker pronto."

# 2. Sobe os containers (banco PostGIS + Streamlit)
Set-Location $PSScriptRoot
Write-Host "Subindo os containers (build se necessário)..."
docker compose up -d --build

# 3. Aguarda o Streamlit responder e abre o navegador
Write-Host "Aguardando o Streamlit responder em http://localhost:8501 ..."
$pronto = $false
$tentativas = 0
do {
    Start-Sleep -Seconds 3
    $tentativas++
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 3
        if ($resp.StatusCode -eq 200) { $pronto = $true }
    } catch {
        $pronto = $false
    }
} while (-not $pronto -and $tentativas -lt 40)

if ($pronto) {
    Write-Host "Streamlit no ar! Abrindo o navegador..."
    Start-Process "http://localhost:8501"
} else {
    Write-Host "O Streamlit ainda não respondeu. Verifique os logs com: docker logs -f streamlit_educamap"
}
