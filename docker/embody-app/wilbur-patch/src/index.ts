// Copyright Epic Games, Inc. All Rights Reserved.
import express from 'express';
import { execFileSync } from 'child_process';
import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import {
    SignallingServer,
    IServerConfig,
    WebServer,
    InitLogging,
    Logger,
    IWebServerConfig
} from '@epicgames-ps/lib-pixelstreamingsignalling-ue5.7';
import { beautify, IProgramOptions } from './Utils';
import { initInputHandler } from './InputHandler';
import { Command, Option } from 'commander';
import { initialize } from 'express-openapi';
import { MatchmakerClient } from './MatchmakerClient';

// eslint-disable-next-line  @typescript-eslint/no-unsafe-assignment
const pjson = require('../package.json');

/* eslint-disable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-argument */
// possible config file options
let config_file: IProgramOptions = {};
const configArgsParser = new Command()
    .option('--no_config', 'Skips the reading of the config file. Only CLI options will be used.', false)
    .option(
        '--config_file <path>',
        'Sets the path of the config file.',
        `${path.resolve(__dirname, '..', 'config.json')}`
    )
    .helpOption(false)
    .allowUnknownOption() // ignore unknown options as we are doing a minimal parse here
    .parse()
    .opts();
// If we do not get passed `--no_config` then attempt open the config file
if (!configArgsParser.no_config) {
    try {
        if (fs.existsSync(configArgsParser.config_file)) {
            console.log(`Config file configured as: ${configArgsParser.config_file}`);
            const configData = fs.readFileSync(configArgsParser.config_file, { encoding: 'utf8' });
            config_file = JSON.parse(configData);
        } else {
            // Even though proper logging is not intialized, logging here is better than nothing.
            console.log(`No config file found at: ${configArgsParser.config_file}`);
        }
    } catch (error: unknown) {
        console.error(error);
    }
}

const program = new Command();
program
    .name('node dist/index.js')
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
    .description(pjson.description)
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
    .version(pjson.version);

// For any switch that doesn't take an argument, like --serve, its important to give it a default value.
// Without the default, not supplying the default will mean the option is `undefined` in
// `cli_option`s` and loading from the configuration file will not work as intended.
// The way the configuration file works is that if it is found it will parsed for key/values that match
// the argument names specified below. If one is found it will become the new default value for that option.
// This allow the user to have values in the configuration file but also override them by specifying an argument on the command line.
program
    .option('--log_folder <path>', 'Sets the path for the log files.', config_file.log_folder || 'logs')
    .addOption(
        new Option('--log_level_console <level>', 'Sets the logging level for console messages.')
            .choices(['debug', 'info', 'warning', 'error'])
            .default(config_file.log_level_console || 'info')
    )
    .addOption(
        new Option('--log_level_file <level>', 'Sets the logging level for log files.')
            .choices(['debug', 'info', 'warning', 'error'])
            .default(config_file.log_level_file || 'info')
    )
    .addOption(
        new Option(
            '--console_messages [detail]',
            'Displays incoming and outgoing signalling messages on the console.'
        )
            .choices(['basic', 'verbose', 'formatted'])
            .preset(config_file.console_messages || 'basic')
    )
    .option(
        '--streamer_port <port>',
        'Sets the listening port for streamer connections.',
        config_file.streamer_port || '8888'
    )
    .option(
        '--player_port <port>',
        'Sets the listening port for player connections.',
        config_file.player_port || '80'
    )
    .option(
        '--sfu_port <port>',
        'Sets the listening port for SFU connections.',
        config_file.sfu_port || '8889'
    )
    .option(
        '--max_players <number>',
        'Sets the maximum number of subscribers per streamer. 0 = unlimited',
        config_file.max_players || '0'
    )
    .option('--serve', 'Enables the webserver on player_port.', config_file.serve || false)
    .option(
        '--http_root <path>',
        'Sets the path for the webserver root.',
        config_file.http_root || `${path.resolve(__dirname, '..', 'www')}`
    )
    .option(
        '--homepage <filename>',
        'The default html file to serve on the web server.',
        config_file.homepage || 'player.html'
    )
    .option('--https', 'Enables the webserver on https_port and enabling SSL', config_file.https || false)
    .addOption(
        new Option('--https_port <port>', 'Sets the listen port for the https server.')
            .implies({ https: true })
            .default(config_file.https_port || 443)
    )
    .option(
        '--ssl_key_path <path>',
        'Sets the path for the SSL key file.',
        config_file.ssl_key_path || 'certificates/client-key.pem'
    )
    .option(
        '--ssl_cert_path <path>',
        'Sets the path for the SSL certificate file.',
        config_file.ssl_cert_path || 'certificates/client-cert.pem'
    )
    .option(
        '--https_redirect',
        'Enables the redirection of connection attempts on http to https. If this is not set the webserver will only listen on https_port. Player websockets will still listen on player_port.',
        config_file.https_redirect || false
    )
    .option(
        '--rest_api',
        'Enables the rest API interface that can be accessed at <server_url>/api/api-definition',
        config_file.rest_api || false
    )
    .addOption(
        new Option(
            '--peer_options <json-string>',
            'Additional JSON data to send in peerConnectionOptions of the config message.'
        )
            .argParser(JSON.parse)
            .default(config_file.peer_options || '')
    )
    .addOption(
        new Option(
            '--peer_options_file <filename>',
            'Additional JSON data to send in peerConnectionOptions of the config message. This allows you to provide JSON data without having to deal with it on the command line.'
        ).default(config_file.peer_options_file || '')
    )
    .option(
        '--reverse-proxy',
        'Enables reverse proxy mode. This will trust the X-Forwarded-For header.',
        config_file.reverse_proxy || false
    )
    .addOption(
        new Option(
            '--reverse-proxy-num-proxies <number>',
            'Sets the number of proxies to trust. This is used to calculate the real client IP address.'
        )
            .implies({ reverse_proxy: true })
            .default(config_file.reverse_proxy_num_proxies || 1)
    )
    .option(
        '--log_config',
        'Will print the program configuration on startup.',
        config_file.log_config || false
    )
    .option(
        '--public_ip <ip-or-hostname>',
        'The public IP/hostname of the host running this signalling server. Use "auto" to detect via https://api.ipify.org (requires curl).',
        config_file.public_ip || 'localhost'
    )
    .option(
        '--public_port <port>',
        'The public port used to reach player connections (useful when the server is behind a port-mapping proxy). Defaults to player_port.',
        config_file.public_port || ''
    )
    .option(
        '--use_matchmaker',
        'Enables registering with a Cirrus-style Matchmaker over TCP.',
        config_file.use_matchmaker || false
    )
    .option(
        '--matchmaker_address <host>',
        'Hostname or IP of the Matchmaker.',
        config_file.matchmaker_address || ''
    )
    .option(
        '--matchmaker_port <port>',
        'TCP port the Matchmaker listens on.',
        config_file.matchmaker_port || '9999'
    )
    .option(
        '--streamer_id <id>',
        'Optional streamer/avatar identifier to send to the Matchmaker for routing.',
        config_file.streamer_id || ''
    )
    .option(
        '--matchmaker_retry_interval <seconds>',
        'Seconds to wait before reconnecting to the Matchmaker after disconnect.',
        config_file.matchmaker_retry_interval || '5'
    )
    .option(
        '--matchmaker_keep_alive_interval <seconds>',
        'Seconds between Matchmaker ping messages.',
        config_file.matchmaker_keep_alive_interval || '30'
    )
    .option(
        '--auth_token_secret <secret>',
        'If set, requires a HS256 JWT in the player websocket query string (default param "token").',
        config_file.auth_token_secret || ''
    )
    .option(
        '--auth_token_query_param <name>',
        'Query string parameter name to read the auth token from.',
        config_file.auth_token_query_param || 'token'
    )
    .option('--stdin', 'Allows stdin input while running.', config_file.stdin || false)
    .option(
        '--save',
        'After arguments are parsed the config.json is saved with whatever arguments were specified at launch.',
        config_file.save || false
    )
    .helpOption('-h, --help', 'Display this help text.')
    .allowUnknownOption() // ignore unknown options which will allow versions to be swapped out into existing scripts with maybe older/newer options
    .parse();

// parsed command line options
const cli_options: IProgramOptions = program.opts();
const options: IProgramOptions = { ...cli_options };

// save out new configuration (unless disabled)
if (options.save) {
    // dont save certain options
    const save_options = { ...options };
    delete save_options.no_config;
    delete save_options.config_file;
    delete save_options.save;

    // save out the config file with the current settings
    fs.writeFile(configArgsParser.config_file, beautify(save_options), (error: any) => {
        if (error) throw error;
    });
}

InitLogging({
    logDir: options.log_folder,
    logMessagesToConsole: options.console_messages,
    logLevelConsole: options.log_level_console,
    logLevelFile: options.log_level_file
});

// read the peer_options_file
if (options.peer_options_file) {
    if (!fs.existsSync(options.peer_options_file)) {
        Logger.error(`peer_options_file "${options.peer_options_file}" does not exist.`);
        throw Error(`Failed to find a peer options config file a file called ${options.peer_options_file}.`);
    }

    options.peer_options = JSON.parse(fs.readFileSync(options.peer_options_file, 'utf-8'));
} else if (options.peer_options) {
    Logger.warn(
        `The --peer_options cli flag has many issues with passing JSON data on the command line. It is recommended that you use --peer_options_file instead.`
    );
}

// eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
Logger.info(`${pjson.name} v${pjson.version} starting...`);
if (options.log_config) {
    Logger.info('Config:');
    for (const key in options) {
        Logger.info(`"${key}": ${JSON.stringify(options[key])}`);
    }
}

function base64UrlDecode(input: string): Buffer {
    const normalized = input.replace(/-/g, '+').replace(/_/g, '/');
    const padLen = (4 - (normalized.length % 4)) % 4;
    const padded = normalized + '='.repeat(padLen);
    return Buffer.from(padded, 'base64');
}

// Minimal HS256 JWT verification to avoid adding dependencies.
// Returns the decoded payload on success, throws on failure.
function verifyHs256Jwt(token: string, secret: string): any {
    const parts = token.split('.');
    if (parts.length !== 3) throw new Error('invalid jwt format');
    const [h, p, s] = parts;

    const header = JSON.parse(base64UrlDecode(h).toString('utf8'));
    if (!header || header.alg !== 'HS256') throw new Error('unsupported jwt alg');
    const payload = JSON.parse(base64UrlDecode(p).toString('utf8'));

    const expected = crypto.createHmac('sha256', secret).update(`${h}.${p}`).digest();
    const actual = base64UrlDecode(s);
    if (expected.length !== actual.length || !crypto.timingSafeEqual(expected, actual)) {
        throw new Error('invalid jwt signature');
    }

    const now = Math.floor(Date.now() / 1000);
    if (payload && typeof payload.exp === 'number' && payload.exp <= now) throw new Error('jwt expired');
    return payload;
}

function resolvePublicIp(publicIp: string): string {
    if (publicIp !== 'auto') return publicIp;
    try {
        const out = execFileSync('curl', ['-fsS', '--max-time', '3', 'https://api.ipify.org'], {
            encoding: 'utf8'
        }).trim();
        return out || '127.0.0.1';
    } catch (err) {
        Logger.warn(`Unable to auto-detect public IP (curl/ipify). Set --public_ip explicitly. Error: ${err}`);
        return '127.0.0.1';
    }
}

const app = express();
app.get('/healthz', (_req, res) => {
    res.status(200).send('ok');
});
if (options.reverse_proxy) {
    app.set('trust proxy', options.reverse_proxy_num_proxies);
}

const publicIp = resolvePublicIp(String(options.public_ip || 'localhost'));
const publicPort = parseInt(String(options.public_port || options.player_port), 10);

const serverOpts: IServerConfig = {
    streamerPort: options.streamer_port,
    playerPort: options.player_port,
    sfuPort: options.sfu_port,
    peerOptions: options.peer_options,
    maxSubscribers: options.max_players
};

if (options.auth_token_secret) {
    const secret = String(options.auth_token_secret);
    const qsParam = String(options.auth_token_query_param || 'token');

    serverOpts.playerWsOptions = {
        verifyClient: (info, done) => {
            try {
                const url = new URL(info.req.url || '/', 'http://127.0.0.1');
                const token = url.searchParams.get(qsParam) || '';
                if (!token) {
                    done(false, 401, 'Unauthorized');
                    return;
                }
                verifyHs256Jwt(token, secret);
                done(true);
            } catch (err) {
                Logger.warn(`Player websocket auth failed: ${err}`);
                done(false, 401, 'Unauthorized');
            }
        }
    };
}

if (options.serve) {
    const webserverOptions: IWebServerConfig = {
        httpPort: options.player_port,
        root: options.http_root,
        homepageFile: options.homepage
    };
    if (options.https) {
        webserverOptions.httpsPort = options.https_port;
        const sslKeyPath = path.join(__dirname, '..', options.ssl_key_path);
        const sslCertPath = path.join(__dirname, '..', options.ssl_cert_path);
        if (fs.existsSync(sslKeyPath) && fs.existsSync(sslCertPath)) {
            Logger.info(`Reading SSL key and cert. Key path: ${sslKeyPath} | Cert path: ${sslCertPath}`);
            webserverOptions.ssl_key = fs.readFileSync(sslKeyPath);
            webserverOptions.ssl_cert = fs.readFileSync(sslCertPath);
        } else {
            Logger.warn(`No SSL key/cert found. Key path: ${sslKeyPath} | Cert path: ${sslCertPath}`);
        }
        webserverOptions.https_redirect = options.https_redirect;
    }
    const webServer = new WebServer(app, webserverOptions);
    if (!options.https || webserverOptions.https_redirect) {
        serverOpts.httpServer = webServer.httpServer;
    }
    serverOpts.httpsServer = webServer.httpsServer;
}

const signallingServer = new SignallingServer(serverOpts);

if (options.use_matchmaker) {
    const getReady = () => signallingServer.streamerRegistry.streamers.some((s) => s.streaming);
    const getPlayerConnected = () => signallingServer.playerRegistry.count() > 0;

    const matchmaker = new MatchmakerClient(
        {
            matchmakerAddress: String(options.matchmaker_address || ''),
            matchmakerPort: parseInt(String(options.matchmaker_port || '9999'), 10),
            publicAddress: publicIp,
            publicPort: publicPort,
            publicHttps: Boolean(options.https),
            streamerId: String(options.streamer_id || '') || undefined,
            retryIntervalSeconds: parseInt(String(options.matchmaker_retry_interval || '5'), 10),
            keepAliveIntervalSeconds: parseInt(String(options.matchmaker_keep_alive_interval || '30'), 10)
        },
        { getReady, getPlayerConnected }
    );
    matchmaker.start();

    let lastReady = getReady();
    const updateReady = () => {
        const ready = getReady();
        if (ready === lastReady) return;
        lastReady = ready;
        if (ready) {
            matchmaker.sendStreamerConnected();
        } else {
            matchmaker.sendStreamerDisconnected();
        }
    };

    signallingServer.playerRegistry.on('added', () => matchmaker.sendClientConnected());
    signallingServer.playerRegistry.on('removed', () => matchmaker.sendClientDisconnected());

    signallingServer.streamerRegistry.on('added', (streamerId: string) => {
        const streamer = signallingServer.streamerRegistry.find(streamerId);
        if (!streamer) return;
        streamer.on('id_changed', () => updateReady());
        updateReady();
    });
    signallingServer.streamerRegistry.on('removed', () => updateReady());
    updateReady();
}

if (options.stdin) {
    initInputHandler(options, signallingServer);
}

if (options.rest_api) {
    void initialize({
        app,
        docsPath: '/api-definition',
        exposeApiDocs: true,
        apiDoc: './apidoc/api-definition-base.yml',
        paths: './dist/paths',
        dependencies: {
            signallingServer
        }
    });
}
