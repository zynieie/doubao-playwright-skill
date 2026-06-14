# Doubao Playwright Skill

> 通过 Playwright 自动化控制豆包 AI 网页端 —— 消息收发、文件上传、对话管理、URL 持久化。

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40%2B-green)](https://playwright.dev/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

## 项目简介

`doubao-playwright-skill` 是一个用 **Playwright + Python** 实现的豆包 AI 浏览器自动化工具。它通过控制一个真实的 Chromium 浏览器，调用豆包网页端：

- 自动发送消息并等待流式回复
- 上传文件让豆包分析（论文、报告、合同等）
- 管理历史对话：列出、切换、读取、归档
- 保存重要对话的 URL，下次启动直接跳转
- 检测页面是否出现验证码
- 使用独立 Profile 目录，不污染用户 Chrome

适用场景：批量文件分析、历史对话归档、把豆包塞进自己的脚本或 CLI。

> **免责声明**：本项目**与字节跳动/豆包官方没有任何关联**，仅作为个人效率工具开源分享。请遵守豆包用户协议，不要用于违法违规用途。

---

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/<your-username>/doubao-playwright-skill.git
cd doubao-playwright-skill
pip install -r requirements.txt
playwright install chromium
```

### 2. 登录并保存 Cookies（只需做一次）

```bash
python tools/save_cookies.py
```

脚本会打开一个浏览器窗口 → **手动登录豆包** → 检测到登录成功后自动保存 `cookies.json` + `session.json` → 关闭浏览器。

> 详细说明见 [docs/COOKIE_GUIDE.md](docs/COOKIE_GUIDE.md)

### 3. 开始使用

**方式 A：交互式控制器（推荐）**
```bash
python doubao_controller.py
```
然后输入命令：`list` / `switch 0` / `send 你好` / `upload file.pdf` / `q`

**方式 B：Python 脚本调用**
```python
import sys, io
sys.path.insert(0, '.')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from doubao_core import DoubaoBrowser

browser = DoubaoBrowser(keep_open=True)
browser.launch()
browser.send_message("你好豆包")
success, reply = browser.wait_for_reply(timeout=180)
if success:
    print(reply)
browser.close()
```

完整示例见 [examples/](examples/)，详细 API 见 [docs/USAGE.md](docs/USAGE.md)。

---

## 目录结构

```
doubao-playwright-skill/
├── README.md                 # 本文件
├── LICENSE                   # Apache-2.0 许可证
├── requirements.txt          # Python 依赖
├── .gitignore                # git 忽略规则
├── cookies.example.json      # cookies 模板（脱敏）
│
├── doubao_core.py            # 核心库：DoubaoBrowser 类
├── doubao_controller.py      # 交互式控制器（推荐入口）
├── doubao_bot.py             # 早期版本主脚本（保留兼容）
├── doubao_manager.py         # 轻量版对话管理器
├── quick_send.py             # 命令行快速发送
│
├── docs/
│   ├── SETUP.md              # 详细安装与配置
│   ├── USAGE.md              # 完整使用文档
│   └── COOKIE_GUIDE.md       # Cookie 获取详解
│
├── examples/
│   └── basic_chat.py         # 极简示例
│
├── tools/
│   └── save_cookies.py       # 一键登录保存 cookies
│
└── assets/                   # 截图、徽章等
```

---

## 核心能力一览

| 功能 | 方法 | 说明 |
|------|------|------|
| 启动浏览器 | `browser.launch()` | 自动加载 cookies |
| 发送消息 | `browser.send_message(text)` | 文字消息 |
| 等待回复 | `browser.wait_for_reply(timeout=180)` | 流式检测，默认 180 秒超时 |
| 上传文件 | `browser.upload_file(path)` | 走回形针按钮 |
| 列出对话 | `browser.get_conversations()` | 返回带 Element 的列表 |
| 切换对话 | `browser.switch_to_conversation(idx_or_title)` | 按序号或模糊标题 |
| 创建对话 | `browser.create_new_conversation()` | 点击"新对话"按钮 |
| 读取对话 | `browser.read_current_conversation()` | 提取纯文本 |
| 批量预览 | `browser.read_conversations_preview(n=5)` | 前 n 个对话的预览 |
| 保存 URL | `browser.save_conversation_url(title)` | 重要对话标记 |
| 跳转 URL | `browser.switch_to_saved_conversation(idx_or_title)` | 跨会话恢复 |

详细 API 见 [docs/USAGE.md](docs/USAGE.md)

---

## 典型使用场景

### 场景 1：让豆包分析一个 PDF
```python
from doubao_core import DoubaoBrowser

browser = DoubaoBrowser(keep_open=True)
browser.launch()
browser.upload_file(r"D:\papers\thesis.pdf")
browser.send_message("请总结这篇论文的核心贡献")
success, reply = browser.wait_for_reply(timeout=300)
print(reply)
browser.close()
```

### 场景 2：批量读取历史对话归档
```python
browser = DoubaoBrowser(keep_open=True)
browser.launch()

# 读取前 10 个对话的预览
previews = browser.read_conversations_preview(n=10)
for p in previews:
    print(f"### {p['title']}\n{p['preview']}\n")

browser.close()
```

### 场景 3：跨会话恢复重要对话
```python
# 第一次：保存重要对话的 URL
browser.save_conversation_url("我的毕业论文讨论")

# 下次启动：直接跳过去
browser.switch_to_saved_conversation("我的毕业论文讨论")
```

更多示例见 [examples/](examples/)

---

## 常见问题

### Q：登录后 cookies 过期了怎么办？
重新运行 `python tools/save_cookies.py`，覆盖 `cookies.json` 即可。

### Q：触发人机验证怎么办？
使用 `keep_open=True` 让浏览器保持打开状态，避免频繁开关。

### Q：能 headless 模式跑吗？
可以：`DoubaoBrowser(headless=True)`。但首次登录必须用有头模式。

### Q：怎么找到某个对话的标题？
```python
convs = browser.get_conversations()
for c in convs:
    print(f"[{c['index']}] {c['title']}")
```

### Q：能不能集成到其他项目？
可以。直接 `from doubao_core import DoubaoBrowser`，把整个目录作为模块引入即可。

更多问题见 [docs/USAGE.md](docs/USAGE.md) 的"常见问题"章节。

---

## 贡献

欢迎 PR / Issue。请注意：
- 提交前跑通基础示例 `examples/basic_chat.py`
- 改动核心库 `doubao_core.py` 时同步更新文档
- 新功能优先在 `tools/` 或 `examples/` 下加示例脚本

---

## License

本项目基于 **Apache-2.0 License** 开源，详见 [LICENSE](LICENSE)。

---

## 重要声明

1. **本项目与豆包/字节跳动官方没有任何关联**，仅作为个人效率工具开源分享。
2. 使用本工具请遵守[豆包用户协议](https://www.doubao.com/terms)及相关法律法规。
3. 自动化操作可能触发风控，请合理使用，不要高频请求。
4. 项目作者不对使用本工具产生的任何后果负责。
5. 豆包网页结构（DOM 选择器、按钮位置等）可能随时变化，本工具不保证长期可用。
