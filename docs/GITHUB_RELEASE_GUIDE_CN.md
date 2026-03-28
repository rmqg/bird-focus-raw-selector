# GitHub 发布指南（v1.2 适用）

## 1) 提交代码

```powershell
cd E:\bird_select
git add .
git commit -m "release: prepare v1.2.0 / 发布: 准备 v1.2.0"
```

## 2) GitHub 认证

优先网页授权：

```powershell
gh auth login --hostname github.com --web --git-protocol https
gh auth status
```

若网页授权失败，再使用 token（只在本机终端输入，不要发到聊天）：

```powershell
$env:GH_TOKEN = "<your-token>"
$env:GH_TOKEN | gh auth login --with-token
gh auth status
```

## 3) 生成发布资产

源码包：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_source.ps1
```

CPU 便携包（已内置 Python）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_portable_cpu.ps1
```

GPU 便携包（GPU 专用，已内置 Python，模型可自动下载）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_portable_gpu_online.ps1
```

一键构建（默认：源码 + CPU + GPU-online）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_all_packages.ps1
```

## 4) 发布前检查

```powershell
git status
```

要求：
- 工作区干净（没有未提交改动）。
- `LICENSE` 为 GPLv3 正文，且 `README`/`pyproject.toml` 的许可证声明一致。
- `release` 目录中存在最新 3 类文件：
- `bird-select-source-*.zip`
- `bird-select-portable-win64_cpu_*.zip`
- `bird-select-portable-win64_gpu-online_*.zip`

## 5) 自动发布 Release（推荐）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_github_release.ps1 `
  -Repo "rmqg/bird-focus-raw-selector" `
  -Tag "v1.2.0" `
  -Title "v1.2.0" `
  -Notes "Bird Focus RAW Selector v1.2.0"
```

脚本会：
- 推送当前分支与 tag。
- 创建或更新对应 Release。
- 上传源码包 + CPU 包 + GPU-online 包（若文件小于 GitHub 2GB 限制）。

## 6) 手动发布（可选）

```powershell
gh release create v1.2.0 --title "v1.2.0" --notes "Bird Focus RAW Selector v1.2.0"
gh release upload v1.2.0 .\release\bird-select-source-*.zip --clobber
gh release upload v1.2.0 .\release\bird-select-portable-win64_cpu_*.zip --clobber
gh release upload v1.2.0 .\release\bird-select-portable-win64_gpu-online_*.zip --clobber
```

## 7) 发布后自检

- 在另一台机器或全新目录中解压 CPU 包并实测。
- 在有 NVIDIA 环境的机器解压 GPU 包并实测（首次联网安装依赖 + 模型下载）。
- 确认 `dry-run` 与 `copy` 两个入口都可用，且日志正常输出。
