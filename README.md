# v2rayN Extended Core Builder

> 自动化构建支持多内核扩展（Cloudflared, EasyTier, GOST, Chisel, OpenSSH 等）的 v2rayN 客户端与 `ServiceLib.dll` 补丁组件。

---

## 📖 项目简介

官方 v2rayN 具备成熟的节点管理、真连接测速、系统代理及路由分流生态。本项目通过结构化声明与源码补丁引擎，将更多现代代理/穿透/组网工具（如 Cloudflare Tunnel、EasyTier、GOST、Chisel、OpenSSH 等）无缝集成进 v2rayN 的核心管理调度系统中。

### 核心特性
- **声明式内核扩展**：新增内核只需在 `cores.json` 中添加配置项，无需手动修改 C# 源码。
- **全自动 CI 构建**：借助 GitHub Actions 支持针对任意 v2rayN 官方版本（如 7.14.x、7.24.x 或最新版）一键打包构建。
- **双重交付物**：同时产出轻量级 `ServiceLib.dll` 补丁压缩包与内置 .NET 运行时的免安装图形界面完整版客户端（Self-Contained）。
- **原生测速支持**：保留 v2rayN 的本地代理监听感知，扩展内核同样支持 **真连接测速（Google 204）** 与 **Tcping 延迟测试**。

---

## 🎯 内核准入要求（哪些内核符合添加条件）

符合添加要求的内核通常满足以下条件：

1. **独立可执行程序（CLI Binary）**：内核为独立的命令行可执行文件（如 Windows 下的 `.exe`），无外部复杂运行库依赖。
2. **支持参数或配置文件启动**：支持通过命令行参数（CLI Flags）或传入标准配置文件路径启动服务。
3. **具备本地网络接口（SOCKS5 / HTTP / 本地端口转发）**：内核启动后在本地回环地址（`127.0.0.1`）监听端口，供 v2rayN 接管系统代理或发起真连接测速。
4. **标准标准输入输出与退出生命周期**：进程能够响应退出信号正常终止，并输出日志供 v2rayN 日志面板实时捕获。

---

## 📚 新增内核服务端执行命令与客户端 v2rayN 配置案例

以下为各新增扩展内核在服务端部署与 v2rayN 客户端添加的完整案例：

### 1. Cloudflare Tunnel (`cloudflared`)

* **应用场景**：免公网 IP 内网穿透、访问私有网络、TCP 端口转发。
* **内核存放路径**：`bin/cloudflared/cloudflared.exe`
* **服务端执行命令**（Linux / VPS / 内网机器）：
  ```bash
  # 方式 1：使用 Token 运行 Tunnel
  cloudflared tunnel run --token <YOUR_TUNNEL_TOKEN>

  # 方式 2：快速映射本地服务（如本地 SSH 22 端口）
  cloudflared tunnel --url tcp://localhost:22
  ```
* **客户端 v2rayN 配置**：
  1. 点击 `服务器` -> `添加自定义配置服务器`。
  2. **Core类型**：选择 `cloudflared`。
  3. **Socks端口**：填 `10808`。
  4. **配置文本参数**（粘贴以下内容）：
     ```text
     access socks5 --hostname tunnel.yourdomain.com --url 127.0.0.1:10808
     ```
     *(如做 TCP 转发可使用: `access tcp --hostname ssh.yourdomain.com --url 127.0.0.1:10808`)*

---

### 2. GOST 多协议隧道 (`gost`)

* **应用场景**：WebSocket/WSS 加密中继、多级链式代理转发、Socks5 安全穿透。
* **内核存放路径**：`bin/gost/gost.exe`
* **服务端执行命令**（Linux / VPS）：
  ```bash
  # 启动 WSS 传输层中继并开启代理出站
  gost -L "relay+wss://gpuser:gppass@:443"
  ```
* **客户端 v2rayN 配置**：
  1. 点击 `服务器` -> `添加自定义配置服务器`。
  2. **Core类型**：选择 `gost`。
  3. **Socks端口**：填 `10809`。
  4. **配置文本参数**（粘贴以下内容）：
     ```text
     -L tcp://:10809 -F "relay+wss://gpuser:gppass@freedns.koalas.kdns.fr:443"
     ```
     *(或本地标准 Socks5 监听: `-L socks5://:10809 -F "relay+wss://gpuser:gppass@your-domain.com:443"`)*

---

### 3. EasyTier 异地组网 (`easytier`)

* **应用场景**：去中心化 P2P 虚拟局域网异地组网、全互联 Mesh 网络。
* **内核存放路径**：`bin/easytier/easytier-core.exe`
* **服务端 / 公网节点执行命令**（VPS）：
  ```bash
  easytier-core -d --ipv4 10.144.144.1 -n my_mesh_network -p my_mesh_password -l 0.0.0.0:11010
  ```
* **客户端 v2rayN 配置**：
  1. 点击 `服务器` -> `添加自定义配置服务器`。
  2. **Core类型**：选择 `easytier`。
  3. **Socks端口**：填 `0`（组网节点无需本地代理端口）。
  4. **配置文本参数**（粘贴以下内容）：
     ```text
     -i 10.144.144.2 --peers tcp://public.easytier.top:11010 -n my_mesh_network -p my_mesh_password
     ```

---

### 4. Chisel 高性能隧道 (`chisel`)

* **应用场景**：通过 HTTP/Websocket 进行多路复用 TCP/UDP 穿透代理。
* **内核存放路径**：`bin/chisel/chisel.exe`
* **服务端执行命令**（VPS）：
  ```bash
  chisel server --port 8080 --reverse --socks5
  ```
* **客户端 v2rayN 配置**：
  1. 点击 `服务器` -> `添加自定义配置服务器`。
  2. **Core类型**：选择 `chisel`。
  3. **Socks端口**：填 `10808`。
  4. **配置文本参数**（粘贴以下内容）：
     ```text
     client --keepalive 25s https://your-chisel-server.com:8080 socks:127.0.0.1:10808
     ```

---

### 5. OpenSSH 动态转发 (`ssh`)

* **应用场景**：直接利用云服务器原生 SSH 端口建立动态 SOCKS5 代理。
* **内核存放路径**：`bin/ssh/ssh.exe`（或直接利用系统自带 `ssh`）
* **服务端执行命令**：云服务器标准 `sshd` 正常运行即可。
* **客户端 v2rayN 配置**：
  1. 点击 `服务器` -> `添加自定义配置服务器`。
  2. **Core类型**：选择 `ssh`。
  3. **Socks端口**：填 `10808`。
  4. **配置文本参数**（粘贴以下内容）：
     ```text
     -N -D 127.0.0.1:10808 -p 22 -o StrictHostKeyChecking=no root@your-vps-ip -i C:/Users/YourUser/.ssh/id_rsa
     ```

---

## 🛠️ 如何使用本项目进行构建

### 方案一：GitHub Actions 在线自动构建（推荐）

1. **Fork 本仓库** 到个人 GitHub 账号。
2. 进入仓库页面的 **Actions** 标签页，选择 **`Build v2rayN with Extended Cores`** 工作流。
3. 点击 **Run workflow**：
   - **v2rayN Target Version**：填入目标版本（例如 `latest`，或指定版本如 `7.24.4`、`7.14.12`）。
   - **Build full v2rayN-Extended package**：勾选生成完整客户端包。
4. 构建完成后，直接在 Actions 运行记录或 Releases 页面下载 `v2rayN-Extended-win64-SelfContained-*.zip`（已内置 .NET 8 桌面运行时，开箱双击即可启动图形界面）。

### 方案二：本地命令行构建

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

# 5. （可选）发布免安装自包含完整客户端
dotnet publish ./v2rayN-upstream/v2rayN/v2rayN/v2rayN.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false -o ./dist/v2rayN-Extended
```

---

## 📊 真连接测速与系统代理说明

- **真连接测速（Speedtest / 延迟测试）**：
  在节点中正确填写了 `Socks端口`（如 `10808` / `10809`）后，在节点列表中按 `Ctrl + R` 或右键点击 **测试服务器真连接延迟**，v2rayN 会自动通过该内核的本地监听端口发起真实 HTTP 握手并显示延迟毫秒数与连通状态。
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
