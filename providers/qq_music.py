"""
QQ 音乐插件

实现 QQ 音乐平台的搜索、下载、元数据获取功能。
支持无损音质 (FLAC) 下载。
"""

import asyncio
import hashlib
import time
import random
import string
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


class QQMusicConfig(PlatformConfig):
    """QQ 音乐配置"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.uin: Optional[str] = kwargs.get("uin")  # QQ 号
        self.qqmusic_key: Optional[str] = kwargs.get("qqmusic_key")
        
    def validate(self) -> bool:
        """验证配置"""
        # QQ 音乐部分接口需要登录，部分可以匿名访问
        return True


class QQMusicProvider(BaseProvider):
    """
    QQ 音乐平台插件
    
    功能:
    - 歌曲搜索
    - 无损音质下载 (FLAC)
    - 元数据获取
    - 歌单获取
    """
    
    platform_name = "qq_music"
    platform_display_name = "QQ 音乐"
    config_class = QQMusicConfig
    
    # API 端点
    BASE_URL = "https://u.y.qq.com/cgi-bin/musicu.fcg"
    SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    LYRIC_URL = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
    
    # 音质对应的 file_type
    QUALITY_MAP = {
        Quality.STANDARD: {"type": "M500", "format": "mp3", "bitrate": 128},
        Quality.HIGH: {"type": "M800", "format": "mp3", "bitrate": 320},
        Quality.LOSSLESS: {"type": "F000", "format": "flac", "bitrate": None},
        Quality.HI_RES: {"type": "RS01", "format": "flac", "bitrate": None},
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._session: Optional[httpx.AsyncClient] = None
        self._uin = self.config.uin or self._generate_uin()
    
    def _generate_uin(self) -> str:
        """生成随机 UIN"""
        return str(random.randint(1000000000, 9999999999))
    
    def _get_common_params(self) -> Dict[str, str]:
        """获取公共参数"""
        return {
            "format": "json",
            "inCharset": "utf8",
            "outCharset": "utf-8",
            "notice": "0",
            "platform": "yqq.json",
            "needNewCode": "1",
        }
    
    def _generate_caller(self) -> str:
        """生成 caller 参数"""
        return "androidQQMusic" + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10)
        )
    
    def _generate_guid(self) -> str:
        """生成 GUID"""
        return "".join(
            random.choices(string.ascii_lowercase + string.digits, k=32)
        )
    
    async def initialize(self) -> bool:
        """初始化 HTTP 会话"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://y.qq.com/",
            }
            
            if self.config.cookie:
                headers["Cookie"] = self.config.cookie
            
            self._session = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True,
            )
            
            self._initialized = True
            logger.info(f"{self.platform_display_name} 插件初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"{self.platform_display_name} 初始化失败：{e}")
            return False
    
    async def search(self, query: str, limit: int = 20) -> List[TrackInfo]:
        """
        搜索歌曲
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量
            
        Returns:
            List[TrackInfo]: 搜索结果
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            params = {
                "w": query,
                "format": "json",
                "inCharset": "utf8",
                "outCharset": "utf-8",
                "n": limit,
                "p": 1,
                "remoteplace": "txt.mqq.all",
                "t": "0",
                "aggr": "1",
                "cr": "1",
                "catZhida": "1",
                "lossless": "0",
                "flag_qc": "0",
            }
            
            response = await self._session.get(
                self.SEARCH_URL,
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise SearchError(f"搜索失败：{data.get('msg', '未知错误')}", self.platform_name)
            
            songs = data.get("data", {}).get("song", {}).get("list", [])
            
            results = []
            for song in songs[:limit]:
                # 解析可用音质
                quality_available = [Quality.STANDARD]
                if song.get("file", {}).get("size_320mp3", 0) > 0:
                    quality_available.append(Quality.HIGH)
                if song.get("file", {}).get("size_flac", 0) > 0:
                    quality_available.append(Quality.LOSSLESS)
                if song.get("file", {}).get("size_hires", 0) > 0:
                    quality_available.append(Quality.HI_RES)
                
                track = TrackInfo(
                    id=song.get("songmid", ""),
                    title=song.get("songname", ""),
                    artist=", ".join(
                        s.get("name", "") for s in song.get("singer", [])
                    ),
                    album=song.get("albumname"),
                    duration=song.get("interval", 0),
                    cover_url=self._get_cover_url(song.get("albummid", "")),
                    quality_available=quality_available,
                    extra={
                        "albummid": song.get("albummid", ""),
                        "singer": song.get("singer", []),
                        "file": song.get("file", {}),
                    },
                )
                results.append(track)
            
            logger.info(f"搜索 '{query}' 返回 {len(results)} 条结果")
            return results
            
        except httpx.HTTPError as e:
            raise SearchError(f"HTTP 错误：{e}", self.platform_name)
        except Exception as e:
            raise SearchError(f"搜索异常：{e}", self.platform_name)
    
    def _get_cover_url(self, album_mid: str, size: int = 300) -> str:
        """获取专辑封面 URL"""
        if not album_mid:
            return ""
        return f"https://y.gtimg.cn/music/photo_new/T002R{size}x{size}M000{album_mid}.jpg"
    
    async def get_stream_url(self, track_id: str, quality: Quality = Quality.LOSSLESS) -> str:
        """
        获取歌曲流媒体 URL
        
        Args:
            track_id: 歌曲 songmid
            quality: 音质质量
            
        Returns:
            str: 流媒体 URL
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            quality_info = self.QUALITY_MAP.get(quality, self.QUALITY_MAP[Quality.STANDARD])
            
            # 构建请求数据
            req_data = {
                "req_0": {
                    "module": "vkey.GetVkeyServer",
                    "method": "CgiGetVkey",
                    "param": {
                        "filename": [f"{quality_info['type']}{track_id}.{quality_info['format']}"],
                        "songmid": [track_id],
                        "songtype": [1],
                        "uin": self._uin,
                        "loginflag": 1,
                        "platform": "20",
                    },
                },
            }
            
            payload = {
                "comm": {
                    "cv": 4747474,
                    "ct": 24,
                    "format": "json",
                    "inCharset": "utf-8",
                    "outCharset": "utf-8",
                    "notice": 0,
                    "platform": "yqq.json",
                    "needNewCode": 1,
                    "uin": self._uin,
                },
                **req_data,
            }
            
            response = await self._session.post(
                self.BASE_URL,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            # 解析响应
            vkey_data = data.get("req_0", {}).get("data", {})
            if not vkey_data:
                raise URLFetchError("无法获取播放密钥", self.platform_name)
            
            midurlinfo = vkey_data.get("midurlinfo", [])
            if not midurlinfo or not midurlinfo[0].get("purl"):
                raise URLFetchError("未找到可用音源", self.platform_name)
            
            purl = midurlinfo[0]["purl"]
            if not purl:
                raise URLFetchError("音源 URL 为空", self.platform_name)
            
            # 构建完整 URL
            sip = vkey_data.get("sip", [])
            if not sip:
                raise URLFetchError("未找到服务器地址", self.platform_name)
            
            # 选择第一个服务器（通常是最优的）
            base_url = sip[0]
            if base_url.startswith("http://"):
                base_url = base_url.replace("http://", "https://")
            
            stream_url = f"{base_url}{purl}"
            logger.debug(f"获取到流媒体 URL: {stream_url[:50]}...")
            return stream_url
            
        except httpx.HTTPError as e:
            raise URLFetchError(f"HTTP 错误：{e}", self.platform_name)
        except Exception as e:
            raise URLFetchError(f"获取 URL 异常：{e}", self.platform_name)
    
    async def download(self, track_id: str, save_path: Path, 
                      quality: Quality = Quality.LOSSLESS) -> DownloadResult:
        """
        下载歌曲
        
        Args:
            track_id: 歌曲 songmid
            save_path: 保存路径
            quality: 音质质量
            
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
                filename = f"{metadata.artist} - {metadata.title}"
                quality_info = self.QUALITY_MAP.get(quality, self.QUALITY_MAP[Quality.STANDARD])
                filename += f".{quality_info['format']}"
                file_path = save_path / filename
            else:
                file_path = save_path
            
            # 下载文件
            async with self._session.stream("GET", stream_url) as response:
                response.raise_for_status()
                
                file_size = int(response.headers.get("content-length", 0))
                
                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
            
            logger.info(f"下载完成：{file_path}")
            
            return DownloadResult(
                success=True,
                file_path=file_path,
                quality=quality,
                file_size=file_path.stat().st_size if file_path.exists() else None,
                metadata=metadata,
            )
            
        except httpx.HTTPError as e:
            logger.error(f"下载 HTTP 错误：{e}")
            return DownloadResult(
                success=False,
                error=f"HTTP 错误：{e}",
                quality=quality,
            )
        except Exception as e:
            logger.error(f"下载异常：{e}")
            return DownloadResult(
                success=False,
                error=str(e),
                quality=quality,
            )
    
    async def get_metadata(self, track_id: str) -> TrackMetadata:
        """
        获取歌曲元数据
        
        Args:
            track_id: 歌曲 songmid
            
        Returns:
            TrackMetadata: 元数据
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 使用搜索接口获取详细信息
            params = {
                "songmid": track_id,
                "format": "json",
                "inCharset": "utf8",
                "outCharset": "utf-8",
                "nobase64": "1",
            }
            
            response = await self._session.get(
                self.LYRIC_URL,
                params=params,
                headers={"Referer": "https://y.qq.com/"},
            )
            response.raise_for_status()
            data = response.json()
            
            # 解析元数据
            lyric = data.get("lyric", "")
            trans = data.get("trans", "")
            
            # 从 extra 中获取更多信息（需要在搜索时缓存）
            # 这里简化处理，实际应该从缓存或额外 API 获取
            metadata = TrackMetadata(
                title="",  # 需要从额外 API 获取
                artist="",
                lyrics=lyric if lyric else None,
            )
            
            return metadata
            
        except Exception as e:
            logger.warning(f"获取元数据失败：{e}")
            # 返回空元数据而不是抛出异常
            return TrackMetadata(title="", artist="")
    
    async def get_playlist(self, playlist_id: str) -> List[TrackInfo]:
        """
        获取歌单歌曲列表
        
        Args:
            playlist_id: 歌单 ID
            
        Returns:
            List[TrackInfo]: 歌曲列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建歌单请求
            payload = {
                "comm": {
                    "cv": 4747474,
                    "ct": 24,
                    "format": "json",
                    "inCharset": "utf-8",
                    "outCharset": "utf-8",
                    "notice": 0,
                    "platform": "yqq.json",
                    "needNewCode": 1,
                },
                "playlist": {
                    "method": "get_playlist_detail",
                    "module": "music.playlist.PlayListHub",
                    "param": {
                        "dissid": playlist_id,
                        "userinfo": 1,
                        "song_begin": 0,
                        "song_num": 100,
                    },
                },
            }
            
            response = await self._session.post(
                self.BASE_URL,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            playlist_data = data.get("playlist", {}).get("data", {})
            songs = playlist_data.get("song", [])
            
            results = []
            for song in songs:
                track = TrackInfo(
                    id=song.get("songmid", ""),
                    title=song.get("songname", ""),
                    artist=", ".join(
                        s.get("name", "") for s in song.get("singer", [])
                    ),
                    album=song.get("albumname"),
                    duration=song.get("interval", 0),
                    extra={"albummid": song.get("albummid", "")},
                )
                results.append(track)
            
            logger.info(f"获取歌单 {playlist_id} 共 {len(results)} 首歌曲")
            return results
            
        except Exception as e:
            logger.error(f"获取歌单失败：{e}")
            return []
    
    async def close(self):
        """关闭插件"""
        await super().close()


# 便捷函数
async def create_provider(config: Optional[Dict[str, Any]] = None) -> QQMusicProvider:
    """创建 QQ 音乐插件实例"""
    provider = QQMusicProvider(config)
    await provider.initialize()
    return provider
