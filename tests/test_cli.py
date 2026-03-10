"""
CLI 功能测试 - 测试命令行接口
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typer.testing import CliRunner

from musichub.cli.main import app
from musichub.core.engine import DownloadEngine
from musichub.core.config import Config
from musichub.core.manager import TrackInfo
from musichub.plugins.base import PluginRegistry


runner = CliRunner()


class TestCLISearch:
    """CLI 搜索命令测试"""
    
    @pytest.mark.asyncio
    async def test_search_command_basic(self):
        """测试基本搜索命令"""
        # Mock engine
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        search_result = MagicMock()
        search_result.source = "test_source"
        search_result.query = "test song"
        search_result.total = 2
        search_result.tracks = [
            TrackInfo(id="1", title="Test Song 1", artist="Artist 1", duration=180),
            TrackInfo(id="2", title="Test Song 2", artist="Artist 2", duration=240)
        ]
        mock_engine.search = AsyncMock(return_value=search_result)
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, ["search", "test song", "--source", "test_source", "--limit", "10"])
        
        assert result.exit_code == 0
        assert "Test Song 1" in result.stdout
        assert "Test Song 2" in result.stdout
        assert "Artist 1" in result.stdout
        mock_engine.search.assert_called_once_with("test song", source="test_source", limit=10)
    
    @pytest.mark.asyncio
    async def test_search_command_no_results(self):
        """测试搜索无结果"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        search_result = MagicMock()
        search_result.source = "test_source"
        search_result.query = "nonexistent"
        search_result.total = 0
        search_result.tracks = []
        mock_engine.search = AsyncMock(return_value=search_result)
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, ["search", "nonexistent"])
        
        assert result.exit_code == 0
        assert "共 0 条" in result.stdout
    
    @pytest.mark.asyncio
    async def test_search_command_with_duration(self):
        """测试搜索结果显示时长"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        search_result = MagicMock()
        search_result.source = "test"
        search_result.query = "test"
        search_result.total = 1
        search_result.tracks = [
            TrackInfo(id="1", title="Long Song", artist="Artist", duration=3661)  # 1:01:01
        ]
        mock_engine.search = AsyncMock(return_value=search_result)
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, ["search", "test"])
        
        assert result.exit_code == 0
        assert "61:01" in result.stdout  # 3661 秒 = 61 分 01 秒


class TestCLIDownload:
    """CLI 下载命令测试"""
    
    @pytest.mark.asyncio
    async def test_download_command_success(self, temp_dir):
        """测试成功下载"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        # Mock search result
        search_result = MagicMock()
        search_result.tracks = [
            TrackInfo(id="1", title="Test Song", artist="Artist", source="test")
        ]
        
        # Mock download result
        download_result = MagicMock()
        download_result.success = True
        download_result.output_path = temp_dir / "output.mp3"
        
        mock_engine.search = AsyncMock(return_value=search_result)
        mock_engine.download = AsyncMock(return_value=download_result)
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, [
                "download",
                "test song",
                "--format",
                "mp3",
                "--output",
                str(temp_dir / "output.mp3")
            ])
        
        assert result.exit_code == 0
        assert "开始下载" in result.stdout
        assert "下载完成" in result.stdout
        mock_engine.search.assert_called_once()
        mock_engine.download.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_command_not_found(self):
        """测试下载未找到音乐"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        search_result = MagicMock()
        search_result.tracks = []
        mock_engine.search = AsyncMock(return_value=search_result)
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, ["download", "nonexistent"])
        
        assert result.exit_code == 1
        assert "未找到匹配的音乐" in result.stdout
    
    @pytest.mark.asyncio
    async def test_download_command_failure(self):
        """测试下载失败"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        search_result = MagicMock()
        search_result.tracks = [TrackInfo(id="1", title="Test", artist="Artist")]
        
        download_result = MagicMock()
        download_result.success = False
        download_result.error_message = "Network error"
        
        mock_engine.search = AsyncMock(return_value=search_result)
        mock_engine.download = AsyncMock(return_value=download_result)
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, ["download", "test song"])
        
        assert result.exit_code == 1
        assert "下载失败" in result.stdout
        assert "Network error" in result.stdout
    
    @pytest.mark.asyncio
    async def test_download_with_format_option(self):
        """测试下载格式选项"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        search_result = MagicMock()
        search_result.tracks = [TrackInfo(id="1", title="Test", artist="Artist")]
        
        download_result = MagicMock()
        download_result.success = True
        download_result.output_path = Path("/tmp/test.flac")
        
        mock_engine.search = AsyncMock(return_value=search_result)
        mock_engine.download = AsyncMock(return_value=download_result)
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, ["download", "test", "--format", "flac"])
        
        assert result.exit_code == 0
        # 验证 format 参数被传递
        call_args = mock_engine.download.call_args
        assert call_args[1]["output_format"] == "flac"


class TestCLIVersion:
    """CLI 版本命令测试"""
    
    def test_version_command(self):
        """测试版本命令"""
        result = runner.invoke(app, ["version"])
        
        assert result.exit_code == 0
        assert "MusicHub v" in result.stdout


class TestCLIPlugins:
    """CLI 插件命令测试"""
    
    def test_plugins_command(self):
        """测试插件列表命令"""
        # Mock registry
        mock_registry = MagicMock()
        mock_registry.list_sources.return_value = ["netease", "qqmusic"]
        mock_registry.list_downloaders.return_value = ["http"]
        mock_registry.list_exporters.return_value = ["mp3", "flac"]
        
        mock_source = MagicMock()
        mock_source.description = "Netease source"
        mock_registry.get_source.return_value = mock_source
        
        mock_downloader = MagicMock()
        mock_downloader.description = "HTTP downloader"
        mock_registry.get_downloader.return_value = mock_downloader
        
        mock_exporter = MagicMock()
        mock_exporter.description = "MP3 exporter"
        mock_registry.get_exporter.return_value = mock_exporter
        
        with patch('musichub.cli.main.PluginRegistry.load_from_entry_points', return_value=mock_registry):
            result = runner.invoke(app, ["plugins"])
        
        assert result.exit_code == 0
        assert "音源插件" in result.stdout
        assert "下载器插件" in result.stdout
        assert "导出器插件" in result.stdout
        assert "netease" in result.stdout
        assert "http" in result.stdout
        assert "mp3" in result.stdout


class TestCLIBatch:
    """CLI 批量下载命令测试"""
    
    @pytest.mark.asyncio
    async def test_batch_command(self):
        """测试批量下载命令"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, [
                "batch",
                "https://playlist.example.com/123",
                "--format",
                "mp3",
                "--concurrency",
                "5"
            ])
        
        assert result.exit_code == 0
        assert "批量下载歌单" in result.stdout


class TestCLIHelp:
    """CLI 帮助命令测试"""
    
    def test_help_command(self):
        """测试帮助命令"""
        result = runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "musichub" in result.stdout
        assert "search" in result.stdout
        assert "download" in result.stdout
        assert "batch" in result.stdout
        assert "version" in result.stdout
        assert "plugins" in result.stdout
    
    def test_search_help(self):
        """测试搜索命令帮助"""
        result = runner.invoke(app, ["search", "--help"])
        
        assert result.exit_code == 0
        assert "搜索关键词" in result.stdout
        assert "--source" in result.stdout
        assert "--limit" in result.stdout
    
    def test_download_help(self):
        """测试下载命令帮助"""
        result = runner.invoke(app, ["download", "--help"])
        
        assert result.exit_code == 0
        assert "--format" in result.stdout
        assert "--output" in result.stdout
        assert "--concurrency" in result.stdout


class TestCLIGetEngine:
    """get_engine 函数测试"""
    
    def test_get_engine_creation(self):
        """测试 get_engine 函数"""
        from musichub.cli.main import get_engine
        
        with patch('musichub.cli.main.Config') as mock_config, \
             patch('musichub.cli.main.PluginRegistry') as mock_registry:
            
            mock_config_instance = MagicMock()
            mock_config.return_value = mock_config_instance
            
            mock_registry_instance = MagicMock()
            mock_registry.load_from_entry_points.return_value = mock_registry_instance
            
            engine = get_engine()
            
            mock_config.assert_called_once()
            mock_registry.load_from_entry_points.assert_called_once()


class TestCLIIntegration:
    """CLI 集成测试"""
    
    @pytest.mark.asyncio
    async def test_search_then_download_workflow(self, temp_dir):
        """测试搜索后下载的工作流程"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        # 第一次调用返回搜索结果
        search_result = MagicMock()
        search_result.tracks = [TrackInfo(id="1", title="Target Song", artist="Artist")]
        
        # 第二次调用返回下载结果
        download_result = MagicMock()
        download_result.success = True
        download_result.output_path = temp_dir / "downloaded.mp3"
        
        mock_engine.search = AsyncMock(return_value=search_result)
        mock_engine.download = AsyncMock(return_value=download_result)
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            # 先搜索
            search_result = runner.invoke(app, ["search", "target song"])
            assert search_result.exit_code == 0
            
            # 再下载
            download_result = runner.invoke(app, ["download", "target song"])
            assert download_result.exit_code == 0
        
        # 验证调用顺序
        assert mock_engine.search.call_count >= 1
        assert mock_engine.download.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_cli_error_handling(self):
        """测试 CLI 错误处理"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock(side_effect=Exception("Init failed"))
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, ["search", "test"])
        
        # 异常应该被传播或处理
        # 根据实现，可能 exit_code 不为 0
        assert result.exit_code != 0 or "Init failed" in str(result.exception)


class TestCLIConcurreny:
    """CLI 并发选项测试"""
    
    @pytest.mark.asyncio
    async def test_download_concurrency_option(self):
        """测试下载并发选项"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        search_result = MagicMock()
        search_result.tracks = [TrackInfo(id="1", title="Test", artist="Artist")]
        
        download_result = MagicMock()
        download_result.success = True
        
        mock_engine.search = AsyncMock(return_value=search_result)
        mock_engine.download = AsyncMock(return_value=download_result)
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, [
                "download",
                "test",
                "--concurrency",
                "10"
            ])
        
        assert result.exit_code == 0


class TestCLIOutput:
    """CLI 输出格式测试"""
    
    @pytest.mark.asyncio
    async def test_search_output_format(self):
        """测试搜索输出格式"""
        mock_engine = AsyncMock(spec=DownloadEngine)
        mock_engine.initialize = AsyncMock()
        mock_engine.shutdown = AsyncMock()
        
        search_result = MagicMock()
        search_result.source = "netease"
        search_result.query = "test"
        search_result.total = 1
        search_result.tracks = [
            TrackInfo(
                id="1",
                title="Test Song",
                artist="Test Artist",
                album="Test Album",
                duration=200
            )
        ]
        
        mock_engine.search = AsyncMock(return_value=search_result)
        
        with patch('musichub.cli.main.get_engine', return_value=mock_engine):
            result = runner.invoke(app, ["search", "test"])
        
        assert result.exit_code == 0
        # 验证输出包含所有字段
        assert "搜索结果" in result.stdout
        assert "netease" in result.stdout
        assert "Test Song" in result.stdout
        assert "Test Artist" in result.stdout
        assert "Test Album" in result.stdout
        assert "3:20" in result.stdout  # 200 秒 = 3:20
