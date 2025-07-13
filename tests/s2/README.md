# Phase 2: S2 Performance & Tool Utilization Testing

**Phase 2** focuses on comprehensive testing of the S2 (AutoGen Teams) system, measuring multi-agent team processing performance and validating tool usage alignment.

## 🎯 Phase 2 Objectives

| Goal | Target | Success Metric |
|------|--------|---------------|
| Fast multi-agent reasoning | Trader/Educator/Streamer teams | **< 2.0s** P95 total processing |
| Correct tool usage | AutoGen `tool_call` events vs. planned tools | **100%** alignment |
| Comprehensive logging | Tool decisions & durations | Logs in `/logs/s2/` |

## 📁 Directory Structure

```
logs/s2/
├── raw/                    # Raw container logs and debug output
└── summaries/              # JSON/CSV metrics per test run

tests/s2/
├── perf/
│   └── test_s2_latency.py  # Team processing latency tests
├── tools/
│   └── test_tool_usage.py  # Tool usage verification tests
└── README.md               # This documentation
```

## 🚀 Quick Start

### Prerequisites

1. **S2 AutoGen container running**:
   ```bash
   docker ps | grep autogen_s2
   ```

2. **S2 API accessible**:
   ```bash
   curl http://localhost:8200/health
   ```

3. **Docker log access**:
   ```bash
   docker logs autogen_s2 --tail 10
   ```

### Run Team Latency Tests

```bash
# Basic latency test for all teams
cd /path/to/autonomy
python tests/s2/perf/test_s2_latency.py

# Test specific teams with custom parameters
python tests/s2/perf/test_s2_latency.py \
  --teams trader,educator \
  --requests 10 \
  --threshold 2.5

# Assert performance targets (CI/CD ready)
python tests/s2/perf/test_s2_latency.py \
  --teams trader,educator,streamer \
  --requests 5 \
  --assert
```

### Run Tool Usage Tests

```bash
# Basic tool usage verification
python tests/s2/tools/test_tool_usage.py

# Test specific teams with verification
python tests/s2/tools/test_tool_usage.py \
  --teams trader,streamer \
  --scenarios 5 \
  --verify-alignment

# Generate comprehensive tool report
python tests/s2/tools/test_tool_usage.py \
  --teams trader,educator,streamer \
  --scenarios 3 \
  --output detailed_tool_report.json
```

## 📊 Performance Targets

### Team Processing Latency
- **P95 Total Processing**: < 2.0 seconds
- **P95 Team Processing**: < 1.5 seconds  
- **Success Rate**: > 95%
- **Tool Completion Rate**: > 90%

### Tool Usage Alignment
- **Overall Alignment Score**: > 80%
- **Tool Coverage**: > 60% of expected tools per team
- **Tool Success Rate**: > 90%
- **Perfect Alignment Rate**: > 50% of scenarios

## 🔧 S2 System Components

### AutoGen Teams

**Trader Team**:
- **Agents**: Coordinator, Analyst, Strategist, Memory
- **Expected Tools**: market_data, trading_analysis, risk_assessment, technical_indicators
- **Performance Target**: < 2.0s P95 for market analysis tasks

**Educator Team**:
- **Agents**: Coordinator, Teacher, Curriculum Designer, Memory  
- **Expected Tools**: educational_content, curriculum_design, assessment_creation, lesson_planning
- **Performance Target**: < 2.0s P95 for educational content generation

**Streamer Team**:
- **Agents**: Coordinator, Content Creator, Engagement Specialist, Memory
- **Expected Tools**: content_creation, community_management, streaming_analytics, audience_engagement
- **Performance Target**: < 2.0s P95 for content strategy tasks

### Tool Categories

**System Tools** (All Teams):
- system_status, communication, utility

**Trading Tools** (Trader Team):
- market_data, trading_analysis, risk_assessment, technical_indicators, portfolio_analysis

**Education Tools** (Educator Team):
- educational_content, curriculum_design, assessment_creation, learning_analytics

**Content Tools** (Streamer Team):
- content_creation, community_management, streaming_analytics, social_media

## 📝 Timestamp Logging

Phase 2 implements comprehensive timestamp logging for S2 team processing:

### S2 Processing Events
```
S2_RECEIVED {stimuli_id} {timestamp}           # Stimuli received by queue
S2_PROCESSING_START {stimuli_id} {timestamp}   # Processing begins
S2_TEAM_START {stimuli_id} {timestamp}         # Team processing starts
S2_TOOLS_AVAILABLE {stimuli_id} {timestamp}    # Tools made available
S2_TOOL_INVOKED {stimuli_id} {tool_name} {timestamp}    # Tool invoked
S2_TOOL_COMPLETED {stimuli_id} {tool_name} {timestamp}  # Tool completed
S2_INSIGHTS_EXTRACTED {stimuli_id} {timestamp} # Insights extracted
S2_TEAM_COMPLETE {stimuli_id} {timestamp}      # Team processing complete
S2_PROCESSING_COMPLETE {stimuli_id} {timestamp} # Overall processing complete
```

### Example Log Output
```
2025-01-13T15:30:00.123 - INFO - S2_RECEIVED test_12345 2025-01-13T15:30:00.123456
2025-01-13T15:30:00.125 - INFO - S2_PROCESSING_START test_12345 2025-01-13T15:30:00.125456
2025-01-13T15:30:00.127 - INFO - S2_TEAM_START test_12345 2025-01-13T15:30:00.127456
2025-01-13T15:30:00.130 - INFO - S2_TOOLS_AVAILABLE test_12345 2025-01-13T15:30:00.130456
2025-01-13T15:30:00.135 - INFO - S2_TOOL_INVOKED test_12345 market_data 2025-01-13T15:30:00.135456
2025-01-13T15:30:00.345 - INFO - S2_TOOL_COMPLETED test_12345 market_data 2025-01-13T15:30:00.345456
2025-01-13T15:30:01.200 - INFO - S2_INSIGHTS_EXTRACTED test_12345 2025-01-13T15:30:01.200456
2025-01-13T15:30:01.205 - INFO - S2_TEAM_COMPLETE test_12345 2025-01-13T15:30:01.205456
2025-01-13T15:30:01.210 - INFO - S2_PROCESSING_COMPLETE test_12345 2025-01-13T15:30:01.210456
```

## 🧪 Test Scenarios

### Team Latency Test Scenarios

**Trader Team Scenarios**:
1. Bitcoin market analysis and trading opportunities
2. Technical indicators evaluation for Ethereum
3. Risk-reward assessment for swing trading
4. Fed policy impact on cryptocurrency markets

**Educator Team Scenarios**:
1. Quantum computing concepts for undergraduates
2. Python programming lesson plan creation
3. Machine learning assessment design
4. Sustainable energy educational content

**Streamer Team Scenarios**:
1. Gaming livestream content ideas
2. Community engagement event planning
3. Interactive variety show segments
4. Audience growth strategy development

### Tool Usage Test Scenarios

**Trader Tool Scenarios**:
- **Crypto Analysis**: Expected tools: market_data, trading_analysis, technical_indicators
- **Risk Assessment**: Expected tools: risk_assessment, portfolio_analysis, market_data
- **Technical Analysis**: Expected tools: technical_indicators, market_data

**Educator Tool Scenarios**:
- **Lesson Creation**: Expected tools: educational_content, curriculum_design, lesson_planning
- **Assessment Design**: Expected tools: assessment_creation, educational_content
- **Curriculum Design**: Expected tools: curriculum_design, learning_analytics, educational_content

**Streamer Tool Scenarios**:
- **Content Generation**: Expected tools: content_creation, audience_engagement
- **Performance Analysis**: Expected tools: streaming_analytics, performance_tracking, community_management
- **Community Growth**: Expected tools: community_management, audience_engagement, social_media

## 📈 Test Results Analysis

### Latency Metrics

**Key Performance Indicators**:
- **Total Processing Time**: S2_RECEIVED → S2_PROCESSING_COMPLETE
- **Team Processing Time**: S2_TEAM_START → S2_TEAM_COMPLETE  
- **Processing Overhead**: S2_RECEIVED → S2_TEAM_START
- **Tool Processing Time**: S2_TOOL_INVOKED → S2_TOOL_COMPLETED (per tool)
- **Insights Extraction**: S2_INSIGHTS_EXTRACTED → S2_TEAM_COMPLETE

### Tool Alignment Metrics

**Alignment Scores**:
- **Coverage Score**: Expected tools invoked / Total expected tools
- **Precision Score**: Expected tools invoked / Total tools invoked
- **Alignment Score**: (Coverage + Precision) / 2
- **Tool Success Rate**: Tools completed / Tools invoked

### Statistical Analysis

Tests automatically calculate:
- Mean, median, P95, P99 latencies
- Success rates and error rates
- Per-team performance breakdown
- Tool usage frequency analysis
- Perfect alignment achievement rates

## 🔍 Troubleshooting

### Common Issues

**High Latency (P95 > 2.0s)**:
1. Check AutoGen team initialization time
2. Verify LLM model performance (Ollama/LLaMA)
3. Analyze tool execution overhead
4. Check container resource constraints

**Low Tool Alignment**:
1. Verify tool registration and discovery
2. Check team-specific tool availability
3. Analyze scenario relevance to expected tools
4. Review tool invocation patterns in logs

**Missing Tool Events**:
1. Verify timestamp logging is enabled
2. Check container log verbosity level
3. Ensure Docker log retention policies
4. Validate log parsing regex patterns

### Debug Commands

```bash
# Check S2 container health
docker logs autogen_s2 --tail 50 | grep -E "(S2_|ERROR|WARNING)"

# Verify API endpoints
curl -s http://localhost:8200/health | jq .
curl -s http://localhost:8200/api/stimuli/tools | jq .

# Monitor real-time processing
docker logs autogen_s2 -f | grep "S2_"

# Check team initialization
docker logs autogen_s2 | grep -E "(TEAM|Creating|✅|❌)"
```

### Performance Optimization

**Team Processing**:
- Reduce AutoGen max_rounds if conversations are too long
- Optimize tool timeout values
- Use more efficient LLM models
- Implement tool result caching

**Tool Usage**:
- Optimize tool parameter validation
- Implement async tool execution where possible
- Add tool result memoization
- Reduce tool initialization overhead

## 🔧 Integration with CI/CD

### GitHub Actions Example

```yaml
name: S2 Performance Tests
on: [push, pull_request]

jobs:
  s2-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start S2 System
        run: docker-compose up -d autogen_s2
        
      - name: Wait for S2 Ready
        run: timeout 60 bash -c 'until curl -f http://localhost:8200/health; do sleep 2; done'
        
      - name: Run S2 Latency Tests
        run: |
          python tests/s2/perf/test_s2_latency.py \
            --teams trader,educator,streamer \
            --requests 3 \
            --threshold 2.5 \
            --assert
            
      - name: Run Tool Usage Tests
        run: |
          python tests/s2/tools/test_tool_usage.py \
            --teams trader,educator,streamer \
            --scenarios 2 \
            --verify-alignment
            
      - name: Archive Test Results
        uses: actions/upload-artifact@v3
        with:
          name: s2-test-results
          path: logs/s2/summaries/
```

### Performance Budgets

```json
{
  "s2_performance_budgets": {
    "total_processing_p95": "2.0s",
    "team_processing_p95": "1.5s", 
    "success_rate": "95%",
    "tool_completion_rate": "90%",
    "tool_alignment_score": "80%",
    "tool_coverage": "60%"
  }
}
```

## 📚 Implementation Details

### Code Modifications

**Added Timestamp Logging**:
1. `simplified_queue_consumer.py`: S2_RECEIVED, S2_PROCESSING_START/COMPLETE
2. `simplified_autogen_team.py`: S2_TEAM_START/COMPLETE, S2_TOOLS_AVAILABLE, S2_INSIGHTS_EXTRACTED
3. `base_tool.py`: S2_TOOL_INVOKED/COMPLETED for all tool executions

**Test Infrastructure**:
1. `test_s2_latency.py`: 500+ lines comprehensive latency testing
2. `test_tool_usage.py`: 600+ lines tool usage verification
3. Docker log parsing with regex pattern matching
4. Statistical analysis and performance assertions

### Dependencies

**Python Packages**:
- `requests`: API communication
- `asyncio`: Async test execution  
- `subprocess`: Docker log access
- `statistics`: Performance calculations
- `re`: Log parsing patterns

**System Requirements**:
- Docker with container log access
- S2 AutoGen container running
- Network access to S2 API (port 8200)
- Sufficient disk space for log storage

## 🎓 Usage Examples

### Development Workflow

```bash
# 1. Make S2 system changes
# 2. Rebuild container if needed
docker-compose build --no-cache autogen_s2

# 3. Restart services
docker-compose up -d autogen_s2

# 4. Run quick performance check
python tests/s2/perf/test_s2_latency.py --teams trader --requests 3

# 5. Run tool alignment check
python tests/s2/tools/test_tool_usage.py --teams trader --scenarios 2

# 6. Review results
ls -la logs/s2/summaries/
```

### Advanced Usage

```bash
# Comprehensive team comparison
python tests/s2/perf/test_s2_latency.py \
  --teams trader,educator,streamer \
  --requests 10 \
  --threshold 2.0 \
  --output comprehensive_s2_performance.json

# Tool usage deep dive
python tests/s2/tools/test_tool_usage.py \
  --teams trader,educator,streamer \
  --scenarios 5 \
  --verify-alignment \
  --output detailed_tool_analysis.json

# Custom container testing
python tests/s2/perf/test_s2_latency.py \
  --container my_custom_s2 \
  --api-url http://localhost:8300 \
  --threshold 1.5 \
  --assert
```

---

**Phase 2 Status**: ✅ **Implementation Complete**

- ✅ S2 timestamp logging implemented
- ✅ Team latency testing framework
- ✅ Tool usage verification system
- ✅ Performance assertion capabilities
- ✅ Comprehensive documentation

**Next Phase**: Phase 3 - SCB (Shared Cognitive Blackboard) Redesign & Validation 