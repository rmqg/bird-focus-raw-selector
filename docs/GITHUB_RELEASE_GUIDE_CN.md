# GitHub 发布与交付指南

---

## 1. 初始化（已建议）

在项目根目录：
```powershell
git init -b main
```

---

## 2. 建议首提交流程

```powershell
git add .
git commit -m "feat: bird raw selector cli + packaging docs"
```

---

## 3. 连接 GitHub 远程

```powershell
git remote add origin <你的仓库地址>
git push -u origin main
```

如果 `gh auth login --web` 临时失败，可重试一次；或改用 token 登录（不要把 token 发给聊天）：

```powershell
$env:GH_TOKEN = "<你的token>"
$env:GH_TOKEN | gh auth login --with-token
gh auth status
```

---

## 4. 生成源码 zip（可直接发人）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_source.ps1
```

输出在 `release/`。

---

## 5. 生成便携包 zip（小白双击）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_portable.ps1
```

输出在 `release/`，含：
- `bird-select.exe`
- 双击 `.bat` 启动器
- 朋友说明文档

---

## 6. 推荐发版策略

- `v0.x`：以实用迭代为主，允许参数变化。
- 每次发版都附：
  - `README`
  - 参数说明
  - 已知限制
  - 典型结果统计
