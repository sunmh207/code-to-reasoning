"""
Gitea Pull Request Handler
平台字段映射：number/index -> request_number, repository.name -> repo_name
"""
import os
import re
import time
from urllib.parse import urljoin

import requests

from biz.utils.log import logger

PLATFORM = "gitea"


def filter_changes(changes: list) -> list:
    """复用 SUPPORTED_EXTENSIONS"""
    supported_extensions = os.getenv("SUPPORTED_EXTENSIONS", ".java,.py,.php").split(",")
    result = []
    for item in changes:
        status = (item.get("status") or "").lower()
        if status in ("removed", "deleted"):
            continue
        new_path = item.get("new_path") or item.get("filename") or item.get("path")
        if not new_path or not any(new_path.endswith(ext) for ext in supported_extensions):
            continue
        diff_text = item.get("diff") or item.get("patch") or ""
        result.append({
            "diff": diff_text,
            "new_path": new_path,
            "additions": item.get("additions", 0),
            "deletions": item.get("deletions", 0),
        })
    return result


class PullRequestHandler:
    """Gitea PR Handler，返回平台无关的 request_number/request_url/request_title"""

    def __init__(self, webhook_data: dict, token: str, base_url: str):
        self.webhook_data = webhook_data
        self.token = token
        self.base_url = (base_url or "https://gitea.com").rstrip("/") + "/"
        pr = webhook_data.get("pull_request", {})
        repo = webhook_data.get("repository", {})
        self.repo_name = repo.get("name", "")
        self.repo_full_name = repo.get("full_name", self.repo_name)
        self.request_number = pr.get("number") or pr.get("index") or pr.get("id")  # Gitea: number or index
        self.request_url = pr.get("html_url") or pr.get("url", "")
        self.request_title = pr.get("title", "")
        head = pr.get("head") or {}
        base = pr.get("base") or {}
        self.source_branch = head.get("ref") or pr.get("head_branch", "")
        self.target_branch = base.get("ref") or pr.get("base_branch", "")
        self.action = webhook_data.get("action")
        self.last_commit_id = head.get("sha") or pr.get("merge_base", "")
        self.author = (pr.get("user") or {}).get("login") or (pr.get("user") or {}).get("username", "")

    def _headers(self):
        return {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_changes(self) -> list:
        if not self.repo_full_name or not self.request_number:
            return []
        url = urljoin(
            self.base_url,
            f"api/v1/repos/{self.repo_full_name}/pulls/{self.request_number}/files",
        )
        for attempt in range(3):
            resp = requests.get(url, headers=self._headers(), verify=False)
            if resp.status_code == 200:
                files = resp.json() or []
                if files:
                    return [
                        {
                            "diff": f.get("patch") or f.get("diff", ""),
                            "new_path": f.get("filename") or f.get("path", ""),
                            "additions": f.get("additions", 0),
                            "deletions": f.get("deletions", 0),
                        }
                        for f in files
                    ]
            time.sleep(10)
        return []

    def get_commits(self) -> list:
        if not self.repo_full_name or not self.request_number:
            return []
        url = urljoin(
            self.base_url,
            f"api/v1/repos/{self.repo_full_name}/pulls/{self.request_number}/commits",
        )
        resp = requests.get(url, headers=self._headers(), verify=False)
        if resp.status_code != 200:
            return []
        result = []
        for c in resp.json() or []:
            msg = c.get("commit", {}).get("message", "") or c.get("message", "")
            result.append({
                "id": c.get("sha") or c.get("id"),
                "title": msg.split("\n")[0] if msg else "",
                "message": msg,
            })
        return result
