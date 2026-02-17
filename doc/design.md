# code-to-reasoning 设计方案

## 一、项目定位

从代码变更反推业务变更，持久化存储并支持 Dashboard 展示，方便项目业务变更跟踪。

| 决策项 | 方案 |
|--------|------|
| 回写 | 不回写 GitLab Note，仅本地存储 |
| 输出 | 结构化 JSON |
| 触发 | 仅 MR/PR |
| 平台 | 支持 GitLab、GitHub、Gitee、Gitea 多平台扩展 |
| IM 通知 | 不需要 |
| 文件过滤 | 复用 SUPPORTED_EXTENSIONS |
| 去重 | last_commit_id |
| Dashboard | 需要 |

---

## 二、多平台扩展设计

### 平台术语映射

| 通用概念 | GitLab | GitHub | Gitea | Gitee |
|----------|--------|--------|-------|-------|
| 平台标识 | gitlab | github | gitea | gitee |
| 合并请求 | Merge Request (iid) | Pull Request (number) | Pull Request (index) | Pull Request (number) |
| 仓库名 | project.name | repository.name | repository.name | project.name |
| 请求编号 | object_attributes.iid | pull_request.number | pull_request.number/index | - |

### 数据库设计（平台无关）

**关键原则：** 不使用平台专属字段名（如 `mr_iid`），统一使用通用字段。

```sql
CREATE TABLE business_reasoning_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- 平台与仓库（支持多平台）
    platform TEXT NOT NULL,              -- gitlab|github|gitea|gitee
    repo_name TEXT NOT NULL,             -- 仓库/项目名（各平台均可映射）
    -- 合并请求通用字段（平台无关命名）
    request_number INTEGER,             -- MR/PR 编号：GitLab iid, GitHub number, Gitea index
    request_url TEXT,                    -- 合并请求链接
    request_title TEXT,                  -- 合并请求标题
    -- 分支与提交
    source_branch TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    last_commit_id TEXT NOT NULL,
    -- 元数据
    author TEXT,
    commit_messages TEXT,
    created_at INTEGER NOT NULL,
    -- 业务推理结果
    business_summary TEXT NOT NULL,       -- JSON.summary
    reasoning_categories TEXT,           -- JSON.categories 序列化
    reasoning_details TEXT,              -- JSON.details 序列化
    raw_reasoning_json TEXT,             -- 完整 LLM 返回（解析失败时保留）
    diff_summary TEXT,                   -- 可选
    -- 去重约束：同平台同仓库同分支同提交只记录一次
    UNIQUE(platform, repo_name, source_branch, target_branch, last_commit_id)
);

CREATE INDEX idx_brl_platform ON business_reasoning_log(platform);
CREATE INDEX idx_brl_repo ON business_reasoning_log(repo_name);
CREATE INDEX idx_brl_created_at ON business_reasoning_log(created_at);
```

**字段说明：**
- `request_number`：各平台的 MR/PR 序号，均为整数
- `request_url` / `request_title`：各平台均有对应字段
- `repo_name`：GitLab 用 project.name，GitHub 用 repository.name，语义统一为“仓库名”

---

## 三、架构与目录结构

见 README 与代码注释。
