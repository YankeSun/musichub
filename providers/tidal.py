"""
Tidal 平台插件

实现 Tidal 平台的搜索、下载、元数据获取功能。
支持 HiFi 和 HiFi Plus 订阅的无损音质下载。

依赖:
- httpx: 用于 HTTP 请求
- mutagen: 用于元数据写入

音质支持:
- LOSSLESS: 16bit/44.1kHz FLAC (HiFi 订阅)
- HI_RES: 24bit/192kHz FLAC (HiFi Plus 订阅)
- HIGH: 320kbps AAC (免费/高级订阅)
- STANDARD: 96kbps AAC (免费订阅)

配置要求:
- Tidal 账号（免费/付费）
- API Token 或 Client ID/Secret（用于认证）
"""

import asyncio
import base64
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import logging
import re

import httpx

from .base import (
    BaseProvider, PlatformConfig, Quality,
    TrackInfo, TrackMetadata, DownloadResult,
    SearchError, URLFetchError, DownloadError,
    MetadataError, AuthenticationError, ProviderError
)

logger = logging.getLogger(__name__)


class TidalQuality(Enum):
    """Tidal 音质等级"""
    LOW = "LOW"  # 96kbps AAC
    HIGH = "HIGH"  # 320kbps AAC
    LOSSLESS = "LOSSLESS"  # 16bit/44.1kHz FLAC (HiFi)
    HI_RES = "HI_RES"  # 24bit/192kHz FLAC (HiFi Plus)
    HI_RES_LOSSLESS = "HI_RES_LOSSLESS"  # 24bit/192kHz FLAC (HiFi Plus)


# Quality 到 TidalQuality 的映射
QUALITY_MAP = {
    Quality.STANDARD: TidalQuality.LOW,
    Quality.HIGH: TidalQuality.HIGH,
    Quality.LOSSLESS: TidalQuality.LOSSLESS,
    Quality.HI_RES: TidalQuality.HI_RES,
}


class TidalConfig(PlatformConfig):
    """
    Tidal 配置类
    
    配置项:
    - api_token: Tidal API 访问令牌 (可选)
    - client_id: Tidal API Client ID (可选，默认使用内置)
    - client_secret: Tidal API Client Secret (可选，默认使用内置)
    - quality: 期望的音质等级 (可选，默认 LOSSLESS)
    - country_code: 国家/地区代码 (可选，默认 US)
    - timeout: 请求超时时间
    - retry_times: 重试次数
    - proxy: 代理地址
    """
    
    # 默认 Tidal Android 客户端凭证
    DEFAULT_CLIENT_ID = "km8T9pS355y7dd"
    DEFAULT_CLIENT_SECRET = "66k2C6IZmV7cbrQUN99VqKzrN5WQ33J2oZ7Cz2b5sNA="
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_token: Optional[str] = kwargs.get("api_token")
        self.client_id: str = kwargs.get("client_id", self.DEFAULT_CLIENT_ID)
        self.client_secret: str = kwargs.get("client_secret", self.DEFAULT_CLIENT_SECRET)
        self.quality: str = kwargs.get("quality", "LOSSLESS")
        self.country_code: str = kwargs.get("country_code", "US")
        
    def validate(self) -> bool:
        """
        验证配置是否完整
        
        Returns:
            bool: 配置是否有效
        """
        # 至少需要 api_token 或 client_id/secret
        if not self.api_token and (not self.client_id or not self.client_secret):
            logger.warning("Tidal: 缺少认证凭证 (api_token 或 client_id/client_secret)")
            return False
        return True


class TidalProvider(BaseProvider):
    """
    Tidal 平台插件
    
    功能:
    - 歌曲/专辑/播放列表搜索
    - 音频流 URL 获取
    - 无损音质下载 (HiFi/HiFi Plus)
    - 元数据获取 (封面、歌词、专辑信息)
    
    音质支持:
    - STANDARD: 96kbps AAC
    - HIGH: 320kbps AAC
    - LOSSLESS: 16bit/44.1kHz FLAC (需要 HiFi 订阅)
    - HI_RES: 24bit/192kHz FLAC (需要 HiFi Plus 订阅)
    
    配置要求:
    - Tidal 账号（免费/付费）
    - API Token 或 Client ID/Secret（用于认证）
    
    使用示例:
        config = {
            "client_id": "your_client_id",  # 可选，使用默认
            "client_secret": "your_client_secret",  # 可选，使用默认
            "quality": "LOSSLESS",  # LOSSLESS 或 HI_RES
        }
        provider = TidalProvider(config)
        await provider.initialize()
        
        # 搜索歌曲
        results = await provider.search("Bohemian Rhapsody")
        
        # 下载无损音质
        result = await provider.download(
            track_id="12345678",
            save_path=Path("./downloads"),
            quality=Quality.LOSSLESS
        )
    """
    
    platform_name = "tidal"
    platform_display_name = "Tidal"
    config_class = TidalConfig
    
    BASE_URL = "https://api.tidalhifi.com/v1"
    AUTH_URL = "https://auth.tidal.com/v1"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Tidal 插件
        
        Args:
            config: 配置字典
        """
        super().__init__(config)
        self._session: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._subscription_type: str = "FREE"
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        初始化插件
        
        建立 HTTP 会话，验证认证
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 初始化 HTTP 会话
            headers = {
                "User-Agent": "Tidal/2.89.0 (Android; Android 13)",
                "X-Tidal-Unit": "android",
            }
            
            self._session = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True,
            )
            
            # 认证
            if self.config.api_token:
                self._access_token = self.config.api_token
                logger.info(f"{self.platform_display_name} 插件初始化成功 (使用 API Token)")
            else:
                # 使用客户端凭证获取 token
                await self._authenticate_with_client_credentials()
                logger.info(f"{self.platform_display_name} 插件初始化成功 (使用客户端凭证)")
            
            # 获取用户信息
            await self._fetch_user_info()
            
            self._initialized = True
            return True
            
        except AuthenticationError as e:
            logger.error(f"{self.platform_display_name} 认证失败：{e}")
            return False
        except Exception as e:
            logger.error(f"{self.platform_display_name} 初始化失败：{e}")
            return False
    
    async def _authenticate_with_client_credentials(self) -> None:
        """
        使用客户端凭证获取访问令牌
        
        Raises:
            AuthenticationError: 认证失败时抛出
        """
        try:
            url = f"{self.AUTH_URL}/oauth2/token"
            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "grant_type": "client_credentials",
            }
            
            response = await self._session.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            self._access_token = result.get("access_token")
            
            if not self._access_token:
                raise AuthenticationError("Failed to get access token", self.platform_name)
            
            logger.debug(f"{self.platform_display_name} 认证成功")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid client credentials", self.platform_name) from e
            raise AuthenticationError(f"Authentication failed: {e}", self.platform_name) from e
        except Exception as e:
            raise AuthenticationError(f"Authentication error: {e}", self.platform_name) from e
    
    async def _fetch_user_info(self) -> None:
        """获取用户信息和订阅状态"""
        try:
            url = f"{self.BASE_URL}/user"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            
            response = await self._session.get(url, headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            self._user_id = str(user_data.get("id", ""))
            
            # 获取订阅信息
            subscription = user_data.get("subscription", {})
            self._subscription_type = subscription.get("type", "FREE")
            
            # 更新国家代码
            self.config.country_code = user_data.get("countryCode", "US")
            
            logger.info(
                f"{self.platform_display_name} 用户：{self._user_id}, "
                f"订阅：{self._subscription_type}, 国家：{self.config.country_code}"
            )
            
        except Exception as e:
            logger.warning(f"获取用户信息失败：{e}")
            self._subscription_type = "FREE"
    
    async def _ensure_initialized(self):
        """确保插件已初始化"""
        if not self._initialized:
            await self.initialize()
    
    async def search(self, query: str, limit: int = 20) -> List[TrackInfo]:
        """
        搜索歌曲
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            List[TrackInfo]: 搜索结果列表
            
        Raises:
            SearchError: 搜索失败时抛出
        """
        await self._ensure_initialized()
        
        try:
            url = f"{self.BASE_URL}/search"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            params = {
                "query": query,
                "limit": min(limit, 100),
                "offset": 0,
                "types": "tracks",
                "countryCode": self.config.country_code,
            }
            
            response = await self._session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            tracks_data = data.get("tracks", {}).get("items", [])
            
            results = []
            for track in tracks_data:
                if track:
                    track_info = self._parse_track(track)
                    # 根据订阅设置可用音质
                    track_info.quality_available = self._get_available_qualities()
                    results.append(track_info)
                    
                    if len(results) >= limit:
                        break
            
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Tidal 搜索错误：{e.response.status_code}")
            if e.response.status_code == 401:
                await self._authenticate_with_client_credentials()
                return await self.search(query, limit)
            raise SearchError(f"Search failed: {e}", self.platform_name) from e
        except Exception as e:
            logger.error(f"Tidal 搜索错误：{e}")
            raise SearchError(f"Search failed: {e}", self.platform_name) from e
    
    def _parse_track(self, track_data: Dict[str, Any]) -> TrackInfo:
        """解析 Tidal 音轨数据为 TrackInfo"""
        artist = track_data.get("artist", {})
        album = track_data.get("album", {})
        
        # 解析艺术家名称
        if isinstance(artist, dict):
            artist_name = artist.get("name", "Unknown Artist")
        else:
            artist_name = str(artist)
        
        # 解析专辑名称
        if isinstance(album, dict):
            album_name = album.get("title", "")
        else:
            album_name = str(album) if album else ""
        
        # 获取封面 URL
        cover_url = self._get_cover_url(album)
        
        # 获取时长
        duration = track_data.get("duration", 0)
        
        # 解析额外信息
        extra = {
            "album_id": album.get("id") if isinstance(album, dict) else None,
            "artist_id": artist.get("id") if isinstance(artist, dict) else None,
            "track_number": track_data.get("trackNumber"),
            "release_date": album.get("releaseDate") if isinstance(album, dict) else None,
            "explicit": track_data.get("explicit", False),
            "popularity": track_data.get("popularity", 0),
        }
        
        return TrackInfo(
            id=str(track_data.get("id", "")),
            title=track_data.get("title", "Unknown"),
            artist=artist_name,
            album=album_name,
            duration=duration,
            cover_url=cover_url,
            extra=extra,
        )
    
    def _get_cover_url(self, album: Dict[str, Any], size: str = "1280x1280") -> Optional[str]:
        """获取专辑封面 URL"""
        if not album or not isinstance(album, dict):
            return None
        
        cover_id = album.get("cover", "")
        if not cover_id:
            return None
        
        # Tidal 封面 URL 格式：替换 - 为 /
        cover_id = cover_id.replace("-", "/")
        return f"https://resources.tidal.com/images/{cover_id}/{size}.jpg"
    
    def _get_available_qualities(self) -> List[Quality]:
        """根据订阅类型返回可用音质"""
        if self._subscription_type == "HIFI_PLUS":
            return [Quality.STANDARD, Quality.HIGH, Quality.LOSSLESS, Quality.HI_RES]
        elif self._subscription_type == "HIFI":
            return [Quality.STANDARD, Quality.HIGH, Quality.LOSSLESS]
        elif self._subscription_type == "PREMIUM":
            return [Quality.STANDARD, Quality.HIGH]
        else:
            return [Quality.STANDARD]
    
    async def get_stream_url(self, track_id: str, quality: Quality = Quality.LOSSLESS) -> str:
        """
        获取歌曲流媒体 URL
        
        Args:
            track_id: 歌曲 ID
            quality: 期望的音质质量
            
        Returns:
            str: 流媒体 URL
            
        Raises:
            URLFetchError: 获取 URL 失败时抛出
        """
        await self._ensure_initialized()
        
        # 映射音质
        tidal_quality = QUALITY_MAP.get(quality, TidalQuality.LOSSLESS)
        
        # 检查订阅是否支持请求的音质
        available = self._get_available_qualities()
        if quality not in available:
            logger.warning(
                f"请求的音质 {quality.value} 不可用，订阅类型：{self._subscription_type}. "
                f"可用音质：{[q.value for q in available]}"
            )
            # 降级到最高可用音质
            tidal_quality = QUALITY_MAP.get(available[-1], TidalQuality.HIGH)
        
        try:
            url = f"{self.BASE_URL}/tracks/{track_id}/playbackinfopostpaywall"
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "X-Tidal-Unit": "android",
            }
            params = {
                "countryCode": self.config.country_code,
                "playbackmode": "STREAM",
                "assetpresentation": "FULL",
            }
            json_data = {
                "audioquality": tidal_quality.value,
            }
            
            response = await self._session.post(
                url,
                headers=headers,
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 解析响应
            if "manifest" in data:
                # 新版 API 返回 manifest (base64 编码)
                manifest = data["manifest"]
                manifest_mime = manifest.get("mimeType", "application/dash+xml")
                
                if manifest_mime == "application/dash+xml":
                    # DASH manifest
                    manifest_data = base64.b64decode(manifest.get("data", "")).decode("utf-8")
                    # 从 DASH manifest 提取 URL
                    stream_url = self._extract_dash_url(manifest_data)
                    if stream_url:
                        return stream_url
                
                elif manifest_mime == "video/mp4":
                    # MP4 流（可能加密）
                    manifest_data = base64.b64decode(manifest.get("data", "")).decode("utf-8")
                    # 解析 MP4 manifest
                    stream_url = self._extract_mp4_url(manifest_data)
                    if stream_url:
                        return stream_url
            
            # 旧版 API 直接返回 URL
            if "streamUrl" in data:
                return data["streamUrl"]
            
            raise URLFetchError(f"No stream URL found in response", self.platform_name)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                await self._authenticate_with_client_credentials()
                return await self.get_stream_url(track_id, quality)
            if e.response.status_code == 403:
                raise URLFetchError(
                    f"Access denied. This track may require a higher subscription tier.",
                    self.platform_name
                ) from e
            raise URLFetchError(f"Failed to get stream URL: {e}", self.platform_name) from e
        except Exception as e:
            raise URLFetchError(f"Failed to get stream URL: {e}", self.platform_name) from e
    
    def _extract_dash_url(self, manifest_xml: str) -> Optional[str]:
        """从 DASH manifest 提取流 URL"""
        try:
            root = ET.fromstring(manifest_xml)
            ns = {"mpd": "urn:mpeg:dash:schema:mpd:2011"}
            
            # 查找 BaseURL
            base_url = root.findtext(".//mpd:BaseURL", "", ns)
            if base_url:
                return base_url
            
            # 查找 SegmentURL
            segment = root.find(".//mpd:SegmentURL", ns)
            if segment is not None:
                media_url = segment.get("media")
                if media_url:
                    return media_url
            
            return None
            
        except ET.ParseError as e:
            logger.warning(f"解析 DASH manifest 失败：{e}")
            return None
    
    def _extract_mp4_url(self, manifest_data: str) -> Optional[str]:
        """从 MP4 manifest 提取流 URL"""
        # MP4 manifest 通常是 JSON 格式
        try:
            import json
            manifest = json.loads(manifest_data)
            
            # 尝试提取 URL
            if "url" in manifest:
                return manifest["url"]
            if "urls" in manifest and len(manifest["urls"]) > 0:
                return manifest["urls"][0]
            
            return None
            
        except Exception as e:
            logger.warning(f"解析 MP4 manifest 失败：{e}")
            return None
    
    async def download(
        self,
        track_id: str,
        save_path: Path,
        quality: Quality = Quality.LOSSLESS,
    ) -> DownloadResult:
        """
        下载歌曲
        
        Args:
            track_id: 歌曲 ID
            save_path: 保存路径（目录或完整文件路径）
            quality: 期望的音质质量
            
        Returns:
            DownloadResult: 下载结果
        """
        await self._ensure_initialized()
        
        try:
            # 获取音轨信息
            track_info = await self._get_track_info(track_id)
            
            # 获取流 URL
            stream_url = await self.get_stream_url(track_id, quality)
            
            # 确定保存路径
            if save_path.is_dir():
                # 是目录，生成文件名
                safe_title = self._sanitize_filename(track_info.title)
                safe_artist = self._sanitize_filename(track_info.artist)
                
                # 根据音质确定扩展名
                ext = "flac" if quality in (Quality.LOSSLESS, Quality.HI_RES) else "m4a"
                filename = f"{safe_artist} - {safe_title}.{ext}"
                output_path = save_path / filename
            else:
                output_path = save_path
            
            # 确保目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 下载文件
            downloaded = await self._download_file(stream_url, output_path)
            
            if not downloaded:
                return DownloadResult(
                    success=False,
                    error="Download failed",
                    quality=quality,
                )
            
            # 获取并写入元数据
            try:
                metadata = await self.get_metadata(track_id)
                await self._write_metadata(output_path, metadata)
            except Exception as e:
                logger.warning(f"写入元数据失败：{e}")
            
            return DownloadResult(
                success=True,
                file_path=output_path,
                quality=quality,
                file_size=output_path.stat().st_size,
            )
            
        except Exception as e:
            logger.error(f"下载失败：{e}")
            return DownloadResult(
                success=False,
                error=str(e),
                quality=quality,
            )
    
    async def _get_track_info(self, track_id: str) -> TrackInfo:
        """获取音轨详细信息"""
        try:
            url = f"{self.BASE_URL}/tracks/{track_id}"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            params = {"countryCode": self.config.country_code}
            
            response = await self._session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            return self._parse_track(response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ProviderError(f"Track not found: {track_id}", self.platform_name) from e
            raise ProviderError(f"Failed to get track info: {e}", self.platform_name) from e
    
    async def _download_file(self, url: str, output_path: Path) -> bool:
        """下载文件"""
        try:
            async with self._session.stream("GET", url) as response:
                if response.status_code != 200:
                    logger.error(f"下载失败：HTTP {response.status_code}")
                    return False
                
                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                
                return True
                
        except Exception as e:
            logger.error(f"下载失败：{e}")
            return False
    
    def _sanitize_filename(self, name: str) -> str:
        """清理文件名中的非法字符"""
        # 移除或替换非法字符
        illegal_chars = r'[<>:"/\\|？*]'
        sanitized = re.sub(illegal_chars, "_", name)
        return sanitized.strip()
    
    async def get_metadata(self, track_id: str) -> TrackMetadata:
        """
        获取歌曲元数据
        
        Args:
            track_id: 歌曲 ID
            
        Returns:
            TrackMetadata: 歌曲元数据
            
        Raises:
            MetadataError: 获取元数据失败时抛出
        """
        await self._ensure_initialized()
        
        try:
            # 获取音轨详细信息
            track_info = await self._get_track_info(track_id)
            
            # 获取专辑信息
            album_id = track_info.extra.get("album_id")
            album_data = None
            if album_id:
                album_data = await self._get_album_info(album_id)
            
            # 获取封面数据
            cover_data = None
            if track_info.cover_url:
                cover_data = await self._download_cover(track_info.cover_url)
            
            # 构建元数据
            metadata = TrackMetadata(
                title=track_info.title,
                artist=track_info.artist,
                album=track_info.album,
                track_number=track_info.extra.get("track_number"),
                year=self._extract_year(album_data) if album_data else None,
                genre=None,  # Tidal API 不直接提供流派
                cover_data=cover_data,
                lyrics=None,  # 需要额外 API 调用
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"获取元数据失败：{e}")
            raise MetadataError(f"Failed to get metadata: {e}", self.platform_name) from e
    
    async def _get_album_info(self, album_id: str) -> Optional[Dict[str, Any]]:
        """获取专辑信息"""
        try:
            url = f"{self.BASE_URL}/albums/{album_id}"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            params = {"countryCode": self.config.country_code}
            
            response = await self._session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.warning(f"获取专辑信息失败：{e}")
            return None
    
    def _extract_year(self, album_data: Dict[str, Any]) -> Optional[int]:
        """从专辑数据提取年份"""
        if not album_data:
            return None
        
        release_date = album_data.get("releaseDate", "")
        if release_date:
            try:
                return int(release_date[:4])
            except (ValueError, TypeError):
                pass
        return None
    
    async def _download_cover(self, cover_url: str) -> Optional[bytes]:
        """下载封面图片"""
        try:
            response = await self._session.get(cover_url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.warning(f"下载封面失败：{e}")
            return None
    
    async def _write_metadata(self, file_path: Path, metadata: TrackMetadata) -> None:
        """写入元数据到音频文件"""
        try:
            from mutagen.flac import FLAC
            from mutagen.mp4 import MP4
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC
            from mutagen.mp3 import MP3
            
            ext = file_path.suffix.lower()
            
            if ext == ".flac":
                audio = FLAC(file_path)
                audio["title"] = metadata.title
                audio["artist"] = metadata.artist
                if metadata.album:
                    audio["album"] = metadata.album
                if metadata.year:
                    audio["date"] = str(metadata.year)
                if metadata.track_number:
                    audio["tracknumber"] = str(metadata.track_number)
                if metadata.cover_data:
                    audio.clear_pictures()
                    from mutagen.flac import Picture
                    pic = Picture()
                    pic.data = metadata.cover_data
                    pic.mime = "image/jpeg"
                    pic.type = 3
                    pic.desc = "Cover"
                    audio.add_picture(pic)
                audio.save()
                
            elif ext == ".m4a":
                audio = MP4(file_path)
                audio["\xa9nam"] = metadata.title
                audio["\xa9ART"] = metadata.artist
                if metadata.album:
                    audio["\xa9alb"] = metadata.album
                if metadata.year:
                    audio["\xa9day"] = str(metadata.year)
                if metadata.track_number:
                    audio["trkn"] = [(metadata.track_number, 0)]
                if metadata.cover_data:
                    from mutagen.mp4 import MP4Cover
                    audio["covr"] = [MP4Cover(metadata.cover_data)]
                audio.save()
                
            elif ext == ".mp3":
                audio = MP3(file_path)
                if audio.tags is None:
                    audio.add_tags()
                audio.tags.add(TIT2(encoding=3, text=metadata.title))
                audio.tags.add(TPE1(encoding=3, text=metadata.artist))
                if metadata.album:
                    audio.tags.add(TALB(encoding=3, text=metadata.album))
                if metadata.year:
                    audio.tags.add(TDRC(encoding=3, text=str(metadata.year)))
                if metadata.track_number:
                    audio.tags.add(TRCK(encoding=3, text=str(metadata.track_number)))
                if metadata.cover_data:
                    audio.tags.add(APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=metadata.cover_data,
                    ))
                audio.save()
            
            logger.debug(f"已写入元数据：{file_path.name}")
            
        except ImportError:
            logger.warning("mutagen 未安装，跳过元数据写入")
        except Exception as e:
            logger.warning(f"写入元数据失败：{e}")
    
    async def get_playlist(self, playlist_id: str) -> List[TrackInfo]:
        """
        获取歌单歌曲列表
        
        Args:
            playlist_id: 歌单 ID
            
        Returns:
            List[TrackInfo]: 歌单中的歌曲列表
        """
        await self._ensure_initialized()
        
        try:
            url = f"{self.BASE_URL}/playlists/{playlist_id}/items"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            params = {
                "countryCode": self.config.country_code,
                "limit": 100,
                "offset": 0,
            }
            
            all_tracks = []
            
            while True:
                response = await self._session.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("items", [])
                
                for item in items:
                    track = item.get("track")
                    if track:
                        all_tracks.append(self._parse_track(track))
                
                # 检查是否有更多页面
                total = data.get("totalNumberOfItems", 0)
                if len(all_tracks) >= total:
                    break
                
                params["offset"] += params["limit"]
            
            return all_tracks
            
        except Exception as e:
            logger.error(f"获取歌单失败：{e}")
            raise ProviderError(f"Failed to get playlist: {e}", self.platform_name) from e
    
    async def get_album_tracks(self, album_id: str) -> List[TrackInfo]:
        """
        获取专辑中的所有音轨
        
        Args:
            album_id: 专辑 ID
            
        Returns:
            List[TrackInfo]: 专辑中的歌曲列表
        """
        await self._ensure_initialized()
        
        try:
            url = f"{self.BASE_URL}/albums/{album_id}/items"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            params = {
                "countryCode": self.config.country_code,
                "limit": 100,
                "offset": 0,
            }
            
            all_tracks = []
            
            while True:
                response = await self._session.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("items", [])
                
                for item in items:
                    if "track" in item:
                        all_tracks.append(self._parse_track(item["track"]))
                    elif "id" in item:
                        all_tracks.append(self._parse_track(item))
                
                # 检查是否有更多页面
                total = data.get("totalNumberOfItems", 0)
                if len(all_tracks) >= total:
                    break
                
                params["offset"] += params["limit"]
            
            return all_tracks
            
        except Exception as e:
            logger.error(f"获取专辑音轨失败：{e}")
            raise ProviderError(f"Failed to get album tracks: {e}", self.platform_name) from e
    
    async def close(self):
        """关闭插件，释放资源"""
        if self._session:
            await self._session.aclose()
            self._session = None
        self._access_token = None
        self._user_id = None
        self._initialized = False
        logger.debug(f"{self.platform_display_name} 插件已关闭")


# 工厂函数
def create_provider(config: Optional[Dict[str, Any]] = None) -> TidalProvider:
    """创建 Tidal 插件实例"""
    return TidalProvider(config)


__all__ = [
    "TidalProvider",
    "TidalConfig",
    "TidalQuality",
    "create_provider",
]
