"""Generate Super Mario HTML via Sclerotium OS — direct API with debug."""
import asyncio, os, sys, time, json, urllib.request, traceback
from pathlib import Path

os.environ["DEEPSEEK_API_KEY"] = "sk-9a10241fc127458f8d552c0a3f88b1f7"
API_KEY = os.environ["DEEPSEEK_API_KEY"]

async def main():
    print("=" * 60)
    print("  SCLEROTIUM OS — MARIO GENERATION (direct)")
    print("=" * 60)

    prompt = """写一个高还原度的超级马里奥网页版游戏，要求：

1. 完整的 HTML+CSS+JS 单文件
2. 包含：马里奥角色、砖块、问号方块、管道、蘑菇敌人、金币、旗杆终点
3. 支持键盘控制：左右移动、跳跃（空格键）
4. 有物理重力、碰撞检测
5. 有分数系统
6. 画面精美，像素风格
7. 有背景音乐或音效（用 Web Audio API 简单生成）
8. 有开始界面和游戏结束界面
9. 代码可以直接在浏览器中打开运行

请输出完整的 HTML 文件代码，用 ```html 包裹。"""

    # Short system prompt
    system = "You are an expert game developer. Create a complete, playable Super Mario Bros web game in a single HTML file. Output ONLY the HTML code."

    print(f"System prompt: {len(system)} chars")
    print(f"User prompt: {len(prompt)} chars")
    print()
    print("Calling DeepSeek v4 Pro...")

    body = {
        "model": "deepseek-v4-pro",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 8192,
        "temperature": 0.3,
        "top_p": 0.9,
    }

    t0 = time.time()
    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.time() - t0

        print(f"Response in {elapsed:.1f}s")

        if "error" in data:
            print(f"API ERROR: {data['error']}")
            return

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        print(f"Content: {len(content)} chars")
        print(f"Tokens:  {usage}")
    except Exception as e:
        print(f"Request failed: {e}")
        traceback.print_exc()
        return

    # Extract HTML
    print()
    print("Extracting HTML...")
    html = _extract_html(content)
    print(f"HTML extracted: {len(html)} chars")

    if len(html) < 100:
        print("ERROR: HTML too short!")
        print("Raw content preview:")
        print(content[:500])
        return

    # Save
    output_path = Path("mario_game.html")
    output_path.write_text(html, encoding="utf-8")
    print(f"Saved: {output_path.absolute()} ({len(html)} chars)")

    # Open in browser
    import webbrowser
    webbrowser.open(str(output_path.absolute()))
    print("Opening in browser...")


def _extract_html(content: str) -> str:
    content = content.strip()
    for fence in ["```html", "```HTML", "```"]:
        if fence in content:
            parts = content.split(fence)
            if len(parts) >= 2:
                remaining = fence.join(parts[1:])
                if "```" in remaining:
                    code = remaining.split("```")[0]
                    return code.strip()
                return remaining.strip()
    if content.lower().startswith("<!doctype") or content.lower().startswith("<html"):
        return content
    return content


if __name__ == "__main__":
    asyncio.run(main())
