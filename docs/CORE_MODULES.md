# MusicHub 核心模块

本文档描述 MusicHub 的核心功能模块实现。

## 📦 模块概览

### 1. 下载引擎 (`core/downloader.py`)

异步下载引擎，支持：
- ✅ 并发下载控制（信号量限制）
- ✅ 断点续传（Range 请求）
- ✅ 进度回调（异步回调函数）
- ✅ 自动重试（指数退避）
- ✅ 任务管理（暂停/取消）

**核心类：**
- `Downloader` - 主下载器类
- `DownloadTask` - 下载任务数据类
- `DownloadResult` - 下载结果数据类
- `DownloadStatus` - 下载状态枚举

**使用示例：**
```python
from musichub.core import Downloader, DownloadTask

async with Downloader(max_concurrency=5) as downloader:
    result = await downloader.download(
        url="https://example.com/song.mp3",
        dest_path=Path("/music/song.mp3"),
    )
    
    if result.success:
        print(f"Downloaded: {result.file_path}")
```

**批量下载：**
```python
downloads = [
    {"url": "http://a.com/1.mp3", "dest_path": "/music/1.mp3"},
    {"url": "http://b.com/2.mp3", "dest_path": "/music/2.mp3"},
]
results = await downloader.batch_download(downloads)
```

---

### 2. 元数据管理 (`core/metadata.py`)

音频元数据读写，支持：
- ✅ ID3 标签写入（MP3）
- ✅ 专辑封面嵌入（MP3/FLAC/M4A）
- ✅ 歌词同步（USLT 标签）
- ✅ 多格式支持（MP3/FLAC/M4A/OGG）

**核心类：**
- `MetadataManager` - 元数据管理器
- `TrackMetadata` - 音轨元数据数据类
- `AudioFormat` - 音频格式枚举

**使用示例：**
```python
from musichub.core import MetadataManager, TrackMetadata

manager = MetadataManager()

# 读取元数据
metadata = manager.read_metadata("/music/song.mp3")
print(f"{metadata.artist} - {metadata.title}")

# 写入元数据
metadata = TrackMetadata(
    title="Song Title",
    artist="Artist Name",
    album="Album Name",
    year=2024,
    track_number=1,
    genre="Rock",
)
manager.write_metadata("/music/song.mp3", metadata)

# 嵌入封面
manager.embed_cover("/music/song.mp3", "/covers/album.jpg")

# 同步歌词
manager.sync_lyrics_from_file("/music/song.mp3", "/lyrics/song.lrc")
```

**依赖：** `pip install mutagen`

---

### 3. 格式转换 (`core/converter.py`)

音频格式转换，支持：
- ✅ FLAC ↔ MP3 ↔ ALAC ↔ M4A ↔ OGG ↔ WAV
- ✅ 质量预设（Lossless/High/Medium/Low）
- ✅ 自定义参数（比特率、采样率、声道）
- ✅ 进度回调
- ✅ 批量转换

**核心类：**
- `AudioConverter` - 音频转换器
- `ConversionOptions` - 转换选项
- `ConversionResult` - 转换结果
- `AudioQuality` - 质量预设枚举

**使用示例：**
```python
from musichub.core import AudioConverter, ConversionOptions, AudioQuality

converter = AudioConverter()

# 检查 ffmpeg
if not await converter.check_ffmpeg():
    print("ffmpeg not found!")
    exit(1)

# 转换文件
options = ConversionOptions(
    output_format="mp3",
    quality=AudioQuality.HIGH,  # 320kbps
)
result = await converter.convert(
    input_path=Path("/music/song.flac"),
    options=options,
)

if result.success:
    print(f"Converted: {result.output_path}")
    print(f"Duration: {result.duration:.2f}s")
```

**便捷函数：**
```python
from musichub.core import convert_audio, AudioQuality

result = await convert_audio(
    input_path=Path("/music/song.flac"),
    output_format="mp3",
    quality=AudioQuality.HIGH,
)
```

**依赖：** `ffmpeg` 必须安装在系统中

---

## 🧪 测试

运行所有测试：
```bash
cd /root/.openclaw/workspace/projects/musichub
python run_tests.py
```

运行特定模块测试：
```bash
python run_tests.py downloader  # 下载器测试
python run_tests.py metadata    # 元数据测试
python run_tests.py converter   # 转换器测试
```

使用 pytest 直接运行：
```bash
pytest tests/unit -v
```

---

## 📋 依赖安装

```bash
# 核心依赖
pip install aiohttp mutagen

# 开发依赖
pip install pytest pytest-asyncio
```

---

## 🏗️ 架构设计

### 下载引擎架构

```
┌─────────────────────────────────────────┐
│              Downloader                  │
├─────────────────────────────────────────┤
│  - max_concurrency (Semaphore)          │
│  - progress_callback                    │
│  - _tasks: Dict[str, DownloadTask]      │
│  - _cancel_flags: Dict[str, Event]      │
└─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │ Task 1 │  │ Task 2 │  │ Task 3 │
   └────────┘  └────────┘  └────────┘
```

### 元数据管理架构

```
┌─────────────────────────────────────────┐
│           MetadataManager                │
├─────────────────────────────────────────┤
│  read_metadata(file) → TrackMetadata    │
│  write_metadata(file, metadata) → bool  │
│  embed_cover(file, cover) → bool        │
│  embed_lyrics(file, lyrics) → bool      │
└─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │  MP3   │  │  FLAC  │  │  M4A   │
   │ ID3    │  │ Vorbis │  │  MP4   │
   └────────┘  └────────┘  └────────┘
```

### 格式转换架构

```
┌─────────────────────────────────────────┐
│            AudioConverter                │
├─────────────────────────────────────────┤
│  convert(input, options) → Result       │
│  batch_convert(files, options)          │
│  get_audio_info(file) → Dict            │
└─────────────────────────────────────────┘
                    │
                    ▼
         ┌───────────────────┐
         │    ffmpeg CLI     │
         │  (subprocess)     │
         └───────────────────┘
```

---

## ⚠️ 注意事项

1. **异步上下文**：`Downloader` 必须使用 `async with` 上下文管理器
2. **ffmpeg 依赖**：转换器需要系统安装 ffmpeg
3. **mutagen 依赖**：元数据管理需要安装 mutagen 库
4. **文件权限**：确保对目标目录有写入权限
5. **并发限制**：批量操作时注意并发数限制，避免资源耗尽

---

*最后更新：2026-03-10*
