# GraphFlow External Stimuli System - Architecture Diagram

## System Architecture

```mermaid
graph TB
    %% External Sources
    subgraph External["External Sources"]
        Admin["Admin Console"]
        User["User Chat"]
        Social["Social Media"]
        System["System Monitors"]
    end

    %% API Layer
    subgraph API["API Layer"]
        REST["REST API<br/>/api/v1/stimuli"]
        WS["WebSocket<br/>/ws/stimuli"]
        Auth["Authentication<br/>Middleware"]
    end

    %% Core Gateway
    subgraph Gateway["Gateway Agent"]
        GW["GraphFlow<br/>Gateway Agent"]
        FM["Flow Managers"]
        MC["Metrics Collector"]
    end

    %% Processing Pipeline
    subgraph Pipeline["Processing Pipeline"]
        Cat["Categorizer Node<br/>• LLM Analysis<br/>• Pattern Matching"]
        Ana["Analyzer Node<br/>• Context Analysis<br/>• State Assessment"]
        Rou["Router Node<br/>• Decision Matrix<br/>• Priority Routing"]
        Exe["Executor Node<br/>• Action Execution<br/>• Result Tracking"]
    end

    %% System Integrations
    subgraph Systems["System Integrations"]
        S1["System1<br/>Avatar/VTuber<br/>• Speech<br/>• Expressions"]
        S2["System2<br/>AutoGen Agents<br/>• Multi-Agent<br/>• Complex Tasks"]
    end

    %% Data Stores
    subgraph Storage["Storage & Cache"]
        Redis["Redis<br/>• State Cache<br/>• Rate Limiting"]
        PG["PostgreSQL<br/>• Stimuli History<br/>• Analytics"]
    end

    %% Monitoring
    subgraph Monitor["Monitoring"]
        Prom["Prometheus<br/>Metrics"]
        Graf["Grafana<br/>Dashboards"]
        Logs["Structured<br/>Logging"]
    end

    %% Flow connections
    Admin --> REST
    User --> REST
    Social --> WS
    System --> REST

    REST --> Auth
    WS --> Auth
    Auth --> GW

    GW --> FM
    GW --> MC
    FM --> Cat

    Cat --> Ana
    Ana --> Rou
    Rou --> Exe

    Exe --> S1
    Exe --> S2

    GW -.-> Redis
    Exe -.-> PG

    MC --> Prom
    Prom --> Graf
    GW -.-> Logs

    %% Styling
    classDef external fill:#e1f5e1,stroke:#4caf50,stroke-width:2px
    classDef api fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef core fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef pipeline fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    classDef system fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    classDef storage fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    classDef monitor fill:#e0f2f1,stroke:#009688,stroke-width:2px

    class Admin,User,Social,System external
    class REST,WS,Auth api
    class GW,FM,MC core
    class Cat,Ana,Rou,Exe pipeline
    class S1,S2 system
    class Redis,PG storage
    class Prom,Graf,Logs monitor
```

## Data Flow Example

```mermaid
sequenceDiagram
    participant User as User Chat
    participant API as API Server
    participant Auth as Auth Middleware
    participant GW as Gateway Agent
    participant Cat as Categorizer
    participant Ana as Analyzer
    participant Rou as Router
    participant Exe as Executor
    participant S1 as System1 (Avatar)
    participant S2 as System2 (Agents)

    User->>API: POST /api/v1/stimuli/submit
    API->>Auth: Verify API Key
    Auth-->>API: Authorized
    API->>GW: Process Stimuli
    
    GW->>Cat: Categorize Stimuli
    Note over Cat: LLM Analysis<br/>Pattern Matching
    Cat-->>GW: Category: USER_INTERACTION
    
    GW->>Ana: Analyze Context
    Note over Ana: System State<br/>User Context<br/>Resources
    Ana-->>GW: Context Analysis
    
    GW->>Rou: Route Decision
    Note over Rou: Decision Matrix<br/>Priority Rules
    Rou-->>GW: Route to System1
    
    GW->>Exe: Execute Plan
    Exe->>S1: Send to Avatar
    S1-->>Exe: Response Generated
    
    Exe-->>GW: Execution Result
    GW-->>API: Processing Result
    API-->>User: Response
```

## Component Details

### 1. **API Layer**
- **REST API**: Main entry point for stimuli submission
- **WebSocket**: Real-time updates and streaming
- **Authentication**: API key-based auth with permissions

### 2. **Gateway Agent**
- **Core Orchestrator**: Manages the entire pipeline
- **Flow Managers**: Control stimuli and decision flows
- **Metrics Collector**: Tracks performance and usage

### 3. **Processing Pipeline**
- **Categorizer**: Intelligent classification using LLM
- **Analyzer**: Multi-dimensional context analysis
- **Router**: Decision-based routing logic
- **Executor**: Action execution and integration

### 4. **System Integrations**
- **System1**: Direct avatar control (speech, expressions)
- **System2**: Complex multi-agent processing

### 5. **Storage & Monitoring**
- **Redis**: Fast caching and state management
- **PostgreSQL**: Historical data and analytics
- **Prometheus/Grafana**: Real-time monitoring
- **Structured Logging**: Detailed operation tracking

## Key Features

1. **Scalability**: Horizontal scaling through stateless design
2. **Resilience**: Graceful degradation and fallback mechanisms
3. **Observability**: Comprehensive monitoring and logging
4. **Flexibility**: Extensible architecture for new integrations
5. **Performance**: Async processing and intelligent caching