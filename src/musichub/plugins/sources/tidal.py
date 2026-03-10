"""
Tidal 音源插件

支持 Tidal 平台的音乐搜索、流媒体获取和无损下载

功能:
- 搜索歌曲/专辑/播放列表
- 获取音频流 URL
- 下载 HiFi/HiFi Plus 无损音质
- 获取元数据

音质等级:
- LOSSLESS: 16bit/44.1kHz (HiFi)
- HI_RES: 24bit/192kHz (HiFi Plus)

配置要求:
- Tidal 账号（免费/付费）
- API Token（用于认证）
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Dict, List
from dataclasses import dataclass

import httpx

from musichub.plugins.base import SourcePlugin, PluginMetadata
from musichub.core.types import TrackInfo

logger = logging.getLogger(__name__)


class TidalQuality(Enum):
    """Tidal 音质等级"""
    LOW = "LOW"  # 96kbps AAC
    HIGH = "HIGH"  # 320kbps AAC
    LOSSLESS = "LOSSLESS"  # 16bit/44.1kHz FLAC (HiFi)
    HI_RES = "HI_RES"  # 24bit/192kHz FLAC (HiFi Plus)
    HI_RES_LOSSLESS = "HI_RES_LOSSLESS"  # 24bit/192kHz FLAC (HiFi Plus)


@dataclass
class TidalConfig:
    """Tidal 插件配置"""
    api_token: str = ""
    quality: TidalQuality = TidalQuality.LOSSLESS
    client_id: str = "km8T9pS355y7dd"  # 默认 Tidal Android 客户端 ID
    client_secret: str = "66k2C6IZmV7cbrQUN99VqKzrN5WQ33J2oZ7Cz2b5sNA="
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TidalConfig":
        """从字典创建配置"""
        quality_str = data.get("quality", "LOSSLESS")
        try:
            quality = TidalQuality(quality_str)
        except ValueError:
            quality = TidalQuality.LOSSLESS
            logger.warning(f"Invalid quality '{quality_str}', using LOSSLESS")
        
        return cls(
            api_token=data.get("api_token", ""),
            quality=quality,
            client_id=data.get("client_id", cls.client_id),
            client_secret=data.get("client_secret", cls.client_secret),
        )


class TidalError(Exception):
    """Tidal API 错误"""
    pass


class TidalAuthError(TidalError):
    """Tidal 认证错误"""
    pass


class TidalNotFoundError(TidalError):
    """资源未找到错误"""
    pass


class TidalSourcePlugin(SourcePlugin):
    """
    Tidal 音源插件
    
    实现 SourcePlugin 接口，提供 Tidal 平台的音乐搜索和下载功能
    """
    
    metadata = PluginMetadata(
        name="tidal",
        version="1.0.0",
        description="Tidal 音乐平台插件 - 支持 HiFi/HiFi Plus 无损音质",
    )
    
    # 类属性（兼容旧接口）
    name = "tidal"
    version = "1.0.0"
    description = "Tidal 音乐平台插件 - 支持 HiFi/HiFi Plus 无损音质"
    
    BASE_URL = "https://api.tidalhifi.com/v1"
    AUTH_URL = "https://auth.tidal.com/v1"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Tidal 插件
        
        Args:
            config: 配置字典，包含 api_token, quality 等
        """
        super().__init__(config)
        self._config = TidalConfig.from_dict(config or {})
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._country_code: str = "US"
    
    async def initialize(self) -> bool:
        """
        初始化插件
        
        Returns:
            是否初始化成功
        """
        try:
            # 创建 HTTP 客户端
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={
                    "User-Agent": "Tidal/2.89.0 (Android; Android 13)",
                    "X-Tidal-Unit": "android",
                },
            )
            
            # 验证配置
            if not self._config.api_token:
                logger.warning("Tidal API token not configured")
                # 尝试使用客户端凭证获取 token
                await self._authenticate_with_client_credentials()
            else:
                self._access_token = self._config.api_token
            
            # 获取用户信息
            await self._fetch_user_info()
            
            self._initialized = True
            logger.info(f"Tidal plugin initialized. Quality: {self._config.quality.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Tidal plugin: {e}")
            return False
    
    async def _authenticate_with_client_credentials(self) -> None:
        """使用客户端凭证获取访问令牌"""
        try:
            url = f"{self.AUTH_URL}/oauth2/token"
            data = {
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "grant_type": "client_credentials",
            }
            
            response = await self._client.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            self._access_token = result.get("access_token")
            
            if not self._access_token:
                raise TidalAuthError("Failed to get access token")
            
            logger.info("Authenticated with Tidal using client credentials")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TidalAuthError("Invalid client credentials") from e
            raise TidalAuthError(f"Authentication failed: {e}") from e
        except Exception as e:
            raise TidalAuthError(f"Authentication error: {e}") from e
    
    async def _fetch_user_info(self) -> None:
        """获取用户信息"""
        try:
            url = f"{self.BASE_URL}/user"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            
            response = await self._client.get(url, headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            self._user_id = str(user_data.get("id", ""))
            self._country_code = user_data.get("countryCode", "US")
            
            # 检查订阅状态
            subscription = user_data.get("subscription", {})
            sub_type = subscription.get("type", "FREE")
            logger.info(f"Tidal user: {self._user_id}, Subscription: {sub_type}, Country: {self._country_code}")
            
        except Exception as e:
            logger.warning(f"Failed to fetch user info: {e}")
            self._country_code = "US"  # 使用默认值
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._access_token = None
        self._user_id = None
        self._initialized = False
        logger.info("Tidal plugin cleaned up")
    
    # 兼容旧接口的 shutdown 方法
    async def shutdown(self) -> None:
        """关闭插件"""
        await self.cleanup()
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self._config.api_token and not self._config.client_id:
            logger.error("Tidal configuration missing: api_token or client_id required")
            return False
        return True
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        search_type: str = "tracks",
    ) -> List[TrackInfo]:
        """
        搜索音乐
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            search_type: 搜索类型 (tracks, albums, playlists, artists)
        
        Returns:
            TrackInfo 列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            url = f"{self.BASE_URL}/search"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            params = {
                "query": query,
                "limit": min(limit, 100),
                "offset": 0,
                "types": search_type,
                "countryCode": self._country_code,
            }
            
            response = await self._client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if search_type == "tracks" or "tracks" in data:
                tracks_data = data.get("tracks", {}).get("items", [])
                return [self._parse_track(track) for track in tracks_data if track]
            
            elif search_type == "albums" or "albums" in data:
                # 返回专辑中的歌曲
                albums_data = data.get("albums", {}).get("items", [])
                results = []
                for album in albums_data[:limit // 5]:  # 限制专辑数量
                    album_tracks = await self.get_album_tracks(album.get("id", ""))
                    results.extend(album_tracks)
                    if len(results) >= limit:
                        break
                return results[:limit]
            
            elif search_type == "playlists" or "playlists" in data:
                # 返回播放列表中的歌曲
                playlists_data = data.get("playlists", {}).get("items", [])
                results = []
                for playlist in playlists_data[:limit // 10]:
                    playlist_tracks = await self.get_playlist_tracks(playlist.get("uuid", ""))
                    results.extend(playlist_tracks)
                    if len(results) >= limit:
                        break
                return results[:limit]
            
            return []
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Tidal search error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 401:
                await self._authenticate_with_client_credentials()
                return await self.search(query, limit, search_type)
            raise TidalError(f"Search failed: {e}") from e
        except Exception as e:
            logger.error(f"Tidal search error: {e}")
            raise TidalError(f"Search failed: {e}") from e
    
    def _parse_track(self, track_data: Dict[str, Any]) -> TrackInfo:
        """解析 Tidal 音轨数据为 TrackInfo"""
        artist = track_data.get("artist", {})
        album = track_data.get("album", {})
        
        return TrackInfo(
            id=str(track_data.get("id", "")),
            title=track_data.get("title", "Unknown"),
            artist=artist.get("name", "Unknown Artist") if isinstance(artist, dict) else str(artist),
            album=album.get("title", "") if isinstance(album, dict) else str(album),
            duration=track_data.get("duration", 0),
            source="tidal",
            cover_url=self._get_cover_url(album),
            year=int(album.get("releaseDate", "")[:4]) if album.get("releaseDate") else None,
            genre="",
            track_number=track_data.get("trackNumber"),
        )
    
    def _get_cover_url(self, album: Dict[str, Any], size: str = "1280x1280") -> Optional[str]:
        """获取专辑封面 URL"""
        if not album or not isinstance(album, dict):
            return None
        
        cover_id = album.get("cover", "")
        if not cover_id:
            return None
        
        # Tidal 封面 URL 格式
        cover_id = cover_id.replace("-", "/")
        return f"https://resources.tidal.com/images/{cover_id}/{size}.jpg"
    
    async def get_track_info(self, track_id: str) -> TrackInfo:
        """
        获取音轨详细信息
        
        Args:
            track_id: 音轨 ID
        
        Returns:
            TrackInfo
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            url = f"{self.BASE_URL}/tracks/{track_id}"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            params = {"countryCode": self._country_code}
            
            response = await self._client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            track_data = response.json()
            return self._parse_track(track_data)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise TidalNotFoundError(f"Track not found: {track_id}") from e
            if e.response.status_code == 401:
                await self._authenticate_with_client_credentials()
                return await self.get_track_info(track_id)
            raise TidalError(f"Failed to get track info: {e}") from e
        except Exception as e:
            raise TidalError(f"Failed to get track info: {e}") from e
    
    async def get_album_tracks(self, album_id: str) -> List[TrackInfo]:
        """
        获取专辑中的所有音轨
        
        Args:
            album_id: 专辑 ID
        
        Returns:
            TrackInfo 列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            url = f"{self.BASE_URL}/albums/{album_id}/items"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            params = {
                "countryCode": self._country_code,
                "limit": 100,
                "offset": 0,
            }
            
            all_tracks = []
            
            while True:
                response = await self._client.get(url, headers=headers, params=params)
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
            logger.error(f"Failed to get album tracks: {e}")
            raise TidalError(f"Failed to get album tracks: {e}") from e
    
    async def get_playlist_tracks(self, playlist_id: str) -> List[TrackInfo]:
        """
        获取播放列表中的所有音轨
        
        Args:
            playlist_id: 播放列表 ID
        
        Returns:
            TrackInfo 列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            url = f"{self.BASE_URL}/playlists/{playlist_id}/items"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            params = {
                "countryCode": self._country_code,
                "limit": 100,
                "offset": 0,
            }
            
            all_tracks = []
            
            while True:
                response = await self._client.get(url, headers=headers, params=params)
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
            logger.error(f"Failed to get playlist tracks: {e}")
            raise TidalError(f"Failed to get playlist tracks: {e}") from e
    
    async def get_stream_url(
        self,
        track_id: str,
        quality: Optional[TidalQuality] = None,
    ) -> Dict[str, Any]:
        """
        获取音频流 URL 和元数据
        
        Args:
            track_id: 音轨 ID
            quality: 音质等级（可选，默认使用配置的音质）
        
        Returns:
            包含流 URL 和音频信息的字典:
            - url: 流媒体 URL
            - codec: 编解码器 (FLAC, AAC, etc.)
            - sample_rate: 采样率
            - bit_depth: 位深度
            - quality: 实际音质等级
        """
        if not self._initialized:
            await self.initialize()
        
        target_quality = quality or self._config.quality
        
        try:
            url = f"{self.BASE_URL}/tracks/{track_id}/playbackinfopostpaywall"
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "X-Tidal-Unit": "android",
            }
            params = {
                "countryCode": self._country_code,
                "playbackmode": "STREAM",
                "assetpresentation": "FULL",
            }
            json_data = {
                "audioquality": target_quality.value,
            }
            
            response = await self._client.post(
                url,
                headers=headers,
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 检查实际返回的音质
            actual_quality = data.get("audioQuality", target_quality.value)
            audio_mode = data.get("audioMode", "STEREO")
            
            result = {
                "track_id": track_id,
                "quality": actual_quality,
                "audio_mode": audio_mode,
                "codec": "UNKNOWN",
                "sample_rate": 44100,
                "bit_depth": 16,
                "url": None,
                "manifest": None,
            }
            
            # 处理不同类型的响应
            if "manifest" in data:
                # 新版 API 返回 manifest
                manifest = data["manifest"]
                manifest_mime_type = manifest.get("mimeType", "application/dash+xml")
                
                if manifest_mime_type == "application/dash+xml":
                    # DASH 流
                    import base64
                    manifest_data = base64.b64decode(manifest.get("data", "")).decode("utf-8")
                    result["manifest"] = manifest_data
                    result["codec"] = "DASH"
                    
                elif manifest_mime_type == "video/mp4":
                    # MP4 流（加密）
                    import base64
                    manifest_data = base64.b64decode(manifest.get("data", "")).decode("utf-8")
                    result["manifest"] = manifest_data
                    result["codec"] = "MP4"
                
                # 从 manifest 解析音频信息
                result["codec"] = manifest.get("codecs", result["codec"])
                
            elif "streamUrl" in data:
                # 旧版 API 直接返回 URL
                result["url"] = data["streamUrl"]
                result["codec"] = "MP4"
            
            # 根据音质设置采样率和位深度
            if actual_quality in ("HI_RES", "HI_RES_LOSSLESS"):
                result["sample_rate"] = 192000
                result["bit_depth"] = 24
            elif actual_quality == "LOSSLESS":
                result["sample_rate"] = 44100
                result["bit_depth"] = 16
            
            logger.info(
                f"Got stream URL for track {track_id}: "
                f"Quality={actual_quality}, Codec={result['codec']}, "
                f"{result['bit_depth']}bit/{result['sample_rate']}Hz"
            )
            
            return result
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                await self._authenticate_with_client_credentials()
                return await self.get_stream_url(track_id, quality)
            if e.response.status_code == 403:
                raise TidalError(
                    f"Access denied for track {track_id}. "
                    f"This track may require a higher subscription tier."
                ) from e
            raise TidalError(f"Failed to get stream URL: {e}") from e
        except Exception as e:
            raise TidalError(f"Failed to get stream URL: {e}") from e
    
    async def download_track(
        self,
        track_id: str,
        output_dir: Path,
        quality: Optional[TidalQuality] = None,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        下载音轨
        
        Args:
            track_id: 音轨 ID
            output_dir: 输出目录
            quality: 音质等级
            progress_callback: 进度回调
        
        Returns:
            下载结果字典
        """
        import time
        from musichub.core.engine import DownloadResult
        
        start_time = time.time()
        
        try:
            # 获取音轨信息
            track_info = await self.get_track_info(track_id)
            
            # 获取流 URL
            stream_info = await self.get_stream_url(track_id, quality)
            
            # 创建输出目录
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 确定输出文件名
            safe_title = "".join(c for c in track_info.title if c.isalnum() or c in " -_")
            safe_artist = "".join(c for c in track_info.artist if c.isalnum() or c in " -_")
            
            # 根据音质确定文件扩展名
            if stream_info["quality"] in ("HI_RES", "HI_RES_LOSSLESS", "LOSSLESS"):
                ext = "flac"
            else:
                ext = "m4a"
            
            output_path = output_dir / f"{safe_artist} - {safe_title}.{ext}"
            
            # 下载文件
            download_result = await self._download_file(
                stream_info,
                output_path,
                progress_callback,
            )
            
            elapsed = time.time() - start_time
            
            return {
                "success": download_result.success,
                "track_info": track_info,
                "output_path": str(output_path) if download_result.success else None,
                "quality": stream_info["quality"],
                "codec": stream_info["codec"],
                "sample_rate": stream_info["sample_rate"],
                "bit_depth": stream_info["bit_depth"],
                "duration": elapsed,
                "size_bytes": download_result.size_bytes if download_result.success else 0,
                "error": download_result.error if not download_result.success else None,
            }
            
        except Exception as e:
            logger.error(f"Failed to download track {track_id}: {e}")
            return {
                "success": False,
                "track_id": track_id,
                "error": str(e),
            }
    
    async def _download_file(
        self,
        stream_info: Dict[str, Any],
        output_path: Path,
        progress_callback: Optional[callable] = None,
    ) -> "DownloadResult":
        """
        下载文件（处理 manifest 或直接 URL）
        
        Args:
            stream_info: 流信息字典
            output_path: 输出路径
            progress_callback: 进度回调
        
        Returns:
            DownloadResult
        """
        from musichub.core.engine import DownloadResult
        
        try:
            # 如果有 manifest，需要解析 DASH 或 MP4
            if stream_info.get("manifest"):
                return await self._download_from_manifest(
                    stream_info["manifest"],
                    output_path,
                    progress_callback,
                )
            
            # 直接下载 URL
            if not stream_info.get("url"):
                return DownloadResult(
                    success=False,
                    error="No stream URL available",
                )
            
            async with self._client.stream("GET", stream_info["url"]) as response:
                if response.status_code != 200:
                    return DownloadResult(
                        success=False,
                        error=f"HTTP {response.status_code}",
                    )
                
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                
                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total > 0:
                            progress_callback(downloaded, total)
                
                return DownloadResult(
                    success=True,
                    file_path=output_path,
                    size_bytes=downloaded,
                )
                
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return DownloadResult(
                success=False,
                error=str(e),
            )
    
    async def _download_from_manifest(
        self,
        manifest_data: str,
        output_path: Path,
        progress_callback: Optional[callable] = None,
    ) -> "DownloadResult":
        """
        从 manifest 下载文件（DASH 或加密 MP4）
        
        Args:
            manifest_data: manifest 数据（XML 或 JSON）
            output_path: 输出路径
            progress_callback: 进度回调
        
        Returns:
            DownloadResult
        """
        from musichub.core.engine import DownloadResult
        
        try:
            # 尝试解析 DASH manifest
            if "<?xml" in manifest_data or "<MPD" in manifest_data:
                # DASH manifest
                return await self._download_dash(
                    manifest_data,
                    output_path,
                    progress_callback,
                )
            
            # MP4 manifest (加密)
            # 需要解密，这里简化处理
            logger.warning("Encrypted MP4 stream requires decryption (not implemented)")
            return DownloadResult(
                success=False,
                error="Encrypted content requires additional decryption",
            )
            
        except Exception as e:
            logger.error(f"Manifest download failed: {e}")
            return DownloadResult(
                success=False,
                error=str(e),
            )
    
    async def _download_dash(
        self,
        manifest_xml: str,
        output_path: Path,
        progress_callback: Optional[callable] = None,
    ) -> "DownloadResult":
        """
        下载 DASH 流
        
        Args:
            manifest_xml: DASH manifest XML
            output_path: 输出路径
            progress_callback: 进度回调
        
        Returns:
            DownloadResult
        """
        from musichub.core.engine import DownloadResult
        import xml.etree.ElementTree as ET
        
        try:
            # 解析 DASH manifest
            root = ET.fromstring(manifest_xml)
            ns = {"mpd": "urn:mpeg:dash:schema:mpd:2011"}
            
            # 查找 Representation（选择最高音质的）
            representations = root.findall(".//mpd:Representation", ns)
            if not representations:
                # 尝试不带命名空间
                representations = root.findall(".//Representation")
            
            if not representations:
                return DownloadResult(
                    success=False,
                    error="No representations found in DASH manifest",
                )
            
            # 选择音频表示（通常 bandwidth 最高的是最佳音质）
            best_rep = max(
                representations,
                key=lambda r: int(r.get("bandwidth", 0)),
            )
            
            # 获取 SegmentURL 列表
            segment_urls = []
            for segment in best_rep.findall(".//mpd:SegmentURL", ns) or best_rep.findall(".//SegmentURL"):
                media_url = segment.get("media")
                if media_url:
                    # 处理相对 URL
                    if not media_url.startswith("http"):
                        base_url = best_rep.findtext(".//mpd:BaseURL", "", ns) or best_rep.findtext(".//BaseURL", "")
                        if base_url and not base_url.startswith("http"):
                            # 需要从 manifest 获取基础 URL
                            pass
                        media_url = base_url + media_url if base_url else media_url
                    segment_urls.append(media_url)
            
            if not segment_urls:
                # 尝试使用 initialization + segment template
                init_url = best_rep.findtext(".//mpd:Initialization/@sourceURL", "", ns)
                if init_url:
                    segment_urls.append(init_url)
            
            # 下载所有片段
            downloaded_bytes = 0
            with open(output_path, "wb") as f:
                for i, url in enumerate(segment_urls):
                    response = await self._client.get(url)
                    if response.status_code == 200:
                        f.write(response.content)
                        downloaded_bytes += len(response.content)
                        
                        if progress_callback:
                            progress_callback(i + 1, len(segment_urls))
            
            return DownloadResult(
                success=True,
                file_path=output_path,
                size_bytes=downloaded_bytes,
            )
            
        except ET.ParseError as e:
            return DownloadResult(
                success=False,
                error=f"Failed to parse DASH manifest: {e}",
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                error=f"DASH download failed: {e}",
            )
    
    def get_quality_info(self) -> Dict[str, Any]:
        """
        获取当前音质配置信息
        
        Returns:
            音质信息字典
        """
        quality_map = {
            TidalQuality.LOW: {"name": "Low", "bitrate": "96kbps", "codec": "AAC"},
            TidalQuality.HIGH: {"name": "High", "bitrate": "320kbps", "codec": "AAC"},
            TidalQuality.LOSSLESS: {"name": "Lossless", "bitrate": "1411kbps", "codec": "FLAC", "bit_depth": 16, "sample_rate": 44100},
            TidalQuality.HI_RES: {"name": "Hi-Res", "bitrate": "Variable", "codec": "FLAC", "bit_depth": 24, "sample_rate": 192000},
            TidalQuality.HI_RES_LOSSLESS: {"name": "Hi-Res Lossless", "bitrate": "Variable", "codec": "FLAC", "bit_depth": 24, "sample_rate": 192000},
        }
        
        current = quality_map.get(self._config.quality, {})
        
        return {
            "configured_quality": self._config.quality.value,
            **current,
            "subscription_required": "HiFi" if self._config.quality in (TidalQuality.LOSSLESS, TidalQuality.HI_RES, TidalQuality.HI_RES_LOSSLESS) else "Free",
        }


# 插件导出
def create_plugin(config: Optional[Dict[str, Any]] = None) -> TidalSourcePlugin:
    """创建 Tidal 插件实例"""
    return TidalSourcePlugin(config)
