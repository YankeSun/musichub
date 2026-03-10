"""
MusicHub 平台插件包

提供多个音乐平台的统一接口实现。

支持的 platform:
- qq_music: QQ 音乐
- netease: 网易云音乐
- spotify: Spotify
- tidal: Tidal
- apple_music: Apple Music
"""

from .base import (
    BaseProvider,
    PlatformConfig,
    Quality,
    TrackInfo,
    TrackMetadata,
    DownloadResult,
    ProviderError,
    SearchError,
    URLFetchError,
    DownloadError,
    MetadataError,
    AuthenticationError,
)

from .qq_music import QQMusicProvider, QQMusicConfig
from .netease import NetEaseProvider, NetEaseConfig
from .spotify import SpotifyProvider, SpotifyConfig
from .tidal import TidalProvider, TidalConfig
from .apple_music import AppleMusicProvider, AppleMusicConfig


# 平台注册表
PROVIDERS = {
    "qq_music": QQMusicProvider,
    "netease": NetEaseProvider,
    "spotify": SpotifyProvider,
    "tidal": TidalProvider,
    "apple_music": AppleMusicProvider,
}

# 配置类注册表
PROVIDER_CONFIGS = {
    "qq_music": QQMusicConfig,
    "netease": NetEaseConfig,
    "spotify": SpotifyConfig,
    "tidal": TidalConfig,
    "apple_music": AppleMusicConfig,
}


def get_provider(platform: str, config: dict = None):
    """
    获取指定平台的插件实例
    
    Args:
        platform: 平台名称 ('qq_music', 'netease', 'spotify', 'tidal', 'apple_music')
        config: 配置字典
        
    Returns:
        BaseProvider: 插件实例
        
    Raises:
        ValueError: 不支持的平台
    """
    if platform not in PROVIDERS:
        raise ValueError(f"不支持的平台：{platform}. 支持的平台：{list(PROVIDERS.keys())}")
    
    provider_class = PROVIDERS[platform]
    return provider_class(config)


async def create_provider(platform: str, config: dict = None):
    """
    创建并初始化指定平台的插件实例
    
    Args:
        platform: 平台名称
        config: 配置字典
        
    Returns:
        BaseProvider: 已初始化的插件实例
    """
    provider = get_provider(platform, config)
    await provider.initialize()
    return provider


__all__ = [
    # 基类
    "BaseProvider",
    "PlatformConfig",
    # 数据类
    "Quality",
    "TrackInfo",
    "TrackMetadata",
    "DownloadResult",
    # 异常
    "ProviderError",
    "SearchError",
    "URLFetchError",
    "DownloadError",
    "MetadataError",
    "AuthenticationError",
    # 具体平台
    "QQMusicProvider",
    "QQMusicConfig",
    "NetEaseProvider",
    "NetEaseConfig",
    "SpotifyProvider",
    "SpotifyConfig",
    "TidalProvider",
    "TidalConfig",
    "AppleMusicProvider",
    "AppleMusicConfig",
    # 工厂函数
    "get_provider",
    "create_provider",
    # 注册表
    "PROVIDERS",
    "PROVIDER_CONFIGS",
]
