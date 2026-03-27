# GitHub 发布与交付指南

## 1) 本地提交

```powershell
cd E:\bird_select
git add .
git commit -m "chore: improve scan exclusion, packaging, and release workflow"
```

## 2) 认证（不要在聊天里发 token）

优先网页授权：
```powershell
gh auth login --hostname github.com --web --git-protocol https
gh auth status
```

如果网页授权失败，可用 token（本机执行）：
```powershell
$env:GH_TOKEN = "<your-token>"
$env:GH_TOKEN | gh auth login --with-token
gh auth status
```

## 3) 连接远程并推送

```powershell
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

## 4) 生成交付包

源码包：
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_source.ps1
```

CPU 便携包（跨机器更稳）：
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_portable_cpu.ps1
```

统一入口（默认源码 + CPU）：
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_all_packages.ps1
```

## 5) 发布前检查

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_release.ps1
```

## 6) 一键发布 GitHub Release（推荐）

仓库已有脚本：`scripts/publish_github_release.ps1`

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_github_release.ps1 `
  -Repo "<user>/<repo>" `
  -Tag "v0.3.3" `
  -Title "v0.3.3" `
  -Notes "Bird Focus RAW Selector v0.3.3"
```

脚本会上传：
- 最新 `bird-select-source-*.zip`
- 最新 `bird-select-portable-win64_cpu_*.zip`（如果没有 CPU 包，会回退匹配 `bird-select-portable-win64_*.zip`）

## 7) 手动创建 Release（可选）

```powershell
gh release create v0.3.3 --title "v0.3.3" --notes "Bird Focus RAW Selector v0.3.3"
gh release upload v0.3.3 .\release\bird-select-source-*.zip
```

说明：
- GitHub Release 单文件上限约 2GB；优先上传 CPU 便携包。
- 若便携包超过 2GB，请改用更小配置重打包，或用网盘分享大文件。
