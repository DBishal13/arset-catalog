<#
.SYNOPSIS
  Runs the tracker and opens a pull request with whatever it found.

.DESCRIPTION
  Used by the Windows scheduled task (scripts/install-task.ps1), because
  Earthdata returns 403 to GitHub-hosted runners. Starts from an up-to-date,
  clean main; if the tracker changed anything under data/ or inbox/videos.yaml,
  commits it to a new tracker/<date> branch, pushes it and opens a PR whose
  description is inbox/REPORT.md. Otherwise it discards the run's bookkeeping
  changes and exits. Log: build/logs/track-task.log (not committed).

.PARAMETER Python
  Python executable to use (the scheduled task passes a full path).

.PARAMETER DryRun
  Only report what the tracker would find; change nothing.
#>
param(
    [string]$Python = "python",
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$logDir = Join-Path $repo "build\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir "track-task.log"

function Log([string]$message) {
    $line = "{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $message
    Add-Content -Path $log -Value $line -Encoding utf8
    Write-Output $line
}

if ($DryRun) {
    & $Python -m arset track --dry-run
    exit $LASTEXITCODE
}

if (git status --porcelain) {
    Log "skipped: the working tree has uncommitted changes (commit or stash them first)"
    exit 0
}
git checkout -q main
git pull -q --ff-only
if ($LASTEXITCODE -ne 0) { Log "failed: could not fast-forward main"; exit 1 }

Log "running tracker"
& $Python -m arset track *>> $log
$trackExit = $LASTEXITCODE

$found = git status --porcelain -- data inbox/videos.yaml
if (-not $found) {
    git checkout -q -- state inbox
    if ($trackExit -ne 0) { Log "failed: tracker reported only errors (see inbox/REPORT.md in the log above)"; exit 1 }
    Log "nothing new"
    exit 0
}

& $Python -m arset validate *>> $log
$branch = "tracker/{0:yyyy-MM-dd-HHmm}" -f (Get-Date)
git checkout -q -b $branch
git add data inbox state
git commit -q -m "Tracker: new ARSET content ($(Get-Date -Format yyyy-MM-dd))"
git push -q -u origin $branch
if ($LASTEXITCODE -ne 0) { Log "failed: push of $branch"; git checkout -q main; exit 1 }
$pr = gh pr create --base main --head $branch --title "Tracker: new ARSET content ($(Get-Date -Format yyyy-MM-dd))" --body-file inbox/REPORT.md
Log "opened $pr"
git checkout -q main
exit 0
