"""
性能测试
"""

import pytest
import time
import asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.core.performance import performance_optimizer, database_optimizer
from app.core.async_optimizer import async_optimizer, concurrency_optimizer
from app.core.optimized_queries import optimized_queries


class TestPerformanceOptimizer:
    """性能优化器测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_slow_queries(self):
        """测试慢查询分析"""
        with patch('app.core.performance.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock查询结果
            mock_result = AsyncMock()
            mock_result.fetchall.return_value = [
                ("SELECT * FROM users", 5, 1500.0, 300.0, 500.0, 50.0)
            ]
            mock_session.execute.return_value = mock_result
            
            result = await performance_optimizer.analyze_slow_queries(threshold=1.0)
            
            assert result["slow_queries_count"] == 1
            assert len(result["slow_queries"]) == 1
            assert result["slow_queries"][0]["mean_time_ms"] == 300.0
    
    @pytest.mark.asyncio
    async def test_optimize_database_indexes(self):
        """测试数据库索引优化"""
        with patch('app.core.performance.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            result = await performance_optimizer.optimize_database_indexes()
            
            assert "suggestions" in result
            assert "total_suggestions" in result
    
    @pytest.mark.asyncio
    async def test_batch_process_records(self):
        """测试批量处理记录"""
        # Mock查询函数
        async def mock_query_func(db, offset, batch_size):
            if offset == 0:
                return [{"id": 1}, {"id": 2}]
            return []  # 没有更多记录
        
        # Mock处理函数
        async def mock_process_func(db, record):
            await asyncio.sleep(0.01)  # 模拟处理时间
            return record
        
        result = await performance_optimizer.batch_process_records(
            query_func=mock_query_func,
            process_func=mock_process_func,
            batch_size=10
        )
        
        assert result["processed_count"] == 2
        assert result["error_count"] == 0
        assert result["records_per_second"] > 0


class TestDatabaseOptimizer:
    """数据库优化器测试"""
    
    @pytest.mark.asyncio
    async def test_vacuum_analyze_tables(self):
        """测试表清理和分析"""
        with patch('app.core.performance.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.execute = AsyncMock()
            
            result = await database_optimizer.vacuum_analyze_tables()
            
            assert "results" in result
            assert "completed_at" in result
    
    @pytest.mark.asyncio
    async def test_update_table_statistics(self):
        """测试更新表统计信息"""
        with patch('app.core.performance.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.execute = AsyncMock()
            
            result = await database_optimizer.update_table_statistics()
            
            assert result["status"] == "success"
            assert "completed_at" in result
    
    @pytest.mark.asyncio
    async def test_reindex_tables(self):
        """测试重建索引"""
        tables = ["users", "meetings"]
        
        with patch('app.core.performance.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.execute = AsyncMock()
            
            result = await database_optimizer.reindex_tables(tables)
            
            assert "results" in result
            assert len(result["results"]) == 2


class TestAsyncOptimizer:
    """异步优化器测试"""
    
    @pytest.mark.asyncio
    async def test_submit_task(self):
        """测试提交异步任务"""
        async def test_task(x, y):
            await asyncio.sleep(0.1)
            return x + y
        
        task_id = await async_optimizer.submit_task(
            func=test_task,
            args=(1, 2),
            timeout=5.0
        )
        
        assert task_id is not None
        assert task_id.startswith("task_")
    
    @pytest.mark.asyncio
    async def test_get_task_status(self):
        """测试获取任务状态"""
        # 添加一个完成的任务到测试中
        task_id = "test_task_123"
        async_optimizer.completed_tasks[task_id] = {
            "result": "test_result",
            "execution_time": 0.5,
            "completed_at": "2024-01-01T12:00:00Z"
        }
        
        status = await async_optimizer.get_task_status(task_id)
        
        assert status["status"] == "completed"
        assert status["result"] == "test_result"
    
    @pytest.mark.asyncio
    async def test_get_queue_status(self):
        """测试获取队列状态"""
        status = await async_optimizer.get_queue_status()
        
        assert "queue_size" in status
        assert "running_tasks" in status
        assert "completed_tasks" in status
        assert "failed_tasks" in status


class TestConcurrencyOptimizer:
    """并发优化器测试"""
    
    @pytest.mark.asyncio
    async def test_parallel_execute(self):
        """测试并行执行"""
        async def test_func(item):
            await asyncio.sleep(0.01)
            return item * 2
        
        items = [1, 2, 3, 4, 5]
        
        start_time = time.time()
        results = await concurrency_optimizer.parallel_execute(
            func=test_func,
            items=items,
            max_concurrent=3
        )
        end_time = time.time()
        
        assert len(results) == 5
        assert results == [2, 4, 6, 8, 10]
        # 并行执行应该比串行执行快
        assert end_time - start_time < 0.1
    
    @pytest.mark.asyncio
    async def test_throttle_decorator(self):
        """测试限流装饰器"""
        @concurrency_optimizer.throttle(calls_per_second=5)
        async def throttled_func():
            return "result"
        
        start_time = time.time()
        
        # 连续调用多次
        results = []
        for _ in range(3):
            result = await throttled_func()
            results.append(result)
        
        end_time = time.time()
        
        assert len(results) == 3
        assert all(r == "result" for r in results)
        # 限流应该增加执行时间
        assert end_time - start_time >= 0.4  # 3次调用，每次间隔0.2秒
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self):
        """测试熔断器"""
        call_count = 0
        
        @concurrency_optimizer.circuit_breaker(failure_threshold=2, recovery_timeout=1)
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Test failure")
            return "success"
        
        # 前两次调用应该失败
        with pytest.raises(Exception, match="Test failure"):
            await failing_func()
        
        with pytest.raises(Exception, match="Test failure"):
            await failing_func()
        
        # 第三次调用触发熔断器
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await failing_func()


class TestOptimizedQueries:
    """优化查询测试"""
    
    @pytest.mark.asyncio
    async def test_cached_query_execution(self, db_session):
        """测试缓存查询执行"""
        with patch.object(optimized_queries.optimizer, 'cache_enabled', True):
            with patch('app.core.cache.cache_manager.get') as mock_get:
                with patch('app.core.cache.cache_manager.set') as mock_set:
                    # 第一次调用 - 缓存未命中
                    mock_get.return_value = None
                    
                    @optimized_queries.optimizer.cache_query("test_query", ttl=300)
                    async def test_query():
                        return {"data": "test_result"}
                    
                    result1 = await test_query()
                    
                    assert result1 == {"data": "test_result"}
                    mock_set.assert_called_once()
                    
                    # 第二次调用 - 缓存命中
                    mock_get.return_value = {"data": "cached_result"}
                    
                    result2 = await test_query()
                    
                    assert result2 == {"data": "cached_result"}


class TestPerformanceMetrics:
    """性能指标测试"""
    
    @pytest.mark.asyncio
    async def test_query_execution_time_tracking(self):
        """测试查询执行时间追踪"""
        with patch('app.core.monitoring.metrics_collector.record_metric') as mock_metric:
            with patch('app.core.cache.cache_manager.get') as mock_get:
                mock_get.return_value = None  # 缓存未命中
                
                async def slow_query():
                    await asyncio.sleep(0.1)  # 模拟慢查询
                    return "result"
                
                result = await performance_optimizer.optimize_query_performance(
                    query_func=slow_query,
                    cache_key="test_slow_query"
                )
                
                assert result == "result"
                
                # 验证指标被记录
                mock_metric.assert_any_call("query_cache_miss", 1.0)
                
                # 检查是否记录了执行时间
                execution_time_calls = [
                    call for call in mock_metric.call_args_list 
                    if call[0][0] == "query_execution_time"
                ]
                assert len(execution_time_calls) == 1
                assert execution_time_calls[0][0][1] >= 0.1  # 执行时间应该≥0.1秒
    
    @pytest.mark.asyncio
    async def test_slow_query_detection(self):
        """测试慢查询检测"""
        with patch('app.core.monitoring.metrics_collector.record_metric') as mock_metric:
            with patch('app.core.cache.cache_manager.get') as mock_get:
                mock_get.return_value = None
                
                async def very_slow_query():
                    await asyncio.sleep(2.0)  # 超过慢查询阈值
                    return "result"
                
                await performance_optimizer.optimize_query_performance(
                    query_func=very_slow_query,
                    cache_key="test_very_slow_query"
                )
                
                # 验证慢查询指标被记录
                mock_metric.assert_any_call("slow_query_count", 1.0)


class TestLoadTesting:
    """负载测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_api_requests(self, client: AsyncClient, auth_headers: dict):
        """测试并发API请求"""
        async def make_request():
            response = await client.get("/api/v1/auth/me", headers=auth_headers)
            return response.status_code
        
        # 创建100个并发请求
        tasks = [make_request() for _ in range(100)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # 验证所有请求都成功
        assert all(status == 200 for status in results)
        
        # 验证平均响应时间合理
        avg_response_time = (end_time - start_time) / len(results)
        assert avg_response_time < 0.1  # 每个请求平均响应时间小于100ms
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_database_connection_pool(self, db_session):
        """测试数据库连接池性能"""
        async def db_operation():
            # 模拟数据库操作
            await asyncio.sleep(0.01)
            return True
        
        # 创建多个并发数据库操作
        tasks = [db_operation() for _ in range(50)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        assert all(results)
        assert end_time - start_time < 1.0  # 总时间小于1秒
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cache_performance(self):
        """测试缓存性能"""
        from app.core.cache import cache_manager
        
        # 设置多个缓存项
        start_time = time.time()
        
        set_tasks = []
        for i in range(1000):
            set_tasks.append(cache_manager.set(f"test_key_{i}", f"test_value_{i}"))
        
        await asyncio.gather(*set_tasks)
        set_time = time.time() - start_time
        
        # 获取缓存项
        start_time = time.time()
        
        get_tasks = []
        for i in range(1000):
            get_tasks.append(cache_manager.get(f"test_key_{i}"))
        
        results = await asyncio.gather(*get_tasks)
        get_time = time.time() - start_time
        
        # 验证缓存性能
        assert set_time < 2.0  # 设置1000个键值对应该在2秒内完成
        assert get_time < 1.0   # 获取1000个键值对应该在1秒内完成
        assert all(r == f"test_value_{i}" for i, r in enumerate(results))


class TestMemoryUsage:
    """内存使用测试"""
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        """测试内存泄漏检测"""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 执行大量操作
        for i in range(1000):
            # 创建和销毁对象
            data = {"key": f"value_{i}"}
            del data
        
        # 强制垃圾回收
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 内存增长应该在合理范围内（小于10MB）
        assert memory_increase < 10 * 1024 * 1024
    
    @pytest.mark.asyncio
    async def test_large_data_processing(self):
        """测试大数据处理"""
        # 创建大量测试数据
        large_dataset = [{"id": i, "data": f"test_data_{i}"} for i in range(10000)]
        
        async def process_item(item):
            # 模拟处理
            return item["id"] * 2
        
        start_time = time.time()
        results = await concurrency_optimizer.parallel_execute(
            func=process_item,
            items=large_dataset,
            max_concurrent=50,
            batch_size=100
        )
        end_time = time.time()
        
        assert len(results) == 10000
        assert results[0] == 0
        assert results[999] == 1998
        
        # 处理时间应该合理
        processing_time = end_time - start_time
        assert processing_time < 5.0  # 应该在5秒内完成


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """性能基准测试"""
    
    @pytest.mark.asyncio
    async def test_api_response_time_benchmark(self, client: AsyncClient, auth_headers: dict):
        """API响应时间基准测试"""
        endpoints = [
            "/api/v1/auth/me",
            "/api/v1/meetings/", 
            "/api/v1/notes/"
        ]
        
        response_times = []
        
        for endpoint in endpoints:
            start_time = time.time()
            response = await client.get(endpoint, headers=auth_headers)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            assert response.status_code == 200
            assert response_time < 0.5  # 响应时间应该小于500ms
        
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 0.2  # 平均响应时间小于200ms
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self, db_session):
        """数据库查询性能测试"""
        from sqlalchemy import text
        
        # 测试简单查询性能
        start_time = time.time()
        
        for _ in range(100):
            result = await db_session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 100次简单查询应该在1秒内完成
        assert total_time < 1.0
        
        # 平均查询时间应该很短
        avg_query_time = total_time / 100
        assert avg_query_time < 0.01  # 平均每次查询小于10ms