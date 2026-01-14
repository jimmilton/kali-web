"""Embedded task queue for background job execution.

Copyright 2025 milbert.ai

Replaces Celery + Redis with a simple asyncio-based task queue.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a background task."""

    id: UUID
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskQueue:
    """Simple embedded task queue using asyncio."""

    _instance: Optional["TaskQueue"] = None

    def __init__(self, max_workers: int = 4):
        self.tasks: Dict[UUID, Task] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._scheduler_task: Optional[asyncio.Task] = None
        self._scheduled_tasks: List[Dict] = []

    @classmethod
    def get_instance(cls) -> "TaskQueue":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = TaskQueue()
        return cls._instance

    async def start(self):
        """Start the task queue worker."""
        if self.running:
            return

        self.running = True
        self._worker_task = asyncio.create_task(self._worker())
        self._scheduler_task = asyncio.create_task(self._scheduler())
        logger.info("Task queue started")

    async def stop(self):
        """Stop the task queue worker."""
        self.running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        self.executor.shutdown(wait=False)
        logger.info("Task queue stopped")

    def enqueue(
        self,
        func: Callable,
        *args,
        task_name: Optional[str] = None,
        **kwargs,
    ) -> UUID:
        """Add a task to the queue."""
        task_id = uuid4()
        task = Task(
            id=task_id,
            name=task_name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
        )
        self.tasks[task_id] = task

        # Put task in queue
        try:
            self.queue.put_nowait(task)
            logger.debug(f"Task {task_id} enqueued: {task.name}")
        except asyncio.QueueFull:
            logger.error(f"Task queue full, dropping task {task_id}")
            task.status = TaskStatus.FAILED
            task.error = "Queue full"

        return task_id

    def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def schedule(
        self,
        func: Callable,
        interval_seconds: int,
        task_name: Optional[str] = None,
    ):
        """Schedule a recurring task."""
        self._scheduled_tasks.append({
            "func": func,
            "interval": interval_seconds,
            "name": task_name or func.__name__,
            "last_run": None,
        })
        logger.info(f"Scheduled task '{task_name}' every {interval_seconds}s")

    async def _worker(self):
        """Background worker that processes tasks."""
        while self.running:
            try:
                # Wait for task with timeout to allow checking running flag
                try:
                    task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Update task status
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                logger.info(f"Executing task {task.id}: {task.name}")

                try:
                    # Check if function is async
                    if asyncio.iscoroutinefunction(task.func):
                        task.result = await task.func(*task.args, **task.kwargs)
                    else:
                        # Run sync function in thread pool
                        loop = asyncio.get_event_loop()
                        task.result = await loop.run_in_executor(
                            self.executor,
                            lambda: task.func(*task.args, **task.kwargs),
                        )

                    task.status = TaskStatus.COMPLETED
                    logger.info(f"Task {task.id} completed")

                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    logger.exception(f"Task {task.id} failed: {e}")

                finally:
                    task.completed_at = datetime.utcnow()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Worker error: {e}")

    async def _scheduler(self):
        """Background scheduler for recurring tasks."""
        while self.running:
            try:
                now = datetime.utcnow()

                for scheduled in self._scheduled_tasks:
                    last_run = scheduled["last_run"]
                    interval = scheduled["interval"]

                    if last_run is None or (now - last_run).total_seconds() >= interval:
                        scheduled["last_run"] = now
                        self.enqueue(
                            scheduled["func"],
                            task_name=f"scheduled:{scheduled['name']}",
                        )

                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Scheduler error: {e}")


# Global task queue instance
task_queue = TaskQueue.get_instance()


def enqueue_task(func: Callable, *args, **kwargs) -> UUID:
    """Convenience function to enqueue a task."""
    return task_queue.enqueue(func, *args, **kwargs)


def schedule_task(func: Callable, interval_seconds: int, task_name: Optional[str] = None):
    """Convenience function to schedule a recurring task."""
    task_queue.schedule(func, interval_seconds, task_name)
