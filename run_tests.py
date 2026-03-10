#!/usr/bin/env python3
"""
MusicHub 核心模块测试运行器

用法:
    python run_tests.py              # 运行所有测试
    python run_tests.py -v           # 详细输出
    python run_tests.py downloader   # 只运行下载器测试
"""

import sys
import subprocess
from pathlib import Path


def main():
    """运行测试"""
    # 确保 src 在 Python 路径中
    src_path = Path(__file__).parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # 构建 pytest 命令
    cmd = [sys.executable, "-m", "pytest"]

    # 添加命令行参数
    if len(sys.argv) > 1:
        # 如果有特定测试文件/类
        for arg in sys.argv[1:]:
            if arg.startswith("-"):
                cmd.append(arg)
            else:
                # 查找测试文件
                test_file = Path(__file__).parent / "tests" / "unit" / f"test_{arg}.py"
                if test_file.exists():
                    cmd.append(str(test_file))
                else:
                    print(f"Warning: Test file not found: test_{arg}.py")
    else:
        # 默认运行所有单元测试
        cmd.append("tests/unit")

    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)

    # 运行 pytest
    result = subprocess.run(cmd, cwd=Path(__file__).parent)

    print("-" * 50)
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed with code {result.returncode}")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
