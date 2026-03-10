"""
Apple Music 平台插件

支持功能:
- 搜索歌曲/专辑/播放列表
- 获取音频流 URL
- 下载 ALAC 无损音质 (LOSSLESS: 16bit/44.1kHz, HI_RES: 24bit/192kHz)
- 获取元数据（含 Dolby Atmos 支持）

配置要求:
- Apple Music API Token
- Music User Token（用于获取流媒体 URL）
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from providers.base import (
    BaseProvider,
    PlatformConfig,
    Quality,
    TrackInfo,
    TrackMetadata,
    DownloadResult,
    ProviderError,
    SearchError,
    URLFetchError,
    DownloadError,
    MetadataError,
    AuthenticationError,
)

logger = logging.getLogger(__name__)


class AppleMusicConfig(PlatformConfig):
    """Apple Music 平台配置"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_token: str = kwargs.get("api_token", "")
        self.music_user_token: str = kwargs.get("music_user_token", "")
        self.country: str = kwargs.get("country", "US")
        self.language: str = kwargs.get("language", "en-US")
        self.spatial_audio: bool = kwargs.get("spatial_audio", False)
    
    def validate(self) -> bool:
        """验证配置"""
        if not self.api_token:
            logger.error("缺少 Apple Music API Token")
            return False
        return True


@dataclass
class AppleMusicTrackInfo(TrackInfo):
    """Apple Music 音轨信息（扩展）"""
    isrc: Optional[str] = None
    composer: Optional[str] = None
    content_rating: Optional[str] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    codec: Optional[str] = None
    album_id: Optional[str] = None
    artist_id: Optional[str] = None
    playlist_id: Optional[str] = None


class AppleMusicProvider(BaseProvider):
    """
    Apple Music 平台插件
    
    实现 Apple Music API 集成，支持搜索、流媒体 URL 获取和无损下载
    """
    
    platform_name = "apple_music"
    platform_display_name = "Apple Music"
    config_class = AppleMusicConfig
    
    BASE_URL = "https://api.music.apple.com"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._token_expires_at: float = 0
        self._quality_map = {
            Quality.STANDARD: "HIGH",
            Quality.HIGH: "HIGH",
            Quality.LOSSLESS: "LOSSLESS",
            Quality.HI_RES: "HI_RES_LOSSLESS",
        }
    
    async def initialize(self) -> bool:
        """
        初始化插件
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            if not self.config.validate():
                return False
            
            # 创建 HTTP 会话
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers={
                    "Authorization": f"Bearer {self.config.api_token}",
                    "Accept": "application/json",
                    "User-Agent": "MusicHub/1.0"
                }
            )
            
            # 验证 API Token
            await self._validate_token()
            
            self._initialized = True
            logger.info(f"Apple Music 插件初始化成功 (区域：{self.config.country})")
            return True
            
        except Exception as e:
            logger.error(f"Apple Music 插件初始化失败：{e}")
            if self._session:
                await self._session.close()
                self._session = None
            return False
    
    async def _validate_token(self) -> None:
        """验证 API Token"""
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/me"
            async with self._session.get(url) as resp:
                if resp.status == 401:
                    raise AuthenticationError("API Token 无效或已过期", self.platform_name)
                elif resp.status == 403:
                    raise AuthenticationError("API Token 权限不足", self.platform_name)
        except aiohttp.ClientError as e:
            logger.warning(f"Token 验证请求失败：{e}")
    
    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        use_user_token: bool = False
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        headers = {}
        
        if use_user_token:
            if not self.config.music_user_token:
                raise AuthenticationError("需要 Music User Token 来获取流媒体 URL", self.platform_name)
            headers["Authorization"] = f"Bearer {self.config.music_user_token}"
        
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.retry_times:
            try:
                async with self._session.request(
                    method,
                    url,
                    params=params,
                    json=data,
                    headers=headers if use_user_token else None
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 401:
                        raise AuthenticationError("认证失败", self.platform_name)
                    elif resp.status == 403:
                        raise AuthenticationError("权限不足", self.platform_name)
                    elif resp.status == 404:
                        raise URLFetchError(f"资源未找到：{url}", self.platform_name)
                    elif resp.status == 429:
                        raise URLFetchError("请求速率限制", self.platform_name)
                    else:
                        error_text = await resp.text()
                        raise ProviderError(f"HTTP {resp.status}: {error_text}", self.platform_name)
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                retry_count += 1
                if retry_count <= self.config.retry_times:
                    wait_time = 2 ** retry_count
                    logger.warning(f"请求失败，{wait_time}秒后重试：{e}")
                    await asyncio.sleep(wait_time)
                else:
                    break
        
        raise last_error or ProviderError("请求失败", self.platform_name)
    
    async def search(self, query: str, limit: int = 20) -> List[AppleMusicTrackInfo]:
        """
        搜索歌曲
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            List[AppleMusicTrackInfo]: 搜索结果列表
        """
        if not self._initialized:
            raise ProviderError("插件未初始化", self.platform_name)
        
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/search"
            params = {
                "term": query,
                "limit": min(limit, 100),
                "types": "songs"
            }
            
            response = await self._request("GET", url, params=params)
            
            results = []
            for track_data in response.get("data", []):
                track_info = self._parse_track(track_data)
                if track_info:
                    results.append(track_info)
            
            return results[:limit]
            
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise SearchError(f"搜索失败：{e}", self.platform_name)
    
    def _parse_track(self, track_data: Dict[str, Any]) -> Optional[AppleMusicTrackInfo]:
        """解析音轨数据"""
        try:
            attributes = track_data.get("attributes", {})
            
            # 获取音质信息
            quality_available = []
            bitrate = None
            sample_rate = None
            bit_depth = None
            codec = None
            
            availability = attributes.get("audioTraits", [])
            
            if "lossless-stereo" in availability:
                quality_available.append(Quality.LOSSLESS)
                bitrate = 1411
                sample_rate = 44100
                bit_depth = 16
                codec = "ALAC"
            elif "hi-res-lossless" in availability or "lossless-hires" in availability:
                quality_available.append(Quality.HI_RES)
                bitrate = 4608
                sample_rate = 192000
                bit_depth = 24
                codec = "ALAC"
            
            # 始终支持标准音质
            quality_available.insert(0, Quality.STANDARD)
            quality_available.insert(1, Quality.HIGH)
            
            # 去重
            quality_available = list(dict.fromkeys(quality_available))
            
            # 获取封面 URL
            cover_url = None
            artwork = attributes.get("artwork", {})
            if artwork:
                url = artwork.get("url", "")
                if url:
                    cover_url = url.replace("{w}", "1000").replace("{h}", "1000")
            
            # 解析年份
            year = None
            release_date = attributes.get("releaseDate", "")
            if release_date:
                try:
                    year = int(release_date.split("-")[0])
                except (ValueError, IndexError):
                    pass
            
            return AppleMusicTrackInfo(
                id=track_data.get("id", ""),
                title=attributes.get("name", "Unknown"),
                artist=attributes.get("artistName", "Unknown"),
                album=attributes.get("albumName"),
                duration=attributes.get("durationInMillis", 0) // 1000,
                cover_url=cover_url,
                quality_available=quality_available,
                year=year,
                genre=attributes.get("genreNames", [None])[0],
                isrc=attributes.get("isrc"),
                composer=attributes.get("composerName"),
                content_rating=attributes.get("contentRating"),
                bitrate=bitrate,
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                codec=codec,
                album_id=track_data.get("relationships", {}).get("albums", {}).get("data", [{}])[0].get("id"),
                artist_id=track_data.get("relationships", {}).get("artists", {}).get("data", [{}])[0].get("id")
            )
            
        except Exception as e:
            logger.error(f"解析音轨数据失败：{e}")
            return None
    
    async def get_stream_url(self, track_id: str, quality: Quality = Quality.LOSSLESS) -> str:
        """
        获取歌曲流媒体 URL
        
        Args:
            track_id: 歌曲 ID
            quality: 期望的音质质量
            
        Returns:
            str: 流媒体 URL
        """
        if not self._initialized:
            raise ProviderError("插件未初始化", self.platform_name)
        
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/songs/{track_id}/play"
            
            # 构建请求体
            data = {
                "mediaTypes": ["HLS"],
                "audioQuality": self._quality_map.get(quality, "HIGH")
            }
            
            if self.config.spatial_audio:
                data["audioTraits"] = ["dolby-atmos"]
            
            response = await self._request(
                "POST",
                url,
                data=data,
                use_user_token=True
            )
            
            # 解析播放 URL
            playlists = response.get("playlists", [])
            if not playlists:
                raise URLFetchError("未找到播放列表", self.platform_name)
            
            # 返回第一个可用的流 URL
            for playlist in playlists:
                stream_url = playlist.get("url")
                if stream_url:
                    return stream_url
            
            raise URLFetchError("无法获取流媒体 URL", self.platform_name)
            
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise URLFetchError(f"获取流媒体 URL 失败：{e}", self.platform_name)
    
    async def download(
        self,
        track_id: str,
        save_path: Path,
        quality: Quality = Quality.LOSSLESS
    ) -> DownloadResult:
        """
        下载歌曲
        
        Args:
            track_id: 歌曲 ID
            save_path: 保存路径
            quality: 期望的音质质量
            
        Returns:
            DownloadResult: 下载结果
        """
        if not self._initialized:
            raise ProviderError("插件未初始化", self.platform_name)
        
        try:
            # 获取流媒体 URL
            stream_url = await self.get_stream_url(track_id, quality)
            
            # 获取音轨信息用于文件名
            track_info = await self._get_track_info(track_id)
            
            # 确定保存路径
            if save_path.is_dir():
                filename = f"{track_info.artist} - {track_info.title}.m4a"
                save_path = save_path / filename
            
            # 下载文件
            async with self._session.get(stream_url) as resp:
                if resp.status != 200:
                    raise DownloadError(f"下载失败：HTTP {resp.status}", self.platform_name)
                
                file_size = 0
                with open(save_path, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)
                        file_size += len(chunk)
            
            # 获取元数据
            metadata = await self.get_metadata(track_id)
            
            return DownloadResult(
                success=True,
                file_path=save_path,
                quality=quality,
                file_size=file_size,
                metadata=metadata
            )
            
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise DownloadError(f"下载失败：{e}", self.platform_name)
    
    async def _get_track_info(self, track_id: str) -> AppleMusicTrackInfo:
        """获取音轨详细信息"""
        url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/songs/{track_id}"
        response = await self._request("GET", url)
        
        data = response.get("data", [])
        if not data:
            raise URLFetchError(f"音轨未找到：{track_id}", self.platform_name)
        
        track_info = self._parse_track(data[0])
        if not track_info:
            raise MetadataError("无法解析音轨信息", self.platform_name)
        
        return track_info
    
    async def get_metadata(self, track_id: str) -> TrackMetadata:
        """
        获取歌曲元数据
        
        Args:
            track_id: 歌曲 ID
            
        Returns:
            TrackMetadata: 歌曲元数据
        """
        if not self._initialized:
            raise ProviderError("插件未初始化", self.platform_name)
        
        try:
            track_info = await self._get_track_info(track_id)
            
            # 获取封面图片数据
            cover_data = None
            if track_info.cover_url:
                async with self._session.get(track_info.cover_url) as resp:
                    if resp.status == 200:
                        cover_data = await resp.read()
            
            return TrackMetadata(
                title=track_info.title,
                artist=track_info.artist,
                album=track_info.album,
                year=track_info.year,
                genre=track_info.extra.get("genre"),
                cover_data=cover_data,
                extra={
                    "isrc": track_info.isrc,
                    "composer": track_info.composer,
                    "codec": track_info.codec,
                    "bitrate": track_info.bitrate,
                    "sample_rate": track_info.sample_rate,
                    "bit_depth": track_info.bit_depth
                }
            )
            
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise MetadataError(f"获取元数据失败：{e}", self.platform_name)
    
    async def get_playlist(self, playlist_id: str) -> List[TrackInfo]:
        """
        获取歌单歌曲列表
        
        Args:
            playlist_id: 歌单 ID
            
        Returns:
            List[TrackInfo]: 歌单中的歌曲列表
        """
        if not self._initialized:
            raise ProviderError("插件未初始化", self.platform_name)
        
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/playlists/{playlist_id}/tracks"
            params = {"limit": 300}
            
            response = await self._request("GET", url, params=params)
            
            tracks = []
            for track_data in response.get("data", []):
                track_info = self._parse_track(track_data)
                if track_info:
                    track_info.playlist_id = playlist_id
                    tracks.append(track_info)
            
            return tracks
            
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise SearchError(f"获取歌单失败：{e}", self.platform_name)
    
    async def search_albums(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索专辑"""
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/search"
            params = {
                "term": query,
                "limit": limit,
                "types": "albums"
            }
            
            response = await self._request("GET", url, params=params)
            
            albums = []
            for album_data in response.get("data", []):
                attributes = album_data.get("attributes", {})
                albums.append({
                    "id": album_data.get("id"),
                    "name": attributes.get("name"),
                    "artist": attributes.get("artistName"),
                    "release_date": attributes.get("releaseDate"),
                    "track_count": attributes.get("trackCount"),
                    "cover_url": self._get_cover_url(attributes.get("artwork", {})),
                })
            
            return albums
            
        except Exception as e:
            logger.error(f"搜索专辑失败：{e}")
            return []
    
    async def search_artists(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索艺术家"""
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/search"
            params = {
                "term": query,
                "limit": limit,
                "types": "artists"
            }
            
            response = await self._request("GET", url, params=params)
            
            artists = []
            for artist_data in response.get("data", []):
                attributes = artist_data.get("attributes", {})
                artists.append({
                    "id": artist_data.get("id"),
                    "name": attributes.get("name"),
                    "genre": attributes.get("genreNames", []),
                })
            
            return artists
            
        except Exception as e:
            logger.error(f"搜索艺术家失败：{e}")
            return []
    
    async def get_album_tracks(self, album_id: str) -> List[AppleMusicTrackInfo]:
        """获取专辑的所有音轨"""
        if not self._initialized:
            raise ProviderError("插件未初始化", self.platform_name)
        
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/albums/{album_id}/tracks"
            params = {"limit": 300}
            
            response = await self._request("GET", url, params=params)
            
            tracks = []
            for track_data in response.get("data", []):
                track_info = self._parse_track(track_data)
                if track_info:
                    track_info.album_id = album_id
                    tracks.append(track_info)
            
            return tracks
            
        except Exception as e:
            logger.error(f"获取专辑音轨失败：{e}")
            return []
    
    async def get_artist_top_songs(self, artist_id: str, limit: int = 20) -> List[AppleMusicTrackInfo]:
        """获取艺术家的热门歌曲"""
        if not self._initialized:
            raise ProviderError("插件未初始化", self.platform_name)
        
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/artists/{artist_id}/top-songs"
            params = {"limit": min(limit, 100)}
            
            response = await self._request("GET", url, params=params)
            
            tracks = []
            for track_data in response.get("data", []):
                track_info = self._parse_track(track_data)
                if track_info:
                    track_info.artist_id = artist_id
                    tracks.append(track_info)
            
            return tracks
            
        except Exception as e:
            logger.error(f"获取艺术家热门歌曲失败：{e}")
            return []
    
    def _get_cover_url(self, artwork: Dict[str, Any], size: int = 1000) -> Optional[str]:
        """获取封面图片 URL"""
        if not artwork:
            return None
        
        url = artwork.get("url", "")
        if url:
            return url.replace("{w}", str(size)).replace("{h}", str(size))
        return None
    
    def get_quality_info(self, quality: Quality) -> Dict[str, Any]:
        """获取音质详细信息"""
        quality_info = {
            Quality.STANDARD: {
                "codec": "AAC",
                "bitrate": 256,
                "sample_rate": 44100,
                "bit_depth": 16,
                "description": "标准音质 (256kbps AAC)"
            },
            Quality.HIGH: {
                "codec": "AAC",
                "bitrate": 256,
                "sample_rate": 44100,
                "bit_depth": 16,
                "description": "高品质 (256kbps AAC)"
            },
            Quality.LOSSLESS: {
                "codec": "ALAC",
                "bitrate": 1411,
                "sample_rate": 44100,
                "bit_depth": 16,
                "description": "无损音质 (16bit/44.1kHz ALAC)"
            },
            Quality.HI_RES: {
                "codec": "ALAC",
                "bitrate": 4608,
                "sample_rate": 192000,
                "bit_depth": 24,
                "description": "高解析度无损 (24bit/192kHz ALAC)"
            }
        }
        
        info = quality_info.get(quality, {})
        info["spatial_audio"] = "dolby_atmos" if self.config.spatial_audio else "stereo"
        return info
    
    async def close(self):
        """关闭插件，释放资源"""
        await super().close()
        logger.info("Apple Music 插件已关闭")


# 工厂函数
def create_provider(config: Optional[Dict[str, Any]] = None) -> AppleMusicProvider:
    """创建 Apple Music 插件实例"""
    return AppleMusicProvider(config)


# 注册到插件系统
def register(registry) -> None:
    """注册到插件注册表"""
    provider = AppleMusicProvider()
    registry.register_source("apple_music", provider)
    logger.info("Apple Music 插件已注册")
