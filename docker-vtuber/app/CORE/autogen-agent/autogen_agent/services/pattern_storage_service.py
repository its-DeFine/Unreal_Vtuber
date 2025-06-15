"""
Pattern Storage Service for Long-term Learning
Stores successful patterns and improvements in Cognee for semantic retrieval
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class PatternStorageService:
    """
    Store successful patterns and improvements in Cognee
    """
    
    def __init__(self, cognee_service):
        self.cognee_service = cognee_service
        
    async def store_successful_pattern(self, pattern_data: Dict):
        """Store successful decision/improvement patterns"""
        pattern_id = pattern_data.get('id', f"pattern_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
        pattern_type = pattern_data.get('type', 'decision')
        success_rate = pattern_data.get('success_rate', 0.0)
        context = pattern_data.get('context', {})
        actions = pattern_data.get('actions', [])
        outcomes = pattern_data.get('outcomes', {})
        performance_impact = pattern_data.get('performance_impact', {})
        
        # Create structured document for Cognee
        pattern_doc = f"""
Pattern ID: {pattern_id}
Type: {pattern_type}
Success Rate: {success_rate:.2%}
Timestamp: {datetime.utcnow().isoformat()}

CONTEXT:
{self._format_context(context)}

ACTIONS TAKEN:
{self._format_actions(actions)}

OUTCOMES:
{self._format_outcomes(outcomes)}

PERFORMANCE IMPACT:
{self._format_performance_impact(performance_impact)}

TAGS: {', '.join(self._generate_tags(pattern_data))}
"""
        
        try:
            # Store in Cognee
            await self.cognee_service.add_data([pattern_doc])
            logger.info(f"✅ [PATTERNS] Stored successful pattern {pattern_id} (type: {pattern_type})")
            
            # If this is an evolution pattern with high success, store additional metadata
            if pattern_type == 'evolution' and success_rate > 0.8:
                await self._store_evolution_metadata(pattern_data)
                
        except Exception as e:
            logger.error(f"❌ [PATTERNS] Failed to store pattern {pattern_id}: {e}")
            
    async def retrieve_similar_patterns(self, context: Dict, limit: int = 5) -> List[Dict]:
        """Retrieve patterns similar to current context"""
        try:
            # Build semantic query from context
            query = self._build_context_query(context)
            
            # Search in Cognee
            results = await self.cognee_service.search(query, limit=limit)
            
            # Parse and return patterns
            patterns = self._parse_pattern_results(results)
            
            logger.info(f"🔍 [PATTERNS] Retrieved {len(patterns)} similar patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"❌ [PATTERNS] Failed to retrieve patterns: {e}")
            return []
            
    async def store_tool_effectiveness_pattern(self, tool_data: Dict):
        """Store patterns about tool effectiveness in different contexts"""
        pattern_doc = f"""
Tool Effectiveness Pattern
Tool: {tool_data.get('tool_name')}
Context: {tool_data.get('context_type')}
Success Rate: {tool_data.get('success_rate', 0):.2%}
Average Execution Time: {tool_data.get('avg_execution_time', 0):.2f}s
Usage Count: {tool_data.get('usage_count', 0)}

EFFECTIVE IN:
{self._format_list(tool_data.get('effective_contexts', []))}

INEFFECTIVE IN:
{self._format_list(tool_data.get('ineffective_contexts', []))}

BEST PRACTICES:
{self._format_list(tool_data.get('best_practices', []))}

TAGS: tool-pattern, {tool_data.get('tool_name')}, effectiveness
"""
        
        await self.cognee_service.add_data([pattern_doc])
        
    async def store_agent_collaboration_pattern(self, collaboration_data: Dict):
        """Store patterns about effective agent collaborations"""
        agents = collaboration_data.get('agents', [])
        pattern_doc = f"""
Agent Collaboration Pattern
Agents: {', '.join(agents)}
Collaboration Type: {collaboration_data.get('type')}
Success Rate: {collaboration_data.get('success_rate', 0):.2%}
Average Decision Time: {collaboration_data.get('avg_decision_time', 0):.2f}s

EFFECTIVE FOR TASKS:
{self._format_list(collaboration_data.get('effective_tasks', []))}

COLLABORATION PATTERNS:
{self._format_collaboration_patterns(collaboration_data.get('patterns', {}))}

INSIGHTS:
{self._format_list(collaboration_data.get('insights', []))}

TAGS: collaboration-pattern, {', '.join(agents)}
"""
        
        await self.cognee_service.add_data([pattern_doc])
        
    async def get_evolution_recommendations(self, current_metrics: Dict) -> List[Dict]:
        """Get evolution recommendations based on stored patterns"""
        # Query for successful evolution patterns
        query = f"""
        evolution patterns with performance improvement > 10%
        current metrics: {json.dumps(current_metrics)}
        """
        
        results = await self.cognee_service.search(query, limit=10)
        
        recommendations = []
        for result in results:
            if 'evolution' in result.get('content', '').lower():
                recommendation = self._extract_evolution_recommendation(result)
                if recommendation:
                    recommendations.append(recommendation)
                    
        return recommendations
        
    # Private helper methods
    
    def _format_context(self, context: Dict) -> str:
        """Format context dictionary for storage"""
        lines = []
        for key, value in context.items():
            if isinstance(value, dict):
                lines.append(f"- {key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  - {sub_key}: {sub_value}")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)
        
    def _format_actions(self, actions: List) -> str:
        """Format actions list for storage"""
        if not actions:
            return "No actions recorded"
            
        lines = []
        for i, action in enumerate(actions, 1):
            if isinstance(action, dict):
                lines.append(f"{i}. {action.get('type', 'Unknown')}: {action.get('details', '')}")
            else:
                lines.append(f"{i}. {action}")
        return "\n".join(lines)
        
    def _format_outcomes(self, outcomes: Dict) -> str:
        """Format outcomes for storage"""
        lines = []
        for key, value in outcomes.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "No outcomes recorded"
        
    def _format_performance_impact(self, impact: Dict) -> str:
        """Format performance impact for storage"""
        lines = []
        for metric, value in impact.items():
            if isinstance(value, (int, float)):
                change = "+" if value > 0 else ""
                lines.append(f"- {metric}: {change}{value:.2f}%")
            else:
                lines.append(f"- {metric}: {value}")
        return "\n".join(lines) if lines else "No performance impact recorded"
        
    def _format_list(self, items: List) -> str:
        """Format a list of items"""
        if not items:
            return "None"
        return "\n".join(f"- {item}" for item in items)
        
    def _format_collaboration_patterns(self, patterns: Dict) -> str:
        """Format collaboration patterns"""
        lines = []
        for pattern_name, details in patterns.items():
            lines.append(f"- {pattern_name}: {details}")
        return "\n".join(lines) if lines else "No patterns recorded"
        
    def _generate_tags(self, pattern_data: Dict) -> List[str]:
        """Generate searchable tags for a pattern"""
        tags = []
        
        # Add type tag
        pattern_type = pattern_data.get('type', 'unknown')
        tags.append(f"{pattern_type}-pattern")
        
        # Add performance tags
        success_rate = pattern_data.get('success_rate', 0)
        if success_rate > 0.9:
            tags.append('high-success')
        elif success_rate > 0.7:
            tags.append('moderate-success')
            
        # Add context tags
        context = pattern_data.get('context', {})
        if 'goal_type' in context:
            tags.append(f"goal-{context['goal_type']}")
        if 'tool' in context:
            tags.append(f"tool-{context['tool']}")
            
        # Add impact tags
        impact = pattern_data.get('performance_impact', {})
        if any(v > 10 for v in impact.values() if isinstance(v, (int, float))):
            tags.append('high-impact')
            
        return tags
        
    def _build_context_query(self, context: Dict) -> str:
        """Build semantic search query from context"""
        query_parts = []
        
        # Add goal information
        if 'goal' in context:
            query_parts.append(f"goal: {context['goal']}")
            
        # Add current metrics
        if 'metrics' in context:
            metrics = context['metrics']
            query_parts.append(f"performance metrics: {json.dumps(metrics)}")
            
        # Add problem description
        if 'problem' in context:
            query_parts.append(f"problem: {context['problem']}")
            
        # Add constraints
        if 'constraints' in context:
            query_parts.append(f"constraints: {context['constraints']}")
            
        return " ".join(query_parts)
        
    def _parse_pattern_results(self, results: List[Dict]) -> List[Dict]:
        """Parse Cognee results into pattern objects"""
        patterns = []
        
        for result in results:
            content = result.get('content', '')
            
            # Extract pattern information
            pattern = {
                'id': self._extract_field(content, 'Pattern ID'),
                'type': self._extract_field(content, 'Type'),
                'success_rate': self._extract_percentage(content, 'Success Rate'),
                'content': content,
                'relevance_score': result.get('score', 0)
            }
            
            # Extract performance impact if present
            if 'PERFORMANCE IMPACT:' in content:
                impact_section = content.split('PERFORMANCE IMPACT:')[1].split('\n\n')[0]
                pattern['performance_impact'] = self._parse_impact_section(impact_section)
                
            patterns.append(pattern)
            
        return patterns
        
    def _extract_field(self, content: str, field_name: str) -> str:
        """Extract a field value from pattern content"""
        for line in content.split('\n'):
            if line.startswith(f"{field_name}:"):
                return line.split(':', 1)[1].strip()
        return ''
        
    def _extract_percentage(self, content: str, field_name: str) -> float:
        """Extract a percentage value from pattern content"""
        value_str = self._extract_field(content, field_name)
        if value_str and '%' in value_str:
            try:
                return float(value_str.rstrip('%')) / 100
            except ValueError:
                pass
        return 0.0
        
    def _parse_impact_section(self, impact_text: str) -> Dict:
        """Parse performance impact section"""
        impact = {}
        for line in impact_text.split('\n'):
            if ':' in line and line.strip().startswith('-'):
                parts = line.strip('- ').split(':', 1)
                if len(parts) == 2:
                    metric = parts[0].strip()
                    value_str = parts[1].strip().rstrip('%')
                    try:
                        value = float(value_str)
                        impact[metric] = value
                    except ValueError:
                        impact[metric] = value_str
        return impact
        
    def _extract_evolution_recommendation(self, result: Dict) -> Optional[Dict]:
        """Extract evolution recommendation from search result"""
        content = result.get('content', '')
        
        if 'evolution' not in content.lower():
            return None
            
        recommendation = {
            'pattern_id': self._extract_field(content, 'Pattern ID'),
            'target': self._extract_field(content, 'Target'),
            'expected_improvement': self._extract_percentage(content, 'Expected Improvement'),
            'risk_level': self._extract_field(content, 'Risk Level') or 'medium',
            'description': content,
            'relevance_score': result.get('score', 0)
        }
        
        return recommendation if recommendation['pattern_id'] else None
        
    async def _store_evolution_metadata(self, pattern_data: Dict):
        """Store additional metadata for highly successful evolution patterns"""
        metadata_doc = f"""
Evolution Success Metadata
Pattern ID: {pattern_data.get('id')}
File: {pattern_data.get('target_file')}
Modification Type: {pattern_data.get('modification_type')}
Code Before: {pattern_data.get('code_before', 'Not recorded')}
Code After: {pattern_data.get('code_after', 'Not recorded')}
Validation Steps: {self._format_list(pattern_data.get('validation_steps', []))}
Rollback Strategy: {pattern_data.get('rollback_strategy', 'Standard rollback')}

TAGS: evolution-success, reusable-pattern
"""
        
        await self.cognee_service.add_data([metadata_doc])