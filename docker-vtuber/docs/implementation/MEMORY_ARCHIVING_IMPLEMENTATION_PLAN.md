# 🗄️ Memory Archiving Implementation Plan - CRITICAL

**Priority**: P0 - BLOCKING for multi-agent deployment  
**Timeline**: Must complete before spawning multiple agents  
**Risk**: Database performance collapse without this system

---

## 🚨 Why Memory Archiving is CRITICAL

### Current Risk Assessment
- **Single agent**: 117 memories (manageable)
- **10 active agents**: 1,170+ memories per hour = **28,080 memories/day**
- **Database impact**: Query performance degrades exponentially after 10K+ memories
- **System failure**: Without archiving, system becomes unusable within 3-5 days

### Performance Thresholds
```
Memories Count    | Query Performance | System Status
0 - 1,000        | <50ms            | ✅ Optimal
1,000 - 5,000    | 50-200ms         | ⚠️ Degrading
5,000 - 10,000   | 200-500ms        | 🔶 Poor
10,000+          | >500ms           | 🔴 Critical
50,000+          | >2000ms          | 💥 Unusable
```

---

## 🏗️ Implementation Architecture

### Phase 1: Core Archiving Engine (Week 1)

```typescript
// src/memory/MemoryArchivingEngine.ts
export class MemoryArchivingEngine {
  private elizaRuntime: IAgentRuntime;
  private archivingConfig: MemoryArchivingConfig;
  private archivingInterval: NodeJS.Timeout | null = null;

  constructor(runtime: IAgentRuntime, config: MemoryArchivingConfig) {
    this.elizaRuntime = runtime;
    this.archivingConfig = config;
    
    // Add comprehensive logging
    console.log(`[MemoryArchivingEngine] Initialized for agent ${runtime.agentId}`);
    console.log(`[MemoryArchivingEngine] Config:`, {
      activeMemoryLimit: config.activeMemoryLimit,
      archiveThresholds: config.archiveThresholds,
      archivingIntervalMinutes: config.archivingIntervalMinutes
    });
  }

  async startContinuousArchiving(): Promise<void> {
    console.log(`[MemoryArchivingEngine] Starting continuous archiving for agent ${this.elizaRuntime.agentId}`);
    
    // Initial archiving run
    await this.performArchivingCycle();
    
    // Schedule periodic archiving
    this.archivingInterval = setInterval(async () => {
      try {
        await this.performArchivingCycle();
      } catch (error) {
        console.error(`[MemoryArchivingEngine] Archiving cycle failed:`, error);
        // Continue running despite errors
      }
    }, this.archivingConfig.archivingIntervalMinutes * 60 * 1000);
    
    console.log(`[MemoryArchivingEngine] Continuous archiving started with ${this.archivingConfig.archivingIntervalMinutes}min intervals`);
  }

  async performArchivingCycle(): Promise<ArchivingResult> {
    const startTime = Date.now();
    console.log(`[MemoryArchivingEngine] Starting archiving cycle for agent ${this.elizaRuntime.agentId}`);
    
    try {
      // 1. Get current memory count
      const currentMemoryCount = await this.getCurrentMemoryCount();
      console.log(`[MemoryArchivingEngine] Current memory count: ${currentMemoryCount}`);
      
      if (currentMemoryCount <= this.archivingConfig.activeMemoryLimit) {
        console.log(`[MemoryArchivingEngine] Memory count below threshold, skipping archiving`);
        return { archived: 0, skipped: true, reason: 'below_threshold' };
      }

      // 2. Identify candidates for archiving
      const candidates = await this.identifyArchiveCandidates();
      console.log(`[MemoryArchivingEngine] Found ${candidates.length} archiving candidates`);
      
      if (candidates.length === 0) {
        console.log(`[MemoryArchivingEngine] No archiving candidates found`);
        return { archived: 0, skipped: true, reason: 'no_candidates' };
      }

      // 3. Archive memories in batches
      const archiveResult = await this.archiveMemoriesBatch(candidates);
      
      const duration = Date.now() - startTime;
      console.log(`[MemoryArchivingEngine] Archiving cycle completed in ${duration}ms:`, archiveResult);
      
      return archiveResult;
    } catch (error) {
      console.error(`[MemoryArchivingEngine] Archiving cycle failed:`, error);
      throw error;
    }
  }

  private async getCurrentMemoryCount(): Promise<number> {
    // Use ElizaOS database adapter
    const memories = await this.elizaRuntime.databaseAdapter.getMemories({
      agentId: this.elizaRuntime.agentId,
      tableName: 'memories',
      count: 1 // Just get count, not actual memories
    });
    
    // Get actual count via direct query
    const result = await this.elizaRuntime.databaseAdapter.db.query(
      'SELECT COUNT(*) as count FROM memories WHERE "agentId" = $1',
      [this.elizaRuntime.agentId]
    );
    
    return parseInt(result.rows[0].count);
  }

  private async identifyArchiveCandidates(): Promise<Memory[]> {
    const { archiveThresholds } = this.archivingConfig;
    
    // Get memories that meet archiving criteria
    const query = `
      SELECT m.*, ml.access_count, ml.last_accessed, ml.importance_score
      FROM memories m
      LEFT JOIN memory_lifecycle ml ON m.id = ml.memory_id
      WHERE m."agentId" = $1
      AND (
        -- Time-based archiving
        m."createdAt" < NOW() - INTERVAL '${archiveThresholds.timeBasedHours} hours'
        OR
        -- Importance-based archiving
        COALESCE(ml.importance_score, 0.5) < $2
        OR
        -- Access-based archiving
        COALESCE(ml.last_accessed, m."createdAt") < NOW() - INTERVAL '${archiveThresholds.accessFrequency} days'
      )
      ORDER BY 
        COALESCE(ml.importance_score, 0.5) ASC,
        m."createdAt" ASC
      LIMIT $3
    `;
    
    const result = await this.elizaRuntime.databaseAdapter.db.query(query, [
      this.elizaRuntime.agentId,
      archiveThresholds.importanceScore,
      this.archivingConfig.archivingBatchSize
    ]);
    
    return result.rows.map(row => ({
      id: row.id,
      type: row.type,
      createdAt: row.createdAt,
      content: typeof row.content === 'string' ? JSON.parse(row.content) : row.content,
      agentId: row.agentId,
      roomId: row.roomId,
      metadata: row.metadata
    }));
  }

  private async archiveMemoriesBatch(memories: Memory[]): Promise<ArchivingResult> {
    console.log(`[MemoryArchivingEngine] Archiving ${memories.length} memories`);
    
    let archivedCount = 0;
    const errors: string[] = [];
    
    // Process in smaller batches to avoid transaction timeouts
    const batchSize = 10;
    for (let i = 0; i < memories.length; i += batchSize) {
      const batch = memories.slice(i, i + batchSize);
      
      try {
        await this.elizaRuntime.databaseAdapter.db.transaction(async (tx) => {
          for (const memory of batch) {
            // 1. Calculate importance score
            const importanceScore = await this.calculateImportanceScore(memory);
            
            // 2. Insert into archive
            await tx.query(`
              INSERT INTO memory_archive (
                original_memory_id, agent_id, importance_score, 
                archive_reason, compressed_content, embedding
              ) VALUES ($1, $2, $3, $4, $5, $6)
            `, [
              memory.id,
              memory.agentId,
              importanceScore,
              'automatic_archival',
              JSON.stringify(memory.content),
              null // TODO: Copy embedding if exists
            ]);
            
            // 3. Delete from active memories
            await tx.query('DELETE FROM memories WHERE id = $1', [memory.id]);
            
            // 4. Clean up lifecycle tracking
            await tx.query('DELETE FROM memory_lifecycle WHERE memory_id = $1', [memory.id]);
            
            archivedCount++;
            console.log(`[MemoryArchivingEngine] Archived memory ${memory.id} (importance: ${importanceScore})`);
          }
        });
      } catch (error) {
        console.error(`[MemoryArchivingEngine] Failed to archive batch:`, error);
        errors.push(`Batch ${i}-${i + batchSize}: ${error.message}`);
      }
    }
    
    return {
      archived: archivedCount,
      errors: errors.length > 0 ? errors : undefined,
      skipped: false
    };
  }

  private async calculateImportanceScore(memory: Memory): Promise<number> {
    // Simple importance scoring algorithm
    let score = 0.5; // Base score
    
    // Recency bonus (newer = more important)
    const ageHours = (Date.now() - new Date(memory.createdAt).getTime()) / (1000 * 60 * 60);
    if (ageHours < 24) score += 0.2;
    else if (ageHours < 168) score += 0.1; // 1 week
    
    // Content type bonus
    if (memory.type === 'facts') score += 0.2;
    else if (memory.type === 'memories') score += 0.1;
    
    // Content length bonus (longer = potentially more important)
    const contentLength = JSON.stringify(memory.content).length;
    if (contentLength > 500) score += 0.1;
    
    return Math.min(1.0, Math.max(0.0, score));
  }

  async stopContinuousArchiving(): Promise<void> {
    if (this.archivingInterval) {
      clearInterval(this.archivingInterval);
      this.archivingInterval = null;
      console.log(`[MemoryArchivingEngine] Continuous archiving stopped for agent ${this.elizaRuntime.agentId}`);
    }
  }
}

interface MemoryArchivingConfig {
  activeMemoryLimit: number;
  archiveThresholds: {
    timeBasedHours: number;
    importanceScore: number;
    accessFrequency: number;
  };
  archivingBatchSize: number;
  archivingIntervalMinutes: number;
}

interface ArchivingResult {
  archived: number;
  skipped: boolean;
  reason?: string;
  errors?: string[];
}
```

### Phase 2: Database Schema Updates (Week 1)

```sql
-- Add to existing database (extends setup_analytics_tables.sql)

-- Memory lifecycle tracking
CREATE TABLE IF NOT EXISTS memory_lifecycle (
    memory_id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    importance_score FLOAT DEFAULT 0.5,
    lifecycle_stage VARCHAR(20) DEFAULT 'active',
    archive_eligible_at TIMESTAMP,
    scheduled_for_archive BOOLEAN DEFAULT FALSE
);

-- Enhanced memory archive (extends existing)
ALTER TABLE memory_archive ADD COLUMN IF NOT EXISTS compressed_content JSONB;
ALTER TABLE memory_archive ADD COLUMN IF NOT EXISTS retrieval_count INTEGER DEFAULT 0;
ALTER TABLE memory_archive ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMP;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_memory_lifecycle_agent_stage 
    ON memory_lifecycle(agent_id, lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_memory_lifecycle_archive_eligible 
    ON memory_lifecycle(archive_eligible_at) 
    WHERE scheduled_for_archive = true;

-- Function to update memory access
CREATE OR REPLACE FUNCTION update_memory_access(p_memory_id UUID) 
RETURNS VOID AS $$
BEGIN
    INSERT INTO memory_lifecycle (memory_id, last_accessed, access_count)
    VALUES (p_memory_id, NOW(), 1)
    ON CONFLICT (memory_id) 
    DO UPDATE SET 
        last_accessed = NOW(),
        access_count = memory_lifecycle.access_count + 1;
END;
$$ LANGUAGE plpgsql;
```

### Phase 3: Integration with AutoGen Agent (Week 1)

```typescript
// src/autonomous/AutonomousAgent.ts
export class AutonomousAgent {
  private memoryArchivingEngine: MemoryArchivingEngine;
  
  constructor(runtime: IAgentRuntime) {
    // Initialize memory archiving
    const archivingConfig: MemoryArchivingConfig = {
      activeMemoryLimit: 500,
      archiveThresholds: {
        timeBasedHours: 24,
        importanceScore: 0.3,
        accessFrequency: 7
      },
      archivingBatchSize: 50,
      archivingIntervalMinutes: 15
    };
    
    this.memoryArchivingEngine = new MemoryArchivingEngine(runtime, archivingConfig);
    
    console.log(`[AutonomousAgent] Initialized with memory archiving for agent ${runtime.agentId}`);
  }
  
  async start(): Promise<void> {
    console.log(`[AutonomousAgent] Starting autonomous agent ${this.runtime.agentId}`);
    
    // Start memory archiving FIRST
    await this.memoryArchivingEngine.startContinuousArchiving();
    
    // Then start main agent loop
    await this.startMainLoop();
  }
  
  async stop(): Promise<void> {
    console.log(`[AutonomousAgent] Stopping autonomous agent ${this.runtime.agentId}`);
    
    // Stop archiving
    await this.memoryArchivingEngine.stopContinuousArchiving();
    
    // Stop main loop
    await this.stopMainLoop();
  }
}
```

---

## 🚀 Implementation Timeline

### Week 1: Core Implementation
- **Day 1-2**: Database schema updates and migration
- **Day 3-4**: MemoryArchivingEngine implementation
- **Day 5-6**: Integration with existing autonomous agent
- **Day 7**: Testing and validation

### Week 2: Optimization & Monitoring
- **Day 1-2**: Performance optimization and batch processing
- **Day 3-4**: Monitoring and alerting system
- **Day 5-6**: Load testing with simulated high memory generation
- **Day 7**: Production deployment preparation

---

## 📊 Success Metrics

### Performance Targets
- **Query response time**: <100ms for memory retrieval
- **Archiving throughput**: 100+ memories per minute
- **Database size**: <1GB active memories per agent
- **System stability**: 99.9% uptime during archiving

### Monitoring Alerts
- Memory count approaching limits (>400 active memories)
- Archiving failures or delays
- Query performance degradation
- Database connection pool exhaustion

---

## ⚠️ Critical Risks & Mitigation

### Risk 1: Archiving Process Failure
- **Impact**: Database performance collapse
- **Mitigation**: Robust error handling, manual archiving procedures
- **Monitoring**: Alert on archiving failures

### Risk 2: Important Memory Loss
- **Impact**: Agent performance degradation
- **Mitigation**: Conservative importance scoring, archive retrieval
- **Monitoring**: Track agent decision quality metrics

### Risk 3: Database Lock Contention
- **Impact**: System slowdown during archiving
- **Mitigation**: Small batch sizes, off-peak scheduling
- **Monitoring**: Database lock monitoring

---

**CRITICAL**: This system MUST be implemented and tested before deploying multiple agents. Database performance will collapse without proper memory management. 