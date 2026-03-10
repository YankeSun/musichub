"""
插件系统基类 - 定义插件接口和注册表
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Type
from pathlib import Path
import logging
from importlib.metadata import entry_points

logger = logging.getLogger(__name__)


class PluginBase(ABC):
    """
    插件基类
    
    所有插件必须继承此类并实现必要的抽象方法
    """
    
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化插件
        
        Returns:
            是否初始化成功
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭插件，清理资源"""
        pass
    
    def validate_config(self) -> bool:
        """验证配置"""
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "initialized": self._initialized
        }


class SourcePlugin(PluginBase):
    """
    音源插件基类
    
    负责从不同平台搜索和获取音源信息
    """
    
    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> List[Any]:
        """
        搜索音乐
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
        
        Returns:
            TrackInfo 列表
        """
        pass
    
    @abstractmethod
    async def get_track_info(self, track_id: str) -> Any:
        """
        获取音轨详细信息
        
        Args:
            track_id: 音轨 ID
        
        Returns:
            TrackInfo
        """
        pass
    
    @abstractmethod
    async def get_stream_url(self, track_id: str) -> Optional[str]:
        """
        获取流媒体 URL
        
        Args:
            track_id: 音轨 ID
        
        Returns:
            流媒体 URL
        """
        pass


class DownloaderPlugin(PluginBase):
    """
    下载器插件基类
    
    负责实际的文件下载
    """
    
    supports_resume: bool = True
    
    @abstractmethod
    async def download(
        self,
        url: str,
        dest: Path,
        resume_data: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        下载文件
        
        Args:
            url: 下载 URL
            dest: 目标路径
            resume_data: 断点续传数据
            progress_callback: 进度回调函数 (downloaded, total)
        
        Returns:
            下载结果字典
        """
        pass


class ExporterPlugin(PluginBase):
    """
    导出器插件基类
    
    负责音频格式转换和元数据写入
    """
    
    supported_formats: List[str] = []
    
    @abstractmethod
    async def export(
        self,
        input_file: Path,
        output_format: str
    ) -> Path:
        """
        导出/转换音频文件
        
        Args:
            input_file: 输入文件路径
            output_format: 输出格式
        
        Returns:
            输出文件路径
        """
        pass
    
    @abstractmethod
    async def write_metadata(
        self,
        file: Path,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        写入元数据
        
        Args:
            file: 音频文件路径
            metadata: 元数据字典
        
        Returns:
            是否成功
        """
        pass


class PluginRegistry:
    """
    插件注册表
    
    管理所有已加载的插件
    """
    
    _instance: Optional["PluginRegistry"] = None
    
    def __new__(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._sources: Dict[str, SourcePlugin] = {}
        self._downloaders: Dict[str, DownloaderPlugin] = {}
        self._exporters: Dict[str, ExporterPlugin] = {}
        self._initialized = True
    
    def register_source(self, name: str, plugin: SourcePlugin) -> None:
        """注册音源插件"""
        self._sources[name] = plugin
        logger.info(f"Registered source plugin: {name}")
    
    def register_downloader(self, name: str, plugin: DownloaderPlugin) -> None:
        """注册下载器插件"""
        self._downloaders[name] = plugin
        logger.info(f"Registered downloader plugin: {name}")
    
    def register_exporter(self, name: str, plugin: ExporterPlugin) -> None:
        """注册导出器插件"""
        self._exporters[name] = plugin
        logger.info(f"Registered exporter plugin: {name}")
    
    def get_source(self, name: str) -> Optional[SourcePlugin]:
        """获取音源插件"""
        return self._sources.get(name)
    
    def get_downloader(self, name: str) -> Optional[DownloaderPlugin]:
        """获取下载器插件"""
        return self._downloaders.get(name)
    
    def get_exporter(self, name: str) -> Optional[ExporterPlugin]:
        """获取导出器插件"""
        return self._exporters.get(name)
    
    def list_sources(self) -> List[str]:
        """列出所有音源插件"""
        return list(self._sources.keys())
    
    def list_downloaders(self) -> List[str]:
        """列出所有下载器插件"""
        return list(self._downloaders.keys())
    
    def list_exporters(self) -> List[str]:
        """列出所有导出器插件"""
        return list(self._exporters.keys())
    
    def unregister_source(self, name: str) -> bool:
        """注销音源插件"""
        if name in self._sources:
            del self._sources[name]
            return True
        return False
    
    def unregister_downloader(self, name: str) -> bool:
        """注销下载器插件"""
        if name in self._downloaders:
            del self._downloaders[name]
            return True
        return False
    
    def unregister_exporter(self, name: str) -> bool:
        """注销导出器插件"""
        if name in self._exporters:
            del self._exporters[name]
            return True
        return False
    
    async def initialize_all(self) -> None:
        """初始化所有插件"""
        for plugin in self._sources.values():
            try:
                await plugin.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize source {plugin.name}: {e}")
        
        for plugin in self._downloaders.values():
            try:
                await plugin.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize downloader {plugin.name}: {e}")
        
        for plugin in self._exporters.values():
            try:
                await plugin.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize exporter {plugin.name}: {e}")
    
    async def shutdown_all(self) -> None:
        """关闭所有插件"""
        for plugin in self._sources.values():
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error(f"Failed to shutdown source {plugin.name}: {e}")
        
        for plugin in self._downloaders.values():
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error(f"Failed to shutdown downloader {plugin.name}: {e}")
        
        for plugin in self._exporters.values():
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error(f"Failed to shutdown exporter {plugin.name}: {e}")
    
    @classmethod
    def load_from_entry_points(cls) -> "PluginRegistry":
        """从 entry points 加载插件"""
        registry = cls()
        
        # 加载音源插件
        try:
            eps = entry_points(group="musichub.sources")
            for ep in eps:
                try:
                    plugin_class: Type[SourcePlugin] = ep.load()
                    plugin = plugin_class()
                    registry.register_source(ep.name, plugin)
                except Exception as e:
                    logger.error(f"Failed to load source plugin {ep.name}: {e}")
        except Exception as e:
            logger.warning(f"No source entry points found: {e}")
        
        # 加载下载器插件
        try:
            eps = entry_points(group="musichub.downloaders")
            for ep in eps:
                try:
                    plugin_class: Type[DownloaderPlugin] = ep.load()
                    plugin = plugin_class()
                    registry.register_downloader(ep.name, plugin)
                except Exception as e:
                    logger.error(f"Failed to load downloader plugin {ep.name}: {e}")
        except Exception as e:
            logger.warning(f"No downloader entry points found: {e}")
        
        # 加载导出器插件
        try:
            eps = entry_points(group="musichub.exporters")
            for ep in eps:
                try:
                    plugin_class: Type[ExporterPlugin] = ep.load()
                    plugin = plugin_class()
                    registry.register_exporter(ep.name, plugin)
                except Exception as e:
                    logger.error(f"Failed to load exporter plugin {ep.name}: {e}")
        except Exception as e:
            logger.warning(f"No exporter entry points found: {e}")
        
        return registry
