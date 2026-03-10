"""
导出器插件基类
"""

from musichub.plugins.base import ExporterPlugin
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MP3Exporter(ExporterPlugin):
    """MP3 格式导出器"""
    
    name = "mp3"
    version = "1.0.0"
    description = "MP3 audio exporter"
    supported_formats = ["mp3"]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._bitrate = config.get("bitrate", "320k") if config else "320k"
    
    async def initialize(self) -> bool:
        self._initialized = True
        return True
    
    async def shutdown(self) -> None:
        self._initialized = False
    
    async def export(self, input_file: Path, output_format: str) -> Path:
        """导出为 MP3 格式"""
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        output_path = input_file.with_suffix(".mp3")
        
        # 简单重命名（实际实现会使用 ffmpeg 或类似工具转换）
        if input_file.suffix != ".mp3":
            input_file.rename(output_path)
        
        return output_path
    
    async def write_metadata(self, file: Path, metadata: Dict[str, Any]) -> bool:
        """写入 MP3 元数据"""
        try:
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
            from mutagen.mp3 import MP3
            
            audio = MP3(file)
            
            if audio.tags is None:
                audio.add_tags()
            
            if "title" in metadata:
                audio.tags.add(TIT2(encoding=3, text=metadata["title"]))
            if "artist" in metadata:
                audio.tags.add(TPE1(encoding=3, text=metadata["artist"]))
            if "album" in metadata:
                audio.tags.add(TALB(encoding=3, text=metadata["album"]))
            
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to write MP3 metadata: {e}")
            return False


class FLACExporter(ExporterPlugin):
    """FLAC 格式导出器"""
    
    name = "flac"
    version = "1.0.0"
    description = "FLAC lossless audio exporter"
    supported_formats = ["flac"]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
    
    async def initialize(self) -> bool:
        self._initialized = True
        return True
    
    async def shutdown(self) -> None:
        self._initialized = False
    
    async def export(self, input_file: Path, output_format: str) -> Path:
        """导出为 FLAC 格式"""
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        output_path = input_file.with_suffix(".flac")
        
        if input_file.suffix != ".flac":
            input_file.rename(output_path)
        
        return output_path
    
    async def write_metadata(self, file: Path, metadata: Dict[str, Any]) -> bool:
        """写入 FLAC 元数据"""
        try:
            from mutagen.flac import FLAC
            
            audio = FLAC(file)
            
            if "title" in metadata:
                audio["title"] = metadata["title"]
            if "artist" in metadata:
                audio["artist"] = metadata["artist"]
            if "album" in metadata:
                audio["album"] = metadata["album"]
            
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to write FLAC metadata: {e}")
            return False


class M4AExporter(ExporterPlugin):
    """M4A 格式导出器"""
    
    name = "m4a"
    version = "1.0.0"
    description = "M4A/AAC audio exporter"
    supported_formats = ["m4a"]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
    
    async def initialize(self) -> bool:
        self._initialized = True
        return True
    
    async def shutdown(self) -> None:
        self._initialized = False
    
    async def export(self, input_file: Path, output_format: str) -> Path:
        """导出为 M4A 格式"""
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        output_path = input_file.with_suffix(".m4a")
        
        if input_file.suffix != ".m4a":
            input_file.rename(output_path)
        
        return output_path
    
    async def write_metadata(self, file: Path, metadata: Dict[str, Any]) -> bool:
        """写入 M4A 元数据"""
        try:
            from mutagen.mp4 import MP4
            
            audio = MP4(file)
            
            if "title" in metadata:
                audio["\xa9nam"] = metadata["title"]
            if "artist" in metadata:
                audio["\xa9ART"] = metadata["artist"]
            if "album" in metadata:
                audio["\xa9alb"] = metadata["album"]
            
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to write M4A metadata: {e}")
            return False
