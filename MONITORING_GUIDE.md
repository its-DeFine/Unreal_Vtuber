# 🔍 Enhanced Autonomous VTuber Monitoring Guide

## 📋 Overview

The enhanced monitoring system provides **structured, digestible logs** for tracking autonomous agent activities, VTuber interactions, SCB states, and memory operations in real-time.

## 🚀 Quick Start

### 1. **System Diagnosis**
```bash
./diagnose_autonomous_db.sh
```
This checks:
- ✅ Container status
- ✅ Database connectivity  
- ✅ Analytics tables
- ✅ Network connectivity
- ✅ System readiness

### 2. **Start Enhanced Monitoring**
```bash
# Monitor for 30 minutes (default)
./monitor_autonomous_system_enhanced.sh

# Monitor for specific duration
./monitor_autonomous_system_enhanced.sh 60  # 60 minutes
```

### 3. **Real-time Dashboard**
The script provides a live dashboard showing:
- 🤖 **System Status**: All container states
- 🔗 **Current SCB State**: Real-time SCB status
- 💾 **Memory Statistics**: Active/archived memory counts
- 📋 **Recent Activity**: Latest agent actions

## 📊 Log Structure

### **Structured Logs** (JSON format)
Located in: `logs/autonomous_monitoring/session_TIMESTAMP/structured/`

- `autonomous_iteration.jsonl` - Agent loop iterations
- `vtuber_stimuli.jsonl` - VTuber external inputs
- `scb_state_change.jsonl` - SCB state transitions
- `memory_operation.jsonl` - Memory operations
- `tool_execution.jsonl` - Tool usage tracking

### **Human-Readable Logs**
Located in: `logs/autonomous_monitoring/session_TIMESTAMP/structured/`

- `readable_autonomous_iteration.log`
- `readable_vtuber_stimuli.log`
- `readable_scb_state_change.log`
- `readable_memory_operation.log`

## 🎯 Event Types Tracked

### 🤖 **Autonomous Agent Iterations**
```
[2025-01-28 10:30:15] 🤖 AUTONOMOUS AGENT ITERATION #42:
   💭 Agent Message: Starting iteration 42
   🎯 Decision: analyzing_context
   🛠️  Tools Triggered:
      - updateScbAction
      - sendToVTuberAction
   🔗 SCB State: mood:focused,env:study_room
   💾 Memory Operations: active:35,archived:0
```

### 🎭 **VTuber External Stimuli**
```
[2025-01-28 10:30:20] 🎭 VTUBER RECEIVED EXTERNAL STIMULI:
   📥 Input: User asked about VR technology
   🔗 SCB State: mood:curious,env:tech_space
   📊 Context: external_stimuli
```

### 🔗 **SCB State Changes**
```
[2025-01-28 10:30:25] 🔗 SCB STATE CHANGE:
   🔄 Previous: mood:neutral,env:default
   ➡️  New: mood:excited,env:gaming_setup
   🎯 Trigger: vtuber_interaction
   📊 Details: Gaming discussion detected
```

### 💾 **Memory Operations**
```
[2025-01-28 10:30:30] 💾 MEMORY OPERATION:
   🔄 Operation: createMemory
   📊 Count: 1
   🎯 Type: autonomous
   📈 Stats: active:36,archived:0
```

## 📋 Generated Reports

### **Enhanced Summary Report**
After monitoring, you get: `ENHANCED_SUMMARY.md`

Contains:
- 📊 **Event Summary**: Count of each event type
- 🤖 **Autonomous Agent Activity**: Recent iterations
- 🎭 **VTuber Interactions**: Recent stimuli
- 🔗 **SCB State Changes**: State transitions
- 💾 **Memory Operations**: Recent operations
- 📁 **Generated Files**: All log files created

## 🔧 Troubleshooting

### **Database Issues**
```bash
# Check database status
docker ps | grep postgres

# Restart database
docker-compose restart autonomous_postgres_bridge

# Check logs
docker logs autonomous_postgres_bridge
```

### **Missing Dependencies**
```bash
# Install jq for JSON parsing
sudo apt-get install jq

# Verify installation
jq --version
```

### **Container Issues**
```bash
# Check all containers
docker ps -a

# Restart specific container
docker-compose restart autonomous_starter_s3
```

## 📊 Analytics Integration

The monitoring system integrates with the analytics tables:
- `tool_usage` - Tracks tool effectiveness
- `decision_patterns` - Analyzes decision patterns
- `context_archive` - Manages memory archiving
- `memory_lifecycle` - Tracks memory lifecycle

## 🎯 Best Practices

### **Monitoring Duration**
- **Short tests**: 5-10 minutes
- **Development**: 30-60 minutes  
- **Production**: 2-4 hours

### **Log Analysis**
1. **Start with readable logs** for quick overview
2. **Use JSON logs** for detailed analysis
3. **Check summary report** for patterns
4. **Monitor SCB state changes** for coherence

### **Performance Monitoring**
- Watch memory statistics for growth
- Monitor iteration frequency
- Track tool usage patterns
- Observe SCB state coherence

## 🚀 Advanced Usage

### **Custom Event Filtering**
Edit the monitoring script to add custom filters:
```bash
# Add custom patterns in parse_autonomous_logs()
if echo "$line" | grep -q "YOUR_PATTERN"; then
    # Custom event handling
fi
```

### **Integration with External Tools**
The JSON logs can be processed by:
- **Elasticsearch** for search
- **Grafana** for visualization
- **Custom scripts** for analysis

## 📞 Support

If you encounter issues:
1. Run `./diagnose_autonomous_db.sh`
2. Check container logs: `docker logs CONTAINER_NAME`
3. Verify database connectivity
4. Ensure all required containers are running

---

**🎯 Ready to monitor your autonomous VTuber system!** 