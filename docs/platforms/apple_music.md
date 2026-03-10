# Apple Music 平台配置指南

## 📋 概述

Apple Music 插件支持从 Apple Music 目录搜索和下载音乐，包括无损和空间音频内容。

---

## 🔑 获取 Apple Music API 凭证

### 前置要求

- Apple ID（需要订阅 Apple Music）
- macOS 或 iTunes（用于生成开发者令牌）

### 步骤 1: 加入 Apple Developer Program

1. 访问 [Apple Developer](https://developer.apple.com/)
2. 登录你的 Apple ID
3. 如果未加入，需注册开发者账号（免费）

### 步骤 2: 创建 MusicKit 密钥

1. 登录 [App Store Connect](https://appstoreconnect.apple.com/)
2. 进入 **Users and Access** → **Keys**
3. 点击 **"+"** 创建新密钥
4. 填写信息：
   - **Name**: MusicHub Key
   - **Access**: Apple Music API
5. 下载生成的 `.p8` 文件（只下载一次！）

![App Store Connect Keys](https://apple.com/assets/app-store-connect-keys.png)

### 步骤 3: 获取必要信息

记录以下信息：
- **Key ID**: 密钥 ID（如 `ABCD123456`）
- **Issuer ID**: 发行者 ID（UUID 格式）
- **Team ID**: 团队 ID（10 位字符）
- **私钥文件**: 下载的 `.p8` 文件内容

---

## ⚙️ 配置 MusicHub

### 方法 1: CLI 配置

```bash
musichub config set sources.apple_music.key_id "你的 Key ID"
musichub config set sources.apple_music.issuer_id "你的 Issuer ID"
musichub config set sources.apple_music.team_id "你的 Team ID"
musichub config set sources.apple_music.private_key_path "~/.config/musichub/AppleMusicKey.p8"
musichub config set sources.apple_music.enabled true
```

### 方法 2: 编辑配置文件

1. 将 `.p8` 文件复制到配置目录：
```bash
cp ~/Downloads/AppleMusicKey_*.p8 ~/.config/musichub/AppleMusicKey.p8
```

2. 编辑 `~/.config/musichub/config.toml`：

```toml
[sources.apple_music]
enabled = true
key_id = "你的 Key ID"
issuer_id = "你的 Issuer ID"
team_id = "你的 Team ID"
private_key_path = "~/.config/musichub/AppleMusicKey.p8"
quality = "lossless"  # standard, high, lossless, hi_res_lossless
country = "US"  # 你的国家代码
```

---

## 🔐 认证说明

Apple Music 使用 JWT 令牌认证。MusicHub 会自动：
1. 使用私钥生成 JWT 令牌
2. 令牌有效期 6 个月
3. 过期前自动刷新

无需手动认证流程。

---

## 🎵 使用示例

```bash
# 搜索音乐
musichub search "Billie Eilish" --source apple_music

# 下载单曲
musichub download "https://music.apple.com/us/album/xxx/xxx?i=xxx" --format m4a

# 下载专辑（无损）
musichub download "https://music.apple.com/album/xxx" --quality lossless

# 下载播放列表
musichub download "https://music.apple.com/playlist/xxx" --concurrency 5

# 下载空间音频
musichub download "xxx" --atmos  # Dolby Atmos
```

---

## 📊 音质等级

| 等级 | 格式 | 规格 | 订阅要求 |
|-----|------|------|---------|
| standard | AAC | 256 kbps | Apple Music |
| high | AAC | 256 kbps | Apple Music |
| lossless | ALAC | 16-bit/44.1kHz | Apple Music |
| hi_res_lossless | ALAC | 24-bit/192kHz | Apple Music |

> 💡 **注意**: Hi-Res Lossless 需要外接 DAC 才能充分发挥音质优势。

---

## 🎼 特殊功能

### 空间音频 (Spatial Audio)

Apple Music 提供 Dolby Atmos 空间音频：

```toml
[sources.apple_music]
prefer_atmos = true  # 优先下载 Atmos 版本
```

### 歌词支持

Apple Music 提供同步歌词：

```bash
musichub download "xxx" --lyrics  # 下载同步歌词
```

### 音乐视频

部分曲目包含音乐视频：

```bash
musichub download "xxx" --include-video  # 下载 MV（如果可用）
```

---

## 🌍 国家/地区代码

Apple Music 内容因地区而异。常用国家代码：

| 代码 | 地区 |
|-----|------|
| US | 美国 |
| CN | 中国大陆 |
| HK | 中国香港 |
| TW | 中国台湾 |
| JP | 日本 |
| GB | 英国 |

在配置中设置：
```toml
country = "CN"
```

---

## ⚠️ 注意事项

1. **订阅要求**: 需要有效的 Apple Music 订阅
2. **DRM 保护**: 部分内容有 DRM 保护
3. **区域限制**: 内容可用性因地区而异
4. **私钥安全**: 妥善保管 `.p8` 私钥文件

---

## 🐛 常见问题

### Q: 403 Forbidden 错误
A: 检查 Key ID、Issuer ID、Team ID 是否正确，确认私钥文件路径。

### Q: 令牌过期
A: MusicHub 会自动刷新。如需手动刷新：`musichub auth apple_music --refresh`

### Q: 某些歌曲无法下载
A: 可能是区域限制。尝试更改 `country` 配置或使用代理。

### Q: 无损音质没有生效
A: 确认订阅支持无损，并检查播放设备是否支持。

---

## 🔗 相关资源

- [Apple Music API 文档](https://developer.apple.com/documentation/applemusicapi)
- [MusicKit 指南](https://developer.apple.com/documentation/musickit)
- [Apple Music 音质说明](https://support.apple.com/zh-cn/HT212124)

---

*最后更新：2026-03-10*
