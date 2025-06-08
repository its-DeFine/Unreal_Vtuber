# Multi-Platform Chat Aggregator System Design

## Overview

The Chat Aggregator System is a unified platform that enables our VTuber to intelligently monitor and respond to chat messages from multiple platforms (Twitch, YouTube, Discord) simultaneously. The system integrates seamlessly with the existing Autoliza autonomous agent to provide coordinated, human-like interactions.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CHAT AGGREGATOR SYSTEM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │   Twitch    │    │   YouTube   │    │   Discord   │             │
│  │   Adapter   │    │   Adapter   │    │   Adapter   │             │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│         │                  │                  │                     │
│         └─────────┬────────┴─────────┬────────┘                     │
│                   │                  │                              │
│                   ▼                  ▼                              │
│         ┌─────────────────────────────────────────┐                 │
│         │        Message Ingestion Queue          │                 │
│         │     (Redis Priority Queue)              │                 │
│         └─────────────────┬───────────────────────┘                 │
│                           │                                         │
│                           ▼                                         │
│         ┌─────────────────────────────────────────┐                 │
│         │        Salience Engine                  │                 │
│         │  • Content Analysis                     │                 │
│         │  • Authority Scoring                    │                 │
│         │  • Contextual Relevance                 │                 │
│         │  • Temporal Factors                     │                 │
│         └─────────────────┬───────────────────────┘                 │
│                           │                                         │
│                           ▼                                         │
│         ┌─────────────────────────────────────────┐                 │
│         │     Attention Management System         │                 │
│         │  • State Machine (Focus/Casual/etc)     │                 │
│         │  • Interrupt Handling                   │                 │
│         │  • Response Timing                      │                 │
│         └─────────────────┬───────────────────────┘                 │
│                           │                                         │
│                           ▼                                         │
│         ┌─────────────────────────────────────────┐                 │
│         │     Response Generation Pipeline        │                 │
│         │  • Context Assembly                     │                 │
│         │  • VTuber Response Generation           │                 │
│         │  • Platform Formatting                  │                 │
│         └─────────────────┬───────────────────────┘                 │
│                           │                                         │
│                           ▼                                         │
│         ┌─────────────────────────────────────────┐                 │
│         │      Autoliza Integration Layer         │                 │
│         │  • Context Updates                      │                 │
│         │  • Strategic Coordination               │                 │
│         │  • Autonomous Feedback                  │                 │
│         └─────────────────┬───────────────────────┘                 │
│                           │                                         │
│                           ▼                                         │
│         ┌─────────────────────────────────────────┐                 │
│         │       VTuber System Integration         │                 │
│         │  • Text Processing                      │                 │
│         │  • SCB Updates                          │                 │
│         │  • Response Delivery                    │                 │
│         └─────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Platform Adapters

Each platform adapter implements the `PlatformAdapter` interface and handles:

- **Connection Management**: WebSocket/API connections
- **Message Ingestion**: Real-time message capture
- **Authentication**: Platform-specific auth handling
- **Rate Limiting**: Respect platform API limits
- **Message Formatting**: Platform-specific response formatting

```typescript
interface PlatformAdapter {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  sendMessage(message: string, channel: string): Promise<void>;
  onMessage(callback: (message: ChatMessage) => void): void;
  getChannelInfo(): Promise<ChannelInfo>;
  isConnected(): boolean;
  getPlatformName(): string;
}
```

#### Twitch Adapter
- Uses Twitch IRC (TMI.js) for chat connections
- Handles badges, emotes, subscriber status
- Supports moderation commands
- Rate limit: 20 messages/30 seconds for verified bots

#### YouTube Adapter  
- Uses YouTube Live Chat API
- Polls for new messages (1-5 second intervals)
- Handles Super Chat, membership status
- Rate limit: 1000 requests/day for live chat

#### Discord Adapter
- Enhances existing Discord plugin
- WebSocket gateway for real-time messages
- Handles threads, reactions, embeds
- Rate limit: 5 messages/5 seconds per channel

### 2. Message Ingestion & Queue Management

```typescript
interface MessageQueue {
  enqueue(message: ChatMessage, priority: number): Promise<void>;
  dequeue(): Promise<ChatMessage | null>;
  peek(): Promise<ChatMessage | null>;
  size(): Promise<number>;
  clear(): Promise<void>;
}
```

**Implementation**: Redis-based priority queue with persistence
- **Priority Levels**: Based on salience scores (CRITICAL > HIGH > MEDIUM > LOW)
- **Batching**: Process messages in batches for efficiency
- **Persistence**: Survive system restarts
- **Monitoring**: Queue depth and processing metrics

### 3. Salience Engine

Multi-dimensional scoring system that evaluates messages across four factors:

#### Content Analysis (40% weight)
```typescript
private analyzeContent(message: ChatMessage): number {
  // VTuber mentions/questions: +0.4
  // Emotional content: +0.2 (max)
  // Technical topics: +0.3 (max)  
  // Creative suggestions: +0.25
}
```

#### Authority Analysis (25% weight)
```typescript
private analyzeAuthority(message: ChatMessage): number {
  // Subscribers: +0.15
  // Moderators: +0.2
  // Long-term followers: +0.1
  // First-time chatters: +0.05
  // Platform badges: +0.1
}
```

#### Contextual Relevance (20% weight)
```typescript
private analyzeRelevance(message: ChatMessage, context: ChatContextUpdate): number {
  // Current topic match: +0.2
  // Recent context reference: +0.15
  // Conversation building: +0.1
}
```

#### Temporal Factors (15% weight)
```typescript
private analyzeTemporalFactors(message: ChatMessage, context: ChatContextUpdate): number {
  // Message recency: 0.15 → 0.0 over 5 minutes
  // Question urgency: +0.1
  // Chat velocity boost: +0.1 (dynamic)
}
```

### 4. Attention Management System

Simulates human-like chat monitoring patterns through state machine:

```typescript
enum AttentionState {
  FOCUSED_INTERACTION = 'focused_interaction',    // 40% of time
  CASUAL_MONITORING = 'casual_monitoring',        // 35% of time  
  DEEP_FOCUS = 'deep_focus',                     // 20% of time
  BREAK_TRANSITION = 'break_transition'          // 5% of time
}
```

**State Transitions**:
- **Time-based**: Automatic transitions every 2-10 minutes
- **Event-driven**: High salience messages trigger state changes
- **Context-aware**: Platform activity levels influence transitions

**Response Patterns**:
- **Focused**: 80% response rate, detailed answers
- **Casual**: 40% response rate, brief acknowledgments  
- **Deep Focus**: 10% response rate, only critical messages
- **Break**: 60% response rate, catch-up mode

### 5. Response Generation Pipeline

```typescript
interface ResponsePipeline {
  generateResponse(
    message: ChatMessage,
    context: ChatContextUpdate,
    autonomousGuidance?: AutonomousContext
  ): Promise<VTuberResponse>;
  
  formatForPlatform(
    response: VTuberResponse,
    platform: string
  ): Promise<PlatformMessage>;
}
```

**Processing Steps**:
1. **Context Assembly**: Gather relevant chat history and platform context
2. **Autoliza Consultation**: Get strategic guidance from autonomous agent
3. **Response Generation**: Create contextually appropriate response
4. **Platform Formatting**: Apply platform-specific formatting (emotes, length limits)
5. **Delivery**: Send through appropriate platform adapter

### 6. Autoliza Integration Layer

Bidirectional communication with the autonomous agent:

**Chat → Autoliza Pipeline**:
```typescript
interface ChatContextUpdate {
  platforms: {
    [platform: string]: {
      activeUsers: number;
      averageSalience: number;
      topTopics: string[];
      sentiment: 'positive' | 'neutral' | 'negative';
      lastInteraction: number;
    };
  };
  globalContext: {
    totalMessages: number;
    responseRate: number;
    engagementTrend: 'increasing' | 'stable' | 'decreasing';
    recommendedAction: string;
  };
}
```

**Autoliza → Chat Pipeline**:
- Strategic conversation topics
- Personality adjustments based on audience
- SCB space updates triggered by chat sentiment
- Autonomous conversation starters during quiet periods

## Data Flow

### 1. Message Ingestion Flow
```
Platform → Adapter → Message Queue → Salience Engine → Attention Manager
```

### 2. Response Generation Flow
```
Message → Context Assembly → Autoliza Consultation → Response Generation → Platform Formatting → Delivery
```

### 3. Context Update Flow
```
Multiple Messages → Context Aggregation → Autoliza Update → Strategic Feedback → Attention Adjustment
```

## Database Schema

### Chat Messages Table
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    channel VARCHAR(100) NOT NULL,
    author_id VARCHAR(100) NOT NULL,
    author_username VARCHAR(100) NOT NULL,
    author_display_name VARCHAR(100),
    content TEXT NOT NULL,
    salience_score FLOAT NOT NULL,
    salience_breakdown JSONB NOT NULL,
    attention_state VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    response_id UUID REFERENCES chat_responses(id)
);

CREATE INDEX idx_chat_messages_salience ON chat_messages(salience_score DESC, created_at DESC);
CREATE INDEX idx_chat_messages_platform ON chat_messages(platform, created_at DESC);
CREATE INDEX idx_chat_messages_attention ON chat_messages(attention_state, created_at DESC);
```

### Chat Responses Table
```sql
CREATE TABLE chat_responses (
    id UUID PRIMARY KEY,
    original_message_id UUID REFERENCES chat_messages(id),
    response_text TEXT NOT NULL,
    response_type VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    attention_state VARCHAR(50),
    generation_time_ms INTEGER,
    autonomous_context JSONB,
    sent_at TIMESTAMP,
    engagement_metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_responses_platform ON chat_responses(platform, sent_at DESC);
CREATE INDEX idx_chat_responses_attention ON chat_responses(attention_state, sent_at DESC);
```

### Platform Metrics Table
```sql
CREATE TABLE platform_metrics (
    id UUID PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    value FLOAT NOT NULL,
    metadata JSONB,
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_platform_metrics_type ON platform_metrics(platform, metric_type, recorded_at DESC);
```

## Performance Considerations

### Scalability Targets
- **Message Throughput**: 1000+ messages/minute across all platforms
- **Response Latency**: <2 seconds for high-priority messages
- **System Resources**: <1GB RAM, <20% CPU during peak load
- **Database**: <100ms query times for salience calculations

### Optimization Strategies
- **Redis Caching**: Cache frequently accessed data (user profiles, recent contexts)
- **Batch Processing**: Process multiple messages together when possible
- **Connection Pooling**: Reuse database and API connections
- **Async Processing**: Non-blocking message handling throughout pipeline

### Monitoring & Alerting
- **Queue Metrics**: Depth, processing rate, backlog alerts
- **Response Metrics**: Generation time, delivery success rate
- **Platform Health**: Connection status, API rate limit usage
- **Salience Accuracy**: Manual scoring correlation tracking

## Configuration Management

### Environment Variables
```env
# Platform Credentials
TWITCH_CLIENT_ID=your_client_id
TWITCH_CLIENT_SECRET=your_secret
YOUTUBE_API_KEY=your_api_key
DISCORD_BOT_TOKEN=your_token

# System Configuration
CHAT_AGGREGATOR_ENABLED=true
MAX_QUEUE_SIZE=10000
SALIENCE_CALCULATION_TIMEOUT=500
ATTENTION_CYCLE_DURATION=300000

# Integration
AUTOLIZA_WEBHOOK_URL=http://autonomous-starter:3000/chat-context
VTUBER_ENDPOINT_URL=http://neurosync:5001/process_text
```

### Platform-Specific Settings
```typescript
interface PlatformConfig {
  name: string;
  enabled: boolean;
  credentials: { [key: string]: string };
  settings: {
    maxMessagesPerMinute: number;
    responseCooldown: number;
    enableModeration: boolean;
    allowedChannels?: string[];
    bannedUsers?: string[];
  };
}
```

## Error Handling & Recovery

### Platform Connection Failures
- **Automatic Reconnection**: Exponential backoff with max retry limits
- **Graceful Degradation**: Continue with available platforms
- **Alerting**: Notify operators of persistent connection issues

### Message Processing Failures
- **Dead Letter Queue**: Store failed messages for manual review
- **Retry Logic**: Automatic retry for transient failures
- **Fallback Responses**: Generic responses when generation fails

### Database Failures
- **Connection Pooling**: Automatic connection recovery
- **Graceful Degradation**: Continue with reduced functionality
- **Data Backup**: Regular backups of chat history and metrics

## Testing Strategy

### Unit Tests
- Salience engine accuracy with various message types
- Platform adapter connection and message handling
- Attention state transitions and timing
- Response generation with different contexts

### Integration Tests
- End-to-end message flow from platform to VTuber
- Autoliza integration and context sharing
- Database operations under load
- Multiple platform simultaneous operation

### Performance Tests
- Message throughput under various loads
- Response latency distribution
- Memory usage over extended periods
- Database query performance

## Deployment & Operations

### Docker Container Architecture
```yaml
services:
  chat-aggregator:
    image: vtuber/chat-aggregator:latest
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
    depends_on:
      - postgres
      - redis
      - autonomous-starter
      - neurosync
```

### Monitoring Dashboard
- Real-time message flow visualization
- Salience score distribution graphs
- Attention state timeline
- Platform health indicators
- Response quality metrics

### Operational Procedures
- **Daily Health Checks**: Platform connections, message processing
- **Weekly Performance Review**: Response quality, engagement trends
- **Monthly Configuration Updates**: Salience tuning, platform settings
- **Incident Response**: Automated alerting and escalation procedures

---

This design document provides the foundation for implementing a sophisticated, production-ready multi-platform chat aggregation system that seamlessly integrates with our existing VTuber infrastructure while providing intelligent, human-like interaction capabilities. 