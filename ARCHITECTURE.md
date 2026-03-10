# MusicHub 架构文档

## 🎵 项目概述

MusicHub 是一个插件化的聚合音乐下载器，支持多平台音源、并发下载、多种导出格式。

**核心设计原则**：
- 插件化架构，易扩展
- 高并发性能
- 清晰的模块边界
- CLI 和 GUI 双接口

---

## 📁 项目目录结构

```
musichub/
├── pyproject.toml              # 项目配置和依赖
├── ARCHITECTURE.md             # 架构文档
├── README.md                   # 使用说明
├── src/
│   └── musichub/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── engine.py       # 下载引擎核心
│       │   ├── manager.py      # 任务管理器
│       │   ├── config.py       # 配置管理
│       │   └── events.py       # 事件系统
│       ├── plugins/
│       │   ├── __init__.py
│       │   ├── base.py         # 插件基类
│       │   ├── registry.py     # 插件注册表
│       │   ├── sources/        # 音源插件
│       │   │   ├── __init__.py
│       │   │   └── base.py     # 音源插件基类
│       │   ├── downloaders/    # 下载器插件
│       │   │   ├── __init__.py
│       │   │   └── base.py     # 下载器基类
│       │   └── exporters/      # 导出器插件
│       │       ├── __init__.py
│       │       └── base.py     # 导出器基类
│       ├── cli/
│       │   ├── __init__.py
│       │   └── main.py         # CLI 入口
│       ├── gui/
│       │   ├── __init__.py
│       │   └── app.py          # GUI 入口（预留）
│       └── utils/
│           ├── __init__.py
│           ├── logger.py       # 日志工具
│           ├── async_utils.py  # 异步工具
│           └── metadata.py     # 元数据处理
├── tests/
│   ├── __init__.py
│   ├── unit/
│   └── integration/
├── docs/
│   └── plugins.md              # 插件开发指南
└── examples/
    └── basic_usage.py
```

---

## 🔧 技术选型

### 语言
- **Python 3.10+** - 利用现代异步特性

### 核心框架/库

| 类别 | 库 | 用途 |
|------|-----|------|
| 异步 | `asyncio` | 并发下载核心 |
| HTTP | `httpx` | 异步 HTTP 客户端 |
| CLI | `typer` | 命令行接口 |
| GUI | `flet` / `nicegui` | 跨平台 GUI（预留） |
| 配置 | `pydantic` | 配置验证 |
| 日志 | `structlog` | 结构化日志 |
| 插件 | 自定义 | 基于 entry points 的插件系统 |
| 音频 | `mutagen` | 元数据编辑 |
| 并发 | `asyncio.Semaphore` | 并发控制 |

### 依赖管理
- **uv** 或 **pip** + **pyproject.toml**

---

## 🧩 核心模块设计

### 1. 下载引擎 (`core/engine.py`)

```
┌─────────────────────────────────────────────────────┐
│                   DownloadEngine                   │
├─────────────────────────────────────────────────────┤
│  - search(query, source) → SearchResults           │
│  - download(track, options) → DownloadTask         │
│  - batch_download(tracks, concurrency)             │
│  - pause/resume/cancel(task_id)                    │
└─────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   ┌──────────┐      ┌──────────┐      ┌──────────┐
   │  Source  │      │ Downloader│     │ Exporter │
   │  Plugin  │      │  Plugin   │     │  Plugin  │
   └──────────┘      └──────────┘      └──────────┘
```

**职责**：
- 协调音源搜索、下载、导出流程
- 管理并发任务
- 处理进度回调和事件

### 2. 任务管理器 (`core/manager.py`)

```python
class TaskManager:
    - 创建下载任务
    - 任务队列管理
    - 进度跟踪
    - 断点续传支持
```

### 3. 配置系统 (`core/config.py`)

```python
class Config:
    - 全局配置（并发数、下载路径、格式）
    - 音源配置（API keys、认证）
    - 用户偏好
```

### 4. 事件系统 (`core/events.py`)

```python
# 核心事件类型
- on_search_start / on_search_complete
- on_download_start / on_download_progress / on_download_complete
- on_error / on_warning
```

---

## 🔌 插件系统架构

### 插件类型

#### 1. 音源插件 (`plugins/sources/`)
负责从不同平台搜索和获取音源信息。

```python
class SourcePlugin(PluginBase):
    async def search(self, query: str) -> list[TrackInfo]
    async def get_track_info(self, track_id: str) -> TrackInfo
    async def get_stream_url(self, track_id: str) -> StreamURL
```

**示例实现**：
- `NeteaseSource` - 网易云音乐
- `QQMusicSource` - QQ 音乐
- `SpotifySource` - Spotify
- `YouTubeSource` - YouTube Music

#### 2. 下载器插件 (`plugins/downloaders/`)
负责实际的文件下载。

```python
class DownloaderPlugin(PluginBase):
    async def download(self, url: str, dest: Path) -> DownloadResult
    supports_resume: bool  # 是否支持断点续传
```

**示例实现**：
- `HTTPDownloader` - 标准 HTTP 下载
- `YTDLDownloader` - yt-dlp 封装
- `StreamDownloader` - 流媒体录制

#### 3. 导出器插件 (`plugins/exporters/`)
负责音频格式转换和元数据写入。

```python
class ExporterPlugin(PluginBase):
    async def export(self, input_file: Path, output_format: str) -> Path
    async def write_metadata(self, file: Path, metadata: TrackMetadata)
```

**示例实现**：
- `MP3Exporter` - MP3 格式
- `FLACExporter` - FLAC 格式
- `M4AExporter` - M4A 格式

### 插件注册机制

使用 Python `entry_points` 实现自动发现：

```toml
# pyproject.toml
[project.entry-points."musichub.sources"]
netease = "musichub.plugins.sources.netease:NeteaseSource"

[project.entry-points."musichub.downloaders"]
http = "musichub.plugins.downloaders.http:HTTPDownloader"

[project.entry-points."musichub.exporters"]
mp3 = "musichub.plugins.exporters.mp3:MP3Exporter"
```

### 插件生命周期

```
发现 → 加载 → 初始化 → 使用 → 卸载
   │        │         │        │
   ▼        ▼         ▼        ▼
entry   validate   configure  cleanup
points  interface
```

---

## ⚡ 并发设计

### 下载并发模型

```python
# 使用信号量控制并发数
semaphore = asyncio.Semaphore(config.max_concurrent_downloads)

async def download_with_limit(track):
    async with semaphore:
        return await engine.download(track)

# 批量下载
tasks = [download_with_limit(t) for t in tracks]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 进度追踪

```python
class ProgressTracker:
    - 每任务进度回调
    - 总体进度聚合
    - 速度计算（ETA）
    - 支持 CLI 进度条和 GUI 进度显示
```

---

## 🖥️ 接口设计

### CLI 接口 (`cli/main.py`)

```bash
# 搜索
musichub search "歌曲名" --source netease

# 下载单曲
musichub download "歌曲名" --format mp3

# 批量下载（从歌单）
musichub download --playlist <url> --concurrency 5

# 管理任务
musichub queue list
musichub queue pause <id>
```

### GUI 接口 (`gui/app.py`)

预留接口，支持：
- 搜索界面
- 下载队列管理
- 进度可视化
- 设置面板

---

## 📊 数据流

```
用户请求
    │
    ▼
┌─────────┐     ┌─────────────┐     ┌──────────────┐
│  CLI/   │────▶│  Download   │────▶│ SourcePlugin │
│  GUI    │     │   Engine    │     │  (search)    │
└─────────┘     └─────────────┘     └──────────────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │ Downloader   │
                                    │   Plugin     │
                                    └──────────────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │ Exporter     │
                                    │   Plugin     │
                                    └──────────────┘
                                           │
                                           ▼
                                      输出文件
```

---

## 🔒 安全与合规

- 不内置任何破解/绕过逻辑
- 用户需自行配置合法音源
- 支持 API 限流和重试
- 日志不包含敏感信息

---

## 📈 扩展性

### 添加新音源
1. 继承 `SourcePlugin` 基类
2. 实现 `search()`、`get_track_info()`、`get_stream_url()`
3. 在 `pyproject.toml` 注册 entry point

### 添加新格式
1. 继承 `ExporterPlugin` 基类
2. 实现 `export()`、`write_metadata()`
3. 注册 entry point

---

## 🧪 测试策略

- **单元测试**：核心逻辑、工具函数
- **集成测试**：插件接口、下载流程
- **Mock 外部依赖**：避免真实网络请求

---

*最后更新：2026-03-10*
