# QQ 机器人（3371871293）

这是一个基于 **NapCat + NoneBot2 + OneBot v11** 的 QQ 机器人项目骨架。

## 技术栈

- NapCatQQ：负责登录 QQ（你的机器人 QQ 号：`3371871293`）
- NoneBot2：Python 机器人框架
- FastAPI/WebSocket Driver：作为 NoneBot 运行驱动
- OneBot v11 Adapter：连接 NapCat

## 已实现功能

- `帮助` / `help` / `菜单`：查看指令
- `ping`：连通性测试
- `时间`：返回当前服务器时间
- `说 <内容>`：复读指定文本
- `生图 <提示词>` / `画图 <提示词>`：调用 MiniMax 文生图
- 关键词轻响应：`你好` / `在吗` / `机器人`
- 已预留定时任务能力（apscheduler）

## 目录结构

```text
qq-bot-3371871293/
├─ bot.py
├─ requirements.txt
├─ .env.example
├─ plugins/
│  ├─ __init__.py
│  └─ basic.py
└─ README.md
```

## 1. 创建虚拟环境并安装依赖

```bash
cd /root/.openclaw/workspace/qq-bot-3371871293
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 2. 配置 NoneBot

```bash
cp .env.example .env
```

默认配置使用 NapCat 正向 WebSocket：

```env
ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]
```

如果你给 NapCat 配了 access token，把 `.env` 里的 `ONEBOT_ACCESS_TOKEN` 一并填上。

## 3. 安装/启动 NapCat

你给的参考文档是 NapCat 的 Shell 启动页：
<https://napneko.github.io/guide/boot/Shell>

Linux 常见做法有两种：

### 方案 A：NapCat 安装脚本

按文档执行安装脚本，装好后登录 QQ：`3371871293`。

### 方案 B：Docker

如果你更想容器化，NapCat 官方也支持 Docker / compose。

## 4. 在 NapCat 里开启 OneBot v11 正向 WebSocket

需要确保 NapCat 的 OneBot 配置里：

- 协议：OneBot v11
- 通信方式：正向 WebSocket
- 地址：`ws://127.0.0.1:3001`
- access token：与 `.env` 保持一致（如果设置了）

> 注意：有些面板里填的是监听端口而不是完整 URL，本质上要保证 NoneBot 能连到 NapCat 提供的 WebSocket 服务。

## 5. 启动机器人

```bash
cd /root/.openclaw/workspace/qq-bot-3371871293
source .venv/bin/activate
python bot.py
```

启动成功后，在 QQ 私聊或群里给机器人发：

```text
帮助
ping
时间
说 你好
```

## 6. 如果你想扩展功能

直接在 `plugins/` 下新增 Python 文件即可，比如：

- 群管功能
- 自动回复
- 定时提醒
- 接入企业内部接口
- 接 ChatGPT/DeepSeek/本地模型

## 常见问题

### 1）机器人没反应

按这个顺序排查：

1. NapCat 是否已经登录 QQ `3371871293`
2. NapCat 的 OneBot v11 WebSocket 是否已开启
3. `.env` 中的 `ONEBOT_WS_URLS` 是否和 NapCat 一致
4. access token 是否一致
5. NoneBot 日志里是否有连接成功信息

### 2）群里收不到消息

检查：

- 机器人是否已进群
- 是否被禁言
- NapCat / QQ 侧是否正常在线

### 3）想做更复杂的功能

建议把功能拆成独立插件，例如：

- `plugins/admin.py`
- `plugins/reminder.py`
- `plugins/llm_chat.py`

---

如果你要，我下一步可以继续直接给你补：

1. **自动聊天 AI 版本**
2. **群管版本（欢迎/禁言/关键词）**
3. **带网页管理面板的版本**
4. **可部署到服务器的一键启动脚本**
