#!/usr/bin/env python3
"""
MusicHub GUI 启动脚本
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

def check_dependencies():
    """检查依赖项"""
    missing = []
    
    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")
    
    if missing:
        print("❌ 缺少依赖项:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\n请运行以下命令安装:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True

def main():
    """主函数"""
    if not check_dependencies():
        sys.exit(1)
    
    from gui.app import main as gui_main
    gui_main()

if __name__ == "__main__":
    main()
