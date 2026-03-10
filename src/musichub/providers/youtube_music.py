"""
YouTube Music 音源插件

支持功能:
- 搜索歌曲/专辑/播放列表/艺术家
- 获取音频流 URL (通过 yt-dlp 集成)
- 下载歌曲（支持最高音质）
- 获取元数据（封面、歌词、专辑信息）

音质等级:
- STANDARD (128kbps)
- HIGH (256kbps AAC)
- BEST (最高可用)

配置要求:
- 无需账号（公开内容）
- 可选：YouTube Premium Cookie（用于更高音质）
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp
from musichub.plugins.base import SourcePlugin
from musichub.core.types import TrackInfo

logger = logging.getLogger(__name__)


class AudioQuality(Enum):
    """音质等级"""
    STANDARD = "standard"  # 128kbps
    HIGH = "high"          # 256kbps AAC
    BEST = "best"          # 最高可用


@dataclass
class YouTubeMusicConfig:
    """YouTube Music 配置"""
    audio_quality: AudioQuality = AudioQuality.HIGH
    country: str = "US"
    language: str = "en"
    timeout: int = 30
    max_retries: int = 3
    cookies_file: Optional[str] = None  # YouTube Premium cookies
    extract_lyrics: bool = True
    extract_cover: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "YouTubeMusicConfig":
        """从字典创建配置"""
        quality_str = data.get("audio_quality", "high")
        return cls(
            audio_quality=AudioQuality(quality_str) if isinstance(quality_str, str) else quality_str,
            country=data.get("country", "US"),
            language=data.get("language", "en"),
            timeout=data.get("timeout", 30),
            max_retries=data.get("max_retries", 3),
            cookies_file=data.get("cookies_file"),
            extract_lyrics=data.get("extract_lyrics", True),
            extract_cover=data.get("extract_cover", True)
        )


@dataclass
class YouTubeMusicTrackInfo(TrackInfo):
    """YouTube Music 音轨信息（扩展）"""
    video_id: Optional[str] = None
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    audio_quality: AudioQuality = AudioQuality.STANDARD
    bitrate: Optional[int] = None
    codec: Optional[str] = None
    format_id: Optional[str] = None
    album_artist: Optional[str] = None
    disc_number: Optional[int] = None
    like_count: Optional[int] = None
    view_count: Optional[int] = None


class YouTubeMusicError(Exception):
    """YouTube Music 插件异常"""
    pass


class NotFoundError(YouTubeMusicError):
    """资源未找到"""
    pass


class ExtractionError(YouTubeMusicError):
    """提取错误"""
    pass


class YouTubeMusicProvider(SourcePlugin):
    """
    YouTube Music 音源插件
    
    实现 YouTube Music 集成，支持搜索、流媒体 URL 获取和下载
    使用 yt-dlp 作为底层提取引擎
    """
    
    name = "youtube_music"
    version = "1.0.0"
    description = "YouTube Music 音源插件 - 支持多音质和元数据提取"
    
    YOUTUBE_MUSIC_URL = "https://music.youtube.com"
    YOUTUBE_URL = "https://www.youtube.com"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.config: YouTubeMusicConfig = YouTubeMusicConfig.from_dict(config or {})
        self._initialized = False
        self._ydl_opts: Dict[str, Any] = {}
    
    def _build_ydl_opts(self) -> Dict[str, Any]:
        """构建 yt-dlp 选项"""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": self.config.timeout,
            "retries": self.config.max_retries,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "web"],
                }
            },
        }
        
        # 添加 cookies 支持（用于 Premium 内容）
        if self.config.cookies_file:
            cookies_path = Path(self.config.cookies_file)
            if cookies_path.exists():
                opts["cookiefile"] = str(cookies_path)
        
        return opts
    
    async def initialize(self) -> bool:
        """初始化插件"""
        try:
            # 验证 yt-dlp 可用
            with yt_dlp.YoutubeDL(self._build_ydl_opts()) as ydl:
                # 测试提取器是否正常工作
                ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
            
            self._ydl_opts = self._build_ydl_opts()
            self._initialized = True
            logger.info(f"YouTube Music 插件初始化成功 (音质：{self.config.audio_quality.value})")
            return True
            
        except Exception as e:
            logger.error(f"YouTube Music 插件初始化失败：{e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭插件，清理资源"""
        self._initialized = False
        logger.info("YouTube Music 插件已关闭")
    
    def validate_config(self) -> bool:
        """验证配置"""
        if self.config.cookies_file:
            cookies_path = Path(self.config.cookies_file)
            if not cookies_path.exists():
                logger.warning(f"Cookie 文件不存在：{self.config.cookies_file}")
        return True
    
    def _get_quality_format(self) -> str:
        """根据音质配置获取 yt-dlp 格式字符串"""
        if self.config.audio_quality == AudioQuality.BEST:
            # 最佳音质：优先 opus，然后 m4a
            return "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio"
        elif self.config.audio_quality == AudioQuality.HIGH:
            # 高音质：256kbps AAC
            return "m4a/bestaudio[ext=m4a]/bestaudio"
        else:
            # 标准音质：128kbps
            return "bestaudio[abr<=128]/bestaudio"
    
    async def search(
        self,
        query: str,
        limit: int = 20
    ) -> List[YouTubeMusicTrackInfo]:
        """
        搜索音乐
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
        
        Returns:
            YouTubeMusicTrackInfo 列表
        """
        if not self._initialized:
            raise YouTubeMusicError("插件未初始化")
        
        try:
            search_query = f"ytsearch{limit}:{query}"
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._search_sync,
                search_query
            )
            
            tracks = []
            for entry in result.get("entries", []):
                if entry:
                    track_info = self._parse_track(entry)
                    if track_info:
                        tracks.append(track_info)
            
            return tracks[:limit]
            
        except Exception as e:
            logger.error(f"搜索失败：{e}")
            raise YouTubeMusicError(f"搜索失败：{e}")
    
    def _search_sync(self, search_query: str) -> Dict[str, Any]:
        """同步搜索（在 executor 中运行）"""
        opts = {
            **self._ydl_opts,
            "extract_flat": "in_playlist",
            "playlistend": int(re.search(r'\d+', search_query).group()) if re.search(r'\d+', search_query) else 20,
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(search_query, download=False)
    
    def _parse_track(self, track_data: Dict[str, Any]) -> Optional[YouTubeMusicTrackInfo]:
        """解析音轨数据"""
        try:
            # 提取艺术家信息
            artist = track_data.get("artist") or track_data.get("channel", "Unknown Artist")
            channel_id = track_data.get("channel_id") or track_data.get("uploader_id")
            channel_name = track_data.get("channel") or track_data.get("uploader")
            
            # 提取时长（秒）
            duration = track_data.get("duration")
            if duration is None:
                duration = track_data.get("duration_string")
                if duration:
                    # 解析时长字符串 (e.g., "3:45")
                    parts = duration.split(":")
                    if len(parts) == 2:
                        duration = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    else:
                        duration = 0
                else:
                    duration = 0
            
            # 提取封面
            cover_url = None
            if self.config.extract_cover:
                thumbnail = track_data.get("thumbnail")
                if thumbnail:
                    cover_url = thumbnail
                elif track_data.get("thumbnails"):
                    # 选择最高分辨率的封面
                    thumbnails = sorted(
                        track_data.get("thumbnails", []),
                        key=lambda x: x.get("width", 0) * x.get("height", 0),
                        reverse=True
                    )
                    if thumbnails:
                        cover_url = thumbnails[0].get("url")
            
            # 提取专辑信息
            album = track_data.get("album")
            album_artist = track_data.get("album_artist")
            
            # 创建 TrackInfo
            return YouTubeMusicTrackInfo(
                id=track_data.get("id", ""),
                video_id=track_data.get("id", ""),
                title=track_data.get("title", "Unknown"),
                artist=artist,
                channel_id=channel_id,
                channel_name=channel_name,
                album=album,
                album_artist=album_artist,
                duration=duration,
                source=self.name,
                cover_url=cover_url,
                track_number=track_data.get("track_number"),
                disc_number=track_data.get("disc_number"),
                year=self._parse_year(track_data.get("release_date", "")),
                genre=track_data.get("genre") or track_data.get("categories", [None])[0],
                like_count=track_data.get("like_count"),
                view_count=track_data.get("view_count"),
            )
            
        except Exception as e:
            logger.error(f"解析音轨数据失败：{e}")
            return None
    
    def _parse_year(self, date_str: str) -> Optional[int]:
        """从日期字符串解析年份"""
        if not date_str:
            return None
        try:
            # 格式：YYYYMMDD
            if len(date_str) >= 4:
                return int(date_str[:4])
        except (ValueError, IndexError):
            return None
        return None
    
    async def get_track_info(self, track_id: str) -> Optional[YouTubeMusicTrackInfo]:
        """
        获取音轨详细信息
        
        Args:
            track_id: 音轨 ID (YouTube video ID)
        
        Returns:
            YouTubeMusicTrackInfo
        """
        if not self._initialized:
            raise YouTubeMusicError("插件未初始化")
        
        try:
            url = f"{self.YOUTUBE_URL}/watch?v={track_id}"
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._extract_info_sync,
                url
            )
            
            return self._parse_track(result)
            
        except Exception as e:
            logger.error(f"获取音轨信息失败：{e}")
            return None
    
    def _extract_info_sync(self, url: str) -> Dict[str, Any]:
        """同步提取信息（在 executor 中运行）"""
        with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    
    async def get_stream_url(
        self,
        track_id: str,
        quality: Optional[AudioQuality] = None
    ) -> Optional[str]:
        """
        获取流媒体 URL
        
        Args:
            track_id: 音轨 ID (YouTube video ID)
            quality: 音质等级
        
        Returns:
            流媒体 URL
        """
        if not self._initialized:
            raise YouTubeMusicError("插件未初始化")
        
        quality = quality or self.config.audio_quality
        
        try:
            url = f"{self.YOUTUBE_URL}/watch?v={track_id}"
            
            loop = asyncio.get_event_loop()
            stream_url = await loop.run_in_executor(
                None,
                self._extract_stream_url_sync,
                url,
                quality
            )
            
            return stream_url
            
        except Exception as e:
            logger.error(f"获取流媒体 URL 失败：{e}")
            return None
    
    def _extract_stream_url_sync(
        self,
        url: str,
        quality: AudioQuality
    ) -> Optional[str]:
        """同步提取流媒体 URL（在 executor 中运行）"""
        # 临时覆盖音质配置
        original_quality = self.config.audio_quality
        self.config.audio_quality = quality
        
        try:
            opts = {
                **self._ydl_opts,
                "format": self._get_quality_format(),
                "extract_audio": True,
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # 获取最佳音频格式
                formats = info.get("formats", [])
                audio_formats = [
                    f for f in formats
                    if f.get("acodec") != "none" and f.get("vcodec") == "none"
                ]
                
                if not audio_formats:
                    # 如果没有纯音频，使用最佳格式
                    audio_formats = formats
                
                if audio_formats:
                    # 选择最佳音质
                    best_format = audio_formats[-1]
                    return best_format.get("url")
                
                return None
                
        finally:
            self.config.audio_quality = original_quality
    
    async def get_download_url(
        self,
        track_id: str,
        quality: Optional[AudioQuality] = None
    ) -> Optional[str]:
        """
        获取下载 URL
        
        Args:
            track_id: 音轨 ID
            quality: 音质等级
        
        Returns:
            下载 URL
        """
        return await self.get_stream_url(track_id, quality)
    
    async def get_lyrics(self, track_id: str) -> Optional[str]:
        """
        获取歌词
        
        Args:
            track_id: 音轨 ID
        
        Returns:
            歌词文本
        """
        if not self._initialized:
            raise YouTubeMusicError("插件未初始化")
        
        if not self.config.extract_lyrics:
            return None
        
        try:
            url = f"{self.YOUTUBE_URL}/watch?v={track_id}"
            
            loop = asyncio.get_event_loop()
            lyrics = await loop.run_in_executor(
                None,
                self._extract_lyrics_sync,
                url
            )
            
            return lyrics
            
        except Exception as e:
            logger.error(f"获取歌词失败：{e}")
            return None
    
    def _extract_lyrics_sync(self, url: str) -> Optional[str]:
        """同步提取歌词（在 executor 中运行）"""
        opts = {
            **self._ydl_opts,
            "extract_flat": False,
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("lyrics")
    
    async def search_albums(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索专辑
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
        
        Returns:
            专辑信息列表
        """
        if not self._initialized:
            raise YouTubeMusicError("插件未初始化")
        
        try:
            search_query = f"ytsearch{limit * 2}:{query} album"
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._search_sync,
                search_query
            )
            
            albums = {}
            for entry in result.get("entries", []):
                if entry and entry.get("album"):
                    album_name = entry.get("album")
                    if album_name not in albums:
                        albums[album_name] = {
                            "name": album_name,
                            "artist": entry.get("artist"),
                            "year": self._parse_year(entry.get("release_date", "")),
                            "tracks": [],
                            "cover_url": entry.get("thumbnail"),
                        }
                    
                    albums[album_name]["tracks"].append({
                        "id": entry.get("id"),
                        "title": entry.get("title"),
                        "track_number": entry.get("track_number"),
                    })
                    
                    if len(albums) >= limit:
                        break
            
            return list(albums.values())[:limit]
            
        except Exception as e:
            logger.error(f"搜索专辑失败：{e}")
            return []
    
    async def search_artists(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索艺术家
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
        
        Returns:
            艺术家信息列表
        """
        if not self._initialized:
            raise YouTubeMusicError("插件未初始化")
        
        try:
            search_query = f"ytsearch{limit}:{query} artist"
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._search_sync,
                search_query
            )
            
            artists = {}
            for entry in result.get("entries", []):
                if entry:
                    channel_id = entry.get("channel_id") or entry.get("uploader_id")
                    if channel_id and channel_id not in artists:
                        artists[channel_id] = {
                            "id": channel_id,
                            "name": entry.get("channel") or entry.get("uploader"),
                            "cover_url": entry.get("thumbnail"),
                        }
                    
                    if len(artists) >= limit:
                        break
            
            return list(artists.values())[:limit]
            
        except Exception as e:
            logger.error(f"搜索艺术家失败：{e}")
            return []
    
    async def search_playlists(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索播放列表
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
        
        Returns:
            播放列表信息列表
        """
        if not self._initialized:
            raise YouTubeMusicError("插件未初始化")
        
        try:
            search_query = f"ytsearch{limit}:{query} playlist"
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._search_sync,
                search_query
            )
            
            playlists = []
            for entry in result.get("entries", []):
                if entry and entry.get("_type") == "playlist":
                    playlists.append({
                        "id": entry.get("id"),
                        "title": entry.get("title"),
                        "channel": entry.get("channel") or entry.get("uploader"),
                        "track_count": entry.get("playlist_count"),
                        "cover_url": entry.get("thumbnail"),
                    })
                    
                    if len(playlists) >= limit:
                        break
            
            return playlists
            
        except Exception as e:
            logger.error(f"搜索播放列表失败：{e}")
            return []
    
    async def get_playlist_tracks(
        self,
        playlist_id: str
    ) -> List[YouTubeMusicTrackInfo]:
        """
        获取播放列表的所有音轨
        
        Args:
            playlist_id: 播放列表 ID
        
        Returns:
            音轨列表
        """
        if not self._initialized:
            raise YouTubeMusicError("插件未初始化")
        
        try:
            url = f"{self.YOUTUBE_URL}/playlist?list={playlist_id}"
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._extract_playlist_sync,
                url
            )
            
            tracks = []
            for entry in result.get("entries", []):
                if entry:
                    track_info = self._parse_track(entry)
                    if track_info:
                        tracks.append(track_info)
            
            return tracks
            
        except Exception as e:
            logger.error(f"获取播放列表音轨失败：{e}")
            return []
    
    def _extract_playlist_sync(self, url: str) -> Dict[str, Any]:
        """同步提取播放列表（在 executor 中运行）"""
        opts = {
            **self._ydl_opts,
            "extract_flat": "in_playlist",
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    
    def get_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        info = super().get_info()
        info["audio_quality"] = self.config.audio_quality.value
        info["supports_premium"] = bool(self.config.cookies_file)
        return info


def create_provider(config: Optional[Dict[str, Any]] = None) -> YouTubeMusicProvider:
    """
    创建 YouTube Music 插件实例
    
    Args:
        config: 配置字典
    
    Returns:
        YouTubeMusicProvider 实例
    """
    return YouTubeMusicProvider(config)
