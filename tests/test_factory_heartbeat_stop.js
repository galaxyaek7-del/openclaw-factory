// factory_loop.js kill switch + heartbeat (TASKS.md items 4-5, 2026-11-18).
// Real finding: no STOP file was honoured by the loop itself, and there was no
// machine-readable heartbeat beyond the log's mtime. These tests prove the
// loop refuses to start a tick while STOP exists, exits through the clean-stop
// path, and leaves real liveness evidence. All paths are temp files; the real
// factory_loop.log / data/heartbeat.json a running supervisor owns are never
// touched.
//
//   node --test tests/test_factory_heartbeat_stop.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const LOG = path.join(os.tmpdir(), `test_hb_log_${process.pid}_${Date.now()}.log`);
const HEARTBEAT = path.join(os.tmpdir(), `test_hb_${process.pid}_${Date.now()}.json`);
process.env.FACTORY_LOOP_LOG_PATH = LOG;
process.env.FACTORY_HEARTBEAT_PATH = HEARTBEAT;

const fl = require('../factory_loop.js');

function tmp(name) {
  return path.join(os.tmpdir(), `test_stop_${name}_${process.pid}_${Date.now()}_${Math.random().toString(36).slice(2)}`);
}

test('stopRequested is false without a file and true once STOP exists', () => {
  const stop = tmp('flag');
  try {
    assert.equal(fl.stopRequested(stop), false);
    fs.writeFileSync(stop, '');
    assert.equal(fl.stopRequested(stop), true);
  } finally {
    try { fs.unlinkSync(stop); } catch { /* absent is fine */ }
  }
});

test('writeHeartbeat writes parseable real liveness fields', () => {
  const file = tmp('hb') + '.json';
  try {
    assert.equal(fl.writeHeartbeat(new Date('2026-11-18T12:00:00.000Z'), { phase: 'start' }, file), true);
    const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
    assert.equal(parsed.at, '2026-11-18T12:00:00.000Z');
    assert.equal(parsed.pid, process.pid);
    assert.equal(parsed.phase, 'start');
    assert.equal(typeof parsed.interval_ms, 'number');
  } finally {
    try { fs.unlinkSync(file); } catch { /* absent is fine */ }
  }
});

test('safeTick does not run the tick while STOP exists and signals a stop', async () => {
  const stop = tmp('stop');
  let ticked = false;
  try {
    fs.writeFileSync(stop, '');
    const result = await fl.safeTick(async () => { ticked = true; }, { stopPath: stop });
    assert.deepEqual(result, { stopped: true });
    assert.equal(ticked, false, 'no tick work may start once STOP is present');
  } finally {
    try { fs.unlinkSync(stop); } catch { /* absent is fine */ }
  }
});

test('safeTick runs the tick and writes a heartbeat when no STOP exists', async () => {
  const stop = tmp('nostop');
  try {
    try { fs.unlinkSync(HEARTBEAT); } catch { /* absent is fine */ }
    let ran = 0;
    const result = await fl.safeTick(async () => { ran += 1; }, { stopPath: stop });
    assert.equal(result, undefined);
    assert.equal(ran, 1);
    const parsed = JSON.parse(fs.readFileSync(HEARTBEAT, 'utf8'));
    assert.equal(parsed.phase, 'end');
  } finally {
    try { fs.unlinkSync(HEARTBEAT); } catch { /* absent is fine */ }
  }
});

test('cleanup temp log', () => {
  try { fs.unlinkSync(LOG); } catch { /* absent is fine */ }
});
