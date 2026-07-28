param(
    [ValidateNotNullOrEmpty()]
    [string]$ServerHost = "1.12.47.29",

    [ValidateNotNullOrEmpty()]
    [string]$ServerUser = "root",

    [ValidateNotNullOrEmpty()]
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\paiguangguang_postgres_ed25519",

    [ValidateRange(1, 65535)]
    [int]$LocalPort = 15432,

    [ValidateRange(1, 65535)]
    [int]$RemotePort = 5432
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    throw "The ssh command was not found. Install Windows OpenSSH Client first."
}

if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
    throw "SSH key not found: $IdentityFile. Run .\setup-postgres-ssh-key.ps1 first."
}

Write-Host "Starting PostgreSQL SSH tunnel..."
Write-Host "Local endpoint: 127.0.0.1:$LocalPort"
Write-Host "Remote endpoint: 127.0.0.1:$RemotePort"
Write-Host "Press Ctrl+C to close the tunnel."

& ssh `
    -N `
    -T `
    -i "$IdentityFile" `
    -L "127.0.0.1:${LocalPort}:127.0.0.1:${RemotePort}" `
    -o "BatchMode=yes" `
    -o "ExitOnForwardFailure=yes" `
    -o "ServerAliveInterval=60" `
    -o "ServerAliveCountMax=3" `
    "${ServerUser}@${ServerHost}"

if ($LASTEXITCODE -ne 0) {
    throw "SSH tunnel exited with code $LASTEXITCODE."
}
