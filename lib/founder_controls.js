// Local founder controls for the factory: the STOP kill switch and the
// production pause flag. Pure file operations only — no network, no
// publishing, no money, no new channel. The server exposes these behind the
// existing mission-control session; this module stays dependency-free so it
// can be tested without booting the server.
//
// Paths mirror the consumers: factory_loop.js reads FACTORY_STOP_PATH (default
// <repo>/STOP), scripts/supervisor.js reads SUPERVISOR_STOP_FILE (same file),
// and server.js's production control reads data/production_control.json.

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');

function resolve(opts = {}) {
  return {
    stop: opts.stop || process.env.FACTORY_STOP_PATH || path.join(ROOT, 'STOP'),
    heartbeat: opts.heartbeat || process.env.FACTORY_HEARTBEAT_PATH || path.join(ROOT, 'data', 'heartbeat.json'),
    production: opts.production || process.env.PRODUCTION_CONTROL_PATH || path.join(ROOT, 'data', 'production_control.json'),
  };
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
}

function heartbeatStatus(file) {
  try {
    const st = fs.statSync(file);
    const data = readJson(file) || {};
    return {
      present: true,
      age_seconds: Math.max(0, Math.round((Date.now() - st.mtimeMs) / 1000)),
      at: typeof data.at === 'string' ? data.at : null,
      pid: Number.isInteger(data.pid) ? data.pid : null,
      phase: typeof data.phase === 'string' ? data.phase : null,
    };
  } catch {
    return { present: false, age_seconds: null, at: null, pid: null, phase: null };
  }
}

function readProduction(file) {
  const d = readJson(file);
  if (!d || typeof d !== 'object') return { paused: false, changed_at: null, reason: null };
  return {
    paused: d.paused === true,
    changed_at: typeof d.changed_at === 'string' ? d.changed_at : null,
    reason: typeof d.reason === 'string' ? d.reason : null,
  };
}

function status(opts = {}) {
  const p = resolve(opts);
  return {
    generated_at: new Date().toISOString(),
    stop: { requested: fs.existsSync(p.stop), path: p.stop },
    production: readProduction(p.production),
    heartbeat: heartbeatStatus(p.heartbeat),
    gates: {
      live_publish: process.env.FACTORY_LIVE_PUBLISH === 'true',
      note: 'Publishing, money and new channels remain founder gates: no button here performs them.',
    },
  };
}

function requestStop(opts = {}) {
  const p = resolve(opts);
  fs.writeFileSync(p.stop, `STOP requested ${new Date().toISOString()} via founder controls\n`, 'utf8');
  return status(opts);
}

function clearStop(opts = {}) {
  const p = resolve(opts);
  try {
    fs.rmSync(p.stop, { force: true });
  } catch {
    // already absent: the desired state
  }
  return status(opts);
}

function setProductionPaused(paused, reason, opts = {}) {
  const p = resolve(opts);
  const state = {
    paused: paused === true,
    changed_at: new Date().toISOString(),
    reason: paused === true ? (reason || 'paused via founder controls') : null,
  };
  fs.mkdirSync(path.dirname(p.production), { recursive: true });
  fs.writeFileSync(p.production, JSON.stringify(state, null, 2), 'utf8');
  return status(opts);
}

module.exports = { status, requestStop, clearStop, setProductionPaused, resolve, readProduction };
