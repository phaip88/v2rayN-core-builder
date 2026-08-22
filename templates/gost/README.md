# GOST 内核配置使用指南

### 1. 放置二进制
从 [go-gost/gost](https://github.com/go-gost/gost/releases) 下载 Windows 压缩包，解压出 `gost.exe` 放置在 v2rayN 的 `bin/gost/` 目录下。

### 2. 添加到 v2rayN
1. 打开 v2rayN，点击 `服务器` -> `添加自定义配置服务器`。
2. Core类型选择：`gost`。
3. Socks端口填：`10808`。
4. 在配置文本框中填入 `http-socks-relay.txt` 中的参数，替换远端转发地址。
