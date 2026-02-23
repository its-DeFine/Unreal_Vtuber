declare module "nanoclaw/plugin-sdk" {
  export type ChannelPlugin<TAccount = unknown> = {
    id: string;
    meta: {
      id: string;
      label: string;
      selectionLabel: string;
      docsPath: string;
      blurb: string;
      order?: number;
      aliases?: string[];
      detailLabel?: string;
    };
    capabilities: {
      chatTypes: string[];
      nativeCommands?: boolean;
      media?: boolean;
      blockStreaming?: boolean;
      reactions?: boolean;
      edit?: boolean;
      unsend?: boolean;
      reply?: boolean;
    };
    reload?: {
      configPrefixes: string[];
      noopPrefixes?: string[];
    };
    config: {
      listAccountIds: (cfg: unknown) => string[];
      resolveAccount: (cfg: unknown, accountId?: string | null) => TAccount;
      defaultAccountId?: (cfg: unknown) => string;
      isEnabled?: (account: TAccount, cfg: unknown) => boolean;
      isConfigured?: (account: TAccount, cfg: unknown) => boolean | Promise<boolean>;
      describeAccount?: (account: TAccount, cfg: unknown) => Record<string, unknown>;
    };
    status?: {
      buildChannelSummary?: (params: {
        account: TAccount;
        cfg: unknown;
        defaultAccountId: string;
        snapshot: Record<string, unknown>;
      }) => Record<string, unknown> | Promise<Record<string, unknown>>;
    };
  };

  export type NanoClawPluginServiceContext = {
    config: unknown;
    workspaceDir?: string;
    stateDir: string;
    logger: {
      info: (message: string) => void;
      warn: (message: string) => void;
      error: (message: string) => void;
      debug?: (message: string) => void;
    };
  };

  export type NanoClawPluginService = {
    id: string;
    start: (ctx: NanoClawPluginServiceContext) => void | Promise<void>;
    stop?: (ctx: NanoClawPluginServiceContext) => void | Promise<void>;
  };

  export type NanoClawPluginApi = {
    id: string;
    name: string;
    source: string;
    config: unknown;
    pluginConfig?: Record<string, unknown>;
    runtime: {
      state: {
        resolveStateDir: () => string;
      };
    };
    logger: {
      info: (message: string) => void;
      warn: (message: string) => void;
      error: (message: string) => void;
      debug?: (message: string) => void;
    };
    registerTool: (...args: unknown[]) => void;
    registerHook: (...args: unknown[]) => void;
    registerHttpHandler: (...args: unknown[]) => void;
    registerHttpRoute: (...args: unknown[]) => void;
    registerChannel: (registration: { plugin: ChannelPlugin<any> } | ChannelPlugin<any>) => void;
    registerGatewayMethod: (...args: unknown[]) => void;
    registerCli: (...args: unknown[]) => void;
    registerService: (service: NanoClawPluginService) => void;
    registerProvider: (...args: unknown[]) => void;
    registerCommand: (command: {
      name: string;
      description: string;
      acceptsArgs?: boolean;
      handler: (ctx: {
        args?: string;
      }) => { text: string } | Promise<{ text: string }>;
    }) => void;
    resolvePath: (input: string) => string;
    on: (...args: unknown[]) => void;
  };
}
