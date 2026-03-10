"""
MusicHub GUI 自定义组件
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QListWidget, QListWidgetItem, QFrame,
    QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont


class SearchResultItem(QWidget):
    """搜索结果项组件"""
    
    download_requested = pyqtSignal(dict)  # 发送歌曲信息
    
    def __init__(self, track_info: dict, parent=None):
        super().__init__(parent)
        self.track_info = track_info
        self.setup_ui()
        self.apply_style()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 序号/图标
        self.index_label = QLabel()
        self.index_label.setFixedWidth(30)
        self.index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.index_label)
        
        # 歌曲信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        # 标题
        self.title_label = QLabel(self.track_info.get('title', 'Unknown'))
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #FFFFFF;")
        info_layout.addWidget(self.title_label)
        
        # 艺术家和专辑
        artist_album = f"{self.track_info.get('artist', 'Unknown')}"
        if self.track_info.get('album'):
            artist_album += f" • {self.track_info.get('album')}"
        
        self.artist_label = QLabel(artist_album)
        self.artist_label.setStyleSheet("color: #B0B0B0; font-size: 12px;")
        info_layout.addWidget(self.artist_label)
        
        # 时长和来源
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(15)
        
        if self.track_info.get('duration'):
            duration_sec = int(self.track_info['duration'])
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            self.duration_label = QLabel(f"{minutes}:{seconds:02d}")
            self.duration_label.setStyleSheet("color: #808080; font-size: 11px;")
            meta_layout.addWidget(self.duration_label)
        
        if self.track_info.get('source'):
            self.source_label = QLabel(self.track_info['source'].upper())
            self.source_label.setStyleSheet(
                "color: #0078D4; background-color: #0078D420; "
                "padding: 2px 8px; border-radius: 4px; font-size: 10px;"
            )
            meta_layout.addWidget(self.source_label)
        
        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)
        
        layout.addLayout(info_layout, 1)
        
        # 下载按钮
        self.download_btn = QPushButton("下载")
        self.download_btn.setObjectName("iconButton")
        self.download_btn.setFixedSize(80, 36)
        self.download_btn.clicked.connect(self.on_download_clicked)
        layout.addWidget(self.download_btn)
        
        self.setObjectName("searchResultItem")
    
    def apply_style(self):
        self.setStyleSheet("""
            QWidget#searchResultItem {
                background-color: #252525;
                border: 1px solid #3D3D3D;
                border-radius: 8px;
                padding: 5px;
            }
            QWidget#searchResultItem:hover {
                background-color: #2D2D2D;
                border: 1px solid #505050;
            }
        """)
    
    def set_index(self, index: int):
        self.index_label.setText(str(index))
    
    def on_download_clicked(self):
        self.download_requested.emit(self.track_info)


class DownloadQueueItem(QWidget):
    """下载队列项组件"""
    
    pause_requested = pyqtSignal(str)  # task_id
    cancel_requested = pyqtSignal(str)  # task_id
    
    def __init__(self, task_info: dict, parent=None):
        super().__init__(parent)
        self.task_info = task_info
        self.task_id = task_info.get('id', '')
        self.setup_ui()
        self.apply_style()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 顶部信息行
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        # 标题
        self.title_label = QLabel(self.task_info.get('title', 'Unknown'))
        self.title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #FFFFFF;")
        top_layout.addWidget(self.title_label, 1)
        
        # 状态标签
        self.status_label = QLabel("等待中")
        self.status_label.setStyleSheet(
            "color: #B0B0B0; background-color: #3D3D3D; "
            "padding: 2px 8px; border-radius: 4px; font-size: 11px;"
        )
        top_layout.addWidget(self.status_label)
        
        layout.addLayout(top_layout)
        
        # 艺术家
        self.artist_label = QLabel(self.task_info.get('artist', ''))
        self.artist_label.setStyleSheet("color: #808080; font-size: 12px;")
        layout.addWidget(self.artist_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 底部信息行
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)
        
        # 速度/ETA
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #808080; font-size: 11px;")
        bottom_layout.addWidget(self.info_label, 1)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setObjectName("iconButton")
        self.pause_btn.setFixedSize(60, 32)
        self.pause_btn.clicked.connect(self.on_pause_clicked)
        btn_layout.addWidget(self.pause_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("iconButton")
        self.cancel_btn.setFixedSize(60, 32)
        self.cancel_btn.setStyleSheet("""
            QPushButton#iconButton {
                color: #D13438;
            }
            QPushButton#iconButton:hover {
                background-color: #D1343820;
            }
        """)
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)
        btn_layout.addWidget(self.cancel_btn)
        
        bottom_layout.addLayout(btn_layout)
        layout.addLayout(bottom_layout)
        
        self.setObjectName("downloadQueueItem")
    
    def apply_style(self):
        self.setStyleSheet("""
            QWidget#downloadQueueItem {
                background-color: #252525;
                border: 1px solid #3D3D3D;
                border-radius: 8px;
                padding: 5px;
            }
            QWidget#downloadQueueItem:hover {
                background-color: #2D2D2D;
            }
        """)
    
    def update_progress(self, progress: float, status: str = "downloading"):
        """更新下载进度"""
        self.progress_bar.setValue(int(progress * 100))
        self.status_label.setText(status)
        
        # 根据状态更新样式
        if status == "downloading":
            self.status_label.setStyleSheet(
                "color: #FFFFFF; background-color: #0078D4; "
                "padding: 2px 8px; border-radius: 4px; font-size: 11px;"
            )
            self.setProperty("status", "downloading")
        elif status == "completed":
            self.status_label.setStyleSheet(
                "color: #FFFFFF; background-color: #107C10; "
                "padding: 2px 8px; border-radius: 4px; font-size: 11px;"
            )
            self.setProperty("status", "completed")
            self.pause_btn.hide()
        elif status == "paused":
            self.status_label.setStyleSheet(
                "color: #FFFFFF; background-color: #FFA500; "
                "padding: 2px 8px; border-radius: 4px; font-size: 11px;"
            )
            self.setProperty("status", "paused")
            self.pause_btn.setText("继续")
        elif status == "failed":
            self.status_label.setStyleSheet(
                "color: #FFFFFF; background-color: #D13438; "
                "padding: 2px 8px; border-radius: 4px; font-size: 11px;"
            )
            self.setProperty("status", "failed")
            self.pause_btn.hide()
        
        self.style().unpolish(self)
        self.style().polish(self)
    
    def update_info(self, speed: str = "", eta: str = ""):
        """更新速度和 ETA 信息"""
        info_parts = []
        if speed:
            info_parts.append(f"速度：{speed}")
        if eta:
            info_parts.append(f"剩余：{eta}")
        self.info_label.setText(" | ".join(info_parts))
    
    def on_pause_clicked(self):
        self.pause_requested.emit(self.task_id)
    
    def on_cancel_clicked(self):
        self.cancel_requested.emit(self.task_id)


class PlaylistItem(QWidget):
    """播放列表项组件"""
    
    play_requested = pyqtSignal(dict)  # track_info
    remove_requested = pyqtSignal(str)  # track_id
    
    def __init__(self, track_info: dict, is_current: bool = False, parent=None):
        super().__init__(parent)
        self.track_info = track_info
        self.is_current = is_current
        self.setup_ui()
        self.apply_style()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(15)
        
        # 播放图标/序号
        self.icon_label = QLabel("▶" if self.is_current else "")
        self.icon_label.setFixedWidth(20)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.is_current:
            self.icon_label.setStyleSheet("color: #107C10;")
        layout.addWidget(self.icon_label)
        
        # 歌曲信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        
        self.title_label = QLabel(self.track_info.get('title', 'Unknown'))
        self.title_label.setFont(QFont("Segoe UI", 13))
        if self.is_current:
            self.title_label.setStyleSheet("color: #107C10; font-weight: bold;")
        else:
            self.title_label.setStyleSheet("color: #E0E0E0;")
        info_layout.addWidget(self.title_label)
        
        self.artist_label = QLabel(self.track_info.get('artist', ''))
        self.artist_label.setStyleSheet("color: #808080; font-size: 11px;")
        info_layout.addWidget(self.artist_label)
        
        layout.addLayout(info_layout, 1)
        
        # 时长
        if self.track_info.get('duration'):
            duration_sec = int(self.track_info['duration'])
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            self.duration_label = QLabel(f"{minutes}:{seconds:02d}")
            self.duration_label.setStyleSheet("color: #808080; font-size: 11px;")
            layout.addWidget(self.duration_label)
        
        # 移除按钮
        self.remove_btn = QPushButton("×")
        self.remove_btn.setObjectName("iconButton")
        self.remove_btn.setFixedSize(28, 28)
        self.remove_btn.setStyleSheet("""
            QPushButton#iconButton {
                color: #808080;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton#iconButton:hover {
                color: #D13438;
                background-color: #D1343820;
            }
        """)
        self.remove_btn.clicked.connect(self.on_remove_clicked)
        layout.addWidget(self.remove_btn)
        
        self.setObjectName("playlistItem")
        if self.is_current:
            self.setProperty("current", True)
    
    def apply_style(self):
        base_style = """
            QWidget#playlistItem {
                background-color: #252525;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 5px;
            }
            QWidget#playlistItem:hover {
                background-color: #2D2D2D;
            }
            QWidget#playlistItem[selected=true] {
                background-color: #0078D4;
            }
        """
        if self.is_current:
            base_style += """
                QWidget#playlistItem[current=true] {
                    background-color: #1D4E2A;
                    border: 1px solid #107C10;
                }
            """
        self.setStyleSheet(base_style)
    
    def set_current(self, is_current: bool):
        self.is_current = is_current
        self.icon_label.setText("▶" if is_current else "")
        self.icon_label.setStyleSheet("color: #107C10;" if is_current else "")
        self.setProperty("current", is_current)
        self.apply_style()
    
    def on_remove_clicked(self):
        self.remove_requested.emit(self.track_info.get('id', ''))


class SettingsOption(QWidget):
    """设置选项组件"""
    
    value_changed = pyqtSignal(str, object)  # key, value
    
    def __init__(self, label: str, option_type: str = "text", 
                 default_value=None, options=None, key: str = "", parent=None):
        """
        Args:
            label: 选项标签
            option_type: 类型 ("text", "number", "select", "checkbox", "path")
            default_value: 默认值
            options: 选项列表 (用于 select 类型)
            key: 选项键名
        """
        super().__init__(parent)
        self.label_text = label
        self.option_type = option_type
        self.default_value = default_value or ""
        self.options = options or []
        self.key = key
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(20)
        
        # 标签
        self.option_label = QLabel(self.label_text)
        self.option_label.setStyleSheet("color: #E0E0E0; font-size: 13px;")
        self.option_label.setFixedWidth(150)
        layout.addWidget(self.option_label)
        
        layout.addStretch()
        
        # 输入控件
        if self.option_type == "checkbox":
            from PyQt6.QtWidgets import QCheckBox
            self.input_widget = QCheckBox()
            self.input_widget.setChecked(bool(self.default_value))
            self.input_widget.stateChanged.connect(self.on_value_changed)
            layout.addWidget(self.input_widget)
        
        elif self.option_type == "select":
            from PyQt6.QtWidgets import QComboBox
            self.input_widget = QComboBox()
            self.input_widget.addItems(self.options)
            if self.default_value in self.options:
                self.input_widget.setCurrentText(self.default_value)
            self.input_widget.currentTextChanged.connect(self.on_value_changed)
            self.input_widget.setFixedWidth(200)
            layout.addWidget(self.input_widget)
        
        elif self.option_type == "number":
            from PyQt6.QtWidgets import QSpinBox
            self.input_widget = QSpinBox()
            self.input_widget.setValue(int(self.default_value))
            self.input_widget.setStyleSheet("""
                QSpinBox {
                    background-color: #2D2D2D;
                    border: 1px solid #3D3D3D;
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: #E0E0E0;
                }
                QSpinBox:focus {
                    border: 1px solid #0078D4;
                }
            """)
            self.input_widget.valueChanged.connect(self.on_value_changed)
            self.input_widget.setFixedWidth(150)
            layout.addWidget(self.input_widget)
        
        elif self.option_type == "path":
            from PyQt6.QtWidgets import QLineEdit, QPushButton
            path_layout = QHBoxLayout()
            path_layout.setSpacing(10)
            
            self.input_widget = QLineEdit()
            self.input_widget.setText(str(self.default_value))
            self.input_widget.textChanged.connect(self.on_value_changed)
            path_layout.addWidget(self.input_widget, 1)
            
            browse_btn = QPushButton("浏览")
            browse_btn.setObjectName("secondaryButton")
            browse_btn.setFixedWidth(70)
            browse_btn.clicked.connect(self.on_browse_clicked)
            path_layout.addWidget(browse_btn)
            
            layout.addLayout(path_layout, 1)
        
        else:  # text
            from PyQt6.QtWidgets import QLineEdit
            self.input_widget = QLineEdit()
            self.input_widget.setText(str(self.default_value))
            self.input_widget.textChanged.connect(self.on_value_changed)
            self.input_widget.setFixedWidth(250)
            layout.addWidget(self.input_widget)
        
        layout.addStretch()
    
    def on_value_changed(self, value):
        self.value_changed.emit(self.key, value)
    
    def on_browse_clicked(self):
        from PyQt6.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self, "选择目录", str(self.input_widget.text())
        )
        if directory:
            self.input_widget.setText(directory)
            self.on_value_changed(directory)
    
    def get_value(self):
        if hasattr(self.input_widget, 'isChecked'):
            return self.input_widget.isChecked()
        elif hasattr(self.input_widget, 'value'):
            return self.input_widget.value()
        elif hasattr(self.input_widget, 'currentText'):
            return self.input_widget.currentText()
        else:
            return self.input_widget.text()


class LoadingSpinner(QWidget):
    """加载动画组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.hide()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 加载标签
        self.loading_label = QLabel("加载中...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            color: #808080;
            font-size: 14px;
        """)
        layout.addWidget(self.loading_label)
        
        self.setFixedSize(200, 100)
    
    def show_loading(self):
        self.show()
    
    def hide_loading(self):
        self.hide()


class EmptyStateWidget(QWidget):
    """空状态提示组件"""
    
    def __init__(self, message: str = "暂无内容", icon: str = "📭", parent=None):
        super().__init__(parent)
        self.message = message
        self.icon = icon
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        
        # 图标
        icon_label = QLabel(self.icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("color: #505050;")
        layout.addWidget(icon_label)
        
        # 提示文字
        message_label = QLabel(self.message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet("""
            color: #808080;
            font-size: 16px;
        """)
        layout.addWidget(message_label)
        
        self.setMinimumHeight(200)
