"""
TaskScheduler 任务调度器测试

测试任务调度器的核心功能：
- 初始化和关闭
- 任务注册和调度
- 写锁保护
- 错误处理
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from iris_memory.tasks.scheduler import TaskScheduler


class TestTaskScheduler:
    """TaskScheduler 测试类"""
    
    @pytest.fixture
    def scheduler(self):
        """创建 TaskScheduler 实例"""
        return TaskScheduler()
    
    @pytest.mark.asyncio
    async def test_initialize(self, scheduler):
        """测试初始化"""
        await scheduler.initialize()
        
        assert scheduler.is_available is True
        assert scheduler._task_queue is not None
        assert scheduler._running is True
        assert "_queue_processor" in scheduler._tasks
        
        # 清理
        await scheduler.shutdown()
    
    @pytest.mark.asyncio
    async def test_shutdown(self, scheduler):
        """测试关闭"""
        await scheduler.initialize()
        await scheduler.shutdown()
        
        assert scheduler.is_available is False
        assert scheduler._running is False
        assert len(scheduler._tasks) == 0
    
    @pytest.mark.asyncio
    async def test_register_periodic_task(self, scheduler):
        """测试注册周期性任务"""
        await scheduler.initialize()
        
        # 创建模拟任务函数
        task_func = AsyncMock()
        
        # 注册任务
        scheduler.register_periodic_task(
            task_name="test_task",
            coro_func=task_func,
            interval_hours=1
        )
        
        assert "test_task" in scheduler._tasks
        assert scheduler.is_task_running("test_task") is True
        
        # 清理
        await scheduler.shutdown()
    
    @pytest.mark.asyncio
    async def test_periodic_task_execution(self, scheduler):
        """测试周期性任务执行"""
        await scheduler.initialize()
        
        # 创建模拟任务函数
        call_count = 0
        
        async def task_func():
            nonlocal call_count
            call_count += 1
        
        # 注册任务（短间隔以便测试）
        scheduler.register_periodic_task(
            task_name="test_task",
            coro_func=task_func,
            interval_hours=0.001  # 3.6 秒
        )
        
        # 等待任务执行
        await asyncio.sleep(0.5)
        
        # 验证任务被执行
        assert call_count >= 1
        
        # 清理
        await scheduler.shutdown()
    
    @pytest.mark.asyncio
    async def test_task_error_handling(self, scheduler):
        """测试任务错误处理"""
        await scheduler.initialize()
        
        # 创建会抛出异常的任务函数
        async def failing_task():
            raise RuntimeError("Test error")
        
        # 注册任务
        scheduler.register_periodic_task(
            task_name="failing_task",
            coro_func=failing_task,
            interval_hours=0.001
        )
        
        # 等待任务执行（不应崩溃）
        await asyncio.sleep(0.5)
        
        # 验证调度器仍在运行
        assert scheduler.is_available is True
        
        # 清理
        await scheduler.shutdown()
    
    @pytest.mark.asyncio
    async def test_write_lock(self, scheduler):
        """测试写锁保护"""
        await scheduler.initialize()
        
        # 获取写锁
        lock = scheduler.write_lock
        
        assert lock is not None
        assert isinstance(lock, asyncio.Lock)
        
        # 测试锁的获取和释放
        async with lock:
            assert lock.locked() is True
        
        assert lock.locked() is False
        
        # 清理
        await scheduler.shutdown()
    
    @pytest.mark.asyncio
    async def test_schedule_task(self, scheduler):
        """测试一次性任务调度"""
        await scheduler.initialize()
        
        # 创建模拟任务函数
        task_func = AsyncMock()
        
        # 调度任务
        await scheduler.schedule_task("one_time_task", task_func)
        
        # 等待任务执行
        await asyncio.sleep(1.5)
        
        # 验证任务被执行
        task_func.assert_called_once()
        
        # 清理
        await scheduler.shutdown()
    
    @pytest.mark.asyncio
    async def test_set_component_manager(self, scheduler):
        """测试设置组件管理器"""
        from iris_memory.core import ComponentManager
        
        # 创建模拟组件管理器
        mock_manager = Mock(spec=ComponentManager)
        
        # 设置组件管理器
        scheduler.set_component_manager(mock_manager)
        
        assert scheduler._component_manager is mock_manager
    
    @pytest.mark.asyncio
    async def test_multiple_tasks(self, scheduler):
        """测试多个任务并行"""
        await scheduler.initialize()
        
        # 创建多个模拟任务函数
        task1_calls = 0
        task2_calls = 0
        
        async def task_func1():
            nonlocal task1_calls
            task1_calls += 1
        
        async def task_func2():
            nonlocal task2_calls
            task2_calls += 1
        
        # 注册两个任务
        scheduler.register_periodic_task("task1", task_func1, 0.001)
        scheduler.register_periodic_task("task2", task_func2, 0.001)
        
        # 等待任务执行
        await asyncio.sleep(0.5)
        
        # 验证两个任务都被执行
        assert task1_calls >= 1
        assert task2_calls >= 1
        
        # 清理
        await scheduler.shutdown()
