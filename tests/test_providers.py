"""
插件接口测试 - 测试插件系统和各种插件实现
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile

from musichub.plugins.base import (
    PluginBase,
    SourcePlugin,
    DownloaderPlugin,
    ExporterPlugin,
    PluginRegistry
)
from musichub.plugins.downloaders.base import HTTPDownloader
from musichub.plugins.exporters.base import MP3Exporter, FLACExporter, M4AExporter


class TestPluginBase:
    """PluginBase 测试类"""
    
    def test_plugin_base_attributes(self):
        """测试插件基类属性"""
        class TestPlugin(PluginBase):
            name = "test_plugin"
            version = "1.0.0"
            description = "Test plugin"
            
            async def initialize(self) -> bool:
                return True
            
            async def shutdown(self) -> None:
                pass
        
        plugin = TestPlugin()
        
        assert plugin.name == "test_plugin"
        assert plugin.version == "1.0.0"
        assert plugin.description == "Test plugin"
        assert plugin._initialized is False
    
    @pytest.mark.asyncio
    async def test_plugin_initialization(self):
        """测试插件初始化"""
        class TestPlugin(PluginBase):
            async def initialize(self) -> bool:
                self._initialized = True
                return True
            
            async def shutdown(self) -> None:
                self._initialized = False
        
        plugin = TestPlugin()
        result = await plugin.initialize()
        
        assert result is True
        assert plugin._initialized is True
        
        await plugin.shutdown()
        assert plugin._initialized is False
    
    def test_plugin_get_info(self):
        """测试获取插件信息"""
        class TestPlugin(PluginBase):
            name = "info_plugin"
            version = "2.0.0"
            description = "Info test"
            
            async def initialize(self) -> bool:
                return True
            
            async def shutdown(self) -> None:
                pass
        
        plugin = TestPlugin()
        info = plugin.get_info()
        
        assert info["name"] == "info_plugin"
        assert info["version"] == "2.0.0"
        assert info["description"] == "Info test"
        assert info["initialized"] is False
    
    def test_plugin_with_config(self):
        """测试带配置的插件"""
        class TestPlugin(PluginBase):
            async def initialize(self) -> bool:
                return True
            
            async def shutdown(self) -> None:
                pass
        
        config = {"key": "value", "number": 42}
        plugin = TestPlugin(config=config)
        
        assert plugin.config == config


class TestPluginRegistry:
    """PluginRegistry 测试类"""
    
    def test_registry_singleton(self):
        """测试注册表单例模式"""
        registry1 = PluginRegistry()
        registry2 = PluginRegistry()
        
        assert registry1 is registry2
    
    def test_register_source(self):
        """测试注册音源插件"""
        registry = PluginRegistry()
        
        mock_source = AsyncMock(spec=SourcePlugin)
        mock_source.name = "test_source"
        
        registry.register_source("test", mock_source)
        
        assert registry.get_source("test") == mock_source
        assert "test" in registry.list_sources()
    
    def test_register_downloader(self):
        """测试注册下载器插件"""
        registry = PluginRegistry()
        
        mock_downloader = AsyncMock(spec=DownloaderPlugin)
        mock_downloader.name = "test_downloader"
        
        registry.register_downloader("test", mock_downloader)
        
        assert registry.get_downloader("test") == mock_downloader
        assert "test" in registry.list_downloaders()
    
    def test_register_exporter(self):
        """测试注册导出器插件"""
        registry = PluginRegistry()
        
        mock_exporter = AsyncMock(spec=ExporterPlugin)
        mock_exporter.name = "test_exporter"
        
        registry.register_exporter("test", mock_exporter)
        
        assert registry.get_exporter("test") == mock_exporter
        assert "test" in registry.list_exporters()
    
    def test_get_nonexistent_plugin(self):
        """测试获取不存在的插件"""
        registry = PluginRegistry()
        
        assert registry.get_source("nonexistent") is None
        assert registry.get_downloader("nonexistent") is None
        assert registry.get_exporter("nonexistent") is None
    
    def test_unregister_plugins(self):
        """测试注销插件"""
        registry = PluginRegistry()
        
        mock_source = AsyncMock(spec=SourcePlugin)
        registry.register_source("test", mock_source)
        
        result = registry.unregister_source("test")
        assert result is True
        assert registry.get_source("test") is None
        
        # 再次注销应返回 False
        result = registry.unregister_source("test")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_initialize_all_plugins(self):
        """测试初始化所有插件"""
        registry = PluginRegistry()
        
        mock_source = AsyncMock(spec=SourcePlugin)
        mock_source.initialize = AsyncMock(return_value=True)
        mock_source.name = "source"
        
        mock_downloader = AsyncMock(spec=DownloaderPlugin)
        mock_downloader.initialize = AsyncMock(return_value=True)
        mock_downloader.name = "downloader"
        
        mock_exporter = AsyncMock(spec=ExporterPlugin)
        mock_exporter.initialize = AsyncMock(return_value=True)
        mock_exporter.name = "exporter"
        
        registry.register_source("test_source", mock_source)
        registry.register_downloader("test_downloader", mock_downloader)
        registry.register_exporter("test_exporter", mock_exporter)
        
        await registry.initialize_all()
        
        mock_source.initialize.assert_called_once()
        mock_downloader.initialize.assert_called_once()
        mock_exporter.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_all_plugins(self):
        """测试关闭所有插件"""
        registry = PluginRegistry()
        
        mock_source = AsyncMock(spec=SourcePlugin)
        mock_source.shutdown = AsyncMock()
        
        mock_downloader = AsyncMock(spec=DownloaderPlugin)
        mock_downloader.shutdown = AsyncMock()
        
        registry.register_source("test", mock_source)
        registry.register_downloader("test", mock_downloader)
        
        await registry.shutdown_all()
        
        mock_source.shutdown.assert_called_once()
        mock_downloader.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_plugin_initialization_error(self):
        """测试插件初始化错误处理"""
        registry = PluginRegistry()
        
        mock_source = AsyncMock(spec=SourcePlugin)
        mock_source.initialize = AsyncMock(side_effect=Exception("Init failed"))
        mock_source.name = "failing_source"
        
        registry.register_source("failing", mock_source)
        
        # 不应抛出异常
        await registry.initialize_all()
        
        # 验证被调用
        mock_source.initialize.assert_called_once()


class TestHTTPDownloader:
    """HTTPDownloader 测试类"""
    
    def test_downloader_attributes(self):
        """测试下载器属性"""
        downloader = HTTPDownloader()
        
        assert downloader.name == "http"
        assert downloader.version == "1.0.0"
        assert downloader.supports_resume is True
    
    @pytest.mark.asyncio
    async def test_downloader_initialize(self):
        """测试下载器初始化"""
        downloader = HTTPDownloader()
        
        result = await downloader.initialize()
        
        assert result is True
        assert downloader._initialized is True
        assert downloader._session is not None
        
        await downloader.shutdown()
    
    @pytest.mark.asyncio
    async def test_downloader_download_success(self, temp_dir, mock_http_response):
        """测试成功下载"""
        downloader = HTTPDownloader({"chunk_size": 1024})
        await downloader.initialize()
        
        # Mock session
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.stream = MagicMock(return_value=mock_context)
        downloader._session = mock_session
        
        output_path = temp_dir / "test_download.mp3"
        
        result = await downloader.download(
            url="https://example.com/test.mp3",
            dest=output_path
        )
        
        assert result["success"] is True
        assert output_path.exists()
        
        await downloader.shutdown()
    
    @pytest.mark.asyncio
    async def test_downloader_download_with_resume(self, temp_dir):
        """测试断点续传下载"""
        downloader = HTTPDownloader()
        await downloader.initialize()
        
        # Mock response for range request
        mock_response = MagicMock()
        mock_response.status_code = 206
        mock_response.headers = {"content-length": "500"}
        mock_response.aiter_bytes = AsyncMock()
        mock_response.aiter_bytes.return_value.__aiter__ = AsyncMock(return_value=iter([b"chunk"]))
        
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.stream = MagicMock(return_value=mock_context)
        downloader._session = mock_session
        
        resume_data = {"downloaded_bytes": 1000}
        output_path = temp_dir / "resume_download.mp3"
        
        result = await downloader.download(
            url="https://example.com/test.mp3",
            dest=output_path,
            resume_data=resume_data
        )
        
        # 验证 Range header 被使用
        mock_session.stream.assert_called_once()
        call_args = mock_session.stream.call_args
        assert "headers" in call_args[1]
        assert call_args[1]["headers"]["Range"] == "bytes=1000-"
        
        await downloader.shutdown()
    
    @pytest.mark.asyncio
    async def test_downloader_download_http_error(self, temp_dir):
        """测试 HTTP 错误处理"""
        downloader = HTTPDownloader()
        await downloader.initialize()
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.stream = MagicMock(return_value=mock_context)
        downloader._session = mock_session
        
        output_path = temp_dir / "error_download.mp3"
        
        result = await downloader.download(
            url="https://example.com/notfound.mp3",
            dest=output_path
        )
        
        assert result["success"] is False
        assert "HTTP 404" in result["error"]
        
        await downloader.shutdown()
    
    @pytest.mark.asyncio
    async def test_downloader_download_with_progress_callback(self, temp_dir):
        """测试下载进度回调"""
        downloader = HTTPDownloader()
        await downloader.initialize()
        
        progress_calls = []
        
        def progress_callback(downloaded, total):
            progress_calls.append((downloaded, total))
        
        # Mock response with chunks
        async def mock_aiter_bytes(chunk_size):
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "18"}
        mock_response.aiter_bytes = mock_aiter_bytes
        
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.stream = MagicMock(return_value=mock_context)
        downloader._session = mock_session
        
        output_path = temp_dir / "progress_download.mp3"
        
        result = await downloader.download(
            url="https://example.com/test.mp3",
            dest=output_path,
            progress_callback=progress_callback
        )
        
        assert len(progress_calls) > 0
        
        await downloader.shutdown()


class TestExporters:
    """导出器测试类"""
    
    def test_mp3_exporter_attributes(self):
        """测试 MP3 导出器属性"""
        exporter = MP3Exporter()
        
        assert exporter.name == "mp3"
        assert "mp3" in exporter.supported_formats
    
    def test_flac_exporter_attributes(self):
        """测试 FLAC 导出器属性"""
        exporter = FLACExporter()
        
        assert exporter.name == "flac"
        assert "flac" in exporter.supported_formats
    
    def test_m4a_exporter_attributes(self):
        """测试 M4A 导出器属性"""
        exporter = M4AExporter()
        
        assert exporter.name == "m4a"
        assert "m4a" in exporter.supported_formats
    
    @pytest.mark.asyncio
    async def test_mp3_exporter_export(self, temp_dir):
        """测试 MP3 导出"""
        exporter = MP3Exporter()
        await exporter.initialize()
        
        # 创建输入文件
        input_file = temp_dir / "input.tmp"
        input_file.write_bytes(b"fake audio data")
        
        output_path = await exporter.export(input_file, "mp3")
        
        assert output_path.suffix == ".mp3"
        assert output_path.exists()
        
        await exporter.shutdown()
    
    @pytest.mark.asyncio
    async def test_mp3_exporter_write_metadata(self, temp_dir):
        """测试 MP3 元数据写入"""
        exporter = MP3Exporter()
        await exporter.initialize()
        
        test_file = temp_dir / "test.mp3"
        test_file.write_bytes(b"fake mp3 data")
        
        metadata = {
            "title": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album"
        }
        
        with patch('musichub.plugins.exporters.base.MP3') as mock_mp3:
            mock_audio = MagicMock()
            mock_audio.tags = None
            mock_mp3.return_value = mock_audio
            
            result = await exporter.write_metadata(test_file, metadata)
            
            assert result is True
            mock_audio.add_tags.assert_called_once()
            mock_audio.save.assert_called_once()
        
        await exporter.shutdown()
    
    @pytest.mark.asyncio
    async def test_flac_exporter_export(self, temp_dir):
        """测试 FLAC 导出"""
        exporter = FLACExporter()
        await exporter.initialize()
        
        input_file = temp_dir / "input.tmp"
        input_file.write_bytes(b"fake audio data")
        
        output_path = await exporter.export(input_file, "flac")
        
        assert output_path.suffix == ".flac"
        
        await exporter.shutdown()
    
    @pytest.mark.asyncio
    async def test_m4a_exporter_export(self, temp_dir):
        """测试 M4A 导出"""
        exporter = M4AExporter()
        await exporter.initialize()
        
        input_file = temp_dir / "input.tmp"
        input_file.write_bytes(b"fake audio data")
        
        output_path = await exporter.export(input_file, "m4a")
        
        assert output_path.suffix == ".m4a"
        
        await exporter.shutdown()
    
    @pytest.mark.asyncio
    async def test_exporter_file_not_found(self, temp_dir):
        """测试文件不存在错误"""
        exporter = MP3Exporter()
        await exporter.initialize()
        
        nonexistent = temp_dir / "nonexistent.tmp"
        
        with pytest.raises(FileNotFoundError):
            await exporter.export(nonexistent, "mp3")
        
        await exporter.shutdown()


class TestSourcePluginInterface:
    """音源插件接口测试"""
    
    @pytest.mark.asyncio
    async def test_source_plugin_interface(self):
        """测试音源插件接口实现"""
        class MockSourcePlugin(SourcePlugin):
            name = "mock_source"
            version = "1.0.0"
            description = "Mock source for testing"
            
            async def initialize(self) -> bool:
                self._initialized = True
                return True
            
            async def shutdown(self) -> None:
                self._initialized = False
            
            async def search(self, query: str, limit: int = 20):
                return [{"id": "1", "title": query}]
            
            async def get_track_info(self, track_id: str):
                return {"id": track_id, "title": "Test"}
            
            async def get_stream_url(self, track_id: str):
                return f"https://example.com/stream/{track_id}"
        
        plugin = MockSourcePlugin()
        
        # 测试初始化
        assert await plugin.initialize() is True
        assert plugin._initialized is True
        
        # 测试搜索
        results = await plugin.search("test query", limit=10)
        assert len(results) == 1
        
        # 测试获取音轨信息
        info = await plugin.get_track_info("track_001")
        assert info["id"] == "track_001"
        
        # 测试获取流 URL
        url = await plugin.get_stream_url("track_001")
        assert "track_001" in url
        
        # 测试关闭
        await plugin.shutdown()
        assert plugin._initialized is False


class TestPluginIntegration:
    """插件集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_plugin_workflow(self, temp_dir):
        """测试完整插件工作流程"""
        registry = PluginRegistry()
        
        # 注册下载器
        downloader = HTTPDownloader()
        registry.register_downloader("http", downloader)
        
        # 注册导出器
        mp3_exporter = MP3Exporter()
        registry.register_exporter("mp3", mp3_exporter)
        
        # 初始化所有插件
        await registry.initialize_all()
        
        # 验证插件已注册
        assert registry.get_downloader("http") is not None
        assert registry.get_exporter("mp3") is not None
        
        # 关闭所有插件
        await registry.shutdown_all()
    
    def test_plugin_registry_list_operations(self):
        """测试插件列表操作"""
        registry = PluginRegistry()
        
        # 初始应为空
        assert len(registry.list_sources()) == 0
        assert len(registry.list_downloaders()) == 0
        assert len(registry.list_exporters()) == 0
        
        # 添加插件
        registry.register_source("source1", AsyncMock())
        registry.register_source("source2", AsyncMock())
        registry.register_downloader("downloader1", AsyncMock())
        registry.register_exporter("exporter1", AsyncMock())
        registry.register_exporter("exporter2", AsyncMock())
        
        # 验证列表
        assert len(registry.list_sources()) == 2
        assert len(registry.list_downloaders()) == 1
        assert len(registry.list_exporters()) == 2
