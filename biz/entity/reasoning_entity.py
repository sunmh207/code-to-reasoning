"""
业务推理实体，平台无关设计
"""
from typing import Optional


class BusinessReasoningEntity:
    """业务推理结果实体，支持多平台 (GitLab/GitHub/Gitea/Gitee)"""

    def __init__(
        self,
        platform: str,
        repo_name: str,
        source_branch: str,
        target_branch: str,
        last_commit_id: str,
        business_summary: str,
        reasoning_categories: str,
        reasoning_details: str,
        raw_reasoning_json: str,
        author: Optional[str] = None,
        commit_messages: Optional[str] = None,
        request_number: Optional[int] = None,
        request_url: Optional[str] = None,
        request_title: Optional[str] = None,
        diff_summary: Optional[str] = None,
    ):
        self.platform = platform
        self.repo_name = repo_name
        self.request_number = request_number
        self.request_url = request_url
        self.request_title = request_title
        self.source_branch = source_branch
        self.target_branch = target_branch
        self.last_commit_id = last_commit_id
        self.author = author or ""
        self.commit_messages = commit_messages or ""
        self.diff_summary = diff_summary
        self.business_summary = business_summary
        self.reasoning_categories = reasoning_categories
        self.reasoning_details = reasoning_details
        self.raw_reasoning_json = raw_reasoning_json
