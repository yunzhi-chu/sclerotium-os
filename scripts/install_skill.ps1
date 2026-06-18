# Sclerotium Trinity — 外部技能按需加载
#
# 用法：
#   .\scripts\install_skill.ps1 -Name "openclaw-master-skills"
#   .\scripts\install_skill.ps1 -Name "all"                          # 全部
#   .\scripts\install_skill.ps1 -Name "openclaw-master-skills,awesome-claude-code"  # 多个

param(
    [Parameter(Mandatory = $true)]
    [string]$Name
)

$ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$MANIFEST = "$ROOT\fungal-cortex\skills\skill_manifest.json"
$SKILLS_DIR = "$ROOT\fungal-cortex\skills"

if (-not (Test-Path $MANIFEST)) {
    Write-Error "未找到技能清单: $MANIFEST"
    exit 1
}

$manifest = Get-Content $MANIFEST -Raw | ConvertFrom-Json
$skills = $manifest.skills
$names = if ($Name -eq "all") { $skills.PSObject.Properties.Name } else { $Name -split "," }

foreach ($name in $names) {
    $name = $name.Trim()
    if (-not $skills.$name) {
        Write-Warning "未知技能: $name"
        continue
    }

    $dir = $skills.$name.dir
    $target = "$SKILLS_DIR\$dir"

    if (Test-Path $target) {
        Write-Host "[✓] $name 已存在" -ForegroundColor Green
        continue
    }

    Write-Host "[↓] 安装 $name ($($skills.$name.description))..." -ForegroundColor Cyan

    # GitHub 搜索 + clone 策略：尝试根据技能名从 openclaw 等来源查找
    $search_name = $name -replace "-main$", ""
    Write-Host "    尝试从 GitHub 获取 $search_name ..."

    # 先检查是否配置为 submodule
    $gitmodules = "$ROOT\.gitmodules"
    if (Test-Path $gitmodules) {
        $sub = git config -f $gitmodules --get-regexp "submodule.*$dir.*url" 2>$null
        if ($sub) {
            $url = ($sub -split " ")[-1]
            Write-Host "    发现 submodule: $url"
            git -C $ROOT submodule update --init --depth 1 "fungal-cortex/skills/$dir" 2>$null
            if ($?) { Write-Host "[✓] $name submodule 安装完成" -ForegroundColor Green; continue }
        }
    }

    # Fallback: 尝试 gh repo clone
    try {
        $repo = gh search repos "$search_name" --limit 1 --json nameWithOwner --jq '.[0].nameWithOwner' 2>$null
        if ($repo) {
            Write-Host "    找到仓库: $repo"
            git clone --depth 1 "https://github.com/$repo.git" $target 2>$null
            if ($?) { Write-Host "[✓] $name 安装完成 (from $repo)" -ForegroundColor Green; continue }
        }
    } catch {
        # github search failed, try alternative
    }

    # 最终 fallback
    Write-Warning "[!] $name 未找到。请手动提供仓库 URL。"
    Write-Host "    git clone --depth 1 <url> $target"
}

Write-Host ""
Write-Host "完成。在 Sclerotium 中使用时，SkillLoader 会自动扫描 $SKILLS_DIR"
