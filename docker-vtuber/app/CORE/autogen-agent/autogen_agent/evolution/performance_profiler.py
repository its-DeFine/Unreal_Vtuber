"""
Performance Profiler for Darwin-Gödel Machine
Measures actual performance improvements instead of using estimates
"""

import os
import sys
import time
import asyncio
import cProfile
import pstats
import tracemalloc
import tempfile
import subprocess
from io import StringIO
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
import importlib.util
import psutil
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results"""
    execution_time: float  # seconds
    memory_peak: int  # bytes
    memory_allocated: int  # bytes
    cpu_percent: float  # percentage
    success_rate: float  # 0.0 to 1.0
    error_count: int
    profile_data: Optional[str] = None  # cProfile output


@dataclass
class TestCase:
    """Test case for performance measurement"""
    name: str
    setup_code: str
    test_code: str
    expected_output: Any = None
    timeout: float = 30.0  # seconds


class PerformanceProfiler:
    """Measures actual performance of code before and after modifications"""
    
    def __init__(self):
        self.process = psutil.Process()
        self._original_sys_path = sys.path.copy()
        
    async def measure_performance(
        self,
        code: str,
        test_cases: List[TestCase],
        warmup_runs: int = 3,
        measurement_runs: int = 10
    ) -> PerformanceMetrics:
        """
        Measure the performance of code using provided test cases
        
        Args:
            code: The code to measure
            test_cases: List of test cases to run
            warmup_runs: Number of warmup runs before measurement
            measurement_runs: Number of runs to average for measurement
            
        Returns:
            PerformanceMetrics with measurement results
        """
        if not test_cases:
            raise ValueError("At least one test case is required")
        
        # Create a temporary module with the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            module_path = f.name
        
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location("test_module", module_path)
            module = importlib.util.module_from_spec(spec)
            
            # Warmup runs
            for _ in range(warmup_runs):
                await self._run_test_cases(module, spec, test_cases)
            
            # Measurement runs
            metrics_list = []
            for _ in range(measurement_runs):
                metrics = await self._measure_single_run(module, spec, test_cases)
                metrics_list.append(metrics)
            
            # Average the results
            return self._average_metrics(metrics_list)
            
        finally:
            # Cleanup
            os.unlink(module_path)
            sys.path = self._original_sys_path.copy()
    
    async def _run_test_cases(
        self,
        module: Any,
        spec: Any,
        test_cases: List[TestCase]
    ) -> Tuple[int, int]:
        """Run test cases and return success/error counts"""
        success_count = 0
        error_count = 0
        
        for test_case in test_cases:
            try:
                # Reload module for clean state
                spec.loader.exec_module(module)
                
                # Execute setup code
                exec(test_case.setup_code, module.__dict__)
                
                # Execute test code
                exec(test_case.test_code, module.__dict__)
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"Test case '{test_case.name}' failed: {e}")
                error_count += 1
        
        return success_count, error_count
    
    async def _measure_single_run(
        self,
        module: Any,
        spec: Any,
        test_cases: List[TestCase]
    ) -> PerformanceMetrics:
        """Measure a single run of all test cases"""
        # Start memory tracking
        tracemalloc.start()
        
        # CPU usage baseline
        self.process.cpu_percent()  # First call to initialize
        
        # Start timing
        start_time = time.perf_counter()
        
        # Profile the execution
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            success_count, error_count = await self._run_test_cases(module, spec, test_cases)
            
            # Stop profiling
            profiler.disable()
            
            # End timing
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Memory metrics
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # CPU usage
            cpu_percent = self.process.cpu_percent()
            
            # Success rate
            total_tests = len(test_cases)
            success_rate = success_count / total_tests if total_tests > 0 else 0.0
            
            # Get profile data
            s = StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
            ps.print_stats(20)  # Top 20 functions
            profile_data = s.getvalue()
            
            return PerformanceMetrics(
                execution_time=execution_time,
                memory_peak=peak,
                memory_allocated=current,
                cpu_percent=cpu_percent,
                success_rate=success_rate,
                error_count=error_count,
                profile_data=profile_data
            )
            
        except Exception as e:
            logger.error(f"Error during measurement: {e}")
            tracemalloc.stop()
            profiler.disable()
            
            return PerformanceMetrics(
                execution_time=float('inf'),
                memory_peak=0,
                memory_allocated=0,
                cpu_percent=0.0,
                success_rate=0.0,
                error_count=len(test_cases)
            )
    
    def _average_metrics(self, metrics_list: List[PerformanceMetrics]) -> PerformanceMetrics:
        """Average multiple performance measurements"""
        if not metrics_list:
            raise ValueError("No metrics to average")
        
        # Filter out failed runs
        valid_metrics = [m for m in metrics_list if m.execution_time != float('inf')]
        
        if not valid_metrics:
            # All runs failed
            return metrics_list[0]
        
        # Calculate averages
        avg_execution_time = sum(m.execution_time for m in valid_metrics) / len(valid_metrics)
        avg_memory_peak = sum(m.memory_peak for m in valid_metrics) / len(valid_metrics)
        avg_memory_allocated = sum(m.memory_allocated for m in valid_metrics) / len(valid_metrics)
        avg_cpu_percent = sum(m.cpu_percent for m in valid_metrics) / len(valid_metrics)
        avg_success_rate = sum(m.success_rate for m in valid_metrics) / len(valid_metrics)
        total_error_count = sum(m.error_count for m in metrics_list)
        
        # Use profile data from the median run
        median_idx = len(valid_metrics) // 2
        profile_data = valid_metrics[median_idx].profile_data if valid_metrics else None
        
        return PerformanceMetrics(
            execution_time=avg_execution_time,
            memory_peak=int(avg_memory_peak),
            memory_allocated=int(avg_memory_allocated),
            cpu_percent=avg_cpu_percent,
            success_rate=avg_success_rate,
            error_count=total_error_count,
            profile_data=profile_data
        )
    
    async def compare_performance(
        self,
        original_code: str,
        modified_code: str,
        test_cases: List[TestCase]
    ) -> Dict[str, Any]:
        """
        Compare performance between original and modified code
        
        Returns:
            Dictionary with comparison results and improvement percentages
        """
        logger.info("Measuring original code performance...")
        original_metrics = await self.measure_performance(original_code, test_cases)
        
        logger.info("Measuring modified code performance...")
        modified_metrics = await self.measure_performance(modified_code, test_cases)
        
        # Calculate improvements
        time_improvement = self._calculate_improvement(
            original_metrics.execution_time,
            modified_metrics.execution_time
        )
        
        memory_improvement = self._calculate_improvement(
            original_metrics.memory_peak,
            modified_metrics.memory_peak
        )
        
        # Overall improvement score (weighted average)
        overall_improvement = (
            time_improvement * 0.6 +  # Time is most important
            memory_improvement * 0.3 +  # Memory is secondary
            (modified_metrics.success_rate - original_metrics.success_rate) * 0.1  # Correctness
        )
        
        return {
            "original_metrics": original_metrics,
            "modified_metrics": modified_metrics,
            "time_improvement": time_improvement,
            "memory_improvement": memory_improvement,
            "overall_improvement": overall_improvement,
            "is_improvement": overall_improvement > 0.05,  # 5% threshold
            "maintains_correctness": modified_metrics.success_rate >= original_metrics.success_rate
        }
    
    def _calculate_improvement(self, original: float, modified: float) -> float:
        """Calculate percentage improvement (positive means better)"""
        if original == 0:
            return 0.0
        return (original - modified) / original
    
    def generate_test_cases_from_code(self, code: str) -> List[TestCase]:
        """
        Generate basic test cases from code analysis
        
        This is a simple implementation that looks for functions and creates basic tests.
        In production, this should be much more sophisticated.
        """
        test_cases = []
        
        # Parse the code to find functions
        try:
            import ast
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Create a basic test case for each function
                    test_case = self._create_test_for_function(node, code)
                    if test_case:
                        test_cases.append(test_case)
        
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
        
        # If no test cases generated, create a generic one
        if not test_cases:
            test_cases.append(TestCase(
                name="generic_execution",
                setup_code="",
                test_code="# Execute the module",
                timeout=10.0
            ))
        
        return test_cases
    
    def _create_test_for_function(self, func_node: ast.FunctionDef, code: str) -> Optional[TestCase]:
        """Create a test case for a function"""
        func_name = func_node.name
        
        # Skip private functions
        if func_name.startswith('_'):
            return None
        
        # Analyze function parameters
        args = []
        for arg in func_node.args.args:
            # Generate appropriate test values based on parameter names
            arg_name = arg.arg
            if 'list' in arg_name.lower() or 'array' in arg_name.lower():
                args.append('[1, 2, 3, 4, 5]')
            elif 'dict' in arg_name.lower() or 'map' in arg_name.lower():
                args.append("{'key': 'value'}")
            elif 'str' in arg_name.lower() or 'text' in arg_name.lower():
                args.append("'test string'")
            elif 'num' in arg_name.lower() or 'int' in arg_name.lower():
                args.append('42')
            elif 'float' in arg_name.lower():
                args.append('3.14')
            else:
                args.append('None')  # Default
        
        # Create test code
        test_code = f"result = {func_name}({', '.join(args)})"
        
        return TestCase(
            name=f"test_{func_name}",
            setup_code="",
            test_code=test_code,
            timeout=5.0
        )