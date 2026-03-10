# 🎵 MusicHub

**插件化聚合音乐下载器**

---

## ✨ 特性

- 🔌 **插件化架构** - 轻松扩展新音源、下载器、导出格式
- ⚡ **高并发下载** - 支持批量下载，可配置并发数
- 📦 **多格式支持** - MP3、FLAC、M4A 等格式
- 🎯 **CLI + GUI** - 命令行和图形界面双支持
- 📝 **元数据写入** - 自动嵌入封面、歌词、专辑信息
- 🌐 **多平台支持** - Spotify、Tidal、Apple Music、QQ 音乐、网易云音乐

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

### 使用不同平台

```bash
# 从 Spotify 搜索
musichub search "Taylor Swift" --source spotify

# 从 Tidal 下载无损
musichub download "专辑链接" --source tidal --quality lossless

# 从 Apple Music 下载
musichub download "https://music.apple.com/album/xxx" --source apple_music

# 从 QQ 音乐下载
musichub download "https://y.qq.com/n/ryqq/songDetail/xxx" --source qq_music

# 从网易云音乐下载
musichub download "https://music.163.com/song?id=xxx" --source netease
```

---

## 🌐 支持的平台

| 平台 | 最高音质 | 需要订阅 | 状态 |
|-----|---------|---------|------|
| **Spotify** | 320 kbps Ogg | Premium (部分) | ✅ 稳定 |
| **Tidal** | 24-bit/192kHz FLAC | HiFi Plus | ✅ 稳定 |
| **Apple Music** | 24-bit/192kHz ALAC | Apple Music | ✅ 稳定 |
| **QQ 音乐** | 24-bit/96kHz+ FLAC | VIP+ | ✅ 稳定 |
| **网易云音乐** | 24-bit/48kHz+ FLAC | SVIP | ✅ 稳定 |

> 💡 更多平台配置详见 [平台配置指南](docs/platforms/)

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
│   ├── platforms/      # 平台配置指南
│   └── plugins.md      # 插件开发指南
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

[sources.spotify]
enabled = true
client_id = "你的 Client ID"
client_secret = "你的 Client Secret"

[sources.tidal]
enabled = true
client_id = "你的 Client ID"
client_secret = "你的 Client Secret"
quality = "HI_RES"

[sources.apple_music]
enabled = true
key_id = "你的 Key ID"
issuer_id = "你的 Issuer ID"
team_id = "你的 Team ID"
private_key_path = "~/.config/musichub/AppleMusicKey.p8"

[sources.qq_music]
enabled = true
cookie = "MUSIC_U=xxx; ..."

[downloader]
max_retries = 3
timeout = 30
```

### 平台认证

首次使用各平台需要认证：

```bash
# Spotify (OAuth)
musichub auth spotify

# Tidal (OAuth)
musichub auth tidal

# Apple Music (JWT - 自动处理)
# 配置好私钥后无需手动认证

# QQ 音乐 (扫码)
musichub auth qqmusic

# 网易云音乐 (扫码)
musichub auth netease
```

详细配置见 [平台配置指南](docs/platforms/)

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
