"""
异步工具模块
"""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, TypeVar

T = TypeVar('T')


def run_async(coro: Any) -> Any:
    """
    在现有事件循环中运行协程
    
    Args:
        coro: 协程对象
    
    Returns:
        协程结果
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        return loop.run_until_complete(coro)


async def gather_with_concurrency(
    limit: int,
    *coros: Any,
    return_exceptions: bool = False,
) -> list[Any]:
    """
    限制并发数执行多个协程
    
    Args:
        limit: 最大并发数
        *coros: 协程列表
        return_exceptions: 是否返回异常而不是抛出
    
    Returns:
        结果列表
    """
    semaphore = asyncio.Semaphore(limit)
    
    async def sem_coro(coro):
        async with semaphore:
            if return_exceptions:
                try:
                    return await coro
                except Exception as e:
                    return e
            else:
                return await coro
    
    return await asyncio.gather(*[sem_coro(c) for c in coros])


class AsyncIterator:
    """
    异步迭代器工具类
    
    用于将同步迭代器转换为异步迭代器
    """
    
    def __init__(self, items: list[Any], delay: float = 0):
        self.items = items
        self.delay = delay
        self.index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        
        item = self.items[self.index]
        self.index += 1
        
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        return item


async def aenumerate(asequence, start: int = 0):
    """
    异步枚举
    
    Args:
        asequence: 异步可迭代对象
        start: 起始索引
    
    Yields:
        (索引，值) 元组
    """
    i = start
    async for elem in asequence:
        yield i, elem
        i += 1


def async_wrap(func: Callable) -> Callable:
    """
    将同步函数包装为异步函数
    
    Args:
        func: 同步函数
    
    Returns:
        异步包装函数
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
    
    return wrapper
