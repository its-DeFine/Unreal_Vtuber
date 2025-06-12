# 🔬 AutoGen Cognitive Enhancement - Standalone Testing

**Mode**: Standalone Cognitive Testing  
**Dependencies**: PostgreSQL only  
**External Services**: None required  

---

## 🎯 **Overview**

This standalone mode allows you to test the AutoGen Cognitive Enhancement system without any external dependencies like NeuroSync VTuber integration or Redis. Perfect for:

- **Core cognitive functionality testing**
- **Memory and decision engine validation**  
- **Development and debugging**
- **Initial deployment verification**

## 🚀 **Quick Start - Standalone Mode**

### **Option 1: Minimal Setup (PostgreSQL only)**

```bash
# Start just PostgreSQL and the cognitive agent
docker-compose -f docker-compose.standalone.yml up postgres autogen_cognitive_standalone -d

# Check system status
curl http://localhost:8100/api/cognitive/status

# Expected response:
{
  "cognitive_enhancement_enabled": true,
  "iteration_count": 1,
  "cognee_url": null,
  "cognee_configured": false,
  "status": "cognitive"
}
```

### **Option 2: With Cognee Knowledge Graph**

```bash
# Start full standalone system with Cognee
docker-compose -f docker-compose.standalone.yml up -d

# Check cognitive status
curl http://localhost:8100/api/cognitive/status

# Expected response:
{
  "cognitive_enhancement_enabled": true,
  "iteration_count": 1,
  "cognee_url": "http://cognee:8000", 
  "cognee_configured": true,
  "status": "cognitive"
}
```

### **Option 3: Pure Standalone (No Cognee)**

```bash
# Edit docker-compose.standalone.yml and comment out:
# - COGNEE_URL=http://cognee:8000
# - COGNEE_API_KEY=${COGNEE_API_KEY:-test_api_key}
# And comment out the cognee service section

# Then start minimal system
docker-compose -f docker-compose.standalone.yml up postgres autogen_cognitive_standalone -d
```

## 📊 **What You'll See in Standalone Mode**

### **Cognitive Agent Logs**
```
🚀 [MAIN] Initializing AutoGen Cognitive Enhancement System...
🔬 [MAIN] Running in STANDALONE mode - no external service dependencies
🧠 [COGNITIVE_MEMORY] Initializing...
🧠 [COGNITIVE_MEMORY] Cognee not configured - using PostgreSQL only
✅ [COGNITIVE_MEMORY] Database connection established
📋 [MAIN] Loaded 2 tools
🧠 [COGNITIVE_DECISION] Enhanced decision engine initialized
✅ [MAIN] Cognitive system initialized successfully
🧠 [MAIN] Cognitive system thread started
🚀 [COGNITIVE_LOOP] Starting enhanced cognitive decision loop

🧠 [COGNITIVE_CYCLE] Starting iteration #1
🔍 [COGNITIVE_DECISION] Enhancing context with memories...
⚡ [COGNITIVE_DECISION] Selecting optimal tool...
🎯 [COGNITIVE_DECISION] Selected tool: cognitive_vtuber_tool (score: 0.500)
🎭 [COGNITIVE_VTUBER] Generated message: 🧠 Cognitive AutoGen Agent - Cycle #1...
✅ [COGNITIVE_DECISION] Decision completed in 0.45s using cognitive_vtuber_tool
🎭 [VTUBER] Message (standalone): 🧠 Cognitive AutoGen Agent - Cycle #1. [Cognitive Enhancement Active]
🔗 [SCB] State (standalone): {
  "iteration": 1,
  "tool_used": "cognitive_vtuber_tool",
  "success": true,
  "timestamp": 1647875269.123,
  "cognitive_enhanced": false
}
✅ [COGNITIVE_CYCLE] Iteration #1 completed successfully
🔄 [COGNITIVE_LOOP] Cognitive cycle completed in 0.52s
```

### **Expected Behavior**

1. **🧠 Cognitive Memory**: Stores interactions in PostgreSQL
2. **⚡ Decision Engine**: Learns tool performance over time
3. **🎭 VTuber Messages**: Displayed in logs (no external service calls)
4. **🔗 SCB State**: Logged locally (no Redis dependency)
5. **📊 Memory Building**: Each cycle adds to the cognitive memory
6. **🎯 Tool Selection**: Gets smarter with each iteration

## 🧪 **Testing Scenarios**

### **Test 1: Basic Cognitive Functionality**

```bash
# Watch the logs for cognitive patterns
docker logs autogen_cognitive_standalone -f

# You should see:
# - Increasing iteration numbers
# - Memory storage and retrieval
# - Tool selection learning
# - Cognitive enhancement indicators
```

### **Test 2: Memory Persistence**

```bash
# Restart the agent
docker restart autogen_cognitive_standalone

# Check if memory persists
curl http://localhost:8100/api/cognitive/status

# Logs should show memory retrieval from previous sessions
```

### **Test 3: Run Tests Inside Container**

```bash
# Run the cognitive test suite
docker exec -it autogen_cognitive_standalone python test_cognitive_system.py

# Expected output:
# ✅ Tool Registry test passed
# ✅ Cognitive Memory test passed  
# ✅ Decision Engine test passed
# ✅ Full System Integration test passed
# 🎉 All tests passed! Cognitive enhancement system is ready.
```

## 📈 **Performance Monitoring**

### **Key Metrics to Watch**

1. **Decision Time**: Should improve over iterations
2. **Memory Usage**: Growing cognitive memories table
3. **Tool Selection**: Should become less random over time
4. **Success Rate**: Track via tool performance metrics

### **Database Monitoring**

```bash
# Connect to PostgreSQL
docker exec -it postgres_standalone psql -U postgres -d autonomous_agent

# Check cognitive memories
SELECT COUNT(*) FROM cognitive_memories;
SELECT action, COUNT(*) FROM cognitive_memories GROUP BY action;

# Check recent memories
SELECT id, action, timestamp FROM cognitive_memories ORDER BY timestamp DESC LIMIT 5;
```

### **API Monitoring**

```bash
# Health check
curl http://localhost:8100/api/health

# Cognitive status
curl http://localhost:8100/api/cognitive/status

# Both should return 200 OK
```

## 🔍 **Troubleshooting**

### **Issue**: Container won't start
```bash
# Check logs
docker logs autogen_cognitive_standalone

# Common solutions:
# 1. Ensure PostgreSQL is running first
# 2. Check DATABASE_URL environment variable
# 3. Verify image build completed successfully
```

### **Issue**: No cognitive enhancement
```bash
# Check environment variables
docker exec autogen_cognitive_standalone env | grep COGNITIVE

# Should show:
# USE_COGNITIVE_ENHANCEMENT=true
# STANDALONE_MODE=true
```

### **Issue**: Database connection failed
```bash
# Check PostgreSQL health
docker logs postgres_standalone

# Test connection
docker exec postgres_standalone pg_isready -U postgres
```

## 🚧 **What's NOT Included in Standalone Mode**

- ❌ **NeuroSync VTuber Integration**: No external avatar communication
- ❌ **Redis SCB Bridge**: State changes logged locally only
- ❌ **External Tool APIs**: Only internal cognitive tools
- ❌ **Network Dependencies**: Self-contained system

## ✅ **What IS Included**

- ✅ **Cognitive Memory Manager**: Full PostgreSQL integration
- ✅ **Decision Engine**: Complete learning and optimization
- ✅ **Tool Performance Tracking**: Historical analysis
- ✅ **Memory Consolidation**: Knowledge graph building (local)
- ✅ **Health Monitoring**: API status endpoints
- ✅ **Optional Cognee**: Knowledge graph enhancement

---

**🎉 Perfect for testing core cognitive functionality before adding external integrations!** 