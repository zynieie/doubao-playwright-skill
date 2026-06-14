"""
豆包自动化 - 交互式控制器
不关闭浏览器，持续执行各种操作

启动后输入指令操作浏览器（new / list / switch / send / upload 等）。
"""
import os
import sys
import time

# 自动把脚本所在目录加入 path，跨平台通用
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doubao_core import DoubaoBrowser


def print_help():
    print("""
=== 豆包控制器命令 ===

【对话操作】
  new          - 创建新对话
  list         - 列出所有对话
  switch <n>   - 切换到第n个对话（数字）
  switch <标题> - 切换到指定标题的对话
  read [n]     - 读取当前对话（或前n个对话预览）
  current      - 显示当前对话标题

【URL管理】（重要！每次打开都是新对话，需要URL跳转）
  saveurl      - 保存当前对话URL到本地
  urllist      - 列出已保存的对话URL
  url <n>      - 跳转到已保存的第n个对话
  url <标题>   - 跳转到已保存的指定标题对话

【消息操作】
  send <消息>  - 发送消息（引号包围）
  upload <路径> - 上传文件

【其他】
  screenshot   - 截图保存
  save         - 保存当前对话
  help         - 显示此帮助
  q            - 退出
""")


def main():
    print("=== 豆包自动化控制器 ===")
    print("启动浏览器...")

    browser = DoubaoBrowser(keep_open=True)
    browser.launch()

    if not browser.is_logged_in():
        print("[FAIL] Not logged in. 请先运行 tools/save_cookies.py 登录并保存 cookies。")
        print("       详见 docs/COOKIE_GUIDE.md")
        browser.close()
        return

    print("[OK] 浏览器已启动，对话列表：")
    convs = browser.get_conversations()
    for c in convs[:10]:
        print(f"  [{c['index']}] {c['title']}")

    print_help()

    # 截图保存路径（脚本所在目录下的 screenshots/）
    screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)

    while True:
        try:
            cmd = input("\n> ").strip()
            if not cmd:
                continue

            parts = cmd.split(None, 1)
            action = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if action in ('q', 'quit', 'exit'):
                print("[INFO] 退出控制器")
                break

            elif action == 'help':
                print_help()

            elif action == 'new':
                browser.create_new_conversation()

            elif action == 'list':
                convs = browser.get_conversations()
                print(f"\n=== 对话列表 ({len(convs)}个) ===")
                for c in convs:
                    print(f"  [{c['index']}] {c['title']}")

            elif action == 'switch':
                if not arg:
                    print("[FAIL] 请指定对话序号或标题")
                elif arg.isdigit():
                    browser.switch_to_conversation(int(arg))
                else:
                    browser.switch_to_conversation(arg)

            elif action == 'read':
                if not arg:
                    content = browser.read_current_conversation()
                    print(f"\n=== 当前对话内容 ({len(content)}字符) ===")
                    print(content[:500] if len(content) > 500 else content)
                else:
                    n = int(arg) if arg.isdigit() else 5
                    print(f"\n=== 读取前{n}个对话 ===")
                    results = browser.read_conversations_preview(n)
                    for r in results:
                        print(f"\n--- [{r['index']}] {r['title']} ---")
                        preview = r['preview']
                        print(preview[:300] + "..." if len(preview) > 300 else preview)

            elif action == 'current':
                convs = browser.get_conversations()
                if convs:
                    print(f"当前对话: [{convs[0]['index']}] {convs[0]['title']}")
                else:
                    print("[WARN] 无法获取当前对话")
                print(f"URL: {browser.get_current_url()}")

            elif action == 'saveurl':
                browser.save_conversation_url()

            elif action == 'urllist':
                convos = browser.get_saved_conversations()
                print(f"\n=== 已保存的对话URL ({len(convos)}个) ===")
                for i, c in enumerate(convos):
                    print(f"  [{i}] {c['title']}")
                    print(f"      {c['url']}")

            elif action == 'url':
                if not arg:
                    print("[FAIL] 请指定序号或标题")
                elif arg.isdigit():
                    browser.switch_to_saved_conversation(int(arg))
                else:
                    browser.switch_to_saved_conversation(arg)

            elif action == 'send':
                if not arg:
                    print("[FAIL] 请输入消息内容")
                else:
                    print(f"[INFO] 发送: {arg[:50]}...")
                    browser.send_message(arg)
                    print("[INFO] 等待回复...")
                    success, reply = browser.wait_for_reply(timeout=300)
                    if success:
                        print(f"\n=== 豆包回复 ({len(reply)}字符) ===")
                        print(reply[:1000] + "..." if len(reply) > 1000 else reply)
                    else:
                        print("[WARN] 未收到有效回复")

            elif action == 'upload':
                if not arg:
                    print("[FAIL] 请指定文件路径")
                else:
                    print(f"[INFO] 上传文件: {arg}")
                    if browser.upload_file(arg):
                        print("[OK] 文件已上传，请在浏览器中发送消息")

            elif action == 'screenshot':
                path = os.path.join(screenshot_dir, f"controller_screenshot_{int(time.time())}.png")
                browser.page.screenshot(path=path)
                print(f"[OK] 截图已保存: {path}")

            elif action == 'save':
                convs = browser.get_conversations()
                if convs:
                    title = convs[0]['title']
                    content = browser.read_current_conversation()
                    browser.save_conversation(title, content)
                else:
                    print("[WARN] 无法保存")

            else:
                print(f"[FAIL] 未知命令: {action}")
                print_help()

        except KeyboardInterrupt:
            print("\n[INFO] 中断，退出控制器")
            break
        except Exception as e:
            print(f"[FAIL] Error: {e}")

    browser.close()
    print("[INFO] 浏览器已关闭")


if __name__ == "__main__":
    main()
