"""
基础示例：5 行代码向豆包提问并获取回复

用法：
    1. 确保已完成登录（python tools/save_cookies.py）
    2. python examples/basic_chat.py
"""
import os
import sys
import io

# Windows 中文输出修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 把项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from doubao_core import DoubaoBrowser

# === 1. 启动浏览器 ===
browser = DoubaoBrowser(keep_open=True)
browser.launch()

# === 2. 检查登录 ===
if not browser.is_logged_in():
    print("[FAIL] 未登录！请先运行: python tools/save_cookies.py")
    browser.close()
    sys.exit(1)

# === 3. 发送问题 ===
question = "用一句话介绍一下你自己"
print(f"[INFO] 提问: {question}")
browser.send_message(question)

# === 4. 等待回复 ===
print("[INFO] 等待回复...")
success, reply = browser.wait_for_reply(timeout=180)

# === 5. 打印结果 ===
if success:
    print()
    print("=" * 50)
    print(f"问: {question}")
    print("=" * 50)
    print(f"豆包: {reply}")
    print("=" * 50)
else:
    print("[WARN] 未收到有效回复")

# === 6. 关闭 ===
browser.close()
