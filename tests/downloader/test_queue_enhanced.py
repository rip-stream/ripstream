# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Enhanced tests for download queue with comprehensive coverage."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from ripstream.downloader.enums import ContentType, DownloadPriority, DownloadState
from ripstream.downloader.queue import DownloadQueue, DownloadTask


@pytest.fixture
def sample_task():
    """Create a sample download task."""
    return DownloadTask(
        content_id="test_123",
        content_type=ContentType.TRACK,
        source="test_source",
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        url="https://example.com/test_123",
        file_path="/path/to/test_track.mp3",
        file_size=5000000,
        checksum="abc123",
        priority=DownloadPriority.NORMAL,
    )


@pytest.fixture
def download_queue():
    """Create a download queue instance."""
    return DownloadQueue(max_size=100)


class TestDownloadTask:
    """Test DownloadTask class."""

    def test_task_creation(self, sample_task):
        """Test creating a download task."""
        assert sample_task.content_id == "test_123"
        assert sample_task.content_type == ContentType.TRACK
        assert sample_task.source == "test_source"
        assert sample_task.title == "Test Track"
        assert sample_task.artist == "Test Artist"
        assert sample_task.album == "Test Album"
        assert sample_task.state == DownloadState.PENDING
        assert sample_task.priority == DownloadPriority.NORMAL
        assert sample_task.progress_percentage == 0.0
        assert sample_task.retry_count == 0

    def test_task_id_generation(self):
        """Test that task IDs are automatically generated."""
        task1 = DownloadTask(
            content_id="test1",
            content_type=ContentType.TRACK,
            source="test",
            title="Test",
            url="https://example.com/test1",
            file_path="/path/to/test1.mp3",
        )
        task2 = DownloadTask(
            content_id="test2",
            content_type=ContentType.TRACK,
            source="test",
            title="Test",
            url="https://example.com/test2",
            file_path="/path/to/test2.mp3",
        )

        assert isinstance(task1.task_id, UUID)
        assert isinstance(task2.task_id, UUID)
        assert task1.task_id != task2.task_id

    @pytest.mark.parametrize(
        ("state", "expected_ready"),
        [
            (DownloadState.PENDING, True),
            (DownloadState.DOWNLOADING, False),
            (DownloadState.COMPLETED, False),
            (DownloadState.FAILED, False),
            (DownloadState.CANCELLED, False),
        ],
    )
    def test_is_ready_property(self, sample_task, state, expected_ready):
        """Test is_ready property with different states."""
        sample_task.state = state
        assert sample_task.is_ready == expected_ready

    def test_is_ready_with_dependencies(self, sample_task):
        """Test is_ready property with dependencies."""
        # Task should not be ready if it has dependencies
        sample_task.add_dependency(uuid4())
        assert sample_task.is_ready is False

        # Task should be ready when dependencies are removed
        sample_task.depends_on.clear()
        assert sample_task.is_ready is True

    @pytest.mark.parametrize(
        ("state", "expected_active"),
        [
            (DownloadState.PENDING, False),
            (DownloadState.DOWNLOADING, True),
            (DownloadState.RETRYING, True),
            (DownloadState.COMPLETED, False),
            (DownloadState.FAILED, False),
        ],
    )
    def test_is_active_property(self, sample_task, state, expected_active):
        """Test is_active property with different states."""
        sample_task.state = state
        assert sample_task.is_active == expected_active

    @pytest.mark.parametrize(
        ("state", "expected_complete"),
        [
            (DownloadState.PENDING, False),
            (DownloadState.DOWNLOADING, False),
            (DownloadState.COMPLETED, True),
            (DownloadState.FAILED, False),
        ],
    )
    def test_is_complete_property(self, sample_task, state, expected_complete):
        """Test is_complete property with different states."""
        sample_task.state = state
        assert sample_task.is_complete == expected_complete

    @pytest.mark.parametrize(
        ("state", "expected_failed"),
        [
            (DownloadState.PENDING, False),
            (DownloadState.DOWNLOADING, False),
            (DownloadState.COMPLETED, False),
            (DownloadState.FAILED, True),
        ],
    )
    def test_is_failed_property(self, sample_task, state, expected_failed):
        """Test is_failed property with different states."""
        sample_task.state = state
        assert sample_task.is_failed == expected_failed

    @pytest.mark.parametrize(
        ("state", "retry_count", "expected_can_retry"),
        [
            (DownloadState.FAILED, 0, True),
            (DownloadState.FAILED, 2, True),
            (DownloadState.FAILED, 3, False),
            (DownloadState.COMPLETED, 0, False),
            (DownloadState.PENDING, 0, False),
        ],
    )
    def test_can_retry_property(
        self, sample_task, state, retry_count, expected_can_retry
    ):
        """Test can_retry property with different states and retry counts."""
        sample_task.state = state
        sample_task.retry_count = retry_count
        assert sample_task.can_retry == expected_can_retry

    @pytest.mark.parametrize(
        ("artist", "title", "expected_display"),
        [
            ("Test Artist", "Test Track", "Test Artist - Test Track"),
            (None, "Test Track", "Test Track"),
            ("", "Test Track", "Test Track"),
            ("Test Artist", "", ""),  # Empty title returns empty string
        ],
    )
    def test_display_name_property(self, artist, title, expected_display):
        """Test display_name property with different artist/title combinations."""
        task = DownloadTask(
            content_id="test",
            content_type=ContentType.TRACK,
            source="test",
            title=title,
            artist=artist,
            url="https://example.com/test",
            file_path="/path/to/test.mp3",
        )
        assert task.display_name == expected_display

    def test_mark_started(self, sample_task):
        """Test marking task as started."""
        start_time = datetime.now(UTC)
        sample_task.mark_started()

        assert sample_task.state == DownloadState.DOWNLOADING
        assert sample_task.started_at is not None
        assert sample_task.started_at >= start_time

    def test_mark_completed(self, sample_task):
        """Test marking task as completed."""
        completion_time = datetime.now(UTC)
        sample_task.mark_completed()

        assert sample_task.state == DownloadState.COMPLETED
        assert sample_task.completed_at is not None
        assert sample_task.completed_at >= completion_time
        assert sample_task.progress_percentage == 100.0

    def test_mark_failed(self, sample_task):
        """Test marking task as failed."""
        error_message = "Download failed"
        initial_retry_count = sample_task.retry_count

        sample_task.mark_failed(error_message)

        assert sample_task.state == DownloadState.FAILED
        assert sample_task.error_message == error_message
        assert sample_task.retry_count == initial_retry_count + 1

    def test_mark_cancelled(self, sample_task):
        """Test marking task as cancelled."""
        sample_task.mark_cancelled()
        assert sample_task.state == DownloadState.CANCELLED

    @pytest.mark.parametrize(
        ("percentage", "expected"),
        [
            (50.0, 50.0),
            (-10.0, 0.0),  # Should clamp to 0
            (150.0, 100.0),  # Should clamp to 100
            (0.0, 0.0),
            (100.0, 100.0),
        ],
    )
    def test_update_progress(self, sample_task, percentage, expected):
        """Test updating task progress with clamping."""
        sample_task.update_progress(percentage)
        assert sample_task.progress_percentage == expected

    def test_dependency_management(self, sample_task):
        """Test adding and removing dependencies."""
        dep1 = uuid4()
        dep2 = uuid4()

        # Add dependencies
        sample_task.add_dependency(dep1)
        sample_task.add_dependency(dep2)
        assert dep1 in sample_task.depends_on
        assert dep2 in sample_task.depends_on
        assert len(sample_task.depends_on) == 2

        # Adding same dependency again should not duplicate
        sample_task.add_dependency(dep1)
        assert len(sample_task.depends_on) == 2

        # Remove dependency
        sample_task.remove_dependency(dep1)
        assert dep1 not in sample_task.depends_on
        assert dep2 in sample_task.depends_on
        assert len(sample_task.depends_on) == 1

        # Removing non-existent dependency should not error
        sample_task.remove_dependency(uuid4())
        assert len(sample_task.depends_on) == 1

    def test_metadata_management(self, sample_task):
        """Test setting and getting metadata."""
        # Set metadata
        sample_task.set_metadata("quality", "320kbps")
        sample_task.set_metadata("format", "MP3")

        # Get metadata
        assert sample_task.get_metadata("quality") == "320kbps"
        assert sample_task.get_metadata("format") == "MP3"
        assert sample_task.get_metadata("nonexistent") is None
        assert sample_task.get_metadata("nonexistent", "default") == "default"

        # Test with non-string values (should be converted to string)
        sample_task.metadata["number"] = 123
        assert sample_task.get_metadata("number") == "123"


class TestDownloadQueue:
    """Test DownloadQueue class."""

    def test_queue_initialization(self):
        """Test queue initialization."""
        queue = DownloadQueue(max_size=50)
        assert queue.max_size == 50
        assert queue.size == 0
        assert queue.pending_count == 0
        assert queue.active_count == 0
        assert queue.completed_count == 0
        assert queue.failed_count == 0
        assert queue.is_empty is True
        assert queue.is_full is False

    def test_queue_properties(self, download_queue, sample_task):
        """Test queue property calculations."""
        # Initially empty
        assert download_queue.is_empty is True
        assert download_queue.is_full is False

        # Test with full queue
        full_queue = DownloadQueue(max_size=1)
        asyncio.run(full_queue.add_task(sample_task))
        assert full_queue.is_full is True
        assert full_queue.is_empty is False

    @pytest.mark.asyncio
    async def test_add_task_success(self, download_queue, sample_task):
        """Test successfully adding a task to the queue."""
        result = await download_queue.add_task(sample_task)

        assert result is True
        assert download_queue.size == 1
        assert download_queue.pending_count == 1
        assert sample_task.task_id in download_queue._tasks

    @pytest.mark.asyncio
    async def test_add_task_queue_full(self, sample_task):
        """Test adding task to full queue."""
        queue = DownloadQueue(max_size=1)

        # Add first task
        result1 = await queue.add_task(sample_task)
        assert result1 is True

        # Try to add second task to full queue
        task2 = DownloadTask(
            content_id="test2",
            content_type=ContentType.TRACK,
            source="test",
            title="Test 2",
            url="https://example.com/test2",
            file_path="/path/to/test2.mp3",
        )
        result2 = await queue.add_task(task2)
        assert result2 is False
        assert queue.size == 1

    @pytest.mark.asyncio
    async def test_add_task_with_dependencies(self, download_queue):
        """Test adding task with dependencies."""
        # Create task with dependency
        task = DownloadTask(
            content_id="test",
            content_type=ContentType.TRACK,
            source="test",
            title="Test",
            url="https://example.com/test",
            file_path="/path/to/test.mp3",
        )
        task.add_dependency(uuid4())

        result = await download_queue.add_task(task)

        assert result is True
        assert download_queue.size == 1
        assert (
            download_queue.pending_count == 0
        )  # Not added to pending queue due to dependency

    @pytest.mark.asyncio
    async def test_get_next_task_success(self, download_queue, sample_task):
        """Test getting next task from queue."""
        await download_queue.add_task(sample_task)

        next_task = await download_queue.get_next_task()

        assert next_task is not None
        assert next_task.task_id == sample_task.task_id
        assert next_task.state == DownloadState.DOWNLOADING
        assert next_task.started_at is not None
        assert download_queue.active_count == 1
        assert download_queue.pending_count == 0

    @pytest.mark.asyncio
    async def test_get_next_task_empty_queue(self, download_queue):
        """Test getting next task from empty queue."""
        next_task = await download_queue.get_next_task()
        assert next_task is None

    @pytest.mark.asyncio
    async def test_get_next_task_priority_order(self, download_queue):
        """Test that tasks are returned in priority order."""
        # Create tasks with different priorities
        low_priority_task = DownloadTask(
            content_id="low",
            content_type=ContentType.TRACK,
            source="test",
            title="Low Priority",
            url="https://example.com/low",
            file_path="/path/to/low.mp3",
            priority=DownloadPriority.LOW,
        )

        high_priority_task = DownloadTask(
            content_id="high",
            content_type=ContentType.TRACK,
            source="test",
            title="High Priority",
            url="https://example.com/high",
            file_path="/path/to/high.mp3",
            priority=DownloadPriority.HIGH,
        )

        # Add low priority first, then high priority
        await download_queue.add_task(low_priority_task)
        await download_queue.add_task(high_priority_task)

        # High priority should come first
        first_task = await download_queue.get_next_task()
        assert first_task.content_id == "high"

        second_task = await download_queue.get_next_task()
        assert second_task.content_id == "low"

    @pytest.mark.asyncio
    async def test_complete_task(self, download_queue, sample_task):
        """Test completing a task."""
        await download_queue.add_task(sample_task)
        task = await download_queue.get_next_task()

        result = await download_queue.complete_task(task.task_id)

        assert result is True
        assert task.state == DownloadState.COMPLETED
        assert task.completed_at is not None
        assert task.progress_percentage == 100.0
        assert download_queue.active_count == 0
        assert download_queue.completed_count == 1

    @pytest.mark.asyncio
    async def test_complete_nonexistent_task(self, download_queue):
        """Test completing a non-existent task."""
        result = await download_queue.complete_task(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_fail_task_with_retry(self, download_queue, sample_task):
        """Test failing a task that can be retried."""
        await download_queue.add_task(sample_task)
        task = await download_queue.get_next_task()

        error_message = "Network error"
        result = await download_queue.fail_task(task.task_id, error_message)

        assert result is True
        assert task.state == DownloadState.FAILED
        assert task.error_message == error_message
        assert task.retry_count == 1
        assert download_queue.active_count == 0
        assert download_queue.pending_count == 1  # Re-queued for retry

    @pytest.mark.asyncio
    async def test_fail_task_no_retry(self, download_queue, sample_task):
        """Test failing a task that cannot be retried."""
        await download_queue.add_task(sample_task)
        task = await download_queue.get_next_task()

        # Exhaust retries
        task.retry_count = 3

        error_message = "Final failure"
        result = await download_queue.fail_task(task.task_id, error_message)

        assert result is True
        assert task.state == DownloadState.FAILED
        assert download_queue.active_count == 0
        assert download_queue.failed_count == 1
        assert download_queue.pending_count == 0  # Not re-queued

    @pytest.mark.asyncio
    async def test_cancel_task(self, download_queue, sample_task):
        """Test cancelling a task."""
        await download_queue.add_task(sample_task)
        task = await download_queue.get_next_task()

        result = await download_queue.cancel_task(task.task_id)

        assert result is True
        assert task.state == DownloadState.CANCELLED
        assert download_queue.active_count == 0

    @pytest.mark.asyncio
    async def test_remove_task(self, download_queue, sample_task):
        """Test removing a task from the queue."""
        await download_queue.add_task(sample_task)

        result = await download_queue.remove_task(sample_task.task_id)

        assert result is True
        assert download_queue.size == 0
        assert sample_task.task_id not in download_queue._tasks

    @pytest.mark.asyncio
    async def test_remove_nonexistent_task(self, download_queue):
        """Test removing a non-existent task."""
        result = await download_queue.remove_task(uuid4())
        assert result is False

    def test_get_task(self, download_queue, sample_task):
        """Test getting a task by ID."""
        asyncio.run(download_queue.add_task(sample_task))

        retrieved_task = download_queue.get_task(sample_task.task_id)
        assert retrieved_task is not None
        assert retrieved_task.task_id == sample_task.task_id

        # Test with non-existent ID
        nonexistent_task = download_queue.get_task(uuid4())
        assert nonexistent_task is None

    @pytest.mark.asyncio
    async def test_get_tasks_by_state(self, download_queue):
        """Test getting tasks by state."""
        # Create tasks with different states
        pending_task = DownloadTask(
            content_id="pending",
            content_type=ContentType.TRACK,
            source="test",
            title="Pending",
            url="https://example.com/pending",
            file_path="/path/to/pending.mp3",
        )

        completed_task = DownloadTask(
            content_id="completed",
            content_type=ContentType.TRACK,
            source="test",
            title="Completed",
            url="https://example.com/completed",
            file_path="/path/to/completed.mp3",
        )
        completed_task.mark_completed()

        await download_queue.add_task(pending_task)
        await download_queue.add_task(completed_task)

        pending_tasks = download_queue.get_tasks_by_state(DownloadState.PENDING)
        completed_tasks = download_queue.get_tasks_by_state(DownloadState.COMPLETED)

        assert len(pending_tasks) == 1
        assert pending_tasks[0].content_id == "pending"
        assert len(completed_tasks) == 1
        assert completed_tasks[0].content_id == "completed"

    @pytest.mark.asyncio
    async def test_get_tasks_by_content_type(self, download_queue):
        """Test getting tasks by content type."""
        track_task = DownloadTask(
            content_id="track",
            content_type=ContentType.TRACK,
            source="test",
            title="Track",
            url="https://example.com/track",
            file_path="/path/to/track.mp3",
        )

        album_task = DownloadTask(
            content_id="album",
            content_type=ContentType.ALBUM,
            source="test",
            title="Album",
            url="https://example.com/album",
            file_path="/path/to/album",
        )

        await download_queue.add_task(track_task)
        await download_queue.add_task(album_task)

        track_tasks = download_queue.get_tasks_by_content_type(ContentType.TRACK)
        album_tasks = download_queue.get_tasks_by_content_type(ContentType.ALBUM)

        assert len(track_tasks) == 1
        assert track_tasks[0].content_id == "track"
        assert len(album_tasks) == 1
        assert album_tasks[0].content_id == "album"

    @pytest.mark.asyncio
    async def test_get_all_tasks(self, download_queue, sample_task):
        """Test getting all tasks."""
        await download_queue.add_task(sample_task)

        all_tasks = download_queue.get_all_tasks()
        assert len(all_tasks) == 1
        assert all_tasks[0].task_id == sample_task.task_id

    @pytest.mark.asyncio
    async def test_clear_completed(self, download_queue):
        """Test clearing completed tasks."""
        # Add completed task
        completed_task = DownloadTask(
            content_id="completed",
            content_type=ContentType.TRACK,
            source="test",
            title="Completed",
            url="https://example.com/completed",
            file_path="/path/to/completed.mp3",
        )
        await download_queue.add_task(completed_task)
        await download_queue.complete_task(completed_task.task_id)

        # Add pending task
        pending_task = DownloadTask(
            content_id="pending",
            content_type=ContentType.TRACK,
            source="test",
            title="Pending",
            url="https://example.com/pending",
            file_path="/path/to/pending.mp3",
        )
        await download_queue.add_task(pending_task)

        cleared_count = await download_queue.clear_completed()

        assert cleared_count == 1
        assert download_queue.size == 1  # Only pending task remains
        assert download_queue.completed_count == 0

    @pytest.mark.asyncio
    async def test_clear_failed(self, download_queue):
        """Test clearing failed tasks."""
        # Add failed task
        failed_task = DownloadTask(
            content_id="failed",
            content_type=ContentType.TRACK,
            source="test",
            title="Failed",
            url="https://example.com/failed",
            file_path="/path/to/failed.mp3",
        )
        failed_task.retry_count = 3  # Prevent retry
        await download_queue.add_task(failed_task)
        task = await download_queue.get_next_task()
        await download_queue.fail_task(task.task_id, "Error")

        # Add pending task
        pending_task = DownloadTask(
            content_id="pending",
            content_type=ContentType.TRACK,
            source="test",
            title="Pending",
            url="https://example.com/pending",
            file_path="/path/to/pending.mp3",
        )
        await download_queue.add_task(pending_task)

        cleared_count = await download_queue.clear_failed()

        assert cleared_count == 1
        assert download_queue.size == 1  # Only pending task remains
        assert download_queue.failed_count == 0

    @pytest.mark.asyncio
    async def test_clear_all(self, download_queue, sample_task):
        """Test clearing all tasks."""
        await download_queue.add_task(sample_task)

        cleared_count = await download_queue.clear_all()

        assert cleared_count == 1
        assert download_queue.size == 0
        assert download_queue.pending_count == 0
        assert download_queue.active_count == 0
        assert download_queue.completed_count == 0
        assert download_queue.failed_count == 0

    def test_callback_registration(self, download_queue):
        """Test registering callbacks."""
        added_callback = MagicMock()
        completed_callback = MagicMock()
        failed_callback = MagicMock()

        download_queue.add_task_added_callback(added_callback)
        download_queue.add_task_completed_callback(completed_callback)
        download_queue.add_task_failed_callback(failed_callback)

        assert added_callback in download_queue._task_added_callbacks
        assert completed_callback in download_queue._task_completed_callbacks
        assert failed_callback in download_queue._task_failed_callbacks

    @pytest.mark.asyncio
    async def test_callback_execution(self, download_queue, sample_task):
        """Test that callbacks are executed."""
        added_callback = MagicMock()
        completed_callback = MagicMock()
        failed_callback = MagicMock()

        download_queue.add_task_added_callback(added_callback)
        download_queue.add_task_completed_callback(completed_callback)
        download_queue.add_task_failed_callback(failed_callback)

        # Test added callback
        await download_queue.add_task(sample_task)
        added_callback.assert_called_once_with(sample_task)

        # Test completed callback
        task = await download_queue.get_next_task()
        await download_queue.complete_task(task.task_id)
        completed_callback.assert_called_once_with(task)

        # Test failed callback
        failed_task = DownloadTask(
            content_id="failed",
            content_type=ContentType.TRACK,
            source="test",
            title="Failed",
            url="https://example.com/failed",
            file_path="/path/to/failed.mp3",
        )
        await download_queue.add_task(failed_task)
        task = await download_queue.get_next_task()
        error_message = "Test error"
        await download_queue.fail_task(task.task_id, error_message)
        failed_callback.assert_called_once_with(task, error_message)

    @pytest.mark.asyncio
    async def test_dependency_resolution(self, download_queue):
        """Test that dependent tasks become ready when dependencies complete."""
        # Create dependency task
        dependency_task = DownloadTask(
            content_id="dependency",
            content_type=ContentType.TRACK,
            source="test",
            title="Dependency",
            url="https://example.com/dependency",
            file_path="/path/to/dependency.mp3",
        )

        # Create dependent task
        dependent_task = DownloadTask(
            content_id="dependent",
            content_type=ContentType.TRACK,
            source="test",
            title="Dependent",
            url="https://example.com/dependent",
            file_path="/path/to/dependent.mp3",
        )
        dependent_task.add_dependency(dependency_task.task_id)

        await download_queue.add_task(dependency_task)
        await download_queue.add_task(dependent_task)

        # Initially, only dependency task should be pending
        assert download_queue.pending_count == 1

        # Complete dependency task
        task = await download_queue.get_next_task()
        assert task.task_id == dependency_task.task_id
        await download_queue.complete_task(task.task_id)

        # Now dependent task should be pending
        assert download_queue.pending_count == 1

        # Get dependent task
        next_task = await download_queue.get_next_task()
        assert next_task.task_id == dependent_task.task_id
        assert len(next_task.depends_on) == 0  # Dependency should be removed

    def test_get_queue_stats(self, download_queue):
        """Test getting queue statistics."""
        stats = download_queue.get_queue_stats()

        expected_stats = {
            "total_tasks": 0,
            "pending_tasks": 0,
            "active_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "queue_capacity": 100,
            "queue_utilization": 0.0,
        }

        assert stats == expected_stats

    @pytest.mark.asyncio
    async def test_queue_stats_with_tasks(self, download_queue, sample_task):
        """Test queue statistics with tasks."""
        await download_queue.add_task(sample_task)
        task = await download_queue.get_next_task()
        await download_queue.complete_task(task.task_id)

        stats = download_queue.get_queue_stats()

        assert stats["total_tasks"] == 1
        assert stats["pending_tasks"] == 0
        assert stats["active_tasks"] == 0
        assert stats["completed_tasks"] == 1
        assert stats["failed_tasks"] == 0
        assert stats["queue_utilization"] == 1.0  # 1/100 * 100

    @pytest.mark.asyncio
    async def test_callback_exception_handling(self, download_queue, sample_task):
        """Test that callback exceptions don't break queue operations."""

        def failing_callback(task):
            msg = "Callback failed"
            raise Exception(msg)

        download_queue.add_task_added_callback(failing_callback)

        # Should not raise exception despite callback failure
        result = await download_queue.add_task(sample_task)
        assert result is True
        assert download_queue.size == 1
