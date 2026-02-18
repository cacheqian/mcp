# WSL 远程控制 Windows 浏览器 MCP 方案

## 需求
1. 浏览器搜索 MCP，免费
2. 本地部署，不使用云端 MCP server
3. 部署在 WSL，通过网络通信调用 Windows 有头浏览器

## 方案结论

经过对以下方案的详细检查：
- @playwright/mcp (微软官方)
- @executeautomation/playwright-mcp-server
- browser-use-mcp-server
- mcp-chrome
- browser-tools-mcp
- DrissionPage

**结论**：以上现成 MCP 均不直接支持远程 CDP 连接。

**推荐方案**：使用 Python + Playwright 自行编写简单的 MCP Server

---

## 架构

```
WSL (MCP Server)  <--CDP (端口9222)-->  Windows Chrome/Edge
```

---

## 完整实施步骤

### 第一步：Windows 端 - 启动调试浏览器

在 Windows PowerShell 中运行：

```powershell
# Chrome
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug"

# 或 Edge
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\edge-debug"
```

**参数说明**：
- `--remote-debugging-port=9222` 开启调试端口
- `--user-data-dir` 指定用户数据目录（保持登录状态）

### 第二步：WSL 端 - 安装依赖

```bash
# 安装 Python
sudo apt update
sudo apt install python3 python3-pip

# 安装 Playwright
pip install playwright
playwright install chromium
```

### 第三步：创建 MCP Server

创建文件 `remote_browser_mcp.py`：

```python
#!/usr/bin/env python3
import json
import sys
from playwright.sync_api import sync_playwright

# 远程浏览器地址 (Windows IP)
REMOTE_URL = "http://192.168.1.X:9222"  # 改成你的Windows IP

browser = None
context = None
page = None

def get_page():
    global browser, context, page
    if not browser:
        browser = sync_playwright().start().chromium.connect_over_cdp(REMOTE_URL)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
    return page

def handle_request(request):
    try:
        p = get_page()
        name = request.get("name", "")
        args = request.get("arguments", {})

        result = {"content": []}

        if name == "navigate":
            p.goto(args["url"], wait_until="networkidle")
            result["content"].append({"type": "text", "text": f"已导航到 {args['url']}"})

        elif name == "screenshot":
            path = args.get("path", "screenshot.png")
            p.screenshot(path=path, full_page=True)
            result["content"].append({"type": "text", "text": f"截图已保存: {path}"})

        elif name == "click":
            p.click(args["selector"])
            result["content"].append({"type": "text", "text": f"已点击: {args['selector']}"})

        elif name == "fill":
            p.fill(args["selector"], args["value"])
            result["content"].append({"type": "text", "text": f"已填写: {args['selector']}"})

        elif name == "evaluate":
            r = p.evaluate(args["script"])
            result["content"].append({"type": "text", "text": str(r)})

        elif name == "get_page_info":
            result["content"].append({"type": "text", "text": f"URL: {p.url}, Title: {p.title}"})

        else:
            result["isError"] = True
            result["content"].append({"type": "text", "text": f"未知工具: {name}"})

        return result

    except Exception as e:
        return {"content": [{"type": "text", "text": f"错误: {str(e)}"}], "isError": True}

# MCP 协议处理
def main():
    tools = [
        {"name": "navigate", "description": "导航到URL", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
        {"name": "screenshot", "description": "截图", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
        {"name": "click", "description": "点击元素", "inputSchema": {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}},
        {"name": "fill", "description": "填写输入框", "inputSchema": {"type": "object", "properties": {"selector": {"type": "string"}, "value": {"type": "string"}}, "required": ["selector", "value"]}},
        {"name": "evaluate", "description": "执行JS代码", "inputSchema": {"type": "object", "properties": {"script": {"type": "string"}}, "required": ["script"]}},
        {"name": "get_page_info", "description": "获取页面信息", "inputSchema": {"type": "object", "properties": {}}},
    ]

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            msg = json.loads(line.strip())
            method = msg.get("method")
            params = msg.get("params", {})

            if method == "tools/list":
                print(json.dumps({"jsonrpc": "2.0", "id": msg.get("id"), "result": {"tools": tools}}), flush=True)
            elif method == "tools/call":
                result = handle_request(params)
                print(json.dumps({"jsonrpc": "2.0", "id": msg.get("id"), "result": result}), flush=True)
        except Exception as e:
            print(json.dumps({"jsonrpc": "2.0", "error": {"message": str(e)}}), flush=True)

if __name__ == "__main__":
    main()
```

### 第四步：配置 MCP 客户端

在 Claude Desktop / Cline / Cursor 等客户端的配置文件中添加：

```json
{
  "mcpServers": {
    "remote-browser": {
      "command": "python3",
      "args": ["/path/to/remote_browser_mcp.py"]
    }
  }
}
```

### 第五步：获取 Windows IP

在 Windows CMD 中运行：
```cmd
ipconfig
```

找到 IPv4 地址（如 `192.168.1.100`），替换到 `remote_browser_mcp.py` 中的 `REMOTE_URL`。

---

## 关键配置提醒

| 项目 | 说明 |
|------|------|
| Windows 防火墙 | 允许 9222 端口入站 |
| 首次登录 | 在浏览器中手动登录网站，后续会复用 session |
| IP 地址 | 用 Windows 真实局域网 IP，不是 localhost |

---

## 费用

- Playwright: MIT 开源，免费
- Python: 免费
- 浏览器: 使用系统已有的 Chrome/Edge

**总计：完全免费**
