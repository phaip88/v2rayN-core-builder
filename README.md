# v2rayN Extended Core Builder

> 自动化构建支持多内核扩展（Cloudflared, EasyTier, GOST, Chisel 等）的 v2rayN 客户端与 `ServiceLib.dll` 补丁组件。

---

## 📖 项目简介

官方 v2rayN 具备成熟的节点管理、真连接测速、系统代理及路由分流生态。本项目通过结构化声明与源码补丁引擎，将更多现代代理/穿透/组网工具（如 Cloudflare Tunnel、EasyTier、GOST、Chisel 等）无缝集成进 v2rayN 的核心管理调度系统中。

### 核心特性
- **声明式内核扩展**：新增内核只需在 `cores.json` 中添加配置项，无需手动修改 C# 源码。
- **全自动 CI 构建**：借助 GitHub Actions 支持针对任意 v2rayN 官方版本（如 7.14.x、7.24.x 或最新版）一键打包构建。
- **双重交付物**：同时产出轻量级 `ServiceLib.dll` 补丁压缩包与开箱即用的完整版客户端整合包。
- **原生测速支持**：保留 v2rayN 的本地代理监听感知，扩展内核同样支持 **真连接测速** 与 **Tcping 延迟测试**。

---

## 🎯 内核准入要求（哪些内核符合添加条件）

并非所有网络工具都适合直接集成到客户端中。符合添加要求的内核通常满足以下条件：

1. **独立可执行程序（CLI Binary）**
   - 内核应为独立的命令行可执行文件（如 Windows 下的 `.exe`），无需安装额外的系统级复杂运行环境。
2. **支持参数或配置文件启动**
   - 支持通过命令行参数（CLI Flags）或传入标准配置文件路径（JSON/YAML/TOML/TXT）启动服务。
3. **具备本地网络接口（SOCKS5 / HTTP / 本地端口转发）**
   - 内核启动后应能在本地回环地址（`127.0.0.1`）监听 Socks5、HTTP 或特定 TCP 端口，以供 v2rayN 接管系统代理或发起真连接测速。
4. **标准标准输入输出与退出生命周期**
   - 进程能够通过标准信号正常启停，并输出标准日志供 v2rayN 日志面板实时捕获。

### 当前默认集成的扩展内核
| 内核标识 | 内核名称 | 典型应用场景 | 官方仓库 |
| :--- | :--- | :--- | :--- |
| `cloudflared` | Cloudflare Tunnel | 免公网 IP 穿透、Socks5 访问私有网络 | [cloudflare/cloudflared](https://github.com/cloudflare/cloudflared) |
| `easytier` | EasyTier | 去中心化 P2P 虚拟局域网异地组网 | [EasyTier/EasyTier](https://github.com/EasyTier/EasyTier) |
| `gost` | GOST | 多协议链式转发、安全隧道穿透 | [go-gost/gost](https://github.com/go-gost/gost) |
| `chisel` | Chisel | 基于 HTTP/Websocket 的高性能 TCP/UDP 隧道 | [jpillora/chisel](https://github.com/jpillora/chisel) |
| `ssh` | OpenSSH | 经典 SSH Dynamic SOCKS5 动态端口转发 | [PowerShell/Win32-OpenSSH](https://github.com/PowerShell/Win32-OpenSSH) |

---

## 🛠️ 如何使用本项目进行构建

### 方案一：GitHub Actions 在线自动构建（推荐）

1. **Fork 本仓库** 到个人 GitHub 账号。
2. 进入仓库页面的 **Actions** 标签页。
3. 选择 **`Build v2rayN with Extended Cores`** 工作流。
4. 点击 **Run workflow**：
   - **v2rayN Target Version**：填入目标版本（例如 `latest`，或指定版本如 `7.24.4`、`7.14.12`）。
   - **Build full v2rayN-Extended package**：勾选则生成完整客户端包。
5. 构建完成后，直接在 Actions 运行记录或 Releases 页面下载编译好的 Zip 资产。

### 方案二：本地命令行构建

#### 前置环境要求
- .NET 8.0 SDK 或更高版本
- Python 3.8+
- Git

#### 构建步骤
```bash
# 1. 克隆本项目
git clone https://github.com/phaip88/v2rayN-core-builder.git
cd v2rayN-core-builder

# 2. 克隆上游 v2rayN 源码
git clone --depth 1 --branch 7.24.4 https://github.com/2dust/v2rayN.git v2rayN-upstream

# 3. 执行内核补丁注入
python scripts/patch_v2rayn.py ./v2rayN-upstream cores.json

# 4. 编译 ServiceLib 类库
dotnet build ./v2rayN-upstream/v2rayN/ServiceLib/ServiceLib.csproj -c Release -o ./dist/ServiceLib

# 5. （可选）发布完整客户端
dotnet publish ./v2rayN-upstream/v2rayN/v2rayN/v2rayN.csproj -c Release -r win-x64 --self-contained false -o ./dist/v2rayN-Extended
```

---

## 🚀 用户使用指南（小白上手教程）

### 第一步：获取客户端与组件

根据需求选择以下任意一种方式：
- **方式 A（整包使用）**：下载 `v2rayN-Extended-win64-<version>.zip` 并解压，即为已打好补丁的完整客户端。
- **方式 B（现有客户端升级）**：下载 `ServiceLib-<version>.zip`，解压得到 `ServiceLib.dll`，覆盖至原有同版本 v2rayN 根目录。

### 第二步：放置对应内核二进制程序

在 v2rayN 根目录下的 `bin` 文件夹中新建对应内核子目录，并将可执行文件放入其中：

| 内核 | 文件夹路径 | 文件重命名要求 |
| :--- | :--- | :--- |
| **Cloudflared** | `bin/cloudflared/` | `cloudflared.exe` |
| **EasyTier** | `bin/easytier/` | `easytier-core.exe` |
| **GOST** | `bin/gost/` | `gost.exe` |
| **Chisel** | `bin/chisel/` | `chisel.exe` |

---

### 第三步：在 v2rayN 中添加并使用节点

1. 打开 v2rayN，点击顶部菜单 **`服务器`** -> **`添加自定义配置服务器`**。
2. 填写节点信息：
   - **别名**：如 `Cloudflare Tunnel 本地出口`。
   - **Core类型**：在下拉框中选择对应的内核（如 `cloudflared`）。
   - **Socks端口**：填入模板中设定的本地端口（如 `10808`）。**（关键：填入端口后方可启用真连接测速与系统代理）**。
   - **配置文件/参数**：在文本框中粘贴启动参数（参考项目内置 `templates/` 目录中的模板）。
3. 点击 **确定** 保存。

#### 示例配置：Cloudflare Tunnel Socks5
```text
access socks5 --hostname tunnel.yourdomain.com --url 127.0.0.1:10808
```

#### 示例配置：GOST 多跳代理
```text
-L socks5://127.0.0.1:10808 -F relay+tls://your-vps.com:443
```

---

## 📊 真连接测速与系统代理说明

- **真连接测速（Speedtest / 延迟测试）**：
  在节点中正确填写了 `Socks端口`（如 `10808`）后，按下 `Ctrl + R` 或右键点击 **测试服务器真连接延迟**，v2rayN 会自动通过该内核的本地监听端口发起 HTTP 握手并反馈毫秒级延迟与连通状态。
- **系统代理控制**：
  设为活动服务器后，开启底部的 **自动配置系统代理**，Windows 全局流量将自动经由该内核本地代理端口转发。

---

## ⚙️ 如何添加新的自定义内核

若想扩展更多内核，只需在 `cores.json` 文件中追加记录：

```json
{
  "id": "mycore",
  "name": "My Custom Core",
  "enumValue": 41,
  "repo": "owner/repo",
  "exes": ["mycore_windows_amd64", "mycore"],
  "arguments": " {0}",
  "isTxtConfig": true,
  "absolutePath": true
}
```
提交推送到 GitHub 后，工作流将自动编译支持该新内核的全部产物。

---

## 📄 开源许可证

本项目遵循 [GPL-3.0 License](LICENSE)，核心基于 [2dust/v2rayN](https://github.com/2dust/v2rayN) 二次构建。
