const fs = require('fs');
const path = require('path');

const DEFAULT_LOCK_PATH = path.join(__dirname, '..', 'data', 'factory_lock.json');

/**
 * Factory Lock — prevents overlapping automated operations.
 * 
 * - acquireFactoryLock(taskName, lockPath) → { acquired: boolean, lock?, existing?, reason? }
 *   If factory is locked (valid lock file), rejects safely.
 *   If not locked, creates factory_lock.json with taskName and startedAt.
 *   Handles invalid JSON as stale/corrupt (removes and allows).
 *   Uses atomic write {flag:'wx'} to avoid race.
 *
 * - releaseFactoryLock(lockPath) → removes lock, never throws, never leaves stale.
 *   Must be called in try/finally to guarantee release on success or failure.
 *
 * - readFactoryLock(lockPath) → parsed lock or null (if not exists or invalid)
 *
 * - isFactoryLocked(lockPath) → boolean
 *
 * Temp-path isolation: all functions accept optional lockPath, tests pass temp file.
 */

function readFactoryLock(lockPath = DEFAULT_LOCK_PATH) {
  try {
    if (!fs.existsSync(lockPath)) return null;
    const raw = fs.readFileSync(lockPath, 'utf8');
    const data = JSON.parse(raw);
    if (data && typeof data.taskName === 'string' && typeof data.startedAt === 'string') {
      return data;
    }
    return null;
  } catch (_) {
    return null;
  }
}

function isFactoryLocked(lockPath = DEFAULT_LOCK_PATH) {
  return readFactoryLock(lockPath) !== null;
}

function acquireFactoryLock(taskName, lockPath = DEFAULT_LOCK_PATH) {
  if (!taskName || typeof taskName !== 'string' || !taskName.trim()) {
    throw new Error('taskName required');
  }
  const name = taskName.trim();

  // Check existing lock — handle invalid JSON as stale
  if (fs.existsSync(lockPath)) {
    try {
      const raw = fs.readFileSync(lockPath, 'utf8');
      try {
        const existing = JSON.parse(raw);
        if (existing && typeof existing.taskName === 'string' && typeof existing.startedAt === 'string') {
          return { acquired: false, reason: 'factory is locked', existing };
        }
        // Valid JSON but missing required fields → treat as corrupt
        throw new Error('invalid lock structure');
      } catch (parseErr) {
        // Invalid JSON or structure → stale/corrupt, remove and allow
        try { fs.unlinkSync(lockPath); } catch (_) {}
        // fall through to creation
      }
    } catch (e) {
      // If we already handled and returned false, we would have returned
      // If we removed corrupt file, proceed to creation
      // If read itself failed, treat as not locked and try to create
      if (e && e.reason === 'factory is locked') throw e;
    }
    // After handling corrupt case, check if still exists (valid lock)
    if (fs.existsSync(lockPath)) {
      const existing = readFactoryLock(lockPath);
      if (existing) {
        return { acquired: false, reason: 'factory is locked', existing };
      }
    }
  }

  // Try atomic creation
  try {
    fs.mkdirSync(path.dirname(lockPath), { recursive: true });
    const payload = {
      taskName: name,
      startedAt: new Date().toISOString(),
      pid: process.pid
    };
    fs.writeFileSync(lockPath, JSON.stringify(payload, null, 2), { flag: 'wx' });
    return { acquired: true, lock: payload };
  } catch (e) {
    if (e.code === 'EEXIST') {
      const existing = readFactoryLock(lockPath);
      return { acquired: false, reason: 'factory is locked', existing: existing || undefined };
    }
    throw e;
  }
}

function releaseFactoryLock(lockPath = DEFAULT_LOCK_PATH) {
  try {
    if (fs.existsSync(lockPath)) {
      fs.unlinkSync(lockPath);
    }
  } catch (_) {
    // never throw, never leave stale
  }
}

module.exports = {
  acquireFactoryLock,
  releaseFactoryLock,
  readFactoryLock,
  isFactoryLocked,
  DEFAULT_LOCK_PATH,
};
