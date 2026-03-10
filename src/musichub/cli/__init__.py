"""MusicHub CLI - 命令行接口模块"""

from .main import app

__all__ = ["app"]


def main():
    """CLI 入口点"""
    app()
