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

新增内置内核需编辑 `patches/v2rayN-extended-cores.patch`；**推荐方式见下一节：填 `cores.user.json` 即可，无需碰补丁。**

---

## ➕ 新增自定义核心：只需填写 `cores.user.json`

无需改补丁、无需改代码。编辑仓库根目录的 **`cores.user.json`**（JSON 数组，空数组 `[]` = 不注入），
然后运行工作流即可。完整可抄示例见 **`cores.user.example.json`**。

构建流程会自动：基础补丁 → 读取 `cores.user.json` → 注入 4 个源文件（锚点定位，
任何锚点缺失立即报错中止，绝不半成品写入）→ 编译。

### 字段说明

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `id` | 字符串 | ✅ | — | C# 合法标识符（字母/数字/下划线，数字不开头）。**建议全小写**：它同时用作 `ECoreType` 枚举名和 `bin/<id>/` 目录名 |
| `enumValue` | 整数 | ✅ | — | 唯一枚举值，**必须在 37–98**（1–30 为 v2rayN 官方占用，31–36 为本项目默认内核，99 保留）。重复会被拒绝并报错 |
| `repo` | 字符串 | ✅ | — | GitHub 仓库 `owner/repo`，用于生成内核的发布页链接（v2rayN 界面"打开下载页"用） |
| `exes` | 字符串数组 | ❌ | `[id]` | 内核可执行文件的候选文件名（**按顺序匹配**，找到即止）。建议同时列出带平台后缀名和裸名 |
| `arguments` | 字符串 | ❌ | `" {0}"` | 启动参数模板，**必须包含 `{0}` 占位符**（否则配置传不进去，仅告警不阻断）。例：`"-c {0}"` |
| `absolutePath` | 布尔 | ❌ | `true` | `{0}` 是否替换为配置文件的**绝对路径**（加引号） |
| `txtArg` | 布尔 | ❌ | `true` | **关键开关**。`true`=该核心把"你在自定义服务器里填的文本"当作**命令行参数本身**接收（gost/chisel/ssh 风格）；`false`=核心期望一个**配置文件路径**（sing-box `-c {0}` 风格） |
| `environment` | 对象 | ❌ | `{}` | 额外环境变量，值中的 `{0}` 会替换为配置路径。如 `{"FILECORE_HOME": "{0}"}` |

> 未知的字段名会被忽略并给出警告（帮你发现拼写错误，比如把 `enumValue` 写成 `enumVal`）。

### 两种典型写法

**风格 A —— 参数内联型**（大多数隧道工具：gost / chisel / ssh / cloudflared / easytier）：

```json
[
  {
    "id": "mytunnel",
    "enumValue": 37,
    "repo": "owner/mytunnel",
    "exes": ["mytunnel_windows_amd64", "mytunnel_linux_amd64", "mytunnel"],
    "arguments": " {0}",
    "txtArg": true
  }
]
```
用户在 v2rayN"配置文本参数"里直接粘贴 CLI 参数（如 `-L socks5://:10808 -F wss://srv:443`），
构建时会把这段文本作为参数原样传给内核。

**风格 B —— 配置文件型**（接受 `-c 配置路径` 的工具）：

```json
[
  {
    "id": "filecore",
    "enumValue": 38,
    "repo": "owner/filecore",
    "exes": ["filecore"],
    "arguments": "-c {0}",
    "absolutePath": false,
    "txtArg": false,
    "environment": { "FILECORE_HOME": "{0}" }
  }
]
```
用户在"配置文本参数"里填的是配置文件**内容**（JSON/YAML），v2rayN 落盘后把**路径**传给内核。

### 判定 `txtArg` 的方法

看该工具官方文档：启动命令是 `tool <一堆参数>` → `txtArg: true`；
是 `tool -c config.json` → `txtArg: false` 并配好 `arguments`。
拿不准时选 `true` + `" {0}"`（与本项目默认 6 核一致）。

### 操作步骤（GitHub 网页即可完成）

1. 打开仓库里的 `cores.user.json` → 铅笔图标编辑。
2. 参照 `cores.user.example.json` 或上表填入你的内核条目（数组里可放多个）。
3. 提交提交到 `main`。
4. `Actions` → `Build v2rayN with Extended Cores` → `Run workflow`
   （version 填目标 v2rayN 版本，`create_release: true` 可发布 Release）。
5. 构建日志中可核对注入结果：每个内核会有 `[+] ECoreType.cs: xxx = nn` 等 3–4 行记录。

### 校验规则（填错会在构建早期报错，不会产出坏 DLL）

- `id` 非法 / `enumValue` 越界或与已有冲突 / 缺 `repo` → **立即报错终止**
- 任一注入锚点在目标版本源码中找不到（v2rayN 大改结构）→ **报错并指出原因**，树保持未修改
- 重复运行/重复声明同一 `id` → 自动跳过（幂等）
- 全部校验通过才写盘；任一步失败则**一个文件都不会被修改**

### 本地预检（可选）

```bash
# 先打好基础补丁，再跑注入器做检查（不编译）
git clone --depth 1 --branch 7.24.4 --filter=blob:none --sparse https://github.com/2dust/v2rayN.git t
cd t && git sparse-checkout set v2rayN
git apply ../patches/v2rayN-extended-cores.patch
python3 ../scripts/add_custom_cores.py ../cores.user.json .
```

### 放置二进制

构建产物不含第三方内核本体。把下载的内核可执行文件放到 v2rayN 的 `bin/<id>/` 目录，
文件名与 `exes` 中某一项对应（Windows 下带 `.exe` 也可，v2rayN 会自动补全），例如 `bin/mytunnel/mytunnel.exe`。

---

## 高级：直接改补丁（维护者）

`patches/v2rayN-extended-cores.patch` 是默认 6 核的事实来源（4 个源文件的最小 diff）。
若要调整默认内核或适配新版 v2rayN 的源码结构，可直接重生成该 diff；普通用户**不需要**动它。
校验补丁能否干净应用：

```bash
git clone --depth 1 --branch 7.24.4 --filter=blob:none --sparse https://github.com/2dust/v2rayN.git t
cd t && git sparse-checkout set v2rayN
git apply --check ../patches/v2rayN-extended-cores.patch && echo OK
```

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
