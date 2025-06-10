import {
  Service,
  type IAgentRuntime,
  type ServiceTypeName,
  logger,
  type UUID,
  type Memory,
  createUniqueUuid,
  ModelType,
} from "@elizaos/core";
import {
  type Experience,
  type ExperienceQuery,
  type ExperienceAnalysis,
  ExperienceType,
  OutcomeType,
  type ExperienceEvent,
  ExperienceServiceType,
} from "./types";
import { v4 as uuidv4 } from "uuid";
import { analyzeExperience, detectPatterns } from "./utils/experienceAnalyzer";
import { ConfidenceDecayManager } from "./utils/confidenceDecay";
import { ExperienceRelationshipManager } from "./utils/experienceRelationships";

export class ExperienceService extends Service {
  static override serviceType: ServiceTypeName =
    ExperienceServiceType.EXPERIENCE;
  override capabilityDescription =
    "Manages agent experiences, learning from successes and failures to improve future decisions";

  private experiences: Map<UUID, Experience> = new Map();
  private experiencesByDomain: Map<string, Set<UUID>> = new Map();
  private experiencesByType: Map<ExperienceType, Set<UUID>> = new Map();
  private maxExperiences = 10000; // Configurable limit - reverted to default
  private decayManager: ConfidenceDecayManager;
  private relationshipManager: ExperienceRelationshipManager;

  constructor(runtime: IAgentRuntime) {
    super(runtime);
    this.decayManager = new ConfidenceDecayManager();
    this.relationshipManager = new ExperienceRelationshipManager();
    this.loadExperiences();
  }

  static async start(runtime: IAgentRuntime): Promise<ExperienceService> {
    const service = new ExperienceService(runtime);
    // loadExperiences is called by constructor
    return service;
  }

  private async loadExperiences(): Promise<void> {
    try {
      // TODO: Load from knowledge service if available
      logger.info("[ExperienceService] Initialized");
    } catch (error) {
      logger.error("[ExperienceService] Error loading experiences:", error);
    }
  }

  async recordExperience(
    experienceData: Partial<Experience>,
  ): Promise<Experience> {
    try {
      // Generate embedding for the experience
      let embedding: number[] | undefined;
      try {
        const embeddingText = `${experienceData.context} ${experienceData.action} ${experienceData.result} ${experienceData.learning}`;
        embedding = await this.runtime.useModel(ModelType.TEXT_EMBEDDING, {
          prompt: embeddingText,
        });
      } catch (error) {
        logger.error("[ExperienceService] Error generating embedding:", error);
        // Leave embedding undefined on error
      }

      const experience: Experience = {
        id: uuidv4() as UUID,
        agentId: this.runtime.agentId,
        type: experienceData.type || ExperienceType.LEARNING,
        outcome: experienceData.outcome || OutcomeType.NEUTRAL,
        context: experienceData.context || "",
        action: experienceData.action || "",
        result: experienceData.result || "",
        learning: experienceData.learning || "",
        domain: experienceData.domain || "general",
        tags: experienceData.tags || [],
        confidence: experienceData.confidence || 0.5,
        importance: experienceData.importance || 0.5,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        accessCount: 0,
        lastAccessedAt: Date.now(),
        embedding,
        relatedExperiences: experienceData.relatedExperiences,
        supersedes: experienceData.supersedes,
        previousBelief: experienceData.previousBelief,
        correctedBelief: experienceData.correctedBelief,
      };

      // Store the experience
      this.experiences.set(experience.id, experience);

      // Update indexes
      if (!this.experiencesByDomain.has(experience.domain)) {
        this.experiencesByDomain.set(experience.domain, new Set());
      }
      this.experiencesByDomain.get(experience.domain)!.add(experience.id);

      if (!this.experiencesByType.has(experience.type)) {
        this.experiencesByType.set(experience.type, new Set());
      }
      this.experiencesByType.get(experience.type)!.add(experience.id);

      // Check for contradictions and add relationships
      const allExperiences = Array.from(this.experiences.values());
      const contradictions = this.relationshipManager.findContradictions(
        experience,
        allExperiences,
      );

      for (const contradiction of contradictions) {
        this.relationshipManager.addRelationship({
          fromId: experience.id,
          toId: contradiction.id,
          type: "contradicts",
          strength: 0.8,
        });
      }

      // Prune if necessary
      if (this.experiences.size > this.maxExperiences) {
        await this.pruneOldExperiences();
      }

      // Emit event
      try {
        await this.runtime.emitEvent("EXPERIENCE_RECORDED", {
          experienceId: experience.id,
          eventType: "created",
          timestamp: experience.createdAt,
        });
      } catch (error) {
        logger.warn(
          "[ExperienceService] Failed to emit experience event:",
          error,
        );
      }

      logger.info(
        `[ExperienceService] Recorded experience: ${experience.id} (${experience.type})`,
      );

      return experience;
    } catch (error) {
      logger.error("[ExperienceService] Error recording experience:", error);
      throw error;
    }
  }

  async queryExperiences(query: ExperienceQuery): Promise<Experience[]> {
    let results: Experience[] = [];

    // Start with all experiences
    let candidates = Array.from(this.experiences.values());

    // Apply filters
    if (query.type) {
      const types = Array.isArray(query.type) ? query.type : [query.type];
      candidates = candidates.filter((exp) => types.includes(exp.type));
    }

    if (query.outcome) {
      candidates = candidates.filter((exp) => exp.outcome === query.outcome);
    }

    if (query.domain) {
      const domains = Array.isArray(query.domain)
        ? query.domain
        : [query.domain];
      candidates = candidates.filter((exp) => domains.includes(exp.domain));
    }

    if (query.tags && query.tags.length > 0) {
      candidates = candidates.filter((exp) =>
        query.tags!.some((tag) => exp.tags.includes(tag)),
      );
    }

    if (query.minConfidence !== undefined) {
      candidates = candidates.filter((exp) => {
        const decayedConfidence = this.decayManager.getDecayedConfidence(exp);
        return decayedConfidence >= query.minConfidence!;
      });
    }

    if (query.minImportance !== undefined) {
      candidates = candidates.filter(
        (exp) => exp.importance >= query.minImportance!,
      );
    }

    if (query.timeRange) {
      candidates = candidates.filter((exp) => {
        if (query.timeRange!.start && exp.createdAt < query.timeRange!.start)
          return false;
        if (query.timeRange!.end && exp.createdAt > query.timeRange!.end)
          return false;
        return true;
      });
    }

    // Sort by relevance (considering decayed confidence)
    candidates.sort((a, b) => {
      const scoreA = this.decayManager.getDecayedConfidence(a) * a.importance;
      const scoreB = this.decayManager.getDecayedConfidence(b) * b.importance;
      return scoreB - scoreA;
    });

    // Apply limit
    results = candidates.slice(0, query.limit || 10);

    // Include related experiences if requested
    if (query.includeRelated) {
      const relatedIds = new Set<UUID>();
      for (const exp of results) {
        if (exp.relatedExperiences) {
          exp.relatedExperiences.forEach((id) => relatedIds.add(id as UUID));
        }
      }

      const related = Array.from(relatedIds)
        .map((id) => this.experiences.get(id))
        .filter((exp): exp is Experience => exp !== undefined)
        .filter((exp) => !results.some((r) => r.id === exp.id));

      results.push(...related);
    }

    // Update access counts
    for (const exp of results) {
      exp.accessCount++;
      exp.lastAccessedAt = Date.now();
    }

    return results;
  }

  async findSimilarExperiences(
    text: string,
    limit: number = 5,
  ): Promise<Experience[]> {
    if (!text || this.experiences.size === 0) {
      return [];
    }

    try {
      // Generate embedding for the query text
      const queryEmbedding = (await this.runtime.useModel(
        ModelType.TEXT_EMBEDDING,
        {
          prompt: text,
        },
      )) as number[];

      // Calculate similarities
      const similarities: Array<{
        experience: Experience;
        similarity: number;
      }> = [];

      for (const experience of this.experiences.values()) {
        if (experience.embedding) {
          const similarity = this.cosineSimilarity(
            queryEmbedding,
            experience.embedding,
          );
          similarities.push({ experience, similarity });
        }
      }

      // Sort by similarity and return top results
      similarities.sort((a, b) => b.similarity - a.similarity);
      const results = similarities
        .slice(0, limit)
        .map((item) => item.experience);

      // Update access counts
      for (const exp of results) {
        exp.accessCount++;
        exp.lastAccessedAt = Date.now();
      }

      return results;
    } catch (error) {
      logger.error(
        "[ExperienceService] Error finding similar experiences:",
        error,
      );
      return [];
    }
  }

  async analyzeExperiences(
    domain?: string,
    type?: ExperienceType,
  ): Promise<ExperienceAnalysis> {
    const experiences = await this.queryExperiences({
      domain: domain ? [domain] : undefined,
      type: type ? [type] : undefined,
      limit: 100,
    });

    if (experiences.length === 0) {
      return {
        pattern: "No experiences found for analysis",
        frequency: 0,
        reliability: 0,
        alternatives: [],
        recommendations: [],
      };
    }

    // Analyze patterns
    const learnings = experiences.map((exp) => exp.learning);
    const commonWords = this.findCommonPatterns(learnings);

    // Calculate reliability based on consistency and confidence
    const avgConfidence =
      experiences.reduce((sum, exp) => sum + exp.confidence, 0) /
      experiences.length;
    const outcomeConsistency = this.calculateOutcomeConsistency(experiences);
    const reliability = (avgConfidence + outcomeConsistency) / 2;

    // Find alternatives
    const alternatives = this.extractAlternatives(experiences);

    // Generate recommendations
    const recommendations = this.generateRecommendations(
      experiences,
      reliability,
    );

    return {
      pattern:
        commonWords.length > 0
          ? `Common patterns: ${commonWords.join(", ")}`
          : "No clear patterns detected",
      frequency: experiences.length,
      reliability,
      alternatives,
      recommendations,
    };
  }

  private cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) return 0;

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    if (normA === 0 || normB === 0) return 0;
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  private findCommonPatterns(texts: string[]): string[] {
    const wordFreq = new Map<string, number>();

    for (const text of texts) {
      const words = text.toLowerCase().split(/\s+/);
      for (const word of words) {
        if (word.length > 3) {
          // Skip short words
          wordFreq.set(word, (wordFreq.get(word) || 0) + 1);
        }
      }
    }

    // Return words that appear in at least 30% of texts
    const threshold = texts.length * 0.3;
    return Array.from(wordFreq.entries())
      .filter(([_, count]) => count >= threshold)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([word]) => word);
  }

  private calculateOutcomeConsistency(experiences: Experience[]): number {
    if (experiences.length === 0) return 0;

    const outcomeCounts = new Map<OutcomeType, number>();
    for (const exp of experiences) {
      outcomeCounts.set(exp.outcome, (outcomeCounts.get(exp.outcome) || 0) + 1);
    }

    const maxCount = Math.max(...outcomeCounts.values());
    return maxCount / experiences.length;
  }

  private extractAlternatives(experiences: Experience[]): string[] {
    const alternatives = new Set<string>();

    for (const exp of experiences) {
      if (exp.type === ExperienceType.CORRECTION && exp.correctedBelief) {
        alternatives.add(exp.correctedBelief);
      }
      if (
        exp.outcome === OutcomeType.NEGATIVE &&
        exp.learning.includes("instead")
      ) {
        // Extract alternative from learning
        const match = exp.learning.match(/instead\s+(.+?)(?:\.|$)/i);
        if (match) {
          alternatives.add(match[1].trim());
        }
      }
    }

    return Array.from(alternatives).slice(0, 5);
  }

  private generateRecommendations(
    experiences: Experience[],
    reliability: number,
  ): string[] {
    const recommendations: string[] = [];

    if (reliability > 0.8) {
      recommendations.push("Continue using successful approaches");
      recommendations.push("Document and share these reliable methods");
    } else if (reliability > 0.6) {
      recommendations.push("Continue using successful approaches with caution");
      recommendations.push("Monitor for potential issues");
      recommendations.push("Consider backup strategies");
    } else if (reliability > 0.4) {
      recommendations.push("Review and improve current approaches");
      recommendations.push("Investigate failure patterns");
      recommendations.push("Consider alternative methods");
    } else {
      recommendations.push("Significant changes needed to current approach");
      recommendations.push("Analyze failure causes thoroughly");
      recommendations.push("Seek alternative solutions");
    }

    // Add specific recommendations based on patterns
    const failureTypes = new Map<string, number>();
    experiences
      .filter((e) => e.outcome === OutcomeType.NEGATIVE)
      .forEach((e) => {
        const key = e.learning.toLowerCase();
        failureTypes.set(key, (failureTypes.get(key) || 0) + 1);
      });

    if (failureTypes.size > 0) {
      const mostCommonFailure = Array.from(failureTypes.entries()).sort(
        (a, b) => b[1] - a[1],
      )[0];

      if (mostCommonFailure[1] > 1) {
        recommendations.push(
          `Address recurring issue: ${mostCommonFailure[0]}`,
        );
      }
    }

    // Add domain-specific recommendations
    const domains = new Set(experiences.map((e) => e.domain));
    if (domains.has("shell")) {
      recommendations.push("Verify command syntax and permissions");
    }
    if (domains.has("coding")) {
      recommendations.push("Test thoroughly before deployment");
    }
    if (domains.has("network")) {
      recommendations.push("Implement retry logic and error handling");
    }

    return recommendations.slice(0, 5); // Limit to 5 recommendations
  }

  private async pruneOldExperiences(): Promise<void> {
    if (this.experiences.size <= this.maxExperiences) {
      return;
    }

    // Sort experiences by importance (ascending) and access count (ascending)
    const experienceArray = Array.from(this.experiences.values());
    experienceArray.sort((a, b) => {
      // First sort by importance
      if (a.importance !== b.importance) {
        return a.importance - b.importance;
      }
      // Then by access count
      if (a.accessCount !== b.accessCount) {
        return a.accessCount - b.accessCount;
      }
      // Finally by age (older first)
      return a.createdAt - b.createdAt;
    });

    // Remove the least important experiences
    const toRemove = experienceArray.slice(
      0,
      experienceArray.length - this.maxExperiences,
    );
    let removedCount = 0;

    for (const experience of toRemove) {
      this.experiences.delete(experience.id);

      // Remove from domain index
      const domainSet = this.experiencesByDomain.get(experience.domain);
      if (domainSet) {
        domainSet.delete(experience.id);
        if (domainSet.size === 0) {
          this.experiencesByDomain.delete(experience.domain);
        }
      }

      // Remove from type index
      const typeSet = this.experiencesByType.get(experience.type);
      if (typeSet) {
        typeSet.delete(experience.id);
        if (typeSet.size === 0) {
          this.experiencesByType.delete(experience.type);
        }
      }

      removedCount++;
    }

    logger.info(`[ExperienceService] Pruned ${removedCount} old experiences`);
  }

  async stop(): Promise<void> {
    logger.info("[ExperienceService] Stopping...");
    // TODO: Save experiences to database
  }
}
