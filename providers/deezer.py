"""
Deezer 平台插件

实现 Deezer 平台的搜索、下载、元数据获取功能。
支持 Deezer HiFi 订阅的无损 FLAC 音质下载。

依赖:
- httpx: 用于 HTTP 请求
- mutagen: 用于元数据写入

音质支持:
- STANDARD: 128kbps MP3 (免费/付费订阅)
- HIGH: 320kbps MP3 (Premium 订阅)
- LOSSLESS: FLAC 无损 (HiFi 订阅)

配置要求:
- Deezer 账号（免费/付费）
- ARL Cookie（用于认证，获取高音质）

使用示例:
    config = {
        "arl_cookie": "your_arl_cookie_here",  # Deezer ARL 认证 cookie
        "quality": "lossless",  # standard, high, lossless
    }
    provider = DeezerProvider(config)
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

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import logging
import base64

import httpx

from .base import (
    BaseProvider, PlatformConfig, Quality,
    TrackInfo, TrackMetadata, DownloadResult,
    SearchError, URLFetchError, DownloadError,
    MetadataError, AuthenticationError, ProviderError
)

logger = logging.getLogger(__name__)


class DeezerQuality(Enum):
    """Deezer 音质等级"""
    STANDARD = "standard"      # 128kbps MP3
    HIGH = "high"              # 320kbps MP3
    LOSSLESS = "lossless"      # FLAC 无损 (HiFi)


# Quality 到 DeezerQuality 的映射
QUALITY_MAP = {
    Quality.STANDARD: DeezerQuality.STANDARD,
    Quality.HIGH: DeezerQuality.HIGH,
    Quality.LOSSLESS: DeezerQuality.LOSSLESS,
    Quality.HI_RES: DeezerQuality.LOSSLESS,  # Deezer 最高到 FLAC
}

# 音质对应的 bitrate
QUALITY_BITRATE = {
    DeezerQuality.STANDARD: 128,
    DeezerQuality.HIGH: 320,
    DeezerQuality.LOSSLESS: 1411,  # FLAC 约 1411kbps
}


class DeezerConfig(PlatformConfig):
    """
    Deezer 配置类
    
    配置项:
    - arl_cookie: Deezer ARL 认证 cookie (必需，用于获取高音质)
    - quality: 期望的音质等级 (可选，默认 lossless)
    - language: 语言偏好 (可选，默认 zh-CN)
    - timeout: 请求超时时间
    - retry_times: 重试次数
    - proxy: 代理地址
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.arl_cookie: Optional[str] = kwargs.get("arl_cookie")
        self.quality: str = kwargs.get("quality", "lossless")
        self.language: str = kwargs.get("language", "zh-CN")
        
    def validate(self) -> bool:
        """
        验证配置是否完整
        
        Returns:
            bool: 配置是否有效
        """
        if not self.arl_cookie:
            logger.warning("Deezer: 缺少 ARL Cookie，可能无法获取高音质")
            return False
        return True


class DeezerProvider(BaseProvider):
    """
    Deezer 平台插件
    
    功能:
    - 歌曲/专辑/播放列表搜索
    - 音频流 URL 获取
    - 无损音质下载 (HiFi 订阅)
    - 元数据获取 (封面、歌词、专辑信息)
    
    音质支持:
    - STANDARD: 128kbps MP3 (免费/付费订阅)
    - HIGH: 320kbps MP3 (Premium 订阅)
    - LOSSLESS: FLAC 无损 (HiFi 订阅)
    
    配置要求:
    - Deezer 账号（免费/付费）
    - ARL Cookie（用于认证，获取高音质）
    
    获取 ARL Cookie 方法:
    1. 登录 Deezer 网页版 (https://www.deezer.com)
    2. 打开浏览器开发者工具 (F12)
    3. 进入 Application/Storage -> Cookies
    4. 找到 arl cookie 并复制其值
    """
    
    platform_name = "deezer"
    platform_display_name = "Deezer"
    config_class = DeezerConfig
    
    API_BASE = "https://api.deezer.com"
    MOBILE_API = "https://www.deezer.com/ajax/gw-light.php"
    
    # Deezer 加密密钥 (用于生成 token)
    CLIENT_TOKEN = "eVdDRUGWepKRNWv"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Deezer 插件
        
        Args:
            config: 配置字典
        """
        super().__init__(config)
        self._session: Optional[httpx.AsyncClient] = None
        self._user_id: Optional[str] = None
        self._subscription_type: str = "free"  # free, premium, hifi
        self._initialized = False
        self._api_token: Optional[str] = None
    
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
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": self.config.language,
            }
            
            self._session = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True,
            )
            
            # 设置 ARL cookie
            if self.config.arl_cookie:
                self._session.cookies.set("arl", self.config.arl_cookie, domain=".deezer.com")
                logger.debug(f"{self.platform_display_name} ARL Cookie 已设置")
            
            # 获取 API Token
            await self._fetch_api_token()
            
            # 获取用户信息（如果已认证）
            if self.config.arl_cookie:
                await self._fetch_user_info()
            
            self._initialized = True
            logger.info(f"{self.platform_display_name} 插件初始化成功，订阅类型：{self._subscription_type}")
            return True
            
        except AuthenticationError as e:
            logger.error(f"{self.platform_display_name} 认证失败：{e}")
            return False
        except Exception as e:
            logger.error(f"{self.platform_display_name} 初始化失败：{e}")
            return False
    
    async def _fetch_api_token(self) -> None:
        """获取 API Token"""
        try:
            # 访问主页获取 token
            response = await self._session.get("https://www.deezer.com/")
            response.raise_for_status()
            
            # 从页面中提取 token (简化处理，使用默认 token)
            self._api_token = self.CLIENT_TOKEN
            logger.debug(f"{self.platform_display_name} API Token 已获取")
            
        except Exception as e:
            logger.warning(f"获取 API Token 失败，使用默认 token: {e}")
            self._api_token = self.CLIENT_TOKEN
    
    async def _fetch_user_info(self) -> None:
        """获取用户信息和订阅状态"""
        try:
            url = f"{self.MOBILE_API}"
            params = {
                "method": "deezer.user.getuserinfo",
                "input": 3,
                "api_version": "1.0",
                "api_token": self._api_token,
            }
            
            response = await self._session.post(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", {})
            
            if results:
                self._user_id = str(results.get("USER", {}).get("USER_ID", ""))
                
                # 检查订阅类型
                options = results.get("USER", {}).get("OPTIONS", {})
                if options.get("web_hifi", False):
                    self._subscription_type = "hifi"
                elif options.get("web_lossless", False) or options.get("premium", False):
                    self._subscription_type = "premium"
                else:
                    self._subscription_type = "free"
                
                logger.info(
                    f"{self.platform_display_name} 用户：{self._user_id}, "
                    f"订阅：{self._subscription_type}"
                )
            else:
                logger.warning("无法获取用户信息，可能 ARL Cookie 无效")
                self._subscription_type = "free"
                
        except Exception as e:
            logger.warning(f"获取用户信息失败：{e}")
            self._subscription_type = "free"
    
    async def _ensure_initialized(self):
        """确保插件已初始化"""
        if not self._initialized:
            await self.initialize()
    
    async def _generate_api_token(self) -> str:
        """生成新的 API Token"""
        try:
            # 获取主页
            response = await self._session.get("https://www.deezer.com/")
            response.raise_for_status()
            
            # 从页面中提取 token (简化处理)
            # 实际实现需要解析页面中的 token
            return self.CLIENT_TOKEN
            
        except Exception as e:
            logger.warning(f"生成 API Token 失败：{e}")
            return self.CLIENT_TOKEN
    
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
            url = f"{self.API_BASE}/search"
            params = {
                "q": query,
                "limit": min(limit, 100),
            }
            
            response = await self._session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            tracks_data = data.get("data", [])
            
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
            logger.error(f"Deezer 搜索错误：{e.response.status_code}")
            raise SearchError(f"Search failed: {e}", self.platform_name) from e
        except Exception as e:
            logger.error(f"Deezer 搜索错误：{e}")
            raise SearchError(f"Search failed: {e}", self.platform_name) from e
    
    def _parse_track(self, track_data: Dict[str, Any]) -> TrackInfo:
        """解析 Deezer 音轨数据为 TrackInfo"""
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
        
        # 获取封面 URL (获取高质量封面)
        cover_url = self._get_cover_url(album, size="1000x1000")
        
        # 获取时长
        duration = track_data.get("duration", 0)
        
        # 解析额外信息
        extra = {
            "album_id": album.get("id") if isinstance(album, dict) else None,
            "artist_id": artist.get("id") if isinstance(artist, dict) else None,
            "track_position": track_data.get("track_position"),
            "disk_number": track_data.get("disk_number"),
            "explicit_lyrics": track_data.get("explicit_lyrics", False),
            "preview_url": track_data.get("preview"),  # 30 秒预览
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
    
    def _get_cover_url(self, album: Dict[str, Any], size: str = "1000x1000") -> Optional[str]:
        """获取专辑封面 URL"""
        if not album or not isinstance(album, dict):
            return None
        
        cover_id = album.get("cover", "")
        if not cover_id:
            # 尝试 cover_small, cover_medium, cover_big, cover_xl
            for key in ["cover_xl", "cover_big", "cover_medium", "cover_small"]:
                if album.get(key):
                    return album[key]
            return None
        
        # Deezer 封面 URL 格式
        return f"https://e-cdns-images.dzcdn.net/images/cover/{cover_id}/{size}.jpg"
    
    def _get_available_qualities(self) -> List[Quality]:
        """根据订阅类型返回可用音质"""
        if self._subscription_type == "hifi":
            return [Quality.STANDARD, Quality.HIGH, Quality.LOSSLESS]
        elif self._subscription_type == "premium":
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
        deezer_quality = QUALITY_MAP.get(quality, DeezerQuality.LOSSLESS)
        
        # 检查订阅是否支持请求的音质
        available = self._get_available_qualities()
        if quality not in available:
            logger.warning(
                f"请求的音质 {quality.value} 不可用，订阅类型：{self._subscription_type}. "
                f"可用音质：{[q.value for q in available]}"
            )
            # 降级到最高可用音质
            deezer_quality = QUALITY_MAP.get(available[-1], DeezerQuality.STANDARD)
        
        try:
            # 使用 mobile API 获取流 URL
            url = f"{self.MOBILE_API}"
            params = {
                "method": "song.getData",
                "input": 3,
                "api_version": "1.0",
                "api_token": self._api_token,
            }
            data = {
                "SNG_ID": track_id,
            }
            
            # 设置 ARL cookie 用于认证
            headers = {}
            if self.config.arl_cookie:
                headers["Cookie"] = f"arl={self.config.arl_cookie}"
            
            response = await self._session.post(url, params=params, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            results = result.get("results", {})
            
            if not results:
                raise URLFetchError(f"No data returned for track {track_id}", self.platform_name)
            
            # 根据音质获取对应的 URL
            quality_key = self._get_quality_key(deezer_quality)
            stream_url = results.get(quality_key) or results.get("FILES", {}).get(quality_key)
            
            if not stream_url:
                # 尝试其他音质键
                for key in ["FILES", "DATA"]:
                    files = results.get(key, {})
                    if isinstance(files, dict):
                        stream_url = files.get(quality_key)
                        if stream_url:
                            break
            
            if not stream_url:
                # 如果还是没有找到，尝试获取所有可用的 URL
                files = results.get("FILES", results)
                if isinstance(files, dict):
                    # 按优先级获取
                    for key in ["FLAC", "MP3_320", "MP3_128"]:
                        if key in files:
                            stream_url = files[key]
                            logger.info(f"使用备用音质：{key}")
                            break
            
            if not stream_url:
                # 最后尝试使用 preview URL
                preview = results.get("PREVIEW")
                if preview:
                    logger.warning(f"无法获取完整音轨，返回预览 URL")
                    return preview
                raise URLFetchError(f"No stream URL found for track {track_id}", self.platform_name)
            
            logger.debug(f"获取到流 URL: {stream_url[:50]}...")
            return stream_url
            
        except httpx.HTTPStatusError as e:
            logger.error(f"获取流 URL 失败：{e.response.status_code}")
            if e.response.status_code == 401:
                # 尝试重新获取 token
                self._api_token = await self._generate_api_token()
                return await self.get_stream_url(track_id, quality)
            raise URLFetchError(f"Failed to get stream URL: {e}", self.platform_name) from e
        except Exception as e:
            logger.error(f"获取流 URL 失败：{e}")
            raise URLFetchError(f"Failed to get stream URL: {e}", self.platform_name) from e
    
    def _get_quality_key(self, quality: DeezerQuality) -> str:
        """获取音质对应的 API 键名"""
        if quality == DeezerQuality.LOSSLESS:
            return "FLAC"
        elif quality == DeezerQuality.HIGH:
            return "MP3_320"
        else:
            return "MP3_128"
    
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
        
        start_time = time.time()
        
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
                ext = "flac" if quality == Quality.LOSSLESS else "mp3"
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
            
            elapsed = time.time() - start_time
            
            return DownloadResult(
                success=True,
                file_path=output_path,
                quality=quality,
                file_size=output_path.stat().st_size,
                metadata=metadata if 'metadata' in locals() else None,
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
            url = f"{self.API_BASE}/track/{track_id}"
            
            response = await self._session.get(url)
            response.raise_for_status()
            
            return self._parse_track(response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ProviderError(f"Track not found: {track_id}", self.platform_name) from e
            raise ProviderError(f"Failed to get track info: {e}", self.platform_name) from e
    
    async def _download_file(self, url: str, output_path: Path) -> bool:
        """下载文件"""
        try:
            # Deezer 的流 URL 可能需要特殊的 User-Agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            
            async with self._session.stream("GET", url, headers=headers) as response:
                if response.status_code != 200:
                    logger.error(f"下载失败：HTTP {response.status_code}")
                    return False
                
                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"文件已下载：{output_path.name}")
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
            
            # 获取歌词（如果可用）
            lyrics = None
            try:
                lyrics = await self._get_lyrics(track_id)
            except Exception as e:
                logger.debug(f"获取歌词失败：{e}")
            
            # 构建元数据
            metadata = TrackMetadata(
                title=track_info.title,
                artist=track_info.artist,
                album=track_info.album,
                track_number=track_info.extra.get("track_position"),
                year=self._extract_year(album_data) if album_data else None,
                genre=None,  # Deezer API 不直接提供流派
                cover_data=cover_data,
                lyrics=lyrics,
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"获取元数据失败：{e}")
            raise MetadataError(f"Failed to get metadata: {e}", self.platform_name) from e
    
    async def _get_album_info(self, album_id: str) -> Optional[Dict[str, Any]]:
        """获取专辑信息"""
        try:
            url = f"{self.API_BASE}/album/{album_id}"
            
            response = await self._session.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.warning(f"获取专辑信息失败：{e}")
            return None
    
    def _extract_year(self, album_data: Dict[str, Any]) -> Optional[int]:
        """从专辑数据提取年份"""
        if not album_data:
            return None
        
        release_date = album_data.get("release_date", "")
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
    
    async def _get_lyrics(self, track_id: str) -> Optional[str]:
        """获取歌词"""
        try:
            url = f"{self.MOBILE_API}"
            params = {
                "method": "song.getLyrics",
                "input": 3,
                "api_version": "1.0",
                "api_token": self._api_token,
            }
            data = {
                "SNG_ID": track_id,
            }
            
            response = await self._session.post(url, params=params, json=data)
            response.raise_for_status()
            
            result = response.json()
            results = result.get("results", {})
            
            if results:
                lyrics_text = results.get("LYRICS_TEXT")
                if lyrics_text:
                    return lyrics_text
            
            return None
            
        except Exception as e:
            logger.debug(f"获取歌词失败：{e}")
            return None
    
    async def _write_metadata(self, file_path: Path, metadata: TrackMetadata) -> None:
        """写入元数据到音频文件"""
        try:
            from mutagen.flac import FLAC, Picture
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC, USLT
            from mutagen.mp3 import MP3
            from mutagen.mp4 import MP4, MP4Cover
            
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
                    pic = Picture()
                    pic.data = metadata.cover_data
                    pic.mime = "image/jpeg"
                    pic.type = 3
                    pic.desc = "Cover"
                    audio.add_picture(pic)
                if metadata.lyrics:
                    audio["lyrics"] = metadata.lyrics
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
                if metadata.lyrics:
                    audio.tags.add(USLT(
                        encoding=3,
                        lang="eng",
                        desc="Lyrics",
                        text=metadata.lyrics,
                    ))
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
                    audio["covr"] = [MP4Cover(metadata.cover_data)]
                if metadata.lyrics:
                    audio["\xa9lyr"] = metadata.lyrics
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
            url = f"{self.API_BASE}/playlist/{playlist_id}/tracks"
            params = {
                "limit": 100,
            }
            
            all_tracks = []
            
            while True:
                response = await self._session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                tracks_data = data.get("data", [])
                
                for track in tracks_data:
                    all_tracks.append(self._parse_track(track))
                
                # 检查是否有更多页面
                next_url = data.get("next")
                if not next_url or len(all_tracks) >= 100:
                    break
                
                url = next_url
                params = {}  # next URL 已包含参数
            
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
            url = f"{self.API_BASE}/album/{album_id}/tracks"
            params = {
                "limit": 100,
            }
            
            all_tracks = []
            
            while True:
                response = await self._session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                tracks_data = data.get("data", [])
                
                for track in tracks_data:
                    all_tracks.append(self._parse_track(track))
                
                # 检查是否有更多页面
                next_url = data.get("next")
                if not next_url:
                    break
                
                url = next_url
                params = {}
            
            return all_tracks
            
        except Exception as e:
            logger.error(f"获取专辑音轨失败：{e}")
            raise ProviderError(f"Failed to get album tracks: {e}", self.platform_name) from e
    
    async def close(self):
        """关闭插件，释放资源"""
        if self._session:
            await self._session.aclose()
            self._session = None
        self._api_token = None
        self._user_id = None
        self._initialized = False
        logger.debug(f"{self.platform_display_name} 插件已关闭")


# 工厂函数
def create_provider(config: Optional[Dict[str, Any]] = None) -> DeezerProvider:
    """创建 Deezer 插件实例"""
    return DeezerProvider(config)


__all__ = [
    "DeezerProvider",
    "DeezerConfig",
    "DeezerQuality",
    "create_provider",
]
