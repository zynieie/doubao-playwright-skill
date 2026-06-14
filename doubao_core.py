"""
豆包浏览器自动化 - 核心库
统一的浏览器控制和对话管理

通过 Playwright 控制豆包 AI 网页端，支持登录态复用、消息收发、
文件上传、对话管理与 URL 持久化等能力。
"""

import json
import os
import subprocess
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# 项目根目录（所有数据文件都存放在这里）
PROJECT_DIR = Path(__file__).parent
COOKIES_FILE = PROJECT_DIR / "cookies.json"
CONVERSATIONS_FILE = PROJECT_DIR / "conversations.json"  # 保存的对话 URL 记录


def get_chrome_path():
    """获取用户 Chrome 配置目录（用于复用登录态）"""
    local = os.environ.get('LOCALAPPDATA', '')
    return os.path.join(local, 'Google', 'Chrome', 'User Data')


def close_chrome():
    """关闭可能占用配置目录的 Chrome 进程"""
    subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'],
                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)


class DoubaoBrowser:
    """豆包浏览器控制类"""

    def __init__(self, headless=False, keep_open=False):
        self.headless = headless
        # 允许通过环境变量 KEEP_BROWSER=true 保持浏览器打开
        self.keep_open = keep_open or os.environ.get('KEEP_BROWSER', '').lower() == 'true'
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def launch(self):
        """启动浏览器并打开豆包

        - 关闭可能存在的 Chrome 进程以避免数据目录冲突
        - 使用项目自带的独立 Profile（避免与用户 Chrome 冲突）
        - 自动加载 cookies.json / local_storage.json（如果存在）
        """
        close_chrome()

        self.playwright = sync_playwright().__enter__()

        # 独立 Profile 目录，避免污染用户 Chrome
        profile_dir = str(PROJECT_DIR / "browser_profile")

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
            args=['--disable-blink-features=AutomationControlled']
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

        # 加载已保存的登录态
        self._load_cookies()

        self.page.goto("https://www.doubao.com/chat/", wait_until="networkidle", timeout=60000)
        return self

    def _load_cookies(self):
        """加载 cookies.json 和 local_storage.json 中的登录态

        如果文件不存在则跳过——首次使用需要先运行 tools/save_cookies.py。
        """
        if not COOKIES_FILE.exists():
            print("[INFO] cookies.json not found, will use fresh login")
            return

        try:
            with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            self.context.add_cookies(cookies)
            print(f"[INFO] Loaded {len(cookies)} cookies")
        except Exception as e:
            print(f"[WARN] Failed to load cookies: {e}")

        # 加载 localStorage（部分登录态保存在这里）
        local_storage_file = PROJECT_DIR / "local_storage.json"
        if local_storage_file.exists():
            try:
                with open(local_storage_file, 'r', encoding='utf-8') as f:
                    local_storage = json.load(f)
                self.page.evaluate("""(items) => {
                    for (let key in items) {
                        localStorage.setItem(key, items[key]);
                    }
                }""", local_storage)
                print(f"[INFO] Loaded {len(local_storage)} localStorage items")
            except Exception as e:
                print(f"[WARN] Failed to load localStorage: {e}")

    def is_logged_in(self):
        """检测是否已登录豆包

        策略：检查页面是否还显示"登录"按钮。
        - 已登录 → 找不到"登录"按钮（被头像/账户区替代）
        - 未登录 → 能找到"登录"按钮
        """
        try:
            self.page.wait_for_selector('text="登录"', timeout=3)
            return False  # 找到了，说明未登录
        except Exception:
            return True  # 没找到"登录"按钮，说明已登录

    def wait_for_input_box(self):
        """等待输入框出现"""
        return self.page.wait_for_selector('textarea.semi-input-textarea', timeout=10000)

    def send_message(self, message):
        """发送一条消息到当前对话"""
        textarea = self.wait_for_input_box()
        textarea.fill(message)
        # 清空输入框防止重复触发（双保险）
        textarea.evaluate("this.value = ''")
        textarea.press('Enter')
        self._message_sent = False

    def upload_file(self, file_path):
        """上传本地文件到豆包

        Args:
            file_path: 本地文件绝对路径

        Returns:
            bool: 是否成功触发上传
        """
        if not os.path.exists(file_path):
            print(f"[FAIL] File not found: {file_path}")
            return False

        try:
            # 1. 点击回形针上传按钮
            upload_btn = self.page.query_selector('button:has(svg path[d*="M17.3977"])')
            if not upload_btn:
                print("[FAIL] Upload button not found")
                return False

            upload_btn.click()
            time.sleep(0.5)
            print(f"[INFO] Upload button clicked")

            # 2. 查找弹出的 file input
            file_input = self.page.query_selector('input[type="file"]')
            if not file_input:
                print("[FAIL] File input not found")
                return False

            # 3. 注入文件
            file_input.set_input_files(file_path)
            print(f"[OK] File uploaded: {os.path.basename(file_path)}")
            return True

        except Exception as e:
            print(f"[FAIL] Upload failed: {e}")
            return False

    def detect_captcha(self):
        """检测页面是否出现验证码"""
        try:
            page_text = self.page.inner_text('body')
            captcha_markers = ['验证码', '验证', 'captcha', '人机验证', '安全验证']
            return any(marker in page_text for marker in captcha_markers)
        except Exception:
            return False

    def wait_for_reply(self, timeout=180):
        """等待豆包回复完成

        阶段性智能检测：
        - 阶段 1：等待响应（10 秒超时）—— 等待"内容由豆包 AI 生成"等标记出现
        - 阶段 2：输出阶段（流式更新）—— 每秒检测内容变化，
                  连续 N 秒无变化则视为输出完成

        验证码处理：检测到验证码时若 keep_open=True 则自动循环等待；
        否则暂停等待用户手动处理。

        Returns:
            tuple: (success, reply_text)
        """
        markers = ["内容由豆包 AI 生成", "快速", "图像生成"]
        WAIT_RESPONSE_TIMEOUT = 10      # 阶段 1 超时
        OUTPUT_IDLE_TIMEOUT = 15        # 阶段 2 多少秒无变化视为结束

        # ===== 阶段 1: 等待响应 =====
        print(f"[INFO] 阶段1: 等待响应... (超时:{WAIT_RESPONSE_TIMEOUT}s)")
        phase = "waiting_response"
        elapsed = 0
        markers_seen = 0
        page_text = ""
        last_output_len = 0
        output_idle_count = 0
        last_output_time = time.time()

        while elapsed < timeout:
            time.sleep(1)
            elapsed += 1

            # 检查浏览器/页面状态
            try:
                if self.context is None:
                    print("[WARN] Browser closed")
                    break
                page_text = self.page.inner_text('body')
            except Exception as e:
                print(f"[WARN] Browser/page error: {e}")
                break

            # 验证码自动等待
            if self.detect_captcha():
                print("[WARN] 检测到验证码！暂停等待...")
                self.page.screenshot(path=str(PROJECT_DIR / "captcha.png"))
                while self.detect_captcha() and elapsed < timeout:
                    time.sleep(1)
                    elapsed += 1
                print("[INFO] 验证码已处理，继续...")

            # 检测标记数量
            markers_found = sum(1 for m in markers if m in page_text)
            if markers_found > markers_seen:
                markers_seen = markers_found
                print(f"[INFO] 标记: {markers_found}/{len(markers)}")

            # ===== 阶段 1 -> 阶段 2 转换 =====
            if phase == "waiting_response":
                if markers_seen >= 1:
                    print("[INFO] 响应开始，进入阶段2: 输出阶段")
                    phase = "output"
                    last_output_time = time.time()
                    last_output_len = len(page_text)
                    output_idle_count = 0
                else:
                    print(f"[INFO] 等待中... {elapsed}/{WAIT_RESPONSE_TIMEOUT}s")
                    continue

            # ===== 阶段 2: 输出阶段 =====
            if phase == "output":
                current_len = len(page_text)
                text_changed = (current_len != last_output_len)

                if text_changed:
                    delta = current_len - last_output_len
                    print(f"[INFO] 输出中... +{delta} 字符 (共 {current_len})")
                    last_output_len = current_len
                    last_output_time = time.time()
                    output_idle_count = 0
                else:
                    output_idle_count += 1
                    idle_time = int(time.time() - last_output_time)
                    print(f"[INFO] 等待输出完成... {idle_time}s 无变化 ({output_idle_count}/{OUTPUT_IDLE_TIMEOUT})")

                # 完成判定：至少 2 个标记 + 连续 OUTPUT_IDLE_TIMEOUT 秒无变化
                if markers_seen >= 2 and output_idle_count >= OUTPUT_IDLE_TIMEOUT:
                    print("[INFO] 输出完成，提取内容...")
                    reply = self._extract_reply(page_text)
                    if reply and len(reply.strip()) >= 5:
                        print(f"[OK] 回复完成 ({len(reply)} 字符)")
                        return True, reply
                    else:
                        # 备用提取策略
                        print("[INFO] 尝试备用提取...")
                        if "内容由豆包 AI 生成" in page_text:
                            idx = page_text.index("内容由豆包 AI 生成")
                            reply = page_text[idx + 10:].strip()
                            for m in markers:
                                if m in reply:
                                    reply = reply[:reply.index(m)].strip()
                            if len(reply) >= 5:
                                return True, reply

                # 超时前最后尝试一次
                if elapsed >= timeout - 10 and markers_seen >= 1:
                    print(f"[WARN] 超时前强制提取...")
                    reply = self._extract_reply(page_text)
                    if reply and len(reply.strip()) >= 5:
                        return True, reply

        # 超时或浏览器关闭
        print(f"[WARN] 等待结束 (elapsed:{elapsed}s, markers:{markers_seen})")
        if markers_seen >= 1:
            reply = self._extract_reply(page_text)
            if reply and len(reply.strip()) >= 5:
                print(f"[OK] 提取到内容 ({len(reply)} 字符)")
                return True, reply

        print(f"[FAIL] 超时，markers: {markers_seen}/{len(markers)}")
        return False, ""

    def _extract_reply(self, page_text):
        """从完整页面文本中提取当前对话的回复内容（去除 UI 框架和历史记录）"""
        lines = page_text.split('\n')
        result = []
        in_conversation = False

        # UI 元素黑名单（这些是页面侧边栏/导航/按钮等非对话内容）
        skip_patterns = ['新对话', 'AI 创作', '云盘', '更多', '历史对话',
                        '快速', '图像生成', '超能模式', 'Beta', 'PPT 生成',
                        '帮我写作', '内容由豆包 AI 生成', '豆包',
                        '手机版对话']

        # 历史对话标题特征（短、可能是项目符号）
        skip_chars = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 跳过 UI 元素
            if any(pattern in line for pattern in skip_patterns):
                continue

            # 跳过纯数字和项目符号开头的历史记录
            if line.isdigit():
                continue
            if len(line) <= 15 and any(line.startswith(c) for c in skip_chars):
                continue

            # 检测是否到达当前回复区域（"内容由豆包 AI 生成"之后）
            if '内容由豆包 AI 生成' in line:
                in_conversation = True
                continue

            # 在对话区域内，只保留有实质内容的行
            if in_conversation:
                if len(line) < 3:
                    continue
                result.append(line)

        # 如果没找到特定区域，返回过滤后的全部内容
        if not result:
            for line in lines:
                line = line.strip()
                if len(line) < 5:
                    continue
                if any(pattern in line for pattern in skip_patterns):
                    continue
                result.append(line)

        return '\n'.join(result)

    def get_conversations(self):
        """获取左侧对话列表

        Returns:
            list: [{'index': int, 'title': str, 'element': ElementHandle}, ...]
        """
        try:
            history_btn = self.page.query_selector('text="历史对话"')
            if history_btn:
                history_btn.click()
                time.sleep(1)
        except Exception:
            pass

        time.sleep(1)

        items = self.page.query_selector_all('[data-testid="chat_list_thread_item"]')
        conversations = []
        for i, item in enumerate(items):
            title = item.inner_text().split('\n')[0]
            conversations.append({'index': i, 'title': title, 'element': item})

        return conversations

    def switch_to_conversation(self, target):
        """切换到指定对话

        Args:
            target: 索引(int) 或 标题(str，模糊匹配)

        Returns:
            bool: 是否切换成功
        """
        convs = self.get_conversations()
        if not convs:
            print("[WARN] No conversations found")
            return False

        if isinstance(target, int):
            if 0 <= target < len(convs):
                conv = convs[target]
            else:
                print(f"[FAIL] Invalid index {target}, range: 0-{len(convs)-1}")
                return False
        else:
            matches = [c for c in convs if target in c['title']]
            if not matches:
                print(f"[FAIL] No conversation with: {target}")
                return False
            conv = matches[0]

        conv['element'].click()
        time.sleep(2)
        print(f"[OK] Switched to: {conv['title']}")
        return True

    def create_new_conversation(self):
        """创建新对话

        Returns:
            bool: 是否成功创建
        """
        try:
            new_conv_btn = self.page.query_selector('text="新对话"')
            if new_conv_btn:
                new_conv_btn.click()
                time.sleep(2)
                print("[OK] 新对话已创建")
                return True
            else:
                print("[FAIL] 未找到新对话按钮")
                return False
        except Exception as e:
            print(f"[FAIL] 创建新对话失败: {e}")
            return False

    def read_current_conversation(self):
        """读取当前对话内容"""
        page_text = self.page.inner_text('body')
        return self._extract_reply(page_text)

    def read_conversations_preview(self, n=5):
        """读取前 n 个对话的预览内容

        Args:
            n: 读取前几个对话，默认 5

        Returns:
            list: [{'index', 'title', 'content', 'preview'}, ...]
        """
        convs = self.get_conversations()
        if not convs:
            print("[WARN] No conversations found")
            return []

        results = []
        current_title = None
        try:
            current_title = convs[0]['title'] if convs else None
        except Exception:
            pass

        # 只读取前 n 个
        for i, conv in enumerate(convs[:n]):
            title = conv['title']
            print(f"[INFO] 读取对话 {i}: {title}...")

            conv['element'].click()
            time.sleep(1.5)

            content = self.read_current_conversation()
            preview = content[:200] + "..." if len(content) > 200 else content

            results.append({
                'index': i,
                'title': title,
                'content': content,
                'preview': preview
            })

            print(f"[INFO] 获取到 {len(content)} 字符")

        # 切回第一个对话
        if current_title:
            self.switch_to_conversation(0)
            print(f"[INFO] 已返回对话: {current_title}")

        return results

    def interactive_select(self):
        """交互式选择对话（命令行提示输入序号或标题）

        Returns:
            bool: 是否成功选择
        """
        convs = self.get_conversations()
        if not convs:
            print("[WARN] No conversations found")
            return False

        print("\n=== 选择对话 ===")
        for c in convs:
            print(f"  [{c['index']}] {c['title']}")
        print("  [q] 取消")

        choice = input("\n请输入序号: ").strip()
        if choice.lower() == 'q':
            print("[CANCEL] 取消选择")
            return False

        try:
            idx = int(choice)
            if 0 <= idx < len(convs):
                self.switch_to_conversation(idx)
                return True
            else:
                print(f"[FAIL] 序号 {idx} 超出范围")
                return False
        except ValueError:
            if self.switch_to_conversation(choice):
                return True
            print(f"[FAIL] 无法识别: {choice}")
            return False

    def interactive_choose_conversation(self):
        """交互式选择：创建新对话还是使用旧对话

        流程：打开浏览器 → 列出对话 → 用户选择 → 返回结果
        """
        self.launch()
        if not self.is_logged_in():
            print("[FAIL] Not logged in")
            return None

        print("\n=== 选择对话 ===")
        convs = self.get_conversations()

        print(f"\n发现 {len(convs)} 个对话：")
        for c in convs:
            print(f"  [{c['index']}] {c['title']}")
        print("  [n] 创建新对话")
        print("  [q] 取消")

        while True:
            choice = input("\n请选择: ").strip().lower()

            if choice == 'q':
                print("[CANCEL] 取消")
                return None

            if choice == 'n':
                print("[INFO] 创建新对话...")
                try:
                    new_conv_btn = self.page.query_selector('text="新对话"')
                    if new_conv_btn:
                        new_conv_btn.click()
                        time.sleep(2)
                        print("[OK] 新对话已创建")
                        return "new"
                    else:
                        print("[WARN] 未找到新对话按钮")
                except Exception as e:
                    print(f"[WARN] 创建新对话失败: {e}")
                return None

            try:
                idx = int(choice)
                if 0 <= idx < len(convs):
                    self.switch_to_conversation(idx)
                    return convs[idx]['title']
                else:
                    print(f"[FAIL] 序号 {idx} 超出范围 (0-{len(convs)-1})")
            except ValueError:
                print("[FAIL] 请输入序号或 n/q")

    def interactive_select_and_send(self, message):
        """选择对话并发送消息

        Args:
            message: 要发送的消息

        Returns:
            tuple: (success, reply_text) 或 (None, None) 如果取消
        """
        result = self.interactive_choose_conversation()
        if result is None:
            return None, None

        if result == "new":
            conv_title = "新对话"
        else:
            conv_title = result

        print(f"\n[INFO] 在「{conv_title}」中发送消息...")
        self.send_message(message)
        print("[INFO] 等待回复...")

        success, reply = self.wait_for_reply()

        if success:
            print(f"\n=== 豆包回复 ===\n{reply}\n")
        else:
            print("\n[WARN] 未收到有效回复")

        return success, reply

    def interactive_chat(self):
        """交互式聊天（不关闭浏览器，持续对话）

        流程：
        1. 选择对话
        2. 输入消息
        3. 发送并等待回复
        4. 循环或退出（输入 q 退出，s 切换对话）
        """
        self.launch()
        if not self.is_logged_in():
            print("[FAIL] Not logged in")
            return

        print("\n=== 豆包自动化 - 交互模式 ===")
        print("浏览器已打开，可以随时查看")
        print("输入 q 退出，输入 s 切换对话\n")

        current_conv = None

        while True:
            if current_conv is None:
                print("\n--- 选择对话 ---")
                if self.interactive_select():
                    convs = self.get_conversations()
                    current_conv = convs[0]['title'] if convs else None
                else:
                    continue

            print(f"\n[当前对话: {current_conv}]")
            print("输入 q 退出，输入 s 切换对话")
            message = input("请输入消息: ").strip()

            if message.lower() == 'q':
                print("\n[BYE] 再见！")
                break

            if message.lower() == 's':
                current_conv = None
                continue

            if not message:
                print("[WARN] 消息不能为空")
                continue

            print("\n[INFO] 发送中...")
            self.send_message(message)
            print("[INFO] 等待回复...")

            success, reply = self.wait_for_reply()

            if success:
                print(f"\n=== 豆包回复 ===\n{reply}\n")
            else:
                print("\n[WARN] 未收到有效回复")

    def save_conversation(self, title, reply=""):
        """保存当前对话到 Markdown 文件"""
        safe_title = title[:20].replace('/', '_').replace('\\', '_').replace(':', '_')
        filename = f"conversation_{safe_title}.md"
        filepath = PROJECT_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            if reply:
                f.write(f"## 最新回复\n\n{reply}\n\n")
            f.write("---\n")

        print(f"[OK] Saved to: {filename}")
        return filepath

    def get_current_url(self):
        """获取当前页面的 URL（对话 URL）"""
        return self.page.url

    def save_conversation_url(self, title=None):
        """保存当前对话 URL 到本地 conversations.json

        为什么要存 URL：每次启动浏览器默认是新对话，
        通过 URL 跳转可以恢复到历史对话。

        Args:
            title: 对话标题（可选，不传则尝试从页面推断）

        Returns:
            str: 保存的 URL
        """
        url = self.get_current_url()

        if not title:
            try:
                page_text = self.page.inner_text('body')
                lines = page_text.split('\n')
                for line in lines[:10]:
                    line = line.strip()
                    if line and len(line) > 2 and len(line) < 50:
                        title = line
                        break
            except Exception:
                title = "未命名对话"

        convos = []
        if CONVERSATIONS_FILE.exists():
            try:
                with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                    convos = json.load(f)
            except Exception:
                convos = []

        # 检查是否已存在
        for c in convos:
            if c['url'] == url:
                c['title'] = title
                break
        else:
            convos.append({
                'title': title,
                'url': url,
                'saved_at': time.strftime('%Y-%m-%d %H:%M:%S')
            })

        with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(convos, f, ensure_ascii=False, indent=2)

        print(f"[OK] URL已保存: {title}")
        print(f"     {url}")
        return url

    def get_saved_conversations(self):
        """获取本地保存的所有对话 URL"""
        if not CONVERSATIONS_FILE.exists():
            return []
        try:
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def goto_conversation_by_url(self, url):
        """通过 URL 直接跳转到指定对话"""
        try:
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            time.sleep(2)
            print(f"[OK] 已跳转到: {url}")
            return True
        except Exception as e:
            print(f"[FAIL] 跳转失败: {e}")
            return False

    def switch_to_saved_conversation(self, index_or_title):
        """跳转到已保存的对话

        Args:
            index_or_title: 索引(int) 或 标题(str)
        """
        convos = self.get_saved_conversations()
        if not convos:
            print("[WARN] 没有已保存的对话")
            return False

        if isinstance(index_or_title, int):
            if 0 <= index_or_title < len(convos):
                target = convos[index_or_title]
            else:
                print(f"[FAIL] 索引超出范围 (0-{len(convos)-1})")
                return False
        else:
            matches = [c for c in convos if index_or_title in c['title']]
            if not matches:
                print(f"[FAIL] 未找到包含 '{index_or_title}' 的对话")
                return False
            target = matches[0]

        return self.goto_conversation_by_url(target['url'])

    def close(self):
        """关闭浏览器和 Playwright"""
        try:
            if self.context:
                self.context.close()
        except Exception as e:
            print(f"[WARN] Close context error: {e}")
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            print(f"[WARN] Stop playwright error: {e}")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False


def send(conv_title, message):
    """快速发送消息（切换对话 + 发送 + 等待回复）

    Args:
        conv_title: 对话标题（模糊匹配），传空字符串则在当前对话发送
        message: 要发送的消息
    """
    with DoubaoBrowser() as browser:
        browser.launch()

        if not browser.is_logged_in():
            print("[FAIL] Not logged in")
            return

        browser._message_sent = False

        if conv_title:
            browser.switch_to_conversation(conv_title)

        browser.send_message(message)
        print(f"[INFO] Waiting for reply...")

        success, reply = browser.wait_for_reply()

        if success:
            print(f"\n豆包回复:\n{reply}")
            browser.save_conversation(conv_title or "未命名", reply)
        else:
            print("[WARN] No reply received")

        return reply


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='豆包浏览器自动化')
    parser.add_argument('action', choices=['send', 'list', 'switch', 'save'],
                        help='操作类型')
    parser.add_argument('target', nargs='?', help='对话标题或索引')
    parser.add_argument('message', nargs='?', help='消息内容（send 时需要）')

    args = parser.parse_args()

    with DoubaoBrowser() as browser:
        browser.launch()

        if args.action == 'list':
            convs = browser.get_conversations()
            print("\n=== 对话列表 ===")
            for c in convs:
                print(f"  [{c['index']}] {c['title']}")

        elif args.action == 'switch':
            if args.target:
                try:
                    idx = int(args.target)
                    browser.switch_to_conversation(idx)
                except ValueError:
                    browser.switch_to_conversation(args.target)

        elif args.action == 'send':
            conv = args.target or ""
            msg = args.message or ""
            if not msg:
                print("[FAIL] Message required")
            else:
                if conv:
                    browser.switch_to_conversation(conv)
                browser.send_message(msg)
                success, reply = browser.wait_for_reply()
                if success:
                    print(f"\n豆包回复:\n{reply}")

        elif args.action == 'save':
            if args.target:
                browser.switch_to_conversation(args.target)
            time.sleep(2)
            browser.save_conversation(args.target or "未命名")
