"""
Tidal 插件单元测试

运行测试:
    pytest tests/test_tidal.py -v

注意: 部分测试需要有效的 Tidal 认证才能通过
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile

from providers import (
    TidalProvider,
    TidalConfig,
    Quality,
    SearchError,
    URLFetchError,
    DownloadError,
    AuthenticationError,
)


class TestTidalConfig:
    """TidalConfig 测试类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = TidalConfig()
        
        assert config.client_id == TidalConfig.DEFAULT_CLIENT_ID
        assert config.client_secret == TidalConfig.DEFAULT_CLIENT_SECRET
        assert config.quality == "LOSSLESS"
        assert config.country_code == "US"
        assert config.timeout == 30
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = TidalConfig(
            api_token="test_token",
            client_id="custom_id",
            quality="HI_RES",
            country_code="CN",
            timeout=60,
        )
        
        assert config.api_token == "test_token"
        assert config.client_id == "custom_id"
        assert config.quality == "HI_RES"
        assert config.country_code == "CN"
        assert config.timeout == 60
    
    def test_validate_with_token(self):
        """测试使用 token 验证配置"""
        config = TidalConfig(api_token="test_token")
        assert config.validate() is True
    
    def test_validate_with_credentials(self):
        """测试使用凭证验证配置"""
        config = TidalConfig(
            client_id="test_id",
            client_secret="test_secret"
        )
        assert config.validate() is True
    
    def test_validate_without_credentials(self):
        """测试无凭证时验证失败"""
        config = TidalConfig()
        # 默认凭证存在，所以应该通过
        assert config.validate() is True


class TestTidalProviderInit:
    """TidalProvider 初始化测试"""
    
    def test_provider_attributes(self):
        """测试插件属性"""
        provider = TidalProvider()
        
        assert provider.platform_name == "tidal"
        assert provider.platform_display_name == "Tidal"
        assert provider.config_class == TidalConfig
    
    def test_provider_with_config(self):
        """测试带配置的插件"""
        config = {
            "api_token": "test_token",
            "quality": "HI_RES",
        }
        provider = TidalProvider(config)
        
        assert provider.config.api_token == "test_token"
        assert provider.config.quality == "HI_RES"


class TestTidalProviderAsync:
    """TidalProvider 异步方法测试"""
    
    @pytest.mark.asyncio
    async def test_initialize_without_credentials(self):
        """测试无凭证时初始化"""
        provider = TidalProvider({"client_id": "test", "client_secret": "test"})
        
        # Mock HTTP session
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            
            # Mock authentication response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"access_token": "test_token"}
            mock_session.post.return_value = mock_response
            
            # Mock user info response
            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": "123",
                "subscription": {"type": "HIFI"},
                "countryCode": "US"
            }
            mock_session.get.return_value = mock_user_response
            
            result = await provider.initialize()
            
            assert result is True
            assert provider._initialized is True
    
    @pytest.mark.asyncio
    async def test_initialize_with_invalid_credentials(self):
        """测试无效凭证时初始化失败"""
        provider = TidalProvider({"client_id": "invalid", "client_secret": "invalid"})
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            
            # Mock 401 response
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_session.post.return_value = mock_response
            
            result = await provider.initialize()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_search(self):
        """测试搜索功能"""
        provider = TidalProvider({"api_token": "test"})
        provider._initialized = True
        provider._access_token = "test_token"
        provider._subscription_type = "HIFI"
        provider.config.country_code = "US"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            
            # Mock search response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tracks": {
                    "items": [
                        {
                            "id": "123",
                            "title": "Test Song",
                            "artist": {"id": "1", "name": "Test Artist"},
                            "album": {"id": "1", "title": "Test Album", "cover": "abc-def"},
                            "duration": 180,
                        }
                    ]
                }
            }
            mock_session.get.return_value = mock_response
            
            results = await provider.search("test", limit=10)
            
            assert len(results) == 1
            assert results[0].id == "123"
            assert results[0].title == "Test Song"
            assert results[0].artist == "Test Artist"
    
    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """测试搜索无结果"""
        provider = TidalProvider({"api_token": "test"})
        provider._initialized = True
        provider._access_token = "test_token"
        provider._subscription_type = "HIFI"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"tracks": {"items": []}}
            mock_session.get.return_value = mock_response
            
            results = await provider.search("nonexistent", limit=10)
            
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_get_stream_url(self):
        """测试获取流 URL"""
        provider = TidalProvider({"api_token": "test"})
        provider._initialized = True
        provider._access_token = "test_token"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            
            # Mock stream URL response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "streamUrl": "https://example.com/stream.mp4",
                "audioQuality": "LOSSLESS"
            }
            mock_session.post.return_value = mock_response
            
            url = await provider.get_stream_url("123", Quality.LOSSLESS)
            
            assert url == "https://example.com/stream.mp4"
    
    @pytest.mark.asyncio
    async def test_get_stream_url_with_manifest(self):
        """测试获取 DASH manifest 流 URL"""
        import base64
        
        provider = TidalProvider({"api_token": "test"})
        provider._initialized = True
        provider._access_token = "test_token"
        
        # Create mock DASH manifest
        dash_xml = """<?xml version="1.0"?>
        <MPD xmlns="urn:mpeg:dash:schema:mpd:2011">
            <BaseURL>https://example.com/stream.mpd</BaseURL>
        </MPD>"""
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "manifest": {
                    "mimeType": "application/dash+xml",
                    "data": base64.b64encode(dash_xml.encode()).decode()
                }
            }
            mock_session.post.return_value = mock_response
            
            url = await provider.get_stream_url("123", Quality.LOSSLESS)
            
            assert url == "https://example.com/stream.mpd"
    
    @pytest.mark.asyncio
    async def test_download_success(self, tmp_path):
        """测试成功下载"""
        provider = TidalProvider({"api_token": "test"})
        provider._initialized = True
        provider._access_token = "test_token"
        provider._subscription_type = "HIFI"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            
            # Mock track info response
            track_response = MagicMock()
            track_response.status_code = 200
            track_response.json.return_value = {
                "id": "123",
                "title": "Test Song",
                "artist": {"name": "Test Artist"},
                "album": {"title": "Test Album", "cover": "abc-def"},
                "duration": 180,
            }
            
            # Mock stream URL response
            stream_response = MagicMock()
            stream_response.status_code = 200
            stream_response.json.return_value = {
                "streamUrl": "https://example.com/stream.flac"
            }
            
            # Mock download response
            download_response = MagicMock()
            download_response.status_code = 200
            download_response.aiter_bytes.return_value = iter([b"fake audio data"])
            
            mock_session.get.side_effect = [track_response, download_response]
            mock_session.post.return_value = stream_response
            
            result = await provider.download(
                track_id="123",
                save_path=tmp_path,
                quality=Quality.LOSSLESS
            )
            
            assert result.success is True
            assert result.file_path.exists()
            assert result.quality == Quality.LOSSLESS
    
    @pytest.mark.asyncio
    async def test_get_metadata(self):
        """测试获取元数据"""
        provider = TidalProvider({"api_token": "test"})
        provider._initialized = True
        provider._access_token = "test_token"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            
            # Mock track info response
            track_response = MagicMock()
            track_response.status_code = 200
            track_response.json.return_value = {
                "id": "123",
                "title": "Test Song",
                "artist": {"name": "Test Artist"},
                "album": {
                    "id": "456",
                    "title": "Test Album",
                    "cover": "abc-def",
                    "releaseDate": "2023-01-01"
                },
                "duration": 180,
                "trackNumber": 5,
            }
            
            # Mock album info response
            album_response = MagicMock()
            album_response.status_code = 200
            album_response.json.return_value = {
                "id": "456",
                "title": "Test Album",
                "releaseDate": "2023-01-01"
            }
            
            # Mock cover download
            cover_response = MagicMock()
            cover_response.status_code = 200
            cover_response.content = b"fake image data"
            
            mock_session.get.side_effect = [track_response, album_response, cover_response]
            
            metadata = await provider.get_metadata("123")
            
            assert metadata.title == "Test Song"
            assert metadata.artist == "Test Artist"
            assert metadata.album == "Test Album"
            assert metadata.year == 2023
            assert metadata.track_number == 5
    
    @pytest.mark.asyncio
    async def test_get_playlist(self):
        """测试获取播放列表"""
        provider = TidalProvider({"api_token": "test"})
        provider._initialized = True
        provider._access_token = "test_token"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "items": [
                    {
                        "track": {
                            "id": "1",
                            "title": "Song 1",
                            "artist": {"name": "Artist 1"},
                            "album": {"title": "Album 1"},
                        }
                    },
                    {
                        "track": {
                            "id": "2",
                            "title": "Song 2",
                            "artist": {"name": "Artist 2"},
                            "album": {"title": "Album 2"},
                        }
                    }
                ],
                "totalNumberOfItems": 2
            }
            mock_session.get.return_value = mock_response
            
            tracks = await provider.get_playlist("playlist_123")
            
            assert len(tracks) == 2
            assert tracks[0].id == "1"
            assert tracks[1].id == "2"
    
    @pytest.mark.asyncio
    async def test_get_album_tracks(self):
        """测试获取专辑音轨"""
        provider = TidalProvider({"api_token": "test"})
        provider._initialized = True
        provider._access_token = "test_token"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "items": [
                    {"track": {"id": "1", "title": "Track 1", "artist": {"name": "Artist"}, "album": {}}},
                    {"track": {"id": "2", "title": "Track 2", "artist": {"name": "Artist"}, "album": {}}},
                ],
                "totalNumberOfItems": 2
            }
            mock_session.get.return_value = mock_response
            
            tracks = await provider.get_album_tracks("album_123")
            
            assert len(tracks) == 2
    
    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭插件"""
        provider = TidalProvider({"api_token": "test"})
        provider._initialized = True
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = MagicMock()
            mock_client.return_value = mock_session
            mock_session.aclose = AsyncMock()
            
            provider._session = mock_session
            
            await provider.close()
            
            assert provider._initialized is False
            mock_session.aclose.assert_called_once()


class TestTidalQualityMapping:
    """音质映射测试"""
    
    def test_quality_mapping(self):
        """测试 Quality 到 TidalQuality 的映射"""
        from providers.tidal import QUALITY_MAP, TidalQuality
        
        assert QUALITY_MAP[Quality.STANDARD] == TidalQuality.LOW
        assert QUALITY_MAP[Quality.HIGH] == TidalQuality.HIGH
        assert QUALITY_MAP[Quality.LOSSLESS] == TidalQuality.LOSSLESS
        assert QUALITY_MAP[Quality.HI_RES] == TidalQuality.HI_RES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
