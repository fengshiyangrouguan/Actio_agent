from __future__ import annotations

import asyncio
from collections import deque
from typing import Deque, Dict, List

from .schemas import AgentTask, MemoryMessage, TaskUpdate


class InMemoryTaskStore:
    """
    内存任务存储类，用于管理任务、消息队列和会话记忆
    功能：
    1. 存储 AgentTask 对象
    2. 管理任务更新队列（异步推送）
    3. 管理会话记忆窗口（最近 N 条消息）
    """

    def __init__(self, memory_window_size: int = 8) -> None:
        """
        初始化 InMemoryTaskStore
        :param memory_window_size: 每个会话记忆窗口最大消息数，默认 8 条
        """
        self._tasks: Dict[str, AgentTask] = {}  # 存储任务对象，key=task_id
        self._queues: Dict[str, asyncio.Queue[TaskUpdate]] = {}  # 存储每个任务的异步更新队列
        self._session_memory: Dict[str, Deque[MemoryMessage]] = {}  # 存储会话记忆，key=session_id
        self._memory_window_size = memory_window_size  # 记忆窗口大小

    def create_task(self, task: AgentTask) -> None:
        """
        创建任务
        1. 将任务加入任务字典
        2. 为任务创建异步队列
        3. 初始化会话记忆（如果不存在）
        """
        self._tasks[task.task_id] = task
        self._queues[task.task_id] = asyncio.Queue()
        self._session_memory.setdefault(
            task.session_id,
            deque(maxlen=self._memory_window_size),  # 记忆窗口有限长度
        )

    def get_task(self, task_id: str) -> AgentTask:
        """根据 task_id 获取任务对象"""
        return self._tasks[task_id]

    def append_memory(self, session_id: str, role: str, content: str) -> None:
        """
        向指定会话的记忆窗口追加一条消息
        :param session_id: 会话 ID
        :param role: 消息角色，例如 "user" 或 "assistant"
        :param content: 消息内容
        """
        memory = self._session_memory.setdefault(
            session_id,
            deque(maxlen=self._memory_window_size),  # 如果没有记忆，初始化 deque
        )
        memory.append(MemoryMessage(role=role, content=content))  # 添加新消息

    def get_memory_window(self, session_id: str) -> List[MemoryMessage]:
        """
        获取指定会话的记忆窗口（最近 N 条消息）
        :param session_id: 会话 ID
        :return: MemoryMessage 列表
        """
        memory = self._session_memory.get(session_id)
        if memory is None:
            return []  # 没有记忆则返回空列表
        return list(memory)

    async def publish(self, task_id: str, update: TaskUpdate) -> None:
        """
        向任务队列发布更新
        1. 将更新加入任务的 updates 列表
        2. 异步放入任务的队列
        :param task_id: 任务 ID
        :param update: TaskUpdate 对象
        """
        task = self._tasks[task_id]
        task.updates.append(update)  # 保存更新历史
        await self._queues[task_id].put(update)  # 异步推送更新

    def queue_for(self, task_id: str) -> asyncio.Queue[TaskUpdate]:
        """
        获取任务的异步队列，用于订阅任务更新
        :param task_id: 任务 ID
        :return: asyncio.Queue 对象
        """
        return self._queues[task_id]