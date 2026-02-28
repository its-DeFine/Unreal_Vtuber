/**
 * Standalone execution is intentionally disabled.
 * This package must be booted by the claw plugin runtime.
 */

console.error(
  "[negotiator] Standalone startup is disabled. Load this package via claw plugin `agent-negotiator`."
);
process.exit(1);
