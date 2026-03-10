"""
下载引擎单元测试
"""

import pytest
import pytest_asyncio

from musichub.core.engine import DownloadEngine, TrackInfo, TaskStatus
from musichub.core.config import Config


@pytest.fixture
def config():
    """测试配置"""
    return Config(
        max_concurrent_downloads=2,
        output_format="mp3",
    )


@pytest_asyncio.fixture
async def engine(config):
    """测试引擎"""
    eng = DownloadEngine(config)
    await eng.initialize()
    yield eng
    await eng.shutdown()


class TestDownloadEngine:
    """下载引擎测试"""
    
    def test_engine_initialization(self, config):
        """测试引擎初始化"""
        engine = DownloadEngine(config)
        assert engine.config == config
        assert engine._running is False
    
    @pytest.mark.asyncio
    async def test_engine_async_init(self, engine):
        """测试异步初始化"""
        assert engine._running is True
        assert engine._semaphore is not None
    
    def test_sanitize_filename(self, engine):
        """测试文件名清理"""
        test_cases = [
            ("正常歌曲.mp3", "正常歌曲.mp3"),
            ("歌曲/名称.mp3", "歌曲名称.mp3"),
            ("特殊<字符>*.mp3", "特殊字符.mp3"),
            ("  空格  .mp3", "空格.mp3"),
            ("", "untitled"),
        ]
        
        for input_name, expected in test_cases:
            result = engine._sanitize_filename(input_name)
            assert result == expected, f"输入：{input_name}"
    
    def test_create_task(self, engine):
        """测试任务创建"""
        track = TrackInfo(
            id="test_001",
            title="测试歌曲",
            artist="测试歌手",
        )
        
        task = engine.create_task(track)
        
        assert task.id is not None
        assert task.track == track
        assert task.status == TaskStatus.PENDING
    
    def test_get_task(self, engine):
        """测试获取任务"""
        track = TrackInfo(
            id="test_002",
            title="测试歌曲 2",
            artist="测试歌手 2",
        )
        
        task = engine.create_task(track)
        retrieved = engine.get_task(task.id)
        
        assert retrieved == task
    
    def test_get_nonexistent_task(self, engine):
        """测试获取不存在的任务"""
        result = engine.get_task("nonexistent_id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, engine):
        """测试取消任务"""
        track = TrackInfo(
            id="test_003",
            title="测试歌曲 3",
            artist="测试歌手 3",
        )
        
        task = engine.create_task(track)
        result = await engine.cancel_task(task.id)
        
        assert result is True
        assert task.status == TaskStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cancel_completed_task(self, engine):
        """测试取消已完成的任务"""
        track = TrackInfo(
            id="test_004",
            title="测试歌曲 4",
            artist="测试歌手 4",
        )
        
        task = engine.create_task(track)
        task.status = TaskStatus.COMPLETED
        
        result = await engine.cancel_task(task.id)
        assert result is False


class TestTrackInfo:
    """音轨信息测试"""
    
    def test_track_info_creation(self):
        """测试音轨信息创建"""
        track = TrackInfo(
            id="12345",
            title="歌曲名",
            artist="艺术家",
            album="专辑名",
            duration=240,
        )
        
        assert track.id == "12345"
        assert track.title == "歌曲名"
        assert track.duration == 240
    
    def test_track_info_defaults(self):
        """测试默认值"""
        track = TrackInfo(
            id="12345",
            title="歌曲名",
            artist="艺术家",
        )
        
        assert track.album is None
        assert track.duration is None
        assert track.metadata == {}
