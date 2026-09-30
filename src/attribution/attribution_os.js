const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const LOG_PATH = path.join(__dirname, '..', '..', 'data', 'attribution_log.jsonl');

// 12-event taxonomy per spec + legacy aliases for backward compatibility
const VALID_EVENT_TYPES = new Set([
  'view', 'click', 'trial_start', 'trial_request', 'output_generated', 'output_rejected',
  'rework_requested', 'rework_completed', 'feedback_submitted', 'repeat_usage',
  'payment_intent', 'payment_verified',
  // legacy aliases (still counted, mapped internally)
  'page_view', 'sale', 'download'
]);

// Map legacy to canonical for reporting
const LEGACY_MAP = {
  'page_view': 'view',
  'sale': 'payment_intent', // legacy sale is NOT verified payment, treat as intent
  'download': 'output_generated'
};

const VALID_SOURCES = new Set(['kdp', 'gumroad', 'direct', 'unknown', 'etsy', 'paddle', 'amazon', 'trial', 'notion', 'envato']);
const VALID_CLASSIFICATIONS = new Set(['REAL', 'TEST', 'MOCK', 'UNKNOWN']);
const SENSITIVE_KEYS = new Set(['password', 'passwd', 'pwd', 'secret', 'token', 'auth', 'credentials', 'payment_credentials', 'card', 'cvv', 'ssn']);
const MAX_METADATA_BYTES = 2048;
const MAX_PRODUCT_LEN = 200;

function generateEventId() {
  return 'evt_' + crypto.randomBytes(8).toString('hex');
}

function hashIdentifier(value) {
  if (!value) return null;
  return crypto.createHash('sha256').update(String(value)).digest('hex').slice(0, 16);
}

function sanitizeMetadata(metadata) {
  if (metadata == null || typeof metadata !== 'object' || Array.isArray(metadata)) return {};
  const out = {};
  const str = JSON.stringify(metadata);
  if (Buffer.byteLength(str, 'utf8') > MAX_METADATA_BYTES) {
    // Oversized: keep as many safe keys as fit, skip overly large single entries
    let size = 0;
    let truncated = false;
    for (const [k, v] of Object.entries(metadata)) {
      if (SENSITIVE_KEYS.has(k.toLowerCase())) { truncated = true; continue; }
      const entry = JSON.stringify({ [k]: v });
      if (entry.length > MAX_METADATA_BYTES) { truncated = true; continue; }
      if (size + entry.length > MAX_METADATA_BYTES) { truncated = true; continue; }
      if (typeof v === 'string' && (v.includes('..') || v.includes('/etc/passwd') || v.includes('\\'))) {
        out[k] = '[filtered]';
      } else {
        out[k] = typeof v === 'string' ? v.slice(0, 500) : v;
      }
      size += entry.length;
    }
    if (truncated || size < Buffer.byteLength(str, 'utf8')) out._truncated = true;
    return out;
  }
  for (const [k, v] of Object.entries(metadata)) {
    if (SENSITIVE_KEYS.has(k.toLowerCase())) continue;
    if (typeof v === 'string' && v.length > 500) {
      out[k] = v.slice(0, 500);
    } else if (typeof v === 'string' && (v.includes('..') || v.includes('/etc/passwd'))) {
      out[k] = '[filtered]';
    } else {
      out[k] = v;
    }
  }
  return out;
}

function isValidTimestamp(ts) {
  if (typeof ts !== 'number' || !Number.isFinite(ts)) return false;
  // Must be plausible: between 2020 and 2030
  return ts > 1577836800000 && ts < 1893456000000;
}

class AttributionOS {
  constructor(logPath = LOG_PATH) {
    this.logPath = logPath;
    this.events = [];
    this.failedEvents = []; // in-memory count of failed validations during runtime
    this._lastMtime = 0;
    this._cachedReport = null;
    this._loadFromDisk();
  }

  _loadFromDisk() {
    try {
      if (!fs.existsSync(this.logPath)) return;
      const stat = fs.statSync(this.logPath);
      this._lastMtime = stat.mtimeMs;
      const raw = fs.readFileSync(this.logPath, 'utf8');
      this.events = [];
      for (const line of raw.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const evt = JSON.parse(trimmed);
          // Handle legacy: old events have type/source/product
          // New events have eventType, source, product, data_classification, etc.
          // We keep any event that has at least an eventType or type
          const hasType = typeof evt.eventType === 'string' || typeof evt.type === 'string';
          if (!hasType) continue; // corrupted event: skip
          // Normalize legacy to new shape for in-memory, but keep original for file
          // For reporting, we will handle both
          this.events.push(evt);
        } catch (_) {
          // corrupted JSONL: keep count but don't crash
          this.failedEvents.push({ reason: 'corrupted_jsonl', line: trimmed.slice(0,100) });
        }
      }
    } catch (_) {
      // disk read failure must never crash OS
    }
  }

  _reloadIfNeeded() {
    try {
      if (!fs.existsSync(this.logPath)) return;
      const stat = fs.statSync(this.logPath);
      if (stat.mtimeMs !== this._lastMtime) {
        this._loadFromDisk();
        this._cachedReport = null;
      }
    } catch (_) {}
  }

  _persist(event) {
    try {
      fs.mkdirSync(path.dirname(this.logPath), { recursive: true });
      fs.appendFileSync(this.logPath, JSON.stringify(event) + '\n', 'utf8');
      // update cache invalidation
      try { this._lastMtime = fs.statSync(this.logPath).mtimeMs; } catch (_) {}
      this._cachedReport = null;
    } catch (_) {
      // persist failure must never block tracking
    }
  }

  _classify(event, context = {}) {
    // System-determined, never trust user-provided data_classification
    const rawType = String(event.eventType || event.type || '').toLowerCase().trim();
    const canonical = LEGACY_MAP[rawType] || rawType;
    const src = String(event.source || '').toLowerCase();

    // Trial integration: trial events are always TEST
    if (canonical.startsWith('trial_') || src === 'trial' || event.metadata?.trial === true || context.isTrial) {
      return 'TEST';
    }
    // Payment verified: only REAL if independently_verified
    if (canonical === 'payment_verified') {
      if (event.metadata && event.metadata.independently_verified === true) {
        return 'REAL';
      }
      // Even verified payment from public POST is not trusted as REAL unless system verified
      // Treat as MOCK (payment intent that is claimed verified but not independently verified)
      return 'MOCK';
    }
    if (canonical === 'payment_intent') {
      return 'MOCK'; // not revenue
    }
    if (VALID_EVENT_TYPES.has(canonical) || VALID_EVENT_TYPES.has(rawType)) {
      // For valid non-trial, non-payment events, treat as REAL activity (but not financial truth)
      // However if context indicates test (e.g., X-Test header), then TEST
      if (context.isTest) return 'TEST';
      return 'REAL';
    }
    return 'UNKNOWN';
  }

  _normalize(event, context = {}) {
    const e = event || {};

    // eventType handling: support both type and eventType, map legacy
    let rawType = String(e.eventType || e.type || 'view').toLowerCase().trim();
    let canonical = LEGACY_MAP[rawType] || rawType;
    let eventType = canonical;
    let isUnknownType = false;
    if (!VALID_EVENT_TYPES.has(canonical) && !VALID_EVENT_TYPES.has(rawType)) {
      eventType = 'UNKNOWN';
      isUnknownType = true;
    } else {
      // If legacy, keep canonical
      eventType = canonical;
    }

    let source = String(e.source || 'unknown').toLowerCase().trim();
    if (!VALID_SOURCES.has(source)) source = 'unknown';

    // campaign if found
    let campaign = null;
    if (e.campaign) campaign = String(e.campaign).slice(0,100);
    else if (e.metadata && e.metadata.campaign) campaign = String(e.metadata.campaign).slice(0,100);
    else if (e.metadata && e.metadata.utm_campaign) campaign = String(e.metadata.utm_campaign).slice(0,100);

    // market: must be from trusted source (event.market if provided via query param market), else UNKNOWN
    // Never invent from accept-language
    let market = 'UNKNOWN';
    if (e.market && typeof e.market === 'string' && e.market.trim().length >= 2) {
      const m = e.market.trim().slice(0,50);
      // basic validation: alphanumeric + _-
      if (/^[a-zA-Z0-9_\-]+$/.test(m)) market = m;
    }
    // language_signal: from accept-language or event.language, but only as signal
    let language_signal = 'UNKNOWN';
    if (e.language_signal) language_signal = String(e.language_signal).slice(0,20);
    else if (e.metadata && e.metadata.language_signal) language_signal = String(e.metadata.language_signal).slice(0,20);
    else if (context.language_signal) language_signal = String(context.language_signal).slice(0,20);

    let product = String(e.product || e.production_id || e.productionId || 'unknown').trim();
    if (!product) product = 'unknown';
    product = product.slice(0, MAX_PRODUCT_LEN);

    let production_id = e.production_id || e.productionId || e.productId || null;
    if (production_id) production_id = String(production_id).slice(0,100);

    let timestamp = e.timestamp;
    if (!isValidTimestamp(timestamp)) {
      // Try eventTimestamp or timestamp as ISO string
      if (typeof e.timestamp === 'string') {
        const parsed = Date.parse(e.timestamp);
        if (!isNaN(parsed)) timestamp = parsed;
        else timestamp = Date.now();
      } else {
        timestamp = Date.now();
      }
    }

    let metadata = sanitizeMetadata(e.metadata);

    // Privacy: hash IP if present, never store raw
    let anonymized_ip = null;
    if (e.ip || e.metadata?.ip || context.ip) {
      const rawIp = e.ip || e.metadata?.ip || context.ip;
      anonymized_ip = hashIdentifier(rawIp);
      // Ensure metadata doesn't contain raw ip
      if (metadata.ip) delete metadata.ip;
    }

    // Data classification is system-determined, ignore user input
    const data_classification = this._classify({ eventType, source, metadata, language_signal, market }, context);

    // eventId
    let eventId = e.eventId || e.event_id;
    if (!eventId || typeof eventId !== 'string') {
      eventId = generateEventId();
    } else {
      eventId = String(eventId).slice(0,50);
    }

    const normalized = {
      timestamp,
      eventId,
      eventType,
      source,
      campaign,
      market,
      language_signal,
      product,
      production_id,
      data_classification,
      metadata,
      anonymized_ip,
      _rawType: rawType,
      _isUnknownType: isUnknownType
    };

    // Preserve original type for backward compat if needed
    if (e.type && e.type !== eventType) {
      normalized.legacy_type = e.type;
    }

    return normalized;
  }

  // تسجيل كل حدث
  track(event, context = {}) {
    // Validate eventType
    if (!event || typeof event !== 'object') {
      this.failedEvents.push({ reason: 'missing_event', at: Date.now() });
      throw new Error('event object required');
    }

    // Check oversized payload before normalize
    try {
      const size = Buffer.byteLength(JSON.stringify(event), 'utf8');
      if (size > 8192) {
        this.failedEvents.push({ reason: 'oversized_payload', size, at: Date.now() });
        throw new Error('payload too large');
      }
    } catch (err) {
      if (err.message === 'payload too large') throw err;
    }

    // Detect sensitive data in raw event before sanitization (for logging failed)
    const rawStr = JSON.stringify(event).toLowerCase();
    for (const k of SENSITIVE_KEYS) {
      if (rawStr.includes(`"${k}"`)) {
        // We will sanitize, but count as warning
        // Do not reject, just sanitize
        break;
      }
    }

    const normalized = this._normalize(event, context);

    // If unknown type, still log but mark UNKNOWN (per spec: reject or classify UNKNOWN)
    // We will log it as UNKNOWN rather than throwing, so Learning Loop can see unknown events

    this.events.push(normalized);
    this._persist(normalized);
    return normalized;
  }

  // تلخيص المصادر
  getSummary() {
    this._reloadIfNeeded();
    const summary = {};
    for (const e of this.events) {
      const src = (e.source || 'unknown').toLowerCase();
      if (!summary[src]) summary[src] = { count: 0, revenue: 0 };
      summary[src].count += 1;
      // Financial truth: revenue only if data_classification REAL and eventType payment_verified independently_verified
      // Never count MOCK/TEST as revenue
      if (e.data_classification === 'REAL' && e.eventType === 'payment_verified') {
        const rev = e.metadata?.revenue ?? e.metadata?.amount ?? e.metadata?.price ?? 0;
        const num = Number(rev);
        if (Number.isFinite(num) && num > 0) summary[src].revenue += num;
      }
    }
    return summary;
  }

  // أفضل مصدر أداءً
  getTopSource() {
    const summary = this.getSummary();
    let top = null;
    let maxCount = -1;
    let maxRev = -1;
    for (const [src, data] of Object.entries(summary)) {
      if (data.count > maxCount || (data.count === maxCount && data.revenue > maxRev)) {
        top = src;
        maxCount = data.count;
        maxRev = data.revenue;
      }
    }
    if (top === null) return null;
    return { source: top, count: maxCount, revenue: maxRev };
  }

  // تقرير يومي
  getDailyReport() {
    this._reloadIfNeeded();
    const daily = {};
    for (const e of this.events) {
      const d = new Date(e.timestamp);
      const day = isNaN(d.getTime()) ? new Date().toISOString().slice(0,10) : d.toISOString().slice(0, 10);
      if (!daily[day]) daily[day] = { date: day, total: 0, sources: {} };
      daily[day].total += 1;
      const src = (e.source || 'unknown').toLowerCase();
      if (!daily[day].sources[src]) daily[day].sources[src] = { count: 0, revenue: 0 };
      daily[day].sources[src].count += 1;
      if (e.data_classification === 'REAL' && e.eventType === 'payment_verified') {
        const rev = e.metadata?.revenue ?? e.metadata?.amount ?? 0;
        const num = Number(rev);
        if (Number.isFinite(num) && num > 0) daily[day].sources[src].revenue += num;
      }
    }
    return Object.values(daily).sort((a, b) => a.date.localeCompare(b.date));
  }

  // Enhanced report per spec section 9
  getReport() {
    this._reloadIfNeeded();
    if (this._cachedReport) return this._cachedReport;

    const total_events = this.events.length;
    const byType = {};
    const bySource = {};
    const byMarket = {};
    const byLanguage = {};
    let trialActivity = 0;
    let repeatUsage = 0;
    let paymentIntent = 0;
    let paymentVerified = 0;
    let verifiedPaymentReal = 0;
    let unknownEvents = 0;
    let failedEvents = this.failedEvents.length;

    // Count corrupted lines that were skipped during load (already in failedEvents)
    // Also count unknown classifications
    for (const e of this.events) {
      const type = e.eventType || e.type || 'unknown';
      byType[type] = (byType[type] || 0) + 1;

      const src = (e.source || 'unknown').toLowerCase();
      bySource[src] = (bySource[src] || 0) + 1;

      const m = e.market || 'UNKNOWN';
      byMarket[m] = (byMarket[m] || 0) + 1;

      const lang = e.language_signal || 'UNKNOWN';
      byLanguage[lang] = (byLanguage[lang] || 0) + 1;

      if (e.data_classification === 'TEST' || (e.source && e.source.toLowerCase() === 'trial') || (e.eventType && e.eventType.startsWith('trial_'))) {
        trialActivity += 1;
      }
      if (e.eventType === 'repeat_usage') repeatUsage += 1;
      if (e.eventType === 'payment_intent') paymentIntent += 1;
      if (e.eventType === 'payment_verified') {
        paymentVerified += 1;
        if (e.data_classification === 'REAL') verifiedPaymentReal += 1;
      }
      if (e.data_classification === 'UNKNOWN' || e._isUnknownType) unknownEvents += 1;
    }

    // Learning Loop insights (analytical, not financial truth)
    const insights = [];
    const views = (byType['view'] || 0) + (byType['page_view'] || 0);
    const clicks = byType['click'] || 0;
    const requests = (byType['trial_request'] || 0);
    const outputs = (byType['output_generated'] || 0);
    const feedbacks = (byType['feedback_submitted'] || 0);
    const reworks = (byType['rework_requested'] || 0);

    if (views > 10 && requests < 2) {
      insights.push({ pattern: 'High Views + Low Requests = Possible Offer / UX Problem', views, requests, severity: 'warning' });
    }
    if (views < 5 && feedbacks > 2) {
      insights.push({ pattern: 'Low Views + High Satisfaction = Distribution Problem', views, feedbacks, severity: 'info' });
    }
    if (requests > 5 && outputs < 2) {
      insights.push({ pattern: 'High Requests + Low Quality = Production Problem', requests, outputs, severity: 'warning' });
    }
    if (repeatUsage > 3 && paymentIntent > 2) {
      insights.push({ pattern: 'High Repeat Usage + High Payment Intent = Strong Commercial Signal', repeatUsage, paymentIntent, severity: 'positive' });
    }

    const summary = this.getSummary();
    const top_source = this.getTopSource();
    const daily = this.getDailyReport();

    // Financial truth separation
    const financialTruth = {
      verified_revenue_events: verifiedPaymentReal,
      provisional_revenue_events: paymentIntent, // payment_intent is NOT revenue
      total_payment_intent_events: paymentIntent,
      total_payment_verified_events: paymentVerified,
      note: 'Financial truth: only REAL payment_verified with independently_verified=true counts as revenue. payment_intent is MOCK. See data_classification.'
    };

    const activity = {
      total_events,
      events_by_type: byType,
      events_by_source: bySource,
      events_by_market: byMarket,
      events_by_language_signal: byLanguage,
      trial_activity: trialActivity,
      repeat_usage: repeatUsage,
      unknown_events: unknownEvents,
      failed_events: failedEvents
    };

    const report = {
      total_events,
      summary,
      top_source,
      daily,
      activity,
      financial_truth: financialTruth,
      trial_activity: trialActivity,
      repeat_usage: repeatUsage,
      payment_intent: paymentIntent,
      payment_verified: paymentVerified,
      verified_payment_events: verifiedPaymentReal,
      unknown_events: unknownEvents,
      failed_events: failedEvents,
      events_by_type: byType,
      events_by_source: bySource,
      events_by_market: byMarket,
      events_by_language_signal: byLanguage,
      insights,
      generated_at: new Date().toISOString(),
    };

    this._cachedReport = report;
    return report;
  }

  // for testing: clear in-memory only (never deletes disk unless explicit)
  _clearMemory() {
    this.events = [];
    this.failedEvents = [];
    this._cachedReport = null;
  }

  // for testing: clear disk and memory
  _clearAllForTest() {
    this.events = [];
    this.failedEvents = [];
    this._cachedReport = null;
    try { fs.unlinkSync(this.logPath); } catch (_) {}
    this._lastMtime = 0;
  }
}

module.exports = AttributionOS;
