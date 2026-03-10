"""
元数据处理 - 音乐元数据管理和写入
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TrackMetadata:
    """音轨元数据"""
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    track_number: int = 0
    disc_number: int = 0
    year: int = 0
    genre: str = ""
    composer: str = ""
    comment: str = ""
    cover_art: Optional[bytes] = None
    cover_url: Optional[str] = None
    duration: int = 0  # 秒
    bitrate: int = 0  # kbps
    sample_rate: int = 0  # Hz
    additional_fields: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_track_info(cls, track_info: Any) -> "TrackMetadata":
        """从 TrackInfo 创建元数据"""
        return cls(
            title=getattr(track_info, "title", ""),
            artist=getattr(track_info, "artist", ""),
            album=getattr(track_info, "album", ""),
            duration=getattr(track_info, "duration", 0),
            cover_url=getattr(track_info, "cover_url", None),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "album_artist": self.album_artist,
            "track_number": self.track_number,
            "disc_number": self.disc_number,
            "year": self.year,
            "genre": self.genre,
            "composer": self.composer,
            "comment": self.comment,
            "duration": self.duration,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            **self.additional_fields
        }
    
    def is_complete(self) -> bool:
        """检查元数据是否完整"""
        return bool(self.title and self.artist)


class MetadataManager:
    """
    元数据管理器
    
    负责：
    - 读取音频文件元数据
    - 写入元数据到音频文件
    - 下载和嵌入封面图片
    """
    
    def __init__(self):
        self._supported_formats = ["mp3", "flac", "m4a", "wav", "ogg"]
    
    async def read_metadata(self, file: Path) -> Optional[TrackMetadata]:
        """读取音频文件的元数据"""
        if not file.exists():
            return None
        
        try:
            from mutagen import File as MutagenFile
            
            audio = MutagenFile(file)
            if audio is None:
                return None
            
            metadata = TrackMetadata()
            
            # 根据格式读取元数据
            if file.suffix.lower() == ".mp3":
                metadata = self._read_mp3_metadata(audio)
            elif file.suffix.lower() == ".flac":
                metadata = self._read_flac_metadata(audio)
            elif file.suffix.lower() in [".m4a", ".mp4"]:
                metadata = self._read_m4a_metadata(audio)
            
            # 读取技术信息
            if audio.info:
                metadata.duration = int(audio.info.length) if hasattr(audio.info, "length") else 0
                metadata.bitrate = int(audio.info.bitrate / 1000) if hasattr(audio.info, "bitrate") else 0
                metadata.sample_rate = audio.info.sample_rate if hasattr(audio.info, "sample_rate") else 0
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to read metadata from {file}: {e}")
            return None
    
    def _read_mp3_metadata(self, audio) -> TrackMetadata:
        """读取 MP3 元数据"""
        metadata = TrackMetadata()
        
        if audio.tags:
            metadata.title = str(audio.tags.get("TIT2", ""))
            metadata.artist = str(audio.tags.get("TPE1", ""))
            metadata.album = str(audio.tags.get("TALB", ""))
            metadata.year = int(str(audio.tags.get("TDRC", 0)) or 0)
            metadata.genre = str(audio.tags.get("TCON", ""))
        
        return metadata
    
    def _read_flac_metadata(self, audio) -> TrackMetadata:
        """读取 FLAC 元数据"""
        metadata = TrackMetadata()
        
        metadata.title = audio.get("title", [""])[0]
        metadata.artist = audio.get("artist", [""])[0]
        metadata.album = audio.get("album", [""])[0]
        metadata.year = int(audio.get("date", ["0"])[0] or 0)
        metadata.genre = audio.get("genre", [""])[0]
        
        return metadata
    
    def _read_m4a_metadata(self, audio) -> TrackMetadata:
        """读取 M4A 元数据"""
        metadata = TrackMetadata()
        
        metadata.title = audio.get("\xa9nam", [""])[0]
        metadata.artist = audio.get("\xa9ART", [""])[0]
        metadata.album = audio.get("\xa9alb", [""])[0]
        metadata.year = int(audio.get("\xa9day", ["0"])[0] or 0)
        metadata.genre = audio.get("\xa9gen", [""])[0]
        
        return metadata
    
    async def write_metadata(
        self,
        file: Path,
        metadata: TrackMetadata,
        embed_cover: bool = True
    ) -> bool:
        """写入元数据到音频文件"""
        if not file.exists():
            logger.error(f"File not found: {file}")
            return False
        
        try:
            if file.suffix.lower() == ".mp3":
                return await self._write_mp3_metadata(file, metadata, embed_cover)
            elif file.suffix.lower() == ".flac":
                return await self._write_flac_metadata(file, metadata, embed_cover)
            elif file.suffix.lower() in [".m4a", ".mp4"]:
                return await self._write_m4a_metadata(file, metadata, embed_cover)
            else:
                logger.warning(f"Unsupported format for metadata: {file.suffix}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to write metadata to {file}: {e}")
            return False
    
    async def _write_mp3_metadata(
        self,
        file: Path,
        metadata: TrackMetadata,
        embed_cover: bool
    ) -> bool:
        """写入 MP3 元数据"""
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, APIC
        from mutagen.mp3 import MP3
        
        try:
            audio = MP3(file)
            
            if audio.tags is None:
                audio.add_tags()
            
            if metadata.title:
                audio.tags.add(TIT2(encoding=3, text=metadata.title))
            if metadata.artist:
                audio.tags.add(TPE1(encoding=3, text=metadata.artist))
            if metadata.album:
                audio.tags.add(TALB(encoding=3, text=metadata.album))
            if metadata.year:
                audio.tags.add(TDRC(encoding=3, text=str(metadata.year)))
            if metadata.genre:
                audio.tags.add(TCON(encoding=3, text=metadata.genre))
            
            # 嵌入封面
            if embed_cover and metadata.cover_art:
                audio.tags.add(APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,  # 封面
                    desc="Cover",
                    data=metadata.cover_art
                ))
            
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to write MP3 metadata: {e}")
            return False
    
    async def _write_flac_metadata(
        self,
        file: Path,
        metadata: TrackMetadata,
        embed_cover: bool
    ) -> bool:
        """写入 FLAC 元数据"""
        from mutagen.flac import FLAC
        
        try:
            audio = FLAC(file)
            
            if metadata.title:
                audio["title"] = metadata.title
            if metadata.artist:
                audio["artist"] = metadata.artist
            if metadata.album:
                audio["album"] = metadata.album
            if metadata.year:
                audio["date"] = str(metadata.year)
            if metadata.genre:
                audio["genre"] = metadata.genre
            
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to write FLAC metadata: {e}")
            return False
    
    async def _write_m4a_metadata(
        self,
        file: Path,
        metadata: TrackMetadata,
        embed_cover: bool
    ) -> bool:
        """写入 M4A 元数据"""
        from mutagen.mp4 import MP4
        
        try:
            audio = MP4(file)
            
            if metadata.title:
                audio["\xa9nam"] = metadata.title
            if metadata.artist:
                audio["\xa9ART"] = metadata.artist
            if metadata.album:
                audio["\xa9alb"] = metadata.album
            if metadata.year:
                audio["\xa9day"] = str(metadata.year)
            if metadata.genre:
                audio["\xa9gen"] = metadata.genre
            
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to write M4A metadata: {e}")
            return False
    
    async def download_cover(self, url: str) -> Optional[bytes]:
        """下载封面图片"""
        if not url:
            return None
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10)
                if response.status_code == 200:
                    return response.content
                    
        except Exception as e:
            logger.error(f"Failed to download cover from {url}: {e}")
        
        return None
