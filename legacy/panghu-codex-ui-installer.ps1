param(
    [switch]$SelfTest
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

function Escape-TomlString {
    param([string]$Value)
    return ($Value -replace '\\', '\\' -replace '"', '\"')
}

function Mask-Secret {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "" }
    if ($Value.Length -le 12) { return "******" }
    return "$($Value.Substring(0, 6))...$($Value.Substring($Value.Length - 4))"
}

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Add-Log {
    param([string]$Message)
    $time = Get-Date -Format "HH:mm:ss"
    $logBox.AppendText("[$time] $Message`r`n")
    $logBox.SelectionStart = $logBox.Text.Length
    $logBox.ScrollToCaret()
    [System.Windows.Forms.Application]::DoEvents()
}

function Install-PanghuCodex {
    param(
        [string]$ApiKey,
        [string]$BaseUrl,
        [string]$Model,
        [bool]$SkipNetworkTest,
        [bool]$OpenCodexApp
    )

    if ([string]::IsNullOrWhiteSpace($ApiKey)) {
        throw "请先输入胖虎AI API Key。"
    }

    if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
        throw "接口地址不能为空。"
    }

    if ([string]::IsNullOrWhiteSpace($Model)) {
        throw "模型名称不能为空。"
    }

    $CodexHome = Join-Path $env:USERPROFILE ".codex"
    $ConfigPath = Join-Path $CodexHome "config.toml"
    $GlobalAgentsPath = Join-Path $CodexHome "AGENTS.md"
    $WorkspaceRoot = Join-Path $env:USERPROFILE "Documents\胖虎AI-Codex工作区"
    $WorkspaceAgentsPath = Join-Path $WorkspaceRoot "AGENTS.md"
    $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

    Add-Log "开始配置胖虎AI Codex。"

    $codexExists = Test-Command "codex"
    if ($codexExists) {
        $version = (& codex --version) 2>$null
        Add-Log "已检测到 Codex：$version"
    } else {
        Add-Log "未检测到 codex 命令。配置仍会写入，稍后安装 Codex App 后可继续使用。"
    }

    New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null
    New-Item -ItemType Directory -Force -Path $WorkspaceRoot | Out-Null
    Add-Log "配置目录：$CodexHome"
    Add-Log "默认工作区：$WorkspaceRoot"

    if (Test-Path -LiteralPath $ConfigPath) {
        $BackupPath = "$ConfigPath.bak-$Timestamp"
        Copy-Item -LiteralPath $ConfigPath -Destination $BackupPath -Force
        Add-Log "已备份旧配置：$BackupPath"
    } else {
        Add-Log "未发现旧配置，将创建新配置。"
    }

    $safeBaseUrl = Escape-TomlString $BaseUrl.TrimEnd("/")
    $safeModel = Escape-TomlString $Model
    $safeApiKey = Escape-TomlString $ApiKey
    $safeWorkspacePath = $WorkspaceRoot.ToLowerInvariant() -replace '\\', '\\'

    $config = @"
model_provider = "panghuai"
model = "$safeModel"
model_reasoning_effort = "medium"
approval_policy = "never"
sandbox_mode = "workspace-write"

[model_providers.panghuai]
name = "胖虎AI中转"
base_url = "$safeBaseUrl"
wire_api = "responses"
experimental_bearer_token = "$safeApiKey"
requires_openai_auth = true

[projects.'$safeWorkspacePath']
trust_level = "trusted"

[desktop]
appearanceTheme = "dark"
conversationDetailMode = "STEPS_PROSE"
"@

    Set-Content -LiteralPath $ConfigPath -Value $config -Encoding UTF8
    Add-Log "已写入 Codex 配置：$ConfigPath"
    Add-Log "接口地址：$BaseUrl"
    Add-Log "模型：$Model"
    Add-Log "Key：$(Mask-Secret $ApiKey)"

    $agents = @"
# 胖虎AI Codex 客户默认规则

- 默认使用简体中文回答。
- 用户没有明确要求英文时，不要切换到英文。
- 解释步骤时使用普通用户能看懂的说法，少用英文术语。
- 遇到 API、模型、网络、权限问题时，先给出可执行的修复步骤。
"@

    Set-Content -LiteralPath $GlobalAgentsPath -Value $agents -Encoding UTF8
    Set-Content -LiteralPath $WorkspaceAgentsPath -Value $agents -Encoding UTF8
    Add-Log "已写入中文规则。"

    if (-not $SkipNetworkTest) {
        Add-Log "正在测试胖虎AI接口..."
        $headers = @{ Authorization = "Bearer $ApiKey" }
        $modelsUrl = "$($BaseUrl.TrimEnd('/'))/v1/models"
        try {
            $response = Invoke-WebRequest -Uri $modelsUrl -Headers $headers -Method GET -TimeoutSec 20 -UseBasicParsing
            Add-Log "接口连通正常：HTTP $($response.StatusCode)"
        } catch {
            Add-Log "接口连通测试失败：$($_.Exception.Message)"
            Add-Log "常见原因：Key 填错、余额不足、网络不通、后台账号池未分配。"
        }
    } else {
        Add-Log "已跳过接口测试。"
    }

    if ($OpenCodexApp) {
        if ($codexExists) {
            try {
                Start-Process -FilePath "codex" -ArgumentList @("app") -WorkingDirectory $WorkspaceRoot
                Add-Log "已尝试打开 Codex App。"
            } catch {
                Add-Log "自动打开 Codex App 失败：$($_.Exception.Message)"
            }
        } else {
            Add-Log "未检测到 codex 命令，请手动打开 Codex App。"
        }
    }

    Add-Log "配置完成。以后请使用工作区：$WorkspaceRoot"
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "胖虎AI Codex 一键配置助手"
$form.StartPosition = "CenterScreen"
$form.Size = New-Object System.Drawing.Size(760, 620)
$form.MinimumSize = New-Object System.Drawing.Size(720, 560)
$form.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 10)
$form.BackColor = [System.Drawing.Color]::FromArgb(248, 250, 252)

$title = New-Object System.Windows.Forms.Label
$title.Text = "胖虎AI Codex 一键配置助手"
$title.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 18, [System.Drawing.FontStyle]::Bold)
$title.ForeColor = [System.Drawing.Color]::FromArgb(15, 23, 42)
$title.AutoSize = $true
$title.Location = New-Object System.Drawing.Point(24, 22)
$form.Controls.Add($title)

$subtitle = New-Object System.Windows.Forms.Label
$subtitle.Text = "输入胖虎AI API Key，自动配置 Codex 中转、默认工作区和中文回答规则。"
$subtitle.ForeColor = [System.Drawing.Color]::FromArgb(71, 85, 105)
$subtitle.AutoSize = $true
$subtitle.Location = New-Object System.Drawing.Point(28, 64)
$form.Controls.Add($subtitle)

$keyLabel = New-Object System.Windows.Forms.Label
$keyLabel.Text = "胖虎AI API Key"
$keyLabel.AutoSize = $true
$keyLabel.Location = New-Object System.Drawing.Point(30, 108)
$form.Controls.Add($keyLabel)

$keyBox = New-Object System.Windows.Forms.TextBox
$keyBox.Location = New-Object System.Drawing.Point(30, 134)
$keyBox.Size = New-Object System.Drawing.Size(640, 30)
$keyBox.PasswordChar = '*'
$form.Controls.Add($keyBox)

$showKey = New-Object System.Windows.Forms.CheckBox
$showKey.Text = "显示"
$showKey.AutoSize = $true
$showKey.Location = New-Object System.Drawing.Point(680, 136)
$showKey.Add_CheckedChanged({
    if ($showKey.Checked) {
        $keyBox.PasswordChar = [char]0
    } else {
        $keyBox.PasswordChar = '*'
    }
})
$form.Controls.Add($showKey)

$baseLabel = New-Object System.Windows.Forms.Label
$baseLabel.Text = "接口地址"
$baseLabel.AutoSize = $true
$baseLabel.Location = New-Object System.Drawing.Point(30, 180)
$form.Controls.Add($baseLabel)

$baseBox = New-Object System.Windows.Forms.TextBox
$baseBox.Location = New-Object System.Drawing.Point(30, 206)
$baseBox.Size = New-Object System.Drawing.Size(420, 30)
$baseBox.Text = "https://aitokenapi.cc"
$form.Controls.Add($baseBox)

$modelLabel = New-Object System.Windows.Forms.Label
$modelLabel.Text = "模型"
$modelLabel.AutoSize = $true
$modelLabel.Location = New-Object System.Drawing.Point(470, 180)
$form.Controls.Add($modelLabel)

$modelBox = New-Object System.Windows.Forms.ComboBox
$modelBox.Location = New-Object System.Drawing.Point(470, 206)
$modelBox.Size = New-Object System.Drawing.Size(240, 30)
$modelBox.DropDownStyle = "DropDown"
[void]$modelBox.Items.Add("gpt-5.5")
[void]$modelBox.Items.Add("gpt-5.4")
[void]$modelBox.Items.Add("gpt-4.1")
$modelBox.Text = "gpt-5.5"
$form.Controls.Add($modelBox)

$skipTest = New-Object System.Windows.Forms.CheckBox
$skipTest.Text = "跳过接口测试"
$skipTest.AutoSize = $true
$skipTest.Location = New-Object System.Drawing.Point(30, 254)
$form.Controls.Add($skipTest)

$openApp = New-Object System.Windows.Forms.CheckBox
$openApp.Text = "配置完成后打开 Codex App"
$openApp.AutoSize = $true
$openApp.Checked = $true
$openApp.Location = New-Object System.Drawing.Point(170, 254)
$form.Controls.Add($openApp)

$installButton = New-Object System.Windows.Forms.Button
$installButton.Text = "一键配置"
$installButton.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 11, [System.Drawing.FontStyle]::Bold)
$installButton.BackColor = [System.Drawing.Color]::FromArgb(37, 99, 235)
$installButton.ForeColor = [System.Drawing.Color]::White
$installButton.FlatStyle = "Flat"
$installButton.Location = New-Object System.Drawing.Point(30, 292)
$installButton.Size = New-Object System.Drawing.Size(140, 42)
$form.Controls.Add($installButton)

$openWorkspaceButton = New-Object System.Windows.Forms.Button
$openWorkspaceButton.Text = "打开工作区"
$openWorkspaceButton.Location = New-Object System.Drawing.Point(186, 292)
$openWorkspaceButton.Size = New-Object System.Drawing.Size(120, 42)
$form.Controls.Add($openWorkspaceButton)

$openConfigButton = New-Object System.Windows.Forms.Button
$openConfigButton.Text = "打开配置目录"
$openConfigButton.Location = New-Object System.Drawing.Point(322, 292)
$openConfigButton.Size = New-Object System.Drawing.Size(130, 42)
$form.Controls.Add($openConfigButton)

$helpLabel = New-Object System.Windows.Forms.Label
$helpLabel.Text = "提示：如果 Codex App 菜单仍是英文，这是官方界面限制；本工具负责中转配置和中文回答规则。"
$helpLabel.ForeColor = [System.Drawing.Color]::FromArgb(100, 116, 139)
$helpLabel.AutoSize = $true
$helpLabel.Location = New-Object System.Drawing.Point(30, 350)
$form.Controls.Add($helpLabel)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Location = New-Object System.Drawing.Point(30, 382)
$logBox.Size = New-Object System.Drawing.Size(680, 150)
$logBox.Multiline = $true
$logBox.ScrollBars = "Vertical"
$logBox.ReadOnly = $true
$logBox.BackColor = [System.Drawing.Color]::White
$form.Controls.Add($logBox)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = "状态：等待配置"
$statusLabel.AutoSize = $true
$statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(71, 85, 105)
$statusLabel.Location = New-Object System.Drawing.Point(30, 548)
$form.Controls.Add($statusLabel)

$installButton.Add_Click({
    $installButton.Enabled = $false
    $statusLabel.Text = "状态：正在配置..."
    try {
        Install-PanghuCodex -ApiKey $keyBox.Text.Trim() -BaseUrl $baseBox.Text.Trim() -Model $modelBox.Text.Trim() -SkipNetworkTest $skipTest.Checked -OpenCodexApp $openApp.Checked
        $statusLabel.Text = "状态：配置完成"
        [System.Windows.Forms.MessageBox]::Show('配置完成。以后请使用：文档\胖虎AI-Codex工作区', '胖虎AI Codex', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
    } catch {
        $statusLabel.Text = "状态：配置失败"
        Add-Log "配置失败：$($_.Exception.Message)"
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, '配置失败', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
    } finally {
        $installButton.Enabled = $true
    }
})

$openWorkspaceButton.Add_Click({
    $WorkspaceRoot = Join-Path $env:USERPROFILE "Documents\胖虎AI-Codex工作区"
    New-Item -ItemType Directory -Force -Path $WorkspaceRoot | Out-Null
    Start-Process explorer.exe $WorkspaceRoot
})

$openConfigButton.Add_Click({
    $CodexHome = Join-Path $env:USERPROFILE ".codex"
    New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null
    Start-Process explorer.exe $CodexHome
})

if ($SelfTest) {
    Write-Output "UI self-test OK"
    exit 0
}

Add-Log "请粘贴胖虎AI API Key，然后点击“一键配置”。"
Add-Log "默认接口：https://aitokenapi.cc"
Add-Log "默认模型：gpt-5.5"

[void]$form.ShowDialog()

