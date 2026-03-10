"""
Spotify 平台插件

实现 Spotify 平台的搜索、下载、元数据获取功能。
通过 spotDL 集成实现下载，支持 STANDARD (128kbps) 和 HIGH (320kbps) 音质。
注意：Spotify 无真正无损音质。

依赖:
- spotDL: 用于下载和元数据获取
- spotipy: 用于 Spotify API 交互
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

import httpx

from .base import (
    BaseProvider, PlatformConfig, Quality,
    TrackInfo, TrackMetadata, DownloadResult,
    SearchError, URLFetchError, DownloadError,
    MetadataError, AuthenticationError
)

logger = logging.getLogger(__name__)


class SpotifyConfig(PlatformConfig):
    """
    Spotify 配置类
    
    配置项:
    - client_id: Spotify API Client ID (必需)
    - client_secret: Spotify API Client Secret (必需)
    - use_premium: 是否使用 Premium 账号 (可选，用于更高音质)
    - cookie: Spotify 认证 cookie (可选)
    - timeout: 请求超时时间
    - retry_times: 重试次数
    - proxy: 代理地址
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client_id: Optional[str] = kwargs.get("client_id")
        self.client_secret: Optional[str] = kwargs.get("client_secret")
        self.use_premium: bool = kwargs.get("use_premium", False)
        self.cookie: Optional[str] = kwargs.get("cookie")
        
    def validate(self) -> bool:
        """
        验证配置是否完整
        
        Returns:
            bool: 配置是否有效
        """
        # Client ID 和 Secret 是必需的
        if not self.client_id or not self.client_secret:
            logger.warning("Spotify: 缺少 client_id 或 client_secret，部分功能可能受限")
            return False
        return True


class SpotifyProvider(BaseProvider):
    """
    Spotify 平台插件
    
    功能:
    - 歌曲/专辑/播放列表搜索
    - 音频流 URL 获取 (通过 spotDL)
    - 歌曲下载 (通过 spotDL 集成)
    - 元数据获取 (封面、歌词、专辑信息)
    
    音质支持:
    - STANDARD: 128kbps
    - HIGH: 320kbps
    - 注意：Spotify 不提供真正的无损音质
    
    配置要求:
    - Spotify Premium 账号 (可选，用于更高音质)
    - Client ID/Secret (用于 API 认证)
    
    使用示例:
        config = {
            "client_id": "your_client_id",
            "client_secret": "your_client_secret",
            "use_premium": True,
        }
        provider = SpotifyProvider(config)
        await provider.initialize()
        
        # 搜索歌曲
        results = await provider.search("Bohemian Rhapsody")
        
        # 下载歌曲
        result = await provider.download(
            track_id="4u7EnebtmKWzUH433cf5Qv",
            save_path=Path("./downloads"),
            quality=Quality.HIGH
        )
    """
    
    platform_name = "spotify"
    platform_display_name = "Spotify"
    config_class = SpotifyConfig
    
    # Spotify 音质映射 (注意：Spotify 无真正无损)
    QUALITY_MAP = {
        Quality.STANDARD: {"bitrate": 128, "name": "128kbps"},
        Quality.HIGH: {"bitrate": 320, "name": "320kbps"},
        # Spotify 不支持真正的无损，LOSSLESS 和 HI_RES 降级为 HIGH
        Quality.LOSSLESS: {"bitrate": 320, "name": "320kbps (best available)"},
        Quality.HI_RES: {"bitrate": 320, "name": "320kbps (best available)"},
    }
    
    # Spotify URL 正则
    TRACK_PATTERN = re.compile(r'spotify\.com/track/([a-zA-Z0-9]+)')
    ALBUM_PATTERN = re.compile(r'spotify\.com/album/([a-zA-Z0-9]+)')
    PLAYLIST_PATTERN = re.compile(r'spotify\.com/playlist/([a-zA-Z0-9]+)')
    ARTIST_PATTERN = re.compile(r'spotify\.com/artist/([a-zA-Z0-9]+)')
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Spotify 插件
        
        Args:
            config: 配置字典
        """
        super().__init__(config)
        self._session: Optional[httpx.AsyncClient] = None
        self._spotipy_client = None
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._initialized = False
        
        # spotDL 配置
        self._spotdl_options: Dict[str, Any] = {}
    
    async def initialize(self) -> bool:
        """
        初始化插件
        
        建立 HTTP 会话，验证 API 认证
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 初始化 HTTP 会话
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            
            if self.config.cookie:
                headers["Cookie"] = self.config.cookie
            
            self._session = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True,
            )
            
            # 验证配置
            if self.config.client_id and self.config.client_secret:
                # 获取访问令牌
                await self._refresh_token()
                logger.info(f"{self.platform_display_name} 插件初始化成功 (API 认证已配置)")
            else:
                logger.warning(f"{self.platform_display_name} 插件初始化：缺少 API 凭证，功能可能受限")
            
            # 配置 spotDL 选项
            self._spotdl_options = {
                "format": "mp3",
                "bitrate": "320k" if self.config.use_premium else "128k",
                "save_file": None,  # 使用默认命名
                "output": "{artists} - {title}.{output-ext}",
                "restrict": None,
                "print_errors": False,
            }
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"{self.platform_display_name} 初始化失败：{e}")
            return False
    
    async def _refresh_token(self) -> None:
        """
        刷新 Spotify API 访问令牌
        
        Raises:
            AuthenticationError: 认证失败时抛出
        """
        import time
        
        # 检查令牌是否仍然有效
        if self._access_token and time.time() < self._token_expires_at - 60:
            return  # 令牌仍然有效
        
        # 获取新的访问令牌
        token_url = "https://accounts.spotify.com/api/token"
        auth_data = {
            "grant_type": "client_credentials",
        }
        auth = (self.config.client_id, self.config.client_secret)
        
        try:
            response = await self._session.post(token_url, data=auth_data, auth=auth)
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            self._token_expires_at = time.time() + token_data["expires_in"]
            
            logger.debug("Spotify API 令牌已刷新")
            
        except httpx.HTTPError as e:
            raise AuthenticationError(
                f"获取 Spotify API 令牌失败：{e}",
                self.platform_name
            )
    
    async def _get_with_retry(self, url: str, max_retries: int = 3) -> httpx.Response:
        """
        带重试的 GET 请求
        
        Args:
            url: 请求 URL
            max_retries: 最大重试次数
            
        Returns:
            httpx.Response: 响应对象
            
        Raises:
            httpx.HTTPError: 请求失败时抛出
        """
        retries = 0
        last_error = None
        
        while retries <= max_retries:
            try:
                headers = self._session.headers.copy()
                if self._access_token:
                    headers["Authorization"] = f"Bearer {self._access_token}"
                
                response = await self._session.get(url, headers=headers)
                response.raise_for_status()
                return response
                
            except httpx.HTTPError as e:
                last_error = e
                retries += 1
                if retries <= max_retries:
                    await asyncio.sleep(1.0 * retries)  # 指数退避
        
        raise last_error
    
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
        if not self._initialized:
            await self.initialize()
        
        try:
            # 确保有有效的访问令牌
            if self.config.client_id and self.config.client_secret:
                await self._refresh_token()
            
            # 使用 Spotify API 搜索
            search_url = "https://api.spotify.com/v1/search"
            params = {
                "q": query,
                "type": "track",
                "limit": min(limit, 50),  # Spotify API 最大限制 50
                "market": "from_token" if self._access_token else "US",
            }
            
            response = await self._get_with_retry(search_url)
            data = response.json()
            
            tracks_data = data.get("tracks", {}).get("items", [])
            
            results = []
            for track_data in tracks_data[:limit]:
                # 跳过不可播放的曲目
                if not track_data.get("is_playable", True):
                    continue
                
                # 解析艺术家信息
                artists = track_data.get("artists", [])
                artist_names = [a.get("name", "") for a in artists]
                artist_ids = [a.get("id", "") for a in artists]
                
                # 解析专辑信息
                album = track_data.get("album", {})
                
                # 构建 TrackInfo
                track = TrackInfo(
                    id=track_data.get("id", ""),
                    title=track_data.get("name", ""),
                    artist=", ".join(artist_names),
                    album=album.get("name") if album else None,
                    duration=track_data.get("duration_ms", 0) // 1000,
                    cover_url=self._get_cover_url(album),
                    quality_available=[Quality.STANDARD, Quality.HIGH],  # Spotify 支持的音质
                    extra={
                        "album_id": album.get("id") if album else None,
                        "artists": artists,
                        "artist_ids": artist_ids,
                        "popularity": track_data.get("popularity", 0),
                        "preview_url": track_data.get("preview_url"),
                        "external_urls": track_data.get("external_urls", {}),
                        "isrc": track_data.get("external_ids", {}).get("isrc"),
                    },
                )
                results.append(track)
            
            logger.info(f"Spotify 搜索 '{query}' 返回 {len(results)} 条结果")
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"Spotify 搜索 HTTP 错误：{e}")
            raise SearchError(f"HTTP 错误：{e}", self.platform_name)
        except Exception as e:
            logger.error(f"Spotify 搜索异常：{e}")
            raise SearchError(f"搜索异常：{e}", self.platform_name)
    
    def _get_cover_url(self, album: Dict[str, Any], min_size: int = 300) -> str:
        """
        获取专辑封面 URL
        
        Args:
            album: 专辑数据字典
            min_size: 最小图片尺寸
            
        Returns:
            str: 封面图片 URL
        """
        if not album:
            return ""
        
        images = album.get("images", [])
        if not images:
            return ""
        
        # 选择合适尺寸的封面 (Spotify 返回多个尺寸)
        for image in sorted(images, key=lambda x: x.get("width", 0), reverse=True):
            if image.get("width", 0) >= min_size:
                return image.get("url", "")
        
        # 如果没有合适尺寸，返回最大的
        return images[0].get("url", "") if images else ""
    
    async def get_stream_url(self, track_id: str, quality: Quality = Quality.HIGH) -> str:
        """
        获取歌曲流媒体 URL
        
        注意：Spotify 的流媒体 URL 是加密的，需要通过 spotDL 获取实际下载链接。
        此方法返回一个特殊的 spotDL URL 格式，供 download 方法使用。
        
        Args:
            track_id: 歌曲 ID
            quality: 期望的音质质量
            
        Returns:
            str: 流媒体 URL (spotDL 格式)
            
        Raises:
            URLFetchError: 获取 URL 失败时抛出
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 验证 track_id 格式
            if not track_id or len(track_id) < 22:
                raise URLFetchError(f"无效的 Spotify track ID: {track_id}", self.platform_name)
            
            # 构建 Spotify track URL
            track_url = f"https://open.spotify.com/track/{track_id}"
            
            # 获取音质信息
            quality_info = self.QUALITY_MAP.get(quality, self.QUALITY_MAP[Quality.STANDARD])
            
            # 返回 spotDL 格式的 URL
            # spotDL 会处理实际的流媒体获取
            logger.debug(f"Spotify 流媒体 URL: {track_url} (quality: {quality_info['name']})")
            return track_url
            
        except Exception as e:
            logger.error(f"获取流媒体 URL 异常：{e}")
            raise URLFetchError(f"获取 URL 异常：{e}", self.platform_name)
    
    async def download(self, track_id: str, save_path: Path,
                      quality: Quality = Quality.HIGH) -> DownloadResult:
        """
        下载歌曲
        
        通过 spotDL 集成实现下载。spotDL 会处理:
        - 从 Spotify 获取元数据
        - 从 YouTube Music 获取音频
        - 嵌入元数据和封面
        
        Args:
            track_id: 歌曲 ID
            save_path: 保存路径（目录或完整文件路径）
            quality: 期望的音质质量
            
        Returns:
            DownloadResult: 下载结果
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 获取流媒体 URL
            stream_url = await self.get_stream_url(track_id, quality)
            
            # 获取元数据
            metadata = await self.get_metadata(track_id)
            
            # 确定保存路径
            if save_path.is_dir():
                # 是目录，构建文件名
                filename = f"{metadata.artist} - {metadata.title}.mp3"
                file_path = save_path / filename
            else:
                file_path = save_path
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用 spotDL 下载
            # 注意：spotDL 是一个同步库，需要在 executor 中运行
            downloaded_path = await self._download_with_spotdl(
                track_url=stream_url,
                output_path=file_path,
                quality=quality,
            )
            
            if not downloaded_path:
                return DownloadResult(
                    success=False,
                    error="spotDL 下载失败",
                    quality=quality,
                )
            
            logger.info(f"Spotify 下载完成：{downloaded_path}")
            
            return DownloadResult(
                success=True,
                file_path=downloaded_path,
                quality=quality,
                file_size=downloaded_path.stat().st_size if downloaded_path.exists() else None,
                metadata=metadata,
            )
            
        except Exception as e:
            logger.error(f"Spotify 下载异常：{e}")
            return DownloadResult(
                success=False,
                error=str(e),
                quality=quality,
            )
    
    async def _download_with_spotdl(
        self,
        track_url: str,
        output_path: Path,
        quality: Quality,
    ) -> Optional[Path]:
        """
        使用 spotDL 下载歌曲
        
        Args:
            track_url: Spotify track URL
            output_path: 输出文件路径
            quality: 音质质量
            
        Returns:
            Optional[Path]: 下载的文件路径，失败返回 None
        """
        try:
            # 尝试导入 spotDL
            import spotdl
            from spotdl.download.downloader import Downloader
            from spotdl.utils.options import get_download_options
            
            # 配置 spotDL
            quality_info = self.QUALITY_MAP.get(quality, self.QUALITY_MAP[Quality.STANDARD])
            bitrate = f"{quality_info['bitrate']}k"
            
            # 创建下载器配置
            downloader_settings = {
                "audio_providers": ["youtube-music"],
                "output": str(output_path.parent),
                "output_format": "mp3",
                "bitrate": bitrate,
                "save_file": False,
                "overwrite": "skip",
                "search_query": None,
                "cookie_file": None,
            }
            
            # 添加 Spotify 认证信息 (如果有)
            if self.config.client_id and self.config.client_secret:
                downloader_settings["client_id"] = self.config.client_id
                downloader_settings["client_secret"] = self.config.client_secret
            
            # 创建下载器
            downloader = Downloader(**downloader_settings)
            
            # 下载歌曲
            # spotDL 会返回下载的文件路径
            downloaded_files = downloader.download_song(track_url)
            
            if downloaded_files and len(downloaded_files) > 0:
                # spotDL 返回的是元组 (song, file_path)
                if isinstance(downloaded_files[0], tuple):
                    return Path(downloaded_files[0][1])
                else:
                    # 可能是直接返回的路径
                    return Path(downloaded_files[0])
            
            return None
            
        except ImportError:
            logger.warning("spotDL 未安装，尝试备用下载方法")
            return await self._download_with_httpx(track_url, output_path, quality)
            
        except Exception as e:
            logger.error(f"spotDL 下载失败：{e}")
            # 备用下载方法
            return await self._download_with_httpx(track_url, output_path, quality)
    
    async def _download_with_httpx(
        self,
        track_url: str,
        output_path: Path,
        quality: Quality,
    ) -> Optional[Path]:
        """
        备用下载方法：使用 httpx 直接下载
        
        注意：这个方法可能无法获取到有效的音频流，因为 Spotify 使用加密流。
        仅作为 spotDL 不可用时的备用方案。
        
        Args:
            track_url: Spotify track URL
            output_path: 输出文件路径
            quality: 音质质量
            
        Returns:
            Optional[Path]: 下载的文件路径，失败返回 None
        """
        logger.warning("使用备用下载方法，可能无法获取有效音频")
        
        # 这个方法实际上很难工作，因为 Spotify 流是加密的
        # 返回 None 表示失败
        return None
    
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
        if not self._initialized:
            await self.initialize()
        
        try:
            # 确保有有效的访问令牌
            if self.config.client_id and self.config.client_secret:
                await self._refresh_token()
            
            # 获取歌曲详情
            track_url = f"https://api.spotify.com/v1/tracks/{track_id}"
            
            response = await self._get_with_retry(track_url)
            track_data = response.json()
            
            # 解析艺术家信息
            artists = track_data.get("artists", [])
            artist_names = [a.get("name", "") for a in artists]
            
            # 解析专辑信息
            album = track_data.get("album", {})
            
            # 获取歌词 (Spotify API 不直接提供歌词，需要从其他来源获取)
            lyrics = await self._get_lyrics(track_id, track_data.get("name", ""), artist_names)
            
            # 获取封面
            cover_data = None
            cover_url = self._get_cover_url(album)
            if cover_url:
                try:
                    cover_response = await self._session.get(cover_url)
                    if cover_response.status_code == 200:
                        cover_data = cover_response.content
                except Exception as e:
                    logger.warning(f"获取封面失败：{e}")
            
            # 构建 TrackMetadata
            metadata = TrackMetadata(
                title=track_data.get("name", ""),
                artist=", ".join(artist_names),
                album=album.get("name") if album else None,
                track_number=track_data.get("track_number"),
                year=None,  # 需要从专辑信息获取
                genre=None,  # Spotify 不直接提供流派信息
                cover_data=cover_data,
                lyrics=lyrics,
                extra={
                    "album_id": album.get("id") if album else None,
                    "artists": artists,
                    "popularity": track_data.get("popularity", 0),
                    "isrc": track_data.get("external_ids", {}).get("isrc"),
                    "external_urls": track_data.get("external_urls", {}),
                    "preview_url": track_data.get("preview_url"),
                },
            )
            
            return metadata
            
        except httpx.HTTPError as e:
            logger.error(f"获取元数据 HTTP 错误：{e}")
            raise MetadataError(f"HTTP 错误：{e}", self.platform_name)
        except Exception as e:
            logger.error(f"获取元数据异常：{e}")
            raise MetadataError(f"获取元数据异常：{e}", self.platform_name)
    
    async def _get_lyrics(self, track_id: str, title: str, artists: List[str]) -> Optional[str]:
        """
        获取歌词
        
        Spotify API 不直接提供歌词，需要从其他来源获取。
        这里使用简单的实现，实际可以集成歌词 API。
        
        Args:
            track_id: Spotify track ID
            title: 歌曲标题
            artists: 艺术家列表
            
        Returns:
            Optional[str]: 歌词文本，获取失败返回 None
        """
        # 简单实现：返回 None
        # 实际可以集成 Genius、LRCLIB 等歌词 API
        logger.debug(f"歌词获取：{title} - {', '.join(artists)} (未实现)")
        return None
    
    async def get_playlist(self, playlist_id: str) -> List[TrackInfo]:
        """
        获取歌单歌曲列表
        
        Args:
            playlist_id: 歌单 ID
            
        Returns:
            List[TrackInfo]: 歌单中的歌曲列表
            
        Raises:
            SearchError: 获取失败时抛出
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 确保有有效的访问令牌
            if self.config.client_id and self.config.client_secret:
                await self._refresh_token()
            
            # 获取歌单详情
            playlist_url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
            params = {"fields": "tracks(total,items(track(id,name,artists,album,duration_ms,is_playable,external_ids)))"}
            
            response = await self._get_with_retry(playlist_url)
            playlist_data = response.json()
            
            tracks_data = playlist_data.get("tracks", {}).get("items", [])
            
            results = []
            for item in tracks_data:
                track_data = item.get("track", {})
                
                # 跳过无效曲目
                if not track_data or not track_data.get("id"):
                    continue
                
                # 跳过不可播放的曲目
                if not track_data.get("is_playable", True):
                    continue
                
                # 解析艺术家信息
                artists = track_data.get("artists", [])
                artist_names = [a.get("name", "") for a in artists]
                
                # 解析专辑信息
                album = track_data.get("album", {})
                
                # 构建 TrackInfo
                track = TrackInfo(
                    id=track_data.get("id", ""),
                    title=track_data.get("name", ""),
                    artist=", ".join(artist_names),
                    album=album.get("name") if album else None,
                    duration=track_data.get("duration_ms", 0) // 1000,
                    cover_url=self._get_cover_url(album),
                    quality_available=[Quality.STANDARD, Quality.HIGH],
                    extra={
                        "album_id": album.get("id") if album else None,
                        "artists": artists,
                        "isrc": track_data.get("external_ids", {}).get("isrc"),
                    },
                )
                results.append(track)
            
            logger.info(f"Spotify 歌单 '{playlist_id}' 包含 {len(results)} 首歌曲")
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"获取歌单 HTTP 错误：{e}")
            raise SearchError(f"HTTP 错误：{e}", self.platform_name)
        except Exception as e:
            logger.error(f"获取歌单异常：{e}")
            raise SearchError(f"获取歌单异常：{e}", self.platform_name)
    
    async def get_album(self, album_id: str) -> List[TrackInfo]:
        """
        获取专辑歌曲列表
        
        Args:
            album_id: 专辑 ID
            
        Returns:
            List[TrackInfo]: 专辑中的歌曲列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 确保有有效的访问令牌
            if self.config.client_id and self.config.client_secret:
                await self._refresh_token()
            
            # 获取专辑详情
            album_url = f"https://api.spotify.com/v1/albums/{album_id}"
            
            response = await self._get_with_retry(album_url)
            album_data = response.json()
            
            tracks_data = album_data.get("tracks", {}).get("items", [])
            album_name = album_data.get("name", "")
            
            results = []
            for track_data in tracks_data:
                # 解析艺术家信息
                artists = track_data.get("artists", [])
                artist_names = [a.get("name", "") for a in artists]
                
                # 构建 TrackInfo
                track = TrackInfo(
                    id=track_data.get("id", ""),
                    title=track_data.get("name", ""),
                    artist=", ".join(artist_names),
                    album=album_name,
                    duration=track_data.get("duration_ms", 0) // 1000,
                    cover_url=self._get_cover_url(album_data),
                    quality_available=[Quality.STANDARD, Quality.HIGH],
                    extra={
                        "album_id": album_id,
                        "artists": artists,
                        "track_number": track_data.get("track_number"),
                    },
                )
                results.append(track)
            
            logger.info(f"Spotify 专辑 '{album_id}' 包含 {len(results)} 首歌曲")
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"获取专辑 HTTP 错误：{e}")
            raise SearchError(f"HTTP 错误：{e}", self.platform_name)
        except Exception as e:
            logger.error(f"获取专辑异常：{e}")
            raise SearchError(f"获取专辑异常：{e}", self.platform_name)
    
    async def get_artist_top_tracks(self, artist_id: str) -> List[TrackInfo]:
        """
        获取艺术家热门歌曲
        
        Args:
            artist_id: 艺术家 ID
            
        Returns:
            List[TrackInfo]: 热门歌曲列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 确保有有效的访问令牌
            if self.config.client_id and self.config.client_secret:
                await self._refresh_token()
            
            # 获取艺术家热门歌曲
            artist_url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks"
            params = {"market": "from_token" if self._access_token else "US"}
            
            response = await self._get_with_retry(artist_url)
            data = response.json()
            
            tracks_data = data.get("tracks", [])
            
            results = []
            for track_data in tracks_data:
                # 解析艺术家信息
                artists = track_data.get("artists", [])
                artist_names = [a.get("name", "") for a in artists]
                
                # 解析专辑信息
                album = track_data.get("album", {})
                
                # 构建 TrackInfo
                track = TrackInfo(
                    id=track_data.get("id", ""),
                    title=track_data.get("name", ""),
                    artist=", ".join(artist_names),
                    album=album.get("name") if album else None,
                    duration=track_data.get("duration_ms", 0) // 1000,
                    cover_url=self._get_cover_url(album),
                    quality_available=[Quality.STANDARD, Quality.HIGH],
                    extra={
                        "album_id": album.get("id") if album else None,
                        "artists": artists,
                        "popularity": track_data.get("popularity", 0),
                    },
                )
                results.append(track)
            
            logger.info(f"Spotify 艺术家 '{artist_id}' 热门歌曲：{len(results)} 首")
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"获取艺术家歌曲 HTTP 错误：{e}")
            raise SearchError(f"HTTP 错误：{e}", self.platform_name)
        except Exception as e:
            logger.error(f"获取艺术家歌曲异常：{e}")
            raise SearchError(f"获取艺术家歌曲异常：{e}", self.platform_name)
    
    def parse_spotify_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        解析 Spotify URL
        
        支持的 URL 格式:
        - https://open.spotify.com/track/{id}
        - https://open.spotify.com/album/{id}
        - https://open.spotify.com/playlist/{id}
        - https://open.spotify.com/artist/{id}
        - spotify:track:{id}
        - spotify:album:{id}
        - spotify:playlist:{id}
        - spotify:artist:{id}
        
        Args:
            url: Spotify URL
            
        Returns:
            Optional[Dict[str, str]]: 解析结果，包含 type 和 id
        """
        # 处理 spotify: 格式
        if url.startswith("spotify:"):
            parts = url.split(":")
            if len(parts) >= 3:
                return {
                    "type": parts[1],
                    "id": parts[2],
                }
        
        # 处理 HTTP URL 格式
        track_match = self.TRACK_PATTERN.search(url)
        if track_match:
            return {"type": "track", "id": track_match.group(1)}
        
        album_match = self.ALBUM_PATTERN.search(url)
        if album_match:
            return {"type": "album", "id": album_match.group(1)}
        
        playlist_match = self.PLAYLIST_PATTERN.search(url)
        if playlist_match:
            return {"type": "playlist", "id": playlist_match.group(1)}
        
        artist_match = self.ARTIST_PATTERN.search(url)
        if artist_match:
            return {"type": "artist", "id": artist_match.group(1)}
        
        return None
    
    async def close(self):
        """关闭插件，释放资源"""
        if self._session:
            await self._session.close()
            self._session = None
        self._spotipy_client = None
        self._access_token = None
        self._initialized = False
        logger.debug(f"{self.platform_display_name} 插件已关闭")
