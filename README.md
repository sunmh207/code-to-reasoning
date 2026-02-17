# code-to-reasoning

从代码变更反推业务变更，持久化存储并支持 Dashboard 展示。

---

## 功能特性

- 支持 **GitLab / GitHub / Gitea** 多平台 MR/PR
- 通过大模型从代码 diff 反推业务描述
- 结构化 JSON 输出，本地 SQLite 持久化
- Dashboard 展示业务变更历史

---

## 原理解析

### 核心思路

在软件开发中，**代码变更**（diff）往往直接反映**业务意图**，但缺乏结构化记录。本项目利用大语言模型（LLM）的语义理解能力，从「代码怎么改」反推「业务要做什么」，形成可追溯的业务变更记录。

```
代码 diff + commit 信息  →  LLM 推理  →  结构化业务描述  →  持久化 + 可视化
```

### 整体流程

```
┌─────────────┐     Webhook      ┌──────────────┐    异步队列     ┌─────────────────┐
│ GitLab/GitHub │ ──────────────→ │ API 服务      │ ─────────────→ │ 业务推理 Worker  │
│ Gitea        │   MR/PR 事件    │ /reasoning/   │                │                 │
└─────────────┘                  │ webhook       │                │ 1. 拉取 changes  │
                                 └──────────────┘                │ 2. 拉取 commits  │
                                                                 │ 3. 调用 LLM 推理 │
                                                                 │ 4. 解析 JSON     │
                                                                 │ 5. 写入 SQLite   │
                                                                 └────────┬────────┘
                                                                          │
                                                                          ▼
                                                                 ┌─────────────────┐
                                                                 │ Dashboard       │
                                                                 │ 展示变更历史     │
                                                                 └─────────────────┘
```

### 关键环节

| 环节 | 说明 |
|------|------|
| **Webhook 触发** | 配置平台 Webhook，指向 `/reasoning/webhook`，仅处理 MR/PR 的创建与更新事件 |
| **平台适配** | 通过请求头区分平台（`X-GitHub-Event` / `X-Gitea-Event` / `object_kind`），统一抽取分支、提交、变更等信息 |
| **文件过滤** | 仅保留业务相关文件（如代码、配置），过滤二进制、依赖等，控制 token 消耗 |
| **LLM 推理** | 将 diff 文本与 commit 信息拼入 Prompt，要求返回 `summary`、`categories`、`details` 结构化 JSON |
| **去重** | 以 `platform + repo_name + source_branch + target_branch + last_commit_id` 唯一标识，避免重复推理 |

---

## 部署

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp conf/.env.dist conf/.env
# 编辑 conf/.env 配置 LLM、平台 Token 等
```

### 3. 启动

```bash
# API 服务（默认 5003）
python api.py

# Dashboard（另开终端，默认 5002）
streamlit run ui.py --server.port=5004 --server.address=0.0.0.0
```

### 4. 配置 Webhook

- **GitLab:** URL=`http://your-host:5003/reasoning/webhook`，勾选 Merge Request Events
- **GitHub:** URL 同上，Content type `application/json`，勾选 Pull requests
- **Gitea:** URL 同上，勾选 Pull Request

### 5. 测试

1. 提交一个 Merge Request / Pull Request
2. 打开 Dashboard `http://your-host:5004` 查看业务变更记录
