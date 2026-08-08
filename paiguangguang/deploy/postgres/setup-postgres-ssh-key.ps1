param(
    [ValidateNotNullOrEmpty()]
    [string]$ServerHost = "1.12.47.29",

    [ValidateNotNullOrEmpty()]
    [string]$ServerUser = "root",

    [ValidateNotNullOrEmpty()]
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\paiguangguang_postgres_ed25519"
)

$ErrorActionPreference = "Stop"

foreach ($commandName in @("ssh", "ssh-keygen")) {
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "$commandName was not found. Install Windows OpenSSH Client first."
    }
}

$keyDirectory = Split-Path -Parent $IdentityFile
if (-not (Test-Path -LiteralPath $keyDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $keyDirectory -Force | Out-Null
}

if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
    Write-Host "Creating a dedicated SSH key..."
    & ssh-keygen `
        -t ed25519 `
        -f "$IdentityFile" `
        -N '""' `
        -C "postgres-tunnel@$ServerHost"

    if ($LASTEXITCODE -ne 0) {
        throw "ssh-keygen exited with code $LASTEXITCODE."
    }
}

$publicKeyFile = "$IdentityFile.pub"
if (-not (Test-Path -LiteralPath $publicKeyFile -PathType Leaf)) {
    throw "SSH public key not found: $publicKeyFile"
}

Write-Host "Installing the public key on $ServerUser@$ServerHost."
Write-Host "Enter the server password once when prompted."

Get-Content -Raw -LiteralPath $publicKeyFile |
    & ssh "$ServerUser@$ServerHost" `
        'umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys; chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys'

if ($LASTEXITCODE -ne 0) {
    throw "Public key installation failed with code $LASTEXITCODE."
}

& ssh `
    -i "$IdentityFile" `
    -o "BatchMode=yes" `
    -o "ConnectTimeout=10" `
    "$ServerUser@$ServerHost" `
    "exit"

if ($LASTEXITCODE -ne 0) {
    throw "Passwordless SSH verification failed with code $LASTEXITCODE."
}

Write-Host "Passwordless SSH is ready."
Write-Host "Run .\start-postgres-tunnel.ps1 to start the tunnel."

