# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Download queue and task management."""

import asyncio
import contextlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from ripstream.downloader.enums import ContentType, DownloadPriority, DownloadState
from ripstream.models.base import RipStreamBaseModel


class DownloadTask(RipStreamBaseModel):
    """Represents a download task in the queue."""

    # Task identification
    task_id: UUID = Field(default_factory=uuid4, description="Unique task identifier")
    content_id: str = Field(..., description="Content identifier from source")
    content_type: ContentType = Field(..., description="Type of content to download")
    source: str = Field(..., description="Source service (spotify, deezer, etc.)")

    # Task metadata
    title: str = Field(..., description="Display title for the task")
    artist: str | None = Field(None, description="Artist name if applicable")
    album: str | None = Field(None, description="Album name if applicable")

    # Download information
    url: str = Field(..., description="Download URL")
    file_path: str = Field(..., description="Target file path")
    file_size: int | None = Field(None, description="Expected file size in bytes")
    checksum: str | None = Field(None, description="Expected file checksum")

    # Task settings
    priority: DownloadPriority = Field(
        default=DownloadPriority.NORMAL, description="Task priority"
    )
    state: DownloadState = Field(
        default=DownloadState.PENDING, description="Current task state"
    )

    # Timing information
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Task creation time"
    )
    started_at: datetime | None = Field(None, description="Download start time")
    completed_at: datetime | None = Field(None, description="Download completion time")

    # Progress and error tracking
    progress_percentage: float = Field(
        default=0.0, description="Download progress (0-100)"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    error_message: str | None = Field(None, description="Last error message")

    # Dependencies and relationships
    depends_on: list[UUID] = Field(
        default_factory=list, description="Task IDs this task depends on"
    )
    parent_task_id: UUID | None = Field(
        None, description="Parent task ID for grouped downloads"
    )

    # Custom metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional task metadata"
    )

    @property
    def is_ready(self) -> bool:
        """Check if task is ready to be processed."""
        return self.state == DownloadState.PENDING and not self.depends_on

    @property
    def is_active(self) -> bool:
        """Check if task is currently being processed."""
        return self.state in (DownloadState.DOWNLOADING, DownloadState.RETRYING)

    @property
    def is_complete(self) -> bool:
        """Check if task is completed."""
        return self.state == DownloadState.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if task has failed."""
        return self.state == DownloadState.FAILED

    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.is_failed and self.retry_count < 3

    @property
    def display_name(self) -> str:
        """Get display name for the task."""
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        return self.title

    def mark_started(self) -> None:
        """Mark task as started."""
        self.state = DownloadState.DOWNLOADING
        self.started_at = datetime.now(UTC)

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.state = DownloadState.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.progress_percentage = 100.0

    def mark_failed(self, error_message: str) -> None:
        """Mark task as failed."""
        self.state = DownloadState.FAILED
        self.error_message = error_message
        self.retry_count += 1

    def mark_cancelled(self) -> None:
        """Mark task as cancelled."""
        self.state = DownloadState.CANCELLED

    def update_progress(self, percentage: float) -> None:
        """Update task progress."""
        self.progress_percentage = max(0.0, min(100.0, percentage))

    def add_dependency(self, task_id: UUID) -> None:
        """Add a task dependency."""
        if task_id not in self.depends_on:
            self.depends_on.append(task_id)

    def remove_dependency(self, task_id: UUID) -> None:
        """Remove a task dependency."""
        if task_id in self.depends_on:
            self.depends_on.remove(task_id)

    def set_metadata(self, key: str, value: str) -> None:
        """Set metadata value."""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: str | None = None) -> str | None:
        """Get metadata value."""
        value = self.metadata.get(key, default)
        if value is None or isinstance(value, str):
            return value
        return str(value)


class DownloadQueue:
    """Manages a queue of download tasks."""

    def __init__(self, max_size: int = 1000) -> None:
        self.max_size = max_size
        self._tasks: dict[UUID, DownloadTask] = {}
        self._pending_queue: asyncio.PriorityQueue[tuple[int, UUID]] = (
            asyncio.PriorityQueue()
        )
        self._active_tasks: set[UUID] = set()
        self._completed_tasks: set[UUID] = set()
        self._failed_tasks: set[UUID] = set()
        self._lock = asyncio.Lock()

        # Event callbacks
        self._task_added_callbacks: list[Callable[[DownloadTask], None]] = []
        self._task_completed_callbacks: list[Callable[[DownloadTask], None]] = []
        self._task_failed_callbacks: list[Callable[[DownloadTask, str], None]] = []

    @property
    def size(self) -> int:
        """Get total number of tasks in queue."""
        return len(self._tasks)

    @property
    def pending_count(self) -> int:
        """Get number of pending tasks."""
        return self._pending_queue.qsize()

    @property
    def active_count(self) -> int:
        """Get number of active tasks."""
        return len(self._active_tasks)

    @property
    def completed_count(self) -> int:
        """Get number of completed tasks."""
        return len(self._completed_tasks)

    @property
    def failed_count(self) -> int:
        """Get number of failed tasks."""
        return len(self._failed_tasks)

    @property
    def is_full(self) -> bool:
        """Check if queue is at capacity."""
        return self.size >= self.max_size

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.size == 0

    async def add_task(self, task: DownloadTask) -> bool:
        """Add a task to the queue."""
        async with self._lock:
            if self.is_full:
                return False

            self._tasks[task.task_id] = task

            # Add to pending queue if ready
            if task.is_ready:
                priority = -task.priority  # Negative for max priority queue
                await self._pending_queue.put((priority, task.task_id))

            # Notify callbacks
            for callback in self._task_added_callbacks:
                with contextlib.suppress(Exception):
                    callback(task)

            return True

    async def get_next_task(self) -> DownloadTask | None:
        """Get the next task to process."""
        try:
            _priority, task_id = await asyncio.wait_for(
                self._pending_queue.get(), timeout=0.1
            )
        except TimeoutError:
            return None

        async with self._lock:
            task = self._tasks.get(task_id)
            if task and task.is_ready:
                self._active_tasks.add(task_id)
                task.mark_started()
                return task

            # Task is no longer ready, skip it
            return None

    async def complete_task(self, task_id: UUID) -> bool:
        """Mark a task as completed."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.mark_completed()
            self._active_tasks.discard(task_id)
            self._completed_tasks.add(task_id)

            # Check for dependent tasks that might now be ready
            await self._check_dependent_tasks(task_id)

            # Notify callbacks
            for callback in self._task_completed_callbacks:
                with contextlib.suppress(Exception):
                    callback(task)

            return True

    async def fail_task(self, task_id: UUID, error_message: str) -> bool:
        """Mark a task as failed."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.mark_failed(error_message)
            self._active_tasks.discard(task_id)

            if task.can_retry:
                # Re-queue for retry
                priority = -task.priority
                await self._pending_queue.put((priority, task_id))
            else:
                self._failed_tasks.add(task_id)

            # Notify callbacks
            for callback in self._task_failed_callbacks:
                with contextlib.suppress(Exception):
                    callback(task, error_message)

            return True

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.mark_cancelled()
            self._active_tasks.discard(task_id)
            return True

    async def remove_task(self, task_id: UUID) -> bool:
        """Remove a task from the queue."""
        async with self._lock:
            if task_id not in self._tasks:
                return False

            del self._tasks[task_id]
            self._active_tasks.discard(task_id)
            self._completed_tasks.discard(task_id)
            self._failed_tasks.discard(task_id)
            return True

    def get_task(self, task_id: UUID) -> DownloadTask | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_tasks_by_state(self, state: DownloadState) -> list[DownloadTask]:
        """Get all tasks with a specific state."""
        return [task for task in self._tasks.values() if task.state == state]

    def get_tasks_by_content_type(
        self, content_type: ContentType
    ) -> list[DownloadTask]:
        """Get all tasks with a specific content type."""
        return [
            task for task in self._tasks.values() if task.content_type == content_type
        ]

    def get_all_tasks(self) -> list[DownloadTask]:
        """Get all tasks in the queue."""
        return list(self._tasks.values())

    async def clear_completed(self) -> int:
        """Clear completed tasks from the queue."""
        async with self._lock:
            completed_ids = list(self._completed_tasks)
            for task_id in completed_ids:
                del self._tasks[task_id]
                self._completed_tasks.remove(task_id)
            return len(completed_ids)

    async def clear_failed(self) -> int:
        """Clear failed tasks from the queue."""
        async with self._lock:
            failed_ids = list(self._failed_tasks)
            for task_id in failed_ids:
                del self._tasks[task_id]
                self._failed_tasks.remove(task_id)
            return len(failed_ids)

    async def clear_all(self) -> int:
        """Clear all tasks from the queue."""
        async with self._lock:
            count = len(self._tasks)
            self._tasks.clear()
            self._active_tasks.clear()
            self._completed_tasks.clear()
            self._failed_tasks.clear()

            # Clear the pending queue
            while not self._pending_queue.empty():
                try:
                    self._pending_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            return count

    def add_task_added_callback(self, callback: Callable[[DownloadTask], None]) -> None:
        """Add callback for when tasks are added."""
        self._task_added_callbacks.append(callback)

    def add_task_completed_callback(
        self, callback: Callable[[DownloadTask], None]
    ) -> None:
        """Add callback for when tasks are completed."""
        self._task_completed_callbacks.append(callback)

    def add_task_failed_callback(
        self, callback: Callable[[DownloadTask, str], None]
    ) -> None:
        """Add callback for when tasks fail."""
        self._task_failed_callbacks.append(callback)

    async def _check_dependent_tasks(self, completed_task_id: UUID) -> None:
        """Check if any tasks are now ready after a dependency completes."""
        for task in self._tasks.values():
            if completed_task_id in task.depends_on:
                task.remove_dependency(completed_task_id)

                # If task is now ready, add to pending queue
                if task.is_ready:
                    priority = -task.priority
                    await self._pending_queue.put((priority, task.task_id))

    def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return {
            "total_tasks": self.size,
            "pending_tasks": self.pending_count,
            "active_tasks": self.active_count,
            "completed_tasks": self.completed_count,
            "failed_tasks": self.failed_count,
            "queue_capacity": self.max_size,
            "queue_utilization": (self.size / self.max_size) * 100
            if self.max_size > 0
            else 0,
        }
