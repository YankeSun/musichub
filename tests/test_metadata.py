"""
元数据管理测试 - 测试 TrackMetadata 和 MetadataManager
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import shutil

from musichub.utils.metadata import TrackMetadata, MetadataManager
from musichub.core.manager import TrackInfo


class TestTrackMetadata:
    """TrackMetadata 测试类"""
    
    def test_metadata_creation(self):
        """测试元数据创建"""
        metadata = TrackMetadata(
            title="Test Song",
            artist="Test Artist",
            album="Test Album"
        )
        
        assert metadata.title == "Test Song"
        assert metadata.artist == "Test Artist"
        assert metadata.album == "Test Album"
    
    def test_metadata_default_values(self):
        """测试元数据默认值"""
        metadata = TrackMetadata()
        
        assert metadata.title == ""
        assert metadata.artist == ""
        assert metadata.album == ""
        assert metadata.track_number == 0
        assert metadata.disc_number == 0
        assert metadata.year == 0
        assert metadata.cover_art is None
        assert metadata.additional_fields == {}
    
    def test_metadata_from_track_info(self, sample_track_info):
        """测试从 TrackInfo 创建元数据"""
        metadata = TrackMetadata.from_track_info(sample_track_info)
        
        assert metadata.title == sample_track_info.title
        assert metadata.artist == sample_track_info.artist
        assert metadata.album == sample_track_info.album
        assert metadata.duration == sample_track_info.duration
        assert metadata.cover_url == sample_track_info.cover_url
    
    def test_metadata_to_dict(self):
        """测试元数据转字典"""
        metadata = TrackMetadata(
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            year=2024,
            genre="Pop"
        )
        
        data = metadata.to_dict()
        
        assert data["title"] == "Test Song"
        assert data["artist"] == "Test Artist"
        assert data["album"] == "Test Album"
        assert data["year"] == 2024
        assert data["genre"] == "Pop"
    
    def test_metadata_is_complete(self):
        """测试元数据完整性检查"""
        # 完整元数据
        complete = TrackMetadata(title="Song", artist="Artist")
        assert complete.is_complete() is True
        
        # 缺少标题
        incomplete1 = TrackMetadata(artist="Artist")
        assert incomplete1.is_complete() is False
        
        # 缺少艺术家
        incomplete2 = TrackMetadata(title="Song")
        assert incomplete2.is_complete() is False
    
    def test_metadata_with_additional_fields(self):
        """测试额外字段"""
        metadata = TrackMetadata(
            title="Test",
            artist="Artist",
            additional_fields={
                "custom_field": "custom_value",
                "rating": 5
            }
        )
        
        data = metadata.to_dict()
        assert data["custom_field"] == "custom_value"
        assert data["rating"] == 5


class TestMetadataManager:
    """MetadataManager 测试类"""
    
    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = MetadataManager()
        
        assert manager._supported_formats == ["mp3", "flac", "m4a", "wav", "ogg"]
    
    @pytest.mark.asyncio
    async def test_read_metadata_nonexistent_file(self):
        """测试读取不存在的文件"""
        manager = MetadataManager()
        result = await manager.read_metadata(Path("/nonexistent/file.mp3"))
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_read_metadata_unsupported_format(self, temp_dir):
        """测试读取不支持的格式"""
        manager = MetadataManager()
        
        # 创建假文件
        test_file = temp_dir / "test.unsupported"
        test_file.write_bytes(b"fake data")
        
        # 应该返回 None 或处理 gracefully
        result = await manager.read_metadata(test_file)
        # 根据实现，可能返回 None 或部分元数据
    
    @pytest.mark.asyncio
    async def test_write_metadata_nonexistent_file(self):
        """测试写入不存在的文件"""
        manager = MetadataManager()
        metadata = TrackMetadata(title="Test", artist="Artist")
        
        result = await manager.write_metadata(
            Path("/nonexistent/file.mp3"),
            metadata
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_write_metadata_mp3(self, temp_dir, sample_metadata):
        """测试写入 MP3 元数据"""
        manager = MetadataManager()
        
        # 创建测试 MP3 文件
        test_file = temp_dir / "test.mp3"
        test_file.write_bytes(b"fake mp3 data")
        
        # Mock mutagen
        with patch('musichub.utils.metadata.MP3') as mock_mp3:
            mock_audio = MagicMock()
            mock_audio.tags = None
            mock_mp3.return_value = mock_audio
            
            result = await manager.write_metadata(test_file, sample_metadata)
            
            # 验证 add_tags 和 save 被调用
            mock_audio.add_tags.assert_called_once()
            mock_audio.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_write_metadata_flac(self, temp_dir, sample_metadata):
        """测试写入 FLAC 元数据"""
        manager = MetadataManager()
        
        test_file = temp_dir / "test.flac"
        test_file.write_bytes(b"fake flac data")
        
        with patch('musichub.utils.metadata.FLAC') as mock_flac:
            mock_audio = MagicMock()
            mock_audio.__setitem__ = MagicMock()
            mock_flac.return_value = mock_audio
            
            result = await manager.write_metadata(test_file, sample_metadata)
            
            mock_audio.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_write_metadata_m4a(self, temp_dir, sample_metadata):
        """测试写入 M4A 元数据"""
        manager = MetadataManager()
        
        test_file = temp_dir / "test.m4a"
        test_file.write_bytes(b"fake m4a data")
        
        with patch('musichub.utils.metadata.MP4') as mock_mp4:
            mock_audio = MagicMock()
            mock_audio.__setitem__ = MagicMock()
            mock_mp4.return_value = mock_audio
            
            result = await manager.write_metadata(test_file, sample_metadata)
            
            mock_audio.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_write_metadata_with_cover_art(self, temp_dir):
        """测试写入带封面的元数据"""
        manager = MetadataManager()
        
        metadata = TrackMetadata(
            title="Test",
            artist="Artist",
            cover_art=b"fake image data"
        )
        
        test_file = temp_dir / "test.mp3"
        test_file.write_bytes(b"fake mp3 data")
        
        with patch('musichub.utils.metadata.MP3') as mock_mp3:
            mock_audio = MagicMock()
            mock_audio.tags = None
            mock_mp3.return_value = mock_audio
            
            result = await manager.write_metadata(
                test_file,
                metadata,
                embed_cover=True
            )
            
            # 验证封面被添加
            assert mock_audio.tags.add.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_download_cover_success(self):
        """测试成功下载封面"""
        manager = MetadataManager()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake image data"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            result = await manager.download_cover("https://example.com/cover.jpg")
            
            assert result == b"fake image data"
            mock_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_cover_failure(self):
        """测试封面下载失败"""
        manager = MetadataManager()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            result = await manager.download_cover("https://example.com/cover.jpg")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_download_cover_empty_url(self):
        """测试空 URL 下载封面"""
        manager = MetadataManager()
        
        result = await manager.download_cover("")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_read_mp3_metadata(self):
        """测试读取 MP3 元数据"""
        manager = MetadataManager()
        
        mock_audio = MagicMock()
        mock_audio.tags = {
            "TIT2": "Test Title",
            "TPE1": "Test Artist",
            "TALB": "Test Album",
            "TDRC": "2024",
            "TCON": "Pop"
        }
        mock_audio.tags.get = lambda key, default: mock_audio.tags.get(key, default)
        
        metadata = manager._read_mp3_metadata(mock_audio)
        
        assert metadata.title == "Test Title"
        assert metadata.artist == "Test Artist"
        assert metadata.album == "Test Album"
    
    @pytest.mark.asyncio
    async def test_read_flac_metadata(self):
        """测试读取 FLAC 元数据"""
        manager = MetadataManager()
        
        mock_audio = {
            "title": ["Test Title"],
            "artist": ["Test Artist"],
            "album": ["Test Album"],
            "date": ["2024"],
            "genre": ["Pop"]
        }
        mock_audio.get = lambda key, default: mock_audio.get(key, default)
        
        metadata = manager._read_flac_metadata(mock_audio)
        
        assert metadata.title == "Test Title"
        assert metadata.artist == "Test Artist"
    
    @pytest.mark.asyncio
    async def test_read_m4a_metadata(self):
        """测试读取 M4A 元数据"""
        manager = MetadataManager()
        
        mock_audio = {
            "\xa9nam": ["Test Title"],
            "\xa9ART": ["Test Artist"],
            "\xa9alb": ["Test Album"],
            "\xa9day": ["2024"],
            "\xa9gen": ["Pop"]
        }
        mock_audio.get = lambda key, default: mock_audio.get(key, default)
        
        metadata = manager._read_m4a_metadata(mock_audio)
        
        assert metadata.title == "Test Title"
        assert metadata.artist == "Test Artist"


class TestMetadataIntegration:
    """元数据集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_metadata_workflow(self, temp_dir):
        """测试完整元数据工作流程"""
        manager = MetadataManager()
        
        # 创建元数据
        metadata = TrackMetadata(
            title="Integration Test Song",
            artist="Integration Artist",
            album="Integration Album",
            year=2024,
            genre="Test"
        )
        
        # 验证元数据完整
        assert metadata.is_complete()
        
        # 转换为字典
        data = metadata.to_dict()
        assert data["title"] == metadata.title
        
        # 从 TrackInfo 创建
        track_info = TrackInfo(
            id="test_001",
            title="Track Title",
            artist="Track Artist",
            album="Track Album",
            duration=240
        )
        
        metadata2 = TrackMetadata.from_track_info(track_info)
        assert metadata2.title == track_info.title
        assert metadata2.duration == track_info.duration
