import {
  type Provider,
  type IAgentRuntime,
  type Memory,
  type State,
  logger,
  type ProviderResult,
} from "@elizaos/core";
import { PluginManagerService } from "../services/pluginManagerService";
import { type PluginState, PluginStatus } from "../types";

export const pluginStateProvider: Provider = {
  name: "pluginState",
  description:
    "Provides information about the current state of all plugins including loaded status, missing environment variables, and errors",

  async get(
    runtime: IAgentRuntime,
    message: Memory,
    state: State,
  ): Promise<ProviderResult> {
    try {
      const pluginManager = runtime.getService(
        "PLUGIN_MANAGER",
      ) as PluginManagerService;

      if (!pluginManager) {
        return {
          text: "Plugin Manager service is not available",
          values: {},
          data: {
            error: "Plugin Manager service not found",
          },
        };
      }

      const plugins = pluginManager.getAllPlugins();
      const loadedPlugins = plugins.filter(
        (p) => p.status === PluginStatus.LOADED,
      );
      const errorPlugins = plugins.filter(
        (p) => p.status === PluginStatus.ERROR,
      );
      const readyPlugins = plugins.filter(
        (p) => p.status === PluginStatus.READY,
      );
      const buildingPlugins = plugins.filter(
        (p) => p.status === PluginStatus.BUILDING,
      );

      // Format plugin information
      const formatPlugin = (plugin: PluginState) => {
        const parts: string[] = [`${plugin.name} (${plugin.status})`];

        if (plugin.missingEnvVars?.length > 0) {
          parts.push(`Missing ENV vars: ${plugin.missingEnvVars.join(", ")}`);
        }

        if (plugin.error) {
          parts.push(`Error: ${plugin.error}`);
        }

        if (plugin.loadedAt) {
          parts.push(
            `Loaded at: ${new Date(plugin.loadedAt).toLocaleString()}`,
          );
        }

        return parts.join(" - ");
      };

      const sections: string[] = [];

      if (loadedPlugins.length > 0) {
        sections.push(
          "**Loaded Plugins:**\n" +
            loadedPlugins.map((p) => `- ${formatPlugin(p)}`).join("\n"),
        );
      }

      if (errorPlugins.length > 0) {
        sections.push(
          "**Plugins with Errors:**\n" +
            errorPlugins.map((p) => `- ${formatPlugin(p)}`).join("\n"),
        );
      }

      if (readyPlugins.length > 0) {
        sections.push(
          "**Ready to Load:**\n" +
            readyPlugins.map((p) => `- ${formatPlugin(p)}`).join("\n"),
        );
      }

      if (buildingPlugins.length > 0) {
        sections.push(
          "**Building:**\n" +
            buildingPlugins.map((p) => `- ${formatPlugin(p)}`).join("\n"),
        );
      }

      // Collect all missing environment variables
      const allMissingEnvVars = new Set<string>();
      plugins.forEach((p) => {
        p.missingEnvVars?.forEach((v) => allMissingEnvVars.add(v));
      });

      if (allMissingEnvVars.size > 0) {
        sections.push(
          `**All Missing Environment Variables:**\n${Array.from(
            allMissingEnvVars,
          )
            .map((v) => `- ${v}`)
            .join("\n")}`,
        );
      }

      const text =
        sections.length > 0
          ? sections.join("\n\n")
          : "No plugins registered in the Plugin Manager.";

      return {
        text,
        values: {
          totalPlugins: plugins.length,
          loadedCount: loadedPlugins.length,
          errorCount: errorPlugins.length,
          readyCount: readyPlugins.length,
          buildingCount: buildingPlugins.length,
          missingEnvVars: Array.from(allMissingEnvVars),
        },
        data: {
          plugins: plugins.map((p) => ({
            id: p.id,
            name: p.name,
            status: p.status,
            error: p.error,
            missingEnvVars: p.missingEnvVars,
            createdAt: p.createdAt,
            loadedAt: p.loadedAt,
            unloadedAt: p.unloadedAt,
          })),
        },
      };
    } catch (error) {
      logger.error("[pluginStateProvider] Error getting plugin state:", error);
      return {
        text: "Error retrieving plugin state information",
        values: {},
        data: {
          error: error instanceof Error ? error.message : String(error),
        },
      };
    }
  },
};
