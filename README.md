# code-to-reasoning

从代码变更反推业务变更，持久化存储并支持 Dashboard 展示。

## 功能

- 支持 **GitLab / GitHub / Gitea** 多平台 MR/PR
- 通过大模型从代码 diff 反推业务描述
- 结构化 JSON 输出，本地存储
- Dashboard 展示业务变更历史

## 原理

1. 配置对应平台的 Webhook，指向 `/reasoning/webhook`
2. 创建/更新 MR/PR 时触发
3. 获取 changes 和 commits，调用 LLM 反推业务
4. 解析 JSON，写入 SQLite
5. Dashboard 展示

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

## 数据库设计（多平台）

使用平台无关字段，便于扩展：

| 字段 | 说明 |
|------|------|
| platform | gitlab \| github \| gitea |
| repo_name | 仓库名 |
| request_number | MR/PR 编号（GitLab iid, GitHub number, Gitea index） |
| request_url | 合并请求链接 |
| request_title | 标题 |
| business_summary | 业务摘要 |
| reasoning_categories | 分类 |
| reasoning_details | 变更明细 JSON |

去重：`(platform, repo_name, source_branch, target_branch, last_commit_id)` 唯一。

## 项目结构

```
code-to-reasoning/
├── api.py
├── ui.py
├── conf/
├── biz/
│   ├── api/routes/webhook.py
│   ├── platforms/gitlab|github|gitea/
│   ├── queue/worker.py
│   ├── service/storage_service.py
│   ├── service/business_reasoning_service.py
│   └── llm/
├── data/
└── doc/design.md
```
