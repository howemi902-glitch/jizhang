# Email Assistant Agent (MVP)

这个 Agent 会每天从 Gmail 拉取最近 24 小时邮件，自动做：

1. 今日邮件摘要
2. 识别重要且需要回复的邮件
3. 给出建议回复草稿

## 功能

- Gmail API 拉取邮件（仅读取）
- LLM 分类（需要回复 / 重要信息 / 普通通知）
- 每日摘要输出到控制台（可扩展 Telegram/邮件推送）
- SQLite 持久化避免重复处理

## 快速开始

1. 安装依赖

```bash
pip install -r agent/requirements.txt
```

2. 配置环境变量

复制 `.env.example` 到 `.env` 并填写：

- `OPENAI_API_KEY`
- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN`
- `GMAIL_USER`（例如 `me`）

3. 运行

```bash
python agent/email_assistant.py
```

## 定时运行（每天 8:30 UTC）

```bash
30 8 * * * cd /path/to/repo && /usr/bin/python3 agent/email_assistant.py >> agent.log 2>&1
```

## 注意

- 首次接入 Gmail API 需在 Google Cloud Console 开启 Gmail API。
- 建议生产部署时将 SQLite 换成托管数据库。
