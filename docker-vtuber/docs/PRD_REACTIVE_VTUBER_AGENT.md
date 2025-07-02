# Product Requirements Document: Reactive VTuber Agent System

## Executive Summary

The Reactive VTuber Agent System is a streamlined, character-driven virtual avatar that responds intelligently to external inputs while maintaining consistent personality and contextual awareness. The system prioritizes simplicity, extensibility, and high-quality interactions over complex multi-agent architectures.

## Vision

Create a state-of-the-art reactive VTuber system that can adapt to various use cases (secretary, teacher, entertainer) through character configuration files, while maintaining engaging, non-repetitive interactions through intelligent context management.

## Core Principles

1. **Simplicity First**: Focus on LLM-to-Face pipeline with minimal complexity
2. **Character-Driven**: All behavior stems from well-defined character profiles
3. **Context-Aware**: Leverage SCB (Shared Contextual Bridge) for memory and context
4. **Reactive Intelligence**: Respond appropriately to external inputs and events
5. **Non-Repetitive**: Maintain conversation history to avoid boring, repeated responses

## System Architecture

### 1. Character Configuration System

#### Character Profile Structure
```yaml
character:
  id: "secretary_ai"
  name: "Ava"
  role: "Executive Assistant"
  
  personality:
    traits:
      - professional
      - efficient
      - proactive
      - friendly
    communication_style: "formal but approachable"
    emotional_range: "calm and supportive"
  
  domain_expertise:
    - calendar management
    - email prioritization
    - meeting coordination
    - task organization
  
  response_patterns:
    greeting: "Good {time_of_day}, how may I assist you today?"
    email_notification: "You have a new {priority} email from {sender} regarding {subject}"
    meeting_reminder: "Your {meeting_type} with {attendees} starts in {time}"
  
  behavioral_rules:
    - "Always prioritize urgent matters"
    - "Summarize long emails to key points"
    - "Proactively suggest time optimizations"
    - "Maintain professional boundaries"
  
  memory_preferences:
    scb_context_lines: 50
    conversation_history: 100
    priority_topics:
      - upcoming meetings
      - pending tasks
      - important contacts
```

#### Character Manager Features
- Hot-reload character profiles without restart
- Character switching via API
- Template library for common roles
- Character state persistence

### 2. Context Management (SCB Integration)

#### Memory Architecture
```
┌─────────────────────────────────┐
│     Character Profile           │
├─────────────────────────────────┤
│     SCB Context (N lines)       │
├─────────────────────────────────┤
│   Conversation History          │
├─────────────────────────────────┤
│    External Input Queue         │
└─────────────────────────────────┘
                 │
                 ▼
           LLM Processing
                 │
                 ▼
         Response Generation
```

#### SCB Configuration
- Configurable context window (lines from SCB)
- Topic-based filtering
- Relevance scoring
- Time-decay for old memories

### 3. External Input System

#### Input Sources
1. **Direct API Calls**
   - REST endpoints for commands
   - WebSocket for real-time events
   - Structured input format

2. **Event Subscriptions**
   - Email notifications
   - Calendar events
   - System alerts
   - Custom webhooks

3. **Integration Adapters**
   - Gmail API adapter
   - Calendar systems
   - Task management tools
   - Custom data sources

#### Input Processing Pipeline
```
External Event → Input Adapter → Event Queue → Context Builder → LLM → Response
```

### 4. Response Generation

#### LLM Pipeline
1. **Context Assembly**
   - Character profile
   - SCB context (filtered)
   - Recent conversation
   - Current external input
   
2. **Prompt Engineering**
   ```
   Character: {profile}
   Context: {scb_lines}
   History: {recent_conversations}
   Current Input: {external_event}
   
   Generate appropriate response following character guidelines.
   Avoid repetition of these recent responses: {recent_responses}
   ```

3. **Response Validation**
   - Character consistency check
   - Repetition detection
   - Length optimization
   - Emotion/tone validation

#### Anti-Repetition Strategies
- Response history tracking
- Semantic similarity detection
- Topic variation enforcement
- Dynamic vocabulary usage

### 5. Use Case Examples

#### Secretary VTuber
```python
# Configuration
character = "secretary_ai"
external_inputs = [
    EmailMonitor(gmail_api_key),
    CalendarMonitor(calendar_api),
    TaskMonitor(todoist_api)
]

# Example interaction
Input: New email from CEO about quarterly review
Response: "You have an important email from the CEO regarding the quarterly review. 
          The main points are: 1) Review scheduled for Friday 2PM, 
          2) Please prepare sales figures, 3) Focus on Q3 performance. 
          Would you like me to block time for preparation?"
```

#### Teacher VTuber
```python
# Configuration  
character = "teacher_ai"
external_inputs = [
    StudentProgressMonitor(),
    QuizResultsMonitor(),
    LearningResourceMonitor()
]

# Example interaction
Input: Student answered incorrectly about photosynthesis
Response: "I see you're having trouble with photosynthesis. Let's break it down: 
          Plants use sunlight to convert CO2 and water into glucose and oxygen. 
          Can you tell me what role chlorophyll plays in this process?"
```

### 6. API Specification

#### Character Management
```
POST   /character/load
PUT    /character/update
GET    /character/current
GET    /character/list
DELETE /character/unload
```

#### External Input
```
POST   /input/event
POST   /input/subscribe
DELETE /input/unsubscribe
GET    /input/sources
```

#### Response Control
```
POST   /response/generate
GET    /response/history
PUT    /response/settings
```

#### SCB Integration
```
GET    /context/current
PUT    /context/settings
POST   /context/clear
```

## Implementation Roadmap

### Phase 1: Core System (Week 1)
- [ ] Character configuration loader
- [ ] Basic LLM-to-Face pipeline
- [ ] Simple external input API
- [ ] Response generation with character profile

### Phase 2: Context Integration (Week 2)
- [ ] SCB integration
- [ ] Conversation history management
- [ ] Anti-repetition system
- [ ] Context filtering and relevance

### Phase 3: External Adapters (Week 3)
- [ ] Email adapter (Gmail)
- [ ] Calendar adapter
- [ ] WebSocket event system
- [ ] Custom webhook support

### Phase 4: Polish & Optimization (Week 4)
- [ ] Performance optimization
- [ ] Character template library
- [ ] Advanced prompt engineering
- [ ] Comprehensive testing

## Success Metrics

1. **Response Quality**
   - Character consistency: >95%
   - Repetition rate: <5%
   - Response relevance: >90%

2. **Performance**
   - Response latency: <2s
   - Context assembly: <500ms
   - Character switching: <1s

3. **Reliability**
   - Uptime: 99.9%
   - Error recovery: Automatic
   - Memory efficiency: <500MB

## Technical Requirements

### Dependencies
- Python 3.10+
- LangChain or similar LLM framework
- FastAPI for API endpoints
- Redis for queue management
- PostgreSQL for conversation history

### Hardware
- CPU: 4+ cores
- RAM: 8GB minimum
- GPU: Optional (for local LLM)
- Storage: 50GB for logs/history

## Security Considerations

1. **API Authentication**
   - JWT tokens for API access
   - API key management
   - Rate limiting

2. **Data Privacy**
   - Encrypted storage for sensitive data
   - Configurable data retention
   - User consent management

3. **Input Validation**
   - Sanitize external inputs
   - Prevent prompt injection
   - Content filtering options

## Future Enhancements

1. **Multi-language Support**
   - Character profiles in multiple languages
   - Real-time translation
   - Cultural adaptation

2. **Advanced Analytics**
   - Interaction analytics
   - Character performance metrics
   - User satisfaction tracking

3. **Plugin System**
   - Custom input adapters
   - Response processors
   - Character behavior extensions

## Conclusion

The Reactive VTuber Agent System represents a focused approach to creating intelligent, character-driven virtual avatars. By prioritizing simplicity, character consistency, and contextual awareness, we can deliver a system that provides genuine value across multiple use cases while maintaining high quality interactions. 