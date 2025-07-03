# GraphFlow External Stimuli System - Code Walkthrough

## Table of Contents

1. [System Overview](#system-overview)
2. [GraphFlow Nodes Explained](#graphflow-nodes-explained)
3. [Decision Engine Implementation](#decision-engine-implementation)
4. [Integration Interfaces](#integration-interfaces)
5. [Concurrent Execution Handling](#concurrent-execution-handling)
6. [Important Algorithms](#important-algorithms)
7. [Design Patterns Used](#design-patterns-used)

## System Overview

The GraphFlow External Stimuli System is built around Microsoft AutoGen's GraphFlow pattern, implementing a pipeline of processing nodes that handle external stimuli through categorization, analysis, decision-making, and execution.

### Core Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Stimuli   │────▶│  GraphFlow  │────▶│  Execution  │
│   Input     │     │   Pipeline  │     │   Output    │
└─────────────┘     └─────────────┘     └─────────────┘
```

## GraphFlow Nodes Explained

### Node Base Pattern

All nodes follow a consistent pattern for initialization, processing, and cleanup:

```python
class BaseNode:
    """Base pattern for all GraphFlow nodes."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_structured_logger(self.__class__.__name__)
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize node resources."""
        try:
            # Initialize resources
            await self._setup_resources()
            self.is_initialized = True
            self.logger.info(f"{self.__class__.__name__} initialized")
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise
    
    async def process(self, input_data: Any) -> Any:
        """Process input through the node."""
        if not self.is_initialized:
            raise RuntimeError("Node not initialized")
        
        start_time = time.time()
        try:
            result = await self._do_processing(input_data)
            processing_time = time.time() - start_time
            
            self.logger.info(
                "Processing completed",
                input_id=getattr(input_data, 'id', 'unknown'),
                processing_time=processing_time
            )
            return result
            
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Cleanup node resources."""
        await self._cleanup_resources()
        self.is_initialized = False
```

### 1. Categorizer Node

The Categorizer Node classifies incoming stimuli into predefined categories using a hybrid approach:

```python
class StimuliCategorizerNode:
    """
    Categorizes stimuli using:
    1. LLM-based classification (primary)
    2. Keyword pattern matching (fallback)
    3. Source-based rules (override)
    """
    
    async def process(self, stimuli: ExternalStimuli) -> CategorizedStimuli:
        # Extract features for classification
        features = self._extract_features(stimuli)
        
        # Try LLM classification first
        if self.config.use_llm:
            try:
                category_result = await self._apply_llm_classification(features)
            except Exception as e:
                self.logger.warning(f"LLM classification failed: {e}")
                category_result = self._apply_keyword_classification(features)
        else:
            category_result = self._apply_keyword_classification(features)
        
        # Apply source-based overrides
        if stimuli.source == 'admin_console':
            category_result = {
                'category': StimuliCategory.DIRECT_ADMIN,
                'confidence': 0.95,
                'method': 'source_override'
            }
        
        # Create categorized stimuli
        return CategorizedStimuli(
            **stimuli.__dict__,
            category=category_result['category'],
            confidence=category_result['confidence'],
            classification_metadata=category_result
        )
```

**Key Features:**
- Multi-method classification for robustness
- Configurable confidence thresholds
- Built-in caching for performance
- Feature extraction for better accuracy

### 2. Analyzer Node

The Analyzer Node performs deep contextual analysis on categorized stimuli:

```python
class StimuliAnalyzerNode:
    """
    Analyzes stimuli to extract:
    - Intent and entities
    - Sentiment and urgency
    - Context requirements
    - Action recommendations
    """
    
    async def process(self, categorized: CategorizedStimuli) -> AnalyzedStimuli:
        # Parallel analysis tasks
        analysis_tasks = [
            self._extract_entities(categorized),
            self._analyze_sentiment(categorized),
            self._determine_urgency(categorized),
            self._get_context_requirements(categorized),
            self._generate_recommendations(categorized)
        ]
        
        # Execute analyses concurrently
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Aggregate results
        entities, sentiment, urgency, context_reqs, recommendations = results
        
        # Build comprehensive analysis
        analysis = {
            'entities': entities if not isinstance(entities, Exception) else [],
            'sentiment': sentiment if not isinstance(sentiment, Exception) else 'neutral',
            'urgency': urgency if not isinstance(urgency, Exception) else 0.5,
            'context_required': context_reqs if not isinstance(context_reqs, Exception) else [],
            'recommended_actions': recommendations if not isinstance(recommendations, Exception) else []
        }
        
        # Enrich with historical context
        if self.context_service:
            historical_context = await self.context_service.get_relevant_context(
                user_id=categorized.metadata.get('user_id'),
                category=categorized.category,
                limit=5
            )
            analysis['historical_context'] = historical_context
        
        return AnalyzedStimuli(
            **categorized.__dict__,
            analysis=analysis,
            analysis_timestamp=datetime.now()
        )
```

**Key Features:**
- Concurrent analysis operations
- Graceful error handling
- Context enrichment from history
- Comprehensive metadata extraction

### 3. Router Node

The Router Node applies decision matrix rules to determine processing paths:

```python
class DecisionRouterNode:
    """
    Routes stimuli based on:
    - Decision matrix rules
    - Dynamic conditions
    - Emergency overrides
    - Confidence thresholds
    """
    
    async def process(self, analyzed: AnalyzedStimuli) -> RoutingDecision:
        # Check emergency overrides first
        if override := await self._check_emergency_overrides(analyzed):
            return override
    
        # Evaluate all applicable rules
        applicable_rules = []
        for rule in self.decision_matrix.get_active_rules():
            if self._evaluate_conditions(rule.conditions, analyzed):
                applicable_rules.append(rule)
    
        # Sort by priority and select best match
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        
        if applicable_rules:
            selected_rule = applicable_rules[0]
            base_confidence = analyzed.confidence
            
            # Apply confidence modifiers
            confidence = min(1.0, max(0.0, 
                base_confidence + selected_rule.confidence_modifier
            ))
            
            return RoutingDecision(
                decision=selected_rule.decision,
                confidence_score=confidence,
                reasoning=f"Applied rule: {selected_rule.name}",
                applied_rules=[r.id for r in applicable_rules],
                analyzed_stimuli=analyzed
            )
        
        # Fallback to default decision
        return RoutingDecision(
            decision=ProcessingDecision(self.config.default_decision),
            confidence_score=0.5,
            reasoning="No matching rules, using default",
            analyzed_stimuli=analyzed
        )
    
    def _evaluate_conditions(self, conditions: Dict, analyzed: AnalyzedStimuli) -> bool:
        """Recursively evaluate complex conditions."""
        if 'or' in conditions:
            return any(self._evaluate_conditions(c, analyzed) for c in conditions['or'])
        
        if 'and' in conditions:
            return all(self._evaluate_conditions(c, analyzed) for c in conditions['and'])

        # Simple conditions
        for field, expected in conditions.items():
            actual = self._get_nested_value(analyzed, field)
            
            if isinstance(expected, dict) and 'operator' in expected:
                # Comparison operators
                if not self._evaluate_comparison(actual, expected):
                    return False
            elif isinstance(expected, list):
                # Any match in list
                if actual not in expected:
                    return False
            else:
                # Exact match
                if actual != expected:
                    return False
        
        return True
```

**Key Features:**
- Rule priority system
- Complex condition evaluation
- Emergency override support
- Confidence score calculation

### 4. Executor Node

The Executor Node coordinates with external systems to execute decisions:

```python
class ExecutionCoordinatorNode:
    """
    Executes routing decisions by:
    - Coordinating with System1/System2
    - Managing concurrent operations
    - Handling retries and failures
    - Tracking execution results
    """
    
    async def process(self, routing: RoutingDecision) -> ExecutionResult:
        execution_tasks = []
        
        # Determine execution strategy
        if routing.decision == ProcessingDecision.AVATAR_AND_ANALYSIS:
            # Execute both systems concurrently
            execution_tasks.extend([
                self._execute_system1(routing),
                self._execute_system2(routing)
            ])
        elif routing.decision == ProcessingDecision.ANALYSIS_ONLY:
            # Only System2
            execution_tasks.append(self._execute_system2(routing))
        elif routing.decision == ProcessingDecision.LOG_ONLY:
            # Just log
            execution_tasks.append(self._execute_logging(routing))
        
        # Execute with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*execution_tasks, return_exceptions=True),
                timeout=self.config.execution_timeout
            )
            
            # Process results
            success = all(
                r.get('success', False) if isinstance(r, dict) else False 
                for r in results
            )
            
            return ExecutionResult(
                decision=routing.decision,
                success=success,
                system1_result=results[0] if len(results) > 0 else None,
                system2_result=results[1] if len(results) > 1 else None,
                execution_time=time.time() - start_time,
                metadata={
                    'stimuli_id': routing.analyzed_stimuli.id,
                    'retries': retry_count
                }
            )
            
        except asyncio.TimeoutError:
            self.logger.error("Execution timeout", stimuli_id=routing.analyzed_stimuli.id)
            return ExecutionResult(
                decision=routing.decision,
                success=False,
                error="Execution timeout"
            )
    
    async def _execute_with_retry(self, func, *args, **kwargs):
        """Execute with exponential backoff retry."""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise last_error
```

**Key Features:**
- Concurrent system execution
- Retry with exponential backoff
- Timeout management
- Result aggregation

## Decision Engine Implementation

The decision engine is the brain of the system, evaluating complex rules and conditions:

### Decision Matrix Structure

```python
class DecisionMatrix:
    """
    Manages decision rules with:
    - Rule prioritization
    - Dynamic loading
    - Condition evaluation
    - Performance optimization
    """
    
    def __init__(self):
        self.rules: List[DecisionRule] = []
        self._rule_index: Dict[str, DecisionRule] = {}
        self._compiled_conditions: Dict[str, Any] = {}
    
    def load_rules(self, rules_config: List[Dict]) -> None:
        """Load and validate rules."""
        for rule_data in rules_config:
            rule = DecisionRule.from_dict(rule_data)
            
            # Validate rule
            if not self._validate_rule(rule):
                self.logger.warning(f"Invalid rule: {rule.id}")
                continue
            
            # Compile conditions for performance
            self._compiled_conditions[rule.id] = self._compile_conditions(rule.conditions)
            
            self.rules.append(rule)
            self._rule_index[rule.id] = rule
        
        # Sort by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[DecisionRule]:
        """Evaluate context against all rules."""
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # Use compiled conditions for speed
            compiled = self._compiled_conditions.get(rule.id)
            if compiled and self._evaluate_compiled(compiled, context):
                return rule
        
        return None
```

### Condition Evaluation Engine

```python
class ConditionEvaluator:
    """
    Evaluates complex conditions with support for:
    - Nested boolean logic (AND, OR, NOT)
    - Comparison operators
    - Pattern matching
    - Custom functions
    """
    
    def evaluate(self, condition: Dict, context: Dict) -> bool:
        # Boolean operators
        if 'or' in condition:
            return any(self.evaluate(c, context) for c in condition['or'])
        
        if 'and' in condition:
            return all(self.evaluate(c, context) for c in condition['and'])
        
        if 'not' in condition:
            return not self.evaluate(condition['not'], context)
        
        # Field comparisons
        for field, expected in condition.items():
            actual = self._resolve_field(field, context)
            
            if isinstance(expected, dict):
                # Complex comparison
                if not self._evaluate_comparison(actual, expected):
                    return False
            else:
                # Simple equality
                if actual != expected:
                    return False
        
        return True
    
    def _evaluate_comparison(self, actual: Any, comparison: Dict) -> bool:
        """Evaluate comparison operators."""
        operator = comparison.get('operator', 'eq')
        value = comparison.get('value')
        
        operators = {
            'eq': lambda a, v: a == v,
            'ne': lambda a, v: a != v,
            'gt': lambda a, v: a > v,
            'gte': lambda a, v: a >= v,
            'lt': lambda a, v: a < v,
            'lte': lambda a, v: a <= v,
            'in': lambda a, v: a in v,
            'contains': lambda a, v: v in str(a),
            'regex': lambda a, v: bool(re.match(v, str(a))),
            'exists': lambda a, v: a is not None if v else a is None
        }
        
        if operator in operators:
            return operators[operator](actual, value)
        
        raise ValueError(f"Unknown operator: {operator}")
```

## Integration Interfaces

### System1 Interface (Avatar/Speech)

```python
class System1Interface:
    """
    Interface for Avatar/Speech system with:
    - Connection pooling
    - Request queuing
    - State synchronization
    - Error recovery
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.endpoint = config['endpoint']
        self.session: Optional[aiohttp.ClientSession] = None
        self._request_queue = asyncio.Queue(maxsize=100)
        self._state_cache = {}
    
    async def trigger_avatar_response(
        self, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trigger avatar to speak with given content."""
        # Check current state
        current_state = await self._get_avatar_state()
        
        if current_state.get('is_speaking'):
            # Queue if already speaking
            await self._request_queue.put({
                'content': content,
                'metadata': metadata,
                'timestamp': datetime.now()
            })
            return {'queued': True, 'queue_size': self._request_queue.qsize()}
        
        # Prepare request
        request_data = {
            'text': content,
            'voice_settings': {
                'voice_id': metadata.get('voice_id', 'default'),
                'speed': metadata.get('speed', 1.0),
                'pitch': metadata.get('pitch', 1.0)
            },
            'expression': self._determine_expression(content, metadata),
            'priority': metadata.get('priority', 'medium')
        }
        
        # Send request with retry
        async with self._request_semaphore:
            response = await self._send_with_retry(
                'POST',
                f'{self.endpoint}/api/speak',
                json=request_data
            )
        
        # Update state cache
        self._state_cache['last_speech'] = {
            'content': content,
            'timestamp': datetime.now(),
            'speech_id': response.get('speech_id')
        }
        
        return response
    
    def _determine_expression(self, content: str, metadata: Dict) -> str:
        """Determine avatar expression based on content."""
        # Sentiment-based expression mapping
        sentiment = metadata.get('sentiment', 'neutral')
        
        expression_map = {
            'positive': 'happy',
            'negative': 'sad',
            'angry': 'angry',
            'surprised': 'surprised',
            'neutral': 'neutral'
        }
        
        return expression_map.get(sentiment, 'neutral')
```

### System2 Interface (Multi-Agent)

```python
class System2Interface:
    """
    Interface for Multi-Agent system with:
    - Agent pool management
    - Task distribution
    - Result aggregation
    - Progress tracking
    """
    
    async def submit_for_analysis(
        self, 
        analyzed_stimuli: AnalyzedStimuli
    ) -> Dict[str, Any]:
        """Submit stimuli for multi-agent analysis."""
        # Prepare analysis request
        analysis_request = {
            'stimuli_id': analyzed_stimuli.id,
            'content': analyzed_stimuli.content,
            'category': analyzed_stimuli.category.value,
            'analysis': analyzed_stimuli.analysis,
            'context': analyzed_stimuli.get_context(),
            'requested_agents': self._select_agents(analyzed_stimuli)
        }
        
        # Submit to agent system
        response = await self._send_with_retry(
            'POST',
            f'{self.endpoint}/api/analysis/submit',
            json=analysis_request
        )
        
        task_id = response['task_id']
        
        # Poll for results with timeout
        start_time = time.time()
        while time.time() - start_time < self.config.analysis_timeout:
            result = await self._check_analysis_status(task_id)
            
            if result['status'] == 'completed':
                return self._aggregate_agent_results(result['agent_results'])
            
            elif result['status'] == 'failed':
                raise RuntimeError(f"Analysis failed: {result.get('error')}")
            
            # Wait before next poll
            await asyncio.sleep(self.config.poll_interval)
        
        raise asyncio.TimeoutError("Analysis timeout")
    
    def _select_agents(self, analyzed: AnalyzedStimuli) -> List[str]:
        """Select appropriate agents based on stimuli."""
        agents = ['observer_agent']  # Always include observer
        
        # Add specialized agents based on category
        if analyzed.category == StimuliCategory.USER_INTERACTION:
            agents.append('cognitive_ai_agent')
        
        if 'technical' in analyzed.analysis.get('keywords', []):
            agents.append('programmer_agent')
        
        if analyzed.analysis.get('urgency', 0) > 0.7:
            agents.append('priority_handler_agent')
        
        return agents
    
    def _aggregate_agent_results(self, agent_results: List[Dict]) -> Dict[str, Any]:
        """Aggregate results from multiple agents."""
        aggregated = {
            'consensus': None,
            'recommendations': [],
            'insights': [],
            'confidence': 0.0,
            'agent_responses': {}
        }
        
        # Collect all recommendations and insights
        for result in agent_results:
            agent_name = result['agent_name']
            aggregated['agent_responses'][agent_name] = result
            
            if 'recommendations' in result:
                aggregated['recommendations'].extend(result['recommendations'])
            
            if 'insights' in result:
                aggregated['insights'].extend(result['insights'])
        
        # Calculate consensus
        decisions = [r.get('decision') for r in agent_results if 'decision' in r]
        if decisions:
            # Most common decision
            from collections import Counter
            decision_counts = Counter(decisions)
            aggregated['consensus'] = decision_counts.most_common(1)[0][0]
            
            # Confidence based on agreement
            aggregated['confidence'] = decision_counts[aggregated['consensus']] / len(decisions)
        
        return aggregated
```

## Concurrent Execution Handling

### Request Context Manager

```python
class RequestContextManager:
    """
    Manages concurrent request execution with:
    - Request tracking
    - Resource limiting
    - Graceful degradation
    - Performance monitoring
    """
    
    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent
        self._active_requests = 0
        self._request_queue = asyncio.Queue()
        self._processing_lock = asyncio.Lock()
        self._request_contexts: Dict[str, RequestContext] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    @asynccontextmanager
    async def request_context(self, request_id: str):
        """Context manager for request lifecycle."""
        # Wait for available slot
        await self._semaphore.acquire()
        
        # Create context
        context = RequestContext(
            request_id=request_id,
            start_time=time.time(),
            resources={}
        )
        
        async with self._processing_lock:
            self._active_requests += 1
            self._request_contexts[request_id] = context
        
        try:
            yield context
        finally:
            # Cleanup
            async with self._processing_lock:
                self._active_requests -= 1
                del self._request_contexts[request_id]
            
            self._semaphore.release()
            
            # Record metrics
            processing_time = time.time() - context.start_time
            self._record_metrics(request_id, processing_time)
```

### Async Task Coordination

```python
class TaskCoordinator:
    """
    Coordinates async tasks with:
    - Task grouping
    - Failure isolation
    - Progress tracking
    - Result aggregation
    """
    
    async def execute_task_group(
        self, 
        tasks: List[Callable], 
        strategy: str = 'all'
    ) -> List[Any]:
        """Execute a group of tasks with specified strategy."""
        if strategy == 'all':
            # Wait for all tasks
            return await self._execute_all(tasks)
        elif strategy == 'any':
            # Return when any task completes
            return await self._execute_any(tasks)
        elif strategy == 'race':
            # Return first successful result
            return await self._execute_race(tasks)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    async def _execute_all(self, tasks: List[Callable]) -> List[Any]:
        """Execute all tasks, isolating failures."""
        results = []
        
        # Create wrapped tasks that handle errors
        wrapped_tasks = []
        for i, task in enumerate(tasks):
            async def wrapped(task_idx=i, task_func=task):
                try:
                    return await task_func()
                except Exception as e:
                    self.logger.error(f"Task {task_idx} failed: {e}")
                    return TaskError(task_idx, str(e))
            
            wrapped_tasks.append(wrapped())
        
        # Execute concurrently
        results = await asyncio.gather(*wrapped_tasks)
        
        # Check for failures
        failures = [r for r in results if isinstance(r, TaskError)]
        if failures and self.config.fail_fast:
            raise RuntimeError(f"{len(failures)} tasks failed")
        
        return results
```

## Important Algorithms

### 1. Confidence Score Calculation

```python
def calculate_composite_confidence(
    categorization_confidence: float,
    analysis_confidence: float,
    context_confidence: float,
    weights: Dict[str, float] = None
) -> float:
    """
    Calculate weighted confidence score.
    
    Uses a weighted harmonic mean to penalize low scores
    more than arithmetic mean would.
    """
    if weights is None:
        weights = {
            'categorization': 0.4,
            'analysis': 0.3,
            'context': 0.3
        }
    
    # Validate weights sum to 1.0
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 0.001:
        weights = {k: v/total_weight for k, v in weights.items()}
    
    # Calculate weighted harmonic mean
    scores = {
        'categorization': categorization_confidence,
        'analysis': analysis_confidence,
        'context': context_confidence
    }
    
    # Avoid division by zero
    weighted_sum = 0.0
    for component, score in scores.items():
        if score > 0:
            weighted_sum += weights[component] / score
    
    if weighted_sum > 0:
        return 1.0 / weighted_sum
    else:
        return 0.0
```

### 2. Priority Queue with Decay

```python
class PriorityQueueWithDecay:
    """
    Priority queue where priorities decay over time
    to prevent starvation of lower priority items.
    """
    
    def __init__(self, decay_rate: float = 0.1):
        self.decay_rate = decay_rate
        self._queue: List[Tuple[float, float, Any]] = []
        self._lock = asyncio.Lock()
    
    async def put(self, item: Any, priority: float) -> None:
        """Add item with priority."""
        async with self._lock:
            timestamp = time.time()
            heapq.heappush(self._queue, (-priority, timestamp, item))
    
    async def get(self) -> Any:
        """Get highest priority item with decay applied."""
        async with self._lock:
            if not self._queue:
                raise asyncio.QueueEmpty()
            
            # Apply decay to all items
            current_time = time.time()
            updated_queue = []
            
            for neg_priority, timestamp, item in self._queue:
                age = current_time - timestamp
                decay = self.decay_rate * age
                new_priority = -neg_priority - decay
                
                heapq.heappush(updated_queue, (-new_priority, timestamp, item))
            
            self._queue = updated_queue
            
            # Get highest priority item
            _, _, item = heapq.heappop(self._queue)
            return item
```

### 3. Circuit Breaker Pattern

```python
class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Failing, reject requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self.state = 'CLOSED'
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_count = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        async with self._lock:
            if self.state == 'OPEN':
                # Check if we should try half-open
                if (time.time() - self.last_failure_time) > self.recovery_timeout:
                    self.state = 'HALF_OPEN'
                    self.half_open_count = 0
                else:
                    raise CircuitBreakerOpen("Circuit breaker is OPEN")
            
            if self.state == 'HALF_OPEN' and self.half_open_count >= self.half_open_requests:
                # Successful half-open tests, close circuit
                self.state = 'CLOSED'
                self.failure_count = 0
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - update state
            async with self._lock:
                if self.state == 'HALF_OPEN':
                    self.half_open_count += 1
                elif self.state == 'CLOSED':
                    self.failure_count = 0
            
            return result
            
        except Exception as e:
            # Failure - update state
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.state == 'HALF_OPEN':
                    # Failed during recovery, reopen
                    self.state = 'OPEN'
                elif self.failure_count >= self.failure_threshold:
                    # Too many failures, open circuit
                    self.state = 'OPEN'
            
            raise
```

## Design Patterns Used

### 1. Chain of Responsibility

The GraphFlow pipeline implements Chain of Responsibility where each node processes and passes data to the next:

```python
class ProcessingPipeline:
    """Chain of Responsibility implementation."""
    
    def __init__(self):
        self.nodes: List[BaseNode] = []
    
    def add_node(self, node: BaseNode) -> 'ProcessingPipeline':
        """Add node to pipeline."""
        self.nodes.append(node)
        return self
    
    async def process(self, input_data: Any) -> Any:
        """Process through all nodes in sequence."""
        result = input_data
        
        for node in self.nodes:
            result = await node.process(result)
            
            # Allow nodes to stop processing
            if hasattr(result, 'stop_processing') and result.stop_processing:
                break
        
        return result
```

### 2. Strategy Pattern

Decision strategies are implemented using the Strategy pattern:

```python
class DecisionStrategy(ABC):
    """Abstract strategy for decision making."""
    
    @abstractmethod
    async def decide(self, context: AnalyzedStimuli) -> ProcessingDecision:
        """Make a decision based on context."""
        pass

class RuleBasedStrategy(DecisionStrategy):
    """Rule-based decision strategy."""
    
    async def decide(self, context: AnalyzedStimuli) -> ProcessingDecision:
        # Apply rules
        pass

class MLBasedStrategy(DecisionStrategy):
    """Machine learning based strategy."""
    
    async def decide(self, context: AnalyzedStimuli) -> ProcessingDecision:
        # Use ML model
        pass

class DecisionContext:
    """Context for strategy selection."""
    
    def __init__(self):
        self.strategies = {
            'rules': RuleBasedStrategy(),
            'ml': MLBasedStrategy()
        }
    
    async def make_decision(
        self, 
        stimuli: AnalyzedStimuli, 
        strategy_name: str = 'rules'
    ) -> ProcessingDecision:
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        return await strategy.decide(stimuli)
```

### 3. Observer Pattern

Event notification system using Observer pattern:

```python
class EventBus:
    """Event bus for system-wide notifications."""
    
    def __init__(self):
        self._observers: Dict[str, List[Callable]] = {}
        self._async_observers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable, is_async: bool = False):
        """Subscribe to event type."""
        if is_async:
            self._async_observers.setdefault(event_type, []).append(handler)
        else:
            self._observers.setdefault(event_type, []).append(handler)
    
    async def publish(self, event_type: str, data: Any):
        """Publish event to all subscribers."""
        # Sync handlers
        for handler in self._observers.get(event_type, []):
            try:
                handler(data)
            except Exception as e:
                self.logger.error(f"Sync handler error: {e}")
        
        # Async handlers
        async_handlers = self._async_observers.get(event_type, [])
        if async_handlers:
            await asyncio.gather(
                *[handler(data) for handler in async_handlers],
                return_exceptions=True
            )

# Usage
event_bus = EventBus()

# Subscribe to events
event_bus.subscribe('stimuli.processed', lambda data: print(f"Processed: {data}"))
event_bus.subscribe('decision.made', async_notification_handler, is_async=True)

# Publish events
await event_bus.publish('stimuli.processed', {'stimuli_id': '123', 'decision': 'AVATAR_AND_ANALYSIS'})
```

### 4. Factory Pattern

Node creation using Factory pattern:

```python
class NodeFactory:
    """Factory for creating processing nodes."""
    
    _node_types = {
        'categorizer': StimuliCategorizerNode,
        'analyzer': StimuliAnalyzerNode,
        'router': DecisionRouterNode,
        'executor': ExecutionCoordinatorNode
    }
    
    @classmethod
    def create_node(cls, node_type: str, config: Dict[str, Any]) -> BaseNode:
        """Create node of specified type."""
        node_class = cls._node_types.get(node_type)
        if not node_class:
            raise ValueError(f"Unknown node type: {node_type}")
        
        return node_class(config)
    
    @classmethod
    def register_node_type(cls, name: str, node_class: Type[BaseNode]):
        """Register new node type."""
        cls._node_types[name] = node_class

# Usage
categorizer = NodeFactory.create_node('categorizer', categorizer_config)
analyzer = NodeFactory.create_node('analyzer', analyzer_config)
```

### 5. Singleton Pattern

Shared services using Singleton pattern:

```python
class MetricsCollector:
    """Singleton metrics collector."""
    
    _instance: Optional['MetricsCollector'] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self._metrics = {}
            self._lock = asyncio.Lock()
            self.initialized = True
    
    async def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric value."""
        async with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            
            self._metrics[name].append({
                'value': value,
                'timestamp': time.time(),
                'tags': tags or {}
            })

# Global metrics instance
metrics = MetricsCollector()
```

This code walkthrough demonstrates how the GraphFlow External Stimuli System implements sophisticated processing through well-designed nodes, robust error handling, efficient algorithms, and proven design patterns. The system is built for scalability, maintainability, and extensibility.