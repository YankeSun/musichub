"""
任务管理器模块

负责下载任务的创建、调度、进度跟踪
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from enum import Enum

from musichub.core.types import TrackInfo, DownloadResult, TaskStatus, DownloadTask


@dataclass
class TaskProgress:
    """任务进度信息"""
    task_id: str
    status: TaskStatus
    progress: float  # 0-100
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: float = 0.0  # bytes/s
    eta: float = 0.0  # 预计剩余时间（秒）
    started_at: float | None = None
    completed_at: float | None = None


@dataclass
class QueueStats:
    """队列统计信息"""
    total_tasks: int = 0
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total_downloaded: int = 0  # bytes
    average_speed: float = 0.0  # bytes/s


class TaskManager:
    """
    任务管理器
    
    管理下载任务队列、进度跟踪、断点续传
    """
    
    def __init__(self):
        self._tasks: dict[str, DownloadTask] = {}
        self._progress: dict[str, TaskProgress] = {}
        self._queue: asyncio.Queue[DownloadTask] = asyncio.Queue()
        self._running = False
        self._worker_tasks: list[asyncio.Task] = []
        self._stats = QueueStats()
        self._progress_callbacks: list[Callable[[TaskProgress], None]] = []
    
    def create_task(
        self,
        track: TrackInfo,
        options: dict[str, Any] | None = None,
    ) -> DownloadTask:
        """
        创建下载任务
        
        Args:
            track: 音轨信息
            options: 下载选项
        
        Returns:
            下载任务对象
        """
        import uuid
        task = DownloadTask(
            id=str(uuid.uuid4()),
            track=track,
            options=options or {},
        )
        self._tasks[task.id] = task
        self._progress[task.id] = TaskProgress(
            task_id=task.id,
            status=TaskStatus.PENDING,
            progress=0.0,
        )
        self._stats.total_tasks += 1
        self._stats.pending += 1
        return task
    
    def get_task(self, task_id: str) -> DownloadTask | None:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_progress(self, task_id: str) -> TaskProgress | None:
        """获取任务进度"""
        return self._progress.get(task_id)
    
    def get_all_progress(self) -> list[TaskProgress]:
        """获取所有任务进度"""
        return list(self._progress.values())
    
    def get_stats(self) -> QueueStats:
        """获取队列统计"""
        return self._stats
    
    async def add_to_queue(self, task: DownloadTask) -> None:
        """添加任务到队列"""
        task.status = TaskStatus.PENDING
        await self._queue.put(task)
    
    async def start_worker(self, executor: Callable, num_workers: int = 1) -> None:
        """
        启动工作线程处理队列
        
        Args:
            executor: 任务执行函数 (async)
            num_workers: 工作线程数
        """
        self._running = True
        
        async def worker():
            while self._running:
                try:
                    task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                if task.status == TaskStatus.CANCELLED:
                    self._queue.task_done()
                    continue
                
                try:
                    await self._execute_task(task, executor)
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.result = DownloadResult(success=False, error=str(e))
                    self._update_stats(task)
                finally:
                    self._queue.task_done()
        
        self._worker_tasks = [asyncio.create_task(worker()) for _ in range(num_workers)]
    
    async def _execute_task(self, task: DownloadTask, executor: Callable) -> None:
        """执行单个任务"""
        task.status = TaskStatus.DOWNLOADING
        progress = self._progress[task.id]
        progress.status = TaskStatus.DOWNLOADING
        progress.started_at = time.time()
        
        self._update_stats(task)
        
        # 执行下载
        result = await executor(task)
        task.result = result
        
        if result.success:
            task.status = TaskStatus.COMPLETED
            progress.status = TaskStatus.COMPLETED
            progress.progress = 100.0
            progress.completed_at = time.time()
        else:
            task.status = TaskStatus.FAILED
            progress.status = TaskStatus.FAILED
        
        progress.downloaded_bytes = result.size_bytes if result.success else 0
        self._update_stats(task)
        
        # 通知进度
        await self._notify_progress(progress)
    
    def _update_stats(self, task: DownloadTask) -> None:
        """更新统计信息"""
        # 重置计数
        self._stats.pending = 0
        self._stats.running = 0
        self._stats.completed = 0
        self._stats.failed = 0
        self._stats.cancelled = 0
        self._stats.total_downloaded = 0
        
        for t in self._tasks.values():
            if t.status == TaskStatus.PENDING:
                self._stats.pending += 1
            elif t.status in (TaskStatus.SEARCHING, TaskStatus.DOWNLOADING, TaskStatus.EXPORTING):
                self._stats.running += 1
            elif t.status == TaskStatus.COMPLETED:
                self._stats.completed += 1
                if t.result and t.result.success:
                    self._stats.total_downloaded += t.result.size_bytes
            elif t.status == TaskStatus.FAILED:
                self._stats.failed += 1
            elif t.status == TaskStatus.CANCELLED:
                self._stats.cancelled += 1
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.DOWNLOADING:
            task.status = TaskStatus.PAUSED
            self._progress[task_id].status = TaskStatus.PAUSED
            self._update_stats(task)
            return True
        return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PAUSED:
            task.status = TaskStatus.DOWNLOADING
            self._progress[task_id].status = TaskStatus.DOWNLOADING
            await self._queue.put(task)
            self._update_stats(task)
            return True
        return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if task and task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.status = TaskStatus.CANCELLED
            self._progress[task_id].status = TaskStatus.CANCELLED
            self._update_stats(task)
            return True
        return False
    
    def on_progress(self, callback: Callable[[TaskProgress], None]) -> None:
        """注册进度回调"""
        self._progress_callbacks.append(callback)
    
    async def _notify_progress(self, progress: TaskProgress) -> None:
        """通知进度更新"""
        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception:
                pass
    
    async def stop(self) -> None:
        """停止任务管理器"""
        self._running = False
        for worker in self._worker_tasks:
            worker.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
    
    async def wait_all(self) -> None:
        """等待所有任务完成"""
        await self._queue.join()
