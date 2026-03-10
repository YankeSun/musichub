"""
Apple Music 插件单元测试
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from musichub.providers.apple_music import (
    AppleMusicProvider,
    AppleMusicConfig,
    AudioQuality,
    SpatialAudio,
    AppleMusicError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    AppleMusicTrackInfo,
)


class TestAppleMusicConfig:
    """测试配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = AppleMusicConfig()
        assert config.country == "US"
        assert config.language == "en-US"
        assert config.audio_quality == AudioQuality.LOSSLESS
        assert config.spatial_audio == SpatialAudio.STEREO
        assert config.timeout == 30
        assert config.max_retries == 3
    
    def test_from_dict(self):
        """测试从字典创建配置"""
        data = {
            "api_token": "test_token",
            "music_user_token": "user_token",
            "country": "CN",
            "language": "zh-CN",
            "audio_quality": "hi_res",
            "spatial_audio": "dolby_atmos",
            "timeout": 60,
            "max_retries": 5
        }
        
        config = AppleMusicConfig.from_dict(data)
        assert config.api_token == "test_token"
        assert config.music_user_token == "user_token"
        assert config.country == "CN"
        assert config.language == "zh-CN"
        assert config.audio_quality == AudioQuality.HI_RES
        assert config.spatial_audio == SpatialAudio.DOLBY_ATMOS
        assert config.timeout == 60
        assert config.max_retries == 5
    
    def test_from_dict_with_enums(self):
        """测试从字典创建配置（枚举类型）"""
        data = {
            "audio_quality": AudioQuality.LOSSLESS,
            "spatial_audio": SpatialAudio.STEREO
        }
        
        config = AppleMusicConfig.from_dict(data)
        assert config.audio_quality == AudioQuality.LOSSLESS
        assert config.spatial_audio == SpatialAudio.STEREO


class TestAppleMusicProvider:
    """测试插件类"""
    
    @pytest.fixture
    def provider(self):
        """创建测试用插件实例"""
        config = {
            "api_token": "test_token",
            "music_user_token": "test_user_token",
            "country": "US"
        }
        return AppleMusicProvider(config)
    
    def test_initialization(self, provider):
        """测试初始化"""
        assert provider.name == "apple_music"
        assert provider.version == "1.0.0"
        assert provider.description != ""
        assert provider._initialized is False
    
    def test_validate_config_success(self, provider):
        """测试配置验证（成功）"""
        assert provider.validate_config() is True
    
    def test_validate_config_missing_token(self):
        """测试配置验证（缺少 Token）"""
        provider = AppleMusicProvider({})
        assert provider.validate_config() is False
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, provider):
        """测试初始化成功"""
        with patch.object(provider, '_validate_token', new_callable=AsyncMock):
            with patch('aiohttp.ClientSession'):
                result = await provider.initialize()
                assert result is True
                assert provider._initialized is True
    
    @pytest.mark.asyncio
    async def test_initialize_missing_token(self):
        """测试初始化失败（缺少 Token）"""
        provider = AppleMusicProvider({})
        result = await provider.initialize()
        assert result is False
        assert provider._initialized is False
    
    @pytest.mark.asyncio
    async def test_shutdown(self, provider):
        """测试关闭插件"""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        provider._session = mock_session
        provider._initialized = True
        
        await provider.shutdown()
        
        assert provider._initialized is False
        mock_session.close.assert_called_once()
    
    def test_get_quality_info(self, provider):
        """测试获取音质信息"""
        info = provider.get_quality_info(AudioQuality.STANDARD)
        assert info["codec"] == "AAC"
        assert info["bitrate"] == 256
        
        info = provider.get_quality_info(AudioQuality.LOSSLESS)
        assert info["codec"] == "ALAC"
        assert info["bitrate"] == 1411
        assert info["sample_rate"] == 44100
        assert info["bit_depth"] == 16
        
        info = provider.get_quality_info(AudioQuality.HI_RES)
        assert info["codec"] == "ALAC"
        assert info["bitrate"] == 4608
        assert info["sample_rate"] == 192000
        assert info["bit_depth"] == 24
    
    def test_parse_track(self, provider):
        """测试解析音轨数据"""
        track_data = {
            "id": "1234567890",
            "attributes": {
                "name": "Test Song",
                "artistName": "Test Artist",
                "albumName": "Test Album",
                "durationInMillis": 180000,
                "releaseDate": "2024-01-01",
                "genreNames": ["Pop"],
                "trackNumber": 1,
                "isrc": "USRC12345678",
                "composerName": "Test Composer",
                "artwork": {
                    "url": "https://example.com/{w}x{h}.jpg"
                },
                "audioTraits": ["lossless-stereo"]
            }
        }
        
        track_info = provider._parse_track(track_data)
        
        assert track_info is not None
        assert track_info.id == "1234567890"
        assert track_info.title == "Test Song"
        assert track_info.artist == "Test Artist"
        assert track_info.album == "Test Album"
        assert track_info.duration == 180
        assert track_info.year == 2024
        assert track_info.genre == "Pop"
        assert track_info.track_number == 1
        assert track_info.isrc == "USRC12345678"
        assert track_info.composer == "Test Composer"
        assert track_info.audio_quality == AudioQuality.LOSSLESS
        assert track_info.codec == "ALAC"
        assert track_info.bitrate == 1411
        assert track_info.sample_rate == 44100
        assert track_info.bit_depth == 16
        assert track_info.cover_url == "https://example.com/1000x1000.jpg"
    
    def test_parse_track_hires(self, provider):
        """测试解析高解析度音轨"""
        track_data = {
            "id": "1234567890",
            "attributes": {
                "name": "Test Song",
                "artistName": "Test Artist",
                "audioTraits": ["hi-res-lossless", "dolby-atmos"]
            }
        }
        
        track_info = provider._parse_track(track_data)
        
        assert track_info.audio_quality == AudioQuality.HI_RES
        assert track_info.spatial_audio == SpatialAudio.DOLBY_ATMOS
        assert track_info.sample_rate == 192000
        assert track_info.bit_depth == 24
    
    def test_parse_track_standard(self, provider):
        """测试解析标准音质音轨"""
        track_data = {
            "id": "1234567890",
            "attributes": {
                "name": "Test Song",
                "artistName": "Test Artist",
                "audioTraits": []
            }
        }
        
        track_info = provider._parse_track(track_data)
        
        assert track_info.audio_quality == AudioQuality.STANDARD
        assert track_info.spatial_audio == SpatialAudio.STEREO
    
    def test_get_cover_url(self, provider):
        """测试获取封面 URL"""
        artwork = {"url": "https://example.com/{w}x{h}.jpg"}
        url = provider._get_cover_url(artwork, size=500)
        assert url == "https://example.com/500x500.jpg"
    
    def test_get_cover_url_none(self, provider):
        """测试获取封面 URL（无封面）"""
        assert provider._get_cover_url({}) is None
        assert provider._get_cover_url(None) is None
    
    def test_parse_year(self, provider):
        """测试解析年份"""
        assert provider._parse_year("2024-01-01") == 2024
        assert provider._parse_year("2024") == 2024
        assert provider._parse_year("") is None
        assert provider._parse_year(None) is None
    
    @pytest.mark.asyncio
    async def test_search_not_initialized(self, provider):
        """测试搜索（未初始化）"""
        with pytest.raises(AppleMusicError):
            await provider.search("test")
    
    @pytest.mark.asyncio
    async def test_get_track_info_not_initialized(self, provider):
        """测试获取音轨信息（未初始化）"""
        with pytest.raises(AppleMusicError):
            await provider.get_track_info("123")
    
    @pytest.mark.asyncio
    async def test_get_stream_url_not_initialized(self, provider):
        """测试获取流媒体 URL（未初始化）"""
        with pytest.raises(AppleMusicError):
            await provider.get_stream_url("123")


class TestAppleMusicTrackInfo:
    """测试音轨信息类"""
    
    def test_str(self):
        """测试字符串表示"""
        track = AppleMusicTrackInfo(
            id="123",
            title="Test Song",
            artist="Test Artist"
        )
        assert str(track) == "Test Artist - Test Song"
    
    def test_default_values(self):
        """测试默认值"""
        track = AppleMusicTrackInfo(
            id="123",
            title="Test Song",
            artist="Test Artist"
        )
        assert track.album is None
        assert track.duration is None
        assert track.stream_url is None
        assert track.source == "unknown"
        assert track.cover_url is None
        assert track.lyrics is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
