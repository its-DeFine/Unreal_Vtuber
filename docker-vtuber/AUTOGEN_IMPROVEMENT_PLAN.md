# AutoGen System Improvement Plan

**Created**: December 12, 2024  
**Purpose**: Handoff document for next development session  
**Current State**: System analyzed, initial fixes applied, architectural issues identified

## 🎯 Executive Summary

The AutoGen autonomous agent system is partially functional. The multi-agent conversations work well, but agents don't execute tools. This plan outlines the steps needed to create a truly autonomous system.

## 📍 Current Situation

### What's Working ✅
- Multi-agent AutoGen system with 3 specialized agents
- Intelligent tool selection algorithm (improved with diversity fixes)
- Darwin-Gödel code analysis engine
- Basic API endpoints and health checks
- Cognitive cycles running at ~3/minute

### What's Not Working ❌
- **Critical**: Agents talk but don't execute tools
- Cognee memory service (DNS failures)
- SMART goal initialization
- Memory API response format errors

### Root Cause
**Architectural Mismatch**: The AutoGen agents are designed for conversation, while the tool system expects direct execution. They operate in parallel without integration.

## 🛠️ Priority Tasks

### Task 1: Integrate Tool Execution with AutoGen Agents (CRITICAL)
**Goal**: Make agents actually execute tools, not just discuss them

**Approach A - Function Calling**:
```python
# In main.py, modify agent initialization to include functions
cognitive_ai_agent = AssistantAgent(
    name="cognitive_ai_agent",
    system_message="...",
    functions=[
        {
            "name": "execute_tool",
            "description": "Execute a tool from the registry",
            "parameters": {
                "tool_name": "string",
                "context": "object"
            }
        }
    ]
)
```

**Approach B - Response Parser**:
```python
# Add after agent response
if "EXECUTE_TOOL:" in response:
    tool_name = extract_tool_name(response)
    await registry.execute_tool_async(tool_name, context)
```

**Files to Modify**:
- `/app/CORE/autogen-agent/autogen_agent/main.py` (lines 430-550)
- Consider creating `/app/CORE/autogen-agent/autogen_agent/agent_tool_bridge.py`

### Task 2: Fix Cognee Integration
**Goal**: Either fix DNS or disable Cognee completely

**Option 1 - Disable Cognee**:
```yaml
# In docker-compose.autogen-ollama.yml
environment:
  - COGNEE_URL=""  # Empty disables it
  - COGNEE_API_KEY=""
```

**Option 2 - Fix Cognee Service**:
```yaml
# Add to docker-compose.autogen-ollama.yml
cognee:
  image: cognee/cognee:latest
  container_name: cognee_memory
  ports:
    - "8000:8000"
  networks:
    - autogen_net
```

**Files to Check**:
- `/app/CORE/autogen-agent/autogen_agent/cognitive_memory.py`
- `/app/CORE/autogen-agent/autogen_agent/services/cognee_service.py`

### Task 3: Add Context Generation
**Goal**: Generate meaningful context for tool selection

```python
# Add to cognitive_decision_engine.py
async def generate_context_from_environment():
    context = {
        "iteration": self.iteration_count,
        "time_of_day": datetime.now().hour,
        "recent_errors": self.error_count,
        "goals": await self.get_active_goals(),
        "memory_summary": await self.get_memory_summary(),
        "autonomous": True
    }
    return context
```

### Task 4: Fix API Response Formats
**Goal**: Ensure all APIs return proper dict responses

**Known Issues**:
- Memory API returns lists in some cases
- Goal API has initialization problems

**Files to Fix**:
- `/app/CORE/autogen-agent/autogen_agent/main.py` (API endpoints)
- Check all `return` statements in API functions

## 📋 Implementation Checklist

### Phase 1: Core Integration (1-2 hours)
- [ ] Choose integration approach (Function Calling vs Response Parser)
- [ ] Implement agent-to-tool bridge
- [ ] Test that agents can execute tools
- [ ] Verify tool diversity works

### Phase 2: Memory System (30 mins)
- [ ] Decide on Cognee (fix or disable)
- [ ] Update environment configuration
- [ ] Test memory storage and retrieval
- [ ] Fix API response formats

### Phase 3: Context Enhancement (1 hour)
- [ ] Implement context generation
- [ ] Add environmental awareness
- [ ] Connect to goal system
- [ ] Test context-aware tool selection

### Phase 4: Testing & Validation (1 hour)
- [ ] Run `test_system_capabilities.py`
- [ ] Monitor for 30 minutes
- [ ] Check tool execution diversity
- [ ] Verify autonomous behavior

## 🧪 Test Commands

```bash
# After making changes, rebuild and restart
docker-compose -f docker-compose.autogen-ollama.yml up -d --build autogen_agent

# Monitor logs
docker logs -f autogen_agent_ollama

# Run tests
python3 test_system_capabilities.py
python3 test_autogen_basic.py

# Check specific behaviors
curl http://localhost:8201/api/statistics
```

## 📊 Success Criteria

The system will be considered successful when:

1. **Tool Execution**: Agents execute at least 1 tool per minute
2. **Tool Diversity**: No single tool exceeds 50% of executions
3. **Memory Works**: No errors in memory storage/retrieval
4. **Goals Active**: Can create and track SMART goals
5. **True Autonomy**: System takes actions without human prompting

## 💡 Key Insights from Analysis

1. **The Big Fix**: Connect agent decisions to tool execution
2. **Simplify First**: Consider disabling Cognee until core works
3. **Context Matters**: Empty context leads to poor tool selection
4. **Monitor Everything**: Add logging to track agent->tool flow

## 🚨 Common Pitfalls to Avoid

1. Don't modify AutoGen internals - use its extension points
2. Test each change incrementally
3. Keep the feedback loop short (test every 10 mins)
4. If stuck, simplify rather than add complexity

## 📚 Relevant Documentation

- AutoGen Function Calling: https://microsoft.github.io/autogen/docs/Use-Cases/agent_chat/
- Tool Registry: `/app/CORE/autogen-agent/autogen_agent/tool_registry.py`
- Current Architecture: `/home/geo/docker-vt/ARCHITECTURE_TRUTH.md`
- Test Suites: `/home/geo/docker-vt/test_*.py`

## 🎬 Next Steps

1. Start with Task 1 - it's the most critical
2. Use Approach B (Response Parser) for quicker results
3. Test frequently with the provided test scripts
4. Document any new findings in this file

Good luck! The system has great potential - it just needs the agents to stop talking and start doing! 🚀