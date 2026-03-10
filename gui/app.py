"""
MusicHub GUI 主界面
基于 PyQt6 的现代音乐下载管理器
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QTabWidget,
    QProgressBar, QStatusBar, QToolBar, QFrame, QScrollArea,
    QSplitter, QSizePolicy, QSpacerItem, QMessageBox, QFileDialog,
    QSystemTrayIcon, QMenu, QAction, QSlider, QGroupBox, QCheckBox,
    QSpinBox, QDialog, QDialogButtonBox, QListWidget, QListWidgetItem,
    QStackedWidget, QGridLayout
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QObject, QUrl, QSettings,
    QStandardPaths
)
from PyQt6.QtGui import (
    QIcon, QFont, QAction, QPalette, QColor, QPixmap, QPainter,
    QLinearGradient, QBrush
)

from .styles import STYLESHEET
from .widgets import (
    SearchResultItem, DownloadQueueItem, PlaylistItem,
    SettingsOption, LoadingSpinner, EmptyStateWidget
)


# 尝试导入 musichub 核心模块
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from musichub.core.engine import DownloadEngine
    from musichub.core.config import Config
    from musichub.core.types import TrackInfo, TaskStatus
    MUSIC_HUB_AVAILABLE = True
except ImportError:
    MUSIC_HUB_AVAILABLE = False
    print("Warning: MusicHub core not available. Running in demo mode.")


class SearchWorker(QThread):
    """搜索工作线程"""
    search_complete = pyqtSignal(list)  # 搜索结果列表
    search_error = pyqtSignal(str)  # 错误信息
    
    def __init__(self, engine, query: str, source: str = "all"):
        super().__init__()
        self.engine = engine
        self.query = query
        self.source = source
    
    def run(self):
        try:
            if MUSIC_HUB_AVAILABLE and self.engine:
                # 异步搜索需要在事件循环中运行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self.engine.search(self.query, self.source if self.source != "all" else None)
                    )
                    tracks = [
                        {
                            'id': t.id,
                            'title': t.title,
                            'artist': t.artist,
                            'album': t.album or '',
                            'duration': t.duration or 0,
                            'source': t.source,
                            'cover_url': t.cover_url or '',
                        }
                        for t in result.tracks
                    ]
                    self.search_complete.emit(tracks)
                finally:
                    loop.close()
            else:
                # Demo 模式：模拟搜索结果
                import time
                time.sleep(1)  # 模拟网络延迟
                demo_results = [
                    {
                        'id': f'demo_{i}',
                        'title': f'示例歌曲 {i+1}',
                        'artist': '示例歌手',
                        'album': '示例专辑',
                        'duration': 180 + i * 10,
                        'source': self.source if self.source != "all" else 'netease',
                        'cover_url': '',
                    }
                    for i in range(5)
                ]
                self.search_complete.emit(demo_results)
        except Exception as e:
            self.search_error.emit(str(e))


class DownloadWorker(QThread):
    """下载工作线程"""
    download_started = pyqtSignal(str)  # task_id
    download_progress = pyqtSignal(str, float, str)  # task_id, progress, status
    download_complete = pyqtSignal(str, str)  # task_id, file_path
    download_error = pyqtSignal(str, str)  # task_id, error_message
    
    def __init__(self, engine, track: dict, output_path: Path):
        super().__init__()
        self.engine = engine
        self.track = track
        self.output_path = output_path
        self.task_id = None
    
    def run(self):
        try:
            import uuid
            self.task_id = str(uuid.uuid4())[:8]
            self.download_started.emit(self.task_id)
            
            if MUSIC_HUB_AVAILABLE and self.engine:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # 创建 TrackInfo 对象
                    track_info = TrackInfo(
                        id=self.track['id'],
                        title=self.track['title'],
                        artist=self.track['artist'],
                        album=self.track.get('album'),
                        duration=self.track.get('duration'),
                        source=self.track.get('source', 'unknown'),
                    )
                    
                    # 模拟下载进度
                    for progress in range(0, 101, 10):
                        import time
                        time.sleep(0.2)
                        self.download_progress.emit(
                            self.task_id,
                            progress / 100.0,
                            "downloading"
                        )
                    
                    # 创建输出文件
                    self.output_path.parent.mkdir(parents=True, exist_ok=True)
                    self.output_path.touch()
                    
                    self.download_complete.emit(self.task_id, str(self.output_path))
                finally:
                    loop.close()
            else:
                # Demo 模式：模拟下载
                for progress in range(0, 101, 10):
                    import time
                    time.sleep(0.3)
                    self.download_progress.emit(
                        self.task_id,
                        progress / 100.0,
                        "downloading"
                    )
                
                self.output_path.parent.mkdir(parents=True, exist_ok=True)
                self.output_path.touch()
                self.download_complete.emit(self.task_id, str(self.output_path))
                
        except Exception as e:
            self.download_error.emit(self.task_id or "unknown", str(e))


class MusicPlayer:
    """简易音乐播放器"""
    
    def __init__(self):
        self.current_track = None
        self.is_playing = False
        self.position = 0
        self.duration = 0
    
    def load(self, file_path: str):
        """加载音乐文件"""
        self.current_track = file_path
        self.position = 0
        # 实际实现需要集成音频播放库如 pygame 或 vlc
    
    def play(self):
        """播放"""
        self.is_playing = True
    
    def pause(self):
        """暂停"""
        self.is_playing = False
    
    def stop(self):
        """停止"""
        self.is_playing = False
        self.position = 0
    
    def seek(self, position: int):
        """跳转到指定位置（秒）"""
        self.position = position


class SearchTab(QWidget):
    """搜索标签页"""
    
    download_requested = pyqtSignal(dict)  # track_info
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_style()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 搜索区域
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索歌曲、歌手或专辑...")
        self.search_input.setFont(QFont("Segoe UI", 14))
        self.search_input.setFixedHeight(44)
        self.search_input.returnPressed.connect(self.on_search_clicked)
        search_layout.addWidget(self.search_input, 1)
        
        # 平台选择
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["全部", "网易云音乐", "QQ 音乐", "酷狗音乐"])
        self.platform_combo.setFixedHeight(44)
        self.platform_combo.setFixedWidth(150)
        search_layout.addWidget(self.platform_combo)
        
        # 搜索按钮
        self.search_btn = QPushButton("搜索")
        self.search_btn.setObjectName("primaryButton")
        self.search_btn.setFixedHeight(44)
        self.search_btn.setFixedWidth(100)
        self.search_btn.clicked.connect(self.on_search_clicked)
        search_layout.addWidget(self.search_btn)
        
        layout.addLayout(search_layout)
        
        # 结果数量标签
        self.result_count_label = QLabel("")
        self.result_count_label.setStyleSheet("color: #808080; font-size: 12px;")
        layout.addWidget(self.result_count_label)
        
        # 搜索结果列表
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(10)
        self.results_layout.addStretch()
        
        self.results_scroll.setWidget(self.results_container)
        self.results_scroll.setMinimumHeight(400)
        layout.addWidget(self.results_scroll, 1)
        
        # 空状态
        self.empty_state = EmptyStateWidget(
            message="输入关键词开始搜索",
            icon="🔍"
        )
        layout.addWidget(self.empty_state)
        
        # 加载动画
        self.loading_spinner = LoadingSpinner()
        layout.addWidget(self.loading_spinner)
        
        # 存储搜索结果
        self.search_results = []
    
    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #252525;
            }
        """)
    
    def on_search_clicked(self):
        query = self.search_input.text().strip()
        if not query:
            return
        
        # 清空之前的结果
        self.clear_results()
        
        # 显示加载动画
        self.loading_spinner.show_loading()
        self.empty_state.hide()
        
        # 获取平台
        platform_map = {
            "全部": "all",
            "网易云音乐": "netease",
            "QQ 音乐": "qqmusic",
            "酷狗音乐": "kugou"
        }
        source = platform_map.get(self.platform_combo.currentText(), "all")
        
        # 启动搜索线程
        if MUSIC_HUB_AVAILABLE:
            engine = DownloadEngine()
        else:
            engine = None
        
        self.search_worker = SearchWorker(engine, query, source)
        self.search_worker.search_complete.connect(self.on_search_complete)
        self.search_worker.search_error.connect(self.on_search_error)
        self.search_worker.start()
    
    def on_search_complete(self, results: list):
        self.loading_spinner.hide_loading()
        self.search_results = results
        
        if not results:
            self.empty_state.message = "未找到相关结果"
            self.empty_state.icon = "😕"
            self.empty_state.show()
            self.result_count_label.setText("")
            return
        
        self.empty_state.hide()
        self.result_count_label.setText(f"找到 {len(results)} 首歌曲")
        
        # 显示结果
        for i, track in enumerate(results, 1):
            item = SearchResultItem(track)
            item.set_index(i)
            item.download_requested.connect(self.download_requested.emit)
            self.results_layout.insertWidget(self.results_layout.count() - 1, item)
    
    def on_search_error(self, error: str):
        self.loading_spinner.hide_loading()
        self.empty_state.message = f"搜索失败：{error}"
        self.empty_state.icon = "❌"
        self.empty_state.show()
    
    def clear_results(self):
        self.search_results = []
        # 移除所有搜索结果项
        for i in reversed(range(self.results_layout.count())):
            widget = self.results_layout.itemAt(i).widget()
            if widget and isinstance(widget, SearchResultItem):
                widget.deleteLater()
        self.result_count_label.setText("")


class DownloadTab(QWidget):
    """下载标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_style()
        self.download_tasks = {}
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)
        
        # 全部开始按钮
        self.start_all_btn = QPushButton("全部开始")
        self.start_all_btn.setObjectName("primaryButton")
        self.start_all_btn.setFixedHeight(36)
        self.start_all_btn.clicked.connect(self.on_start_all)
        toolbar_layout.addWidget(self.start_all_btn)
        
        # 全部暂停按钮
        self.pause_all_btn = QPushButton("全部暂停")
        self.pause_all_btn.setObjectName("secondaryButton")
        self.pause_all_btn.setFixedHeight(36)
        self.pause_all_btn.clicked.connect(self.on_pause_all)
        toolbar_layout.addWidget(self.pause_all_btn)
        
        # 清空已完成按钮
        self.clear_btn = QPushButton("清空已完成")
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.setFixedHeight(36)
        self.clear_btn.clicked.connect(self.on_clear_completed)
        toolbar_layout.addWidget(self.clear_btn)
        
        toolbar_layout.addStretch()
        
        # 并发数设置
        concurrency_layout = QHBoxLayout()
        concurrency_layout.setSpacing(10)
        
        concurrency_label = QLabel("并发数:")
        concurrency_label.setStyleSheet("color: #B0B0B0;")
        concurrency_layout.addWidget(concurrency_label)
        
        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setRange(1, 10)
        self.concurrency_spin.setValue(5)
        self.concurrency_spin.setFixedWidth(60)
        self.concurrency_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                border-radius: 6px;
                padding: 6px 10px;
                color: #E0E0E0;
            }
        """)
        concurrency_layout.addWidget(self.concurrency_spin)
        
        toolbar_layout.addLayout(concurrency_layout)
        
        layout.addLayout(toolbar_layout)
        
        # 下载列表
        self.downloads_scroll = QScrollArea()
        self.downloads_scroll.setWidgetResizable(True)
        self.downloads_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.downloads_container = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_container)
        self.downloads_layout.setContentsMargins(0, 0, 0, 0)
        self.downloads_layout.setSpacing(10)
        self.downloads_layout.addStretch()
        
        self.downloads_scroll.setWidget(self.downloads_container)
        self.downloads_scroll.setMinimumHeight(300)
        layout.addWidget(self.downloads_scroll, 1)
        
        # 空状态
        self.empty_state = EmptyStateWidget(
            message="暂无下载任务",
            icon="📥"
        )
        layout.addWidget(self.empty_state)
        
        # 统计信息
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #808080; font-size: 12px;")
        layout.addWidget(self.stats_label)
    
    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #252525;
            }
        """)
    
    def add_task(self, track_info: dict):
        """添加下载任务"""
        task_id = f"task_{len(self.download_tasks) + 1}"
        
        item = DownloadQueueItem({
            'id': task_id,
            'title': track_info.get('title', 'Unknown'),
            'artist': track_info.get('artist', ''),
        })
        item.pause_requested.connect(self.on_pause_task)
        item.cancel_requested.connect(self.on_cancel_task)
        
        self.downloads_layout.insertWidget(self.downloads_layout.count() - 1, item)
        self.download_tasks[task_id] = {
            'item': item,
            'track': track_info,
            'status': 'pending',
            'progress': 0.0,
        }
        
        self.empty_state.hide()
        self.update_stats()
    
    def update_task_progress(self, task_id: str, progress: float, status: str):
        """更新任务进度"""
        if task_id in self.download_tasks:
            task = self.download_tasks[task_id]
            task['progress'] = progress
            task['status'] = status
            task['item'].update_progress(progress, status)
            self.update_stats()
    
    def update_task_info(self, task_id: str, speed: str = "", eta: str = ""):
        """更新任务信息"""
        if task_id in self.download_tasks:
            self.download_tasks[task_id]['item'].update_info(speed, eta)
    
    def remove_task(self, task_id: str):
        """移除任务"""
        if task_id in self.download_tasks:
            task = self.download_tasks[task_id]
            task['item'].deleteLater()
            del self.download_tasks[task_id]
            self.update_stats()
            
            if not self.download_tasks:
                self.empty_state.show()
    
    def update_stats(self):
        """更新统计信息"""
        total = len(self.download_tasks)
        completed = sum(1 for t in self.download_tasks.values() if t['status'] == 'completed')
        downloading = sum(1 for t in self.download_tasks.values() if t['status'] == 'downloading')
        
        self.stats_label.setText(
            f"总计：{total} | 下载中：{downloading} | 已完成：{completed}"
        )
    
    def on_start_all(self):
        """全部开始"""
        for task_id, task in self.download_tasks.items():
            if task['status'] in ['pending', 'paused']:
                # 实际实现中会触发下载
                task['item'].update_progress(task['progress'], "downloading")
                task['status'] = 'downloading'
        self.update_stats()
    
    def on_pause_all(self):
        """全部暂停"""
        for task_id, task in self.download_tasks.items():
            if task['status'] == 'downloading':
                task['item'].update_progress(task['progress'], "paused")
                task['status'] = 'paused'
        self.update_stats()
    
    def on_pause_task(self, task_id: str):
        """暂停单个任务"""
        if task_id in self.download_tasks:
            task = self.download_tasks[task_id]
            if task['status'] == 'downloading':
                task['item'].update_progress(task['progress'], "paused")
                task['status'] = 'paused'
            elif task['status'] == 'paused':
                task['item'].update_progress(task['progress'], "downloading")
                task['status'] = 'downloading'
            self.update_stats()
    
    def on_cancel_task(self, task_id: str):
        """取消单个任务"""
        reply = QMessageBox.question(
            self, "确认取消", "确定要取消此下载任务吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.remove_task(task_id)
    
    def on_clear_completed(self):
        """清空已完成的任务"""
        completed_tasks = [
            task_id for task_id, task in self.download_tasks.items()
            if task['status'] == 'completed'
        ]
        for task_id in completed_tasks:
            self.remove_task(task_id)


class SettingsTab(QWidget):
    """设置标签页"""
    
    settings_changed = pyqtSignal(dict)  # 设置变更
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(20)
        
        # 下载设置
        download_group = QGroupBox("下载设置")
        download_layout = QVBoxLayout(download_group)
        download_layout.setSpacing(10)
        
        # 下载路径
        self.path_option = SettingsOption(
            label="下载路径",
            option_type="path",
            default_value=str(Path.home() / "Music" / "MusicHub"),
            key="download_path"
        )
        self.path_option.value_changed.connect(self.on_setting_changed)
        download_layout.addWidget(self.path_option)
        
        # 并发数
        self.concurrency_option = SettingsOption(
            label="最大并发数",
            option_type="number",
            default_value=5,
            key="max_concurrency"
        )
        # 设置范围
        self.concurrency_option.input_widget.setRange(1, 10)
        self.concurrency_option.value_changed.connect(self.on_setting_changed)
        download_layout.addWidget(self.concurrency_option)
        
        container_layout.addWidget(download_group)
        
        # 音质设置
        quality_group = QGroupBox("音质设置")
        quality_layout = QVBoxLayout(quality_group)
        quality_layout.setSpacing(10)
        
        # 音质选择
        self.quality_option = SettingsOption(
            label="默认音质",
            option_type="select",
            default_value="320k",
            options=["128k", "192k", "256k", "320k", "lossless"],
            key="audio_quality"
        )
        self.quality_option.value_changed.connect(self.on_setting_changed)
        quality_layout.addWidget(self.quality_option)
        
        # 输出格式
        self.format_option = SettingsOption(
            label="输出格式",
            option_type="select",
            default_value="mp3",
            options=["mp3", "flac", "m4a", "wav", "ogg"],
            key="output_format"
        )
        self.format_option.value_changed.connect(self.on_setting_changed)
        quality_layout.addWidget(self.format_option)
        
        # 写入元数据
        self.metadata_option = SettingsOption(
            label="写入 ID3 元数据",
            option_type="checkbox",
            default_value=True,
            key="write_metadata"
        )
        self.metadata_option.value_changed.connect(self.on_setting_changed)
        quality_layout.addWidget(self.metadata_option)
        
        container_layout.addWidget(quality_group)
        
        # 界面设置
        interface_group = QGroupBox("界面设置")
        interface_layout = QVBoxLayout(interface_group)
        interface_layout.setSpacing(10)
        
        # 主题
        self.theme_option = SettingsOption(
            label="主题",
            option_type="select",
            default_value="暗色",
            options=["暗色", "亮色"],
            key="theme"
        )
        self.theme_option.value_changed.connect(self.on_setting_changed)
        interface_layout.addWidget(self.theme_option)
        
        # 语言
        self.language_option = SettingsOption(
            label="语言",
            option_type="select",
            default_value="简体中文",
            options=["简体中文", "English"],
            key="language"
        )
        self.language_option.value_changed.connect(self.on_setting_changed)
        interface_layout.addWidget(self.language_option)
        
        container_layout.addWidget(interface_group)
        
        # 关于
        about_group = QGroupBox("关于")
        about_layout = QVBoxLayout(about_group)
        about_layout.setSpacing(10)
        
        about_info = QLabel(
            "<b>MusicHub</b> v1.0.0<br>"
            "一款现代化的音乐下载管理器<br><br>"
            "基于 PyQt6 构建"
        )
        about_info.setStyleSheet("color: #B0B0B0; line-height: 1.6;")
        about_layout.addWidget(about_info)
        
        check_update_btn = QPushButton("检查更新")
        check_update_btn.setObjectName("secondaryButton")
        check_update_btn.setFixedWidth(120)
        about_layout.addWidget(check_update_btn)
        
        container_layout.addWidget(about_group)
        container_layout.addStretch()
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
    
    def load_settings(self):
        """加载设置"""
        settings = QSettings("MusicHub", "Settings")
        
        # 恢复保存的设置
        download_path = settings.value("download_path", str(Path.home() / "Music" / "MusicHub"))
        self.path_option.input_widget.setText(download_path)
        
        max_concurrency = settings.value("max_concurrency", 5, type=int)
        self.concurrency_option.input_widget.setValue(max_concurrency)
        
        audio_quality = settings.value("audio_quality", "320k")
        if audio_quality in self.quality_option.options:
            self.quality_option.input_widget.setCurrentText(audio_quality)
        
        output_format = settings.value("output_format", "mp3")
        if output_format in self.format_option.options:
            self.format_option.input_widget.setCurrentText(output_format)
        
        write_metadata = settings.value("write_metadata", True, type=bool)
        self.metadata_option.input_widget.setChecked(write_metadata)
    
    def save_settings(self):
        """保存设置"""
        settings = QSettings("MusicHub", "Settings")
        
        settings.setValue("download_path", self.path_option.get_value())
        settings.setValue("max_concurrency", self.concurrency_option.get_value())
        settings.setValue("audio_quality", self.quality_option.get_value())
        settings.setValue("output_format", self.format_option.get_value())
        settings.setValue("write_metadata", self.metadata_option.get_value())
        settings.setValue("theme", self.theme_option.get_value())
        settings.setValue("language", self.language_option.get_value())
    
    def on_setting_changed(self, key: str, value):
        """设置变更"""
        self.settings_changed.emit({key: value})
        self.save_settings()


class PlaylistTab(QWidget):
    """播放列表标签页"""
    
    play_requested = pyqtSignal(dict)  # track_info
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_style()
        self.playlist = []
        self.current_index = -1
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)
        
        # 添加歌曲按钮
        self.add_btn = QPushButton("添加歌曲")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setFixedHeight(36)
        self.add_btn.clicked.connect(self.on_add_songs)
        toolbar_layout.addWidget(self.add_btn)
        
        # 清空列表按钮
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.setFixedHeight(36)
        self.clear_btn.clicked.connect(self.on_clear_playlist)
        toolbar_layout.addWidget(self.clear_btn)
        
        toolbar_layout.addStretch()
        
        # 歌曲数量
        self.count_label = QLabel("0 首歌曲")
        self.count_label.setStyleSheet("color: #808080; font-size: 12px;")
        toolbar_layout.addWidget(self.count_label)
        
        layout.addLayout(toolbar_layout)
        
        # 播放列表
        self.playlist_scroll = QScrollArea()
        self.playlist_scroll.setWidgetResizable(True)
        self.playlist_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.playlist_container = QWidget()
        self.playlist_layout = QVBoxLayout(self.playlist_container)
        self.playlist_layout.setContentsMargins(0, 0, 0, 0)
        self.playlist_layout.setSpacing(5)
        self.playlist_layout.addStretch()
        
        self.playlist_scroll.setWidget(self.playlist_container)
        self.playlist_scroll.setMinimumHeight(300)
        layout.addWidget(self.playlist_scroll, 1)
        
        # 空状态
        self.empty_state = EmptyStateWidget(
            message="播放列表为空\n点击\"添加歌曲\"或从搜索结果添加",
            icon="🎵"
        )
        layout.addWidget(self.empty_state)
        
        # 播放器控制
        player_group = QGroupBox("播放器")
        player_layout = QVBoxLayout(player_group)
        player_layout.setSpacing(15)
        
        # 当前播放信息
        self.current_track_label = QLabel("未播放")
        self.current_track_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.current_track_label.setStyleSheet("color: #FFFFFF;")
        self.current_track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        player_layout.addWidget(self.current_track_label)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(0)
        player_layout.addWidget(self.progress_slider)
        
        # 播放控制按钮
        control_layout = QHBoxLayout()
        control_layout.setSpacing(20)
        control_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setObjectName("iconButton")
        self.prev_btn.setFixedSize(50, 50)
        self.prev_btn.setFont(QFont("Segoe UI", 16))
        self.prev_btn.clicked.connect(self.on_previous)
        control_layout.addWidget(self.prev_btn)
        
        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setObjectName("primaryButton")
        self.play_pause_btn.setFixedSize(60, 60)
        self.play_pause_btn.setFont(QFont("Segoe UI", 20))
        self.play_pause_btn.clicked.connect(self.on_play_pause)
        control_layout.addWidget(self.play_pause_btn)
        
        self.next_btn = QPushButton("⏭")
        self.next_btn.setObjectName("iconButton")
        self.next_btn.setFixedSize(50, 50)
        self.next_btn.setFont(QFont("Segoe UI", 16))
        self.next_btn.clicked.connect(self.on_next)
        control_layout.addWidget(self.next_btn)
        
        player_layout.addLayout(control_layout)
        
        layout.addWidget(player_group)
    
    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #252525;
            }
        """)
    
    def add_to_playlist(self, track_info: dict):
        """添加到播放列表"""
        self.playlist.append(track_info)
        
        item = PlaylistItem(track_info, is_current=False)
        item.play_requested.connect(self.on_play_requested)
        item.remove_requested.connect(self.on_remove_requested)
        
        # 插入到空状态之前
        self.playlist_layout.insertWidget(self.playlist_layout.count() - 1, item)
        
        self.update_count()
        self.empty_state.hide()
    
    def update_count(self):
        """更新歌曲数量显示"""
        self.count_label.setText(f"{len(self.playlist)} 首歌曲")
    
    def play_track(self, index: int):
        """播放指定索引的歌曲"""
        if 0 <= index < len(self.playlist):
            # 更新当前播放标记
            for i, track in enumerate(self.playlist):
                item = self.playlist_layout.itemAt(i).widget()
                if item and isinstance(item, PlaylistItem):
                    item.set_current(i == index)
            
            self.current_index = index
            track = self.playlist[index]
            self.current_track_label.setText(f"{track['artist']} - {track['title']}")
            self.play_pause_btn.setText("⏸")
            
            self.play_requested.emit(track)
    
    def on_play_requested(self, track_info: dict):
        """播放请求"""
        index = next((i for i, t in enumerate(self.playlist) if t['id'] == track_info['id']), -1)
        if index >= 0:
            self.play_track(index)
    
    def on_remove_requested(self, track_id: str):
        """移除请求"""
        index = next((i for i, t in enumerate(self.playlist) if t['id'] == track_id), -1)
        if index >= 0:
            item = self.playlist_layout.itemAt(index).widget()
            if item:
                item.deleteLater()
            self.playlist.pop(index)
            self.update_count()
            
            if not self.playlist:
                self.empty_state.show()
                self.current_index = -1
                self.current_track_label.setText("未播放")
    
    def on_play_pause(self):
        """播放/暂停"""
        if self.current_index >= 0:
            if self.play_pause_btn.text() == "▶":
                self.play_pause_btn.setText("⏸")
                # 继续播放
            else:
                self.play_pause_btn.setText("▶")
                # 暂停播放
    
    def on_previous(self):
        """上一首"""
        if self.current_index > 0:
            self.play_track(self.current_index - 1)
    
    def on_next(self):
        """下一首"""
        if self.current_index < len(self.playlist) - 1:
            self.play_track(self.current_index + 1)
    
    def on_add_songs(self):
        """添加歌曲"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音乐文件", "",
            "音频文件 (*.mp3 *.flac *.m4a *.wav *.ogg);;所有文件 (*)"
        )
        for file_path in files:
            path = Path(file_path)
            track_info = {
                'id': f'local_{path.stem}',
                'title': path.stem,
                'artist': '本地音乐',
                'album': '',
                'duration': 0,
                'source': 'local',
                'file_path': str(path),
            }
            self.add_to_playlist(track_info)
    
    def on_clear_playlist(self):
        """清空播放列表"""
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空播放列表吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for i in reversed(range(self.playlist_layout.count())):
                widget = self.playlist_layout.itemAt(i).widget()
                if widget and isinstance(widget, PlaylistItem):
                    widget.deleteLater()
            self.playlist = []
            self.current_index = -1
            self.update_count()
            self.empty_state.show()
            self.current_track_label.setText("未播放")


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.engine = None
        self.config = None
        self.download_workers = {}
        
        if MUSIC_HUB_AVAILABLE:
            try:
                self.config = Config()
                self.engine = DownloadEngine(self.config)
                # 异步初始化
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.engine.initialize())
                finally:
                    loop.close()
            except Exception as e:
                print(f"Failed to initialize MusicHub engine: {e}")
        
        self.setup_ui()
        self.apply_style()
        self.setup_system_tray()
    
    def setup_ui(self):
        self.setWindowTitle("MusicHub - 音乐下载管理器")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # 中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        
        # 搜索标签页
        self.search_tab = SearchTab()
        self.search_tab.download_requested.connect(self.on_download_requested)
        self.tabs.addTab(self.search_tab, "🔍 搜索")
        
        # 下载标签页
        self.download_tab = DownloadTab()
        self.tabs.addTab(self.download_tab, "📥 下载")
        
        # 播放列表标签页
        self.playlist_tab = PlaylistTab()
        self.playlist_tab.play_requested.connect(self.on_play_requested)
        self.tabs.addTab(self.playlist_tab, "🎵 播放列表")
        
        # 设置标签页
        self.settings_tab = SettingsTab()
        self.settings_tab.settings_changed.connect(self.on_settings_changed)
        self.tabs.addTab(self.settings_tab, "⚙️ 设置")
        
        main_layout.addWidget(self.tabs)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 定时更新状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)
    
    def apply_style(self):
        self.setStyleSheet(STYLESHEET)
    
    def setup_system_tray(self):
        """设置系统托盘"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.tray_icon = QSystemTrayIcon(self)
        # 创建简单的图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#0078D4"))
        self.tray_icon.setIcon(QIcon(pixmap))
        
        tray_menu = QMenu()
        
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
    
    def on_tray_activated(self, reason):
        """系统托盘激活"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()
    
    def on_download_requested(self, track_info: dict):
        """下载请求"""
        # 添加到下载队列
        self.download_tab.add_task(track_info)
        
        # 切换到下载标签页
        self.tabs.setCurrentIndex(1)
        
        # 启动下载
        settings = QSettings("MusicHub", "Settings")
        download_path = Path(settings.value("download_path", str(Path.home() / "Music" / "MusicHub")))
        
        filename = f"{track_info['artist']} - {track_info['title']}.mp3"
        output_path = download_path / filename
        
        worker = DownloadWorker(self.engine, track_info, output_path)
        worker.download_started.connect(self.on_download_started)
        worker.download_progress.connect(self.on_download_progress)
        worker.download_complete.connect(self.on_download_complete)
        worker.download_error.connect(self.on_download_error)
        worker.start()
        
        self.download_workers[track_info['id']] = worker
        
        self.status_bar.showMessage(f"开始下载：{track_info['title']}")
    
    def on_download_started(self, task_id: str):
        """下载开始"""
        self.status_bar.showMessage(f"下载任务 {task_id} 已开始")
    
    def on_download_progress(self, task_id: str, progress: float, status: str):
        """下载进度更新"""
        # 查找对应的任务项并更新
        for track_id, worker in self.download_workers.items():
            if hasattr(worker, 'task_id') and worker.task_id == task_id:
                self.download_tab.update_task_progress(track_id, progress, status)
                break
    
    def on_download_complete(self, task_id: str, file_path: str):
        """下载完成"""
        self.status_bar.showMessage(f"下载完成：{Path(file_path).name}")
        
        # 查找并更新任务状态
        for track_id, worker in self.download_workers.items():
            if hasattr(worker, 'task_id') and worker.task_id == task_id:
                self.download_tab.update_task_progress(track_id, 1.0, "completed")
                
                # 添加到播放列表
                self.playlist_tab.add_to_playlist(worker.track)
                break
    
    def on_download_error(self, task_id: str, error: str):
        """下载错误"""
        self.status_bar.showMessage(f"下载失败：{error}")
        QMessageBox.warning(self, "下载失败", f"下载失败：{error}")
    
    def on_play_requested(self, track_info: dict):
        """播放请求"""
        self.status_bar.showMessage(f"播放：{track_info['artist']} - {track_info['title']}")
    
    def on_settings_changed(self, settings: dict):
        """设置变更"""
        for key, value in settings.items():
            self.status_bar.showMessage(f"设置已更新：{key}")
    
    def update_status(self):
        """更新状态栏"""
        if MUSIC_HUB_AVAILABLE and self.engine:
            # 可以显示引擎状态
            pass
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        # 最小化到托盘而不是退出
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "MusicHub",
                "程序已最小化到系统托盘",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            # 清理资源
            if MUSIC_HUB_AVAILABLE and self.engine:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.engine.shutdown())
                finally:
                    loop.close()
            event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("MusicHub")
    app.setOrganizationName("MusicHub")
    
    # 设置应用字体
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # 设置调色板
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1E1E1E"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#252525"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1E1E1E"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#2D2D2D"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FF0000"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#0078D4"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#0078D4"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
