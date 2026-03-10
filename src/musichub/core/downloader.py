"""
下载引擎 - 支持并发下载、断点续传、进度回调
"""

import asyncio
import aiohttp
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable, Dict, List
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadTask:
    """下载任务数据类"""
    id: str
    url: str
    dest_path: Path
    status: DownloadStatus = DownloadStatus.PENDING
    total_size: int = 0
    downloaded_size: int = 0
    start_time: float = 0
    end_time: float = 0
    error: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3

    @property
    def progress(self) -> float:
        """返回下载进度 (0.0 - 1.0)"""
        if self.total_size == 0:
            return 0.0
        return self.downloaded_size / self.total_size

    @property
    def speed(self) -> float:
        """返回下载速度 (bytes/s)"""
        if self.start_time == 0:
            return 0.0
        # 使用 end_time 或当前时间计算
        end = self.end_time if self.end_time > 0 else time.time()
        elapsed = end - self.start_time
        if elapsed <= 0:
            return 0.0
        return self.downloaded_size / elapsed

    @property
    def eta(self) -> float:
        """返回预计剩余时间 (秒)"""
        if self.total_size == 0:
            return 0.0
        if self.speed <= 0:
            return float('inf')
        remaining = self.total_size - self.downloaded_size
        eta_val = remaining / self.speed
        return max(0.0, eta_val)  # 确保不为负


@dataclass
class DownloadResult:
    """下载结果数据类"""
    success: bool
    task: DownloadTask
    file_path: Optional[Path] = None
    message: str = ""


class Downloader:
    """
    异步下载器，支持：
    - 并发下载控制
    - 断点续传
    - 进度回调
    - 自动重试
    """

    def __init__(
        self,
        max_concurrency: int = 5,
        chunk_size: int = 8192,
        timeout: int = 30,
        progress_callback: Optional[Callable[[DownloadTask], Awaitable[None]]] = None,
    ):
        """
        初始化下载器

        Args:
            max_concurrency: 最大并发下载数
            chunk_size: 下载块大小 (bytes)
            timeout: 请求超时时间 (秒)
            progress_callback: 进度回调函数 (async)
        """
        self.max_concurrency = max_concurrency
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.progress_callback = progress_callback
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._session: Optional[aiohttp.ClientSession] = None
        self._tasks: Dict[str, DownloadTask] = {}
        self._cancel_flags: Dict[str, asyncio.Event] = {}

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": "MusicHub/1.0"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def close(self):
        """关闭下载器"""
        if self._session:
            await self._session.close()
            self._session = None

    async def download(
        self,
        url: str,
        dest_path: Path,
        task_id: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> DownloadResult:
        """
        下载单个文件

        Args:
            url: 下载链接
            dest_path: 目标路径
            task_id: 任务 ID (可选，默认生成 UUID)
            headers: 额外请求头

        Returns:
            DownloadResult: 下载结果
        """
        import uuid
        task_id = task_id or str(uuid.uuid4())[:8]

        task = DownloadTask(
            id=task_id,
            url=url,
            dest_path=dest_path,
            headers=headers or {},
        )
        self._tasks[task_id] = task
        self._cancel_flags[task_id] = asyncio.Event()

        try:
            async with self._semaphore:
                result = await self._download_with_resume(task)
                return result
        except asyncio.CancelledError:
            task.status = DownloadStatus.CANCELLED
            task.error = "Download cancelled by user"
            return DownloadResult(
                success=False,
                task=task,
                message="Download cancelled"
            )
        except Exception as e:
            logger.exception(f"Download failed for task {task_id}: {e}")
            task.status = DownloadStatus.FAILED
            task.error = str(e)
            return DownloadResult(
                success=False,
                task=task,
                message=f"Download failed: {e}"
            )
        finally:
            self._cancel_flags.pop(task_id, None)

    async def _download_with_resume(self, task: DownloadTask) -> DownloadResult:
        """
        支持断点续传的下载逻辑

        Args:
            task: 下载任务

        Returns:
            DownloadResult: 下载结果
        """
        if not self._session:
            raise RuntimeError("Downloader not initialized. Use 'async with' context.")

        dest_path = task.dest_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # 检查是否存在部分下载的文件
        start_pos = 0
        if dest_path.exists():
            start_pos = dest_path.stat().st_size
            logger.info(f"Resuming download from {start_pos} bytes")

        headers = {**task.headers}
        if start_pos > 0:
            headers["Range"] = f"bytes={start_pos}-"

        task.status = DownloadStatus.DOWNLOADING
        task.start_time = time.time()
        task.downloaded_size = start_pos

        try:
            async with self._session.get(task.url, headers=headers) as response:
                if response.status == 416:
                    # Range not satisfiable - 文件可能已完整下载
                    if start_pos > 0:
                        task.status = DownloadStatus.COMPLETED
                        task.end_time = time.time()
                        return DownloadResult(
                            success=True,
                            task=task,
                            file_path=dest_path,
                            message="File already complete"
                        )

                if response.status not in (200, 206):
                    raise Exception(f"HTTP {response.status}: {response.reason}")

                # 获取总大小
                content_length = response.headers.get("Content-Length")
                if content_length:
                    task.total_size = start_pos + int(content_length)
                else:
                    task.total_size = 0  # 未知总大小

                # 写入文件
                mode = "ab" if start_pos > 0 else "wb"
                async with aiofiles.open(dest_path, mode) as f:
                    async for chunk in response.content.iter_chunked(self.chunk_size):
                        # 检查取消标志
                        if self._cancel_flags.get(task.id, asyncio.Event()).is_set():
                            raise asyncio.CancelledError()

                        await f.write(chunk)
                        task.downloaded_size += len(chunk)

                        # 触发进度回调
                        if self.progress_callback:
                            try:
                                await self.progress_callback(task)
                            except Exception as e:
                                logger.warning(f"Progress callback error: {e}")

            task.status = DownloadStatus.COMPLETED
            task.end_time = time.time()

            logger.info(
                f"Download completed: {dest_path.name} "
                f"({task.downloaded_size / 1024 / 1024:.2f} MB, "
                f"{task.speed / 1024:.2f} KB/s)"
            )

            return DownloadResult(
                success=True,
                task=task,
                file_path=dest_path,
                message="Download completed successfully"
            )

        except aiohttp.ClientError as e:
            # 网络错误，支持重试
            task.retry_count += 1
            if task.retry_count <= task.max_retries:
                logger.warning(
                    f"Download failed, retrying ({task.retry_count}/{task.max_retries}): {e}"
                )
                await asyncio.sleep(2 ** task.retry_count)  # 指数退避
                return await self._download_with_resume(task)
            else:
                raise

    async def batch_download(
        self,
        downloads: List[Dict],
        progress_callback: Optional[Callable[[DownloadTask], Awaitable[None]]] = None,
    ) -> List[DownloadResult]:
        """
        批量下载

        Args:
            downloads: 下载列表，每项包含 {url, dest_path, task_id?, headers?}
            progress_callback: 进度回调函数

        Returns:
            List[DownloadResult]: 下载结果列表
        """
        tasks = [
            self.download(
                url=item["url"],
                dest_path=Path(item["dest_path"]),
                task_id=item.get("task_id"),
                headers=item.get("headers"),
            )
            for item in downloads
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 转换异常为 DownloadResult
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.exception(f"Batch download item {i} failed: {result}")
                processed_results.append(DownloadResult(
                    success=False,
                    task=DownloadTask(
                        id=f"batch_{i}",
                        url=downloads[i]["url"],
                        dest_path=Path(downloads[i]["dest_path"]),
                        status=DownloadStatus.FAILED,
                        error=str(result),
                    ),
                    message=str(result),
                ))
            else:
                processed_results.append(result)

        return processed_results

    async def pause(self, task_id: str) -> bool:
        """暂停下载任务"""
        if task_id not in self._tasks:
            return False
        # 设置取消标志，实际暂停逻辑需要下载循环配合
        self._cancel_flags.get(task_id, asyncio.Event()).set()
        self._tasks[task_id].status = DownloadStatus.PAUSED
        return True

    async def cancel(self, task_id: str) -> bool:
        """取消下载任务"""
        if task_id not in self._tasks:
            return False
        self._cancel_flags.get(task_id, asyncio.Event()).set()
        self._tasks[task_id].status = DownloadStatus.CANCELLED
        return True

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务状态"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, DownloadTask]:
        """获取所有任务"""
        return self._tasks.copy()


# 需要 aiofiles 支持异步文件操作
# 安装：pip install aiofiles
try:
    import aiofiles
except ImportError:
    logger.warning("aiofiles not installed. Install with: pip install aiofiles")
    # Fallback: 使用同步文件操作包装
    import builtins

    class aiofiles:
        @staticmethod
        async def open(path, mode="r"):
            return open(path, mode)
