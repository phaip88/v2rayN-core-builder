# Cloudflared 内核配置使用指南

### 1. 放置二进制
从 [cloudflare/cloudflared](https://github.com/cloudflare/cloudflared/releases) 下载 `cloudflared-windows-amd64.exe`，重命名为 `cloudflared.exe` 并放置在 v2rayN 的 `bin/cloudflared/` 目录下。

### 2. 添加到 v2rayN
1. 打开 v2rayN，点击 `服务器` -> `添加自定义配置服务器`。
2. 别名填：`Cloudflare Tunnel - Socks5`。
3. Core类型选择：`cloudflared`。
4. Socks端口填：`10808`（与模板中的本地端口一致，供真连接测速与系统代理使用）。
5. 在配置文本框中填入 `socks5-proxy.txt` 中的参数，将 `your-tunnel.example.com` 替换为你的 Cloudflare 域名。
6. 点击确认保存。
