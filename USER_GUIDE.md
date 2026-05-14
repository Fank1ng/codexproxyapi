# Codex Account Pool Proxy — 用户使用文档

## 项目简介

本地代理服务器，管理多个 ChatGPT Plus 账号组成号池，轮换使用并自动故障转移。配 Web 管理界面实时查看配额。

## 核心能力

| 功能 | 说明 |
|------|------|
| 号池轮换 | 多个 Plus 账号 round-robin 轮换，均匀消耗额度 |
| 自动故障转移 | 某账号触发 429 限流 → 60 秒冷却 → 自动切下一个 |
| Token 自动刷新 | 检测到 401 过期 → 用 refresh_token 换新 token |
| Web 管理面板 | 浏览器管理账号、查看配额、修改配置 |
| 配额实时监控 | 每 5 分钟拉取各账号 5 小时 / 7 天窗口用量 |

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 添加账号 A（当前已登录的号）

```bash
mkdir -p accounts/a
cp ~/.codex/auth.json accounts/a/auth.json
```

### 3. 启动代理

```bash
python3 proxy.py
```

访问 Web 管理界面：`http://127.0.0.1:8800/app`

### 4. 配置 Codex 走代理

在 `~/.codex/config.toml` 追加：

```toml
openai_base_url = "http://127.0.0.1:8800/v1"
chatgpt_base_url = "http://127.0.0.1:8800"
```

### 5. 添加更多账号

Web 界面 → 账号管理 → 添加账号 → 填入名称 → 生成登录命令 → 终端执行 → 重新扫描。

```bash
# Web 界面会生成类似这条命令
CODEX_HOME=/path/to/codexproxyapi/accounts/b /Applications/Codex.app/Contents/Resources/codex login
```

浏览器弹出后用**另一个** OpenAI 账号登录，Token 自动落盘。

---

## Web 管理界面

访问 `http://127.0.0.1:8800/app`，三个标签页：

### 仪表盘
- 账号总数、活跃数、限流中数量
- 轮换策略
- 各账号配额总览（5 小时 %、7 天 %、订阅类型）

### 账号管理
- 账号列表（名称、邮箱、状态、用量进度条）
- 操作：启用/禁用、刷新令牌、删除
- 添加账号（生成终端登录命令）

### 设置
- 端口、限流冷却时间、轮换策略、最大重试次数、配额刷新间隔
- 修改端口需重启代理

---

## 配置文件

`config.json`（也可通过 Web 设置页面修改）：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `port` | 8800 | 代理监听端口 |
| `rate_limit_cooldown` | 60 | 触发 429 后冷却秒数 |
| `rotation_strategy` | `round_robin` | 轮换策略：`round_robin` / `least_used` |
| `max_retries` | 10 | 单次请求最大重试次数 |
| `quota_refresh_interval` | 300 | 配额刷新间隔（秒） |

---

## 账号存储

每个账号存储在 `accounts/<name>/` 目录下：

```
accounts/
├── a/
│   ├── auth.json    # OAuth token（access_token + refresh_token）
│   └── quota.json   # 最新配额数据（自动生成）
├── b/
│   └── ...
```

**安全提示**：`accounts/` 目录包含完整账号凭证，已在 `.gitignore` 中排除，不会提交到 Git。

---

## 日常使用

```bash
# 启动代理
cd /path/to/codexproxyapi
python3 proxy.py

# 浏览器查看状态
open http://127.0.0.1:8800/app

# 正常使用 Codex，代理自动工作
```

停止代理：终端 `Ctrl+C`。

---

## 故障排查

| 现象 | 可能原因 | 解决 |
|------|---------|------|
| Web 界面邮箱显示 `—` | Token 解析失败 | 检查 accounts/*/auth.json 是否完整 |
| 配额显示为空 | 网络问题或 API 限制 | 等待 5 分钟自动重试；确认可访问 chatgpt.com |
| 端口被占用 | 上次代理未正常退出 | `lsof -ti:8800 \| xargs kill -9` |
| 所有账号限流 | Plus 额度全部耗尽 | 等待冷却时间过去或添加新账号 |
