# Cookie 获取指南

> 重要：**本项目不带任何 cookies.json**。你需要登录自己的豆包账号后，把登录态保存到 `cookies.json` 才能使用。

---

## 什么是 Cookies？为什么需要？

Cookies 是浏览器保存的"登录凭证"。当你登录豆包后，服务器给你的浏览器下发一组 cookies；下次访问时带上这些 cookies，服务器就知道"你已登录"。

本项目通过 Playwright 读取这些 cookies，让自动化脚本"伪装"成已登录的浏览器，从而操作你的豆包账号。

**安全提示：cookies.json 等同于你的账号密码，不要分享或上传到公共仓库。**

## 方法一：一键脚本（推荐）

```bash
python tools/save_cookies.py
```

脚本会：
1. 启动 Chromium 浏览器（有头模式）
2. 打开 `https://www.doubao.com/chat/`
3. **你手动登录**（扫码 / 手机号 / 微信 等）
4. 脚本每秒检测一次"登录"按钮是否消失
5. 检测到登录成功 → 自动保存 `cookies.json` + `session.json`
6. 关闭浏览器

整个流程约 1~2 分钟。

### 运行截图（文字版）

```
========================================
       豆包 Cookie 一键保存工具
========================================

[INFO] 启动浏览器...
[INFO] 等待你登录豆包...
[INFO] 请在打开的浏览器窗口中完成登录
[INFO] 登录成功后脚本会自动保存

  ✓ 等待登录中...（你可以去浏览器操作）

[INFO] 检测到登录成功！
[OK] cookies.json 已保存（24 个 cookie）
[OK] session.json 已保存（12 项 localStorage）
[INFO] 完成！可以关闭浏览器了。
```

---

## 方法二：手动导出（备选）

如果一键脚本有问题，可以手动从浏览器导出。

### 步骤 1：在 Chrome 登录豆包

打开 `https://www.doubao.com/chat/`，正常登录你的账号。

### 步骤 2：打开 DevTools

按 `F12` 打开开发者工具，切换到 `Application` 标签。

### 步骤 3：找到 Cookies

左侧树形菜单：`Storage` → `Cookies` → `https://www.doubao.com`

### 步骤 4：复制所有 cookies

**方法 A：用浏览器扩展**
- 安装 "EditThisCookie" 或 "Cookie-Editor" 扩展
- 一键导出为 JSON 格式

**方法 B：用代码获取完整 JSON 数组（推荐）**

在 Console 标签执行：

```js
(async () => {
  const cookies = await cookieStore.getAll();
  const json = JSON.stringify(cookies, null, 2);
  console.log(json);
  copy(json);
  alert("已复制 " + cookies.length + " 个 cookies 到剪贴板！");
})();
```

> 注意：部分浏览器的 `cookieStore` API 只返回非 httpOnly 的 cookies。对于本项目**非 httpOnly cookies 够用**（httpOnly cookies 通常仅用于服务端 API 调用）。

### 步骤 5：保存到 `cookies.json`

将复制的 JSON 粘贴到项目根目录的 `cookies.json` 文件中：

```json
[
  {
    "name": "sessionid",
    "value": "abc123...",
    "domain": ".doubao.com",
    "path": "/",
    "expires": 1735689600,
    "httpOnly": true,
    "secure": false,
    "sameSite": "Lax"
  },
  {
    "name": "uid",
    "value": "user_123",
    "domain": ".doubao.com",
    "path": "/",
    "expires": 1735689600,
    "httpOnly": false,
    "secure": false,
    "sameSite": "Lax"
  }
]
```

### 步骤 6：保存 localStorage（可选但推荐）

部分登录态保存在 localStorage 中。在 Console 执行：

```js
const items = {};
for (let i = 0; i < localStorage.length; i++) {
  const key = localStorage.key(i);
  items[key] = localStorage.getItem(key);
}
copy(JSON.stringify(items, null, 2));
alert("已复制 " + localStorage.length + " 项 localStorage！");
```

将复制的内容保存到 `session.json`。

---

## 常见问题

### Q：cookies 多久会过期？

豆包的登录 cookies 通常有效期为 **2~4 周**。具体取决于：
- 你的账号安全设置
- 是否有"信任设备"标记
- 是否主动登出过

### Q：脚本提示"登录成功"但下次启动还是未登录？

可能原因：
1. 浏览器提示"异地登录"被风控了 → 重新登录
2. cookies.json 没保存到正确位置 → 检查文件是否在项目根目录
3. localStorage 没保存（部分登录态在 session.json）→ 同时保存 session.json

### Q：触发"人机验证"怎么办？

1. 用 `keep_open=True` 让浏览器保持打开
2. 等待 5~10 分钟后再试
3. 在浏览器中手动完成验证（滑动拼图 / 点选字符）
4. 验证完成后重新运行 `tools/save_cookies.py`

### Q：能不能用我已登录的 Chrome 的 cookies？

技术上可以（通过 `get_user_chrome_path()` 路径），但：
- 需要关闭所有 Chrome 窗口
- 存在安全风险（cookies 是明文存储）
- 推荐用独立的 `browser_profile/` 目录（这是本项目默认方式）

### Q：cookies 会不会被项目作者收集？

**不会。** 整个 `tools/save_cookies.py` 是本地运行的纯客户端脚本，不连接任何外部服务器。`cookies.json` 也已在 `.gitignore` 中，不会被 git 跟踪。

### Q：登出后 cookies 还有效吗？

**无效。** 如果你在浏览器里点了"退出登录"，服务器会让当前 cookies 失效，需要重新登录保存。

---

## 安全建议

1. **不要把 `cookies.json` 提交到 git**（本项目已自动忽略）
2. **不要在公共电脑保存 cookies**
3. **不要把 cookies 发给任何人**（等同于账号密码）
4. **定期重新登录**以刷新 cookies
5. **如果怀疑泄露**，立即在豆包设置中"退出所有设备"

---

## 故障排查

如果登录检测脚本卡住或失败：

1. **检查网络**：能否访问 `https://www.doubao.com`
2. **检查 Chrome 进程**：确保没有其他 Chrome 窗口占用端口
3. **手动重试**：先 `taskkill /F /IM chrome.exe`（Windows）或 `pkill chrome`（Linux/macOS）
4. **查看 `login_status.png`**：脚本会截图当前状态，便于诊断
5. **降低检测超时**：编辑 `tools/save_cookies.py` 中的 `check_interval = 2` 改大一点

如果问题持续，请在 GitHub Issues 提交 bug，并附上：
- 操作系统 + Python 版本
- Playwright 版本
- 错误截图（`login_status.png`）
- 控制台完整输出
