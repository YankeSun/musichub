"""
音源插件 - Providers

提供不同音乐平台的音源接入
"""

from typing import Dict, Any, Optional, Type
from musichub.plugins.base import SourcePlugin

# 导入所有可用的 providers
from musichub.providers.apple_music import AppleMusicProvider, create_provider as create_apple_music_provider
from musichub.providers.qobuz import QobuzProvider, create_provider as create_qobuz_provider
from musichub.providers.youtube_music import YouTubeMusicProvider, create_provider as create_youtube_music_provider

__all__ = [
    "AppleMusicProvider",
    "QobuzProvider",
    "YouTubeMusicProvider",
    "create_provider",
    "get_provider",
    "list_providers",
    "register_provider",
    "unregister_provider",
]

# 已注册的 providers
_PROVIDERS: Dict[str, Type[SourcePlugin]] = {
    "apple_music": AppleMusicProvider,
    "qobuz": QobuzProvider,
    "youtube_music": YouTubeMusicProvider,
}


def get_provider(name: str, config: Optional[Dict[str, Any]] = None) -> Optional[SourcePlugin]:
    """
    获取音源插件实例
    
    Args:
        name: 插件名称
        config: 配置字典
    
    Returns:
        插件实例，如果不存在则返回 None
    """
    provider_class = _PROVIDERS.get(name)
    if provider_class:
        return provider_class(config)
    return None


def list_providers() -> list[str]:
    """
    列出所有可用的音源插件
    
    Returns:
        插件名称列表
    """
    return list(_PROVIDERS.keys())


def register_provider(name: str, provider_class: Type[SourcePlugin]) -> None:
    """
    注册新的音源插件
    
    Args:
        name: 插件名称
        provider_class: 插件类
    """
    _PROVIDERS[name] = provider_class


def unregister_provider(name: str) -> bool:
    """
    注销音源插件
    
    Args:
        name: 插件名称
    
    Returns:
        是否成功注销
    """
    if name in _PROVIDERS:
        del _PROVIDERS[name]
        return True
    return False
