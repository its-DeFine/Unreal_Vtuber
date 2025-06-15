"""
Test suite for Darwin-Gödel LLM integration
Verifies that real code generation and performance measurement work
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock

# Set test environment
os.environ['DARWIN_GODEL_REAL_MODIFICATIONS'] = 'false'
os.environ['DARWIN_GODEL_REQUIRE_APPROVAL'] = 'false'

from autogen_agent.evolution.darwin_godel_engine import DarwinGodelEngine
from autogen_agent.evolution.llm_code_generator import LLMCodeGenerator
from autogen_agent.evolution.performance_profiler import PerformanceProfiler, TestCase


class TestDarwinGodelLLM:
    """Test the LLM integration for Darwin-Gödel Machine"""
    
    @pytest.fixture
    def llm_generator(self):
        """Create LLM generator instance"""
        return LLMCodeGenerator(temperature=0.1)
    
    @pytest.fixture
    def performance_profiler(self):
        """Create performance profiler instance"""
        return PerformanceProfiler()
    
    @pytest.fixture
    async def dgm_engine(self):
        """Create Darwin-Gödel engine instance"""
        engine = DarwinGodelEngine(
            autogen_agent_dir="/tmp/test_autogen",
            sandbox_dir="/tmp/test_sandbox"
        )
        await engine.initialize()
        return engine
    
    @pytest.mark.asyncio
    async def test_llm_code_generation(self, llm_generator):
        """Test that LLM can generate improved code"""
        # Sample inefficient code
        original_code = '''
def find_max(numbers):
    """Find the maximum number in a list"""
    max_num = numbers[0]
    for i in range(len(numbers)):
        if numbers[i] > max_num:
            max_num = numbers[i]
    return max_num
'''
        
        # Test generation with API key check
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OpenAI API key not available")
        
        improved_code = await llm_generator.generate_code_improvement(
            code_context=original_code,
            opportunity="Optimize loop efficiency and use built-in functions",
            constraints=["Maintain exact functionality", "Use Python built-ins"]
        )
        
        # Verify we got code back
        assert improved_code is not None
        assert len(improved_code) > 0
        assert "def find_max" in improved_code
    
    @pytest.mark.asyncio
    async def test_performance_measurement(self, performance_profiler):
        """Test that performance profiler can measure improvements"""
        # Original inefficient code
        original_code = '''
def sum_squares(n):
    """Calculate sum of squares from 1 to n"""
    total = 0
    for i in range(1, n + 1):
        total += i * i
    return total
'''
        
        # Optimized version
        optimized_code = '''
def sum_squares(n):
    """Calculate sum of squares from 1 to n"""
    return n * (n + 1) * (2 * n + 1) // 6
'''
        
        # Create test case
        test_case = TestCase(
            name="test_sum_squares",
            setup_code="",
            test_code="result = sum_squares(1000)",
            expected_output=None,
            timeout=5.0
        )
        
        # Compare performance
        comparison = await performance_profiler.compare_performance(
            original_code=original_code,
            modified_code=optimized_code,
            test_cases=[test_case]
        )
        
        # Verify improvement
        assert comparison['is_improvement'] is True
        assert comparison['time_improvement'] > 0  # Should be faster
        assert comparison['maintains_correctness'] is True
    
    @pytest.mark.asyncio
    async def test_darwin_godel_integration(self, dgm_engine):
        """Test the full Darwin-Gödel flow with LLM"""
        # Mock file to analyze
        test_file_content = '''
def bubble_sort(arr):
    """Sort array using bubble sort"""
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
'''
        
        # Write test file
        test_file_path = "/tmp/test_sort.py"
        with open(test_file_path, 'w') as f:
            f.write(test_file_content)
        
        try:
            # Analyze the code
            analysis_results = await dgm_engine.analyze_code_performance(test_file_path)
            assert len(analysis_results) > 0
            
            # Check that opportunities were identified
            analysis = analysis_results[0]
            assert len(analysis.improvement_opportunities) > 0
            assert "algorithm" in str(analysis.improvement_opportunities).lower()
            
            # Generate improvements (this will use LLM if API key is available)
            improvements = await dgm_engine.generate_improvements(
                analysis_results, 
                historical_context={}
            )
            
            # Verify improvement was generated
            assert len(improvements) > 0
            improvement = improvements[0]
            assert improvement['generated_code'] != ""
            assert improvement['expected_improvement'] >= 0.0
            
        finally:
            # Cleanup
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
    
    @pytest.mark.asyncio
    async def test_llm_fallback_mechanism(self, llm_generator):
        """Test that system falls back gracefully when LLM is unavailable"""
        # Temporarily disable the client
        original_client = llm_generator.client
        llm_generator.client = None
        
        try:
            result = await llm_generator.generate_code_improvement(
                code_context="def test(): pass",
                opportunity="Optimize performance"
            )
            
            # Should return None when client is unavailable
            assert result is None
            
        finally:
            llm_generator.client = original_client
    
    @pytest.mark.asyncio 
    async def test_code_syntax_validation(self, llm_generator):
        """Test that generated code is validated for syntax"""
        # Test the validation method directly
        valid_code = "def test():\n    return 42"
        invalid_code = "def test(\n    return 42"
        
        assert llm_generator._validate_code_syntax(valid_code) is True
        assert llm_generator._validate_code_syntax(invalid_code) is False
    
    def test_prompt_building(self, llm_generator):
        """Test that prompts are built correctly"""
        prompt = llm_generator._build_improvement_prompt(
            code_context="def slow(): pass",
            opportunity="Make it faster",
            constraints=["Keep interface", "Add logging"],
            examples=[{"approach": "Use cache", "performance_gain": 0.5}]
        )
        
        # Verify prompt contains key elements
        assert "def slow(): pass" in prompt
        assert "Make it faster" in prompt
        assert "Keep interface" in prompt
        assert "Add logging" in prompt
        assert "Use cache" in prompt
        assert "50.0%" in prompt  # Performance gain
    
    @pytest.mark.asyncio
    async def test_performance_profiler_test_generation(self, performance_profiler):
        """Test automatic test case generation"""
        code = '''
def process_list(input_list):
    """Process a list of items"""
    return [x * 2 for x in input_list]

def calculate_sum(numbers):
    """Calculate sum of numbers"""
    return sum(numbers)
'''
        
        test_cases = performance_profiler.generate_test_cases_from_code(code)
        
        # Should generate test cases for both functions
        assert len(test_cases) >= 2
        assert any("process_list" in tc.test_code for tc in test_cases)
        assert any("calculate_sum" in tc.test_code for tc in test_cases)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])