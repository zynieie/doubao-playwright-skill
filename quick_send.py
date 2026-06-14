"""
快速发送消息 - 命令行工具
切换到指定对话，发送一条消息，等回复后打印。

用法：
    python quick_send.py <对话标题> <消息内容>
    python quick_send.py "我的论文" "请帮我总结一下"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doubao_core import send


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python quick_send.py <对话标题> <消息>")
        print('Example: python quick_send.py "我的论文" "请帮我总结一下"')
        sys.exit(1)

    conv_title = sys.argv[1]
    message = sys.argv[2]
    send(conv_title, message)
