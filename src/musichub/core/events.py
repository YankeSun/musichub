"""
事件系统模块

提供发布/订阅模式的事件通知机制
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable


class EventType(Enum):
    """事件类型"""
    # 搜索事件
    SEARCH_START = auto()
    SEARCH_COMPLETE = auto()
    SEARCH_ERROR = auto()
    
    # 下载事件
    DOWNLOAD_START = auto()
    DOWNLOAD_PROGRESS = auto()
    DOWNLOAD_COMPLETE = auto()
    DOWNLOAD_ERROR = auto()
    
    # 导出事件
    EXPORT_START = auto()
    EXPORT_COMPLETE = auto()
    EXPORT_ERROR = auto()
    
    # 任务事件
    TASK_CREATED = auto()
    TASK_CANCELLED = auto()
    TASK_PAUSED = auto()
    TASK_RESUMED = auto()
    
    # 通用事件
    ERROR = auto()
    WARNING = auto()
    INFO = auto()


@dataclass
class Event:
    """事件对象"""
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())


@dataclass
class DownloadEvent(Event):
    """下载事件"""
    task_id: str = ""
    track_id: str = ""
    url: str = ""
    progress: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    message: str = ""


@dataclass
class SearchEvent(Event):
    """搜索事件"""
    query: str = ""
    source: str = ""
    results_count: int = 0


class EventSystem:
    """
    事件系统
    
    支持同步和异步事件处理器
    """
    
    def __init__(self):
        self._handlers: dict[EventType, list[Callable]] = {}
        self._async_handlers: dict[EventType, list[Callable]] = {}
    
    def on(self, event_type: EventType, callback: Callable, async_handler: bool = False) -> None:
        """
        注册事件监听器
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            async_handler: 是否为异步处理器
        """
        if async_handler:
            handlers = self._async_handlers.setdefault(event_type, [])
        else:
            handlers = self._handlers.setdefault(event_type, [])
        
        if callback not in handlers:
            handlers.append(callback)
    
    def off(self, event_type: EventType, callback: Callable) -> None:
        """
        移除事件监听器
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        for handlers in [self._handlers, self._async_handlers]:
            if event_type in handlers:
                handlers[event_type] = [h for h in handlers[event_type] if h != callback]
    
    async def emit(self, event_type: EventType, data: dict[str, Any] | None = None) -> None:
        """
        触发事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        event = Event(type=event_type, data=data or {})
        
        # 调用同步处理器
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                # 记录错误但不中断其他处理器
                print(f"事件处理器错误：{e}")
        
        # 调用异步处理器
        async_handlers = self._async_handlers.get(event_type, [])
        if async_handlers:
            await asyncio.gather(
                *[self._call_async_handler(h, event) for h in async_handlers],
                return_exceptions=True,
            )
    
    async def _call_async_handler(self, handler: Callable, event: Event) -> None:
        """调用异步处理器"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            print(f"异步事件处理器错误：{e}")
    
    def clear(self) -> None:
        """清除所有事件监听器"""
        self._handlers.clear()
        self._async_handlers.clear()
