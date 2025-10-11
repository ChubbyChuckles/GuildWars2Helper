Param(
    [string]$Version = "3.4"
)

$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$depsDir = Join-Path $scriptDir "deps"
$glfwDir = Join-Path $depsDir "glfw"
$archive = "glfw-$Version.zip"
$url = "https://github.com/glfw/glfw/releases/download/$Version/$archive"

if (Test-Path $glfwDir) {
    Write-Output "GLFW already downloaded at $glfwDir"
    exit 0
}

New-Item -ItemType Directory -Force -Path $depsDir | Out-Null
Set-Location $depsDir

if (-Not (Test-Path $archive)) {
    Write-Output "Downloading GLFW $Version..."
    Invoke-WebRequest -Uri $url -OutFile $archive
}

Write-Output "Extracting GLFW..."
Expand-Archive -Path $archive -DestinationPath $depsDir -Force
Rename-Item -Path (Join-Path $depsDir "glfw-$Version") -NewName "glfw"

Write-Output "GLFW ready in $glfwDir"
