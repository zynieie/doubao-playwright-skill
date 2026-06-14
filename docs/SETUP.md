# 安装与设置指南

本文档讲解如何从零开始把 `doubao-playwright-skill` 跑起来。

---

## 1. 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10+ / macOS 10.15+ / Linux (主流发行版) |
| Python | 3.8 或更高 |
| 磁盘空间 | 约 500 MB（Playwright Chromium 浏览器） |
| 网络 | 能访问 `doubao.com` |

---

## 2. 安装步骤

### 2.1 克隆仓库

```bash
git clone https://github.com/<your-username>/doubao-playwright-skill.git
cd doubao-playwright-skill
```

> 如果你下载的是 zip 压缩包，解压后进入目录即可。

### 2.2 （推荐）创建虚拟环境

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2.3 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2.4 安装 Playwright 浏览器内核

```bash
playwright install chromium
```

这会下载约 200 MB 的 Chromium 浏览器。

> ⚠️ 跳过此步骤会报 `Executable doesn't exist` 错误。

### 2.5 验证安装

```bash
python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

应该输出 `OK`。

---

## 3. 首次登录（必须）

豆包的网页端需要登录才能使用。**登录态通过 cookies 保存**，本项目**不内置任何 cookies**——你需要登录自己的豆包账号并把 cookies 存到本地。

### 3.1 一键登录保存（推荐）

```bash
python tools/save_cookies.py
```

脚本会：
1. 启动一个 Chromium 浏览器窗口
2. 打开豆包登录页
3. **你在浏览器中手动登录**（扫码 / 手机号 / 微信 等）
4. 脚本检测到登录成功后，自动保存：
   - `cookies.json`（核心登录凭证）
   - `session.json`（localStorage 数据）
5. 关闭浏览器

整个过程 1~2 分钟。

### 3.2 手动登录保存（备选）

如果一键脚本有问题，可以手动从浏览器 DevTools 导出 cookies：

1. 在 Chrome 打开 `https://www.doubao.com/chat/` 并登录
2. 按 F12 打开 DevTools → Application 标签 → Cookies → `https://www.doubao.com`
3. 全选所有 cookies，复制为 JSON 数组格式
4. 粘贴到项目根目录的 `cookies.json` 中

格式参考 `cookies.example.json`：

```json
[
  {
    "name": "sessionid",
    "value": "xxx",
    "domain": ".doubao.com",
    "path": "/",
    "expires": -1,
    "httpOnly": true,
    "secure": false,
    "sameSite": "Lax"
  }
]
```

> 详细图文教程见 [COOKIE_GUIDE.md](COOKIE_GUIDE.md)

---

## 4. 验证一切就绪

运行最简示例：

```bash
python examples/basic_chat.py
```

如果看到类似下面的输出，说明一切正常：

```
[INFO] Loaded 24 cookies
[INFO] 阶段1: 等待响应... (超时:10s)
[INFO] 标记: 1/3
[INFO] 响应开始，进入阶段2: 输出阶段
[INFO] 输出中... +X 字符 (共 Y)
...
[OK] 回复完成 (Z 字符)

=== 豆包回复 ===
你好！我是豆包 AI...
```

---

## 5. 常见安装问题

### Q：`playwright install` 下载太慢 / 失败

可以设置镜像：

```bash
# 中国用户（使用清华镜像）
set PLAYWRIGHT_DOWNLOAD_HOST=https://mirrors.tuna.tsinghua.edu.cn/playwright  # Windows
export PLAYWRIGHT_DOWNLOAD_HOST=https://mirrors.tuna.tsinghua.edu.cn/playwright  # Linux/macOS

playwright install chromium
```

### Q：提示 `ModuleNotFoundError: No module named 'playwright'`

确认已激活虚拟环境，且 `pip install -r requirements.txt` 成功执行。

### Q：Windows 下中文输出乱码

在脚本开头加上：
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
```

### Q：macOS / Linux 下 `chrome` 相关报错

部分系统需要先安装系统级依赖：

```bash
# Ubuntu / Debian
sudo apt-get install libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2

# macOS（一般自带，但如果有权限问题）
xcode-select --install
```

---

## 下一步

- 📖 查看 [USAGE.md](USAGE.md) 学习所有 API 用法
- 🍪 查看 [COOKIE_GUIDE.md](COOKIE_GUIDE.md) 深入理解 Cookie 机制
- 🚀 运行 `python doubao_controller.py` 进入交互模式
