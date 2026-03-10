"""
Qobuz 音源插件

支持功能:
- 搜索歌曲/专辑/播放列表
- 获取音频流 URL
- 下载 Hi-Res 无损音质 (最高 24bit/192kHz)
- 获取元数据（含 Hi-Res 认证）

配置要求:
- Qobuz 账号（Sublime+ 订阅）
- API Key（app_id 和 app_secret 用于认证）

音质等级:
- LOSSLESS: 16bit/44.1kHz CD Quality
- HI_RES: 24bit/192kHz High-Resolution
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from musichub.plugins.base import SourcePlugin
from musichub.core.types import TrackInfo

logger = logging.getLogger(__name__)


class AudioQuality(Enum):
    """音质等级"""
    STANDARD = "standard"    # MP3 320kbps
    LOSSLESS = "lossless"    # FLAC 16bit/44.1kHz CD Quality
    HI_RES = "hi_res"        # FLAC 24bit/192kHz High-Resolution


@dataclass
class QobuzConfig:
    """Qobuz 配置"""
    app_id: str = ""
    app_secret: str = ""
    country: str = "US"
    language: str = "en"
    audio_quality: AudioQuality = AudioQuality.HI_RES
    timeout: int = 30
    max_retries: int = 3
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QobuzConfig":
        """从字典创建配置"""
        quality_str = data.get("audio_quality", "hi_res")
        
        return cls(
            app_id=data.get("app_id", ""),
            app_secret=data.get("app_secret", ""),
            country=data.get("country", "US"),
            language=data.get("language", "en"),
            audio_quality=AudioQuality(quality_str) if isinstance(quality_str, str) else quality_str,
            timeout=data.get("timeout", 30),
            max_retries=data.get("max_retries", 3)
        )


@dataclass
class QobuzTrackInfo(TrackInfo):
    """Qobuz 音轨信息（扩展）"""
    isrc: Optional[str] = None
    composer: Optional[str] = None
    publisher: Optional[str] = None
    audio_quality: AudioQuality = AudioQuality.STANDARD
    bitrate: Optional[int] = None
    sample_rate: Optional[float] = None
    bit_depth: Optional[int] = None
    codec: Optional[str] = None
    album_id: Optional[str] = None
    artist_id: Optional[str] = None
    hi_res: bool = False
    hi_res_description: Optional[str] = None


class QobuzError(Exception):
    """Qobuz 插件异常"""
    pass


class AuthenticationError(QobuzError):
    """认证错误"""
    pass


class SubscriptionError(QobuzError):
    """订阅错误（需要 Sublime+）"""
    pass


class NotFoundError(QobuzError):
    """资源未找到"""
    pass


class RateLimitError(QobuzError):
    """速率限制"""
    pass


class QobuzProvider(SourcePlugin):
    """
    Qobuz 音源插件
    
    实现 Qobuz API 集成，支持搜索、流媒体 URL 获取和 Hi-Res 无损下载
    Qobuz API: https://www.qobuz.com/api.json/0.2
    """
    
    name = "qobuz"
    version = "1.0.0"
    description = "Qobuz 音源插件 - 支持 Hi-Res 无损音质 (最高 24bit/192kHz)"
    
    BASE_URL = "https://www.qobuz.com/api.json/0.2"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.config: QobuzConfig = QobuzConfig.from_dict(config or {})
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        self._auth_token: Optional[str] = None
        self._user_id: Optional[int] = None
        self._token_expires_at: float = 0
    
    async def initialize(self) -> bool:
        """初始化插件"""
        try:
            if not self.config.app_id or not self.config.app_secret:
                logger.error("Qobuz API credentials 未配置 (app_id / app_secret)")
                return False
            
            # 创建 HTTP 会话
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"MusicHub/{self.version}"
                }
            )
            
            # 验证 API 凭证
            await self._validate_credentials()
            
            self._initialized = True
            logger.info(f"Qobuz 插件初始化成功 (音质：{self.config.audio_quality.value})")
            return True
            
        except Exception as e:
            logger.error(f"Qobuz 插件初始化失败：{e}")
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
        logger.info("Qobuz 插件已关闭")
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.config.app_id:
            logger.error("缺少 Qobuz app_id")
            return False
        if not self.config.app_secret:
            logger.error("缺少 Qobuz app_secret")
            return False
        return True
    
    def _generate_signature(self, url: str, timestamp: int) -> str:
        """
        生成 API 请求签名
        
        Qobuz API 使用 app_secret 对 URL + timestamp + app_secret 进行 MD5 哈希
        
        Args:
            url: 请求 URL（不含域名，如 /track/getFileUrl）
            timestamp: Unix 时间戳
        
        Returns:
            签名字符串
        """
        # 签名格式：url + timestamp + app_secret
        signature_string = f"{url}{timestamp}{self.config.app_secret}"
        signature = hashlib.md5(signature_string.encode('utf-8')).hexdigest()
        return signature
    
    async def _validate_credentials(self) -> None:
        """验证 API 凭证"""
        try:
            # 使用 getUserAuthToken 接口验证
            url = f"{self.BASE_URL}/user/getUserAuthToken"
            timestamp = int(time.time())
            signature = self._generate_signature("/user/getUserAuthToken", timestamp)
            
            params = {
                "app_id": self.config.app_id,
                "request_ts": timestamp,
                "request_sig": signature
            }
            
            async with self._session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") == "success":
                        user_data = data.get("user", {})
                        self._user_id = user_data.get("id")
                        # 检查订阅状态
                        credential = user_data.get("credential", {})
                        label = credential.get("label", "")
                        if "sublime" not in label.lower():
                            logger.warning(f"当前账号订阅等级：{label}，可能需要 Sublime+ 才能获取流媒体 URL")
                    else:
                        raise AuthenticationError(f"API 认证失败：{data.get('message', 'Unknown error')}")
                elif resp.status == 401:
                    raise AuthenticationError("API 凭证无效 (app_id / app_secret)")
                elif resp.status == 403:
                    raise AuthenticationError("API 凭证权限不足")
                else:
                    error_text = await resp.text()
                    raise QobuzError(f"HTTP {resp.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            logger.warning(f"凭证验证请求失败：{e}")
            raise
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法
            endpoint: API 端点（如 /track/getFileUrl）
            params: 查询参数
            data: 请求体
        
        Returns:
            响应 JSON
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        # 添加认证参数
        timestamp = int(time.time())
        signature = self._generate_signature(endpoint, timestamp)
        
        auth_params = {
            "app_id": self.config.app_id,
            "request_ts": timestamp,
            "request_sig": signature
        }
        
        if params:
            auth_params.update(params)
        
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retries:
            try:
                if method.upper() == "GET":
                    async with self._session.get(url, params=auth_params) as resp:
                        return await self._handle_response(resp)
                elif method.upper() == "POST":
                    async with self._session.post(url, params=auth_params, json=data) as resp:
                        return await self._handle_response(resp)
                else:
                    raise QobuzError(f"不支持的 HTTP 方法：{method}")
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                retry_count += 1
                if retry_count <= self.config.max_retries:
                    wait_time = 2 ** retry_count
                    logger.warning(f"请求失败，{wait_time}秒后重试：{e}")
                    await asyncio.sleep(wait_time)
                else:
                    break
        
        raise last_error or QobuzError("请求失败")
    
    async def _handle_response(self, resp: aiohttp.ClientResponse) -> Dict[str, Any]:
        """处理 HTTP 响应"""
        if resp.status == 200:
            data = await resp.json()
            if data.get("status") == "success" or "tracks" in data or "albums" in data:
                return data
            elif data.get("status") == "error":
                raise QobuzError(f"API 错误：{data.get('message', 'Unknown error')}")
            return data
        elif resp.status == 401:
            raise AuthenticationError("认证失败")
        elif resp.status == 403:
            # 检查是否是订阅问题
            raise SubscriptionError("需要 Qobuz Sublime+ 订阅才能访问此资源")
        elif resp.status == 404:
            raise NotFoundError(f"资源未找到")
        elif resp.status == 429:
            raise RateLimitError("请求速率限制")
        else:
            error_text = await resp.text()
            raise QobuzError(f"HTTP {resp.status}: {error_text}")
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        types: Optional[List[str]] = None
    ) -> List[QobuzTrackInfo]:
        """
        搜索音乐
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            types: 搜索类型 (tracks, albums, playlists, artists)
        
        Returns:
            QobuzTrackInfo 列表
        """
        if not self._initialized:
            raise QobuzError("插件未初始化")
        
        types = types or ["tracks"]
        results = []
        
        for search_type in types:
            try:
                endpoint = "/track/search"
                params = {
                    "query": query,
                    "limit": min(limit, 100),
                    "extra": "artist_ids"
                }
                
                response = await self._request("GET", endpoint, params=params)
                
                tracks_data = response.get("tracks", {}).get("items", [])
                
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
    
    def _parse_track(self, track_data: Dict[str, Any]) -> Optional[QobuzTrackInfo]:
        """解析音轨数据"""
        try:
            # Qobuz API 响应结构
            album_data = track_data.get("album", {})
            artist_data = track_data.get("performer", {}) or track_data.get("artist", {})
            
            # 获取音质信息
            audio_quality = AudioQuality.STANDARD
            bitrate = None
            sample_rate = None
            bit_depth = None
            codec = None
            hi_res = False
            hi_res_description = None
            
            # Qobuz 音质标识
            max_bit_depth = album_data.get("maximum_bit_depth", 16)
            maximum_sampling_rate = album_data.get("maximum_sampling_rate", 44.1)
            
            if max_bit_depth >= 24 or maximum_sampling_rate > 48:
                audio_quality = AudioQuality.HI_RES
                hi_res = True
                bit_depth = max_bit_depth
                sample_rate = maximum_sampling_rate * 1000  # 转换为 Hz
                codec = "FLAC"
                hi_res_description = f"{max_bit_depth}bit/{maximum_sampling_rate}kHz Hi-Res"
                # 估算比特率：bit_depth * sample_rate * 2 (立体声)
                bitrate = int(bit_depth * sample_rate * 2 / 1000)
            elif max_bit_depth == 16:
                audio_quality = AudioQuality.LOSSLESS
                bit_depth = 16
                sample_rate = 44100
                codec = "FLAC"
                bitrate = 1411  # CD 音质
                hi_res_description = "16bit/44.1kHz CD Quality"
            else:
                bitrate = 320
                codec = "MP3"
            
            # 提取艺术家信息
            artist_name = ""
            if isinstance(artist_data, dict):
                artist_name = artist_data.get("name", "")
            elif isinstance(artist_data, list) and len(artist_data) > 0:
                artist_name = artist_data[0].get("name", "")
            
            # 获取封面 URL
            cover_url = None
            album_image = album_data.get("image", {})
            if album_image:
                # Qobuz 提供多个尺寸的封面
                cover_url = album_image.get("large") or album_image.get("small") or album_image.get("thumbnail")
            
            # 解析年份
            year = None
            release_date = album_data.get("release_date_original") or album_data.get("release_date")
            if release_date:
                try:
                    year = int(release_date.split("-")[0])
                except (ValueError, IndexError):
                    pass
            
            return QobuzTrackInfo(
                id=str(track_data.get("id", "")),
                title=track_data.get("title", "Unknown"),
                artist=artist_name,
                album=album_data.get("title"),
                duration=track_data.get("duration", 0),
                source=self.name,
                cover_url=cover_url,
                year=year,
                genre=track_data.get("work", {}).get("genre", {}).get("name") if track_data.get("work") else None,
                track_number=track_data.get("track_number"),
                isrc=track_data.get("isrc"),
                composer=track_data.get("composer", {}).get("name") if track_data.get("composer") else None,
                publisher=album_data.get("publisher", {}).get("name") if album_data.get("publisher") else None,
                audio_quality=audio_quality,
                bitrate=bitrate,
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                codec=codec,
                hi_res=hi_res,
                hi_res_description=hi_res_description,
                album_id=str(album_data.get("id", "")) if album_data.get("id") else None,
                artist_id=str(artist_data.get("id", "")) if isinstance(artist_data, dict) and artist_data.get("id") else None
            )
            
        except Exception as e:
            logger.error(f"解析音轨数据失败：{e}")
            return None
    
    async def get_track_info(self, track_id: str) -> Optional[QobuzTrackInfo]:
        """
        获取音轨详细信息
        
        Args:
            track_id: 音轨 ID
        
        Returns:
            QobuzTrackInfo
        """
        if not self._initialized:
            raise QobuzError("插件未初始化")
        
        try:
            endpoint = "/track/get"
            params = {
                "track_id": track_id,
                "extra": "artist_ids"
            }
            
            response = await self._request("GET", endpoint, params=params)
            
            if not response:
                raise NotFoundError(f"音轨未找到：{track_id}")
            
            return self._parse_track(response)
            
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
            raise QobuzError("插件未初始化")
        
        quality = quality or self.config.audio_quality
        
        try:
            endpoint = "/track/getFileUrl"
            
            # 映射音质到 Qobuz format_id
            # Qobuz format_id: 1=MP3 320, 2=FLAC 16bit, 3=FLAC 24bit <96kHz, 4=FLAC 24bit >=96kHz
            if quality == AudioQuality.HI_RES:
                format_id = 4  # 最高音质
            elif quality == AudioQuality.LOSSLESS:
                format_id = 2  # CD Quality
            else:
                format_id = 1  # MP3
            
            params = {
                "track_id": track_id,
                "format_id": format_id,
                "intent": "stream"
            }
            
            response = await self._request("GET", endpoint, params=params)
            
            # 解析流媒体 URL
            url = response.get("url")
            if not url:
                raise QobuzError("未找到流媒体 URL")
            
            return url
            
        except SubscriptionError:
            logger.error(f"获取流媒体 URL 失败：需要 Qobuz Sublime+ 订阅")
            raise
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
        if not self._initialized:
            raise QobuzError("插件未初始化")
        
        quality = quality or self.config.audio_quality
        
        try:
            endpoint = "/track/getFileUrl"
            
            # 映射音质到 Qobuz format_id
            if quality == AudioQuality.HI_RES:
                format_id = 4  # 最高音质
            elif quality == AudioQuality.LOSSLESS:
                format_id = 2  # CD Quality
            else:
                format_id = 1  # MP3
            
            params = {
                "track_id": track_id,
                "format_id": format_id,
                "intent": "purchase"  # 购买意图用于下载
            }
            
            response = await self._request("GET", endpoint, params=params)
            
            url = response.get("url")
            if not url:
                raise QobuzError("未找到下载 URL")
            
            return url
            
        except SubscriptionError:
            logger.error(f"获取下载 URL 失败：需要 Qobuz Sublime+ 订阅")
            raise
        except Exception as e:
            logger.error(f"获取下载 URL 失败：{e}")
            return None
    
    async def get_album_tracks(self, album_id: str) -> List[QobuzTrackInfo]:
        """
        获取专辑的所有音轨
        
        Args:
            album_id: 专辑 ID
        
        Returns:
            音轨列表
        """
        if not self._initialized:
            raise QobuzError("插件未初始化")
        
        try:
            endpoint = "/album/get"
            params = {
                "album_id": album_id,
                "extra": "artist_ids"
            }
            
            response = await self._request("GET", endpoint, params=params)
            
            tracks = []
            tracks_data = response.get("tracks", {}).get("items", [])
            
            for track_data in tracks_data:
                track_info = self._parse_track(track_data)
                if track_info:
                    track_info.album_id = album_id
                    tracks.append(track_info)
            
            return tracks
            
        except Exception as e:
            logger.error(f"获取专辑音轨失败：{e}")
            return []
    
    async def get_playlist_tracks(self, playlist_id: str) -> List[QobuzTrackInfo]:
        """
        获取播放列表的所有音轨
        
        Args:
            playlist_id: 播放列表 ID
        
        Returns:
            音轨列表
        """
        if not self._initialized:
            raise QobuzError("插件未初始化")
        
        try:
            endpoint = "/playlist/get"
            params = {
                "playlist_id": playlist_id,
                "extra": "artist_ids",
                "limit": 300
            }
            
            response = await self._request("GET", endpoint, params=params)
            
            tracks = []
            tracks_data = response.get("tracks", {}).get("items", [])
            
            for track_data in tracks_data:
                track_info = self._parse_track(track_data)
                if track_info:
                    tracks.append(track_info)
            
            return tracks
            
        except Exception as e:
            logger.error(f"获取播放列表音轨失败：{e}")
            return []
    
    async def get_artist_top_tracks(self, artist_id: str, limit: int = 20) -> List[QobuzTrackInfo]:
        """
        获取艺术家的热门歌曲
        
        Args:
            artist_id: 艺术家 ID
            limit: 数量限制
        
        Returns:
            音轨列表
        """
        if not self._initialized:
            raise QobuzError("插件未初始化")
        
        try:
            endpoint = "/artist/get"
            params = {
                "artist_id": artist_id,
                "extra": "artist_ids",
                "limit": min(limit, 100)
            }
            
            response = await self._request("GET", endpoint, params=params)
            
            tracks = []
            tracks_data = response.get("albums", {}).get("items", [])
            
            # 从专辑中获取音轨
            for album_data in tracks_data[:5]:  # 限制前 5 个专辑
                album_id = album_data.get("id")
                if album_id:
                    album_tracks = await self.get_album_tracks(str(album_id))
                    tracks.extend(album_tracks[:4])  # 每个专辑取 4 首
            
            return tracks[:limit]
            
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
                "codec": "MP3",
                "bitrate": 320,
                "sample_rate": 44100,
                "bit_depth": 16,
                "description": "标准音质 (320kbps MP3)"
            },
            AudioQuality.LOSSLESS: {
                "codec": "FLAC",
                "bitrate": 1411,
                "sample_rate": 44100,
                "bit_depth": 16,
                "description": "无损音质 (16bit/44.1kHz FLAC - CD Quality)"
            },
            AudioQuality.HI_RES: {
                "codec": "FLAC",
                "bitrate": 4608,
                "sample_rate": 192000,
                "bit_depth": 24,
                "description": "高解析度无损 (24bit/192kHz FLAC - Hi-Res)"
            }
        }
        
        return quality_info.get(quality, {})
    
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
            endpoint = "/album/search"
            params = {
                "query": query,
                "limit": limit,
                "extra": "artist_ids"
            }
            
            response = await self._request("GET", endpoint, params=params)
            
            albums = []
            albums_data = response.get("albums", {}).get("items", [])
            
            for album_data in albums_data:
                artist_data = album_data.get("artist", {})
                artist_name = ""
                if isinstance(artist_data, dict):
                    artist_name = artist_data.get("name", "")
                
                album_image = album_data.get("image", {})
                cover_url = album_image.get("large") if album_image else None
                
                albums.append({
                    "id": str(album_data.get("id", "")),
                    "name": album_data.get("title"),
                    "artist": artist_name,
                    "release_date": album_data.get("release_date_original") or album_data.get("release_date"),
                    "track_count": album_data.get("tracks_count"),
                    "cover_url": cover_url,
                    "hi_res": album_data.get("maximum_bit_depth", 16) >= 24,
                    "url": f"https://www.qobuz.com/album/{album_data.get('id')}"
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
            endpoint = "/playlist/search"
            params = {
                "query": query,
                "limit": limit
            }
            
            response = await self._request("GET", endpoint, params=params)
            
            playlists = []
            playlists_data = response.get("playlists", {}).get("items", [])
            
            for playlist_data in playlists_data:
                owner_data = playlist_data.get("owner", {})
                owner_name = owner_data.get("name", "") if isinstance(owner_data, dict) else ""
                
                playlist_image = playlist_data.get("image", {})
                cover_url = playlist_image.get("large") if playlist_image else None
                
                playlists.append({
                    "id": str(playlist_data.get("id", "")),
                    "name": playlist_data.get("name"),
                    "curator": owner_name,
                    "track_count": playlist_data.get("tracks_count"),
                    "cover_url": cover_url,
                    "url": f"https://www.qobuz.com/playlist/{playlist_data.get('id')}"
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
            endpoint = "/artist/search"
            params = {
                "query": query,
                "limit": limit
            }
            
            response = await self._request("GET", endpoint, params=params)
            
            artists = []
            artists_data = response.get("artists", {}).get("items", [])
            
            for artist_data in artists_data:
                artist_image = artist_data.get("image", {})
                cover_url = artist_image.get("large") if artist_image else None
                
                artists.append({
                    "id": str(artist_data.get("id", "")),
                    "name": artist_data.get("name"),
                    "cover_url": cover_url,
                    "url": f"https://www.qobuz.com/artist/{artist_data.get('id')}"
                })
            
            return artists
            
        except Exception as e:
            logger.error(f"搜索艺术家失败：{e}")
            return []


# 插件工厂函数
def create_provider(config: Optional[Dict[str, Any]] = None) -> QobuzProvider:
    """
    创建 Qobuz 插件实例
    
    Args:
        config: 配置字典
    
    Returns:
        QobuzProvider 实例
    """
    return QobuzProvider(config)


# 注册到插件系统
def register(registry) -> None:
    """
    注册到插件注册表
    
    Args:
        registry: 插件注册表实例
    """
    provider = QobuzProvider()
    registry.register_source("qobuz", provider)
    logger.info("Qobuz 插件已注册")
