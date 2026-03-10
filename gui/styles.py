"""
MusicHub GUI 样式表
现代暗色主题设计
"""

STYLESHEET = """
/* ========================================
   全局样式
   ======================================== */
QWidget {
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 14px;
    color: #E0E0E0;
    background-color: #1E1E1E;
}

/* ========================================
   主窗口
   ======================================== */
QMainWindow {
    background-color: #1E1E1E;
}

QMainWindow::separator {
    background-color: #2D2D2D;
    width: 1px;
}

/* ========================================
   标签页 (QTabWidget)
   ======================================== */
QTabWidget::pane {
    background-color: #252525;
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    padding: 10px;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar::tab {
    background-color: #2D2D2D;
    color: #B0B0B0;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-width: 100px;
}

QTabBar::tab:selected {
    background-color: #3D3D3D;
    color: #FFFFFF;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background-color: #383838;
    color: #E0E0E0;
}

/* ========================================
   按钮 (QPushButton)
   ======================================== */
QPushButton {
    background-color: #0078D4;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
    min-height: 36px;
}

QPushButton:hover {
    background-color: #1084D8;
}

QPushButton:pressed {
    background-color: #006CBE;
}

QPushButton:disabled {
    background-color: #3D3D3D;
    color: #808080;
}

/* 主要按钮 */
QPushButton#primaryButton {
    background-color: #0078D4;
    font-size: 15px;
    padding: 10px 30px;
}

QPushButton#primaryButton:hover {
    background-color: #1084D8;
}

/* 次要按钮 */
QPushButton#secondaryButton {
    background-color: #3D3D3D;
    border: 1px solid #505050;
}

QPushButton#secondaryButton:hover {
    background-color: #4D4D4D;
}

/* 危险按钮 */
QPushButton#dangerButton {
    background-color: #D13438;
}

QPushButton#dangerButton:hover {
    background-color: #E81123;
}

/* 图标按钮 */
QPushButton#iconButton {
    background-color: transparent;
    padding: 6px 12px;
    min-height: 32px;
    min-width: 32px;
}

QPushButton#iconButton:hover {
    background-color: #3D3D3D;
}

/* ========================================
   输入框 (QLineEdit, QTextEdit)
   ======================================== */
QLineEdit {
    background-color: #2D2D2D;
    border: 1px solid #3D3D3D;
    border-radius: 6px;
    padding: 8px 12px;
    color: #E0E0E0;
    selection-background-color: #0078D4;
}

QLineEdit:focus {
    border: 1px solid #0078D4;
}

QLineEdit:disabled {
    background-color: #1E1E1E;
    color: #808080;
}

QTextEdit {
    background-color: #2D2D2D;
    border: 1px solid #3D3D3D;
    border-radius: 6px;
    padding: 8px;
    color: #E0E0E0;
    selection-background-color: #0078D4;
}

QTextEdit:focus {
    border: 1px solid #0078D4;
}

/* ========================================
   下拉框 (QComboBox)
   ======================================== */
QComboBox {
    background-color: #2D2D2D;
    border: 1px solid #3D3D3D;
    border-radius: 6px;
    padding: 8px 12px;
    color: #E0E0E0;
    min-height: 36px;
}

QComboBox:focus {
    border: 1px solid #0078D4;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
    padding-right: 10px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #E0E0E0;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #2D2D2D;
    border: 1px solid #3D3D3D;
    border-radius: 6px;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
    outline: none;
    padding: 5px;
}

QComboBox QAbstractItemView::item {
    min-height: 36px;
    padding: 5px 10px;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #3D3D3D;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #0078D4;
    color: #FFFFFF;
}

/* ========================================
   列表 (QListWidget)
   ======================================== */
QListWidget {
    background-color: #252525;
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    padding: 5px;
    outline: none;
}

QListWidget::item {
    background-color: transparent;
    padding: 10px;
    border-radius: 6px;
    margin: 2px 0;
    border: 1px solid transparent;
}

QListWidget::item:hover {
    background-color: #2D2D2D;
    border: 1px solid #3D3D3D;
}

QListWidget::item:selected {
    background-color: #0078D4;
    color: #FFFFFF;
    border: 1px solid #0078D4;
}

/* ========================================
   表格 (QTableWidget)
   ======================================== */
QTableWidget {
    background-color: #252525;
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    gridline-color: #3D3D3D;
    outline: none;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:hover {
    background-color: #2D2D2D;
}

QTableWidget::item:selected {
    background-color: #0078D4;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #2D2D2D;
    color: #B0B0B0;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #3D3D3D;
    font-weight: bold;
}

QHeaderView::section:hover {
    background-color: #383838;
}

/* ========================================
   进度条 (QProgressBar)
   ======================================== */
QProgressBar {
    background-color: #2D2D2D;
    border: none;
    border-radius: 6px;
    height: 20px;
    text-align: center;
    color: #FFFFFF;
    font-weight: bold;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0078D4, stop:1 #00BCF2);
    border-radius: 6px;
}

/* ========================================
   滚动条 (QScrollBar)
   ======================================== */
QScrollBar:vertical {
    background-color: #1E1E1E;
    width: 12px;
    border-radius: 6px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #3D3D3D;
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4D4D4D;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #1E1E1E;
    height: 12px;
    border-radius: 6px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #3D3D3D;
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4D4D4D;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ========================================
   分组框 (QGroupBox)
   ======================================== */
QGroupBox {
    background-color: #252525;
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    margin-top: 15px;
    padding-top: 15px;
    font-weight: bold;
    color: #E0E0E0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    padding: 0 10px;
    color: #0078D4;
}

/* ========================================
   复选框 (QCheckBox)
   ======================================== */
QCheckBox {
    color: #E0E0E0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #3D3D3D;
    background-color: #2D2D2D;
}

QCheckBox::indicator:checked {
    background-color: #0078D4;
    border: 2px solid #0078D4;
    image: url(:/icons/checkmark.png);
}

QCheckBox::indicator:hover {
    border: 2px solid #0078D4;
}

/* ========================================
   单选框 (QRadioButton)
   ======================================== */
QRadioButton {
    color: #E0E0E0;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 20px;
    height: 20px;
    border-radius: 10px;
    border: 2px solid #3D3D3D;
    background-color: #2D2D2D;
}

QRadioButton::indicator:checked {
    background-color: #0078D4;
    border: 2px solid #0078D4;
}

QRadioButton::indicator:hover {
    border: 2px solid #0078D4;
}

/* ========================================
   滑块 (QSlider)
   ======================================== */
QSlider::groove:horizontal {
    background-color: #2D2D2D;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #0078D4;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background-color: #1084D8;
}

QSlider::sub-page:horizontal {
    background-color: #0078D4;
    border-radius: 3px;
}

QSlider::add-page:horizontal {
    background-color: #2D2D2D;
    border-radius: 3px;
}

/* ========================================
   工具提示 (QToolTip)
   ======================================== */
QToolTip {
    background-color: #2D2D2D;
    color: #E0E0E0;
    border: 1px solid #3D3D3D;
    border-radius: 4px;
    padding: 5px 10px;
}

/* ========================================
   状态栏 (QStatusBar)
   ======================================== */
QStatusBar {
    background-color: #252525;
    border-top: 1px solid #3D3D3D;
    color: #B0B0B0;
    padding: 5px;
}

QStatusBar::item {
    border: none;
}

/* ========================================
   菜单 (QMenu, QMenuBar)
   ======================================== */
QMenuBar {
    background-color: #1E1E1E;
    color: #E0E0E0;
    padding: 5px;
}

QMenuBar::item {
    padding: 5px 15px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #3D3D3D;
}

QMenu {
    background-color: #252525;
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    padding: 5px;
}

QMenu::item {
    padding: 8px 30px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #0078D4;
    color: #FFFFFF;
}

QMenu::separator {
    height: 1px;
    background-color: #3D3D3D;
    margin: 5px 10px;
}

/* ========================================
   对话框 (QDialog)
   ======================================== */
QDialog {
    background-color: #1E1E1E;
}

/* ========================================
   标签 (QLabel)
   ======================================== */
QLabel {
    color: #E0E0E0;
    background-color: transparent;
}

QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel#subtitleLabel {
    font-size: 14px;
    color: #B0B0B0;
}

QLabel#infoLabel {
    color: #808080;
    font-size: 12px;
}

QLabel#errorLabel {
    color: #D13438;
}

QLabel#successLabel {
    color: #107C10;
}

/* ========================================
   框架 (QFrame)
   ======================================== */
QFrame {
    background-color: transparent;
}

QFrame#separator {
    background-color: #3D3D3D;
    max-height: 1px;
}

QFrame#card {
    background-color: #252525;
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    padding: 15px;
}

QFrame#card:hover {
    border: 1px solid #505050;
}

/* ========================================
   工具栏 (QToolBar)
   ======================================== */
QToolBar {
    background-color: #252525;
    border: none;
    border-bottom: 1px solid #3D3D3D;
    padding: 5px;
    spacing: 5px;
}

QToolBar::separator {
    background-color: #3D3D3D;
    width: 1px;
    margin: 5px;
}

/* ========================================
   自定义组件样式
   ======================================== */

/* 搜索结果项 */
QWidget#searchResultItem {
    background-color: #252525;
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    padding: 10px;
}

QWidget#searchResultItem:hover {
    background-color: #2D2D2D;
    border: 1px solid #505050;
}

QWidget#searchResultItem:selected {
    background-color: #0078D4;
    border: 1px solid #0078D4;
}

/* 下载队列项 */
QWidget#downloadQueueItem {
    background-color: #252525;
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    padding: 10px;
}

QWidget#downloadQueueItem:hover {
    background-color: #2D2D2D;
}

QWidget#downloadQueueItem[status="downloading"] {
    border: 1px solid #0078D4;
}

QWidget#downloadQueueItem[status="completed"] {
    border: 1px solid #107C10;
}

QWidget#downloadQueueItem[status="failed"] {
    border: 1px solid #D13438;
}

/* 播放列表项 */
QWidget#playlistItem {
    background-color: #252525;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 8px;
}

QWidget#playlistItem:hover {
    background-color: #2D2D2D;
}

QWidget#playlistItem:selected {
    background-color: #0078D4;
}

QWidget#playlistItem[current] {
    background-color: #1D4E2A;
    border: 1px solid #107C10;
}

/* 设置面板 */
QWidget#settingsPanel {
    background-color: #252525;
    border-radius: 8px;
    padding: 20px;
}

/* ========================================
   滚动区域 (QScrollArea)
   ======================================== */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* ========================================
   尺寸调整器 (QSizeGrip)
   ======================================== */
QSizeGrip {
    background-color: transparent;
    width: 16px;
    height: 16px;
}
"""
