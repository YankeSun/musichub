"""
核心类型定义

避免循环导入，所有核心数据类型在此定义
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class TrackInfo:
    """音轨信息"""
    id: str
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[int] = None  # 秒
    stream_url: Optional[str] = None
    source: str = "unknown"
    cover_url: Optional[str] = None
    lyrics: Optional[str] = None
    track_number: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.artist} - {self.title}"


@dataclass
class DownloadResult:
    """下载结果"""
    success: bool
    output_path: Optional[Path] = None
    size_bytes: int = 0
    duration: float = 0.0  # 下载耗时（秒）
    error: Optional[str] = None


@dataclass
class DownloadTask:
    """下载任务"""
    id: str
    track: Optional[TrackInfo] = None
    options: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0  # 0-100
    result: Optional[DownloadResult] = None
    error_message: Optional[str] = None
    created_at: float = field(default_factory=lambda: __import__('time').time())
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    success: bool
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
