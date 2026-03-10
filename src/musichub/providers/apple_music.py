"""
Apple Music 音源插件

支持功能:
- 搜索歌曲/专辑/播放列表
- 获取音频流 URL
- 下载 ALAC 无损音质 (LOSSLESS: 16bit/44.1kHz, HI_RES: 24bit/192kHz)
- 获取元数据（含 Dolby Atmos 支持）

配置要求:
- Apple Music 账号
- API Token（用于认证）
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from musichub.plugins.base import SourcePlugin
from musichub.core.types import TrackInfo

logger = logging.getLogger(__name__)


class AudioQuality(Enum):
    """音质等级"""
    STANDARD = "standard"  # AAC 256kbps
    LOSSLESS = "lossless"  # ALAC 16bit/44.1kHz
    HI_RES = "hi_res"      # ALAC 24bit/192kHz


class SpatialAudio(Enum):
    """空间音频"""
    STEREO = "stereo"
    DOLBY_ATMOS = "dolby_atmos"


@dataclass
class AppleMusicConfig:
    """Apple Music 配置"""
    api_token: str = ""
    music_user_token: str = ""
    country: str = "US"
    language: str = "en-US"
    audio_quality: AudioQuality = AudioQuality.LOSSLESS
    spatial_audio: SpatialAudio = SpatialAudio.STEREO
    timeout: int = 30
    max_retries: int = 3
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppleMusicConfig":
        """从字典创建配置"""
        quality_str = data.get("audio_quality", "lossless")
        spatial_str = data.get("spatial_audio", "stereo")
        
        return cls(
            api_token=data.get("api_token", ""),
            music_user_token=data.get("music_user_token", ""),
            country=data.get("country", "US"),
            language=data.get("language", "en-US"),
            audio_quality=AudioQuality(quality_str) if isinstance(quality_str, str) else quality_str,
            spatial_audio=SpatialAudio(spatial_str) if isinstance(spatial_str, str) else spatial_str,
            timeout=data.get("timeout", 30),
            max_retries=data.get("max_retries", 3)
        )


@dataclass
class AppleMusicTrackInfo(TrackInfo):
    """Apple Music 音轨信息（扩展）"""
    isrc: Optional[str] = None
    composer: Optional[str] = None
    content_rating: Optional[str] = None
    audio_quality: AudioQuality = AudioQuality.STANDARD
    spatial_audio: SpatialAudio = SpatialAudio.STEREO
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    codec: Optional[str] = None
    playlist_id: Optional[str] = None
    album_id: Optional[str] = None
    artist_id: Optional[str] = None


class AppleMusicError(Exception):
    """Apple Music 插件异常"""
    pass


class AuthenticationError(AppleMusicError):
    """认证错误"""
    pass


class NotFoundError(AppleMusicError):
    """资源未找到"""
    pass


class RateLimitError(AppleMusicError):
    """速率限制"""
    pass


class AppleMusicProvider(SourcePlugin):
    """
    Apple Music 音源插件
    
    实现 Apple Music API 集成，支持搜索、流媒体 URL 获取和无损下载
    """
    
    name = "apple_music"
    version = "1.0.0"
    description = "Apple Music 音源插件 - 支持无损音质和 Dolby Atmos"
    
    BASE_URL = "https://api.music.apple.com"
    CATALOG_URL = "https://catalog-api.music.apple.com"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.config: AppleMusicConfig = AppleMusicConfig.from_dict(config or {})
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        self._user_token: Optional[str] = None
        self._token_expires_at: float = 0
    
    async def initialize(self) -> bool:
        """初始化插件"""
        try:
            if not self.config.api_token:
                logger.error("Apple Music API Token 未配置")
                return False
            
            # 创建 HTTP 会话
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers={
                    "Authorization": f"Bearer {self.config.api_token}",
                    "Accept": "application/json",
                    "User-Agent": f"MusicHub/{self.version}"
                }
            )
            
            # 验证 API Token
            await self._validate_token()
            
            self._initialized = True
            logger.info(f"Apple Music 插件初始化成功 (音质：{self.config.audio_quality.value})")
            return True
            
        except Exception as e:
            logger.error(f"Apple Music 插件初始化失败：{e}")
            if self._session:
                await self._session.close()
                self._session = None
            return False
    
    async def shutdown(self) -> None:
        """关闭插件，清理资源"""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False
        logger.info("Apple Music 插件已关闭")
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.config.api_token:
            logger.error("缺少 Apple Music API Token")
            return False
        return True
    
    async def _validate_token(self) -> None:
        """验证 API Token"""
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/me"
            async with self._session.get(url) as resp:
                if resp.status == 401:
                    raise AuthenticationError("API Token 无效或已过期")
                elif resp.status == 403:
                    raise AuthenticationError("API Token 权限不足")
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
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法
            url: 请求 URL
            params: 查询参数
            data: 请求体
            use_user_token: 是否使用用户 Token（用于获取流媒体 URL）
        
        Returns:
            响应 JSON
        """
        headers = {}
        
        if use_user_token:
            if not self.config.music_user_token:
                raise AuthenticationError("需要 Music User Token 来获取流媒体 URL")
            headers["Authorization"] = f"Bearer {self.config.music_user_token}"
        
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retries:
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
                        raise AuthenticationError("认证失败")
                    elif resp.status == 403:
                        raise AuthenticationError("权限不足")
                    elif resp.status == 404:
                        raise NotFoundError(f"资源未找到：{url}")
                    elif resp.status == 429:
                        raise RateLimitError("请求速率限制")
                    else:
                        error_text = await resp.text()
                        raise AppleMusicError(f"HTTP {resp.status}: {error_text}")
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                retry_count += 1
                if retry_count <= self.config.max_retries:
                    wait_time = 2 ** retry_count
                    logger.warning(f"请求失败，{wait_time}秒后重试：{e}")
                    await asyncio.sleep(wait_time)
                else:
                    break
        
        raise last_error or AppleMusicError("请求失败")
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        types: Optional[List[str]] = None
    ) -> List[AppleMusicTrackInfo]:
        """
        搜索音乐
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            types: 搜索类型 (songs, albums, playlists, artists)
        
        Returns:
            AppleMusicTrackInfo 列表
        """
        if not self._initialized:
            raise AppleMusicError("插件未初始化")
        
        types = types or ["songs"]
        results = []
        
        for search_type in types:
            try:
                url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/search"
                params = {
                    "term": query,
                    "limit": min(limit, 100),
                    "types": search_type
                }
                
                response = await self._request("GET", url, params=params)
                
                if search_type == "songs":
                    tracks_data = response.get("data", [])
                else:
                    # 对于专辑/播放列表，需要进一步获取音轨
                    tracks_data = await self._expand_results(response.get("data", []), search_type)
                
                for track_data in tracks_data:
                    track_info = self._parse_track(track_data)
                    if track_info:
                        results.append(track_info)
                
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"搜索 {search_type} 失败：{e}")
                continue
        
        return results[:limit]
    
    async def _expand_results(
        self,
        items: List[Dict[str, Any]],
        item_type: str
    ) -> List[Dict[str, Any]]:
        """展开专辑/播放列表为音轨列表"""
        tracks = []
        
        for item in items:
            try:
                item_id = item.get("id")
                if not item_id:
                    continue
                
                if item_type == "albums":
                    url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/albums/{item_id}/tracks"
                elif item_type == "playlists":
                    url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/playlists/{item_id}/tracks"
                else:
                    continue
                
                params = {"limit": 100}
                response = await self._request("GET", url, params=params)
                tracks.extend(response.get("data", []))
                
            except Exception as e:
                logger.error(f"展开 {item_type} 失败：{e}")
                continue
        
        return tracks
    
    def _parse_track(self, track_data: Dict[str, Any]) -> Optional[AppleMusicTrackInfo]:
        """解析音轨数据"""
        try:
            attributes = track_data.get("attributes", {})
            
            # 获取音质信息
            audio_quality = AudioQuality.STANDARD
            bitrate = None
            sample_rate = None
            bit_depth = None
            codec = None
            
            availability = attributes.get("audioTraits", [])
            if "lossless-stereo" in availability:
                audio_quality = AudioQuality.LOSSLESS
                bitrate = 1411  # CD 音质
                sample_rate = 44100
                bit_depth = 16
                codec = "ALAC"
            elif "lossless-hires" in availability or "hi-res-lossless" in availability:
                audio_quality = AudioQuality.HI_RES
                bitrate = 4608  # Hi-Res
                sample_rate = 192000
                bit_depth = 24
                codec = "ALAC"
            
            # 空间音频
            spatial_audio = SpatialAudio.STEREO
            if "dolby-atmos" in availability:
                spatial_audio = SpatialAudio.DOLBY_ATMOS
            
            return AppleMusicTrackInfo(
                id=track_data.get("id", ""),
                title=attributes.get("name", "Unknown"),
                artist=", ".join(attributes.get("artistName", "").split(", ")[:3]),
                album=attributes.get("albumName"),
                duration=attributes.get("durationInMillis", 0) // 1000,
                source=self.name,
                cover_url=self._get_cover_url(attributes.get("artwork", {})),
                year=self._parse_year(attributes.get("releaseDate", "")),
                genre=attributes.get("genreNames", [None])[0],
                track_number=attributes.get("trackNumber"),
                isrc=attributes.get("isrc"),
                composer=attributes.get("composerName"),
                content_rating=attributes.get("contentRating"),
                audio_quality=audio_quality,
                spatial_audio=spatial_audio,
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
    
    def _get_cover_url(self, artwork: Dict[str, Any], size: int = 1000) -> Optional[str]:
        """获取封面图片 URL"""
        if not artwork:
            return None
        
        url = artwork.get("url", "")
        if url:
            # 替换尺寸占位符
            url = url.replace("{w}", str(size)).replace("{h}", str(size))
            return url
        return None
    
    def _parse_year(self, date_str: str) -> Optional[int]:
        """从日期字符串解析年份"""
        if not date_str:
            return None
        try:
            return int(date_str.split("-")[0])
        except (ValueError, IndexError):
            return None
    
    async def get_track_info(self, track_id: str) -> Optional[AppleMusicTrackInfo]:
        """
        获取音轨详细信息
        
        Args:
            track_id: 音轨 ID
        
        Returns:
            AppleMusicTrackInfo
        """
        if not self._initialized:
            raise AppleMusicError("插件未初始化")
        
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/songs/{track_id}"
            response = await self._request("GET", url)
            
            data = response.get("data", [])
            if not data:
                raise NotFoundError(f"音轨未找到：{track_id}")
            
            return self._parse_track(data[0])
            
        except Exception as e:
            logger.error(f"获取音轨信息失败：{e}")
            return None
    
    async def get_stream_url(
        self,
        track_id: str,
        quality: Optional[AudioQuality] = None
    ) -> Optional[str]:
        """
        获取流媒体 URL
        
        Args:
            track_id: 音轨 ID
            quality: 音质等级
        
        Returns:
            流媒体 URL
        """
        if not self._initialized:
            raise AppleMusicError("插件未初始化")
        
        quality = quality or self.config.audio_quality
        
        try:
            # Apple Music 需要通过 playback API 获取流媒体 URL
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/songs/{track_id}/play"
            
            # 构建请求体
            data = {
                "mediaTypes": ["HLS"],
                "audioQuality": quality.value.upper() if quality != AudioQuality.STANDARD else "HIGH"
            }
            
            if self.config.spatial_audio == SpatialAudio.DOLBY_ATMOS:
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
                raise AppleMusicError("未找到播放列表")
            
            # 选择最佳音质的流
            best_stream = None
            best_bitrate = 0
            
            for playlist in playlists:
                stream_url = playlist.get("url")
                stream_type = playlist.get("type", "")
                
                if stream_url:
                    # 优先选择无损音质
                    if quality == AudioQuality.HI_RES and "hi-res" in stream_type:
                        return stream_url
                    elif quality == AudioQuality.LOSSLESS and "lossless" in stream_type:
                        return stream_url
                    elif not best_stream:
                        best_stream = stream_url
            
            return best_stream
            
        except Exception as e:
            logger.error(f"获取流媒体 URL 失败：{e}")
            return None
    
    async def get_download_url(
        self,
        track_id: str,
        quality: Optional[AudioQuality] = None
    ) -> Optional[str]:
        """
        获取下载 URL（用于直接下载）
        
        Args:
            track_id: 音轨 ID
            quality: 音质等级
        
        Returns:
            下载 URL
        """
        return await self.get_stream_url(track_id, quality)
    
    async def get_album_tracks(self, album_id: str) -> List[AppleMusicTrackInfo]:
        """
        获取专辑的所有音轨
        
        Args:
            album_id: 专辑 ID
        
        Returns:
            音轨列表
        """
        if not self._initialized:
            raise AppleMusicError("插件未初始化")
        
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
    
    async def get_playlist_tracks(self, playlist_id: str) -> List[AppleMusicTrackInfo]:
        """
        获取播放列表的所有音轨
        
        Args:
            playlist_id: 播放列表 ID
        
        Returns:
            音轨列表
        """
        if not self._initialized:
            raise AppleMusicError("插件未初始化")
        
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
            logger.error(f"获取播放列表音轨失败：{e}")
            return []
    
    async def get_artist_top_songs(self, artist_id: str, limit: int = 20) -> List[AppleMusicTrackInfo]:
        """
        获取艺术家的热门歌曲
        
        Args:
            artist_id: 艺术家 ID
            limit: 数量限制
        
        Returns:
            音轨列表
        """
        if not self._initialized:
            raise AppleMusicError("插件未初始化")
        
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
    
    def get_quality_info(self, quality: AudioQuality) -> Dict[str, Any]:
        """
        获取音质详细信息
        
        Args:
            quality: 音质等级
        
        Returns:
            音质信息字典
        """
        quality_info = {
            AudioQuality.STANDARD: {
                "codec": "AAC",
                "bitrate": 256,
                "sample_rate": 44100,
                "bit_depth": 16,
                "description": "标准音质 (256kbps AAC)"
            },
            AudioQuality.LOSSLESS: {
                "codec": "ALAC",
                "bitrate": 1411,
                "sample_rate": 44100,
                "bit_depth": 16,
                "description": "无损音质 (16bit/44.1kHz ALAC)"
            },
            AudioQuality.HI_RES: {
                "codec": "ALAC",
                "bitrate": 4608,
                "sample_rate": 192000,
                "bit_depth": 24,
                "description": "高解析度无损 (24bit/192kHz ALAC)"
            }
        }
        
        info = quality_info.get(quality, {})
        info["spatial_audio"] = self.config.spatial_audio.value
        return info
    
    async def search_albums(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索专辑
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
        
        Returns:
            专辑信息列表
        """
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
                    "url": attributes.get("url")
                })
            
            return albums
            
        except Exception as e:
            logger.error(f"搜索专辑失败：{e}")
            return []
    
    async def search_playlists(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索播放列表
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
        
        Returns:
            播放列表信息列表
        """
        try:
            url = f"{self.BASE_URL}/v1/catalog/{self.config.country}/search"
            params = {
                "term": query,
                "limit": limit,
                "types": "playlists"
            }
            
            response = await self._request("GET", url, params=params)
            
            playlists = []
            for playlist_data in response.get("data", []):
                attributes = playlist_data.get("attributes", {})
                playlists.append({
                    "id": playlist_data.get("id"),
                    "name": attributes.get("name"),
                    "curator": attributes.get("curatorName"),
                    "track_count": attributes.get("trackCount"),
                    "cover_url": self._get_cover_url(attributes.get("artwork", {})),
                    "url": attributes.get("url")
                })
            
            return playlists
            
        except Exception as e:
            logger.error(f"搜索播放列表失败：{e}")
            return []
    
    async def search_artists(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索艺术家
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
        
        Returns:
            艺术家信息列表
        """
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
                    "cover_url": self._get_cover_url(attributes.get("artwork", {})),
                    "url": attributes.get("url")
                })
            
            return artists
            
        except Exception as e:
            logger.error(f"搜索艺术家失败：{e}")
            return []


# 插件工厂函数
def create_provider(config: Optional[Dict[str, Any]] = None) -> AppleMusicProvider:
    """
    创建 Apple Music 插件实例
    
    Args:
        config: 配置字典
    
    Returns:
        AppleMusicProvider 实例
    """
    return AppleMusicProvider(config)


# 注册到插件系统
def register(registry) -> None:
    """
    注册到插件注册表
    
    Args:
        registry: 插件注册表实例
    """
    provider = AppleMusicProvider()
    registry.register_source("apple_music", provider)
    logger.info("Apple Music 插件已注册")
