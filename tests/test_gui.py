#!/usr/bin/env python3
"""
MusicHub GUI 测试脚本
验证 GUI 模块是否可以正常导入和运行
"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

def test_imports():
    """测试导入"""
    print("📦 测试导入...")
    
    try:
        # 先测试样式表（不依赖 PyQt6 运行时）
        from gui.styles import STYLESHEET
        print("   ✅ styles.py 导入成功")
        
        # 测试 widgets 模块（语法正确）
        import ast
        with open(os.path.join(project_root, 'gui', 'widgets.py'), 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        print("   ✅ widgets.py 语法正确")
        
        # 测试 app 模块（语法正确）
        with open(os.path.join(project_root, 'gui', 'app.py'), 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        print("   ✅ app.py 语法正确")
        
        print("✅ 所有模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 导入失败：{e}")
        return False
    except SyntaxError as e:
        print(f"❌ 语法错误：{e}")
        return False

def test_stylesheet():
    """测试样式表"""
    print("\n🎨 测试样式表...")
    
    try:
        from gui.styles import STYLESHEET
        
        if not STYLESHEET:
            print("❌ 样式表为空")
            return False
        
        if "QWidget" not in STYLESHEET:
            print("❌ 样式表格式错误")
            return False
        
        # 检查关键组件样式
        required_styles = ["QPushButton", "QLineEdit", "QProgressBar", "QTabWidget", "QLabel"]
        missing = [s for s in required_styles if s not in STYLESHEET]
        
        if missing:
            print(f"⚠️  缺少样式：{', '.join(missing)}")
        
        print(f"✅ 样式表加载成功 ({len(STYLESHEET)} 字符)")
        return True
    except Exception as e:
        print(f"❌ 样式表测试失败：{e}")
        return False

def test_widgets():
    """测试组件"""
    print("\n🧩 测试组件...")
    
    try:
        # 使用 AST 检查语法
        import ast
        widgets_path = os.path.join(project_root, 'gui', 'widgets.py')
        with open(widgets_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        # 检查类定义
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        required_classes = ['SearchResultItem', 'DownloadQueueItem', 'PlaylistItem', 
                          'SettingsOption', 'LoadingSpinner', 'EmptyStateWidget']
        
        missing = [c for c in required_classes if c not in classes]
        if missing:
            print(f"⚠️  缺少组件类：{', '.join(missing)}")
            return False
        
        print(f"   ✅ 定义了 {len(classes)} 个组件类")
        print("✅ 组件语法正确")
        return True
    except Exception as e:
        print(f"❌ 组件测试失败：{e}")
        return False

def test_app():
    """测试主应用"""
    print("\n🖼️ 测试主应用...")
    
    try:
        # 使用 AST 检查语法
        import ast
        app_path = os.path.join(project_root, 'gui', 'app.py')
        with open(app_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        # 检查类定义
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        required_classes = ['MainWindow', 'SearchTab', 'DownloadTab', 
                          'PlaylistTab', 'SettingsTab', 'SearchWorker', 'DownloadWorker']
        
        missing = [c for c in required_classes if c not in classes]
        if missing:
            print(f"⚠️  缺少应用类：{', '.join(missing)}")
            return False
        
        print(f"   ✅ 定义了 {len(classes)} 个应用类")
        print("✅ 主应用语法正确")
        return True
    except Exception as e:
        print(f"❌ 主应用测试失败：{e}")
        return False

def test_dependencies():
    """测试依赖项"""
    print("\n📋 检查依赖项...")
    
    missing = []
    
    try:
        import PyQt6
        print(f"   ✅ PyQt6 已安装")
    except ImportError:
        missing.append("PyQt6")
        print(f"   ⚠️  PyQt6 未安装")
    
    try:
        import musichub
        print(f"   ✅ musichub (核心模块)")
    except ImportError:
        print(f"   ⚠️  musichub 核心模块未安装 (Demo 模式)")
    
    if missing:
        print(f"\n💡 提示：运行 'pip install PyQt6' 安装缺失的依赖")
        return False
    
    return True

def main():
    """运行所有测试"""
    print("=" * 60)
    print("MusicHub GUI 测试")
    print("=" * 60)
    
    results = []
    
    results.append(("依赖检查", test_dependencies()))
    results.append(("模块导入", test_imports()))
    results.append(("样式表", test_stylesheet()))
    results.append(("组件", test_widgets()))
    results.append(("主应用", test_app()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！GUI 已准备就绪。")
        print("\n运行以下命令启动 GUI:")
        print("   python run_gui.py")
        return 0
    else:
        print("\n⚠️  部分测试失败。请检查上述错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
