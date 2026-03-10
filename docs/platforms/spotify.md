# Spotify 平台配置指南

## 📋 概述

Spotify 插件允许你从 Spotify 平台搜索和下载音乐。本指南将帮助你完成 API 配置。

---

## 🔑 获取 Spotify API 凭证

### 步骤 1: 创建 Spotify Developer 账号

1. 访问 [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. 使用你的 Spotify 账号登录（没有则需注册）
3. 同意开发者协议

### 步骤 2: 创建应用

1. 点击 **"Create App"** 按钮
2. 填写应用信息：
   - **App name**: MusicHub（或你喜欢的名称）
   - **App description**: 个人音乐下载工具
   - **Redirect URI**: `http://localhost:8888/callback`
   - **Website**: （可选）
   - 勾选同意条款
3. 点击 **"Create"**

### 步骤 3: 获取凭证

创建成功后，你将看到：
- **Client ID**: 一串字符（如 `1a2b3c4d5e6f...`）
- **Client Secret**: 点击 "Show Client Secret" 查看

![Spotify Dashboard 示例](https://developer.spotify.com/assets/images/dashboard.png)

### 步骤 4: 配置重定向 URI

1. 点击 **"Edit Settings"**
2. 添加 Redirect URI: `http://localhost:8888/callback`
3. 点击 **"Save"**

---

## ⚙️ 配置 MusicHub

### 方法 1: 使用 CLI 配置

```bash
musichub config set sources.spotify.client_id "你的 Client ID"
musichub config set sources.spotify.client_secret "你的 Client Secret"
musichub config set sources.spotify.enabled true
```

### 方法 2: 编辑配置文件

编辑 `~/.config/musichub/config.toml`：

```toml
[sources.spotify]
enabled = true
client_id = "你的 Client ID"
client_secret = "你的 Client Secret"
quality = "high"  # low, normal, high, very_high
```

---

## 🔐 认证流程

Spotify 使用 OAuth 2.0 认证。首次使用时：

```bash
musichub auth spotify
```

这将：
1. 在浏览器中打开 Spotify 授权页面
2. 你需登录并授权 MusicHub
3. 自动获取并保存访问令牌

令牌会自动刷新，无需手动干预。

---

## 🎵 使用示例

```bash
# 搜索音乐
musichub search "Taylor Swift" --source spotify

# 下载单曲
musichub download "https://open.spotify.com/track/xxx" --format mp3

# 下载整张专辑
musichub download "https://open.spotify.com/album/xxx" --format flac

# 下载播放列表
musichub download "https://open.spotify.com/playlist/xxx" --concurrency 5
```

---

## 📊 音质说明

| 质量等级 | 比特率 | 格式 |
|---------|--------|------|
| low | 96 kbps | Ogg Vorbis |
| normal | 160 kbps | Ogg Vorbis |
| high | 320 kbps | Ogg Vorbis |
| very_high | 320 kbps | Ogg Vorbis |

> ⚠️ **注意**: Spotify 不提供无损格式（FLAC）。如需无损音质，请使用 Tidal 或 Apple Music。

---

## ⚠️ 注意事项

1. **API 限制**: 免费账号有 API 调用限制
2. **版权**: 仅下载你有权使用的音乐
3. **Premium 账号**: 某些功能需要 Spotify Premium 订阅
4. **区域限制**: 部分内容可能因地区不可用

---

## 🐛 常见问题

### Q: 认证失败怎么办？
A: 检查 Client ID 和 Secret 是否正确，确保 Redirect URI 配置一致。

### Q: 下载的歌曲有 DRM 吗？
A: 通过 API 获取的音频流可能有 DRM 保护。请遵守 Spotify 服务条款。

### Q: 如何刷新令牌？
A: 令牌会自动刷新。如需手动刷新：`musichub auth spotify --refresh`

---

## 🔗 相关资源

- [Spotify API 文档](https://developer.spotify.com/documentation/web-api)
- [Spotify Web API Console](https://developer.spotify.com/console/)
- [OAuth 2.0 指南](https://developer.spotify.com/documentation/general/guides/authorization-guide)

---

*最后更新：2026-03-10*
