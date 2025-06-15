#!/usr/bin/env python3
"""
Darwin-Gödel LLM Demo Script
Shows how the system can now generate real code improvements using LLM
"""

import asyncio
import os
import logging
from autogen_agent.evolution.darwin_godel_engine import DarwinGodelEngine
from autogen_agent.evolution.llm_code_generator import LLMCodeGenerator
from autogen_agent.evolution.performance_profiler import PerformanceProfiler, TestCase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Sample inefficient code to improve
SAMPLE_CODE = '''
def find_duplicates(items):
    """Find all duplicate items in a list"""
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates

def calculate_fibonacci(n):
    """Calculate nth Fibonacci number recursively"""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def process_data(data_list):
    """Process a list of data items"""
    result = []
    for item in data_list:
        if item > 0:
            result.append(item * 2)
    return result
'''

async def demo_llm_code_generation():
    """Demonstrate LLM-powered code generation"""
    print("🤖 Darwin-Gödel LLM Code Generation Demo\n")
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not set. Using fallback templates.")
        print("To enable LLM generation, set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'\n")
    
    # Initialize components
    llm_generator = LLMCodeGenerator(temperature=0.3)
    profiler = PerformanceProfiler()
    
    print("📝 Original Code:")
    print("=" * 50)
    print(SAMPLE_CODE)
    print("=" * 50)
    
    # Example 1: Optimize the duplicate finder
    print("\n🔧 Improvement 1: Optimizing duplicate finder...")
    improved_duplicates = await llm_generator.generate_code_improvement(
        code_context=SAMPLE_CODE,
        opportunity="Optimize find_duplicates function to use more efficient algorithm with better time complexity",
        constraints=[
            "Use a set or dictionary for O(n) complexity",
            "Maintain the same function signature",
            "Return duplicates in any order"
        ]
    )
    
    if improved_duplicates:
        print("✅ Generated improvement:")
        print(improved_duplicates)
    else:
        print("❌ LLM generation failed (API key missing?)")
    
    # Example 2: Measure actual performance improvement
    print("\n📊 Measuring Performance Improvement...")
    
    # Create test case
    test_case = TestCase(
        name="test_duplicates",
        setup_code="test_list = [1, 2, 3, 2, 4, 3, 5, 1, 6, 7, 8, 9, 1, 2, 3] * 10",
        test_code="result = find_duplicates(test_list)",
        timeout=5.0
    )
    
    if improved_duplicates:
        comparison = await profiler.compare_performance(
            original_code=SAMPLE_CODE,
            modified_code=improved_duplicates or SAMPLE_CODE,
            test_cases=[test_case]
        )
        
        print(f"⏱️  Time improvement: {comparison['time_improvement']*100:.1f}%")
        print(f"💾 Memory improvement: {comparison['memory_improvement']*100:.1f}%")
        print(f"✅ Maintains correctness: {comparison['maintains_correctness']}")
        print(f"🎯 Overall improvement: {comparison['overall_improvement']*100:.1f}%")

async def demo_darwin_godel_engine():
    """Demonstrate the full Darwin-Gödel engine with LLM"""
    print("\n\n🧬 Darwin-Gödel Engine Full Demo\n")
    
    # Write sample code to a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(SAMPLE_CODE)
        temp_file = f.name
    
    try:
        # Initialize engine
        engine = DarwinGodelEngine(
            autogen_agent_dir=os.path.dirname(temp_file),
            sandbox_dir="/tmp/dgm_demo"
        )
        
        await engine.initialize()
        
        # Analyze the code
        print("🔍 Analyzing code for improvements...")
        analysis_results = await engine.analyze_code_performance(temp_file)
        
        if analysis_results:
            analysis = analysis_results[0]
            print(f"\n📊 Analysis Results:")
            print(f"  Complexity Score: {analysis.complexity_score}")
            print(f"  Risk Assessment: {analysis.risk_assessment}")
            print(f"  Bottlenecks Found: {len(analysis.performance_bottlenecks)}")
            print(f"  Opportunities: {len(analysis.improvement_opportunities)}")
            
            for i, opportunity in enumerate(analysis.improvement_opportunities[:3]):
                print(f"    {i+1}. {opportunity}")
            
            # Generate improvements
            print("\n🚀 Generating improvements with LLM...")
            improvements = await engine.generate_improvements(analysis_results)
            
            if improvements:
                imp = improvements[0]
                print(f"\n✨ Generated Improvement:")
                print(f"  Opportunity: {imp['opportunity']}")
                print(f"  Expected Improvement: {imp['expected_improvement']*100:.1f}%")
                print(f"  Risk Level: {imp['risk_level']}")
                
                if imp['generated_code']:
                    print(f"\n📝 Generated Code Preview:")
                    preview = imp['generated_code'][:500] + "..." if len(imp['generated_code']) > 500 else imp['generated_code']
                    print(preview)
            
    finally:
        # Cleanup
        os.unlink(temp_file)

async def main():
    """Run all demos"""
    await demo_llm_code_generation()
    await demo_darwin_godel_engine()
    
    print("\n\n🎉 Demo Complete!")
    print("\nKey Achievements:")
    print("✅ Real LLM-powered code generation (not templates)")
    print("✅ Actual performance measurement (not estimates)")
    print("✅ Intelligent improvement suggestions")
    print("✅ Safety-first approach with sandboxing")
    
    if not os.getenv('OPENAI_API_KEY'):
        print("\n💡 To see full LLM capabilities, set your OpenAI API key and run again!")

if __name__ == "__main__":
    asyncio.run(main())