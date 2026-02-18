# WSL 远程浏览器 MCP 项目

## 项目概述

通过 WSL 运行 MCP Server，连接 Windows 上的浏览器（Chrome/Edge），实现远程浏览器控制。

## 架构

```
WSL (MCP Server) <--CDP (端口9223)--> Windows Chrome/Edge
```

## 核心文件

- `remote_browser_mcp.py` - MCP 服务器实现，基于 Playwright 连接远程浏览器
- `plan.md` - 项目方案文档

## MCP 工具（共 7 个）

| 工具 | 描述 | 参数 |
|------|------|------|
| `navigate` | 导航到指定URL | `url` (必填) |
| `screenshot` | 截取当前页面截图 | `path` (可选) |
| `click` | 点击页面元素 | `selector` (必填) |
| `fill` | 填写输入框 | `selector`, `value` (必填) |
| `evaluate` | 执行JavaScript代码 | `script` (必填) |
| `get_page_info` | 获取页面信息(URL和标题) | 无 |
| `get_html` | 获取页面HTML源码 | 无 |

## 使用方式

在 MCP 客户端（Claude Desktop、Cline 等）配置：

```json
{
  "mcpServers": {
    "remote-browser": {
      "command": "python3",
      "args": ["/home/mcp-learning/remote_browser_mcp.py"]
    }
  }
}
```

## 注意事项

1. Windows 端需先启动调试浏览器：`chrome.exe --remote-debugging-port=9223`
2. 防火墙需允许 9223 端口入站
3. MCP 客户端会自动管理服务器进程，无需手动运行
4. 浏览器连接地址在 `remote_browser_mcp.py` 第 11 行配置
