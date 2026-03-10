"""
MusicHub 插件抽象基类

定义所有音乐平台插件必须实现的统一接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Quality(Enum):
    """音频质量枚举"""
    STANDARD = "standard"      # 标准品质 (128kbps MP3)
    HIGH = "high"              # 高品质 (320kbps MP3)
    LOSSLESS = "lossless"      # 无损 (FLAC)
    HI_RES = "hi_res"          # 高解析度 (24bit/96kHz+)


@dataclass
class TrackInfo:
    """歌曲信息数据类"""
    id: str
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[int] = None  # 秒
    cover_url: Optional[str] = None
    quality_available: List[Quality] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"{self.artist} - {self.title}"


@dataclass
class TrackMetadata:
    """歌曲元数据（用于写入文件标签）"""
    title: str
    artist: str
    album: Optional[str] = None
    track_number: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    cover_data: Optional[bytes] = None  # 封面图片二进制数据
    lyrics: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DownloadResult:
    """下载结果数据类"""
    success: bool
    file_path: Optional[Path] = None
    error: Optional[str] = None
    quality: Optional[Quality] = None
    file_size: Optional[int] = None  # 字节
    metadata: Optional[TrackMetadata] = None


class PlatformConfig:
    """平台配置基类"""
    
    def __init__(self, **kwargs):
        self.api_key: Optional[str] = kwargs.get("api_key")
        self.api_secret: Optional[str] = kwargs.get("api_secret")
        self.cookie: Optional[str] = kwargs.get("cookie")
        self.timeout: int = kwargs.get("timeout", 30)
        self.retry_times: int = kwargs.get("retry_times", 3)
        self.proxy: Optional[str] = kwargs.get("proxy")
        
    def validate(self) -> bool:
        """验证配置是否有效"""
        return True


class BaseProvider(ABC):
    """
    音乐平台插件抽象基类
    
    所有平台插件必须继承此类并实现所有抽象方法。
    """
    
    # 平台标识符（子类必须定义）
    platform_name: str = "base"
    platform_display_name: str = "未知平台"
    
    # 默认配置类（子类可覆盖）
    config_class = PlatformConfig
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化插件
        
        Args:
            config: 配置字典，包含 api_key, cookie 等
        """
        self.config = self.config_class(**(config or {}))
        self._session = None
        self._initialized = False
        logger.debug(f"{self.platform_display_name} 插件初始化")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化插件（建立连接、验证认证等）
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def download(self, track_id: str, save_path: Path, 
                      quality: Quality = Quality.LOSSLESS) -> DownloadResult:
        """
        下载歌曲
        
        Args:
            track_id: 歌曲 ID
            save_path: 保存路径（目录或完整文件路径）
            quality: 期望的音质质量
            
        Returns:
            DownloadResult: 下载结果
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_playlist(self, playlist_id: str) -> List[TrackInfo]:
        """
        获取歌单歌曲列表
        
        Args:
            playlist_id: 歌单 ID
            
        Returns:
            List[TrackInfo]: 歌单中的歌曲列表
        """
        pass
    
    async def close(self):
        """关闭插件，释放资源"""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False
        logger.debug(f"{self.platform_display_name} 插件已关闭")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# ============== 异常定义 ==============

class ProviderError(Exception):
    """插件基类异常"""
    def __init__(self, message: str, platform: str = "unknown"):
        self.platform = platform
        super().__init__(f"[{platform}] {message}")


class SearchError(ProviderError):
    """搜索异常"""
    pass


class URLFetchError(ProviderError):
    """URL 获取异常"""
    pass


class DownloadError(ProviderError):
    """下载异常"""
    pass


class MetadataError(ProviderError):
    """元数据获取异常"""
    pass


class AuthenticationError(ProviderError):
    """认证异常"""
    pass
