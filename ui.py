# -*- coding: utf-8 -*-
"""业务变更 Dashboard"""
import datetime
import json
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

PAGE_SIZE = 20


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


@st.dialog("业务摘要详情", width="large")
def show_detail_dialog(row):
    """弹窗显示业务摘要及关联详情"""
    st.markdown(f"**业务摘要**\n\n{row.get('business_summary', '')}")
    st.markdown(f"**分类:** {row.get('reasoning_categories', '')}")
    details = row.get("reasoning_details", "[]")
    if details:
        try:
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
    total = len(df)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    # 初始化/重置页码（筛选变化时重置到第一页）
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1
    # 使用 session_state 存储上次筛选条件，筛选变化时重置页码
    filter_key = (platform, tuple(repo_names or []), tuple(authors or []), created_at_gte, created_at_lte)
    if "last_filter" not in st.session_state or st.session_state.last_filter != filter_key:
        st.session_state.last_filter = filter_key
        st.session_state.current_page = 1

    # 限制页码在有效范围内
    page = min(max(1, st.session_state.current_page), total_pages)
    st.session_state.current_page = page
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total)
    df_page = df.iloc[start_idx:end_idx].copy()

    st.success(f"共 {total} 条记录，第 {start_idx + 1}-{end_idx} 条")

    # 表格列：去掉「请求号」
    cols = [
        "platform", "repo_name", "request_title",
        "source_branch", "target_branch", "author", "created_at",
        "business_summary", "reasoning_categories",
    ]
    display_cols = [c for c in cols if c in df_page.columns]
    df_display = df_page[display_cols].copy()
    df_display.columns = [
        "平台", "仓库", "标题", "源分支", "目标分支", "作者", "时间",
        "业务摘要", "分类",
    ]

    # 使用 single-cell 模式：点击行内任意单元格即可弹窗，无需点复选框
    event = st.dataframe(
        df_display,
        use_container_width=True,
        key="biz_dataframe",
        on_select="rerun",
        selection_mode="single-cell",
        column_config={
            "业务摘要": st.column_config.TextColumn("业务摘要", width="large"),
            "标题": st.column_config.TextColumn("标题", width="medium"),
        },
    )

    # 点击任意单元格时弹窗显示业务摘要详情（从 cells 或 rows 获取行索引）
    selected_row_idx = None
    if event.selection:
        if event.selection.rows:
            selected_row_idx = event.selection.rows[0]
        elif event.selection.cells:
            selected_row_idx = event.selection.cells[0][0]  # (row_idx, col_name)
    if selected_row_idx is not None:
        actual_idx = df_page.index[selected_row_idx]
        row = df.loc[actual_idx]
        show_detail_dialog(row)

    # 翻页控件（使用 form 确保按钮点击可靠触发，所有控件同一行）
    st.divider()
    with st.form("pagination_form"):
        col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 1, 1])
        with col1:
            prev_clicked = st.form_submit_button("◀ 上一页")
        with col2:
            st.markdown(f"第 {page} / {total_pages} 页（每页 {PAGE_SIZE} 条）")
        with col3:
            # 跳转到页 与 下拉框 同一行
            r1, r2 = st.columns([1, 2])
            with r1:
                st.text("跳转到页")
            with r2:
                goto = st.selectbox("页", range(1, total_pages + 1), index=page - 1, key="page_select", label_visibility="collapsed")
        with col4:
            go_clicked = st.form_submit_button("跳转")
        with col5:
            next_clicked = st.form_submit_button("下一页 ▶")

    # 处理翻页
    if prev_clicked and page > 1:
        st.session_state.current_page = page - 1
        st.rerun()
    if next_clicked and page < total_pages:
        st.session_state.current_page = page + 1
        st.rerun()
    if go_clicked and goto != page:
        st.session_state.current_page = goto
        st.rerun()
