"""
Statistics Collector for Autonomous Agent System
Handles collection and persistence of all system metrics
"""
import asyncio
import json
import time
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import asyncpg
import logging

logger = logging.getLogger(__name__)


class StatisticsCollector:
    """
    Centralized statistics collection and persistence
    """
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.buffer = []  # Batch writes
        self.buffer_size = int(os.getenv('STATISTICS_BATCH_SIZE', '100'))
        self.flush_interval = 5.0  # seconds
        self.pool = None
        self._flush_task = None
        self._last_flush = time.time()
        
    async def initialize(self):
        """Initialize database connection pool and start flush task"""
        try:
            # Parse database URL and create connection pool
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=10,
                timeout=30
            )
            
            # Start background flush task
            self._flush_task = asyncio.create_task(self._periodic_flush())
            
            logger.info("📊 [STATISTICS] Collector initialized with database pool")
            
        except Exception as e:
            logger.error(f"❌ [STATISTICS] Failed to initialize: {e}")
            raise
            
    async def close(self):
        """Clean up resources"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
                
        # Flush remaining buffer
        await self._flush_buffer()
        
        if self.pool:
            await self.pool.close()
            
    async def collect_cycle_stats(self, cycle_data: Dict):
        """Collect statistics for each decision cycle"""
        stats = {
            "timestamp": datetime.utcnow(),
            "iteration": cycle_data.get("iteration"),
            "cycle_duration": cycle_data.get("duration"),
            "agents_participated": json.dumps(cycle_data.get("agents", [])),
            "tools_executed": cycle_data.get("tools_executed", 0),
            "success": cycle_data.get("success", False),
            "error_count": cycle_data.get("errors", 0),
            "memory_usage": self._get_memory_usage(),
            "decision_time": cycle_data.get("decision_time", 0.0)
        }
        
        await self._add_to_buffer('performance_metrics', stats)
        
        # Update daily summary
        await self._update_statistics_summary(stats)
        
    async def collect_tool_usage(self, tool_data: Dict):
        """Collect tool execution statistics"""
        usage = {
            "timestamp": datetime.utcnow(),
            "tool_name": tool_data.get("tool"),
            "execution_time": tool_data.get("execution_time"),
            "success": tool_data.get("success", False),
            "input_context": json.dumps(tool_data.get("context", {})),
            "output_result": json.dumps(tool_data.get("result", {})),
            "agent_id": tool_data.get("agent", "system"),
            "selection_score": tool_data.get("score", 0.0),
            "iteration": tool_data.get("iteration", 0)
        }
        
        await self._persist_tool_usage(usage)
        
    async def collect_evolution_action(self, evolution_data: Dict):
        """Track evolution engine actions"""
        record = {
            "id": evolution_data.get("id"),
            "timestamp": datetime.utcnow(),
            "target_file": evolution_data.get("target_file"),
            "modification_type": evolution_data.get("modification_type"),
            "expected_improvement": evolution_data.get("expected_improvement", 0.0),
            "risk_level": evolution_data.get("risk_level", "medium"),
            "backup_path": evolution_data.get("backup_path"),
            "status": evolution_data.get("status", "pending"),
            "performance_impact": json.dumps(evolution_data.get("performance_impact", {}))
        }
        
        await self._persist_evolution_history(record)
        
    async def update_evolution_result(self, evolution_result: Dict):
        """Update evolution record with actual results"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE evolution_history 
                SET actual_improvement = $1,
                    status = $2,
                    performance_impact = $3
                WHERE id = $4
            """, 
            evolution_result.get("actual_improvement", 0.0),
            evolution_result.get("status", "completed"),
            json.dumps(evolution_result.get("performance_impact", {})),
            evolution_result.get("id")
            )
            
    async def get_statistics(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """Get comprehensive statistics with filtering"""
        async with self.pool.acquire() as conn:
            # Build date filter
            date_filter = ""
            params = []
            param_count = 0
            
            if start_date:
                param_count += 1
                date_filter += f" WHERE timestamp >= ${param_count}"
                params.append(datetime.fromisoformat(start_date))
                
            if end_date:
                param_count += 1
                connector = " AND " if date_filter else " WHERE "
                date_filter += f"{connector}timestamp <= ${param_count}"
                params.append(datetime.fromisoformat(end_date))
                
            # Get summary statistics
            summary_query = f"""
                SELECT 
                    COUNT(*) as total_cycles,
                    AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
                    AVG(decision_time) as avg_decision_time,
                    SUM(tools_executed) as total_tools_executed,
                    AVG(memory_usage) as avg_memory_usage,
                    SUM(error_count) as total_errors
                FROM performance_metrics
                {date_filter}
            """
            
            summary = await conn.fetchrow(summary_query, *params)
            
            # Get tool statistics
            tool_stats = await conn.fetch(f"""
                SELECT 
                    tool_name,
                    COUNT(*) as usage_count,
                    AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
                    AVG(execution_time) as avg_execution_time
                FROM tool_usage
                {date_filter}
                GROUP BY tool_name
                ORDER BY usage_count DESC
            """, *params)
            
            # Get agent statistics
            agent_stats = await conn.fetch(f"""
                SELECT 
                    agent_id,
                    COUNT(*) as participation_count,
                    AVG(decision_quality) as avg_quality,
                    AVG(response_time) as avg_response_time
                FROM agent_metrics
                {date_filter}
                GROUP BY agent_id
            """, *params)
            
            # Get evolution statistics
            evolution_stats = await conn.fetchrow(f"""
                SELECT 
                    COUNT(*) as total_modifications,
                    COUNT(CASE WHEN status = 'applied' THEN 1 END) as successful_modifications,
                    AVG(actual_improvement) as avg_improvement
                FROM evolution_history
                {date_filter}
            """, *params)
            
            return {
                "total_cycles": summary['total_cycles'] or 0,
                "success_rate": float(summary['success_rate'] or 0),
                "avg_decision_time": float(summary['avg_decision_time'] or 0),
                "total_tools_executed": summary['total_tools_executed'] or 0,
                "avg_memory_usage": float(summary['avg_memory_usage'] or 0),
                "total_errors": summary['total_errors'] or 0,
                "tool_statistics": [dict(row) for row in tool_stats],
                "agent_statistics": [dict(row) for row in agent_stats],
                "evolution_statistics": dict(evolution_stats) if evolution_stats else {},
                "performance_trend": await self._calculate_performance_trend()
            }
            
    async def get_tool_usage(self, tool_name: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get detailed tool usage analytics"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    tool_name,
                    COUNT(*) as usage_count,
                    AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
                    AVG(execution_time) as avg_time,
                    MAX(execution_time) as max_time,
                    MIN(execution_time) as min_time
                FROM tool_usage
            """
            
            if tool_name:
                query += " WHERE tool_name = $1"
                query += " GROUP BY tool_name ORDER BY usage_count DESC LIMIT $2"
                results = await conn.fetch(query, tool_name, limit)
            else:
                query += " GROUP BY tool_name ORDER BY usage_count DESC LIMIT $1"
                results = await conn.fetch(query, limit)
                
            return [dict(row) for row in results]
            
    async def get_evolution_history(self) -> List[Dict]:
        """Get history of all evolution changes"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT * FROM evolution_history
                ORDER BY timestamp DESC
                LIMIT 1000
            """)
            
            return [dict(row) for row in results]
            
    async def generate_report(self, report_type: str, timeframe: str, filters: Dict) -> Dict:
        """Generate custom analytics report"""
        # Calculate date range based on timeframe
        end_date = datetime.utcnow()
        if timeframe == "24h":
            start_date = end_date - timedelta(days=1)
        elif timeframe == "7d":
            start_date = end_date - timedelta(days=7)
        elif timeframe == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=1)
            
        # Get statistics for timeframe
        stats = await self.get_statistics(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        # Build report based on type
        if report_type == "comprehensive":
            return {
                "report_type": report_type,
                "timeframe": timeframe,
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_cycles": stats['total_cycles'],
                    "success_rate": stats['success_rate'],
                    "avg_decision_time": stats['avg_decision_time'],
                    "total_tools_executed": stats['total_tools_executed']
                },
                "tools": stats['tool_statistics'][:10],  # Top 10 tools
                "agents": stats['agent_statistics'],
                "evolution": stats['evolution_statistics'],
                "performance_trend": stats['performance_trend']
            }
        elif report_type == "tools":
            return {
                "report_type": report_type,
                "timeframe": timeframe,
                "generated_at": datetime.utcnow().isoformat(),
                "tool_analysis": stats['tool_statistics']
            }
        else:
            return stats
            
    # Private helper methods
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
        
    async def _add_to_buffer(self, table: str, data: Dict):
        """Add data to buffer for batch writing"""
        self.buffer.append((table, data))
        
        # Flush if buffer is full
        if len(self.buffer) >= self.buffer_size:
            await self._flush_buffer()
            
    async def _flush_buffer(self):
        """Flush buffer to database"""
        if not self.buffer or not self.pool:
            return
            
        try:
            async with self.pool.acquire() as conn:
                # Group by table
                tables = {}
                for table, data in self.buffer:
                    if table not in tables:
                        tables[table] = []
                    tables[table].append(data)
                    
                # Insert for each table
                for table, records in tables.items():
                    if table == 'performance_metrics':
                        await self._insert_performance_metrics(conn, records)
                        
            self.buffer.clear()
            self._last_flush = time.time()
            
        except Exception as e:
            logger.error(f"❌ [STATISTICS] Failed to flush buffer: {e}")
            
    async def _periodic_flush(self):
        """Periodically flush buffer"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                if time.time() - self._last_flush >= self.flush_interval:
                    await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ [STATISTICS] Periodic flush error: {e}")
                
    async def _insert_performance_metrics(self, conn, records: List[Dict]):
        """Batch insert performance metrics"""
        await conn.executemany("""
            INSERT INTO performance_metrics (
                timestamp, iteration, cycle_duration, tools_executed,
                success, error_count, memory_usage, decision_time
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, [(
            r['timestamp'], r['iteration'], r['cycle_duration'], r['tools_executed'],
            r['success'], r['error_count'], r['memory_usage'], r['decision_time']
        ) for r in records])
        
    async def _persist_tool_usage(self, usage: Dict):
        """Persist tool usage immediately (not buffered)"""
        if not self.pool:
            return
            
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tool_usage (
                    timestamp, tool_name, execution_time, success,
                    input_context, output_result, agent_id, selection_score, iteration
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, 
            usage['timestamp'], usage['tool_name'], usage['execution_time'],
            usage['success'], usage['input_context'], usage['output_result'],
            usage['agent_id'], usage['selection_score'], usage['iteration']
            )
            
    async def _persist_evolution_history(self, record: Dict):
        """Persist evolution history record"""
        if not self.pool:
            return
            
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO evolution_history (
                    id, timestamp, target_file, modification_type,
                    expected_improvement, risk_level, backup_path, status,
                    performance_impact
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            record['id'], record['timestamp'], record['target_file'],
            record['modification_type'], record['expected_improvement'],
            record['risk_level'], record['backup_path'], record['status'],
            record['performance_impact']
            )
            
    async def _update_statistics_summary(self, stats: Dict):
        """Update daily statistics summary"""
        if not self.pool:
            return
            
        today = datetime.utcnow().date()
        
        async with self.pool.acquire() as conn:
            # Update or insert summary
            await conn.execute("""
                INSERT INTO statistics_summary (
                    date, total_cycles, successful_cycles, total_tools_executed,
                    avg_decision_time, avg_memory_usage, total_errors
                ) VALUES ($1, 1, $2, $3, $4, $5, $6)
                ON CONFLICT (date) DO UPDATE SET
                    total_cycles = statistics_summary.total_cycles + 1,
                    successful_cycles = statistics_summary.successful_cycles + CASE WHEN $2 THEN 1 ELSE 0 END,
                    total_tools_executed = statistics_summary.total_tools_executed + $3,
                    avg_decision_time = (statistics_summary.avg_decision_time * statistics_summary.total_cycles + $4) / (statistics_summary.total_cycles + 1),
                    avg_memory_usage = (statistics_summary.avg_memory_usage * statistics_summary.total_cycles + $5) / (statistics_summary.total_cycles + 1),
                    total_errors = statistics_summary.total_errors + $6,
                    updated_at = CURRENT_TIMESTAMP
            """,
            today, stats['success'], stats['tools_executed'],
            stats['decision_time'], stats['memory_usage'], stats['error_count']
            )
            
    async def _calculate_performance_trend(self) -> List[Dict]:
        """Calculate performance trend over last 7 days"""
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    date,
                    total_cycles,
                    successful_cycles,
                    avg_decision_time,
                    performance_score
                FROM statistics_summary
                WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY date
            """)
            
            return [dict(row) for row in results]


import os
from datetime import timedelta