"""
下载引擎测试 - 测试 DownloadEngine 核心功能
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from musichub.core.engine import DownloadEngine, SearchResult
from musichub.core.config import Config
from musichub.core.manager import TrackInfo, TaskStatus
from musichub.core.events import EventType, EventSystem
from musichub.plugins.base import PluginRegistry


class TestDownloadEngine:
    """DownloadEngine 测试类"""
    
    def test_engine_initialization(self, sample_config, plugin_registry):
        """测试引擎初始化"""
        engine = DownloadEngine(config=sample_config, plugin_registry=plugin_registry)
        
        assert engine.config == sample_config
        assert engine.plugin_registry == plugin_registry
        assert engine.task_manager is not None
        assert engine.event_system is not None
        assert engine._running is False
    
    @pytest.mark.asyncio
    async def test_engine_initialize(self, engine):
        """测试引擎初始化流程"""
        assert engine._running is True
        assert engine._semaphore is not None
        assert engine._semaphore._value == engine.config.download.max_concurrent_downloads
    
    @pytest.mark.asyncio
    async def test_engine_shutdown(self, engine):
        """测试引擎关闭"""
        await engine.shutdown()
        
        assert engine._running is False
        assert len(engine._tasks) == 0
    
    @pytest.mark.asyncio
    async def test_search_single_source(self, engine, sample_track_info):
        """测试单音源搜索"""
        # Mock 音源插件
        mock_source = AsyncMock()
        mock_source.search = AsyncMock(return_value=[sample_track_info])
        engine.plugin_registry.register_source("test_source", mock_source)
        
        # 执行搜索
        result = await engine.search("test query", source="test_source", limit=10)
        
        assert isinstance(result, SearchResult)
        assert result.source == "test_source"
        assert result.query == "test query"
        assert len(result.tracks) == 1
        assert result.tracks[0].id == sample_track_info.id
        
        # 验证插件被调用
        mock_source.search.assert_called_once_with("test query")
    
    @pytest.mark.asyncio
    async def test_search_multiple_sources(self, engine, sample_track_info):
        """测试多音源并行搜索"""
        # Mock 多个音源插件
        mock_source1 = AsyncMock()
        mock_source1.search = AsyncMock(return_value=[sample_track_info])
        
        mock_source2 = AsyncMock()
        track2 = TrackInfo(
            id="track_002",
            title="Another Song",
            artist="Another Artist",
            source="source2"
        )
        mock_source2.search = AsyncMock(return_value=[track2])
        
        engine.plugin_registry.register_source("source1", mock_source1)
        engine.plugin_registry.register_source("source2", mock_source2)
        
        # 执行搜索
        result = await engine.search("test query", limit=20)
        
        assert len(result.tracks) == 2
        mock_source1.search.assert_called_once()
        mock_source2.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_empty_result(self, engine):
        """测试搜索无结果"""
        mock_source = AsyncMock()
        mock_source.search = AsyncMock(return_value=[])
        engine.plugin_registry.register_source("test_source", mock_source)
        
        result = await engine.search("nonexistent", source="test_source")
        
        assert len(result.tracks) == 0
        assert result.total == 0
    
    @pytest.mark.asyncio
    async def test_search_plugin_error(self, engine):
        """测试音源插件错误处理"""
        mock_source = AsyncMock()
        mock_source.search = AsyncMock(side_effect=Exception("API error"))
        engine.plugin_registry.register_source("error_source", mock_source)
        
        # 不应抛出异常，应返回空结果
        result = await engine.search("test", source="error_source")
        
        assert len(result.tracks) == 0
    
    @pytest.mark.asyncio
    async def test_download_single_track(self, engine, sample_track_info, temp_dir):
        """测试单曲下载"""
        # Mock 音源和下载器插件
        mock_source = AsyncMock()
        mock_source.get_stream_url = AsyncMock(return_value="https://example.com/stream.mp3")
        
        mock_downloader = AsyncMock()
        output_file = temp_dir / "test.mp3"
        output_file.write_bytes(b"mock audio data")
        
        mock_downloader.download = AsyncMock(return_value={
            "success": True,
            "downloaded_bytes": 100,
            "total_bytes": 100,
            "path": str(output_file)
        })
        
        engine.plugin_registry.register_source("test_source", mock_source)
        engine.plugin_registry.register_downloader("http", mock_downloader)
        
        # 执行下载
        result = await engine.download(
            sample_track_info,
            output_format="mp3",
            output_path=temp_dir / "output.mp3"
        )
        
        assert result.success is True
        assert result.output_path is not None
        mock_downloader.download.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_no_downloader(self, engine, sample_track_info):
        """测试无下载器插件"""
        # 不注册下载器
        result = await engine.download(sample_track_info)
        
        assert result.success is False
        assert "No downloader plugin available" in result.error_message
    
    @pytest.mark.asyncio
    async def test_batch_download(self, engine, temp_dir):
        """测试批量下载"""
        # 创建多个音轨
        tracks = [
            TrackInfo(id=f"track_{i}", title=f"Song {i}", artist="Artist", source="test")
            for i in range(5)
        ]
        
        # Mock 插件
        mock_source = AsyncMock()
        mock_source.get_stream_url = AsyncMock(return_value="https://example.com/stream.mp3")
        
        mock_downloader = AsyncMock()
        output_file = temp_dir / "test.mp3"
        output_file.write_bytes(b"mock audio data")
        
        mock_downloader.download = AsyncMock(return_value={
            "success": True,
            "downloaded_bytes": 100,
            "total_bytes": 100
        })
        
        engine.plugin_registry.register_source("test", mock_source)
        engine.plugin_registry.register_downloader("http", mock_downloader)
        
        # 执行批量下载
        results = await engine.batch_download(tracks, concurrency=2)
        
        assert len(results) == 5
        # 验证并发限制
        assert mock_downloader.download.call_count == 5
    
    @pytest.mark.asyncio
    async def test_event_subscription(self, engine):
        """测试事件订阅"""
        callback = MagicMock()
        
        engine.subscribe(EventType.DOWNLOAD_PROGRESS, callback)
        
        # 验证订阅成功
        assert engine.event_system.get_subscriber_count(EventType.DOWNLOAD_PROGRESS) == 1
        
        # 取消订阅
        engine.unsubscribe(EventType.DOWNLOAD_PROGRESS, callback)
        assert engine.event_system.get_subscriber_count(EventType.DOWNLOAD_PROGRESS) == 0
    
    @pytest.mark.asyncio
    async def test_task_status_tracking(self, engine, sample_track_info):
        """测试任务状态跟踪"""
        # 创建任务但不执行下载
        task = await engine.task_manager.create_task(sample_track_info)
        
        # 获取任务状态
        status = await engine.get_task_status(task.id)
        
        assert status is not None
        assert status["id"] == task.id
        assert status["status"] == "PENDING"
        assert status["track"]["title"] == sample_track_info.title
    
    @pytest.mark.asyncio
    async def test_download_with_progress_callback(self, engine, sample_track_info, temp_dir):
        """测试下载进度回调"""
        # Mock 下载器，模拟进度回调
        mock_downloader = AsyncMock()
        output_file = temp_dir / "test.mp3"
        output_file.write_bytes(b"mock audio data")
        
        progress_calls = []
        
        def mock_download(url, dest, resume_data=None, progress_callback=None):
            if progress_callback:
                progress_callback(50, 100)
                progress_callback(100, 100)
            return {
                "success": True,
                "downloaded_bytes": 100,
                "total_bytes": 100
            }
        
        mock_downloader.download = mock_download
        engine.plugin_registry.register_downloader("http", mock_downloader)
        
        # 订阅进度事件
        events_received = []
        
        def on_progress(event):
            events_received.append(event)
        
        engine.subscribe(EventType.DOWNLOAD_PROGRESS, on_progress)
        
        # 执行下载
        await engine.download(sample_track_info)
        
        # 验证收到进度事件
        assert len(events_received) > 0
    
    def test_sanitize_filename(self, engine):
        """测试文件名清理"""
        # 测试非法字符
        assert engine._sanitize_filename("test<file>.mp3") == "testfile.mp3"
        assert engine._sanitize_filename("test|file?.mp3") == "testfile.mp3"
        assert engine._sanitize_filename("test\"file\".mp3") == "testfile.mp3"
        
        # 测试长度限制
        long_name = "a" * 300 + ".mp3"
        sanitized = engine._sanitize_filename(long_name)
        assert len(sanitized) <= 200


class TestSearchResult:
    """SearchResult 测试类"""
    
    def test_search_result_creation(self, sample_track_info):
        """测试搜索结果创建"""
        result = SearchResult(
            tracks=[sample_track_info],
            source="test",
            query="test query",
            total=1
        )
        
        assert len(result) == 1
        assert result.source == "test"
        assert result.query == "test query"
    
    def test_search_result_to_dict(self, sample_track_info):
        """测试搜索结果转字典"""
        result = SearchResult(
            tracks=[sample_track_info],
            source="test",
            query="test query"
        )
        
        data = result.to_dict()
        
        assert data["source"] == "test"
        assert data["query"] == "test query"
        assert len(data["tracks"]) == 1
        assert data["tracks"][0]["title"] == sample_track_info.title
    
    def test_search_result_iteration(self, sample_track_info):
        """测试搜索结果迭代"""
        tracks = [
            TrackInfo(id=f"track_{i}", title=f"Song {i}", artist="Artist")
            for i in range(3)
        ]
        
        result = SearchResult(tracks=tracks, source="test", query="test")
        
        # 测试迭代
        titles = [track.title for track in result]
        assert len(titles) == 3


class TestEventSystem:
    """EventSystem 测试类"""
    
    @pytest.mark.asyncio
    async def test_event_publish_subscribe(self):
        """测试事件发布订阅"""
        event_system = EventSystem()
        callback = AsyncMock()
        
        event_system.subscribe(EventType.SEARCH_START, callback)
        
        from musichub.core.events import SearchEvent
        event = SearchEvent(
            event_type=EventType.SEARCH_START,
            query="test",
            source="test"
        )
        
        await event_system.publish(event)
        
        callback.assert_called_once_with(event)
    
    @pytest.mark.asyncio
    async def test_event_unsubscribe(self):
        """测试取消订阅"""
        event_system = EventSystem()
        callback = MagicMock()
        
        event_system.subscribe(EventType.SEARCH_START, callback)
        result = event_system.unsubscribe(EventType.SEARCH_START, callback)
        
        assert result is True
        assert event_system.get_subscriber_count(EventType.SEARCH_START) == 0
    
    def test_clear_events(self):
        """测试清除所有事件订阅"""
        event_system = EventSystem()
        
        event_system.subscribe(EventType.SEARCH_START, MagicMock())
        event_system.subscribe(EventType.DOWNLOAD_START, MagicMock())
        
        event_system.clear()
        
        assert event_system.get_subscriber_count(EventType.SEARCH_START) == 0
        assert event_system.get_subscriber_count(EventType.DOWNLOAD_START) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """测试多个订阅者"""
        event_system = EventSystem()
        callback1 = AsyncMock()
        callback2 = AsyncMock()
        
        event_system.subscribe(EventType.SEARCH_START, callback1)
        event_system.subscribe(EventType.SEARCH_START, callback2)
        
        from musichub.core.events import SearchEvent
        event = SearchEvent(event_type=EventType.SEARCH_START)
        
        await event_system.publish(event)
        
        callback1.assert_called_once()
        callback2.assert_called_once()
