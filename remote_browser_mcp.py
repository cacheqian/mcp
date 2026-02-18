#!/usr/bin/env python3
"""
远程浏览器 MCP Server
通过 CDP 连接 Windows 上的浏览器
"""
import json
import sys
from playwright.sync_api import sync_playwright

# 远程浏览器地址
REMOTE_URL = "http://localhost:9223"

playwright = None
browser = None
context = None
page = None


def get_page():
    """获取或创建页面"""
    global playwright, browser, context, page

    if not playwright:
        playwright = sync_playwright()

    # 如果 browser 为 None 或已关闭，重新连接
    if browser is None or not browser.is_connected():
        pw = playwright.start()
        browser = pw.chromium.connect_over_cdp(REMOTE_URL)

    if not context or context.browser == None:
        context = browser.new_context(viewport={"width": 1920, "height": 1080})

    if not page or page.is_closed():
        page = context.new_page()

    return page


def ensure_connection():
    """确保浏览器连接有效"""
    global browser
    try:
        if browser and browser.is_connected():
            return True
    except:
        pass
    return False


def handle_tool_request(request):
    """处理工具调用请求"""
    try:
        p = get_page()
        name = request.get("name", "")
        args = request.get("arguments", {})

        result = {"content": []}

        if name == "navigate":
            url = args.get("url", "")
            p.goto(url, wait_until="networkidle", timeout=30000)
            result["content"].append({
                "type": "text",
                "text": f"已导航到: {url}\n当前标题: {p.title()}"
            })

        elif name == "screenshot":
            path = args.get("path", "screenshot.png")
            p.screenshot(path=path, full_page=True)
            result["content"].append({"type": "text", "text": f"截图已保存: {path}"})

        elif name == "click":
            selector = args.get("selector", "")
            p.click(selector, timeout=10000)
            result["content"].append({"type": "text", "text": f"已点击: {selector}"})

        elif name == "fill":
            selector = args.get("selector", "")
            value = args.get("value", "")
            p.fill(selector, value, timeout=10000)
            result["content"].append({"type": "text", "text": f"已在 {selector} 填写: {value}"})

        elif name == "evaluate":
            script = args.get("script", "")
            r = p.evaluate(script)
            result["content"].append({"type": "text", "text": f"执行结果: {r}"})

        elif name == "get_page_info":
            info = f"URL: {p.url}\n标题: {p.title()}"
            result["content"].append({"type": "text", "text": info})

        elif name == "get_html":
            html = p.content()
            result["content"].append({"type": "text", "text": html[:5000]})  # 限制长度

        else:
            result["isError"] = True
            result["content"].append({"type": "text", "text": f"未知工具: {name}"})

        return result

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"错误: {str(e)}"}],
            "isError": True
        }


def main():
    """MCP 主循环"""
    tools = [
        {
            "name": "navigate",
            "description": "导航到指定URL",
            "inputSchema": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "要访问的URL"}},
                "required": ["url"]
            }
        },
        {
            "name": "screenshot",
            "description": "截取当前页面截图",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "保存路径，默认 screenshot.png"}}
            }
        },
        {
            "name": "click",
            "description": "点击页面元素",
            "inputSchema": {
                "type": "object",
                "properties": {"selector": {"type": "string", "description": "CSS选择器或XPath"}},
                "required": ["selector"]
            }
        },
        {
            "name": "fill",
            "description": "填写输入框",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS选择器"},
                    "value": {"type": "string", "description": "要填写的值"}
                },
                "required": ["selector", "value"]
            }
        },
        {
            "name": "evaluate",
            "description": "执行JavaScript代码",
            "inputSchema": {
                "type": "object",
                "properties": {"script": {"type": "string", "description": "JavaScript代码"}},
                "required": ["script"]
            }
        },
        {
            "name": "get_page_info",
            "description": "获取当前页面信息(URL和标题)",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "get_html",
            "description": "获取当前页面HTML源码",
            "inputSchema": {"type": "object", "properties": {}}
        },
    ]

    while True:
        line = sys.stdin.readline()
        if not line:
            break

        try:
            msg = json.loads(line.strip())
            method = msg.get("method")
            msg_id = msg.get("id")
            params = msg.get("params", {})

            if method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": tools}
                }
                print(json.dumps(response), flush=True)

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result = handle_tool_request({"name": tool_name, "arguments": tool_args})
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                }
                print(json.dumps(response), flush=True)

        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {"message": str(e)}
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
