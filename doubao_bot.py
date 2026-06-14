"""
豆包浏览器自动化 - 主脚本
功能：登录辅助、单次发送、交互式聊天

推荐优先使用 doubao_controller.py（更稳定、更全）。
本文件保留早期版本的简单入口。
"""

import json
import os
import subprocess
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# Windows 编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 项目路径
PROJECT_DIR = Path(__file__).parent
COOKIES_FILE = PROJECT_DIR / "cookies.json"
SESSION_FILE = PROJECT_DIR / "session.json"
CHAT_LOG_FILE = PROJECT_DIR / "chat_history.md"


def save_chat_log(user_msg: str, bot_msg: str):
    """保存聊天记录到 Markdown 文件"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CHAT_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"## {timestamp}\n\n")
        f.write(f"**我问：** {user_msg}\n\n")
        f.write(f"**豆包答：** {bot_msg}\n\n")
        f.write("---\n\n")


def close_chrome_if_running():
    """关闭可能锁定用户数据的 Chrome 进程"""
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    except Exception:
        pass


def get_user_chrome_path():
    """获取用户 Chrome 默认配置路径（用于复用登录态，可选）"""
    local = os.environ.get('LOCALAPPDATA', '')
    chrome_path = os.path.join(local, 'Google', 'Chrome', 'User Data')
    if os.path.exists(chrome_path):
        return chrome_path
    return None


def login():
    """打开浏览器让用户登录豆包，并把登录态保存到 cookies.json

    第一次使用本项目时运行一次即可。
    登录成功后脚本会自动检测并保存 Cookie，然后关闭浏览器。

    推荐改用 tools/save_cookies.py，功能更全。
    """
    chrome_path = get_user_chrome_path()
    if not chrome_path:
        print("[FAIL] Cannot find Chrome user data directory")
        return False

    close_chrome_if_running()

    with sync_playwright() as p:
        print("[INFO] Launching Chrome...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=chrome_path,
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=['--disable-blink-features=AutomationControlled']
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.doubao.com/chat/", timeout=60000)

        print("=" * 50)
        print("请在打开的浏览器中登录豆包")
        print("登录成功后，脚本会自动检测并保存 Cookie")
        print("看到'登录成功'提示后，关闭浏览器即可")
        print("=" * 50)

        # 轮询检测登录状态
        while True:
            time.sleep(2)

            page.screenshot(path=str(PROJECT_DIR / "login_status.png"))

            # 检查是否已登录（没有"登录"按钮了）
            try:
                page.wait_for_selector('text="登录"', timeout=2)
                continue  # 仍然显示登录按钮，未登录
            except Exception:
                pass

            # 检查是否出现聊天输入框（说明已登录）
            try:
                page.wait_for_selector('textarea.semi-input-textarea', timeout=2)
                break
            except Exception:
                continue

        # 保存 cookies
        cookies = context.cookies()
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"[OK] Cookies saved to: {COOKIES_FILE}")

        # 保存 localStorage
        try:
            local_storage = page.evaluate("""() => {
                let items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    let key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            }""")
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(local_storage, f, ensure_ascii=False, indent=2)
            print(f"[OK] Session saved to: {SESSION_FILE}")
        except Exception:
            pass

        print("\n[OK] Login successful! Cookie saved.")
        print("[INFO] You can close the browser now.")

        context.close()
        return True


def chat(message: str, print_response: bool = True) -> str:
    """发送单条消息并获取回复"""
    with sync_playwright() as p:
        chrome_path = get_user_chrome_path()
        if not chrome_path:
            print("[FAIL] Cannot find Chrome user data directory")
            return ""

        close_chrome_if_running()
        time.sleep(1)

        context = p.chromium.launch_persistent_context(
            user_data_dir=chrome_path,
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.doubao.com/chat/", wait_until="networkidle", timeout=60000)

        # 检查登录状态
        try:
            page.wait_for_selector('text="登录"', timeout=3)
            print("[FAIL] Not logged in. See docs/SETUP.md to login first.")
            context.close()
            return ""
        except Exception:
            pass  # 已登录

        print("[INFO] Ready! Sending message...")

        textarea = page.wait_for_selector('textarea.semi-input-textarea', timeout=10000)
        textarea.fill(message)
        textarea.press('Enter')

        print("[INFO] Waiting for response...")

        # 等待回复（最多 3 分钟）
        elapsed = 0
        max_wait = 180
        last_text = ""
        sent_msg_found = False

        while elapsed < max_wait:
            time.sleep(2)
            elapsed += 2

            try:
                page_text = page.inner_text('body')

                # 验证码检测
                captcha_markers = ['验证码', '验证', 'captcha', '人机验证', '安全验证']
                if any(marker in page_text for marker in captcha_markers):
                    print("[WARN] 检测到验证码！请在浏览器中人工完成验证...")
                    input("完成后按回车继续...")

                # 检查是否已发出消息
                if not sent_msg_found and message in page_text:
                    sent_msg_found = True
                    print(f"[INFO] Message sent successfully")

                # 回复完成检测
                reply_complete_markers = ["内容由豆包 AI 生成", "快速", "图像生成"]
                markers_found = sum(1 for m in reply_complete_markers if m in page_text)

                if sent_msg_found and markers_found >= 2 and page_text == last_text and elapsed > 5:
                    reply = page_text.replace(message, "").strip()
                    if reply:
                        if print_response:
                            print(f"\n豆包回复: {reply}")
                        save_chat_log(message, reply)
                        time.sleep(2)
                        context.close()
                        return reply

                last_text = page_text

            except Exception:
                pass

            print(f"[INFO] Waiting... ({elapsed}s/{max_wait}s)")

        # 超时
        if last_text:
            reply = last_text.replace(message, "").strip()
            if reply:
                if print_response:
                    print(f"\n豆包回复: {reply}")
                save_chat_log(message, reply)

        print("[WARN] No response received")
        context.close()
        return ""


def interactive_mode():
    """交互模式（命令行聊天）"""
    print("\n" + "=" * 50)
    print("Doubao Interactive Mode - Type 'quit' to exit")
    print("=" * 50)

    chrome_path = get_user_chrome_path()
    if not chrome_path:
        print("[FAIL] Cannot find Chrome")
        return

    close_chrome_if_running()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=chrome_path,
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=['--disable-blink-features=AutomationControlled']
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.doubao.com/chat/", wait_until="networkidle", timeout=60000)

        # 检查登录状态
        try:
            page.wait_for_selector('text="登录"', timeout=5)
            print("[FAIL] Not logged in. See docs/SETUP.md to login first.")
            context.close()
            return
        except Exception:
            pass

        while True:
            try:
                message = input("\nYou: ").strip()
                if message.lower() == 'quit':
                    break
                if not message:
                    continue

                textarea = page.wait_for_selector('textarea.semi-input-textarea', timeout=10000)
                textarea.fill(message)
                textarea.press('Enter')

                print("[INFO] Waiting for response...")
                time.sleep(10)

                for sel in ['.message-item', '.chat-message', '[class*="message"]']:
                    msgs = page.query_selector_all(sel)
                    if msgs:
                        for i in range(len(msgs) - 1, -1, -1):
                            text = msgs[i].inner_text()
                            if message in text:
                                continue
                            if text.strip():
                                print(f"\n豆包: {text}")
                                save_chat_log(message, text)
                                break

            except KeyboardInterrupt:
                break

        context.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python doubao_bot.py login          - 登录并保存 cookies（首次使用）")
        print("  python doubao_bot.py chat           - 交互式聊天")
        print("  python doubao_bot.py send <消息>    - 发送单条消息")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "login":
        login()
    elif command == "chat":
        interactive_mode()
    elif command == "send" and len(sys.argv) > 2:
        message = " ".join(sys.argv[2:])
        chat(message)
    else:
        print("Unknown command")
        sys.exit(1)
