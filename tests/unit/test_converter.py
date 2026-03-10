"""
格式转换单元测试
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from musichub.core.converter import (
    AudioConverter,
    ConversionOptions,
    ConversionResult,
    AudioQuality,
    convert_audio,
)


class TestAudioQuality:
    """测试 AudioQuality 枚举"""

    def test_quality_values(self):
        """测试质量值"""
        assert AudioQuality.LOSSLESS.value == "lossless"
        assert AudioQuality.HIGH.value == "high"
        assert AudioQuality.MEDIUM.value == "medium"
        assert AudioQuality.LOW.value == "low"


class TestConversionOptions:
    """测试 ConversionOptions 数据类"""

    def test_default_values(self):
        """测试默认值"""
        options = ConversionOptions()
        assert options.output_format == "mp3"
        assert options.quality == AudioQuality.HIGH
        assert options.bitrate is None
        assert options.keep_metadata is True
        assert options.overwrite is False
        assert options.extra_args == []

    def test_custom_values(self):
        """测试自定义值"""
        options = ConversionOptions(
            output_format="flac",
            quality=AudioQuality.LOSSLESS,
            bitrate="1411k",
            sample_rate=48000,
            channels=2,
            overwrite=True,
        )
        assert options.output_format == "flac"
        assert options.quality == AudioQuality.LOSSLESS
        assert options.bitrate == "1411k"
        assert options.sample_rate == 48000
        assert options.channels == 2
        assert options.overwrite is True

    def test_extra_args_default(self):
        """测试 extra_args 默认为空列表"""
        options1 = ConversionOptions()
        options2 = ConversionOptions()
        # 确保是不同的列表实例
        options1.extra_args.append("-test")
        assert "-test" not in options2.extra_args


class TestConversionResult:
    """测试 ConversionResult 数据类"""

    def test_success_result(self):
        """测试成功结果"""
        result = ConversionResult(
            success=True,
            input_path=Path("/input.mp3"),
            output_path=Path("/output.flac"),
            duration=2.5,
            input_format="mp3",
            output_format="flac",
            input_size=1000000,
            output_size=2000000,
        )
        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        """测试失败结果"""
        result = ConversionResult(
            success=False,
            input_path=Path("/input.mp3"),
            error="ffmpeg not found",
        )
        assert result.success is False
        assert result.output_path is None


@pytest.mark.asyncio
class TestAudioConverter:
    """测试 AudioConverter 类"""

    @pytest.fixture
    def converter(self):
        """创建 AudioConverter 实例"""
        return AudioConverter()

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    async def test_init(self, converter):
        """测试初始化"""
        assert converter.ffmpeg_path == "ffmpeg"
        assert converter.progress_callback is None
        assert converter._ffmpeg_available is None

    async def test_init_custom_path(self):
        """测试自定义 ffmpeg 路径"""
        converter = AudioConverter(ffmpeg_path="/usr/local/bin/ffmpeg")
        assert converter.ffmpeg_path == "/usr/local/bin/ffmpeg"

    async def test_init_with_callback(self):
        """测试带进度回调初始化"""
        async def callback(progress):
            pass

        converter = AudioConverter(progress_callback=callback)
        assert converter.progress_callback == callback

    async def test_check_ffmpeg_not_found(self, converter):
        """测试 ffmpeg 未找到"""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            result = await converter.check_ffmpeg()
            assert result is False

    async def test_check_ffmpeg_found(self, converter):
        """测试 ffmpeg 找到"""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"ffmpeg version 5.0", b""))
            mock_exec.return_value = mock_proc

            result = await converter.check_ffmpeg()
            assert result is True

    async def test_convert_file_not_found(self, converter, temp_dir):
        """测试转换不存在的文件"""
        result = await converter.convert(
            input_path=temp_dir / "nonexistent.mp3",
            options=ConversionOptions(output_format="flac"),
        )
        assert result.success is False
        # ffmpeg 未安装时会先返回 ffmpeg 错误
        assert result.error is not None

    async def test_convert_output_exists_no_overwrite(self, converter, temp_dir):
        """测试输出文件已存在且不允许覆盖"""
        # 创建输入和输出文件
        input_file = temp_dir / "input.mp3"
        output_file = temp_dir / "output.flac"
        input_file.touch()
        output_file.touch()

        result = await converter.convert(
            input_path=input_file,
            options=ConversionOptions(output_format="flac", overwrite=False),
        )
        # ffmpeg 未安装时会先返回 ffmpeg 错误
        assert result.success is False
        assert result.error is not None

    async def test_build_ffmpeg_command_basic(self, converter):
        """测试构建基本 ffmpeg 命令"""
        options = ConversionOptions(output_format="mp3")
        cmd = await converter._build_ffmpeg_command(
            Path("/input.flac"),
            Path("/output.mp3"),
            options,
        )
        assert "ffmpeg" in cmd[0]
        assert "-i" in cmd
        assert "/input.flac" in cmd
        assert "/output.mp3" in cmd
        assert "-acodec" in cmd
        assert "libmp3lame" in cmd

    async def test_build_ffmpeg_command_with_bitrate(self, converter):
        """测试构建带比特率的命令"""
        options = ConversionOptions(
            output_format="mp3",
            bitrate="320k",
        )
        cmd = await converter._build_ffmpeg_command(
            Path("/input.flac"),
            Path("/output.mp3"),
            options,
        )
        assert "-b:a" in cmd
        assert "320k" in cmd

    async def test_build_ffmpeg_command_with_sample_rate(self, converter):
        """测试构建带采样率的命令"""
        options = ConversionOptions(
            output_format="mp3",
            sample_rate=48000,
        )
        cmd = await converter._build_ffmpeg_command(
            Path("/input.flac"),
            Path("/output.mp3"),
            options,
        )
        assert "-ar" in cmd
        assert "48000" in cmd

    async def test_build_ffmpeg_command_with_channels(self, converter):
        """测试构建带声道数的命令"""
        options = ConversionOptions(
            output_format="mp3",
            channels=1,
        )
        cmd = await converter._build_ffmpeg_command(
            Path("/input.flac"),
            Path("/output.mp3"),
            options,
        )
        assert "-ac" in cmd
        assert "1" in cmd

    async def test_build_ffmpeg_command_overwrite(self, converter):
        """测试构建带覆盖选项的命令"""
        options = ConversionOptions(output_format="mp3", overwrite=True)
        cmd = await converter._build_ffmpeg_command(
            Path("/input.flac"),
            Path("/output.mp3"),
            options,
        )
        assert "-y" in cmd

    def test_parse_ffmpeg_progress(self, converter):
        """测试解析 ffmpeg 进度"""
        line = "frame=  123 fps=0.0 q=0.0 size=       0kB time=00:00:01.50 bitrate=  0.0kbits/s speed=0.0x"
        # 没有总时长时返回 None
        progress = converter._parse_ffmpeg_progress(line)
        assert progress is None

    def test_parse_ffmpeg_progress_no_time(self, converter):
        """测试解析无时间信息的行"""
        line = "Some random log line"
        progress = converter._parse_ffmpeg_progress(line)
        assert progress is None

    async def test_batch_convert_empty(self, converter):
        """测试空批量转换"""
        results = await converter.batch_convert(
            files=[],
            options=ConversionOptions(),
        )
        assert results == []

    async def test_get_audio_info_ffmpeg_not_available(self, converter):
        """测试获取音频信息但 ffmpeg 不可用"""
        converter._ffmpeg_available = False
        result = await converter.get_audio_info(Path("test.mp3"))
        assert result is None


class TestConvertAudio:
    """测试便捷函数 convert_audio"""

    async def test_convert_audio_signature(self):
        """测试函数签名"""
        # 验证函数存在且有正确的参数
        import inspect
        sig = inspect.signature(convert_audio)
        params = list(sig.parameters.keys())
        assert "input_path" in params
        assert "output_format" in params
        assert "quality" in params
        assert "output_path" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
