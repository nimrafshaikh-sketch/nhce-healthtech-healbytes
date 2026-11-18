<#
.SYNOPSIS
    Automated PostgreSQL backup script for HealBytes (Windows / Docker).
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\backup_db.ps1
    powershell -ExecutionPolicy Bypass -File .\scripts\backup_db.ps1 -RetentionDays 30
#>
param(
    [string]$BackupDir = ".\backups",
    [int]$RetentionDays = 14,
    [string]$ContainerName = "healbytes_db",
    [string]$DbName = "healbytes",
    [string]$DbUser = "healbytes"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$outFile = Join-Path (Resolve-Path $BackupDir) "${DbName}_${timestamp}.dump"

Write-Output "[backup_db] Backing up '${DbName}' from container '${ContainerName}' -> ${outFile}"

# Dump inside container to temp path then copy cleanly to preserve binary archive integrity on Windows
$containerTmp = "/tmp/${DbName}_${timestamp}.dump"
docker exec $ContainerName pg_dump -U $DbUser -d $DbName --format=custom --compress=9 -f $containerTmp
if ($LASTEXITCODE -ne 0) {
    throw "pg_dump failed with exit code $LASTEXITCODE"
}

docker exec $ContainerName pg_restore --list $containerTmp | Out-Null
if ($LASTEXITCODE -ne 0) {
    docker exec $ContainerName rm -f $containerTmp | Out-Null
    throw "pg_restore integrity verification failed"
}

docker cp "${ContainerName}:${containerTmp}" $outFile
docker exec $ContainerName rm -f $containerTmp | Out-Null

$fileInfo = Get-Item $outFile
if ($fileInfo.Length -le 0) {
    Remove-Item -Force $outFile
    throw "Backup archive is empty: $outFile"
}

Write-Output "[backup_db] Verified backup archive ($($fileInfo.Length) bytes): $outFile"

# Prune old backups
$cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -Path $BackupDir -Filter "${DbName}_*.dump" | Where-Object { $_.LastWriteTime -lt $cutoff } | Remove-Item -Force
Write-Output "[backup_db] Retention cleanup complete (kept last ${RetentionDays} days)."

