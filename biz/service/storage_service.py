"""
存储服务：平台无关的业务推理日志持久化
"""
import json
import os
import sqlite3
from typing import List, Optional

import pandas as pd

from biz.entity.reasoning_entity import BusinessReasoningEntity


class StorageService:
    """业务推理日志存储，支持多平台 (platform, repo_name, request_number 等通用字段)"""

    DB_FILE = "data/data.db"

    @classmethod
    def _db_path(cls) -> str:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base, cls.DB_FILE)

    @classmethod
    def init_db(cls):
        """初始化数据库及表结构（平台无关设计）"""
        db_path = cls._db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS business_reasoning_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        platform TEXT NOT NULL,
                        repo_name TEXT NOT NULL,
                        request_number INTEGER,
                        request_url TEXT,
                        request_title TEXT,
                        source_branch TEXT NOT NULL,
                        target_branch TEXT NOT NULL,
                        last_commit_id TEXT NOT NULL,
                        author TEXT,
                        commit_messages TEXT,
                        created_at INTEGER NOT NULL,
                        business_summary TEXT NOT NULL,
                        reasoning_categories TEXT,
                        reasoning_details TEXT,
                        raw_reasoning_json TEXT,
                        diff_summary TEXT,
                        UNIQUE(platform, repo_name, source_branch, target_branch, last_commit_id)
                    )
                """)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_brl_platform ON business_reasoning_log(platform)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_brl_repo ON business_reasoning_log(repo_name)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_brl_created_at ON business_reasoning_log(created_at)"
                )
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Database initialization failed: {e}")

    @classmethod
    def check_exists(
        cls,
        platform: str,
        repo_name: str,
        source_branch: str,
        target_branch: str,
        last_commit_id: str,
    ) -> bool:
        """检查是否已存在相同提交的记录（去重）"""
        try:
            with sqlite3.connect(cls._db_path()) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM business_reasoning_log
                    WHERE platform = ? AND repo_name = ? AND source_branch = ?
                    AND target_branch = ? AND last_commit_id = ?
                    """,
                    (platform, repo_name, source_branch, target_branch, last_commit_id),
                )
                return cursor.fetchone()[0] > 0
        except sqlite3.DatabaseError as e:
            print(f"Error checking existence: {e}")
            return False

    @classmethod
    def insert(cls, entity: BusinessReasoningEntity, created_at: int):
        """插入业务推理日志"""
        try:
            with sqlite3.connect(cls._db_path()) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO business_reasoning_log (
                        platform, repo_name, request_number, request_url, request_title,
                        source_branch, target_branch, last_commit_id, author, commit_messages,
                        created_at, business_summary, reasoning_categories, reasoning_details,
                        raw_reasoning_json, diff_summary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity.platform,
                        entity.repo_name,
                        entity.request_number,
                        entity.request_url,
                        entity.request_title,
                        entity.source_branch,
                        entity.target_branch,
                        entity.last_commit_id,
                        entity.author,
                        entity.commit_messages,
                        created_at,
                        entity.business_summary,
                        entity.reasoning_categories,
                        entity.reasoning_details,
                        entity.raw_reasoning_json,
                        entity.diff_summary,
                    ),
                )
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting reasoning log: {e}")

    @classmethod
    def get_logs(
        cls,
        platform: Optional[str] = None,
        repo_names: Optional[List[str]] = None,
        authors: Optional[List[str]] = None,
        created_at_gte: Optional[int] = None,
        created_at_lte: Optional[int] = None,
    ) -> pd.DataFrame:
        """获取业务推理日志（Dashboard 用）"""
        try:
            with sqlite3.connect(cls._db_path()) as conn:
                query = """
                    SELECT platform, repo_name, request_number, request_url, request_title,
                           source_branch, target_branch, author, created_at, business_summary,
                           reasoning_categories, reasoning_details, last_commit_id
                    FROM business_reasoning_log
                    WHERE 1=1
                """
                params = []
                if platform:
                    query += " AND platform = ?"
                    params.append(platform)
                if repo_names:
                    placeholders = ",".join(["?"] * len(repo_names))
                    query += f" AND repo_name IN ({placeholders})"
                    params.extend(repo_names)
                if authors:
                    placeholders = ",".join(["?"] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)
                if created_at_gte is not None:
                    query += " AND created_at >= ?"
                    params.append(created_at_gte)
                if created_at_lte is not None:
                    query += " AND created_at <= ?"
                    params.append(created_at_lte)
                query += " ORDER BY created_at DESC"
                return pd.read_sql_query(sql=query, con=conn, params=params or None)
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving logs: {e}")
            return pd.DataFrame()
