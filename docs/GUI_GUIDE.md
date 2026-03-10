# MusicHub GUI 使用指南

## 📖 概述

MusicHub GUI 是一款基于 PyQt6 构建的现代化音乐下载管理器，提供直观的图形界面，让用户轻松搜索、下载和管理音乐。

## ✨ 功能特性

### 🔍 搜索功能
- 多平台搜索（网易云音乐、QQ 音乐、酷狗音乐）
- 实时搜索结果显示
- 歌曲详情展示（标题、艺术家、专辑、时长）
- 一键下载

### 📥 下载管理
- 下载队列管理
- 实时进度显示
- 暂停/继续/取消控制
- 批量下载支持
- 并发数控制

### 🎵 播放列表
- 本地音乐播放
- 播放列表管理
- 播放控制（上一首、播放/暂停、下一首）
- 当前播放显示

### ⚙️ 设置
- 下载路径配置
- 音质选择（128k ~ 320k, lossless）
- 输出格式（MP3, FLAC, M4A, WAV, OGG）
- ID3 元数据写入
- 界面主题设置

## 🚀 快速开始

### 安装依赖

```bash
pip install PyQt6
```

### 启动 GUI

```bash
# 方式 1: 使用启动脚本
python run_gui.py

# 方式 2: 直接运行模块
python -m gui.app

# 方式 3: 从 Python 代码导入
from gui import main
main()
```

## 📸 界面预览

### 主界面
- **搜索标签页**: 输入关键词，选择平台，点击搜索
- **下载标签页**: 查看下载进度，管理下载任务
- **播放列表标签页**: 管理播放列表，播放本地音乐
- **设置标签页**: 配置下载和界面选项

### 暗色主题
采用现代暗色设计，减少眼睛疲劳，提升视觉体验。

## 🎯 使用流程

### 1. 搜索音乐
1. 切换到"搜索"标签页
2. 在搜索框输入歌曲名、歌手或专辑
3. 选择音乐平台（或"全部"）
4. 点击"搜索"按钮

### 2. 下载歌曲
1. 在搜索结果中找到想要的歌曲
2. 点击歌曲右侧的"下载"按钮
3. 自动切换到"下载"标签页
4. 查看下载进度

### 3. 管理下载
- **暂停/继续**: 点击下载项的"暂停"按钮
- **取消**: 点击"取消"按钮
- **批量操作**: 使用"全部开始"/"全部暂停"按钮
- **清理**: 点击"清空已完成"移除已完成任务

### 4. 播放音乐
1. 下载完成的歌曲自动添加到播放列表
2. 切换到"播放列表"标签页
3. 点击歌曲播放
4. 使用播放控制按钮

### 5. 配置设置
1. 切换到"设置"标签页
2. 配置下载路径、音质、格式等
3. 设置自动保存

## 🛠️ 技术架构

```
gui/
├── __init__.py      # 模块导出
├── app.py           # 主界面和核心逻辑
├── widgets.py       # 自定义组件
├── styles.py        # 样式表
└── resources/       # 资源文件
    ├── icons/
    └── images/
```

### 核心组件

- **MainWindow**: 主窗口，包含标签页和状态栏
- **SearchTab**: 搜索界面
- **DownloadTab**: 下载管理界面
- **PlaylistTab**: 播放列表界面
- **SettingsTab**: 设置界面

### 自定义组件

- **SearchResultItem**: 搜索结果项
- **DownloadQueueItem**: 下载队列项
- **PlaylistItem**: 播放列表项
- **SettingsOption**: 设置选项
- **LoadingSpinner**: 加载动画
- **EmptyStateWidget**: 空状态提示

## 🎨 样式定制

GUI 使用 Qt 样式表（QSS），类似 CSS。修改 `gui/styles.py` 中的 `STYLESHEET` 变量即可定制外观。

### 主题颜色

```python
# 主色调
primary_color = "#0078D4"  # 蓝色
background_color = "#1E1E1E"  # 深色背景
card_color = "#252525"  # 卡片背景
```

### 添加自定义样式

```css
/* 示例：修改按钮样式 */
QPushButton#customButton {
    background-color: #FF5722;
    color: #FFFFFF;
    border-radius: 8px;
    padding: 10px 20px;
}
```

## 📝 开发指南

### 添加新功能

1. 在 `widgets.py` 中创建新组件
2. 在 `app.py` 中添加到对应标签页
3. 在 `styles.py` 中添加样式

### 集成后端

```python
from musichub.core.engine import DownloadEngine

engine = DownloadEngine()
results = await engine.search("歌曲名")
```

### 异步处理

使用 QThread 处理耗时操作，避免阻塞 UI：

```python
class MyWorker(QThread):
    result_ready = pyqtSignal(object)
    
    def run(self):
        # 耗时操作
        result = do_something()
        self.result_ready.emit(result)
```

## ⚠️ 注意事项

1. **依赖项**: 确保安装 PyQt6
2. **异步兼容**: MusicHub 核心使用 asyncio，GUI 使用 QThread 桥接
3. **文件路径**: 下载路径需要有写权限
4. **系统托盘**: 某些系统可能不支持系统托盘

## 🐛 故障排除

### GUI 无法启动
```bash
# 检查 PyQt6 安装
pip show PyQt6

# 重新安装
pip install --force-reinstall PyQt6
```

### 搜索无结果
- 检查网络连接
- 确认音源插件可用
- 查看日志输出

### 下载失败
- 检查下载路径权限
- 确认磁盘空间充足
- 查看错误信息

## 📄 许可证

与 MusicHub 主项目相同。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
