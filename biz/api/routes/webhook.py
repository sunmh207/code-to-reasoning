"""
Webhook 路由：支持 GitLab、GitHub、Gitea 多平台 MR/PR
"""
import os
from urllib.parse import urlparse

from flask import Blueprint, request, jsonify

from biz.platforms.gitlab.webhook_handler import (
    MergeRequestHandler as GitLabMRHandler,
    filter_changes as gitlab_filter_changes,
)
from biz.platforms.github.webhook_handler import (
    PullRequestHandler as GitHubPRHandler,
    filter_changes as github_filter_changes,
)
from biz.platforms.gitea.webhook_handler import (
    PullRequestHandler as GiteaPRHandler,
    filter_changes as gitea_filter_changes,
)
from biz.queue.worker import handle_merge_request_event
from biz.utils.log import logger
from biz.utils.queue import handle_queue

webhook_bp = Blueprint("webhook", __name__)


def _run_gitlab(data: dict, token: str, url: str):
    if not token:
        logger.error("Missing GitLab token")
        return
    if not url:
        repo = data.get("repository") or {}
        homepage = repo.get("homepage", "")
        if homepage:
            p = urlparse(homepage)
            url = f"{p.scheme}://{p.netloc}/"
        else:
            logger.error("Missing GitLab URL")
            return
    attrs = data.get("object_attributes", {})
    if attrs.get("draft") or attrs.get("work_in_progress"):
        logger.info("Draft MR, skip")
        return
    if attrs.get("action") not in ("open", "update"):
        return
    handler = GitLabMRHandler(data, token, url)
    handle_merge_request_event(
        platform="gitlab",
        repo_name=handler.repo_name,
        request_number=handler.request_number,
        request_url=handler.request_url,
        request_title=handler.request_title,
        source_branch=handler.source_branch,
        target_branch=handler.target_branch,
        last_commit_id=handler.last_commit_id,
        author=handler.author,
        get_changes=handler.get_changes,
        get_commits=handler.get_commits,
        filter_changes_fn=gitlab_filter_changes,
    )


def _run_github(data: dict, token: str, url: str):
    if not token:
        logger.error("Missing GitHub token")
        return
    if data.get("action") not in ("opened", "synchronize"):
        return
    handler = GitHubPRHandler(data, token, url)
    handle_merge_request_event(
        platform="github",
        repo_name=handler.repo_name,
        request_number=handler.request_number,
        request_url=handler.request_url,
        request_title=handler.request_title,
        source_branch=handler.source_branch,
        target_branch=handler.target_branch,
        last_commit_id=handler.last_commit_id,
        author=handler.author,
        get_changes=handler.get_changes,
        get_commits=handler.get_commits,
        filter_changes_fn=github_filter_changes,
    )


def _run_gitea(data: dict, token: str, url: str):
    if not token:
        logger.error("Missing Gitea token")
        return
    action = data.get("action", "")
    if action not in ("opened", "open", "reopened", "synchronize", "synchronized"):
        return
    handler = GiteaPRHandler(data, token, url)
    handle_merge_request_event(
        platform="gitea",
        repo_name=handler.repo_name,
        request_number=handler.request_number,
        request_url=handler.request_url,
        request_title=handler.request_title,
        source_branch=handler.source_branch,
        target_branch=handler.target_branch,
        last_commit_id=handler.last_commit_id,
        author=handler.author,
        get_changes=handler.get_changes,
        get_commits=handler.get_commits,
        filter_changes_fn=gitea_filter_changes,
    )


@webhook_bp.route("/reasoning/webhook", methods=["POST"])
def handle_webhook():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    gh = request.headers.get("X-GitHub-Event")
    gitea = request.headers.get("X-Gitea-Event")

    if gitea:
        if gitea == "pull_request":
            tok = os.getenv("GITEA_ACCESS_TOKEN") or request.headers.get("X-Gitea-Token")
            url = os.getenv("GITEA_URL", "https://gitea.com")
            handle_queue(_run_gitea, data, tok or "", url)
            return jsonify({"message": "Gitea PR received, processing async."}), 200
        return jsonify({"error": "Only pull_request supported"}), 400

    if gh:
        if gh == "pull_request":
            tok = os.getenv("GITHUB_ACCESS_TOKEN") or request.headers.get("X-GitHub-Token")
            url = os.getenv("GITHUB_URL", "https://github.com")
            handle_queue(_run_github, data, tok or "", url)
            return jsonify({"message": "GitHub PR received, processing async."}), 200
        return jsonify({"error": "Only pull_request supported"}), 400

    if data.get("object_kind") == "merge_request":
        tok = os.getenv("GITLAB_ACCESS_TOKEN") or request.headers.get("X-Gitlab-Token")
        url = os.getenv("GITLAB_URL") or request.headers.get("X-Gitlab-Instance") or ""
        if not url and data.get("repository", {}).get("homepage"):
            p = urlparse(data["repository"]["homepage"])
            url = f"{p.scheme}://{p.netloc}/"
        handle_queue(_run_gitlab, data, tok or "", url)
        return jsonify({"message": "GitLab MR received, processing async."}), 200

    return jsonify({"error": "Unsupported event or platform"}), 400
