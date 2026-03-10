"""
下载引擎核心 - 协调搜索、下载、导出流程
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import logging

from musichub.core.config import Config
from musichub.core.types import TrackInfo, TaskStatus, TaskResult, DownloadTask
from musichub.core.manager import TaskManager
from musichub.core.events import EventSystem, EventType, DownloadEvent, SearchEvent
from musichub.plugins.base import PluginRegistry
from musichub.utils.metadata import TrackMetadata, MetadataManager


logger = logging.getLogger(__name__)


class SearchResult:
    """搜索结果"""
    
    def __init__(
        self,
        tracks: List[TrackInfo],
        source: str,
        query: str,
        total: int = 0
    ):
        self.tracks = tracks
        self.source = source
        self.query = query
        self.total = total or len(tracks)
    
    def __len__(self) -> int:
        return len(self.tracks)
    
    def __iter__(self):
        return iter(self.tracks)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "query": self.query,
            "total": self.total,
            "tracks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "artist": t.artist,
                    "album": t.album,
                    "duration": t.duration,
                }
                for t in self.tracks
            ]
        }


class DownloadEngine:
    """
    下载引擎
    
    核心职责：
    - 协调音源搜索、下载、导出流程
    - 管理并发任务
    - 处理进度回调和事件
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        plugin_registry: Optional[PluginRegistry] = None
    ):
        self.config = config or Config()
        self.plugin_registry = plugin_registry or PluginRegistry()
        self.task_manager = TaskManager()
        self.event_system = EventSystem()
        self.metadata_manager = MetadataManager()
        
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None
    
    async def initialize(self) -> None:
        """初始化引擎"""
        self._semaphore = asyncio.Semaphore(self.config.download.max_concurrent_downloads)
        self._running = True
        self.config.ensure_directories()
        logger.info("DownloadEngine initialized")
    
    async def shutdown(self) -> None:
        """关闭引擎"""
        self._running = False
        
        # 取消所有运行中的任务
        for task in self._tasks.values():
            task.cancel()
        
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()
        
        logger.info("DownloadEngine shutdown complete")
    
    async def search(
        self,
        query: str,
        source: Optional[str] = None,
        limit: int = 20
    ) -> SearchResult:
        """
        搜索音乐
        
        Args:
            query: 搜索关键词
            source: 音源插件名称，None 表示搜索所有启用的音源
            limit: 结果数量限制
        
        Returns:
            SearchResult 包含匹配的音轨列表
        """
        # 发布搜索开始事件
        await self.event_system.publish(SearchEvent(
            event_type=EventType.SEARCH_START,
            query=query,
            source=source or "all"
        ))
        
        all_tracks: List[TrackInfo] = []
        
        # 确定要使用的音源
        if source:
            sources = [source]
        else:
            sources = self.config.sources.enabled_sources
        
        # 并行搜索所有音源
        search_tasks = []
        for source_name in sources:
            plugin = self.plugin_registry.get_source(source_name)
            if plugin:
                search_tasks.append(self._search_source(plugin, query, limit))
        
        if search_tasks:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    all_tracks.extend(result)
        
        # 发布搜索完成事件
        await self.event_system.publish(SearchEvent(
            event_type=EventType.SEARCH_COMPLETE,
            query=query,
            source=source or "all",
            results_count=len(all_tracks)
        ))
        
        return SearchResult(
            tracks=all_tracks[:limit],
            source=source or "combined",
            query=query,
            total=len(all_tracks)
        )
    
    async def _search_source(
        self,
        plugin: Any,
        query: str,
        limit: int
    ) -> List[TrackInfo]:
        """从单个音源搜索"""
        try:
            results = await plugin.search(query)
            return results[:limit]
        except Exception as e:
            logger.error(f"Search failed for source: {e}")
            return []
    
    async def download(
        self,
        track: TrackInfo,
        output_format: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> TaskResult:
        """
        下载单个音轨
        
        Args:
            track: 音轨信息
            output_format: 输出格式，默认使用配置中的格式
            output_path: 输出路径，默认使用配置中的目录
        
        Returns:
            TaskResult 包含下载结果
        """
        # 创建任务
        task = await self.task_manager.create_task(
            track,
            options={
                "format": output_format or self.config.export.default_format,
                "output_path": output_path
            }
        )
        
        # 开始下载
        return await self._process_task(task)
    
    async def batch_download(
        self,
        tracks: List[TrackInfo],
        output_format: Optional[str] = None,
        concurrency: Optional[int] = None
    ) -> List[TaskResult]:
        """
        批量下载
        
        Args:
            tracks: 音轨列表
            output_format: 输出格式
            concurrency: 并发数，默认使用配置中的值
        
        Returns:
            TaskResult 列表
        """
        # 创建所有任务
        tasks = []
        for track in tracks:
            task = await self.task_manager.create_task(
                track,
                options={"format": output_format or self.config.export.default_format}
            )
            tasks.append(task)
        
        # 限制并发数
        max_concurrent = concurrency or self.config.download.max_concurrent_downloads
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(task: DownloadTask) -> TaskResult:
            async with semaphore:
                return await self._process_task(task)
        
        # 并行下载
        results = await asyncio.gather(
            *[download_with_semaphore(t) for t in tasks],
            return_exceptions=True
        )
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(TaskResult(
                    task_id=tasks[i].id,
                    success=False,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_task(self, task: DownloadTask) -> TaskResult:
        """处理单个下载任务"""
        try:
            # 标记任务开始
            await self.task_manager.start_task(task.id)
            
            # 发布下载开始事件
            await self.event_system.publish(DownloadEvent(
                event_type=EventType.DOWNLOAD_START,
                task_id=task.id,
                track_id=task.track.id if task.track else "",
                url=task.track.stream_url if task.track else ""
            ))
            
            # 获取流 URL
            if not task.track or not task.track.stream_url:
                stream_url = await self._get_stream_url(task.track)
                if task.track:
                    task.track.stream_url = stream_url
            
            # 下载文件
            output_path = await self._download_file(task)
            
            # 导出/转换格式
            output_format = task.options.get("format", "mp3")
            final_path = await self._export_file(output_path, output_format, task.track)
            
            # 写入元数据
            if self.config.export.write_metadata and task.track:
                await self.metadata_manager.write_metadata(
                    final_path,
                    TrackMetadata.from_track_info(task.track)
                )
            
            # 标记任务完成
            await self.task_manager.complete_task(task.id, final_path)
            
            # 发布下载完成事件
            await self.event_system.publish(DownloadEvent(
                event_type=EventType.DOWNLOAD_COMPLETE,
                task_id=task.id,
                track_id=task.track.id if task.track else "",
                progress=1.0
            ))
            
            return TaskResult(
                task_id=task.id,
                success=True,
                output_path=final_path
            )
            
        except asyncio.CancelledError:
            await self.task_manager.update_task(task.id, status=TaskStatus.CANCELLED)
            return TaskResult(
                task_id=task.id,
                success=False,
                error_message="Task cancelled"
            )
        except Exception as e:
            logger.error(f"Download failed: {e}")
            await self.task_manager.fail_task(task.id, str(e))
            
            await self.event_system.publish(DownloadEvent(
                event_type=EventType.DOWNLOAD_ERROR,
                task_id=task.id,
                message=str(e)
            ))
            
            return TaskResult(
                task_id=task.id,
                success=False,
                error_message=str(e)
            )
    
    async def _get_stream_url(self, track: TrackInfo) -> Optional[str]:
        """获取音轨的流 URL"""
        if not track:
            return None
        
        source_name = track.source
        plugin = self.plugin_registry.get_source(source_name)
        
        if plugin:
            return await plugin.get_stream_url(track.id)
        
        return track.stream_url
    
    async def _download_file(self, task: DownloadTask) -> Path:
        """下载文件"""
        # 获取下载器插件
        downloader = self.plugin_registry.get_downloader("http")
        
        if not downloader:
            raise RuntimeError("No downloader plugin available")
        
        # 确定输出路径
        output_dir = self.config.export.output_directory
        filename = self._sanitize_filename(
            f"{task.track.artist} - {task.track.title}.tmp"
            if task.track else "download.tmp"
        )
        output_path = output_dir / filename
        
        # 检查断点续传
        resume_data = self.task_manager.get_resume_data(task.id)
        
        # 执行下载
        result = await downloader.download(
            url=task.track.stream_url if task.track else "",
            dest=output_path,
            resume_data=resume_data,
            progress_callback=lambda downloaded, total: self._on_progress(task, downloaded, total)
        )
        
        # 清除续传数据
        self.task_manager.clear_resume_data(task.id)
        
        return output_path
    
    async def _export_file(
        self,
        input_path: Path,
        output_format: str,
        track: Optional[TrackInfo]
    ) -> Path:
        """导出/转换文件格式"""
        if output_format == "tmp":
            # 临时文件，重命名为最终格式
            final_path = input_path.with_suffix(f".{output_format}")
            input_path.rename(final_path)
            return final_path
        
        # 获取导出器插件
        exporter_name = output_format.lower()
        exporter = self.plugin_registry.get_exporter(exporter_name)
        
        if exporter:
            return await exporter.export(input_path, output_format)
        
        # 没有导出器，直接重命名
        final_path = input_path.with_suffix(f".{output_format}")
        input_path.rename(final_path)
        return final_path
    
    def _on_progress(self, task: DownloadTask, downloaded: int, total: int) -> None:
        """下载进度回调"""
        if total > 0:
            progress = downloaded / total
            asyncio.create_task(self.task_manager.update_progress(
                task.id,
                progress=progress,
                downloaded_bytes=downloaded,
                total_bytes=total
            ))
            
            # 发布进度事件
            asyncio.create_task(self.event_system.publish(DownloadEvent(
                event_type=EventType.DOWNLOAD_PROGRESS,
                task_id=task.id,
                progress=progress,
                downloaded_bytes=downloaded,
                total_bytes=total
            )))
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        import re
        # 移除非法字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
        # 限制长度
        return sanitized[:200]
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """订阅事件"""
        self.event_system.subscribe(event_type, callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable) -> bool:
        """取消订阅事件"""
        return self.event_system.unsubscribe(event_type, callback)
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = await self.task_manager.get_task(task_id)
        if not task:
            return None
        
        return {
            "id": task.id,
            "status": task.status.name,
            "progress": task.progress,
            "track": {
                "title": task.track.title,
                "artist": task.track.artist
            } if task.track else None,
            "error": task.error_message
        }
