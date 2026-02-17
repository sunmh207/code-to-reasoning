"""
GitLab Merge Request Handler
平台字段映射：iid -> request_number, project.name -> repo_name
"""
import os
import re
import time
from urllib.parse import urljoin

import requests

from biz.utils.log import logger

PLATFORM = "gitlab"


def filter_changes(changes: list) -> list:
    """复用 SUPPORTED_EXTENSIONS 过滤文件类型"""
    supported_extensions = os.getenv("SUPPORTED_EXTENSIONS", ".java,.py,.php").split(",")
    filter_deleted = [c for c in changes if not c.get("deleted_file")]
    return [
        {
            "diff": item.get("diff", ""),
            "new_path": item.get("new_path", ""),
            "additions": len(re.findall(r"^\+(?!\+\+)", item.get("diff", ""), re.MULTILINE)),
            "deletions": len(re.findall(r"^-(?!--)", item.get("diff", ""), re.MULTILINE)),
        }
        for item in filter_deleted
        if any((item.get("new_path") or "").endswith(ext) for ext in supported_extensions)
    ]


class MergeRequestHandler:
    """GitLab MR Handler，返回平台无关的 request_number/request_url/request_title 等"""

    def __init__(self, webhook_data: dict, token: str, base_url: str):
        self.webhook_data = webhook_data
        self.token = token
        self.base_url = base_url.rstrip("/") + "/"
        self.attrs = webhook_data.get("object_attributes", {})
        self.repo_name = (webhook_data.get("project") or {}).get("name", "")
        self.request_number = self.attrs.get("iid")  # GitLab: iid
        self.request_url = self.attrs.get("url", "")
        self.request_title = self.attrs.get("title", "")
        self.source_branch = self.attrs.get("source_branch", "")
        self.target_branch = self.attrs.get("target_branch", "")
        self.action = self.attrs.get("action")
        last_commit = self.attrs.get("last_commit") or {}
        self.last_commit_id = last_commit.get("id", "")
        self.author = (webhook_data.get("user") or {}).get("username", "")
        self.project_id = self.attrs.get("target_project_id")

    def get_changes(self) -> list:
        if not self.project_id or not self.request_number:
            return []
        max_retries = 3
        for attempt in range(max_retries):
            url = urljoin(
                self.base_url,
                f"api/v4/projects/{self.project_id}/merge_requests/{self.request_number}/changes?access_raw_diffs=true",
            )
            resp = requests.get(
                url, headers={"Private-Token": self.token}, verify=False
            )
            if resp.status_code == 200:
                changes = resp.json().get("changes", [])
                if changes:
                    return changes
            time.sleep(10)
        return []

    def get_commits(self) -> list:
        if not self.project_id or not self.request_number:
            return []
        url = urljoin(
            self.base_url,
            f"api/v4/projects/{self.project_id}/merge_requests/{self.request_number}/commits",
        )
        resp = requests.get(url, headers={"Private-Token": self.token}, verify=False)
        if resp.status_code == 200:
            return resp.json()
        return []
