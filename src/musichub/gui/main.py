"""MusicHub GUI - 图形用户界面

使用 PyQt6 实现，包含搜索框、结果列表、下载队列。
"""

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QProgressBar,
    QComboBox,
    QLabel,
    QGroupBox,
    QTabWidget,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QSpinBox,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor


class SearchWorker(QThread):
    """搜索工作线程"""
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, query: str, source: str, limit: int = 20):
        super().__init__()
        self.query = query
        self.source = source
        self.limit = limit
    
    def run(self):
        try:
            # 模拟搜索结果
            results = []
            for i in range(1, self.limit + 1):
                results.append({
                    "id": i,
                    "title": f"歌曲 {i}",
                    "artist": f"歌手 {i}",
                    "duration": f"3:{i:02d}",
                    "source": self.source,
                })
            self.results_ready.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DownloadWorker(QThread):
    """下载工作线程"""
    progress_updated = pyqtSignal(int, int)  # task_id, progress
    download_complete = pyqtSignal(int, str)  # task_id, path
    error_occurred = pyqtSignal(int, str)  # task_id, error
    
    def __init__(self, task_id: int, track_info: dict, output_path: str, fmt: str):
        super().__init__()
        self.task_id = task_id
        self.track_info = track_info
        self.output_path = output_path
        self.format = fmt
        self._stop = False
    
    def run(self):
        try:
            # 模拟下载进度
            for progress in range(0, 101, 5):
                if self._stop:
                    break
                self.progress_updated.emit(self.task_id, progress)
                self.msleep(100)
            
            if not self._stop:
                path = str(Path(self.output_path) / f"{self.track_info['title']}.{self.format}")
                self.download_complete.emit(self.task_id, path)
        except Exception as e:
            self.error_occurred.emit(self.task_id, str(e))
    
    def stop(self):
        self._stop = True


class MusicHubApp(QMainWindow):
    """MusicHub 主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 MusicHub - 聚合音乐下载器")
        self.setMinimumSize(900, 700)
        self.setStyleSheet(self._get_stylesheet())
        
        self.search_workers = []
        self.download_workers = {}
        self.task_counter = 0
        self.download_queue = []
        
        self._init_ui()
    
    def _get_stylesheet(self) -> str:
        """获取样式表"""
        return """
        QMainWindow {
            background-color: #1a1a2e;
        }
        QWidget {
            color: #eaeaea;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        }
        QLabel {
            color: #eaeaea;
        }
        QLineEdit {
            padding: 10px;
            border: 2px solid #16213e;
            border-radius: 8px;
            background-color: #16213e;
            color: #eaeaea;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 2px solid #0f3460;
        }
        QPushButton {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            background-color: #e94560;
            color: white;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #ff6b6b;
        }
        QPushButton:pressed {
            background-color: #c73e54;
        }
        QPushButton:disabled {
            background-color: #555;
        }
        QComboBox {
            padding: 8px;
            border: 2px solid #16213e;
            border-radius: 6px;
            background-color: #16213e;
            color: #eaeaea;
        }
        QTableWidget {
            background-color: #16213e;
            alternate-background-color: #1a1a2e;
            border: 1px solid #0f3460;
            border-radius: 8px;
            gridline-color: #0f3460;
        }
        QTableWidget::item {
            padding: 8px;
        }
        QTableWidget::item:selected {
            background-color: #0f3460;
        }
        QHeaderView::section {
            background-color: #0f3460;
            color: white;
            padding: 8px;
            border: none;
            font-weight: bold;
        }
        QProgressBar {
            border: none;
            border-radius: 6px;
            background-color: #16213e;
            text-align: center;
            color: white;
        }
        QProgressBar::chunk {
            background-color: #e94560;
            border-radius: 6px;
        }
        QGroupBox {
            border: 2px solid #0f3460;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #e94560;
        }
        QTabWidget::pane {
            border: 1px solid #0f3460;
            border-radius: 8px;
            background-color: #16213e;
        }
        QTabBar::tab {
            background-color: #16213e;
            color: #eaeaea;
            padding: 10px 20px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #0f3460;
        }
        QSpinBox {
            padding: 5px;
            border: 2px solid #16213e;
            border-radius: 6px;
            background-color: #16213e;
            color: #eaeaea;
        }
        QCheckBox {
            spacing: 5px;
        }
        """
    
    def _init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("🎵 MusicHub")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #e94560;")
        main_layout.addWidget(title_label)
        
        # 标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 搜索标签页
        search_tab = self._create_search_tab()
        self.tabs.addTab(search_tab, "🔍 搜索")
        
        # 下载队列标签页
        queue_tab = self._create_queue_tab()
        self.tabs.addTab(queue_tab, "⬇️ 下载队列")
        
        # 设置标签页
        settings_tab = self._create_settings_tab()
        self.tabs.addTab(settings_tab, "⚙️ 设置")
    
    def _create_search_tab(self) -> QWidget:
        """创建搜索标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 搜索区域
        search_group = QGroupBox("搜索音乐")
        search_layout = QHBoxLayout(search_group)
        search_layout.setSpacing(10)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入歌曲名、歌手或专辑...")
        self.search_input.returnPressed.connect(self._do_search)
        search_layout.addWidget(self.search_input, 3)
        
        # 音源选择
        self.source_combo = QComboBox()
        self.source_combo.addItems(["网易云音乐", "QQ 音乐", "Spotify", "YouTube Music"])
        search_layout.addWidget(self.source_combo)
        
        # 搜索按钮
        self.search_btn = QPushButton("🔍 搜索")
        self.search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(self.search_btn)
        
        layout.addWidget(search_group)
        
        # 结果表格
        results_group = QGroupBox("搜索结果")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["ID", "标题", "歌手", "时长", "来源"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        results_layout.addWidget(self.results_table)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.download_selected_btn = QPushButton("⬇️ 下载选中")
        self.download_selected_btn.clicked.connect(self._download_selected)
        btn_layout.addWidget(self.download_selected_btn)
        
        self.download_all_btn = QPushButton("📦 全部下载")
        self.download_all_btn.clicked.connect(self._download_all)
        btn_layout.addWidget(self.download_all_btn)
        
        btn_layout.addStretch()
        results_layout.addLayout(btn_layout)
        
        layout.addWidget(results_group, 1)
        
        return widget
    
    def _create_queue_tab(self) -> QWidget:
        """创建下载队列标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 队列表格
        queue_group = QGroupBox("下载队列")
        queue_layout = QVBoxLayout(queue_group)
        
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(5)
        self.queue_table.setHorizontalHeaderLabels(["ID", "歌曲", "状态", "进度", "操作"])
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        queue_layout.addWidget(self.queue_table)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.pause_all_btn = QPushButton("⏸️ 全部暂停")
        self.pause_all_btn.clicked.connect(self._pause_all)
        btn_layout.addWidget(self.pause_all_btn)
        
        self.resume_all_btn = QPushButton("▶️ 全部继续")
        self.resume_all_btn.clicked.connect(self._resume_all)
        btn_layout.addWidget(self.resume_all_btn)
        
        self.clear_completed_btn = QPushButton("🗑️ 清除已完成")
        self.clear_completed_btn.clicked.connect(self._clear_completed)
        btn_layout.addWidget(self.clear_completed_btn)
        
        btn_layout.addStretch()
        queue_layout.addLayout(btn_layout)
        
        layout.addWidget(queue_group, 1)
        
        return widget
    
    def _create_settings_tab(self) -> QWidget:
        """创建设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 下载设置
        download_group = QGroupBox("下载设置")
        download_layout = QVBoxLayout(download_group)
        
        # 下载路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("下载路径:"))
        self.download_path_input = QLineEdit()
        self.download_path_input.setText(str(Path.home() / "Music"))
        path_layout.addWidget(self.download_path_input)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)
        download_layout.addLayout(path_layout)
        
        # 格式选择
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("默认格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP3", "FLAC", "M4A", "WAV"])
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        download_layout.addLayout(format_layout)
        
        # 并发数
        concurrency_layout = QHBoxLayout()
        concurrency_layout.addWidget(QLabel("最大并发数:"))
        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setRange(1, 10)
        self.concurrency_spin.setValue(3)
        concurrency_layout.addWidget(self.concurrency_spin)
        concurrency_layout.addStretch()
        download_layout.addLayout(concurrency_layout)
        
        layout.addWidget(download_group)
        
        # 元数据设置
        metadata_group = QGroupBox("元数据设置")
        metadata_layout = QVBoxLayout(metadata_group)
        
        self.auto_metadata_check = QCheckBox("自动写入元数据 (封面、歌词等)")
        self.auto_metadata_check.setChecked(True)
        metadata_layout.addWidget(self.auto_metadata_check)
        
        layout.addWidget(metadata_group)
        
        # 保存按钮
        save_btn = QPushButton("💾 保存设置")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        return widget
    
    def _do_search(self):
        """执行搜索"""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "警告", "请输入搜索关键词")
            return
        
        source = self.source_combo.currentText()
        
        # 禁用搜索按钮
        self.search_btn.setEnabled(False)
        self.search_btn.setText("搜索中...")
        
        # 启动搜索线程
        worker = SearchWorker(query, source)
        worker.results_ready.connect(self._on_search_results)
        worker.error_occurred.connect(self._on_search_error)
        self.search_workers.append(worker)
        worker.start()
    
    def _on_search_results(self, results: list):
        """处理搜索结果"""
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 搜索")
        
        self.results_table.setRowCount(len(results))
        for row, r in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(str(r["id"])))
            self.results_table.setItem(row, 1, QTableWidgetItem(r["title"]))
            self.results_table.setItem(row, 2, QTableWidgetItem(r["artist"]))
            self.results_table.setItem(row, 3, QTableWidgetItem(r["duration"]))
            self.results_table.setItem(row, 4, QTableWidgetItem(r["source"]))
    
    def _on_search_error(self, error: str):
        """处理搜索错误"""
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 搜索")
        QMessageBox.critical(self, "错误", f"搜索失败：{error}")
    
    def _download_selected(self):
        """下载选中的歌曲"""
        selected_rows = set(item.row() for item in self.results_table.selectedItems())
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要下载的歌曲")
            return
        
        for row in selected_rows:
            track_info = {
                "id": self.results_table.item(row, 0).text(),
                "title": self.results_table.item(row, 1).text(),
                "artist": self.results_table.item(row, 2).text(),
                "duration": self.results_table.item(row, 3).text(),
                "source": self.results_table.item(row, 4).text(),
            }
            self._add_to_queue(track_info)
        
        self.tabs.setCurrentIndex(1)  # 切换到队列标签页
    
    def _download_all(self):
        """下载所有搜索结果"""
        for row in range(self.results_table.rowCount()):
            track_info = {
                "id": self.results_table.item(row, 0).text(),
                "title": self.results_table.item(row, 1).text(),
                "artist": self.results_table.item(row, 2).text(),
                "duration": self.results_table.item(row, 3).text(),
                "source": self.results_table.item(row, 4).text(),
            }
            self._add_to_queue(track_info)
        
        self.tabs.setCurrentIndex(1)
    
    def _add_to_queue(self, track_info: dict):
        """添加到下载队列"""
        self.task_counter += 1
        task_id = self.task_counter
        
        # 添加到表格
        row = self.queue_table.rowCount()
        self.queue_table.insertRow(row)
        
        self.queue_table.setItem(row, 0, QTableWidgetItem(str(task_id)))
        self.queue_table.setItem(row, 1, QTableWidgetItem(f"{track_info['title']} - {track_info['artist']}"))
        
        status_item = QTableWidgetItem("等待中")
        status_item.setForeground(QColor("#f1c40f"))
        self.queue_table.setItem(row, 2, status_item)
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        self.queue_table.setCellWidget(row, 3, progress_bar)
        
        # 操作按钮
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(5, 0, 5, 0)
        
        pause_btn = QPushButton("⏸️")
        pause_btn.setFixedWidth(40)
        pause_btn.clicked.connect(lambda: self._pause_task(task_id))
        btn_layout.addWidget(pause_btn)
        
        cancel_btn = QPushButton("❌")
        cancel_btn.setFixedWidth(40)
        cancel_btn.clicked.connect(lambda: self._cancel_task(task_id))
        btn_layout.addWidget(cancel_btn)
        
        self.queue_table.setCellWidget(row, 4, btn_widget)
        
        # 启动下载
        output_path = self.download_path_input.text()
        fmt = self.format_combo.currentText().lower()
        
        worker = DownloadWorker(task_id, track_info, output_path, fmt)
        worker.progress_updated.connect(self._on_progress)
        worker.download_complete.connect(self._on_complete)
        worker.error_occurred.connect(self._on_error)
        self.download_workers[task_id] = worker
        worker.start()
    
    def _on_progress(self, task_id: int, progress: int):
        """更新进度"""
        for row in range(self.queue_table.rowCount()):
            if self.queue_table.item(row, 0) and self.queue_table.item(row, 0).text() == str(task_id):
                progress_bar = self.queue_table.cellWidget(row, 3)
                if progress_bar:
                    progress_bar.setValue(progress)
                
                status_item = self.queue_table.item(row, 2)
                if status_item and progress < 100:
                    status_item.setText("下载中")
                    status_item.setForeground(QColor("#3498db"))
                break
    
    def _on_complete(self, task_id: int, path: str):
        """下载完成"""
        for row in range(self.queue_table.rowCount()):
            if self.queue_table.item(row, 0) and self.queue_table.item(row, 0).text() == str(task_id):
                status_item = self.queue_table.item(row, 2)
                if status_item:
                    status_item.setText("已完成")
                    status_item.setForeground(QColor("#27ae60"))
                
                # 禁用操作按钮
                btn_widget = self.queue_table.cellWidget(row, 4)
                if btn_widget:
                    btn_widget.setEnabled(False)
                break
        
        if task_id in self.download_workers:
            del self.download_workers[task_id]
    
    def _on_error(self, task_id: int, error: str):
        """下载错误"""
        for row in range(self.queue_table.rowCount()):
            if self.queue_table.item(row, 0) and self.queue_table.item(row, 0).text() == str(task_id):
                status_item = self.queue_table.item(row, 2)
                if status_item:
                    status_item.setText("失败")
                    status_item.setForeground(QColor("#e74c3c"))
                break
    
    def _pause_task(self, task_id: int):
        """暂停任务"""
        if task_id in self.download_workers:
            self.download_workers[task_id].stop()
    
    def _cancel_task(self, task_id: int):
        """取消任务"""
        if task_id in self.download_workers:
            self.download_workers[task_id].stop()
            del self.download_workers[task_id]
    
    def _pause_all(self):
        """暂停所有任务"""
        for worker in self.download_workers.values():
            worker.stop()
    
    def _resume_all(self):
        """继续所有任务"""
        # 简化实现：重新启动
        QMessageBox.information(self, "提示", "恢复功能开发中...")
    
    def _clear_completed(self):
        """清除已完成的任务"""
        for row in range(self.queue_table.rowCount() - 1, -1, -1):
            status_item = self.queue_table.item(row, 2)
            if status_item and status_item.text() == "已完成":
                self.queue_table.removeRow(row)
    
    def _browse_path(self):
        """浏览路径"""
        path = QFileDialog.getExistingDirectory(self, "选择下载目录")
        if path:
            self.download_path_input.setText(path)
    
    def _save_settings(self):
        """保存设置"""
        QMessageBox.information(self, "成功", "设置已保存")


def main():
    """主入口"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MusicHubApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
