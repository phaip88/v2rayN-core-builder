# v2rayN Extended Core Builder

把更多独立 CLI 内核（GOST / Chisel / OpenSSH / sshpass / EasyTier / Cloudflared）集成进官方
[v2rayN](https://github.com/2dust/v2rayN) 的 `ServiceLib` 调度系统，并产出：

1. **`ServiceLib-extended-<version>.zip`** —— 补丁后的 `ServiceLib.dll`，直接丢进已安装的 v2rayN 即可。
2. **`v2rayN-Extended-win64-SelfContained-<version>.zip`** —— 内置 .NET 8 运行时的完整 Windows 客户端（开箱双击即用）。

> 思路来自 [lukuichina/v2rayN](https://github.com/lukuichina/v2rayN) 与
> [lukuichina/youtube/2025/795](https://github.com/lukuichina/youtube/tree/main/2025/795)。
> 与基于正则“自动补丁”的方案不同，本项目**直接维护一份真实的源码统一 diff 补丁**，
> 由 `git apply`（失败回退 `patch --fuzz`）注入，稳定可复现。

---

## 已集成内核

| 内核 | CoreType | 用途 |
|------|----------|------|
| GOST | `gost` (31) | 多协议加密隧道 / 链式代理 |
| Chisel | `chisel` (32) | HTTP/WS 多路复用 TCP/UDP 隧道 |
| OpenSSH | `ssh` (33) | 原生 SSH 动态 SOCKS5 |
| sshpass | `sshpass` (34) | 带密码的 SSH 动态 SOCKS5 |
| EasyTier | `easytier` (35) | P2P 异地虚拟组网 |
| Cloudflared | `cloudflared` (36) | Cloudflare Tunnel 内网穿透 |

新增内核只需编辑 `patches/v2rayN-extended-cores.patch`（在四个源文件里各加一段），无需改脚本。

---

## 方案原理（为什么这样才有效）

v2rayN 的“自定义配置服务器”通过 `CoreInfoManager`（内核清单）、`ECoreType`（枚举）、
`Global.CoreUrls`（下载源）和 `CoreManager`（进程启动/参数拼接）这 4 个文件协同工作。
要新增内核，必须**真实修改这 4 个 C# 源文件并重新编译 `ServiceLib.dll`** —— 纯声明式配置无法生效。
本项目的补丁对官方 7.24.4 的这 4 个文件做了最小改动：

- `ServiceLib/Enums/ECoreType.cs`：追加 6 个枚举值。
- `ServiceLib/Global.cs`：`CoreUrls` 追加 6 条仓库映射。
- `ServiceLib/Manager/CoreInfoManager.cs`：`_coreInfo` 集合追加 6 个 `CoreInfo`。
- `ServiceLib/Manager/CoreManager.cs`：对这 6 类内核，把配置文件**内容**作为命令行参数传入
  （而非路径），因为它们接收的就是 CLI 参数文本。

---

## 使用方式

### 方式一：GitHub Actions 在线构建（推荐）

1. Fork 本仓库。
2. `Actions` → `Build v2rayN with Extended Cores` → `Run workflow`。
   - **version**：填 `latest` 或具体版本如 `7.24.4`。
   - **create_release**：`true` 会把产物发布为 Release。
3. 在 Artifacts / Release 下载两个 zip。

> 补丁基于 7.24.4。构建较新版本时若 `git apply` 失败，会自动用 `patch --fuzz=3` 模糊应用；
> 若仍失败（v2rayN 大改了这 4 个文件），需手动 rebase 补丁（见下）。

### 方式二：本地命令行构建

```bash
# 需要 .NET 8 SDK；完整客户端构建需要 Windows（v2rayN 主程序是 WinForms）

# 仅 ServiceLib.dll（可在 Linux/macOS 构建）
./scripts/build.sh latest --no-client

# ServiceLib.dll + 完整客户端（需 Windows）
./scripts/build.sh 7.24.4
```

产物在 `dist/`：`ServiceLib-extended-<version>.zip`、`v2rayN-Extended-win64-SelfContained-<version>.zip`。

---

## 客户端使用步骤

1. 解压 `v2rayN-Extended-*.zip` 得到完整客户端；或把 `ServiceLib-extended-*.zip` 里的
   `ServiceLib.dll` 覆盖到已装 v2rayN 的目录。
2. 把各内核可执行文件按 `cores.json` 的 `binNames` 放到 v2rayN 的 `bin/<coreType>/` 目录
   （例如 `bin/gost/gost.exe`）。这些内核不会自动下载，需手动放置。
3. v2rayN 内：`服务器` → `添加自定义配置服务器` → **Core 类型** 选对应内核 →
   填 **Socks 端口**（如 `10808`）→ **配置文本参数** 粘贴该内核的 CLI 参数。
4. 右键节点 `测试服务器真连接延迟`（Ctrl+R）即可走本地端口做真连接测速；设为活动服务器后开启
   `自动配置系统代理` 即可接管系统流量。

---

## 新增 / 调整内核

编辑 `patches/v2rayN-extended-cores.patch`（这是唯一的事实来源），在 4 个文件对应位置追加条目，
同步更新 `cores.json` 文档。校验补丁能否干净应用：

```bash
git clone --depth 1 --branch 7.24.4 --filter=blob:none --sparse https://github.com/2dust/v2rayN.git t
cd t && git sparse-checkout set v2rayN
git apply --check /path/to/patches/v2rayN-extended-cores.patch && echo OK
```

若目标 v2rayN 版本与 7.24.4 差异过大导致应用失败，以该版本源码重新生成 diff 即可
（对 4 个文件做相同的最小改动）。
