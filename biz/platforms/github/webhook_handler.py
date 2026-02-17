"""
GitHub Pull Request Handler
平台字段映射：number -> request_number, repository.name -> repo_name
"""
import os
import re
import time

import requests

from biz.utils.log import logger

PLATFORM = "github"


def filter_changes(changes: list) -> list:
    """复用 SUPPORTED_EXTENSIONS，兼容 GitHub files API 格式"""
    supported_extensions = os.getenv("SUPPORTED_EXTENSIONS", ".java,.py,.php").split(",")
    not_deleted = []
    for c in changes:
        if c.get("status") == "removed":
            continue
        diff = c.get("diff") or c.get("patch") or ""
        if diff:
            m = re.match(r"@@ -\d+,\d+ \+0,0 @@", diff)
            if m and all(
                line.startswith("-") or not line
                for line in diff.split("\n")[1:]
            ):
                continue
        not_deleted.append(c)
    return [
        {
            "diff": item.get("diff") or item.get("patch", ""),
            "new_path": item.get("new_path") or item.get("filename", ""),
            "additions": item.get("additions", 0),
            "deletions": item.get("deletions", 0),
        }
        for item in not_deleted
        if any((item.get("new_path") or item.get("filename") or "").endswith(ext) for ext in supported_extensions)
    ]


class PullRequestHandler:
    """GitHub PR Handler，返回平台无关的 request_number/request_url/request_title"""

    def __init__(self, webhook_data: dict, token: str, base_url: str):
        self.webhook_data = webhook_data
        self.token = token
        self.base_url = (base_url or "https://github.com").rstrip("/")
        pr = webhook_data.get("pull_request", {})
        repo = webhook_data.get("repository", {})
        self.repo_name = repo.get("name", "")
        self.repo_full_name = repo.get("full_name", self.repo_name)
        self.request_number = pr.get("number")  # GitHub: number
        self.request_url = pr.get("html_url", "")
        self.request_title = pr.get("title", "")
        self.source_branch = (pr.get("head") or {}).get("ref", "")
        self.target_branch = (pr.get("base") or {}).get("ref", "")
        self.action = webhook_data.get("action")
        self.last_commit_id = (pr.get("head") or {}).get("sha", "")
        self.author = (pr.get("user") or {}).get("login", "")

    def get_changes(self) -> list:
        if not self.repo_full_name or not self.request_number:
            return []
        url = f"{self.base_url.replace('github.com', 'api.github.com')}/repos/{self.repo_full_name}/pulls/{self.request_number}/files"
        if "api." not in url:
            url = f"https://api.github.com/repos/{self.repo_full_name}/pulls/{self.request_number}/files"
        for attempt in range(3):
            resp = requests.get(
                url,
                headers={
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            if resp.status_code == 200:
                files = resp.json()
                if files:
                    return [
                        {
                            "filename": f.get("filename"),
                            "new_path": f.get("filename"),
                            "diff": f.get("patch", ""),
                            "patch": f.get("patch", ""),
                            "additions": f.get("additions", 0),
                            "deletions": f.get("deletions", 0),
                            "status": f.get("status", ""),
                        }
                        for f in files
                    ]
            time.sleep(10)
        return []

    def get_commits(self) -> list:
        if not self.repo_full_name or not self.request_number:
            return []
        url = f"https://api.github.com/repos/{self.repo_full_name}/pulls/{self.request_number}/commits"
        resp = requests.get(
            url,
            headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        if resp.status_code != 200:
            return []
        result = []
        for c in resp.json():
            cm = c.get("commit", {})
            msg = cm.get("message", "")
            result.append({
                "id": c.get("sha"),
                "title": msg.split("\n")[0] if msg else "",
                "message": msg,
            })
        return result
