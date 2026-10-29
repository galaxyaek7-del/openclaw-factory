// Galaxy Forge — commercial funnel for the CEO dashboard (2026-10-29).
// (Distinct from commercial_truth.py, whose pure functions reconcile sales
// data handed to them; this module reads the files the factory writes.)
//
// Adds three things the read model in lib/ceo_command_center.js did not
// show, reusing its revenue and distribution results instead of recomputing
// them:
//   funnel      the fifteen commercial states, from "product created" to
//               "payout confirmed", each with its value, evidence class and
//               source. A state with no source is UNKNOWN, never zero.
//   delivery    what a buyer actually receives, from the latest read-only
//               Gumroad delivery audit (scripts/gumroad_delivery_audit.py).
//   experiments every commercial experiment and its real status
//               (commercial_experiments.py ledger).
// and a diagnosis naming which funnel case (A..F) the evidence supports.
//
// Pure file reads: no network, no child process, no secret.
const fs = require('fs');
const path = require('path');
const jsonl = require('./jsonl');

function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (_) { return null; }
}

function mtimeIso(p) {
  try { return fs.statSync(p).mtime.toISOString(); } catch (_) { return null; }
}

function stage(n, name, value, kind, source, note) {
  return { n, name, value, kind, source: source || null, note: note || null };
}

// Issues a buyer would notice. ZIP_CONTENTS_UNVERIFIED only means the API
// cannot see inside an archive; it is reported separately, not as a defect.
const BUYER_ISSUES = ['PUBLISHED_WITHOUT_DELIVERABLE', 'PROMISES_SPREADSHEET_NOT_ATTACHED',
  'PROMISES_MORE_FILES_THAN_ATTACHED', 'PREVIEW_FILE_DELIVERED', 'THIN_DELIVERABLE'];

function latestDeliveryAudit(root) {
  const dir = path.join(root, 'reports');
  let names = [];
  try { names = fs.readdirSync(dir).filter(n => /^GUMROAD_DELIVERY_AUDIT_\d{4}-\d{2}-\d{2}\.json$/.test(n)).sort(); } catch (_) { /* none */ }
  if (!names.length) return null;
  const file = path.join('reports', names[names.length - 1]);
  return { file, data: readJson(path.join(root, file)) };
}

function delivery(root, now) {
  const audit = latestDeliveryAudit(root);
  if (!audit || !audit.data) {
    return { kind: 'UNKNOWN', source: null, note: 'no delivery audit report; run scripts/gumroad_delivery_audit.py' };
  }
  const d = audit.data;
  const rows = (d.rows || []).filter(r => r.published);
  const flagged = rows
    .map(r => ({ slug: r.slug, name: r.name, price_usd: r.price_usd,
      issues: (r.issues || []).filter(i => BUYER_ISSUES.includes(i)) }))
    .filter(r => r.issues.length)
    .sort((a, b) => (b.price_usd || 0) - (a.price_usd || 0));
  const ageH = d.generated_at ? (now - new Date(d.generated_at)) / 3.6e6 : null;
  return {
    kind: 'OBSERVED',
    source: { file: audit.file, updated_at: d.generated_at || null },
    stale: ageH == null || ageH > 24 * 8,
    published: rows.length,
    with_buyer_issue: flagged.length,
    serious: flagged.filter(r => r.issues.some(i => i !== 'THIN_DELIVERABLE')).length,
    archive_contents_unverified: rows.filter(r => (r.issues || []).includes('ZIP_CONTENTS_UNVERIFIED')).length,
    issue_counts: d.issue_counts || {},
    flagged,
    note: 'GET-only audit of the files attached to each live listing; a flagged listing promises more than a buyer receives',
  };
}

function experiments(root) {
  const file = path.join('data', 'commercial_experiments.jsonl');
  const p = path.join(root, file);
  const rows = fs.existsSync(p) ? jsonl.readJsonlEntries(p) : [];
  const byId = new Map();
  for (const r of rows) {
    if (!r || !r.experiment_id) continue;
    const e = byId.get(r.experiment_id) || { id: r.experiment_id, observations: 0 };
    if (r.record_type === 'experiment_definition') {
      Object.assign(e, { type: r.experiment_type, hypothesis: r.hypothesis, metric: r.metric,
        status: r.status, created_at: r.created_at });
    } else if (r.record_type === 'status_update') {
      Object.assign(e, { status: r.status, decision: r.decision, reason: r.reason, updated_at: r.updated_at });
    } else if (r.record_type === 'observation') {
      e.observations += 1;
    }
    byId.set(r.experiment_id, e);
  }
  const list = [...byId.values()].filter(e => e.status);
  const count = s => list.filter(e => e.status === s).length;
  return {
    source: { file: file.replace(/\\/g, '/'), updated_at: mtimeIso(p) },
    total: list.length,
    pending_approval: count('PENDING_APPROVAL'),
    running: count('RUNNING'),
    with_observations: list.filter(e => e.observations > 0).length,
    recent: list.filter(e => ['PENDING_APPROVAL', 'RUNNING'].includes(e.status)).slice(-5),
  };
}

function funnel(registry, rev, dist, deliv) {
  const products = (registry && registry.products) || [];
  const regSrc = { file: 'data/product_registry.json', updated_at: (registry && registry.generated_at) || null };
  const byState = s => products.filter(p => p.primary_state === s).length;
  const live = byState('PUBLIC_LISTING_VERIFIED');
  const jobs = dist.jobs_by_state || {};
  const jobSrc = { file: 'data/distribution_dashboard.json' };
  const orders = rev.orders ? rev.orders.value : null;
  const gross = rev.gross_sales ? rev.gross_sales.value : null;
  return [
    stage(1, 'Product created', products.length, 'OBSERVED', regSrc),
    stage(2, 'Product QA passed', products.filter(p => p.manifest).length, 'DERIVED', regSrc,
      `products with a factory manifest (QA recorded); ${products.filter(p => !p.manifest).length} older listings have no QA record`),
    stage(3, 'Listing prepared', live + byState('READY_FOR_AUTHORIZATION') + byState('UPLOAD_COMPLETED'), 'DERIVED', regSrc),
    stage(4, 'Publication approved', null, 'UNKNOWN', null,
      'approvals live in data/publication_approvals.json (kept out of git); older listings predate per-product approvals'),
    stage(5, 'Listing observed live', live, 'OBSERVED', regSrc, 'public page checked by the registry'),
    stage(6, 'Distribution asset prepared', (jobs.QA_PASSED || 0), 'OBSERVED', jobSrc, 'social drafts that passed QA'),
    stage(7, 'Distribution asset published and verified', dist.published_verified || 0, 'OBSERVED', jobSrc),
    stage(8, 'Human traffic observed', null, 'UNKNOWN', null, 'no analytics receiver (backlog B6)'),
    stage(9, 'Product-page visit observed', null, 'UNKNOWN', null, 'Gumroad view counts are not imported'),
    stage(10, 'Checkout or purchase intent observed', null, 'UNKNOWN', null, 'no checkout-event feed'),
    stage(11, 'Order recorded', orders, rev.orders ? rev.orders.kind : 'UNKNOWN', rev.orders ? rev.orders.source : null),
    stage(12, 'Payment confirmed', gross, rev.gross_sales ? rev.gross_sales.kind : 'UNKNOWN',
      rev.gross_sales ? rev.gross_sales.source : null, 'Gumroad gross in cents; a Gumroad sale is a captured payment'),
    stage(13, 'Refunds, fees and adjustments reconciled', null, 'UNKNOWN', null, 'refund and fee feeds are not imported'),
    stage(14, 'Net proceeds calculated', null, 'UNKNOWN', null, 'needs stage 13'),
    stage(15, 'Payout confirmed', null, 'UNKNOWN', null, 'no payout feed is connected'),
  ].map(s => (s.n === 5 && deliv && deliv.with_buyer_issue
    ? { ...s, note: `${s.note}; ${deliv.with_buyer_issue} of them deliver less than they describe (delivery audit)` } : s));
}

// Which funnel case the evidence supports. With no traffic measurement,
// "no traffic" (A) cannot be told apart from "traffic but no interest" (B/C):
// the honest answer names that, rather than picking one.
function diagnosis(stages) {
  const v = n => stages.find(s => s.n === n);
  const orders = v(11).value;
  const traffic = v(8);
  if (orders === null || orders === undefined) {
    return { case: 'UNKNOWN', reason: 'orders are not known, so no funnel case can be named' };
  }
  if (orders === 0 && traffic.kind === 'UNKNOWN') {
    return {
      case: 'A_OR_B_OR_C',
      reason: `${v(5).value} live listings and 0 orders, but visits are not measured, so "no traffic" (A) cannot be distinguished from "traffic without interest" (B) or "interest without purchase" (C)`,
      next: 'measure visits (B6) or run a tracked distribution experiment; making more products does not answer this',
    };
  }
  if (orders === 0) return { case: 'A', reason: 'no orders and no observed traffic' };
  if (v(13).kind === 'UNKNOWN') {
    return { case: 'E_OR_F_PENDING', reason: 'orders exist but refunds and fees are not reconciled, so net proceeds are not verified' };
  }
  return { case: 'NONE', reason: 'orders exist and are reconciled' };
}

function compute({ root, registry, revenue, distribution, now = new Date() }) {
  const deliv = delivery(root, now);
  const stages = funnel(registry, revenue, distribution, deliv.kind === 'OBSERVED' ? deliv : null);
  return {
    funnel: stages,
    diagnosis: diagnosis(stages),
    delivery: deliv,
    experiments: experiments(root),
  };
}

module.exports = { compute, funnel, delivery, experiments, diagnosis, BUYER_ISSUES };
