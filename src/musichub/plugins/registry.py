"""
插件注册表

负责发现、加载、管理所有插件
"""

from __future__ import annotations

import importlib
from typing import TypeVar, Generic, Protocol
from importlib.metadata import entry_points

from musichub.plugins.base import PluginBase, PluginMetadata


class SourcePlugin(Protocol):
    """音源插件协议"""
    name: str
    
    async def search(self, query: str, limit: int = 20) -> list:
        ...
    
    async def get_track_info(self, track_id: str) -> object:
        ...
    
    async def get_stream_url(self, track_id: str) -> object:
        ...


class DownloaderPlugin(Protocol):
    """下载器插件协议"""
    name: str
    supports_resume: bool
    
    async def download(self, url: str, dest: object, **kwargs) -> object:
        ...


class ExporterPlugin(Protocol):
    """导出器插件协议"""
    name: str
    supported_formats: list[str]
    
    async def export(self, input_file: object, output_format: str, **kwargs) -> object:
        ...
    
    async def write_metadata(self, file: object, metadata: object) -> None:
        ...


T = TypeVar('T')


class PluginRegistry:
    """
    插件注册表
    
    使用 entry points 自动发现插件
    """
    
    def __init__(self):
        self._sources: dict[str, SourcePlugin] = {}
        self._downloaders: dict[str, DownloaderPlugin] = {}
        self._exporters: dict[str, ExporterPlugin] = {}
        self._loaded = False
    
    async def discover_plugins(self) -> None:
        """发现并加载所有插件"""
        if self._loaded:
            return
        
        # 加载音源插件
        await self._load_entry_points("musichub.sources", self._sources)
        
        # 加载下载器插件
        await self._load_entry_points("musichub.downloaders", self._downloaders)
        
        # 加载导出器插件
        await self._load_entry_points("musichub.exporters", self._exporters)
        
        self._loaded = True
    
    async def _load_entry_points(self, group: str, registry: dict) -> None:
        """加载指定类型的 entry points"""
        try:
            eps = entry_points(group=group)
        except Exception:
            # Python 3.9 兼容性
            eps = entry_points().get(group, [])
        
        for ep in eps:
            try:
                plugin_class = ep.load()
                instance = plugin_class()
                await instance.initialize()
                registry[instance.name] = instance
            except Exception as e:
                print(f"加载插件失败 {ep.name}: {e}")
    
    def get_source(self, name: str) -> SourcePlugin | None:
        """获取音源插件"""
        return self._sources.get(name)
    
    def get_downloader(self, name: str) -> DownloaderPlugin | None:
        """获取下载器插件"""
        return self._downloaders.get(name)
    
    def get_exporter(self, name: str) -> ExporterPlugin | None:
        """获取导出器插件"""
        return self._exporters.get(name)
    
    def list_sources(self) -> list[str]:
        """列出所有音源插件"""
        return list(self._sources.keys())
    
    def list_downloaders(self) -> list[str]:
        """列出所有下载器插件"""
        return list(self._downloaders.keys())
    
    def list_exporters(self) -> list[str]:
        """列出所有导出器插件"""
        return list(self._exporters.keys())
    
    async def cleanup(self) -> None:
        """清理所有插件资源"""
        for plugin in list(self._sources.values()) + list(self._downloaders.values()) + list(self._exporters.values()):
            try:
                await plugin.cleanup()
            except Exception:
                pass
        self._loaded = False
    
    def register_source(self, name: str, plugin: SourcePlugin) -> None:
        """手动注册音源插件"""
        self._sources[name] = plugin
    
    def register_downloader(self, name: str, plugin: DownloaderPlugin) -> None:
        """手动注册下载器插件"""
        self._downloaders[name] = plugin
    
    def register_exporter(self, name: str, plugin: ExporterPlugin) -> None:
        """手动注册导出器插件"""
        self._exporters[name] = plugin
