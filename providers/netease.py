"""
网易云音乐插件

实现网易云音乐平台的搜索、下载、元数据获取功能。
支持无损音质下载。
"""

import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from .base import (
    BaseProvider, PlatformConfig, Quality,
    TrackInfo, TrackMetadata, DownloadResult,
    SearchError, URLFetchError, DownloadError, 
    MetadataError, AuthenticationError
)

logger = logging.getLogger(__name__)


class NetEaseConfig(PlatformConfig):
    """网易云音乐配置"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cookie: Optional[str] = kwargs.get("cookie")
        self.device_id: Optional[str] = kwargs.get("device_id")
        
    def validate(self) -> bool:
        """验证配置"""
        # 网易云部分接口需要登录
        return True


class NetEaseProvider(BaseProvider):
    """
    网易云音乐平台插件
    
    功能:
    - 歌曲搜索
    - 无损音质下载
    - 元数据获取
    - 歌单获取
    """
    
    platform_name = "netease"
    platform_display_name = "网易云音乐"
    config_class = NetEaseConfig
    
    # API 端点
    BASE_URL = "https://music.163.com"
    SEARCH_URL = "https://music.163.com/api/search/get"
    SONG_URL = "https://music.163.com/api/song/enhance/player/url"
    SONG_DETAIL_URL = "https://music.163.com/api/song/detail"
    LYRIC_URL = "https://music.163.com/api/song/lyric"
    
    # 音质对应的 bitrate
    QUALITY_MAP = {
        Quality.STANDARD: {"br": 128000, "name": "standard"},
        Quality.HIGH: {"br": 320000, "name": "high"},
        Quality.LOSSLESS: {"br": 999000, "name": "lossless"},
        Quality.HI_RES: {"br": 999999, "name": "hires"},
    }
    
    # AES 加密密钥 (网易云使用的密钥)
    AES_KEY = "0CoJUm6Qyw8W8jud"
    AES_IV = "0102030405060708"
    NONCE = "0CoJUm6Qyw8W8jud"
    PUB_KEY = "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._session: Optional[httpx.AsyncClient] = None
        self._device_id = self.config.device_id or self._generate_device_id()
    
    def _generate_device_id(self) -> str:
        """生成设备 ID"""
        return hashlib.md5(
            str(datetime.now().timestamp()).encode()
        ).hexdigest()
    
    def _aes_encrypt(self, text: str) -> str:
        """AES 加密"""
        cipher = AES.new(
            self.AES_KEY.encode(),
            AES.MODE_CBC,
            self.AES_IV.encode()
        )
        padded = pad(text.encode(), AES.block_size)
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode()
    
    def _rsa_encrypt(self, text: str) -> str:
        """RSA 加密 (简化实现)"""
        # 实际应该使用 RSA 加密，这里简化处理
        return text[::-1]  # 只是示例，实际需要正确实现
    
    def _get_encrypted_params(self, params: Dict[str, Any]) -> Dict[str, str]:
        """获取加密后的参数"""
        text = json.dumps(params)
        encrypted = self._aes_encrypt(text)
        return {
            "params": encrypted,
            "encSecKey": self._rsa_encrypt(encrypted)[:256],
        }
    
    async def initialize(self) -> bool:
        """初始化 HTTP 会话"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://music.163.com/",
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
                "s": query,
                "type": 1,  # 1=单曲
                "limit": limit,
                "offset": 0,
            }
            
            response = await self._session.get(
                self.SEARCH_URL,
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 200:
                raise SearchError(
                    f"搜索失败：{data.get('message', '未知错误')}",
                    self.platform_name
                )
            
            songs = data.get("result", {}).get("songs", [])
            
            results = []
            for song in songs[:limit]:
                # 解析可用音质
                quality_available = [Quality.STANDARD]
                if song.get("hMusic"):
                    quality_available.append(Quality.HIGH)
                if song.get("sqMusic"):
                    quality_available.append(Quality.LOSSLESS)
                if song.get("hrMusic"):
                    quality_available.append(Quality.HI_RES)
                
                # 获取歌手信息
                artists = song.get("artists", [])
                artist_names = [a.get("name", "") for a in artists]
                
                # 获取专辑信息
                album = song.get("album", {})
                
                track = TrackInfo(
                    id=str(song.get("id", "")),
                    title=song.get("name", ""),
                    artist=", ".join(artist_names),
                    album=album.get("name") if album else None,
                    duration=song.get("duration", 0) // 1000,  # 毫秒转秒
                    cover_url=self._get_cover_url(album),
                    quality_available=quality_available,
                    extra={
                        "album_id": album.get("id") if album else None,
                        "artists": artists,
                        "hMusic": song.get("hMusic"),
                        "sqMusic": song.get("sqMusic"),
                        "hrMusic": song.get("hrMusic"),
                    },
                )
                results.append(track)
            
            logger.info(f"搜索 '{query}' 返回 {len(results)} 条结果")
            return results
            
        except httpx.HTTPError as e:
            raise SearchError(f"HTTP 错误：{e}", self.platform_name)
        except Exception as e:
            raise SearchError(f"搜索异常：{e}", self.platform_name)
    
    def _get_cover_url(self, album: Dict[str, Any], size: int = 300) -> str:
        """获取专辑封面 URL"""
        if not album:
            return ""
        pic_url = album.get("picUrl", "")
        if pic_url:
            # 调整图片尺寸
            return pic_url.replace("?param=150y150", f"?param={size}y{size}")
        return ""
    
    async def get_stream_url(self, track_id: str, quality: Quality = Quality.LOSSLESS) -> str:
        """
        获取歌曲流媒体 URL
        
        Args:
            track_id: 歌曲 ID
            quality: 音质质量
            
        Returns:
            str: 流媒体 URL
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            quality_info = self.QUALITY_MAP.get(quality, self.QUALITY_MAP[Quality.STANDARD])
            
            params = {
                "ids": f"[{track_id}]",
                "br": quality_info["br"],
            }
            
            response = await self._session.post(
                self.SONG_URL,
                data=params,
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 200:
                raise URLFetchError(
                    f"获取 URL 失败：{data.get('message', '未知错误')}",
                    self.platform_name
                )
            
            song_data = data.get("data", [])
            if not song_data:
                raise URLFetchError("未找到音源数据", self.platform_name)
            
            song_url_info = song_data[0]
            
            # 检查是否可用
            if song_url_info.get("code") != 200:
                raise URLFetchError(
                    f"音源不可用：code={song_url_info.get('code')}",
                    self.platform_name
                )
            
            url = song_url_info.get("url")
            if not url:
                raise URLFetchError("音源 URL 为空", self.platform_name)
            
            # 网易云的 URL 可能是 http，转换为 https
            if url.startswith("http://"):
                url = url.replace("http://", "https://")
            
            logger.debug(f"获取到流媒体 URL: {url[:50]}...")
            return url
            
        except httpx.HTTPError as e:
            raise URLFetchError(f"HTTP 错误：{e}", self.platform_name)
        except Exception as e:
            raise URLFetchError(f"获取 URL 异常：{e}", self.platform_name)
    
    async def download(self, track_id: str, save_path: Path, 
                      quality: Quality = Quality.LOSSLESS) -> DownloadResult:
        """
        下载歌曲
        
        Args:
            track_id: 歌曲 ID
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
                # 根据音质确定扩展名
                if quality in [Quality.LOSSLESS, Quality.HI_RES]:
                    filename += ".flac"
                else:
                    filename += ".mp3"
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
            track_id: 歌曲 ID
            
        Returns:
            TrackMetadata: 元数据
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 获取歌曲详情
            params = {
                "id": track_id,
                "ids": f"[{track_id}]",
            }
            
            response = await self._session.get(
                self.SONG_DETAIL_URL,
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            
            songs = data.get("songs", [])
            if not songs:
                return TrackMetadata(title="", artist="")
            
            song = songs[0]
            
            # 获取歌词
            lyric_params = {"id": track_id, "lv": -1, "tv": -1}
            lyric_response = await self._session.get(
                self.LYRIC_URL,
                params=lyric_params,
            )
            lyric_data = lyric_response.json()
            lyric = lyric_data.get("lrc", {}).get("lyric", "")
            
            # 解析元数据
            artists = song.get("artists", [])
            album = song.get("album", {})
            
            # 获取封面
            cover_data = None
            if album and album.get("picUrl"):
                try:
                    cover_response = await self._session.get(album["picUrl"])
                    if cover_response.status_code == 200:
                        cover_data = cover_response.content
                except Exception as e:
                    logger.warning(f"获取封面失败：{e}")
            
            metadata = TrackMetadata(
                title=song.get("name", ""),
                artist=", ".join(a.get("name", "") for a in artists),
                album=album.get("name") if album else None,
                track_number=song.get("position"),
                year=None,  # 需要从专辑信息获取
                genre=None,
                cover_data=cover_data,
                lyrics=lyric if lyric else None,
                extra={
                    "album_id": album.get("id") if album else None,
                    "artists": artists,
                },
            )
            
            return metadata
            
        except Exception as e:
            logger.warning(f"获取元数据失败：{e}")
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
            params = {"id": playlist_id}
            
            response = await self._session.get(
                f"{self.BASE_URL}/api/playlist/detail",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 200:
                logger.error(f"获取歌单失败：{data.get('message', '未知错误')}")
                return []
            
            tracks = data.get("result", {}).get("tracks", [])
            
            results = []
            for track in tracks:
                artists = track.get("artists", [])
                album = track.get("album", {})
                
                track_info = TrackInfo(
                    id=str(track.get("id", "")),
                    title=track.get("name", ""),
                    artist=", ".join(a.get("name", "") for a in artists),
                    album=album.get("name") if album else None,
                    duration=track.get("duration", 0) // 1000,
                    extra={"album_id": album.get("id") if album else None},
                )
                results.append(track_info)
            
            logger.info(f"获取歌单 {playlist_id} 共 {len(results)} 首歌曲")
            return results
            
        except Exception as e:
            logger.error(f"获取歌单失败：{e}")
            return []
    
    async def close(self):
        """关闭插件"""
        await super().close()


# 便捷函数
async def create_provider(config: Optional[Dict[str, Any]] = None) -> NetEaseProvider:
    """创建网易云音乐插件实例"""
    provider = NetEaseProvider(config)
    await provider.initialize()
    return provider
