# 使用文档

> 本文档讲解 `doubao-playwright-skill` 的所有功能与 API。

---

## 目录

- [快速开始](#快速开始)
- [核心类 DoubaoBrowser](#核心类-doubaobrowser)
- [交互式控制器](#交互式控制器-recommended)
- [常用 API 一览](#常用-api-一览)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 快速开始

### 1. 准备

确保已完成 [SETUP.md](SETUP.md) 的所有步骤：
- ✅ 安装依赖
- ✅ 运行 `python tools/save_cookies.py` 保存登录态

### 2. 第一次运行

```python
import sys
import io

# Windows 中文输出修复
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 引入项目（假设当前在项目根目录）
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doubao_core import DoubaoBrowser

# 启动 + 提问 + 拿回复
browser = DoubaoBrowser(keep_open=True)
browser.launch()
browser.send_message("你好豆包")
success, reply = browser.wait_for_reply(timeout=180)
if success:
    print("豆包说：", reply)
browser.close()
```

---

## 核心类 DoubaoBrowser

### 初始化

```python
DoubaoBrowser(headless=False, keep_open=False)
```

**参数：**
- `headless`：是否无头模式（默认 `False`）。有头模式可以看到浏览器窗口，方便调试；无头模式更快但无法可视化。
- `keep_open`：浏览器启动后是否保持打开（默认 `False`）。建议设为 `True` 以减少反复开关触发人机验证。

**环境变量：**
- `KEEP_BROWSER=true`：等价于 `keep_open=True`

### launch()

```python
browser.launch() -> self
```

启动浏览器并打开豆包。

**自动完成：**
1. 关闭可能冲突的 Chrome 进程
2. 启动 Chromium（使用项目自带的 `browser_profile/` 目录）
3. 加载 `cookies.json` 和 `session.json`（如果存在）
4. 跳转到 `https://www.doubao.com/chat/`

**返回：** `self`（支持链式调用）

### is_logged_in()

```python
browser.is_logged_in() -> bool
```

检测当前是否已登录。

**判定逻辑：** 检查页面是否还有"登录"按钮。
- 找不到"登录"按钮 → 已登录
- 找到"登录"按钮 → 未登录

### send_message(message)

```python
browser.send_message("你的问题")
```

向当前对话发送一条文本消息。

**行为细节：**
- 发送前调用 `wait_for_input_box()`，最多等 10 秒输入框出现
- `textarea.fill(message)` 后通过 JS 把 value 清空再按 Enter（防止某些场景下重复触发）
- 不会等待回复，需自行调用 `wait_for_reply()`

### wait_for_reply(timeout=180)

```python
success, reply = browser.wait_for_reply(timeout=180)
```

等待豆包回复完成。

**参数：**
- `timeout`：最长等待时间（秒），默认 180

**返回：** `(success, reply)`
- `success`：是否成功拿到回复
- `reply`：回复内容（如果失败则为空字符串）

**两阶段检测机制：**
- **阶段 1（等待响应）**：10 秒内等待"内容由豆包 AI 生成"等标记出现
- **阶段 2（流式输出）**：标记出现后进入流式检测，连续 15 秒无变化视为输出完成

**完成判定：** 至少 2 个标记 + 连续 15 秒无变化。

**验证码处理：** 检测到验证码时若 `keep_open=True` 则自动循环等待；否则截图到 `captcha.png` 暂停等用户处理。

### upload_file(file_path)

```python
browser.upload_file(r"D:\papers\thesis.pdf")
```

上传本地文件到豆包。

**实现：** 点击回形针按钮 → 等待 `input[type="file"]` 出现 → 注入文件。

**返回：** `bool`，是否成功触发上传（不是"豆包已分析完"）。

**注意：**
- 上传后需要手动调用 `send_message()` 触发分析
- 依赖 SVG path 选择器 `M17.3977` 定位回形针按钮，豆包前端改版可能失效
- 文件不存在时直接返回 False

### get_conversations()

```python
convs = browser.get_conversations()
# [{'index': 0, 'title': '对话1', 'element': ElementHandle}, ...]
```

获取左侧对话列表。

**返回：** 列表，每个元素包含 `index`、`title`、`element`（Playwright ElementHandle）。

### switch_to_conversation(target)

```python
browser.switch_to_conversation(0)            # 按索引
browser.switch_to_conversation("我的论文")     # 按标题（模糊匹配）
```

切换到指定对话。

### create_new_conversation()

```python
browser.create_new_conversation()
```

点击"新对话"按钮创建新对话。

### read_current_conversation()

```python
content = browser.read_current_conversation()
print(content)
```

读取当前对话的纯文本内容（去除 UI 框架）。

### read_conversations_preview(n=5)

```python
previews = browser.read_conversations_preview(n=5)
for p in previews:
    print(f"### {p['title']}\n{p['preview']}\n")
```

读取前 n 个对话的预览内容。

### URL 管理

每次启动浏览器默认是"新对话"，左侧历史列表经常拿不到。**想恢复历史对话，用 URL 持久化：**

```python
# 保存当前对话的 URL 到 conversations.json
browser.save_conversation_url("我的论文讨论")

# 列出已保存的对话
convos = browser.get_saved_conversations()
for i, c in enumerate(convos):
    print(f"[{i}] {c['title']} - {c['url']}")

# 跳转到已保存的对话
browser.switch_to_saved_conversation(0)            # 按索引
browser.switch_to_saved_conversation("我的论文")     # 按标题（模糊匹配）
```

**注意：** `save_conversation_url(title)` 的 title 不传时会从页面正文前 10 行猜一个，不一定准。

---

## 交互式控制器

不想写代码？直接用交互式命令行：

```bash
python doubao_controller.py
```

### 命令一览

| 命令 | 说明 |
|------|------|
| `new` | 创建新对话 |
| `list` | 列出所有对话 |
| `switch <n>` / `switch <标题>` | 切换对话 |
| `read [n]` | 读取当前对话（或前 n 个的预览） |
| `current` | 显示当前对话标题 + URL |
| `saveurl` | 保存当前对话 URL |
| `urllist` | 列出已保存的 URL |
| `url <n>` / `url <标题>` | 跳转到已保存的对话 |
| `send <消息>` | 发送消息 |
| `upload <路径>` | 上传文件 |
| `screenshot` | 截图保存到 `screenshots/` |
| `save` | 保存当前对话为 Markdown |
| `help` | 显示帮助 |
| `q` / `quit` | 退出 |

---

## 实践建议

### 一次启动，多次操作

```python
# 推荐：保持浏览器打开
browser = DoubaoBrowser(keep_open=True)
browser.launch()

browser.send_message("任务1")
browser.wait_for_reply()

browser.switch_to_conversation(3)
browser.send_message("任务2")
browser.wait_for_reply()

browser.upload_file("report.pdf")
browser.send_message("分析这个文件")
browser.wait_for_reply()

browser.close()  # 只关一次
```

### 避免反复开关

```python
# 不推荐：每次操作都创建新浏览器
for task in tasks:
    browser = DoubaoBrowser()
    browser.launch()
    browser.send_message(task)
    browser.close()  # 反复开关会触发人机验证
```

### 处理验证码

如果脚本检测到验证码：
- 默认会暂停并截图到 `captcha.png`
- 在浏览器中手动完成验证
- 完成后脚本会自动继续

### 文件上传后

上传文件后**必须再调用 `send_message()`** 才会让豆包开始分析。

```python
browser.upload_file("file.pdf")
import time; time.sleep(1)  # 等待上传完成
browser.send_message("请分析这个文件")
```

---

## 常见问题

### Q：消息发不出去？

检查输入框是否加载完成。`send_message()` 内部会调用 `wait_for_input_box()`，最多等 10 秒。

### Q：回复检测不到 / 超时？

确认页面是否包含以下标记：
- `"内容由豆包 AI 生成"`
- `"快速"`
- `"图像生成"`

豆包网页结构可能更新，如果这些标记改变了，需要修改 `doubao_core.py` 中的 `markers` 列表（在 `wait_for_reply` 方法里）。

### Q：触发人机验证？

1. 用 `keep_open=True` 减少开关
2. 等待 5~10 分钟再试
3. 手动完成验证

### Q：能 headless 模式跑吗？

可以：

```python
browser = DoubaoBrowser(headless=True)
```

但首次登录必须用有头模式（`tools/save_cookies.py`）。

### Q：怎么调试？

```python
browser = DoubaoBrowser(keep_open=True)
browser.launch()  # 浏览器会保持打开
# ... 你的代码 ...
# 任何时候可以查看当前状态
print("URL:", browser.get_current_url())
print("标题:", browser.get_conversations()[0]['title'])
# 截图
browser.page.screenshot(path="debug.png")
```

---

## 进阶：嵌入到其他项目

整个项目可以作为一个 Python 模块嵌入：

```python
# 假设 doubao-playwright-skill/ 在你的项目下
import sys
sys.path.insert(0, "path/to/doubao-playwright-skill")

from doubao_core import DoubaoBrowser

# 现在可以用 DoubaoBrowser 了
browser = DoubaoBrowser(keep_open=True)
# ... 你的逻辑 ...
```

或者打成 zip 直接 `sys.path.insert` 进去，无需安装。
