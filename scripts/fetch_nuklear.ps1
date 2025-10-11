$Root = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent | Split-Path -Parent
$CoreTarget = Join-Path $Root "include/nuklear.h"
$GlfwTarget = Join-Path $Root "include/nuklear_glfw_gl2.h"
$CoreUrl = "https://raw.githubusercontent.com/Immediate-Mode-UI/Nuklear/master/src/nuklear.h"
$GlfwUrl = "https://raw.githubusercontent.com/Immediate-Mode-UI/Nuklear/master/demo/glfw_opengl2/nuklear_glfw_gl2.h"

if (-Not (Test-Path $CoreTarget)) {
    Write-Output "Downloading Nuklear core..."
    Invoke-WebRequest -Uri $CoreUrl -OutFile $CoreTarget
}
else {
    Write-Output "nuklear.h already present at $CoreTarget"
}

if (-Not (Test-Path $GlfwTarget)) {
    Write-Output "Downloading Nuklear GLFW helper..."
    Invoke-WebRequest -Uri $GlfwUrl -OutFile $GlfwTarget
}
else {
    Write-Output "nuklear_glfw_gl2.h already present at $GlfwTarget"
}

Write-Output "Nuklear headers ready in include/"
