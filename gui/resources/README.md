# MusicHub GUI Resources

此目录包含 GUI 所需的资源文件。

## 文件结构

```
resources/
├── icons/          # 图标文件
│   ├── checkmark.png
│   ├── search.svg
│   ├── download.svg
│   ├── play.svg
│   ├── pause.svg
│   └── ...
├── images/         # 图片资源
│   └── logo.png
└── fonts/          # 自定义字体（可选）
```

## 图标说明

当前版本使用 Unicode 字符和 PyQt6 内置图标，因此图标文件是可选的。

如需添加自定义图标，请确保：
- 使用 PNG 格式（推荐 24x24, 32x32, 48x48 像素）
- 支持透明背景
- 暗色主题下清晰可见

## 生成图标资源

可以使用以下工具生成图标：
- [Inkscape](https://inkscape.org/) - 矢量图标编辑
- [GIMP](https://www.gimp.org/) - 位图编辑
- [IconScout](https://iconscout.com/) - 图标资源

## Qt 资源系统

如需使用 Qt 资源系统（.qrc 文件），请创建 `resources.qrc`：

```xml
<!DOCTYPE RCC>
<RCC version="1.0">
    <qresource prefix="/">
        <file>icons/checkmark.png</file>
        <file>icons/search.svg</file>
        <file>images/logo.png</file>
    </qresource>
</RCC>
```

然后使用 `pyside6-rcc` 或 `pyrcc6` 编译：

```bash
pyrcc6 resources.qrc -o resources_rc.py
```

并在代码中导入：
```python
from . import resources_rc
```
