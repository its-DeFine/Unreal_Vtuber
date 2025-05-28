import { IAgentRuntime, Memory, logger } from '@elizaos/core';

export interface MemoryArchivingConfig {
  activeMemoryLimit: number;           // 200 memories max in active table
  archiveThresholds: {
    timeBasedHours: number;            // Archive memories > 48 hours old
    importanceScore: number;           // Archive if importance < 0.3
    accessFrequency: number;           // Archive if not accessed in 14 days
  };
  archivingBatchSize: number;          // Process 50 memories per batch
  archivingIntervalMinutes: number;    // Run archiving every 30 minutes
}

export interface ArchivingResult {
  archived: number;
  skipped: boolean;
  reason?: string;
  errors?: string[];
}

export class MemoryArchivingEngine {
  private elizaRuntime: IAgentRuntime;
  private archivingConfig: MemoryArchivingConfig;
  private archivingInterval: NodeJS.Timeout | null = null;

  constructor(runtime: IAgentRuntime, config: MemoryArchivingConfig) {
    this.elizaRuntime = runtime;
    this.archivingConfig = config;
    
    logger.info(`[MemoryArchivingEngine] Initialized for agent ${runtime.agentId}`, {
      activeMemoryLimit: config.activeMemoryLimit,
      archiveThresholds: config.archiveThresholds,
      archivingIntervalMinutes: config.archivingIntervalMinutes
    });
  }

  async startContinuousArchiving(): Promise<void> {
    logger.info(`[MemoryArchivingEngine] Starting continuous archiving for agent ${this.elizaRuntime.agentId}`);
    
    // Initial archiving run
    await this.performArchivingCycle();
    
    // Schedule periodic archiving
    this.archivingInterval = setInterval(async () => {
      try {
        await this.performArchivingCycle();
      } catch (error) {
        logger.error(`[MemoryArchivingEngine] Archiving cycle failed:`, error);
        // Continue running despite errors
      }
    }, this.archivingConfig.archivingIntervalMinutes * 60 * 1000);
    
    logger.info(`[MemoryArchivingEngine] Continuous archiving started with ${this.archivingConfig.archivingIntervalMinutes}min intervals`);
  }

  async performArchivingCycle(): Promise<ArchivingResult> {
    const startTime = Date.now();
    logger.debug(`[MemoryArchivingEngine] Starting archiving cycle for agent ${this.elizaRuntime.agentId}`);
    
    try {
      // 1. Get current memory count
      const currentMemoryCount = await this.getCurrentMemoryCount();
      logger.debug(`[MemoryArchivingEngine] Current memory count: ${currentMemoryCount}`);
      
      if (currentMemoryCount <= this.archivingConfig.activeMemoryLimit) {
        logger.debug(`[MemoryArchivingEngine] Memory count below threshold, skipping archiving`);
        return { archived: 0, skipped: true, reason: 'below_threshold' };
      }

      // 2. Identify candidates for archiving
      const candidates = await this.identifyArchiveCandidates();
      logger.debug(`[MemoryArchivingEngine] Found ${candidates.length} archiving candidates`);
      
      if (candidates.length === 0) {
        logger.debug(`[MemoryArchivingEngine] No archiving candidates found`);
        return { archived: 0, skipped: true, reason: 'no_candidates' };
      }

      // 3. Archive memories in batches
      const archiveResult = await this.archiveMemoriesBatch(candidates);
      
      const duration = Date.now() - startTime;
      logger.info(`[MemoryArchivingEngine] Archiving cycle completed in ${duration}ms:`, archiveResult);
      
      return archiveResult;
    } catch (error) {
      logger.error(`[MemoryArchivingEngine] Archiving cycle failed:`, error);
      throw error;
    }
  }

  private async getCurrentMemoryCount(): Promise<number> {
    try {
      // Use ElizaOS database adapter to get memory count
      const memories = await this.elizaRuntime.databaseAdapter.getMemories({
        agentId: this.elizaRuntime.agentId,
        tableName: 'memories',
        count: 1000 // Get a reasonable number to count
      });
      
      return memories.length;
    } catch (error) {
      logger.error(`[MemoryArchivingEngine] Failed to get memory count:`, error);
      return 0;
    }
  }

  private async identifyArchiveCandidates(): Promise<Memory[]> {
    const { archiveThresholds } = this.archivingConfig;
    
    try {
      // Get all memories for this agent
      const allMemories = await this.elizaRuntime.databaseAdapter.getMemories({
        agentId: this.elizaRuntime.agentId,
        tableName: 'memories',
        count: 1000 // Get more than the limit to identify candidates
      });

      // Filter memories that meet archiving criteria
      const now = Date.now();
      const candidates: Memory[] = [];

      for (const memory of allMemories) {
        const memoryAge = now - new Date(memory.createdAt).getTime();
        const ageHours = memoryAge / (1000 * 60 * 60);
        
        // Time-based archiving
        if (ageHours > archiveThresholds.timeBasedHours) {
          const importanceScore = await this.calculateImportanceScore(memory);
          
          // Only archive if importance is below threshold
          if (importanceScore < archiveThresholds.importanceScore) {
            candidates.push(memory);
          }
        }
      }

      // Sort by importance (lowest first) and age (oldest first)
      candidates.sort((a, b) => {
        const aAge = new Date(a.createdAt).getTime();
        const bAge = new Date(b.createdAt).getTime();
        return aAge - bAge; // Oldest first
      });

      // Return only the batch size
      return candidates.slice(0, this.archivingConfig.archivingBatchSize);
    } catch (error) {
      logger.error(`[MemoryArchivingEngine] Failed to identify archive candidates:`, error);
      return [];
    }
  }

  private async archiveMemoriesBatch(memories: Memory[]): Promise<ArchivingResult> {
    logger.info(`[MemoryArchivingEngine] Archiving ${memories.length} memories`);
    
    let archivedCount = 0;
    const errors: string[] = [];
    
    for (const memory of memories) {
      try {
        // Calculate importance score
        const importanceScore = await this.calculateImportanceScore(memory);
        
        // Store in context_archive table (using existing analytics table)
        await this.storeInArchive(memory, importanceScore);
        
        // Remove from active memories
        await this.removeFromActiveMemories(memory.id);
        
        archivedCount++;
        logger.debug(`[MemoryArchivingEngine] Archived memory ${memory.id} (importance: ${importanceScore})`);
        
      } catch (error) {
        logger.error(`[MemoryArchivingEngine] Failed to archive memory ${memory.id}:`, error);
        errors.push(`Memory ${memory.id}: ${error.message}`);
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
    
    // VTuber-related content bonus
    const contentText = JSON.stringify(memory.content).toLowerCase();
    if (contentText.includes('vtuber') || contentText.includes('autonomous') || contentText.includes('research')) {
      score += 0.15;
    }
    
    return Math.min(1.0, Math.max(0.0, score));
  }

  private async storeInArchive(memory: Memory, importanceScore: number): Promise<void> {
    try {
      // Use the existing context_archive table from analytics
      const archiveData = {
        agent_id: memory.agentId,
        archived_content: {
          memory_id: memory.id,
          content: memory.content,
          metadata: memory.metadata,
          created_at: memory.createdAt,
          type: memory.type
        },
        importance_score: importanceScore,
        archive_reason: 'automatic_archival',
        metadata: {
          archived_at: new Date().toISOString(),
          original_type: memory.type
        }
      };

      // Store using ElizaOS database adapter - Fixed database access
      // Note: This assumes the context_archive table exists from setup_analytics_tables.sql
      await this.elizaRuntime.db.query(`
        INSERT INTO context_archive (
          agent_id, archived_content, importance_score, archive_reason, metadata
        ) VALUES ($1, $2, $3, $4, $5)
      `, [
        archiveData.agent_id,
        JSON.stringify(archiveData.archived_content),
        archiveData.importance_score,
        archiveData.archive_reason,
        JSON.stringify(archiveData.metadata)
      ]);

    } catch (error) {
      logger.error(`[MemoryArchivingEngine] Failed to store memory in archive:`, error);
      throw error;
    }
  }

  private async removeFromActiveMemories(memoryId: string): Promise<void> {
    try {
      // Remove from memories table - Fixed database access
      await this.elizaRuntime.db.query(
        'DELETE FROM memories WHERE id = $1',
        [memoryId]
      );
    } catch (error) {
      logger.error(`[MemoryArchivingEngine] Failed to remove memory from active table:`, error);
      throw error;
    }
  }

  async retrieveFromArchive(query: string, limit: number = 5): Promise<any[]> {
    try {
      logger.debug(`[MemoryArchivingEngine] Retrieving from archive with query: "${query}"`);
      
      // Simple text search in archived content - Fixed database access
      const result = await this.elizaRuntime.db.query(`
        SELECT archived_content, importance_score, timestamp
        FROM context_archive 
        WHERE agent_id = $1 
        AND archived_content::text ILIKE $2
        ORDER BY importance_score DESC, timestamp DESC
        LIMIT $3
      `, [
        this.elizaRuntime.agentId,
        `%${query}%`,
        limit
      ]);

      return result.rows.map(row => ({
        content: typeof row.archived_content === 'string' 
          ? JSON.parse(row.archived_content) 
          : row.archived_content,
        importance: row.importance_score,
        archived_at: row.timestamp
      }));
    } catch (error) {
      logger.error(`[MemoryArchivingEngine] Failed to retrieve from archive:`, error);
      return [];
    }
  }

  async stopContinuousArchiving(): Promise<void> {
    if (this.archivingInterval) {
      clearInterval(this.archivingInterval);
      this.archivingInterval = null;
      logger.info(`[MemoryArchivingEngine] Continuous archiving stopped for agent ${this.elizaRuntime.agentId}`);
    }
  }

  async getArchiveStats(): Promise<{
    totalArchived: number;
    averageImportance: number;
    oldestArchived: string;
    newestArchived: string;
  }> {
    try {
      // Fixed database access - use this.elizaRuntime.db instead of this.elizaRuntime.databaseAdapter.db
      const result = await this.elizaRuntime.db.query(`
        SELECT 
          COUNT(*) as total,
          AVG(importance_score) as avg_importance,
          MIN(timestamp) as oldest,
          MAX(timestamp) as newest
        FROM context_archive 
        WHERE agent_id = $1
      `, [this.elizaRuntime.agentId]);

      const row = result.rows[0];
      return {
        totalArchived: parseInt(row.total) || 0,
        averageImportance: parseFloat(row.avg_importance) || 0,
        oldestArchived: row.oldest || 'N/A',
        newestArchived: row.newest || 'N/A'
      };
    } catch (error) {
      logger.error(`[MemoryArchivingEngine] Failed to get archive stats:`, error);
      return {
        totalArchived: 0,
        averageImportance: 0,
        oldestArchived: 'N/A',
        newestArchived: 'N/A'
      };
    }
  }
} 