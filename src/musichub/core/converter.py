"""
格式转换 - FLAC ↔ MP3 ↔ ALAC 等格式转换
使用 ffmpeg 作为后端
"""

import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable, Awaitable
from enum import Enum

logger = logging.getLogger(__name__)


class AudioQuality(Enum):
    """音频质量预设"""
    LOSSLESS = "lossless"  # 无损
    HIGH = "high"  # 高质量 (320kbps MP3 / 256kbps AAC)
    MEDIUM = "medium"  # 中等质量 (192kbps MP3 / 128kbps AAC)
    LOW = "low"  # 低质量 (128kbps MP3 / 96kbps AAC)


@dataclass
class ConversionOptions:
    """转换选项"""
    output_format: str = "mp3"  # 输出格式
    quality: AudioQuality = AudioQuality.HIGH
    bitrate: Optional[str] = None  # 自定义比特率 (如 "320k")
    sample_rate: Optional[int] = None  # 采样率 (如 44100)
    channels: Optional[int] = None  # 声道数 (1=mono, 2=stereo)
    keep_metadata: bool = True  # 保留元数据
    overwrite: bool = False  # 覆盖输出文件
    extra_args: List[str] = None  # 额外 ffmpeg 参数

    def __post_init__(self):
        if self.extra_args is None:
            self.extra_args = []


@dataclass
class ConversionResult:
    """转换结果"""
    success: bool
    input_path: Path
    output_path: Optional[Path] = None
    error: Optional[str] = None
    duration: float = 0.0  # 转换耗时 (秒)
    input_format: str = ""
    output_format: str = ""
    input_size: int = 0
    output_size: int = 0


class AudioConverter:
    """
    音频格式转换器
    
    支持格式：
    - MP3 (LAME 编码器)
    - FLAC (无损)
    - ALAC/M4A (AAC 编码器)
    - OGG Vorbis
    - WAV
    - 以及其他 ffmpeg 支持的格式
    
    依赖：ffmpeg 必须安装在系统中
    """

    # 格式到 ffmpeg 编码器的映射
    ENCODER_MAP = {
        "mp3": "libmp3lame",
        "flac": "flac",
        "m4a": "aac",
        "aac": "aac",
        "alac": "alac",
        "ogg": "libvorbis",
        "wav": "pcm_s16le",
        "opus": "libopus",
    }

    # 质量预设到比特率的映射
    BITRATE_MAP = {
        AudioQuality.LOSSLESS: None,  # 无损格式不需要比特率
        AudioQuality.HIGH: "320k",
        AudioQuality.MEDIUM: "192k",
        AudioQuality.LOW: "128k",
    }

    # 格式到扩展名的映射
    EXTENSION_MAP = {
        "mp3": ".mp3",
        "flac": ".flac",
        "m4a": ".m4a",
        "aac": ".m4a",
        "alac": ".m4a",
        "ogg": ".ogg",
        "wav": ".wav",
        "opus": ".opus",
    }

    def __init__(
        self,
        ffmpeg_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float], Awaitable[None]]] = None,
    ):
        """
        初始化转换器

        Args:
            ffmpeg_path: ffmpeg 可执行文件路径 (默认从 PATH 查找)
            progress_callback: 进度回调函数 (async, 接收 0.0-1.0 进度值)
        """
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"
        self.progress_callback = progress_callback
        self._ffmpeg_available: Optional[bool] = None

    async def check_ffmpeg(self) -> bool:
        """检查 ffmpeg 是否可用"""
        if self._ffmpeg_available is not None:
            return self._ffmpeg_available

        try:
            proc = await asyncio.create_subprocess_exec(
                self.ffmpeg_path, "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            self._ffmpeg_available = proc.returncode == 0
            if self._ffmpeg_available:
                logger.info(f"ffmpeg found: {self.ffmpeg_path}")
            else:
                logger.error(f"ffmpeg not found or not executable: {self.ffmpeg_path}")
            return self._ffmpeg_available
        except FileNotFoundError:
            self._ffmpeg_available = False
            logger.error(f"ffmpeg not found in PATH: {self.ffmpeg_path}")
            return False

    async def convert(
        self,
        input_path: Path,
        options: Optional[ConversionOptions] = None,
        output_path: Optional[Path] = None,
    ) -> ConversionResult:
        """
        转换音频文件格式

        Args:
            input_path: 输入文件路径
            options: 转换选项
            output_path: 输出文件路径 (可选，默认根据输入路径生成)

        Returns:
            ConversionResult: 转换结果
        """
        import time

        options = options or ConversionOptions()
        input_path = Path(input_path)

        # 检查 ffmpeg
        if not await self.check_ffmpeg():
            return ConversionResult(
                success=False,
                input_path=input_path,
                error="ffmpeg is not installed or not in PATH",
            )

        if not input_path.exists():
            return ConversionResult(
                success=False,
                input_path=input_path,
                error=f"Input file not found: {input_path}",
            )

        # 确定输出路径
        if output_path is None:
            ext = self.EXTENSION_MAP.get(
                options.output_format.lower(),
                f".{options.output_format.lower()}"
            )
            output_path = input_path.with_suffix(ext)

        output_path = Path(output_path)

        # 检查输出文件是否已存在
        if output_path.exists() and not options.overwrite:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                error=f"Output file already exists: {output_path}",
            )

        # 创建输出目录
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 构建 ffmpeg 命令
        cmd = await self._build_ffmpeg_command(
            input_path, output_path, options
        )

        logger.info(f"Converting: {input_path.name} -> {output_path.name}")
        logger.debug(f"Command: {' '.join(cmd)}")

        start_time = time.time()

        try:
            # 执行 ffmpeg
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 读取 stderr 以获取进度信息
            stderr_lines = []
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="ignore").strip()
                stderr_lines.append(line_str)

                # 解析进度
                if self.progress_callback:
                    progress = self._parse_ffmpeg_progress(line_str)
                    if progress is not None:
                        try:
                            await self.progress_callback(progress)
                        except Exception as e:
                            logger.warning(f"Progress callback error: {e}")

            await proc.wait()

            duration = time.time() - start_time

            if proc.returncode != 0:
                error_msg = "\n".join(stderr_lines[-5:])  # 最后 5 行错误
                logger.error(f"Conversion failed: {error_msg}")
                return ConversionResult(
                    success=False,
                    input_path=input_path,
                    output_path=output_path if output_path.exists() else None,
                    error=f"ffmpeg error (code {proc.returncode}): {error_msg}",
                    duration=duration,
                )

            # 获取文件大小
            input_size = input_path.stat().st_size
            output_size = output_path.stat().st_size if output_path.exists() else 0

            logger.info(
                f"Conversion completed in {duration:.2f}s: "
                f"{input_size / 1024 / 1024:.2f} MB -> {output_size / 1024 / 1024:.2f} MB"
            )

            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                duration=duration,
                input_format=input_path.suffix[1:],
                output_format=options.output_format.lower(),
                input_size=input_size,
                output_size=output_size,
            )

        except Exception as e:
            logger.exception(f"Conversion error: {e}")
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path if output_path.exists() else None,
                error=str(e),
            )

    async def _build_ffmpeg_command(
        self,
        input_path: Path,
        output_path: Path,
        options: ConversionOptions,
    ) -> List[str]:
        """构建 ffmpeg 命令行"""
        cmd = [self.ffmpeg_path]

        # 输入文件
        cmd.extend(["-i", str(input_path)])

        # 编码器
        encoder = self.ENCODER_MAP.get(options.output_format.lower())
        if encoder:
            cmd.extend(["-acodec", encoder])

        # 比特率
        bitrate = options.bitrate or self.BITRATE_MAP.get(options.quality)
        if bitrate and options.output_format.lower() not in ("flac", "wav", "alac"):
            cmd.extend(["-b:a", bitrate])

        # 采样率
        if options.sample_rate:
            cmd.extend(["-ar", str(options.sample_rate)])

        # 声道数
        if options.channels:
            cmd.extend(["-ac", str(options.channels)])

        # 额外参数
        cmd.extend(options.extra_args)

        # 输出选项
        if options.output_format.lower() == "mp3":
            cmd.extend(["-id3v2_version", "3"])  # 兼容 ID3 标签

        # 覆盖输出文件
        if options.overwrite:
            cmd.append("-y")
        else:
            cmd.append("-n")

        # 输出文件
        cmd.append(str(output_path))

        return cmd

    def _parse_ffmpeg_progress(self, line: str) -> Optional[float]:
        """
        解析 ffmpeg 进度输出

        ffmpeg 输出格式示例：
        frame=  123 fps=0.0 q=0.0 size=       0kB time=00:00:01.23 bitrate=  0.0kbits/s speed=0.0x

        Returns:
            进度值 (0.0-1.0) 或 None
        """
        # 查找 time= 字段
        if "time=" not in line:
            return None

        try:
            # 提取 time 值
            time_part = line.split("time=")[1].split()[0]
            # 解析时间格式 HH:MM:SS.ss
            parts = time_part.split(":")
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                current_time = hours * 3600 + minutes * 60 + seconds

                # 如果有总时长信息，计算进度
                if "duration=" in line:
                    duration_part = line.split("duration=")[1].split()[0]
                    dur_parts = duration_part.split(":")
                    if len(dur_parts) == 3:
                        total = int(dur_parts[0]) * 3600 + int(dur_parts[1]) * 60 + float(dur_parts[2])
                        if total > 0:
                            return min(current_time / total, 1.0)

                # 否则返回当前时间（用于回调显示）
                return None

        except (ValueError, IndexError):
            pass

        return None

    async def batch_convert(
        self,
        files: List[Path],
        options: ConversionOptions,
        output_dir: Optional[Path] = None,
        concurrency: int = 3,
    ) -> List[ConversionResult]:
        """
        批量转换文件

        Args:
            files: 输入文件列表
            options: 转换选项
            output_dir: 输出目录 (可选)
            concurrency: 并发数

        Returns:
            List[ConversionResult]: 转换结果列表
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def convert_with_limit(file_path: Path) -> ConversionResult:
            async with semaphore:
                output_path = None
                if output_dir:
                    ext = self.EXTENSION_MAP.get(
                        options.output_format.lower(),
                        f".{options.output_format.lower()}"
                    )
                    output_path = output_dir / (file_path.stem + ext)

                return await self.convert(file_path, options, output_path)

        tasks = [convert_with_limit(f) for f in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.exception(f"Batch convert item {i} failed: {result}")
                processed.append(ConversionResult(
                    success=False,
                    input_path=files[i],
                    error=str(result),
                ))
            else:
                processed.append(result)

        return processed

    async def get_audio_info(self, file_path: Path) -> Optional[Dict]:
        """
        获取音频文件信息

        Returns:
            包含格式、时长、比特率等信息的字典，或 None
        """
        if not await self.check_ffmpeg():
            return None

        cmd = [
            self.ffmpeg_path,
            "-i", str(file_path),
            "-f", "null",
            "-",
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            info = {}
            stderr_text = stderr.decode("utf-8", errors="ignore")

            # 解析时长
            if "Duration:" in stderr_text:
                duration_part = stderr_text.split("Duration:")[1].split(",")[0].strip()
                info["duration"] = duration_part

            # 解析比特率
            if "bitrate:" in stderr_text:
                bitrate_part = stderr_text.split("bitrate:")[1].split(",")[0].strip()
                info["bitrate"] = bitrate_part

            # 解析采样率
            if "kHz" in stderr_text or "Hz" in stderr_text:
                for part in stderr_text.split(","):
                    if "Hz" in part:
                        info["sample_rate"] = part.strip()
                        break

            # 解析编码器
            if "Audio:" in stderr_text:
                audio_part = stderr_text.split("Audio:")[1].split(",")[0].strip()
                info["codec"] = audio_part

            return info

        except Exception as e:
            logger.exception(f"Error getting audio info: {e}")
            return None


# 便捷函数
async def convert_audio(
    input_path: Path,
    output_format: str = "mp3",
    quality: AudioQuality = AudioQuality.HIGH,
    output_path: Optional[Path] = None,
) -> ConversionResult:
    """
    便捷函数：转换音频文件

    Args:
        input_path: 输入文件路径
        output_format: 输出格式 (mp3, flac, m4a, etc.)
        quality: 质量预设
        output_path: 输出路径 (可选)

    Returns:
        ConversionResult: 转换结果
    """
    converter = AudioConverter()
    options = ConversionOptions(
        output_format=output_format,
        quality=quality,
    )
    return await converter.convert(input_path, options, output_path)
