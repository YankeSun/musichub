# 🎵 MusicHub

**插件化聚合音乐下载器**

---

## ✨ 特性

- 🔌 **插件化架构** - 轻松扩展新音源、下载器、导出格式
- ⚡ **高并发下载** - 支持批量下载，可配置并发数
- 📦 **多格式支持** - MP3、FLAC、M4A 等格式
- 🎯 **CLI + GUI** - 命令行和图形界面双支持
- 📝 **元数据写入** - 自动嵌入封面、歌词、专辑信息

---

## 🚀 快速开始

### 安装

```bash
# 从源码安装
pip install -e .

# 或使用 uv
uv pip install -e .
```

### 基本使用

```bash
# 搜索音乐
musichub search "周杰伦 七里香"

# 下载音乐
musichub download "周杰伦 七里香" --format mp3

# 批量下载（高并发）
musichub download "Taylor Swift" --concurrency 10

# 查看配置
musichub config --show
```

---

## 📁 项目结构

```
musichub/
├── src/musichub/
│   ├── core/           # 核心引擎
│   ├── plugins/        # 插件系统
│   ├── cli/            # 命令行接口
│   ├── gui/            # 图形界面（预留）
│   └── utils/          # 工具函数
├── tests/              # 测试
├── docs/               # 文档
└── examples/           # 示例
```

---

## 🔌 插件开发

查看 [插件开发指南](docs/plugins.md) 了解如何开发自定义插件。

### 示例：添加新音源

```python
from musichub.plugins.sources.base import SourcePluginBase

class MySource(SourcePluginBase):
    async def search(self, query: str, limit: int = 20) -> list[TrackInfo]:
        # 实现搜索逻辑
        pass
```

---

## ⚙️ 配置

配置文件位于 `~/.config/musichub/config.toml`：

```toml
download_path = "~/Music/MusicHub"
output_format = "mp3"
max_concurrent_downloads = 5
default_source = "netease"

[sources.netease]
enabled = true
quality = "high"

[downloader]
max_retries = 3
timeout = 30
```

---

## 🧪 测试

```bash
# 运行测试
pytest

# 带覆盖率
pytest --cov=src/musichub
```

---

## 📄 许可证

MIT License

---

## 🙏 贡献

欢迎提交 Issue 和 Pull Request！

---

*MusicHub - 让音乐触手可及* 🎶
