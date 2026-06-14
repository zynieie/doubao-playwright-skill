"""
一键登录保存 cookies 工具
==========================

打开浏览器 → 让你手动登录豆包 → 检测到登录成功 → 自动保存 cookies.json + session.json

用法：
    python tools/save_cookies.py

注意：
- 这是本地运行的纯客户端脚本，不连接任何外部服务器
- cookies.json 等同于账号密码，请妥善保管
- 本工具不内置任何 cookies，必须你自己登录才能产生
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path

# Windows 编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 把项目根目录加入 path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from playwright.sync_api import sync_playwright

COOKIES_FILE = PROJECT_DIR / "cookies.json"
SESSION_FILE = PROJECT_DIR / "session.json"


def close_chrome():
    """关闭可能冲突的 Chrome 进程"""
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
    except Exception:
        pass


def main():
    print("=" * 50)
    print("       豆包 Cookie 一键保存工具")
    print("=" * 50)
    print()
    print("[INFO] 启动浏览器...")
    print("[INFO] 等待你登录豆包...")
    print("[INFO] 请在打开的浏览器窗口中完成登录")
    print("[INFO] 登录成功后脚本会自动保存")
    print()

    close_chrome()

    # 使用项目自带的独立 Profile 目录（避免污染用户 Chrome）
    profile_dir = str(PROJECT_DIR / "browser_profile")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=['--disable-blink-features=AutomationControlled']
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.doubao.com/chat/", timeout=60000)

        # 轮询检测登录状态
        max_wait = 300  # 最多等 5 分钟
        elapsed = 0
        check_interval = 2

        while elapsed < max_wait:
            time.sleep(check_interval)
            elapsed += check_interval

            # 截一张图方便诊断
            page.screenshot(path=str(PROJECT_DIR / "login_status.png"))

            # 检查是否还有"登录"按钮
            try:
                page.wait_for_selector('text="登录"', timeout=2)
                # 还在显示登录按钮 → 未登录
                if elapsed % 10 == 0:
                    print(f"  ⏳ 等待登录中... ({elapsed}s / {max_wait}s)")
                continue
            except Exception:
                pass

            # 进一步检查：是否出现聊天输入框（说明已登录到聊天界面）
            try:
                page.wait_for_selector('textarea.semi-input-textarea', timeout=3)
                # 找到了 → 登录成功
                break
            except Exception:
                continue

        else:
            # 超时
            print(f"\n[FAIL] 等待登录超时（{max_wait} 秒）")
            print("[INFO] 请检查网络并重试")
            context.close()
            return False

        # === 登录成功！保存 cookies ===
        print("\n[OK] 检测到登录成功！")
        print("[INFO] 正在保存 cookies...")

        cookies = context.cookies()
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"[OK] cookies.json 已保存（{len(cookies)} 个 cookie）")

        # === 保存 localStorage ===
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
            print(f"[OK] session.json 已保存（{len(local_storage)} 项 localStorage）")
        except Exception as e:
            print(f"[WARN] localStorage 保存失败（不影响主流程）: {e}")

        print()
        print("=" * 50)
        print("[SUCCESS] 全部完成！")
        print()
        print("下一步：")
        print("  1. 关闭浏览器")
        print("  2. 运行: python examples/basic_chat.py  验证登录态")
        print("  3. 或运行: python doubao_controller.py   进入交互模式")
        print("=" * 50)

        # 保持浏览器打开 3 秒，让用户看到提示
        time.sleep(3)
        context.close()
        return True


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断，退出")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
