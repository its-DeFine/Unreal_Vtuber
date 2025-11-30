const express = require("express");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const PORT = process.env.RECORDER_CTRL_PORT || 8889;
const RECORDINGS_DIR = process.env.RECORDER_OUTPUT_DIR || "/recordings";
const SIGNALING_URL = process.env.RECORDER_SIGNALING_URL || "ws://127.0.0.1:80";
const DEFAULT_STREAMER = process.env.RECORDER_STREAMER_ID || null;
const PY_RECORDER = process.env.PY_RECORDER_PATH || "/opt/embody/recorder/gs_webrtc_recorder.py";
const RECORDER_API_TOKEN = process.env.RECORDINGS_API_TOKEN || null;
const ALLOWED_IPS = (process.env.VTUBER_ALLOWED_ADDRESSES || process.env.RECORDINGS_ALLOWED_IPS || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

fs.mkdirSync(RECORDINGS_DIR, { recursive: true });

const app = express();
app.use(express.json());
app.set("trust proxy", true);

let state = {
  proc: null,
  label: null,
  streamerId: null,
  startedAt: null,
  mkv: null,
};

function clientIp(req) {
  if (!req.ip) return null;
  if (req.ip.startsWith("::ffff:")) return req.ip.replace("::ffff:", "");
  return req.ip;
}

function ensureAuth(req, res, next) {
  const ip = clientIp(req);
  if (ALLOWED_IPS.length > 0 && (!ip || !ALLOWED_IPS.includes(ip))) {
    return res.status(403).json({ error: "Forbidden (IP)" });
  }
  if (RECORDER_API_TOKEN) {
    const hdr = req.headers["authorization"] || "";
    const token = hdr.toLowerCase().startsWith("bearer ") ? hdr.slice(7).trim() : hdr.trim();
    if (!token) return res.status(401).json({ error: "Missing token" });
    if (token !== RECORDER_API_TOKEN) return res.status(403).json({ error: "Forbidden (token)" });
  }
  return next();
}

app.get("/recordings/status", ensureAuth, (_req, res) => {
  return res.json({
    active: !!state.proc,
    pid: state.proc ? state.proc.pid : null,
    label: state.label,
    streamerId: state.streamerId,
    startedAt: state.startedAt,
    output: state.mkv,
  });
});

app.post("/recordings/start", ensureAuth, (req, res) => {
  if (state.proc) {
    return res.status(409).json({ error: "Recorder already running", pid: state.proc.pid });
  }
  const label = req.body?.label || "capture";
  const duration = req.body?.duration ? Number(req.body.duration) : null;
  const streamerId = req.body?.streamer_id || DEFAULT_STREAMER;

  const args = [PY_RECORDER, "--label", label];
  if (duration) args.push("--duration", String(duration));
  if (streamerId) args.push("--streamer-id", streamerId);

  const env = { ...process.env };
  env.RECORDER_SIGNALING_URL = env.RECORDER_SIGNALING_URL || SIGNALING_URL;
  env.RECORDER_OUTPUT_DIR = env.RECORDER_OUTPUT_DIR || RECORDINGS_DIR;

  const proc = spawn("python3", args, { env });
  state.proc = proc;
  state.label = label;
  state.streamerId = streamerId;
  state.startedAt = new Date().toISOString();
  const baseTs = Math.floor(Date.now() / 1000);
  state.mkv = path.join(RECORDINGS_DIR, `${label}_${baseTs}.mkv`);

  proc.stdout.on("data", (d) => console.log("[pyrec]", d.toString().trim()));
  proc.stderr.on("data", (d) => console.warn("[pyrec err]", d.toString().trim()));
  proc.on("close", (code) => {
    console.log("[pyrec] exited", code);
    state = { proc: null, label: null, streamerId: null, startedAt: null, mkv: null };
  });

  return res.json({
    started: true,
    pid: proc.pid,
    label,
    streamerId,
    duration,
    output: state.mkv,
  });
});

app.post("/recordings/stop", ensureAuth, (_req, res) => {
  if (!state.proc) return res.status(409).json({ error: "No recorder running" });
  try {
    state.proc.kill("SIGINT");
  } catch (_) {}
  state = { proc: null, label: null, streamerId: null, startedAt: null, mkv: null };
  return res.json({ stopped: true });
});

app.get("/", (_req, res) => res.json({ service: "gs-recorder-control", active: !!state.proc }));

app.listen(PORT, () => {
  console.log(`Recorder control listening on ${PORT}`);
});
