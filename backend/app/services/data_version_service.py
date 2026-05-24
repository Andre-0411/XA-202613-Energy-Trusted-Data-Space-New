"""
数据版本管理服务
================
实现数据资产的版本管理功能：
- 创建新版本（自动递增版本号）
- 获取版本历史
- 版本对比
- 版本回滚
- 版本标签管理

存储方式：内存字典（演示用），可无缝切换到 PostgreSQL
"""
import uuid
import hashlib
import json
import copy
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class DataVersion:
    """数据版本记录"""
    version_id: str
    dataset_id: str
    version_number: str  # e.g. "1.0.0"
    description: str
    created_by: str
    created_at: str
    data_hash: str  # 数据内容哈希
    metadata_snapshot: dict = field(default_factory=dict)
    record_count: int = 0
    file_size_bytes: int = 0
    tags: list[str] = field(default_factory=list)
    parent_version_id: Optional[str] = None
    is_rollback: bool = False
    status: str = "active"  # active / archived / deprecated


@dataclass
class VersionTag:
    """版本标签"""
    tag_id: str
    version_id: str
    dataset_id: str
    tag_name: str  # e.g. "v1.0-release", "stable", "production"
    description: str
    created_by: str
    created_at: str


class DataVersionStore:
    """数据版本管理存储"""

    def __init__(self):
        # dataset_id -> list[DataVersion]
        self._versions: dict[str, list[DataVersion]] = {}
        # version_id -> DataVersion
        self._version_index: dict[str, DataVersion] = {}
        # dataset_id -> list[VersionTag]
        self._tags: dict[str, list[VersionTag]] = {}
        # dataset_id -> current version_id
        self._current: dict[str, str] = {}

    def create_version(
        self,
        dataset_id: str,
        description: str = "",
        created_by: str = "system",
        data_content: Optional[bytes] = None,
        metadata: Optional[dict] = None,
        record_count: int = 0,
        file_size_bytes: int = 0,
        tags: Optional[list[str]] = None,
    ) -> DataVersion:
        """创建新版本"""
        versions = self._versions.get(dataset_id, [])

        # 计算版本号
        if not versions:
            version_number = "1.0.0"
            parent_version_id = None
        else:
            latest = versions[-1]
            # 递增修订号
            parts = latest.version_number.split(".")
            parts[2] = str(int(parts[2]) + 1)
            version_number = ".".join(parts)
            parent_version_id = latest.version_id

        # 计算数据哈希
        if data_content:
            data_hash = hashlib.sha256(data_content).hexdigest()
        else:
            data_hash = hashlib.sha256(
                f"{dataset_id}:{version_number}:{datetime.now(timezone.utc).isoformat()}".encode()
            ).hexdigest()

        version = DataVersion(
            version_id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            version_number=version_number,
            description=description,
            created_by=created_by,
            created_at=datetime.now(timezone.utc).isoformat(),
            data_hash=data_hash,
            metadata_snapshot=metadata or {},
            record_count=record_count,
            file_size_bytes=file_size_bytes,
            tags=tags or [],
            parent_version_id=parent_version_id,
        )

        if dataset_id not in self._versions:
            self._versions[dataset_id] = []
        self._versions[dataset_id].append(version)
        self._version_index[version.version_id] = version
        self._current[dataset_id] = version.version_id

        return version

    def get_versions(
        self,
        dataset_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取版本历史"""
        versions = self._versions.get(dataset_id, [])
        # 按时间倒序
        sorted_versions = sorted(versions, key=lambda v: v.created_at, reverse=True)

        total = len(sorted_versions)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = sorted_versions[start:end]

        return {
            "dataset_id": dataset_id,
            "versions": [self._version_to_dict(v) for v in paginated],
            "total": total,
            "page": page,
            "page_size": page_size,
            "current_version_id": self._current.get(dataset_id),
        }

    def get_version(self, version_id: str) -> Optional[dict]:
        """获取单个版本详情"""
        version = self._version_index.get(version_id)
        if not version:
            return None
        return self._version_to_dict(version)

    def compare_versions(self, version_id_a: str, version_id_b: str) -> dict:
        """对比两个版本"""
        v_a = self._version_index.get(version_id_a)
        v_b = self._version_index.get(version_id_b)

        if not v_a or not v_b:
            return {"error": "版本不存在"}

        diff = {
            "version_a": self._version_to_dict(v_a),
            "version_b": self._version_to_dict(v_b),
            "differences": {
                "description_changed": v_a.description != v_b.description,
                "record_count_diff": v_b.record_count - v_a.record_count,
                "file_size_diff": v_b.file_size_bytes - v_a.file_size_bytes,
                "hash_changed": v_a.data_hash != v_b.data_hash,
                "metadata_changes": self._diff_metadata(
                    v_a.metadata_snapshot, v_b.metadata_snapshot
                ),
                "tags_added": list(set(v_b.tags) - set(v_a.tags)),
                "tags_removed": list(set(v_a.tags) - set(v_b.tags)),
            },
            "time_diff_hours": (
                datetime.fromisoformat(v_b.created_at) -
                datetime.fromisoformat(v_a.created_at)
            ).total_seconds() / 3600,
        }
        return diff

    def rollback_to_version(
        self,
        dataset_id: str,
        target_version_id: str,
        created_by: str = "system",
        reason: str = "",
    ) -> Optional[DataVersion]:
        """回滚到指定版本"""
        target = self._version_index.get(target_version_id)
        if not target or target.dataset_id != dataset_id:
            return None

        # 创建一个新版本，标记为回滚
        versions = self._versions.get(dataset_id, [])
        if versions:
            latest = versions[-1]
            parts = latest.version_number.split(".")
            parts[2] = str(int(parts[2]) + 1)
            version_number = ".".join(parts)
        else:
            version_number = "1.0.0"

        rollback_version = DataVersion(
            version_id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            version_number=version_number,
            description=f"回滚到版本 {target.version_number}" + (f"（原因：{reason}）" if reason else ""),
            created_by=created_by,
            created_at=datetime.now(timezone.utc).isoformat(),
            data_hash=target.data_hash,
            metadata_snapshot=copy.deepcopy(target.metadata_snapshot),
            record_count=target.record_count,
            file_size_bytes=target.file_size_bytes,
            tags=target.tags.copy(),
            parent_version_id=target.version_id,
            is_rollback=True,
        )

        versions.append(rollback_version)
        self._version_index[rollback_version.version_id] = rollback_version
        self._current[dataset_id] = rollback_version.version_id

        return rollback_version

    def add_tag(
        self,
        dataset_id: str,
        version_id: str,
        tag_name: str,
        description: str = "",
        created_by: str = "system",
    ) -> Optional[VersionTag]:
        """为版本添加标签"""
        version = self._version_index.get(version_id)
        if not version or version.dataset_id != dataset_id:
            return None

        tag = VersionTag(
            tag_id=str(uuid.uuid4()),
            version_id=version_id,
            dataset_id=dataset_id,
            tag_name=tag_name,
            description=description,
            created_by=created_by,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        if dataset_id not in self._tags:
            self._tags[dataset_id] = []
        self._tags[dataset_id].append(tag)

        return tag

    def get_tags(self, dataset_id: str) -> list[dict]:
        """获取数据集的所有版本标签"""
        tags = self._tags.get(dataset_id, [])
        return [
            {
                "tag_id": t.tag_id,
                "version_id": t.version_id,
                "tag_name": t.tag_name,
                "description": t.description,
                "created_by": t.created_by,
                "created_at": t.created_at,
            }
            for t in tags
        ]

    def get_current_version(self, dataset_id: str) -> Optional[dict]:
        """获取当前版本"""
        current_id = self._current.get(dataset_id)
        if not current_id:
            return None
        return self.get_version(current_id)

    def get_statistics(self, dataset_id: str) -> dict:
        """获取版本统计"""
        versions = self._versions.get(dataset_id, [])
        tags = self._tags.get(dataset_id, [])

        if not versions:
            return {
                "total_versions": 0,
                "total_tags": 0,
                "first_version_at": None,
                "latest_version_at": None,
                "rollback_count": 0,
            }

        return {
            "total_versions": len(versions),
            "total_tags": len(tags),
            "first_version_at": versions[0].created_at,
            "latest_version_at": versions[-1].created_at,
            "rollback_count": sum(1 for v in versions if v.is_rollback),
            "current_version": self._version_to_dict(versions[-1]),
        }

    @staticmethod
    def _version_to_dict(v: DataVersion) -> dict:
        """版本转字典"""
        return {
            "version_id": v.version_id,
            "dataset_id": v.dataset_id,
            "version_number": v.version_number,
            "description": v.description,
            "created_by": v.created_by,
            "created_at": v.created_at,
            "data_hash": v.data_hash,
            "metadata_snapshot": v.metadata_snapshot,
            "record_count": v.record_count,
            "file_size_bytes": v.file_size_bytes,
            "tags": v.tags,
            "parent_version_id": v.parent_version_id,
            "is_rollback": v.is_rollback,
            "status": v.status,
        }

    @staticmethod
    def _diff_metadata(meta_a: dict, meta_b: dict) -> list[dict]:
        """对比元数据差异"""
        changes = []
        all_keys = set(meta_a.keys()) | set(meta_b.keys())
        for key in all_keys:
            val_a = meta_a.get(key)
            val_b = meta_b.get(key)
            if val_a != val_b:
                changes.append({
                    "field": key,
                    "old_value": val_a,
                    "new_value": val_b,
                    "change_type": "added" if val_a is None else "removed" if val_b is None else "modified",
                })
        return changes


# 全局单例
_version_store = DataVersionStore()


def get_version_store() -> DataVersionStore:
    """获取版本管理存储实例"""
    return _version_store
