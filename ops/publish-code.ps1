<#
.SYNOPSIS
  Flip a competition's code repo from private to public (after judging).

.EXAMPLE
  ./ops/publish-code.ps1 -Repo "aiic-compfest18-app"
#>
param(
    [Parameter(Mandatory = $true)][string]$Repo,
    [string]$Org = "BudakGPT"
)

$ErrorActionPreference = "Stop"

Write-Host "Publishing $Org/$Repo (private -> public)..." -ForegroundColor Cyan
gh repo edit "$Org/$Repo" --visibility public --accept-visibility-change-consequences

Write-Host "✅ $Org/$Repo is now public: https://github.com/$Org/$Repo" -ForegroundColor Green
Write-Host "Tip: make sure the tracker's competition.yml links.code points here." -ForegroundColor Yellow
