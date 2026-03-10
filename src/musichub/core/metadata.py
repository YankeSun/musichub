"""
元数据管理 - ID3 标签写入、专辑封面嵌入、歌词同步
"""

import struct
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Union
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3, ID3NoHeaderError, APIC, USLT, TIT2, TPE1, TALB, TDRC, TCON, TRCK, COMM
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.oggvorbis import OggVorbis
    from mutagen.easyid3 import EasyID3
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    logger.warning("mutagen not installed. Install with: pip install mutagen")


class AudioFormat(Enum):
    """音频格式枚举"""
    MP3 = "mp3"
    FLAC = "flac"
    M4A = "m4a"
    ALAC = "alac"
    OGG = "ogg"
    WAV = "wav"
    UNKNOWN = "unknown"


@dataclass
class TrackMetadata:
    """音轨元数据数据类"""
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    year: Optional[int] = None
    genre: str = ""
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    duration: Optional[float] = None  # 秒
    lyrics: Optional[str] = None
    comment: str = ""
    composer: str = ""
    cover_path: Optional[Path] = None  # 封面图片路径
    cover_data: Optional[bytes] = None  # 封面二进制数据
    cover_mime: str = "image/jpeg"  # 封面 MIME 类型
    isrc: Optional[str] = None  # ISRC 编码
    extra: Dict[str, str] = field(default_factory=dict)  # 额外标签

    def __post_init__(self):
        """数据验证"""
        if self.year is not None and not isinstance(self.year, int):
            try:
                self.year = int(self.year)
            except (ValueError, TypeError):
                self.year = None

        if self.track_number is not None and not isinstance(self.track_number, int):
            try:
                # 处理 "5/12" 格式
                track_str = str(self.track_number).split("/")[0]
                self.track_number = int(track_str)
            except (ValueError, TypeError):
                self.track_number = None


class MetadataManager:
    """
    音频元数据管理器
    
    支持：
    - ID3 标签读写 (MP3)
    - FLAC Vorbis 注释
    - MP4/M4A 元数据
    - 专辑封面嵌入
    - 同步歌词
    """

    # 音频格式扩展名映射
    FORMAT_MAP = {
        ".mp3": AudioFormat.MP3,
        ".flac": AudioFormat.FLAC,
        ".m4a": AudioFormat.M4A,
        ".alac": AudioFormat.ALAC,
        ".ogg": AudioFormat.OGG,
        ".wav": AudioFormat.WAV,
    }

    def __init__(self):
        if not MUTAGEN_AVAILABLE:
            raise ImportError(
                "mutagen library is required. Install with: pip install mutagen"
            )

    @classmethod
    def detect_format(cls, file_path: Union[str, Path]) -> AudioFormat:
        """检测音频文件格式"""
        path = Path(file_path)
        suffix = path.suffix.lower()
        return cls.FORMAT_MAP.get(suffix, AudioFormat.UNKNOWN)

    def read_metadata(self, file_path: Union[str, Path]) -> TrackMetadata:
        """
        读取音频文件元数据

        Args:
            file_path: 音频文件路径

        Returns:
            TrackMetadata: 元数据对象
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        audio = MutagenFile(str(path), easy=True)
        if audio is None:
            raise ValueError(f"Unsupported audio format: {file_path}")

        metadata = TrackMetadata()

        # 读取通用标签
        try:
            metadata.title = audio.get("title", [""])[0]
            metadata.artist = audio.get("artist", [""])[0]
            metadata.album = audio.get("album", [""])[0]
            metadata.album_artist = audio.get("albumartist", [""])[0]
            metadata.genre = audio.get("genre", [""])[0]
            metadata.comment = audio.get("comment", [""])[0]
            metadata.composer = audio.get("composer", [""])[0]

            # 年份
            date = audio.get("date", [""])[0]
            if date:
                metadata.year = int(str(date)[:4])

            # 音轨号
            track = audio.get("tracknumber", [""])[0]
            if track:
                metadata.track_number = int(str(track).split("/")[0])

            # 碟片号
            disc = audio.get("discnumber", [""])[0]
            if disc:
                metadata.disc_number = int(str(disc).split("/")[0])

            # 时长
            if audio.info and hasattr(audio.info, "length"):
                metadata.duration = audio.info.length

        except Exception as e:
            logger.warning(f"Error reading metadata from {file_path}: {e}")

        # 读取封面
        metadata = self._read_cover(path, metadata)

        # 读取歌词 (ID3)
        if path.suffix.lower() == ".mp3":
            metadata = self._read_lyrics_mp3(path, metadata)

        return metadata

    def _read_cover(self, path: Path, metadata: TrackMetadata) -> TrackMetadata:
        """读取专辑封面"""
        try:
            audio = MutagenFile(str(path))
            if audio is None:
                return metadata

            # MP3
            if path.suffix.lower() == ".mp3" and isinstance(audio, MP3):
                if audio.tags and "APIC" in audio.tags:
                    for tag in audio.tags.getall("APIC"):
                        metadata.cover_data = tag.data
                        metadata.cover_mime = tag.mime
                        break

            # FLAC
            elif path.suffix.lower() == ".flac" and isinstance(audio, FLAC):
                if audio.pictures:
                    pic = audio.pictures[0]
                    metadata.cover_data = pic.data
                    metadata.cover_mime = pic.mime

            # MP4/M4A
            elif path.suffix.lower() in (".m4a", ".mp4") and isinstance(audio, MP4):
                if audio.tags and "covr" in audio.tags:
                    cover = audio.tags["covr"][0]
                    metadata.cover_data = bytes(cover)
                    metadata.cover_mime = "image/jpeg"

        except Exception as e:
            logger.debug(f"Could not read cover art: {e}")

        return metadata

    def _read_lyrics_mp3(self, path: Path, metadata: TrackMetadata) -> TrackMetadata:
        """读取 MP3 歌词"""
        try:
            audio = MP3(str(path), ID3=ID3)
            if audio.tags:
                for tag in audio.tags.getall("USLT"):
                    if tag.lang == "eng" or not tag.lang:
                        metadata.lyrics = tag.text
                        break
        except Exception as e:
            logger.debug(f"Could not read lyrics: {e}")
        return metadata

    def write_metadata(
        self,
        file_path: Union[str, Path],
        metadata: TrackMetadata,
        overwrite: bool = True,
    ) -> bool:
        """
        写入音频文件元数据

        Args:
            file_path: 音频文件路径
            metadata: 元数据对象
            overwrite: 是否覆盖现有标签

        Returns:
            bool: 是否成功
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        fmt = self.detect_format(path)

        try:
            if fmt == AudioFormat.MP3:
                return self._write_mp3(path, metadata, overwrite)
            elif fmt == AudioFormat.FLAC:
                return self._write_flac(path, metadata, overwrite)
            elif fmt in (AudioFormat.M4A, AudioFormat.ALAC):
                return self._write_mp4(path, metadata, overwrite)
            elif fmt == AudioFormat.OGG:
                return self._write_ogg(path, metadata, overwrite)
            else:
                logger.warning(f"Unsupported format for writing: {fmt}")
                return False

        except Exception as e:
            logger.exception(f"Error writing metadata to {file_path}: {e}")
            return False

    def _write_mp3(self, path: Path, metadata: TrackMetadata, overwrite: bool) -> bool:
        """写入 MP3 ID3 标签"""
        try:
            # 尝试加载现有 ID3 标签
            try:
                audio = EasyID3(str(path))
            except ID3NoHeaderError:
                # 无 ID3 标签，创建新的
                audio = MP3(str(path))
                audio.add_tags()
                audio = EasyID3(str(path))

            # 写入基本标签
            if metadata.title:
                audio["title"] = metadata.title
            if metadata.artist:
                audio["artist"] = metadata.artist
            if metadata.album:
                audio["album"] = metadata.album
            if metadata.album_artist:
                audio["albumartist"] = metadata.album_artist
            if metadata.genre:
                audio["genre"] = metadata.genre
            if metadata.year:
                audio["date"] = str(metadata.year)
            if metadata.track_number:
                audio["tracknumber"] = str(metadata.track_number)
            if metadata.disc_number:
                audio["discnumber"] = str(metadata.disc_number)
            if metadata.composer:
                audio["composer"] = metadata.composer
            if metadata.comment:
                audio["comment"] = metadata.comment

            audio.save()

            # 写入封面和歌词 (需要低级 ID3 操作)
            self._write_mp3_cover_and_lyrics(path, metadata)

            logger.info(f"Written MP3 metadata: {path.name}")
            return True

        except Exception as e:
            logger.exception(f"Error writing MP3 metadata: {e}")
            return False

    def _write_mp3_cover_and_lyrics(self, path: Path, metadata: TrackMetadata):
        """写入 MP3 封面和歌词"""
        try:
            audio = ID3(str(path))

            # 写入封面
            if metadata.cover_data:
                audio.delall("APIC")  # 删除旧封面
                audio["APIC"] = APIC(
                    encoding=3,
                    mime=metadata.cover_mime,
                    type=3,  # 封面
                    desc="Cover",
                    data=metadata.cover_data,
                )
            elif metadata.cover_path:
                # 从文件读取封面
                cover_data = Path(metadata.cover_path).read_bytes()
                mime = "image/jpeg" if metadata.cover_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                audio.delall("APIC")
                audio["APIC"] = APIC(
                    encoding=3,
                    mime=mime,
                    type=3,
                    desc="Cover",
                    data=cover_data,
                )

            # 写入歌词
            if metadata.lyrics:
                audio.delall("USLT")
                audio["USLT"] = USLT(
                    encoding=3,
                    lang="eng",
                    desc="Lyrics",
                    text=metadata.lyrics,
                )

            audio.save()

        except Exception as e:
            logger.warning(f"Error writing MP3 cover/lyrics: {e}")

    def _write_flac(self, path: Path, metadata: TrackMetadata, overwrite: bool) -> bool:
        """写入 FLAC 元数据"""
        try:
            audio = FLAC(str(path))

            # 写入基本标签
            if metadata.title:
                audio["title"] = metadata.title
            if metadata.artist:
                audio["artist"] = metadata.artist
            if metadata.album:
                audio["album"] = metadata.album
            if metadata.album_artist:
                audio["albumartist"] = metadata.album_artist
            if metadata.genre:
                audio["genre"] = metadata.genre
            if metadata.year:
                audio["date"] = str(metadata.year)
            if metadata.track_number:
                audio["tracknumber"] = str(metadata.track_number)
            if metadata.disc_number:
                audio["discnumber"] = str(metadata.disc_number)
            if metadata.composer:
                audio["composer"] = metadata.composer
            if metadata.lyrics:
                audio["lyrics"] = metadata.lyrics

            # 写入封面
            if metadata.cover_data:
                audio.clear_pictures()
                from mutagen.flac import Picture
                pic = Picture()
                pic.data = metadata.cover_data
                pic.mime = metadata.cover_mime
                pic.type = 3  # 封面
                pic.desc = "Cover"
                audio.add_picture(pic)
            elif metadata.cover_path:
                audio.clear_pictures()
                from mutagen.flac import Picture
                pic = Picture()
                pic.data = Path(metadata.cover_path).read_bytes()
                pic.mime = "image/jpeg" if metadata.cover_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                pic.type = 3
                pic.desc = "Cover"
                audio.add_picture(pic)

            audio.save()
            logger.info(f"Written FLAC metadata: {path.name}")
            return True

        except Exception as e:
            logger.exception(f"Error writing FLAC metadata: {e}")
            return False

    def _write_mp4(self, path: Path, metadata: TrackMetadata, overwrite: bool) -> bool:
        """写入 MP4/M4A 元数据"""
        try:
            audio = MP4(str(path))

            # MP4 标签映射
            if metadata.title:
                audio["\xa9nam"] = metadata.title
            if metadata.artist:
                audio["\xa9ART"] = metadata.artist
            if metadata.album:
                audio["\xa9alb"] = metadata.album
            if metadata.album_artist:
                audio["aART"] = metadata.album_artist
            if metadata.genre:
                audio["\xa9gen"] = metadata.genre
            if metadata.year:
                audio["\xa9day"] = str(metadata.year)
            if metadata.track_number:
                audio["trkn"] = [(metadata.track_number, 0)]
            if metadata.disc_number:
                audio["disk"] = [(metadata.disc_number, 0)]
            if metadata.composer:
                audio["\xa9wrt"] = metadata.composer
            if metadata.lyrics:
                audio["\xa9lyr"] = metadata.lyrics

            # 写入封面
            if metadata.cover_data:
                audio["covr"] = [MP4Cover(metadata.cover_data)]
            elif metadata.cover_path:
                audio["covr"] = [MP4Cover(Path(metadata.cover_path).read_bytes())]

            audio.save()
            logger.info(f"Written MP4 metadata: {path.name}")
            return True

        except Exception as e:
            logger.exception(f"Error writing MP4 metadata: {e}")
            return False

    def _write_ogg(self, path: Path, metadata: TrackMetadata, overwrite: bool) -> bool:
        """写入 OGG Vorbis 元数据"""
        try:
            audio = OggVorbis(str(path))

            if metadata.title:
                audio["title"] = metadata.title
            if metadata.artist:
                audio["artist"] = metadata.artist
            if metadata.album:
                audio["album"] = metadata.album
            if metadata.album_artist:
                audio["albumartist"] = metadata.album_artist
            if metadata.genre:
                audio["genre"] = metadata.genre
            if metadata.year:
                audio["date"] = str(metadata.year)
            if metadata.track_number:
                audio["tracknumber"] = str(metadata.track_number)
            if metadata.lyrics:
                audio["lyrics"] = metadata.lyrics

            audio.save()
            logger.info(f"Written OGG metadata: {path.name}")
            return True

        except Exception as e:
            logger.exception(f"Error writing OGG metadata: {e}")
            return False

    def embed_cover(
        self,
        file_path: Union[str, Path],
        cover_path: Union[str, Path],
        mime_type: str = "image/jpeg",
    ) -> bool:
        """
        嵌入专辑封面

        Args:
            file_path: 音频文件路径
            cover_path: 封面图片路径
            mime_type: 封面 MIME 类型

        Returns:
            bool: 是否成功
        """
        metadata = self.read_metadata(file_path)
        metadata.cover_path = Path(cover_path)
        metadata.cover_mime = mime_type
        return self.write_metadata(file_path, metadata)

    def embed_lyrics(
        self,
        file_path: Union[str, Path],
        lyrics: str,
    ) -> bool:
        """
        嵌入歌词

        Args:
            file_path: 音频文件路径
            lyrics: 歌词文本

        Returns:
            bool: 是否成功
        """
        metadata = self.read_metadata(file_path)
        metadata.lyrics = lyrics
        return self.write_metadata(file_path, metadata)

    def sync_lyrics_from_file(
        self,
        audio_path: Union[str, Path],
        lyrics_path: Optional[Union[str, Path]] = None,
    ) -> bool:
        """
        从外部文件同步歌词到音频文件

        Args:
            audio_path: 音频文件路径
            lyrics_path: 歌词文件路径 (可选，默认查找同名 .lrc 文件)

        Returns:
            bool: 是否成功
        """
        audio_path = Path(audio_path)

        if lyrics_path is None:
            # 查找同名 .lrc 文件
            lyrics_path = audio_path.with_suffix(".lrc")

        lyrics_path = Path(lyrics_path)
        if not lyrics_path.exists():
            logger.warning(f"Lyrics file not found: {lyrics_path}")
            return False

        try:
            lyrics = lyrics_path.read_text(encoding="utf-8")
            return self.embed_lyrics(audio_path, lyrics)
        except Exception as e:
            logger.exception(f"Error syncing lyrics: {e}")
            return False
