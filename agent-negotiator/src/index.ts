/**
 * Standalone entrypoint for agent-negotiator.
 *
 * NanoClaw embedding uses `src/nanoclaw/plugin.ts`.
 */

import { loadNegotiatorEnvConfig, startNegotiatorService } from "./service.js";

async function main() {
  const config = loadNegotiatorEnvConfig();
  const service = await startNegotiatorService(config);

  let shuttingDown = false;
  const shutdown = async (signal: string) => {
    if (shuttingDown) {
      return;
    }
    shuttingDown = true;
    console.log(`[negotiator] Received ${signal}; shutting down...`);
    try {
      await service.stop();
      process.exit(0);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`[negotiator] Shutdown error: ${message}`);
      process.exit(1);
    }
  };

  process.on("SIGTERM", () => {
    void shutdown("SIGTERM");
  });

  process.on("SIGINT", () => {
    void shutdown("SIGINT");
  });
}

main().catch((err) => {
  const message = err instanceof Error ? err.stack ?? err.message : String(err);
  console.error(`[negotiator] Fatal: ${message}`);
  process.exit(1);
});
