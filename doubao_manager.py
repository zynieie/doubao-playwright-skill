"""
豆包对话管理器（轻量版）
- 列出所有对话
- 切换到指定对话
- 获取/保存对话内容

如果只需要完整的自动化控制（发送消息、等待回复），
请优先使用 doubao_core.py + doubao_controller.py。
"""

import os
import subprocess
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# Windows 编码修复
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(__file__).parent


def close_chrome():
    """关闭可能冲突的 Chrome 进程"""
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    except Exception:
        pass


def get_chrome_path():
    """获取用户 Chrome 配置目录"""
    local = os.environ.get('LOCALAPPDATA', '')
    return os.path.join(local, 'Google', 'Chrome', 'User Data')


class DoubaoManager:
    def __init__(self):
        self.context = None
        self.page = None
        self.conversations = []

    def launch(self):
        """启动浏览器并打开豆包"""
        close_chrome()

        p = sync_playwright()
        self.playwright = p.__enter__()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=get_chrome_path(),
            headless=False,
            viewport={"width": 1280, "height": 800}
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.goto("https://www.doubao.com/chat/", wait_until="networkidle", timeout=60000)
        return self

    def get_conversations(self):
        """获取左侧对话列表"""
        try:
            history_btn = self.page.query_selector('text="历史对话"')
            if history_btn:
                history_btn.click()
                time.sleep(1)
        except Exception:
            pass

        time.sleep(2)

        # 通过 JS 一次性抓取所有对话
        conv_list = self.page.evaluate("""() => {
            const items = document.querySelectorAll('[data-testid="chat_list_thread_item"]');
            return Array.from(items).map((el, i) => ({
                index: i,
                title: el.innerText.split('\\n')[0],
                text: el.innerText,
                href: el.href || ''
            }));
        }""")

        self.conversations = conv_list
        return conv_list

    def switch_to_conversation(self, index_or_title):
        """切换到指定对话（按索引或标题）"""
        self.get_conversations()

        if isinstance(index_or_title, int):
            if 0 <= index_or_title < len(self.conversations):
                conv = self.conversations[index_or_title]
            else:
                print(f"[FAIL] Invalid index {index_or_title}, range: 0-{len(self.conversations)-1}")
                return False
        else:
            matches = [c for c in self.conversations if index_or_title in c['title']]
            if not matches:
                print(f"[FAIL] No conversation found with title: {index_or_title}")
                return False
            if len(matches) > 1:
                print(f"[WARN] Multiple matches found, using first one: {matches[0]['title']}")
            conv = matches[0]

        # 点击切换
        items = self.page.query_selector_all('[data-testid="chat_list_thread_item"]')
        for item in items:
            if conv['title'] in item.inner_text():
                item.click()
                time.sleep(2)
                print(f"[OK] Switched to: {conv['title']}")
                return True

        print(f"[FAIL] Could not click conversation: {conv['title']}")
        return False

    def get_current_messages(self):
        """获取当前对话的页面文本和消息元素"""
        time.sleep(2)

        messages = self.page.evaluate("""() => {
            const result = {
                raw: document.body.innerText,
                messages: []
            };

            // 尝试多种消息容器选择器
            const selectors = [
                '.message-item',
                '.chat-message',
                '[class*="message"]',
                '.conversation-item'
            ];

            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                if (els.length > 0) {
                    result.messages = Array.from(els).map(el => ({
                        class: el.className,
                        text: el.innerText.substring(0, 500)
                    }));
                    break;
                }
            }

            return result;
        }""")

        return messages

    def save_conversation(self, title, messages):
        """保存对话到 Markdown 文件"""
        safe_title = title[:20].replace('/', '_').replace('\\', '_').replace(':', '_').replace('?', '_')
        filename = f"conversation_{safe_title}.md"
        filepath = PROJECT_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            f.write(f"## 对话内容\n\n")

            raw_text = messages.get('raw', '')
            lines = raw_text.split('\n')

            in_chat = False
            chat_lines = []

            for line in lines:
                if any(ui in line for ui in ['新对话', 'AI 创作', '云盘', '历史对话', '快速', '图像生成', '超能模式']):
                    continue
                if line.strip() in ['豆包', '更多', '内容由豆包 AI 生成']:
                    continue
                if line.strip():
                    chat_lines.append(line)

            seen = set()
            cleaned = []
            for line in chat_lines:
                if line not in seen and len(line) > 2:
                    seen.add(line)
                    cleaned.append(line)

            f.write('\n'.join(cleaned))

        print(f"[OK] Saved to: {filepath}")
        return filepath

    def close(self):
        """关闭浏览器"""
        if self.context:
            self.context.close()
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def main():
    with DoubaoManager() as bot:
        bot.launch()

        if len(sys.argv) < 2:
            convs = bot.get_conversations()
            print("\n=== Conversations ===")
            for i, c in enumerate(convs):
                print(f"  [{i}] {c['title']}")
            return

        command = sys.argv[1]

        if command == "list":
            convs = bot.get_conversations()
            print("\n=== Conversations ===")
            for i, c in enumerate(convs):
                print(f"  [{i}] {c['title']}")

        elif command == "switch" and len(sys.argv) > 2:
            target = sys.argv[2]
            try:
                index = int(target)
                bot.switch_to_conversation(index)
            except ValueError:
                bot.switch_to_conversation(target)

        elif command == "save" and len(sys.argv) > 2:
            target = sys.argv[2]
            try:
                index = int(target)
                bot.switch_to_conversation(index)
            except ValueError:
                bot.switch_to_conversation(target)
            messages = bot.get_current_messages()
            bot.save_conversation(target, messages)

        elif command == "all":
            convs = bot.get_conversations()
            for i, c in enumerate(convs):
                print(f"[{i}/{len(convs)}] Saving: {c['title']}")
                bot.switch_to_conversation(i)
                messages = bot.get_current_messages()
                bot.save_conversation(c['title'], messages)

        else:
            print("Usage:")
            print("  python doubao_manager.py list              - List all conversations")
            print("  python doubao_manager.py switch <index>   - Switch to conversation by index")
            print("  python doubao_manager.py switch <title>    - Switch to conversation by title")
            print("  python doubao_manager.py save <target>    - Save conversation by index or title")
            print("  python doubao_manager.py all               - Save all conversations")


if __name__ == "__main__":
    main()
