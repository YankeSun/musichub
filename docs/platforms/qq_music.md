# QQ 音乐平台配置指南

## 📋 概述

QQ 音乐插件支持从腾讯 QQ 音乐平台搜索和下载音乐，包括 VIP 和数字专辑内容。

---

## 🔑 获取 QQ 音乐 API 凭证

### 方式 1: Cookie 认证（推荐）

这是最简单的方式，适合个人使用。

#### 步骤 1: 登录 QQ 音乐网页版

1. 访问 [QQ 音乐网页版](https://y.qq.com/)
2. 使用微信或 QQ 扫码登录

#### 步骤 2: 获取 Cookie

**Chrome/Edge 浏览器：**

1. 按 `F12` 打开开发者工具
2. 切换到 **Network**（网络）标签
3. 刷新页面
4. 点击任意请求
5. 在 **Request Headers** 中找到 `Cookie` 字段
6. 复制整个 Cookie 值

![Chrome 开发者工具](https://developers.google.com/web/tools/chrome-devtools/network.png)

**或使用浏览器扩展：**

- Chrome: "EditThisCookie" 扩展
- Firefox: "Cookie Quick Manager" 扩展

#### 步骤 3: 提取关键 Cookie

需要的 Cookie 字段：
- `uin` - 用户 ID
- `qqmusic_key` - 认证密钥
- `qqmusic_fromtag` - 来源标识

---

### 方式 2: MusicHub 自动获取

```bash
musichub auth qqmusic
```

这将：
1. 生成二维码
2. 使用微信/QQ 扫码登录
3. 自动获取并保存 Cookie

---

## ⚙️ 配置 MusicHub

### 方法 1: CLI 配置

```bash
# 使用 Cookie 字符串
musichub config set sources.qq_music.cookie "完整的 Cookie 字符串"
musichub config set sources.qq_music.enabled true
musichub config set sources.qq_music.quality "hires"

# 或使用自动认证
musichub auth qqmusic
```

### 方法 2: 编辑配置文件

编辑 `~/.config/musichub/config.toml`：

```toml
[sources.qq_music]
enabled = true
cookie = "uin=xxx; qqmusic_key=xxx; qqmusic_fromtag=xxx; ..."
quality = "hires"  # standard, high, hires, master
vip_enabled = true  # 是否使用 VIP 权限
```

---

## 🎵 使用示例

```bash
# 搜索音乐
musichub search "周杰伦" --source qq_music

# 下载单曲
musichub download "https://y.qq.com/n/ryqq/songDetail/xxx" --format mp3

# 下载专辑（高解析）
musichub download "https://y.qq.com/n/ryqq/albumDetail/xxx" --quality hires

# 下载歌单
musichub download "https://y.qq.com/n/ryqq/playlist/xxx" --concurrency 5

# 下载数字专辑
musichub download "xxx" --vip  # 需要 VIP 权限
```

---

## 📊 音质等级

| 等级 | 名称 | 格式 | 比特率 | 要求 |
|-----|------|------|--------|------|
| standard | 标准 | MP3 | 128 kbps | 免费 |
| high | 高品质 | MP3 | 320 kbps | 免费 |
| hires | 无损 | FLAC | 16-bit/44.1kHz | VIP |
| master | 母带 | FLAC | 24-bit/96kHz+ | VIP+ |

---

## 🎼 特殊功能

### VIP 内容访问

如果你有 QQ 音乐 VIP：

```toml
[sources.qq_music]
vip_enabled = true
vip_cookie = "特殊的 VIP Cookie"  # 可选
```

### 数字专辑

购买后的数字专辑可以下载：

```bash
musichub download "xxx" --purchased  # 下载已购买的专辑
```

### 歌词下载

QQ 音乐提供歌词（包括翻译）：

```bash
musichub download "xxx" --lyrics  # 下载歌词
musichub download "xxx" --lyrics --translate  # 下载歌词 + 翻译
```

---

## 📱 移动端 Cookie

如需更高权限，可从手机 APP 获取 Cookie：

### Android (需要 root)

1. 安装抓包工具（如 HttpCanary）
2. 捕获 QQ 音乐 APP 请求
3. 提取 Cookie

### iOS (需要越狱或使用代理)

1. 使用 Charles/Proxyman 抓包
2. 配置 HTTPS 解密
3. 捕获 QQ 音乐请求

---

## ⚠️ 注意事项

1. **Cookie 有效期**: Cookie 会过期，需定期更新
2. **VIP 限制**: 部分歌曲仅限 VIP 下载
3. **数字专辑**: 需单独购买
4. **区域限制**: 部分内容仅限中国大陆
5. **账号安全**: 不要分享你的 Cookie

---

## 🐛 常见问题

### Q: Cookie 过期了怎么办？
A: 重新运行 `musichub auth qqmusic` 或手动更新 Cookie。

### Q: VIP 歌曲无法下载
A: 确认 VIP 状态有效，Cookie 包含 VIP 权限。

### Q: 下载速度慢
A: 尝试减少并发数：`--concurrency 2`

### Q: 某些歌曲显示"版权限制"
A: 这是平台版权限制，无法绕过。

---

## 🔧 高级配置

### 使用代理

```toml
[sources.qq_music]
proxy = "http://127.0.0.1:7890"  # 代理地址
```

### 自定义 User-Agent

```toml
[sources.qq_music]
user_agent = "Mozilla/5.0 ..."  # 自定义 UA
```

### 下载限制

```toml
[sources.qq_music]
daily_limit = 100  # 每日下载限制
rate_limit = 10    # 每分钟请求数
```

---

## 🔗 相关资源

- [QQ 音乐网页版](https://y.qq.com/)
- [QQ 音乐 VIP 说明](https://y.qq.com/vip/)
- [数字专辑](https://y.qq.com/album/digital/)

---

*最后更新：2026-03-10*
