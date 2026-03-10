"""
Pytest 配置文件 - 共享 fixtures 和配置
"""

import pytest
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator
import tempfile
import shutil


@pytest.fixture(scope="session")
def event_loop_policy():
    """设置事件循环策略"""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录"""
    tmpdir = tempfile.mkdtemp(prefix="musichub_test_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_track_info():
    """示例音轨信息"""
    from musichub.core.manager import TrackInfo
    
    return TrackInfo(
        id="test_track_001",
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        duration=180,
        source="test_source",
        cover_url="https://example.com/cover.jpg",
        stream_url="https://example.com/stream.mp3"
    )


@pytest.fixture
def sample_metadata():
    """示例元数据"""
    from musichub.utils.metadata import TrackMetadata
    
    return TrackMetadata(
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        year=2024,
        genre="Pop",
        duration=180
    )


@pytest.fixture
def sample_config():
    """示例配置"""
    from musichub.core.config import Config, DownloadConfig, ExportConfig
    
    return Config(
        download=DownloadConfig(
            max_concurrent_downloads=2,
            chunk_size=8192,
            timeout=10,
            max_retries=2
        ),
        export=ExportConfig(
            default_format="mp3",
            write_metadata=True
        )
    )


@pytest.fixture
async def engine(sample_config):
    """创建下载引擎实例"""
    from musichub.core.engine import DownloadEngine
    from musichub.plugins.base import PluginRegistry
    
    registry = PluginRegistry()
    engine = DownloadEngine(config=sample_config, plugin_registry=registry)
    await engine.initialize()
    
    yield engine
    
    await engine.shutdown()


@pytest.fixture
def plugin_registry():
    """创建插件注册表"""
    from musichub.plugins.base import PluginRegistry
    
    registry = PluginRegistry()
    return registry


@pytest.fixture
def mock_http_response():
    """Mock HTTP 响应数据"""
    class MockResponse:
        def __init__(self, status_code=200, content=b"mock audio data", headers=None):
            self.status_code = status_code
            self._content = content
            self.headers = headers or {"content-length": str(len(content))}
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
        
        @property
        def content(self):
            return self._content
        
        async def aiter_bytes(self, chunk_size=8192):
            for i in range(0, len(self._content), chunk_size):
                yield self._content[i:i+chunk_size]
    
    return MockResponse


@pytest.fixture
def mock_async_client():
    """Mock httpx.AsyncClient"""
    class MockClient:
        def __init__(self, response=None):
            self._response = response
            self._closed = False
        
        async def get(self, url, **kwargs):
            return self._response
        
        async def stream(self, method, url, **kwargs):
            return self._response
        
        async def aclose(self):
            self._closed = True
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            await self.aclose()
    
    return MockClient
