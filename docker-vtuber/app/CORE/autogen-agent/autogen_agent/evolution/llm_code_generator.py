"""
LLM Code Generator for Darwin-Gödel Machine
Implements real code generation using LLMs instead of templates
"""

import os
import re
import ast
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import asyncio
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)


class LLMCodeGenerator:
    """Generates code improvements using LLM instead of hardcoded templates"""
    
    # System prompt for code optimization
    DARWIN_GODEL_SYSTEM_PROMPT = """You are a code optimization expert implementing the Darwin-Gödel Machine approach.
Your goal is to generate improved code that:
1. Maintains exact functionality - the behavior must remain identical
2. Improves performance (execution speed and/or memory usage)
3. Follows the existing code style and conventions
4. Is safe and doesn't introduce bugs or security issues
5. Uses only the libraries already imported in the original code

Important constraints:
- Return ONLY the improved code, no explanations or comments
- Do not add new imports unless they're already in the file
- Preserve all function signatures and public interfaces
- Maintain backward compatibility
- Focus on algorithmic improvements, not just syntactic changes"""

    def __init__(self, model: str = "gpt-4-turbo-preview", temperature: float = 0.3):
        """
        Initialize the LLM code generator
        
        Args:
            model: OpenAI model to use for code generation
            temperature: Temperature for generation (lower = more deterministic)
        """
        self.model = model
        self.temperature = temperature
        self.client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize OpenAI client with proper error handling"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found. LLM code generation will be disabled.")
            return
            
        try:
            self.client = AsyncOpenAI(api_key=api_key)
            logger.info(f"OpenAI client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
    
    async def generate_code_improvement(
        self,
        code_context: str,
        opportunity: str,
        constraints: Optional[List[str]] = None,
        examples: Optional[List[Dict]] = None
    ) -> Optional[str]:
        """
        Generate improved code using LLM
        
        Args:
            code_context: The original code to improve
            opportunity: Description of the improvement opportunity
            constraints: Additional constraints for the improvement
            examples: Similar successful improvements from memory
            
        Returns:
            Improved code or None if generation fails
        """
        if not self.client:
            logger.warning("OpenAI client not available. Falling back to template-based generation.")
            return None
            
        try:
            prompt = self._build_improvement_prompt(
                code_context, opportunity, constraints or [], examples or []
            )
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.DARWIN_GODEL_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=4000  # Ensure we have room for code
            )
            
            improved_code = self._extract_code_from_response(response)
            
            # Validate the generated code
            if self._validate_code_syntax(improved_code):
                logger.info(f"Successfully generated improvement for: {opportunity}")
                return improved_code
            else:
                logger.error("Generated code failed syntax validation")
                return None
                
        except Exception as e:
            logger.error(f"Error generating code improvement: {e}")
            return None
    
    def _build_improvement_prompt(
        self,
        code_context: str,
        opportunity: str,
        constraints: List[str],
        examples: List[Dict]
    ) -> str:
        """Build the prompt for code improvement"""
        prompt_parts = [
            f"Improve the following Python code to address this opportunity: {opportunity}",
            "",
            "Original Code:",
            "```python",
            code_context,
            "```",
            ""
        ]
        
        if constraints:
            prompt_parts.extend([
                "Additional Constraints:",
                *[f"- {constraint}" for constraint in constraints],
                ""
            ])
        
        if examples:
            prompt_parts.extend([
                "Similar Successful Improvements:",
                ""
            ])
            for i, example in enumerate(examples[:3]):  # Limit to 3 examples
                prompt_parts.extend([
                    f"Example {i+1}:",
                    f"- Approach: {example.get('approach', 'N/A')}",
                    f"- Performance Gain: {example.get('performance_gain', 0)*100:.1f}%",
                    ""
                ])
        
        prompt_parts.extend([
            "Generate the improved code that addresses the opportunity while maintaining exact functionality.",
            "Return ONLY the improved Python code, no explanations."
        ])
        
        return "\n".join(prompt_parts)
    
    def _extract_code_from_response(self, response) -> str:
        """Extract code from the LLM response"""
        content = response.choices[0].message.content.strip()
        
        # Try to extract code from markdown code blocks
        code_block_pattern = r'```python\s*(.*?)\s*```'
        matches = re.findall(code_block_pattern, content, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks, assume the entire response is code
        return content.strip()
    
    def _validate_code_syntax(self, code: str) -> bool:
        """Validate that the generated code has valid Python syntax"""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error in generated code: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating code: {e}")
            return False
    
    async def generate_with_retry(
        self,
        code_context: str,
        opportunity: str,
        constraints: Optional[List[str]] = None,
        examples: Optional[List[Dict]] = None,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Generate code with retry logic for robustness
        
        Args:
            code_context: The original code to improve
            opportunity: Description of the improvement opportunity
            constraints: Additional constraints
            examples: Similar successful improvements
            max_retries: Maximum number of retry attempts
            
        Returns:
            Improved code or None if all attempts fail
        """
        for attempt in range(max_retries):
            try:
                result = await self.generate_code_improvement(
                    code_context, opportunity, constraints, examples
                )
                
                if result:
                    return result
                
                # If generation failed, add more specific constraints
                if constraints is None:
                    constraints = []
                constraints.append(f"Attempt {attempt + 2}: Ensure valid Python syntax")
                
                # Increase temperature slightly for diversity
                self.temperature = min(0.7, self.temperature + 0.1)
                
            except Exception as e:
                logger.error(f"Retry attempt {attempt + 1} failed: {e}")
                
            # Wait before retry
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"All {max_retries} attempts failed for: {opportunity}")
        return None
    
    def estimate_token_usage(self, code_context: str, opportunity: str) -> Dict[str, int]:
        """
        Estimate token usage for the generation request
        
        Returns:
            Dictionary with estimated prompt and completion tokens
        """
        # Rough estimation: 1 token ≈ 4 characters
        prompt_length = len(self.DARWIN_GODEL_SYSTEM_PROMPT) + len(code_context) + len(opportunity) + 500
        estimated_prompt_tokens = prompt_length // 4
        
        # Assume completion will be similar size to input code
        estimated_completion_tokens = len(code_context) // 4
        
        return {
            "prompt_tokens": estimated_prompt_tokens,
            "completion_tokens": estimated_completion_tokens,
            "total_tokens": estimated_prompt_tokens + estimated_completion_tokens
        }


class CodeImprovementPrompts:
    """Collection of specialized prompts for different optimization types"""
    
    PERFORMANCE_OPTIMIZATION = """Focus on:
- Algorithm complexity reduction (O(n²) → O(n log n) or better)
- Eliminating redundant computations
- Using more efficient data structures
- Reducing memory allocations
- Leveraging built-in optimized functions"""
    
    ASYNC_OPTIMIZATION = """Focus on:
- Converting blocking operations to async
- Proper use of asyncio.gather() for parallel execution
- Eliminating unnecessary await statements
- Using async context managers where appropriate"""
    
    MEMORY_OPTIMIZATION = """Focus on:
- Reducing object creation in loops
- Using generators instead of lists where possible
- Proper cleanup of resources
- Efficient string operations
- Minimizing data copies"""
    
    READABILITY_OPTIMIZATION = """Focus on:
- Simplifying complex logic
- Better variable and function names
- Extracting repeated code into functions
- Reducing nesting levels
- Following PEP 8 guidelines"""
    
    @classmethod
    def get_prompt_for_opportunity(cls, opportunity: str) -> str:
        """Get the appropriate optimization prompt based on the opportunity type"""
        opportunity_lower = opportunity.lower()
        
        if any(keyword in opportunity_lower for keyword in ["performance", "speed", "slow", "optimize"]):
            return cls.PERFORMANCE_OPTIMIZATION
        elif any(keyword in opportunity_lower for keyword in ["async", "concurrent", "parallel"]):
            return cls.ASYNC_OPTIMIZATION
        elif any(keyword in opportunity_lower for keyword in ["memory", "ram", "allocation"]):
            return cls.MEMORY_OPTIMIZATION
        elif any(keyword in opportunity_lower for keyword in ["readability", "clean", "refactor"]):
            return cls.READABILITY_OPTIMIZATION
        else:
            return cls.PERFORMANCE_OPTIMIZATION  # Default to performance