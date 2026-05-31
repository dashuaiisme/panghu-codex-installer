param(
    [string]$ApiKey = "",
    [string]$BaseUrl = "https://aitokenapi.cc",
    [string]$Model = "gpt-5.5",
    [string]$WireApi = "responses",
    [switch]$SkipNetworkTest
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Mask-Secret {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "" }
    if ($Value.Length -le 12) { return "******" }
    return "$($Value.Substring(0, 6))...$($Value.Substring($Value.Length - 4))"
}

function Escape-TomlString {
    param([string]$Value)
    return ($Value -replace '\\', '\\' -replace '"', '\"')
}

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "胖虎AI Codex App 一键安装配置工具" -ForegroundColor Green
Write-Host "用途：自动写入 Codex API 配置、中文规则，并做基础连通性检查。"

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $secure = Read-Host "请输入胖虎中转 API Key" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $ApiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    throw "API Key 不能为空。"
}

$CodexHome = Join-Path $env:USERPROFILE ".codex"
$ConfigPath = Join-Path $CodexHome "config.toml"
$GlobalAgentsPath = Join-Path $CodexHome "AGENTS.md"
$WorkspaceRoot = Join-Path $env:USERPROFILE "Documents\胖虎AI-Codex工作区"
$WorkspaceAgentsPath = Join-Path $WorkspaceRoot "AGENTS.md"
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Step "检查 Codex"
$codexExists = Test-Command "codex"
if ($codexExists) {
    $version = (& codex --version) 2>$null
    Write-Host "已检测到 Codex：$version"
} else {
    Write-Warning "没有检测到 codex 命令。"
    Write-Host "如果你已经安装 Codex App，可以继续；如果还没安装，请先安装 Codex App 后重新运行本脚本。"
    Write-Host "本脚本仍会先写好配置。"
}

Write-Step "准备目录"
New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null
New-Item -ItemType Directory -Force -Path $WorkspaceRoot | Out-Null
Write-Host "Codex 配置目录：$CodexHome"
Write-Host "默认工作区：$WorkspaceRoot"

Write-Step "备份旧配置"
if (Test-Path -LiteralPath $ConfigPath) {
    $BackupPath = "$ConfigPath.bak-$Timestamp"
    Copy-Item -LiteralPath $ConfigPath -Destination $BackupPath -Force
    Write-Host "已备份：$BackupPath"
} else {
    Write-Host "未发现旧配置，将创建新配置。"
}

Write-Step "写入 Codex API 配置"
$safeBaseUrl = Escape-TomlString $BaseUrl.TrimEnd("/")
$safeModel = Escape-TomlString $Model
$safeWireApi = Escape-TomlString $WireApi
$safeApiKey = Escape-TomlString $ApiKey

$config = @"
model_provider = "panghuai"
model = "$safeModel"
model_reasoning_effort = "medium"
approval_policy = "never"
sandbox_mode = "workspace-write"

[model_providers.panghuai]
name = "胖虎AI中转"
base_url = "$safeBaseUrl"
wire_api = "$safeWireApi"
experimental_bearer_token = "$safeApiKey"
requires_openai_auth = true

[projects.'$($WorkspaceRoot.ToLowerInvariant() -replace '\\', '\\')']
trust_level = "trusted"

[desktop]
appearanceTheme = "dark"
conversationDetailMode = "STEPS_PROSE"
"@

Set-Content -LiteralPath $ConfigPath -Value $config -Encoding UTF8
Write-Host "已写入：$ConfigPath"
Write-Host "接口地址：$BaseUrl"
Write-Host "模型：$Model"
Write-Host "Key：$(Mask-Secret $ApiKey)"

Write-Step "写入中文优先规则"
$agents = @"
# 胖虎AI Codex 客户默认规则

- 默认使用简体中文回答。
- 用户没有明确要求英文时，不要切换到英文。
- 解释步骤时使用普通用户能看懂的说法，少用英文术语。
- 遇到 API、模型、网络、权限问题时，先给出可执行的修复步骤。
"@

Set-Content -LiteralPath $GlobalAgentsPath -Value $agents -Encoding UTF8
Set-Content -LiteralPath $WorkspaceAgentsPath -Value $agents -Encoding UTF8
Write-Host "已写入全局中文规则：$GlobalAgentsPath"
Write-Host "已写入工作区中文规则：$WorkspaceAgentsPath"

if (-not $SkipNetworkTest) {
    Write-Step "测试胖虎中转接口"
    $headers = @{ Authorization = "Bearer $ApiKey" }
    $modelsUrl = "$($BaseUrl.TrimEnd('/'))/v1/models"
    try {
        $response = Invoke-WebRequest -Uri $modelsUrl -Headers $headers -Method GET -TimeoutSec 20 -UseBasicParsing
        Write-Host "接口连通正常：HTTP $($response.StatusCode)"
    } catch {
        Write-Warning "接口连通测试失败：$($_.Exception.Message)"
        Write-Host "这通常是 Key 无效、余额不足、接口地址填错、网络被拦截，或中转未开放 /v1/models。"
        Write-Host "配置文件已经写好，仍可打开 Codex App 测试。"
    }
}

Write-Step "启动 Codex App"
if ($codexExists) {
    try {
        Start-Process -FilePath "codex" -ArgumentList @("app") -WorkingDirectory $WorkspaceRoot
        Write-Host "已尝试打开 Codex App。"
    } catch {
        Write-Warning "自动打开失败：$($_.Exception.Message)"
        Write-Host "请手动打开 Codex App。"
    }
} else {
    Write-Host "请手动打开 Codex App。"
}

Write-Host ""
Write-Host "完成。以后客户只需要在这个工作区使用 Codex：" -ForegroundColor Green
Write-Host $WorkspaceRoot
Write-Host ""
Write-Host "如需重跑，可使用："
Write-Host "powershell -ExecutionPolicy Bypass -File .\panghu-codex-oneclick-install.ps1 -ApiKey `"你的Key`""

