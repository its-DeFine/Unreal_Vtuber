import {
  type IAgentRuntime,
  type Service,
  logger,
} from "@elizaos/core";

export interface VTuberStatus {
  endpoint: string;
  connected: boolean;
  lastActivity: Date | null;
  provider: string | null;
  model: string | null;
}

export class VTuberService extends Service {
  static serviceType = "vtuber";
  private status: VTuberStatus;
  private checkInterval: NodeJS.Timeout | null = null;

  constructor() {
    super();
    this.status = {
      endpoint: "",
      connected: false,
      lastActivity: null,
      provider: null,
      model: null,
    };
  }

  async initialize(runtime: IAgentRuntime): Promise<void> {
    logger.info("🎭 Initializing VTuber Service");

    const endpoint = runtime.getSetting("VTUBER_ENDPOINT_URL") || process.env.VTUBER_ENDPOINT_URL;
    
    if (!endpoint) {
      logger.warn("⚠️ VTuber endpoint not configured - VTuber functionality will be disabled");
      return;
    }

    this.status.endpoint = endpoint;
    logger.info(`🔗 VTuber endpoint configured: ${endpoint}`);

    // Test initial connection
    await this.checkConnection(runtime);

    // Set up periodic health checks every 30 seconds
    this.checkInterval = setInterval(async () => {
      await this.checkConnection(runtime);
    }, 30000);

    logger.info("✅ VTuber Service initialized successfully");
  }

  async cleanup(): Promise<void> {
    logger.info("🧹 Cleaning up VTuber Service");
    
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }

    this.status = {
      endpoint: "",
      connected: false,
      lastActivity: null,
      provider: null,
      model: null,
    };

    logger.info("✅ VTuber Service cleanup completed");
  }

  private async checkConnection(runtime: IAgentRuntime): Promise<void> {
    if (!this.status.endpoint) return;

    try {
      // Send a minimal test payload to check if the service is responsive
      const testPayload = {
        text: "health_check",
        autonomous_context: "VTuber service health check"
      };

      const response = await runtime.fetch(this.status.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testPayload),
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });

      if (response.ok) {
        const result = await response.json();
        
        this.status.connected = true;
        this.status.lastActivity = new Date();
        this.status.provider = result.llm_provider || null;
        this.status.model = result.model || null;

        logger.debug("✅ VTuber service health check passed", {
          endpoint: this.status.endpoint,
          provider: this.status.provider,
          model: this.status.model
        });
      } else {
        this.status.connected = false;
        logger.warn(`⚠️ VTuber service health check failed: HTTP ${response.status}`);
      }
    } catch (error) {
      this.status.connected = false;
      logger.warn("⚠️ VTuber service health check failed:", error.message);
    }
  }

  public getStatus(): VTuberStatus {
    return { ...this.status };
  }

  public isAvailable(): boolean {
    return this.status.connected && !!this.status.endpoint;
  }

  public async sendMessage(runtime: IAgentRuntime, text: string, context?: string): Promise<{
    success: boolean;
    data?: any;
    error?: string;
  }> {
    if (!this.isAvailable()) {
      return {
        success: false,
        error: "VTuber service is not available"
      };
    }

    try {
      const payload = {
        text: text.trim(),
        autonomous_context: context || `Agent: ${runtime.character.name}, Activity: Autonomous message`
      };

      logger.info(`🎭 Sending message to VTuber: "${text.substring(0, 100)}${text.length > 100 ? '...' : ''}"`);

      const response = await runtime.fetch(this.status.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(10000), // 10 second timeout
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      this.status.lastActivity = new Date();

      logger.info("✅ VTuber message sent successfully");
      return {
        success: true,
        data: result
      };

    } catch (error) {
      logger.error("❌ Failed to send VTuber message:", error);
      return {
        success: false,
        error: error.message
      };
    }
  }
}

// Export singleton instance
export const vtuberService = new VTuberService(); 