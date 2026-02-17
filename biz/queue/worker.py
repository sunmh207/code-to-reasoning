"""
MR/PR 事件处理：获取 changes -> 业务推理 -> 存储
支持多平台，通过 handler 传入平台无关字段
"""
import traceback
from datetime import datetime
from typing import Any, Callable, List

from biz.entity.reasoning_entity import BusinessReasoningEntity
from biz.service.business_reasoning_service import BusinessReasoningService
from biz.service.storage_service import StorageService
from biz.utils.log import logger


def _commit_messages(commits: List[dict]) -> str:
    """从 commits 提取 message，兼容各平台"""
    texts = []
    for c in commits:
        t = c.get("title") or c.get("message", "")
        if t:
            texts.append(t.strip())
    return "; ".join(texts)


def handle_merge_request_event(
    platform: str,
    repo_name: str,
    request_number: Any,
    request_url: str,
    request_title: str,
    source_branch: str,
    target_branch: str,
    last_commit_id: str,
    author: str,
    get_changes: Callable[[], List],
    get_commits: Callable[[], List],
    filter_changes_fn: Callable[[List], List],
):
    """
    通用 MR/PR 处理逻辑，平台无关。
    get_changes/get_commits 由具体平台 Handler 提供，
    filter_changes_fn 为对应平台的 filter_changes。
    """
    if not last_commit_id:
        logger.warn("last_commit_id is empty, skip")
        return

    if StorageService.check_exists(
        platform, repo_name, source_branch, target_branch, last_commit_id
    ):
        logger.info(
            f"Already exists: {platform}/{repo_name} {source_branch}->{target_branch} {last_commit_id}, skip"
        )
        return

    changes = get_changes()
    changes = filter_changes_fn(changes)
    if not changes:
        logger.info("No supported file changes, skip")
        return

    commits = get_commits()
    commits_text = _commit_messages(commits)
    diffs_text = str(changes)

    svc = BusinessReasoningService()
    result = svc.reason(diffs_text, commits_text)

    entity = BusinessReasoningEntity(
        platform=platform,
        repo_name=repo_name,
        request_number=int(request_number) if request_number is not None else None,
        request_url=request_url or "",
        request_title=request_title or "",
        source_branch=source_branch,
        target_branch=target_branch,
        last_commit_id=last_commit_id,
        author=author,
        commit_messages=commits_text,
        business_summary=result.get("summary", ""),
        reasoning_categories=result.get("categories", ""),
        reasoning_details=result.get("details", "[]"),
        raw_reasoning_json=result.get("raw", ""),
    )
    StorageService.insert(entity, int(datetime.now().timestamp()))
    logger.info(f"Saved: {platform}/{repo_name} #{request_number} -> {result.get('summary', '')[:50]}")
