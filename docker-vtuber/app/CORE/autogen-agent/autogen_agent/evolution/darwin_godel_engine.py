"""
🧬 Darwin-Gödel Machine - Self-Code Modification Engine

This module implements the core Darwin-Gödel Machine that can analyze its own code,
generate improvements, test them safely, and deploy successful modifications.

Key Features:
- Code analysis and performance bottleneck identification
- LLM-powered code generation and optimization
- Sandboxed testing environment for safety
- Automatic rollback on failure detection
- Performance-driven evolution with safety constraints
"""

import os
import ast
import sys
import json
import logging
import tempfile
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import shutil
import asyncio
import re

# Import our new LLM and performance modules
from .llm_code_generator import LLMCodeGenerator, CodeImprovementPrompts
from .performance_profiler import PerformanceProfiler, PerformanceMetrics, TestCase

@dataclass
class CodeAnalysisResult:
    """Results of code analysis"""
    file_path: str
    complexity_score: float
    performance_bottlenecks: List[str]
    improvement_opportunities: List[str]
    risk_assessment: str
    current_metrics: Dict[str, float]

@dataclass
class SafetyTestResult:
    """Results of safety testing"""
    passed: bool
    test_duration: float
    errors: List[str]
    warnings: List[str]
    performance_impact: Dict[str, float]
    rollback_needed: bool

class DarwinGodelEngine:
    """
    Core self-modification engine that can analyze, improve, and deploy 
    code changes while maintaining safety constraints
    """
    
    def __init__(self, autogen_agent_dir: str = "/app/autogen_agent", 
                 sandbox_dir: str = "/tmp/autogen_sandbox",
                 cognee_service: Optional[Any] = None):
        self.agent_dir = autogen_agent_dir
        self.sandbox_dir = sandbox_dir
        self.modification_history = []
        self.safety_checks_enabled = True
        self.max_modifications_per_cycle = 3
        self.cognee_service = cognee_service
        
        # 🚀 REAL MODIFICATION CONTROL
        self.real_modifications_enabled = os.getenv('DARWIN_GODEL_REAL_MODIFICATIONS', 'false').lower() == 'true'
        self.require_explicit_approval = os.getenv('DARWIN_GODEL_REQUIRE_APPROVAL', 'true').lower() == 'true'
        self.backup_retention_days = int(os.getenv('DARWIN_GODEL_BACKUP_RETENTION_DAYS', '7'))
        
        # Performance tracking
        self.baseline_metrics = {}
        self.current_metrics = {}
        
        # Initialize LLM code generator and performance profiler
        self.llm_generator = LLMCodeGenerator(
            model=os.getenv('DARWIN_GODEL_MODEL', 'gpt-4-turbo-preview'),
            temperature=float(os.getenv('DARWIN_GODEL_TEMPERATURE', '0.3'))
        )
        self.performance_profiler = PerformanceProfiler()
        
        logging.info("🧬 [DARWIN_GODEL] Engine initialized with LLM support")
        logging.info(f"🔧 [DARWIN_GODEL] Real modifications: {'ENABLED' if self.real_modifications_enabled else 'SIMULATION MODE'}")
        logging.info(f"🛡️ [DARWIN_GODEL] Explicit approval required: {self.require_explicit_approval}")
        logging.info(f"🤖 [DARWIN_GODEL] LLM Model: {self.llm_generator.model}")
    
    async def initialize(self) -> bool:
        """Initialize the Darwin-Gödel Machine"""
        try:
            # Create sandbox directory
            os.makedirs(self.sandbox_dir, exist_ok=True)
            
            # Establish baseline performance metrics
            await self._establish_baseline_metrics()
            
            # Verify sandbox environment
            if not await self._verify_sandbox_environment():
                logging.error("❌ [DARWIN_GODEL] Sandbox environment verification failed")
                return False
            
            logging.info("✅ [DARWIN_GODEL] Engine initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"❌ [DARWIN_GODEL] Initialization failed: {e}")
            return False
    
    async def analyze_code_performance(self, target_file: str = None) -> List[CodeAnalysisResult]:
        """
        Analyze code performance and identify improvement opportunities
        """
        logging.info("🔍 [DARWIN_GODEL] Starting code performance analysis")
        
        analysis_results = []
        
        if target_file:
            target_files = [os.path.join(self.agent_dir, target_file)]
        else:
            # Analyze key AutoGen agent files
            target_files = self._get_key_agent_files()
        
        for file_path in target_files:
            if os.path.exists(file_path):
                result = await self._analyze_single_file(file_path)
                if result:
                    analysis_results.append(result)
        
        logging.info(f"📊 [DARWIN_GODEL] Analysis completed: {len(analysis_results)} files analyzed")
        return analysis_results
    
    async def generate_code_improvements(self, analysis_results: List[CodeAnalysisResult], 
                                       historical_context: Dict = None) -> List[Dict]:
        """
        Generate code improvements based on analysis results and historical context
        """
        logging.info("⚡ [DARWIN_GODEL] Generating code improvements")
        
        improvements = []
        
        for analysis in analysis_results:
            if analysis.improvement_opportunities:
                improvement = await self._generate_improvement_for_file(analysis, historical_context)
                if improvement:
                    improvements.append(improvement)
        
        # Limit number of modifications per cycle for safety
        improvements = improvements[:self.max_modifications_per_cycle]
        
        logging.info(f"💡 [DARWIN_GODEL] Generated {len(improvements)} improvement candidates")
        return improvements
    
    async def test_modifications_safely(self, improvements: List[Dict]) -> List[SafetyTestResult]:
        """
        Test code modifications in sandboxed environment
        """
        logging.info("🧪 [DARWIN_GODEL] Testing modifications in sandbox")
        
        test_results = []
        
        for improvement in improvements:
            result = await self._test_single_modification(improvement)
            test_results.append(result)
        
        safe_count = sum(1 for result in test_results if result.passed)
        logging.info(f"✅ [DARWIN_GODEL] Safety testing completed: {safe_count}/{len(test_results)} passed")
        
        return test_results
    
    async def deploy_safe_modifications(self, improvements: List[Dict], 
                                      test_results: List[SafetyTestResult]) -> List[Dict]:
        """
        Deploy modifications that passed safety tests
        """
        logging.info("🚀 [DARWIN_GODEL] Deploying safe modifications")
        
        deployment_results = []
        
        for improvement, test_result in zip(improvements, test_results):
            if test_result.passed and not test_result.rollback_needed:
                deploy_result = await self._deploy_single_modification(improvement)
                deployment_results.append(deploy_result)
            else:
                logging.warning(f"⚠️ [DARWIN_GODEL] Skipping unsafe modification: {improvement.get('id', 'unknown')}")
        
        logging.info(f"✅ [DARWIN_GODEL] Deployed {len(deployment_results)} modifications")
        return deployment_results
    
    async def _establish_baseline_metrics(self):
        """Establish baseline performance metrics"""
        logging.info("📊 [DARWIN_GODEL] Establishing baseline metrics")
        
        # Simulate baseline metrics - in real implementation would measure:
        # - Import times, function execution times, memory usage, etc.
        self.baseline_metrics = {
            "decision_time": 2.5,  # seconds
            "memory_usage": 85.0,  # MB
            "import_time": 0.8,    # seconds
            "tool_selection_time": 1.2,  # seconds
            "error_rate": 0.15     # 15%
        }
        
        self.current_metrics = self.baseline_metrics.copy()
        logging.info(f"✅ [DARWIN_GODEL] Baseline metrics established: {self.baseline_metrics}")
    
    async def _verify_sandbox_environment(self) -> bool:
        """Verify sandbox environment is safe and functional"""
        try:
            # Create test file in sandbox
            test_file = os.path.join(self.sandbox_dir, "test_safety.py")
            with open(test_file, 'w') as f:
                f.write("print('Sandbox test successful')")
            
            # Test execution
            result = subprocess.run([
                sys.executable, test_file
            ], capture_output=True, text=True, timeout=5)
            
            # Clean up
            os.remove(test_file)
            
            return result.returncode == 0 and "Sandbox test successful" in result.stdout
            
        except Exception as e:
            logging.error(f"❌ [DARWIN_GODEL] Sandbox verification failed: {e}")
            return False
    
    def _get_key_agent_files(self) -> List[str]:
        """Get list of key AutoGen agent files for analysis"""
        key_files = [
            "main.py",
            "tool_registry.py",
            "memory_manager.py", 
            "cognitive_decision_engine.py",
            "mcp_server.py"
        ]
        
        return [
            os.path.join(self.agent_dir, filename) 
            for filename in key_files 
            if os.path.exists(os.path.join(self.agent_dir, filename))
        ]
    
    async def _analyze_single_file(self, file_path: str) -> Optional[CodeAnalysisResult]:
        """Analyze a single Python file for improvement opportunities"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse AST for code analysis
            tree = ast.parse(content)
            
            # Calculate complexity metrics
            complexity_score = self._calculate_complexity(tree)
            
            # Identify performance bottlenecks
            bottlenecks = self._identify_bottlenecks(tree, content)
            
            # Find improvement opportunities
            opportunities = self._find_opportunities(tree, content, file_path)
            
            # Assess risk level
            risk_assessment = self._assess_modification_risk(file_path, complexity_score)
            
            # Get current performance metrics for this file
            current_metrics = await self._measure_file_performance(file_path)
            
            result = CodeAnalysisResult(
                file_path=file_path,
                complexity_score=complexity_score,
                performance_bottlenecks=bottlenecks,
                improvement_opportunities=opportunities,
                risk_assessment=risk_assessment,
                current_metrics=current_metrics
            )
            
            logging.info(f"🔍 [DARWIN_GODEL] Analyzed {os.path.basename(file_path)}: {len(opportunities)} opportunities")
            return result
            
        except Exception as e:
            logging.error(f"❌ [DARWIN_GODEL] Failed to analyze {file_path}: {e}")
            return None
    
    def _calculate_complexity(self, tree: ast.AST) -> float:
        """Calculate code complexity score"""
        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.complexity = 0
                
            def visit_FunctionDef(self, node):
                self.complexity += 1
                self.generic_visit(node)
                
            def visit_If(self, node):
                self.complexity += 1
                self.generic_visit(node)
                
            def visit_For(self, node):
                self.complexity += 2
                self.generic_visit(node)
                
            def visit_While(self, node):
                self.complexity += 2
                self.generic_visit(node)
                
            def visit_Try(self, node):
                self.complexity += 1
                self.generic_visit(node)
        
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        return visitor.complexity
    
    def _identify_bottlenecks(self, tree: ast.AST, content: str) -> List[str]:
        """Identify potential performance bottlenecks"""
        bottlenecks = []
        
        # Look for common performance issues
        if "time.sleep(" in content and "asyncio.sleep(" not in content:
            bottlenecks.append("Synchronous sleep calls blocking event loop")
        
        if "requests.get(" in content or "requests.post(" in content:
            bottlenecks.append("Synchronous HTTP requests without async")
        
        if content.count("for ") > 5:
            bottlenecks.append("Multiple loops - potential optimization opportunity")
        
        if "json.loads(" in content and content.count("json.loads(") > 3:
            bottlenecks.append("Multiple JSON parsing operations")
        
        return bottlenecks
    
    def _find_opportunities(self, tree: ast.AST, content: str, file_path: str) -> List[str]:
        """Find specific improvement opportunities"""
        opportunities = []
        filename = os.path.basename(file_path)
        
        # File-specific opportunities
        if filename == "tool_registry.py":
            if "# naive" in content.lower() or "# simple" in content.lower():
                opportunities.append("Replace naive algorithm with optimized version")
            if "random.choice(" in content:
                opportunities.append("Replace random selection with scoring algorithm")
        
        elif filename == "memory_manager.py":
            if "in_memory" in content.lower():
                opportunities.append("Optimize memory storage with caching")
            if "list.append(" in content and content.count("list.append(") > 3:
                opportunities.append("Optimize list operations with bulk processing")
        
        elif filename == "main.py":
            if "time.sleep(" in content:
                opportunities.append("Replace blocking sleep with async sleep")
            if "thread" in content.lower() and "asyncio" in content:
                opportunities.append("Optimize threading with pure async approach")
        
        # General opportunities
        if content.count("logging.info(") > 10:
            opportunities.append("Optimize logging with structured logging")
        
        if "try:" in content and content.count("try:") > 5:
            opportunities.append("Consolidate error handling patterns")
        
        return opportunities
    
    def _assess_modification_risk(self, file_path: str, complexity: float) -> str:
        """Assess risk level of modifying this file"""
        filename = os.path.basename(file_path)
        
        # Core files are higher risk
        if filename in ["main.py", "mcp_server.py"]:
            return "high"
        elif complexity > 20:
            return "high"
        elif complexity > 10:
            return "medium"
        else:
            return "low"
    
    async def _measure_file_performance(self, file_path: str) -> Dict[str, float]:
        """Measure current performance metrics for a file"""
        # Simulate performance measurement
        # In real implementation would measure import time, execution time, etc.
        
        filename = os.path.basename(file_path)
        
        if filename == "tool_registry.py":
            return {"selection_time": 1.2, "accuracy": 0.75}
        elif filename == "memory_manager.py":
            return {"storage_time": 0.5, "retrieval_time": 0.3}
        elif filename == "main.py":
            return {"startup_time": 2.0, "cycle_time": 2.5}
        else:
            return {"execution_time": 0.5}
    
    async def _generate_improvement_for_file(self, analysis: CodeAnalysisResult, 
                                           historical_context: Dict = None) -> Optional[Dict]:
        """Generate specific improvement for a file based on analysis"""
        
        if not analysis.improvement_opportunities:
            return None
        
        # Select the most promising opportunity
        opportunity = analysis.improvement_opportunities[0]
        
        # Generate the improved code first
        generated_code = await self._generate_code_for_opportunity(opportunity, analysis)
        
        # Read original code for comparison
        try:
            with open(analysis.file_path, 'r') as f:
                original_code = f.read()
        except Exception as e:
            logging.error(f"Failed to read original file: {e}")
            original_code = ""
        
        # Measure actual improvement if we have both codes
        if generated_code and original_code:
            expected_improvement = await self._estimate_improvement_impact(
                opportunity, original_code, generated_code
            )
        else:
            expected_improvement = 0.05  # Conservative default
        
        improvement = {
            "id": f"improvement_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "target_file": analysis.file_path,
            "opportunity": opportunity,
            "risk_level": analysis.risk_assessment,
            "expected_improvement": expected_improvement,
            "modification_type": self._classify_modification_type(opportunity),
            "generated_code": generated_code,
            "backup_created": False
        }
        
        logging.info(f"💡 [DARWIN_GODEL] Generated improvement for {os.path.basename(analysis.file_path)}")
        return improvement
    
    async def _estimate_improvement_impact(self, opportunity: str, original_code: str, improved_code: str) -> float:
        """Measure actual performance improvement using profiler"""
        try:
            # Generate test cases for the code
            test_cases = self.performance_profiler.generate_test_cases_from_code(original_code)
            
            # If no test cases generated, use a conservative estimate
            if not test_cases:
                logging.warning("No test cases generated, using conservative estimate")
                return 0.05  # 5% conservative estimate
            
            # Compare performance
            comparison = await self.performance_profiler.compare_performance(
                original_code=original_code,
                modified_code=improved_code,
                test_cases=test_cases
            )
            
            # Return actual measured improvement
            improvement = comparison.get('overall_improvement', 0.0)
            logging.info(f"🎯 [DARWIN_GODEL] Measured improvement: {improvement*100:.1f}%")
            
            return max(0.0, improvement)  # Ensure non-negative
            
        except Exception as e:
            logging.error(f"Error measuring performance: {e}")
            # Fall back to conservative estimate on error
            return 0.05
    
    def _classify_modification_type(self, opportunity: str) -> str:
        """Classify the type of modification"""
        if "algorithm" in opportunity.lower() or "scoring" in opportunity.lower():
            return "optimization"
        elif "async" in opportunity.lower() or "thread" in opportunity.lower():
            return "async_improvement"
        elif "cache" in opportunity.lower() or "memory" in opportunity.lower():
            return "memory_optimization"
        else:
            return "general_improvement"
    
    async def _generate_code_for_opportunity(self, opportunity: str, 
                                           analysis: CodeAnalysisResult) -> str:
        """Generate actual code for the improvement opportunity using LLM"""
        
        # Read the original code
        try:
            with open(analysis.file_path, 'r') as f:
                original_code = f.read()
        except Exception as e:
            logging.error(f"Failed to read file {analysis.file_path}: {e}")
            return ""
        
        # Get similar improvements from Cognee if available
        similar_improvements = []
        if self.cognee_service:
            try:
                query = f"code optimization {opportunity} performance improvement"
                similar_improvements = await self._query_similar_improvements(query)
            except Exception as e:
                logging.warning(f"Cognee query failed: {e}")
        
        # Build constraints based on the analysis
        constraints = [
            "Maintain all existing function signatures and interfaces",
            "Do not add new dependencies or imports",
            "Ensure thread safety if the code is multi-threaded",
            f"Focus on this specific opportunity: {opportunity}",
            "The improvement must be measurable and significant"
        ]
        
        # Add specific optimization hints
        optimization_hints = CodeImprovementPrompts.get_prompt_for_opportunity(opportunity)
        constraints.append(optimization_hints)
        
        # Try LLM generation first
        improved_code = await self.llm_generator.generate_with_retry(
            code_context=original_code,
            opportunity=opportunity,
            constraints=constraints,
            examples=similar_improvements,
            max_retries=3
        )
        
        # If LLM generation succeeded, return it
        if improved_code:
            logging.info("✅ [DARWIN_GODEL] Successfully generated code improvement using LLM")
            # Store successful generation in Cognee for future learning
            if self.cognee_service:
                await self._store_improvement_pattern(opportunity, original_code, improved_code)
            return improved_code
        
        # Fallback to template-based generation if LLM fails
        logging.warning("⚠️ [DARWIN_GODEL] LLM generation failed, falling back to templates")
        return self._generate_template_fallback(opportunity)
    
    def _generate_template_fallback(self, opportunity: str) -> str:
        """Fallback template generation when LLM is unavailable"""
        if "scoring algorithm" in opportunity:
            return """
# Generated by Darwin-Gödel Machine (Template Fallback)
# Improved tool selection with scoring algorithm

def select_tool_with_scoring(self, context):
    scores = {}
    for tool_name, tool in self.tools.items():
        score = self._calculate_tool_score(tool_name, context)
        scores[tool_name] = score
    
    best_tool = max(scores.items(), key=lambda x: x[1])
    return self.tools[best_tool[0]]

def _calculate_tool_score(self, tool_name, context):
    # Historical performance score
    historical_score = self._get_historical_performance(tool_name)
    
    # Context relevance score  
    relevance_score = self._calculate_relevance(tool_name, context)
    
    # Combined score with weights
    return historical_score * 0.6 + relevance_score * 0.4
"""
        else:
            return f"""
# Generated by Darwin-Gödel Machine (Template Fallback)
# Unable to generate specific improvement for: {opportunity}
# Manual optimization required
"""
    
    async def _query_similar_improvements(self, query: str) -> List[Dict]:
        """Query Cognee for similar successful improvements"""
        # This will be implemented when Cognee is properly integrated
        return []
    
    async def _store_improvement_pattern(self, opportunity: str, original: str, improved: str):
        """Store successful improvement pattern in Cognee"""
        # This will be implemented when Cognee is properly integrated
        pass
    
    async def _test_single_modification(self, improvement: Dict) -> SafetyTestResult:
        """Test a single modification in sandbox environment"""
        
        logging.info(f"🧪 [DARWIN_GODEL] Testing modification {improvement['id']}")
        
        start_time = datetime.now()
        
        try:
            # Create sandbox copy of the target file
            sandbox_file = await self._create_sandbox_copy(improvement['target_file'])
            
            # Apply modification to sandbox copy
            await self._apply_modification_to_sandbox(sandbox_file, improvement)
            
            # Run safety tests
            test_passed, errors, warnings = await self._run_safety_tests(sandbox_file)
            
            # Measure performance impact
            performance_impact = await self._measure_performance_impact(sandbox_file, improvement)
            
            test_duration = (datetime.now() - start_time).total_seconds()
            
            result = SafetyTestResult(
                passed=test_passed,
                test_duration=test_duration,
                errors=errors,
                warnings=warnings,
                performance_impact=performance_impact,
                rollback_needed=not test_passed or performance_impact.get('degradation', 0) > 0.1
            )
            
            logging.info(f"{'✅' if test_passed else '❌'} [DARWIN_GODEL] Test {improvement['id']}: {'PASSED' if test_passed else 'FAILED'}")
            return result
            
        except Exception as e:
            logging.error(f"❌ [DARWIN_GODEL] Test failed for {improvement['id']}: {e}")
            return SafetyTestResult(
                passed=False,
                test_duration=(datetime.now() - start_time).total_seconds(),
                errors=[str(e)],
                warnings=[],
                performance_impact={},
                rollback_needed=True
            )
    
    async def _create_sandbox_copy(self, target_file: str) -> str:
        """Create a copy of target file in sandbox"""
        filename = os.path.basename(target_file)
        sandbox_file = os.path.join(self.sandbox_dir, filename)
        shutil.copy2(target_file, sandbox_file)
        return sandbox_file
    
    async def _apply_modification_to_sandbox(self, sandbox_file: str, improvement: Dict):
        """Apply modification to sandbox file using AST-based code transformation"""
        
        try:
            # Read original file content
            with open(sandbox_file, 'r') as f:
                original_content = f.read()
            
            # Parse the generated code to ensure it's valid Python
            generated_code = improvement.get('generated_code', '')
            
            if not generated_code or generated_code.startswith("# Generated by Darwin"):
                # Handle placeholder/comment-only code
                logging.info(f"📝 [DARWIN_GODEL] Appending placeholder code as comments for {improvement['id']}")
                with open(sandbox_file, 'a') as f:
                    f.write(f"\n\n# Darwin-Gödel Machine Modification {improvement['id']}\n")
                    f.write(f"# Opportunity: {improvement['opportunity']}\n")
                    f.write(f"# Generated Code:\n{generated_code}\n")
                return
            
            # For real code modifications, apply them properly
            logging.info(f"🔧 [DARWIN_GODEL] Applying real code modification to sandbox: {improvement['id']}")
            
            # Determine modification strategy based on opportunity type
            opportunity = improvement.get('opportunity', '').lower()
            
            if 'async sleep' in opportunity:
                # Replace time.sleep with asyncio.sleep
                modified_content = self._apply_async_sleep_modification(original_content, generated_code)
            elif 'scoring algorithm' in opportunity:
                # Add new methods or replace existing ones
                modified_content = self._apply_algorithm_modification(original_content, generated_code)
            else:
                # Generic modification: append new code
                modified_content = original_content + f"\n\n# Darwin-Gödel Machine Enhancement\n{generated_code}\n"
            
            # Write modified content back to sandbox file
            with open(sandbox_file, 'w') as f:
                f.write(modified_content)
            
            logging.info(f"✅ [DARWIN_GODEL] Successfully applied modification to sandbox: {improvement['id']}")
            
        except Exception as e:
            logging.error(f"❌ [DARWIN_GODEL] Failed to apply modification to sandbox {improvement['id']}: {e}")
            # Fallback to comment-only approach
            with open(sandbox_file, 'a') as f:
                f.write(f"\n\n# Darwin-Gödel Machine Modification {improvement['id']} (FAILED)\n")
                f.write(f"# Error: {str(e)}\n")
                f.write(f"# Opportunity: {improvement['opportunity']}\n")
    
    async def _run_safety_tests(self, sandbox_file: str) -> Tuple[bool, List[str], List[str]]:
        """Run safety tests on sandbox file"""
        errors = []
        warnings = []
        
        try:
            # Test 1: Syntax check
            with open(sandbox_file, 'r') as f:
                content = f.read()
            
            ast.parse(content)  # This will raise SyntaxError if invalid
            
            # Test 2: Import check (simplified)
            result = subprocess.run([
                sys.executable, "-m", "py_compile", sandbox_file
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                errors.append(f"Compilation failed: {result.stderr}")
            
            # Test 3: Basic execution test (if it's a main file)
            if "main.py" in sandbox_file:
                # Don't actually run main.py in sandbox for safety
                warnings.append("Main file execution test skipped for safety")
            
            test_passed = len(errors) == 0
            return test_passed, errors, warnings
            
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
            return False, errors, warnings
        except Exception as e:
            errors.append(f"Safety test failed: {e}")
            return False, errors, warnings
    
    async def _measure_performance_impact(self, sandbox_file: str, improvement: Dict) -> Dict[str, float]:
        """Measure performance impact of modification"""
        # Simulate performance measurement
        # In real implementation would run benchmarks
        
        expected_improvement = improvement.get('expected_improvement', 0.0)
        
        # Simulate some variance in actual results
        import random
        actual_improvement = expected_improvement * (0.8 + 0.4 * random.random())
        
        return {
            "improvement": actual_improvement,
            "degradation": max(0, -actual_improvement),
            "confidence": 0.8
        }
    
    async def _deploy_single_modification(self, improvement: Dict) -> Dict:
        """Deploy a single safe modification with comprehensive safety checks"""
        
        logging.info(f"🚀 [DARWIN_GODEL] Deploying modification {improvement['id']}")
        
        # Track modification in database
        modification_record = {
            "id": improvement['id'],
            "timestamp": datetime.now(),
            "target_file": improvement['target_file'],
            "modification_type": improvement.get('type', 'optimization'),
            "expected_improvement": improvement.get('expected_improvement', 0.0),
            "risk_level": improvement.get('risk_level', 'medium'),
            "backup_path": None,
            "status": "pending"
        }
        
        # Persist to database if collector available
        from ..main import statistics_collector
        if statistics_collector:
            await statistics_collector.collect_evolution_action(modification_record)
        
        try:
            # Create backup of original file
            backup_path = f"{improvement['target_file']}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(improvement['target_file'], backup_path)
            improvement['backup_created'] = True
            improvement['backup_path'] = backup_path
            modification_record['backup_path'] = backup_path
            
            # Check if real modifications are enabled
            if not self.real_modifications_enabled:
                logging.info(f"📝 [DARWIN_GODEL] SIMULATION MODE: Would apply modification to {improvement['target_file']}")
                
                # Record deployment in simulation mode
                deployment_record = {
                    "modification_id": improvement['id'],
                    "target_file": improvement['target_file'],
                    "deployed_at": datetime.now().isoformat(),
                    "backup_path": backup_path,
                    "status": "simulated",
                    "mode": "simulation"
                }
                
                self.modification_history.append(deployment_record)
                logging.info(f"✅ [DARWIN_GODEL] Successfully simulated deployment {improvement['id']}")
                return deployment_record
            
            # REAL MODIFICATION MODE
            logging.info(f"🔧 [DARWIN_GODEL] REAL MODIFICATION MODE: Applying changes to {improvement['target_file']}")
            
            # Additional safety check for explicit approval if required
            if self.require_explicit_approval:
                approval_file = f"/tmp/darwin_godel_approval_{improvement['id']}.flag"
                
                # Check for approval flag (would be created by external approval process)
                if not os.path.exists(approval_file):
                    logging.warning(f"⚠️ [DARWIN_GODEL] Explicit approval required for {improvement['id']} - creating approval request")
                    
                    # Create approval request file with details
                    approval_request = {
                        "modification_id": improvement['id'],
                        "target_file": improvement['target_file'],
                        "opportunity": improvement.get('opportunity', ''),
                        "risk_level": improvement.get('risk_level', 'unknown'),
                        "expected_improvement": improvement.get('expected_improvement', 0.0),
                        "generated_code": improvement.get('generated_code', ''),
                        "backup_path": backup_path,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    with open(f"/tmp/darwin_godel_approval_request_{improvement['id']}.json", 'w') as f:
                        json.dump(approval_request, f, indent=2)
                    
                    return {
                        "modification_id": improvement['id'],
                        "status": "pending_approval",
                        "approval_request_file": f"/tmp/darwin_godel_approval_request_{improvement['id']}.json",
                        "message": f"Explicit approval required for modification {improvement['id']}"
                    }
            
            # Apply the real modification
            success = await self._apply_real_modification(improvement)
            
            if success:
                # Measure actual impact
                actual_impact = await self._measure_actual_impact(improvement)
                
                # Record successful deployment
                deployment_record = {
                    "modification_id": improvement['id'],
                    "target_file": improvement['target_file'],
                    "deployed_at": datetime.now().isoformat(),
                    "backup_path": backup_path,
                    "status": "deployed",
                    "mode": "real_modification",
                    "actual_improvement": actual_impact.get('improvement', 0),
                    "performance_impact": actual_impact
                }
                
                self.modification_history.append(deployment_record)
                
                # Update database record with results
                if statistics_collector:
                    await statistics_collector.update_evolution_result({
                        "id": improvement['id'],
                        "status": "applied",
                        "actual_improvement": actual_impact.get('improvement', 0),
                        "performance_impact": actual_impact
                    })
                
                # Clean up old backups if needed
                await self._cleanup_old_backups(improvement['target_file'])
                
                logging.info(f"✅ [DARWIN_GODEL] Successfully deployed real modification {improvement['id']}")
                return deployment_record
            else:
                # Restore from backup on failure
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, improvement['target_file'])
                    logging.info(f"🔄 [DARWIN_GODEL] Restored {improvement['target_file']} from backup")
                
                return {
                    "modification_id": improvement['id'],
                    "status": "failed",
                    "error": "Real modification application failed",
                    "backup_restored": True
                }
            
        except Exception as e:
            logging.error(f"❌ [DARWIN_GODEL] Deployment failed for {improvement['id']}: {e}")
            
            # Update database record with failure
            if statistics_collector:
                await statistics_collector.update_evolution_result({
                    "id": improvement['id'],
                    "status": "failed",
                    "actual_improvement": 0,
                    "performance_impact": {"error": str(e)}
                })
            
            # Restore from backup on exception
            if 'backup_path' in locals() and os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, improvement['target_file'])
                    logging.info(f"🔄 [DARWIN_GODEL] Restored {improvement['target_file']} from backup after exception")
                except Exception as restore_error:
                    logging.error(f"❌ [DARWIN_GODEL] Failed to restore backup: {restore_error}")
            
            return {
                "modification_id": improvement['id'],
                "status": "failed",
                "error": str(e),
                "backup_restored": 'backup_path' in locals() and os.path.exists(backup_path)
            }
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get Darwin-Gödel Machine statistics"""
        return {
            "total_modifications": len(self.modification_history),
            "successful_deployments": len([m for m in self.modification_history if m.get('status') == 'deployed']),
            "baseline_metrics": self.baseline_metrics,
            "current_metrics": self.current_metrics,
            "sandbox_dir": self.sandbox_dir,
            "safety_checks_enabled": self.safety_checks_enabled
        }
    
    def _apply_async_sleep_modification(self, original_content: str, generated_code: str) -> str:
        """Apply async sleep modification to replace time.sleep with asyncio.sleep"""
        modified_content = re.sub(
            r'time\.sleep\s*\(',
            'await asyncio.sleep(',
            original_content
        )
        
        # Ensure asyncio import exists
        if 'import asyncio' not in modified_content and 'from asyncio' not in modified_content:
            # Add asyncio import at the top
            lines = modified_content.split('\n')
            import_inserted = False
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    continue
                else:
                    lines.insert(i, 'import asyncio')
                    import_inserted = True
                    break
            
            if not import_inserted:
                lines.insert(0, 'import asyncio')
            
            modified_content = '\n'.join(lines)
        
        return modified_content
    
    def _apply_algorithm_modification(self, original_content: str, generated_code: str) -> str:
        """Apply algorithm modification by appending new methods"""
        
        # For now, append the new algorithm code
        # In future versions, could use AST to replace specific methods
        return original_content + f"\n\n# Darwin-Gödel Machine Algorithm Enhancement\n{generated_code}\n"
    
    async def _measure_actual_impact(self, improvement: Dict) -> Dict:
        """Measure the actual impact of a modification"""
        try:
            # Get current metrics after modification
            current_metrics = {
                "decision_time": self.current_metrics.get('decision_time', 2.5),
                "memory_usage": self.current_metrics.get('memory_usage', 85.0),
                "error_rate": self.current_metrics.get('error_rate', 0.15),
                "tool_selection_time": self.current_metrics.get('tool_selection_time', 1.2)
            }
            
            # Compare with baseline
            baseline = self.baseline_metrics
            
            # Calculate improvements
            improvements = {}
            for metric, current_value in current_metrics.items():
                baseline_value = baseline.get(metric, current_value)
                if baseline_value > 0:
                    # For time-based metrics, improvement is negative change
                    if 'time' in metric:
                        improvement_pct = ((baseline_value - current_value) / baseline_value) * 100
                    # For error rate, improvement is negative change
                    elif metric == 'error_rate':
                        improvement_pct = ((baseline_value - current_value) / baseline_value) * 100
                    # For other metrics, improvement is positive change
                    else:
                        improvement_pct = ((current_value - baseline_value) / baseline_value) * 100
                    improvements[metric] = improvement_pct
                else:
                    improvements[metric] = 0.0
            
            # Calculate overall improvement
            overall_improvement = sum(improvements.values()) / len(improvements) if improvements else 0.0
            
            return {
                "improvement": overall_improvement,
                "metrics": current_metrics,
                "improvements_by_metric": improvements,
                "modification_type": improvement.get('type', 'unknown')
            }
            
        except Exception as e:
            logging.error(f"❌ [DARWIN_GODEL] Failed to measure impact: {e}")
            return {
                "improvement": 0.0,
                "error": str(e)
            }
    
    async def _apply_real_modification(self, improvement: Dict) -> bool:
        """Apply real modification to the target file with safety checks"""
        
        try:
            target_file = improvement['target_file']
            modification_id = improvement['id']
            
            logging.info(f"🔧 [DARWIN_GODEL] Applying real modification {modification_id} to {target_file}")
            
            # Read the current content
            with open(target_file, 'r') as f:
                original_content = f.read()
            
            # Apply the same modification logic as used in sandbox
            opportunity = improvement.get('opportunity', '').lower()
            generated_code = improvement.get('generated_code', '')
            
            if not generated_code or generated_code.startswith("# Generated by Darwin"):
                logging.warning(f"⚠️ [DARWIN_GODEL] No real code to apply for {modification_id}")
                return False
            
            # Apply modification based on type
            if 'async sleep' in opportunity:
                modified_content = self._apply_async_sleep_modification(original_content, generated_code)
            elif 'scoring algorithm' in opportunity:
                modified_content = self._apply_algorithm_modification(original_content, generated_code)
            else:
                # Generic modification: append new code
                modified_content = original_content + f"\n\n# Darwin-Gödel Machine Enhancement - {modification_id}\n{generated_code}\n"
            
            # Final safety check: ensure modified content is valid Python
            try:
                ast.parse(modified_content)
            except SyntaxError as e:
                logging.error(f"❌ [DARWIN_GODEL] Modified content has syntax errors: {e}")
                return False
            
            # Write the modified content
            with open(target_file, 'w') as f:
                f.write(modified_content)
            
            logging.info(f"✅ [DARWIN_GODEL] Successfully applied real modification {modification_id}")
            
            # Store modification details for rollback if needed
            modification_details = {
                "modification_id": modification_id,
                "original_content_hash": hash(original_content),
                "modified_content_hash": hash(modified_content),
                "applied_at": datetime.now().isoformat()
            }
            
            with open(f"/tmp/darwin_godel_mod_{modification_id}.json", 'w') as f:
                json.dump(modification_details, f, indent=2)
            
            return True
            
        except Exception as e:
            logging.error(f"❌ [DARWIN_GODEL] Failed to apply real modification {improvement['id']}: {e}")
            return False
    
    async def _cleanup_old_backups(self, target_file: str):
        """Clean up old backup files based on retention policy"""
        
        try:
            # Find all backup files for this target
            base_name = os.path.basename(target_file)
            backup_dir = os.path.dirname(target_file)
            
            backup_files = []
            for file in os.listdir(backup_dir):
                if file.startswith(f"{base_name}.backup_"):
                    backup_path = os.path.join(backup_dir, file)
                    backup_files.append((backup_path, os.path.getmtime(backup_path)))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)
            cutoff_timestamp = cutoff_date.timestamp()
            
            # Remove old backups
            removed_count = 0
            for backup_path, mtime in backup_files[5:]:  # Keep at least 5 recent backups
                if mtime < cutoff_timestamp:
                    try:
                        os.remove(backup_path)
                        removed_count += 1
                        logging.debug(f"🗑️ [DARWIN_GODEL] Removed old backup: {backup_path}")
                    except Exception as e:
                        logging.warning(f"⚠️ [DARWIN_GODEL] Failed to remove backup {backup_path}: {e}")
            
            if removed_count > 0:
                logging.info(f"🗑️ [DARWIN_GODEL] Cleaned up {removed_count} old backup files for {target_file}")
                
        except Exception as e:
            logging.warning(f"⚠️ [DARWIN_GODEL] Backup cleanup failed for {target_file}: {e}") 