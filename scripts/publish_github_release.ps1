param(
    [string]$Repo = "",
    [string]$Tag = "",
    [string]$Title = "",
    [string]$Notes = "",
    [switch]$Draft = $false,
    [switch]$Prerelease = $false
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $repoRoot "release"
$maxAssetBytes = [int64](2GB)

function Get-VersionFromPyProject {
    param([string]$Path)
    $line = Get-Content -Path $Path | Where-Object { $_ -match '^\s*version\s*=\s*".+"$' } | Select-Object -First 1
    if (-not $line) {
        throw "Cannot find version in pyproject.toml"
    }
    if ($line -match '^\s*version\s*=\s*"(.+)"$') {
        return $Matches[1]
    }
    throw "Invalid version line in pyproject.toml: $line"
}

function Get-LatestFile {
    param(
        [string]$Directory,
        [string]$Pattern
    )
    $file = Get-ChildItem -Path $Directory -File -Filter $Pattern -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    return $file
}

function Ensure-AssetSize {
    param([System.IO.FileInfo]$Asset)
    if ($Asset.Length -ge $maxAssetBytes) {
        throw "Asset too large for GitHub Release (>=2GB): $($Asset.FullName)"
    }
}

Push-Location $repoRoot
try {
    gh --version | Out-Null
    gh auth status | Out-Null

    if ([string]::IsNullOrWhiteSpace($Tag)) {
        $version = Get-VersionFromPyProject -Path (Join-Path $repoRoot "pyproject.toml")
        $Tag = "v$version"
    }
    if ([string]::IsNullOrWhiteSpace($Title)) {
        $Title = $Tag
    }
    if ([string]::IsNullOrWhiteSpace($Notes)) {
        $Notes = "Bird Focus RAW Selector $Tag"
    }

    if ([string]::IsNullOrWhiteSpace($Repo)) {
        try {
            $Repo = gh repo view --json nameWithOwner --jq .nameWithOwner
        } catch {
            throw "Repo is empty and cannot infer from current git remote. Use -Repo <owner/repo>."
        }
    }

    if (-not (Test-Path $releaseDir)) {
        throw "Release directory not found: $releaseDir"
    }

    $sourceZip = Get-LatestFile -Directory $releaseDir -Pattern "bird-select-source-*.zip"
    if (-not $sourceZip) {
        throw "Source package not found in release/. Run scripts\\package_source.ps1 first."
    }

    $portableZip = Get-LatestFile -Directory $releaseDir -Pattern "bird-select-portable-win64_cpu_*.zip"
    if (-not $portableZip) {
        $portableZip = Get-LatestFile -Directory $releaseDir -Pattern "bird-select-portable-win64_*.zip"
    }
    if (-not $portableZip) {
        throw "Portable package not found in release/. Run scripts\\build_portable_cpu.ps1 first."
    }
    $gpuPortableZip = Get-LatestFile -Directory $releaseDir -Pattern "bird-select-portable-win64_gpu-*.zip"

    Ensure-AssetSize -Asset $sourceZip
    Ensure-AssetSize -Asset $portableZip
    if ($gpuPortableZip) {
        if ($gpuPortableZip.Length -ge $maxAssetBytes) {
            Write-Host "GPU portable package exceeds GitHub 2GB asset limit and will be skipped: $($gpuPortableZip.FullName)" -ForegroundColor Yellow
            $gpuPortableZip = $null
        } else {
            Ensure-AssetSize -Asset $gpuPortableZip
        }
    }

    git diff --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Working tree is dirty. Commit your changes before publishing."
    }
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Index is dirty. Commit your changes before publishing."
    }

    git push

    $tagExists = (git tag --list $Tag)
    if (-not $tagExists) {
        git tag $Tag
    }
    git push origin $Tag

    $releaseExists = $false
    try {
        gh release view $Tag --repo $Repo | Out-Null
        $releaseExists = $true
    } catch {
        $releaseExists = $false
    }

    if ($releaseExists) {
        $uploadAssets = @($sourceZip.FullName, $portableZip.FullName)
        if ($gpuPortableZip) {
            $uploadAssets += $gpuPortableZip.FullName
        }
        gh release upload $Tag @uploadAssets --repo $Repo --clobber
    } else {
        $createArgs = @(
            "release", "create", $Tag,
            $sourceZip.FullName,
            $portableZip.FullName,
            "--repo", $Repo,
            "--title", $Title,
            "--notes", $Notes
        )
        if ($gpuPortableZip) {
            $createArgs += $gpuPortableZip.FullName
        }
        if ($Draft) { $createArgs += "--draft" }
        if ($Prerelease) { $createArgs += "--prerelease" }
        gh @createArgs
    }

    $url = gh release view $Tag --repo $Repo --json url --jq .url
    Write-Host "Release published: $url" -ForegroundColor Green
} finally {
    Pop-Location
}
