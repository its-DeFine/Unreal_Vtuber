// Copyright Epic Games, Inc. All Rights Reserved.
import net from 'net';
import { Logger } from '@epicgames-ps/lib-pixelstreamingsignalling-ue5.7';

export type MatchmakerClientConfig = {
    matchmakerAddress: string;
    matchmakerPort: number;
    publicAddress: string;
    publicPort: number;
    publicHttps: boolean;
    retryIntervalSeconds: number;
    keepAliveIntervalSeconds: number;
    streamerId?: string;
};

export type MatchmakerStateProvider = {
    getReady: () => boolean;
    getPlayerConnected: () => boolean;
};

type MatchmakerMessage =
    | {
          type: 'connect';
          address: string;
          port: number;
          https: boolean;
          ready: boolean;
          playerConnected: boolean;
          streamer_id?: string;
      }
    | { type: 'streamerConnected'; streamer_id?: string }
    | { type: 'streamerDisconnected'; streamer_id?: string }
    | { type: 'clientConnected' }
    | { type: 'clientDisconnected' }
    | { type: 'ping' };

export class MatchmakerClient {
    private socket: net.Socket | null = null;
    private reconnectTimeout: NodeJS.Timeout | null = null;
    private pingInterval: NodeJS.Timeout | null = null;
    private connected: boolean = false;

    constructor(
        private cfg: MatchmakerClientConfig,
        private stateProvider: MatchmakerStateProvider
    ) {}

    start(): void {
        if (!this.cfg.matchmakerAddress) {
            Logger.warn('Matchmaker is enabled but matchmakerAddress is empty; skipping matchmaker client.');
            return;
        }
        this.connect();
    }

    stop(): void {
        this.clearReconnect();
        this.clearPing();
        this.connected = false;
        if (this.socket && !this.socket.destroyed) {
            this.socket.destroy();
        }
        this.socket = null;
    }

    private connect(): void {
        this.clearReconnect();
        this.clearPing();
        this.connected = false;

        const socket = new net.Socket();
        this.socket = socket;

        socket.on('connect', () => {
            this.connected = true;
            Logger.info(`Connected to Matchmaker ${this.cfg.matchmakerAddress}:${this.cfg.matchmakerPort}`);
            socket.setKeepAlive(true, 60_000);
            this.sendConnect();
            this.startPing();
        });

        socket.on('error', (err) => {
            Logger.warn(`Matchmaker connection error: ${err.message}`);
        });

        socket.on('end', () => {
            Logger.warn('Matchmaker connection ended');
        });

        socket.on('close', (hadError) => {
            this.connected = false;
            Logger.warn(`Matchmaker connection closed (hadError=${hadError})`);
            this.scheduleReconnect();
        });

        try {
            socket.connect(this.cfg.matchmakerPort, this.cfg.matchmakerAddress);
        } catch (err: any) {
            Logger.warn(`Matchmaker connect threw: ${err?.message || String(err)}`);
            this.scheduleReconnect();
        }
    }

    private scheduleReconnect(): void {
        this.clearPing();
        this.clearReconnect();
        Logger.info(`Retrying Matchmaker in ${this.cfg.retryIntervalSeconds} seconds`);
        this.reconnectTimeout = setTimeout(() => this.connect(), this.cfg.retryIntervalSeconds * 1000);
    }

    private clearReconnect(): void {
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
    }

    private startPing(): void {
        this.clearPing();
        this.pingInterval = setInterval(() => {
            this.write({ type: 'ping' });
        }, this.cfg.keepAliveIntervalSeconds * 1000);
    }

    private clearPing(): void {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    private sendConnect(): void {
        const streamerId = (this.cfg.streamerId || '').trim();
        const message: MatchmakerMessage = {
            type: 'connect',
            address: this.cfg.publicAddress,
            port: this.cfg.publicPort,
            https: this.cfg.publicHttps,
            ready: this.stateProvider.getReady(),
            playerConnected: this.stateProvider.getPlayerConnected(),
            streamer_id: streamerId || undefined
        };
        this.write(message);
    }

    sendStreamerConnected(): void {
        const streamerId = (this.cfg.streamerId || '').trim();
        this.write({ type: 'streamerConnected', streamer_id: streamerId || undefined });
    }

    sendStreamerDisconnected(): void {
        const streamerId = (this.cfg.streamerId || '').trim();
        this.write({ type: 'streamerDisconnected', streamer_id: streamerId || undefined });
    }

    sendClientConnected(): void {
        this.write({ type: 'clientConnected' });
    }

    sendClientDisconnected(): void {
        this.write({ type: 'clientDisconnected' });
    }

    private write(message: MatchmakerMessage): void {
        if (!this.connected || !this.socket || this.socket.destroyed) {
            return;
        }
        try {
            this.socket.write(JSON.stringify(message));
        } catch (err: any) {
            Logger.warn(`Failed to write to Matchmaker: ${err?.message || String(err)}`);
        }
    }
}
