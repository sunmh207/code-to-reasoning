# -*- coding: utf-8 -*-
"""业务变更 Dashboard"""
import datetime
import os

import pandas as pd
import streamlit as st

from biz.service.storage_service import StorageService

st.set_page_config(
    layout="wide", page_title="业务变更跟踪", page_icon="📋", initial_sidebar_state="expanded"
)

# 初始化数据库
StorageService.init_db()

# 从 env 加载（可选）
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "conf", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass


def get_data(platform=None, repo_names=None, authors=None, created_at_gte=None, created_at_lte=None):
    df = StorageService.get_logs(
        platform=platform,
        repo_names=repo_names,
        authors=authors,
        created_at_gte=created_at_gte,
        created_at_lte=created_at_lte,
    )
    if df.empty:
        return df
    if "created_at" in df.columns:
        df["created_at"] = df["created_at"].apply(
            lambda ts: datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(ts, (int, float))
            else ts
        )
    return df


st.markdown("# 📋 业务变更跟踪")

# 侧边栏筛选
with st.sidebar:
    st.markdown("### 筛选条件")
    platforms = ["gitlab", "github", "gitea"]
    platform = st.selectbox("平台", [""] + platforms, format_func=lambda x: "全部" if not x else x)
    platform = platform or None

    # 先获取全部数据以生成选项
    _all = StorageService.get_logs()
    if not _all.empty:
        repos = sorted(_all["repo_name"].dropna().unique().tolist())
        authors_list = sorted(_all["author"].dropna().unique().tolist())
    else:
        repos, authors_list = [], []

    repo_names = st.multiselect("仓库", repos, default=[])
    authors = st.multiselect("作者", authors_list, default=[])

    st.markdown("### 时间范围")
    today = datetime.date.today()
    days_back = st.slider("最近天数", 1, 90, 30)
    start = today - datetime.timedelta(days=days_back)
    created_at_gte = int(datetime.datetime.combine(start, datetime.time.min).timestamp())
    created_at_lte = int(datetime.datetime.now().timestamp())

# 查询
df = get_data(
    platform=platform,
    repo_names=repo_names if repo_names else None,
    authors=authors if authors else None,
    created_at_gte=created_at_gte,
    created_at_lte=created_at_lte,
)

if df.empty:
    st.info("暂无业务变更记录，请配置 Webhook 后提交 MR/PR 触发。")
    st.markdown("**Webhook URL:** `/reasoning/webhook`")
else:
    st.success(f"共 {len(df)} 条记录")
    cols = [
        "platform", "repo_name", "request_number", "request_title",
        "source_branch", "target_branch", "author", "created_at",
        "business_summary", "reasoning_categories",
    ]
    display_cols = [c for c in cols if c in df.columns]
    df_display = df[display_cols].copy()
    df_display.columns = [
        "平台", "仓库", "请求号", "标题", "源分支", "目标分支", "作者", "时间",
        "业务摘要", "分类",
    ]
    st.dataframe(
        df_display,
        use_container_width=True,
        column_config={
            "业务摘要": st.column_config.TextColumn("业务摘要", width="large"),
            "标题": st.column_config.TextColumn("标题", width="medium"),
        },
    )

    # 详情展开
    st.markdown("### 详情")
    for idx, row in df.iterrows():
        with st.expander(
            f"{row.get('repo_name', '')} #{row.get('request_number', '')} | {row.get('business_summary', '')[:60]}..."
        ):
            st.markdown(f"**业务摘要:** {row.get('business_summary', '')}")
            st.markdown(f"**分类:** {row.get('reasoning_categories', '')}")
            details = row.get("reasoning_details", "[]")
            if details:
                try:
                    import json
                    arr = json.loads(details)
                    if isinstance(arr, list) and arr:
                        st.markdown("**变更明细:**")
                        for d in arr:
                            if isinstance(d, dict):
                                st.markdown(f"- **{d.get('area', '')}:** {d.get('change', '')}")
                except Exception:
                    st.text(details)
            if row.get("request_url"):
                st.markdown(f"[打开 MR/PR]({row['request_url']})")
