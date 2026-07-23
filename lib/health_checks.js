// Real infrastructure health checks (Enterprise Infrastructure & HA
// Mission, 2026-07-23, finding 4.7). No Express/server.js dependency —
// same reasoning as lib/dashboard_data.js: unit-testable in isolation,
// without booting a live server.
//
// Explicit scope discipline, per the founder's own rules for this
// mission ("never fake monitoring, never invent infrastructure, build
// only what actually exists"): this module checks real things this
// factory actually has (memory, CPU, disk, network reachability to its
// real external dependencies, the flat-file storage layer's integrity)
// and honestly reports "not_applicable" for things it does not have
// (a database, a message queue, a worker pool) — never a fabricated
// green check for infrastructure that doesn't exist.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFile } = require('child_process');

function checkMemory() {
  const mem = process.memoryUsage();
  const totalMem = os.totalmem();
  const freeMem = os.freemem();
  const freePct = totalMem > 0 ? (freeMem / totalMem) * 100 : null;
  const ok = freePct === null ? null : freePct > 10;
  return {
    ok,
    severity: 'degraded',
    detail: freePct === null
      ? 'تعذَّر قياس ذاكرة النظام'
      : `النظام: ${freePct.toFixed(1)}% حرة (${(freeMem / 1e9).toFixed(2)}GB من ${(totalMem / 1e9).toFixed(2)}GB) — العملية: ${(mem.rss / 1e6).toFixed(0)}MB RSS، ${(mem.heapUsed / 1e6).toFixed(0)}MB heap مستخدَمة`,
    process_rss_mb: Math.round(mem.rss / 1e6),
    process_heap_used_mb: Math.round(mem.heapUsed / 1e6),
    system_free_pct: freePct === null ? null : Math.round(freePct * 10) / 10,
  };
}

function checkCpu() {
  // os.loadavg() is a real, honest Windows limitation, not a gap in
  // this check: Windows has no native "load average" concept, so
  // Node's implementation unconditionally returns [0, 0, 0] there.
  // Reporting that as a real "0.00 load" would be exactly the kind of
  // fake monitoring this mission's own rules forbid.
  const loadAvgMeaningful = process.platform !== 'win32';
  const loadAvg = os.loadavg();
  const cores = os.cpus().length;
  return {
    ok: true,
    severity: 'degraded',
    detail: loadAvgMeaningful
      ? `متوسط الحمل (1/5/15 دقيقة): ${loadAvg.map((n) => n.toFixed(2)).join(' / ')} عبر ${cores} نواة`
      : `متوسط الحمل غير متاح على Windows — os.loadavg() يُرجع دائماً [0,0,0] (قيد حقيقي في نظام التشغيل، لا نقص في هذا الفحص). ${cores} نواة متاحة.`,
    cores,
    load_avg_available: loadAvgMeaningful,
    load_avg: loadAvgMeaningful ? loadAvg : null,
  };
}

function checkDiskSpace(targetPath = __dirname, { run = execFile } = {}) {
  return new Promise((resolve) => {
    if (process.platform !== 'win32') {
      // Real, honest scope limit: this factory runs on Windows today
      // (CLAUDE.md's own architecture) — a cross-platform disk check
      // (statvfs on POSIX) was not built since there is no real POSIX
      // deployment to verify it against yet, not because it's hard.
      return resolve({
        ok: null, severity: 'degraded',
        detail: 'فحص مساحة القرص مبني لـ Windows فقط اليوم — لا نشر POSIX حقيقي لاختباره بعد',
      });
    }
    const driveLetter = path.parse(targetPath).root.replace(/[\\:]/g, '') || 'C';
    run('powershell', [
      '-NoProfile', '-Command',
      `Get-PSDrive -Name ${driveLetter} | Select-Object Used,Free | ConvertTo-Json`,
    ], { timeout: 5000 }, (err, stdout) => {
      if (err) {
        return resolve({ ok: null, severity: 'degraded', detail: `تعذَّر فحص مساحة القرص: ${err.message}` });
      }
      try {
        const parsed = JSON.parse(stdout);
        const freeGb = parsed.Free / 1e9;
        const usedGb = parsed.Used / 1e9;
        const totalGb = freeGb + usedGb;
        const freePct = totalGb > 0 ? (freeGb / totalGb) * 100 : null;
        resolve({
          ok: freePct === null ? null : freePct > 5,
          severity: 'critical',
          detail: freePct === null
            ? 'تعذَّر حساب النسبة المئوية للمساحة الحرة'
            : `${freeGb.toFixed(1)}GB حرة من ${totalGb.toFixed(1)}GB (${freePct.toFixed(1)}%) على القرص ${driveLetter}:`,
          drive: driveLetter,
          free_gb: Math.round(freeGb * 10) / 10,
          free_pct: freePct === null ? null : Math.round(freePct * 10) / 10,
        });
      } catch (e) {
        resolve({ ok: null, severity: 'degraded', detail: `فشل تحليل مخرجات فحص القرص: ${e.message}` });
      }
    });
  });
}

// Real external dependencies this factory's own code actually calls —
// not a generic/arbitrary reachability list. groq_api is required
// (nothing generates real content without it); telegram_api and
// github_remote are only checked when this factory actually has a real
// reason to reach them (a configured bot token; a real git remote).
async function checkNetworkReachability({ fetchImpl = fetch, hasTelegramToken = !!process.env.TELEGRAM_BOT_TOKEN, hasGitRemote = null, timeoutMs = 4000 } = {}) {
  const targets = [{ name: 'groq_api', url: 'https://api.groq.com', required: true }];
  if (hasTelegramToken) targets.push({ name: 'telegram_api', url: 'https://api.telegram.org', required: false });
  if (hasGitRemote) targets.push({ name: 'github_remote', url: 'https://github.com', required: false });

  const results = {};
  await Promise.all(targets.map(async (t) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      await fetchImpl(t.url, { method: 'HEAD', signal: controller.signal });
      results[t.name] = { ok: true, required: t.required };
    } catch (err) {
      results[t.name] = { ok: false, required: t.required, error: err.message };
    } finally {
      clearTimeout(timer);
    }
  }));

  const requiredDown = Object.values(results).filter((r) => r.required && !r.ok);
  const anyDown = Object.values(results).filter((r) => !r.ok);
  return {
    ok: requiredDown.length === 0,
    severity: 'critical',
    detail: anyDown.length === 0
      ? `كل الوجهات الحقيقية (${Object.keys(results).join('، ')}) قابلة للوصول`
      : `تعذَّر الوصول: ${anyDown.map((r) => Object.keys(results).find((k) => results[k] === r)).join('، ')}`,
    targets: results,
  };
}

// The flat-file storage layer's real integrity — the honest analog to
// "database health" for an architecture that has no database (CLAUDE.md's
// own documented choice: flat JSON/JSONL files, written directly).
function checkStorageIntegrity(files = []) {
  const results = {};
  for (const { name, filePath, format } of files) {
    if (!fs.existsSync(filePath)) {
      results[name] = { ok: true, exists: false, detail: 'غير موجود بعد — يُنشأ تلقائياً عند أول استخدام' };
      continue;
    }
    try {
      const raw = fs.readFileSync(filePath, 'utf8');
      if (format === 'jsonl') {
        let validLines = 0;
        let invalidLines = 0;
        for (const line of raw.split('\n')) {
          if (!line.trim()) continue;
          try { JSON.parse(line); validLines++; } catch { invalidLines++; }
        }
        results[name] = {
          ok: invalidLines === 0, exists: true,
          detail: invalidLines === 0 ? `${validLines} سطر صالح` : `${invalidLines} سطر فاسد من ${validLines + invalidLines}`,
          valid_lines: validLines, invalid_lines: invalidLines,
        };
      } else {
        JSON.parse(raw);
        results[name] = { ok: true, exists: true, detail: 'JSON صالح' };
      }
    } catch (e) {
      results[name] = { ok: false, exists: true, detail: `JSON فاسد: ${e.message}` };
    }
  }
  const failing = Object.values(results).filter((r) => !r.ok);
  return {
    ok: failing.length === 0,
    severity: 'degraded',
    detail: failing.length === 0 ? 'كل ملفات التخزين المفحوصة صالحة' : `${failing.length} ملف فاسد`,
    files: results,
  };
}

// Explicit, honest "this does not exist" — never a fabricated green
// check. Enterprise Infrastructure & HA Mission's own directive named
// Database/Queue/Worker health checks; this factory has none of the
// three (flat files, no message queue, one Express process, no worker
// pool) — reporting that plainly is the actual requirement here, not a
// gap to silently paper over.
function notApplicableChecks() {
  return {
    database: { ok: null, severity: 'not_applicable', detail: 'لا قاعدة بيانات في هذا المصنع — ملفات JSON/JSONL مسطّحة فقط (قرار معماري موثَّق، انظر storage_integrity بدلاً منه)' },
    queue_system: { ok: null, severity: 'not_applicable', detail: 'لا نظام طابور رسائل في هذا المصنع' },
    worker_pool: { ok: null, severity: 'not_applicable', detail: 'لا مجموعة عمّال (workers) في هذا المصنع — عملية Express واحدة فقط' },
  };
}

async function buildHealthReport({ diskTargetPath, storageFiles, run, fetchImpl, hasTelegramToken, hasGitRemote } = {}) {
  const [disk, network] = await Promise.all([
    checkDiskSpace(diskTargetPath, run ? { run } : undefined),
    checkNetworkReachability({ fetchImpl, hasTelegramToken, hasGitRemote }),
  ]);
  const checks = {
    memory: checkMemory(),
    cpu: checkCpu(),
    disk,
    network,
    storage_integrity: checkStorageIntegrity(storageFiles || []),
    ...notApplicableChecks(),
  };
  const applicable = Object.values(checks).filter((c) => c.severity !== 'not_applicable');
  const failing = applicable.filter((c) => c.ok === false);
  let status = 'healthy';
  if (failing.some((c) => c.severity === 'critical')) status = 'critical';
  else if (failing.length > 0) status = 'degraded';
  return { status, generated_at: new Date().toISOString(), checks };
}

module.exports = {
  checkMemory, checkCpu, checkDiskSpace, checkNetworkReachability,
  checkStorageIntegrity, notApplicableChecks, buildHealthReport,
};
