<#
.SYNOPSIS
  Spin up a new competition: a public tracker repo (+ optional private code repo).

.EXAMPLE
  ./ops/new-competition.ps1 -Name "AI Innovation Challenge" -Repo "aiic-compfest18" -Organizer "COMPFEST 18" -WithCode

.NOTES
  Requires gh (authenticated). The tracker is created from the
  BudakGPT/competition-template and tagged with the `competition` topic so the
  org dashboard picks it up automatically.
#>
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Repo,        # repo slug, e.g. aiic-compfest18
    [string]$Organizer = "",
    [switch]$WithCode,                                   # also create a private <Repo>-app code repo
    [string]$Org = "BudakGPT"
)

$ErrorActionPreference = "Stop"

Write-Host "Creating tracker $Org/$Repo from template..." -ForegroundColor Cyan
gh repo create "$Org/$Repo" `
    --template "$Org/competition-template" `
    --public `
    --description "$Name tracker"

# topic = discovery key for the org dashboard
gh repo edit "$Org/$Repo" --add-topic competition

$codeUrl = ""
if ($WithCode) {
    $codeRepo = "$Repo-app"
    Write-Host "Creating private code repo $Org/$codeRepo..." -ForegroundColor Cyan
    gh repo create "$Org/$codeRepo" --private --description "$Name — project code"
    $codeUrl = "https://github.com/$Org/$codeRepo"
}

Write-Host ""
Write-Host "✅ Tracker:  https://github.com/$Org/$Repo" -ForegroundColor Green
if ($codeUrl) { Write-Host "✅ Code:     $codeUrl (private)" -ForegroundColor Green }
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Clone:   gh repo clone $Org/$Repo"
Write-Host "  2. Edit competition.yml (name, organizer, dates, deliverables, links)."
if ($codeUrl) { Write-Host "     -> set links.code: $codeUrl" }
Write-Host "  3. Push. The Action renders the dashboard automatically."
Write-Host "  4. After judging, publish the code:  ./ops/publish-code.ps1 -Repo $Repo-app"
