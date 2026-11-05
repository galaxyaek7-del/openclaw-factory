// Validates an agency data file before it is used for a demo (services/umrah_assistant/agency_*.json).
// The assistant answers ONLY from this file, so a wrong or half-filled file means wrong answers to customers.
//
//   node services/umrah_assistant/validate_agency.js path/to/agency.json
//
// Exit code 0 = usable, 1 = errors (listed). Warnings never block.
const fs = require('node:fs');

const isStr = (v) => typeof v === 'string' && v.trim().length > 0;
const isPosInt = (v) => Number.isInteger(v) && v > 0;
const bil = (o) => o && isStr(o.ar) && isStr(o.fr);
const bilArr = (o) => o && Array.isArray(o.ar) && Array.isArray(o.fr) && o.ar.length > 0 && o.fr.length > 0 && o.ar.every(isStr) && o.fr.every(isStr);
const PLACEHOLDER = /REMPLIR|FILL ME|TODO|XXXX|\bXX\b|\.\.\.|…/i;

function validate(a) {
  const errors = [];
  const warnings = [];
  const err = (m) => errors.push(m);
  const warn = (m) => warnings.push(m);

  if (!a || typeof a !== 'object') return { ok: false, errors: ['not an object'], warnings, status: null };
  const status = a._status;
  if (!['REAL', 'SIMULATION'].includes(status)) err('_status must be "REAL" (data supplied by the agency) or "SIMULATION" (fictional)');
  if (status === 'SIMULATION') warn('SIMULATION data: fine for a generic demo, never for a real prospect');

  if (!bil(a.name)) err('name.ar and name.fr are required');
  if (!isStr(a.phone)) err('phone is required (the number the customer is told to call)');
  if (!bil(a.hours)) err('hours.ar and hours.fr are required');
  if (!bil(a.currency)) err('currency.ar and currency.fr are required (e.g. دج / DA)');
  if (!bil(a.city)) warn('city.ar / city.fr missing');
  if (!bil(a.flight)) warn('flight.ar / flight.fr missing');

  const ids = new Set();
  if (!Array.isArray(a.packages) || a.packages.length === 0) err('at least one package is required');
  (a.packages || []).forEach((p, i) => {
    const t = `packages[${i}]`;
    if (!isStr(p.id)) err(`${t}.id required`);
    else if (ids.has(p.id)) err(`${t}.id "${p.id}" is duplicated`);
    else ids.add(p.id);
    if (!bil(p.names)) err(`${t}.names.ar/fr required`);
    if (!isPosInt(p.days)) err(`${t}.days must be a positive integer`);
    if (!isPosInt(p.price_dzd)) err(`${t}.price_dzd must be a positive integer (price per person, in DZD)`);
    else if (p.price_dzd < 100000) warn(`${t}.price_dzd = ${p.price_dzd} looks too low for an umrah package: typo?`);
    else if (p.price_dzd > 3000000) warn(`${t}.price_dzd = ${p.price_dzd} looks too high: typo?`);
    if (!bil(p.room)) err(`${t}.room.ar/fr required`);
    if (!bil(p.meals)) err(`${t}.meals.ar/fr required`);
    for (const city of ['makkah', 'madinah']) {
      const h = p[city];
      if (!h || !Number.isInteger(h.stars) || h.stars < 1 || h.stars > 5) err(`${t}.${city}.stars must be 1..5`);
      if (!h || !Number.isInteger(h.distance_m) || h.distance_m < 0) err(`${t}.${city}.distance_m must be a number of metres >= 0`);
    }
    if (p.aliases !== undefined && !(Array.isArray(p.aliases) && p.aliases.every(isStr))) err(`${t}.aliases must be a list of strings`);
  });

  if (!Array.isArray(a.departures) || a.departures.length === 0) err('at least one departure is required');
  const today = new Date().toISOString().slice(0, 10);
  (a.departures || []).forEach((d, i) => {
    const t = `departures[${i}]`;
    if (!isStr(d.date) || !/^\d{4}-\d{2}-\d{2}$/.test(d.date) || Number.isNaN(Date.parse(d.date))) err(`${t}.date must be YYYY-MM-DD`);
    else if (d.date < today) warn(`${t}.date ${d.date} is in the past: the assistant would still offer it`);
    if (!Array.isArray(d.packages) || d.packages.length === 0) err(`${t}.packages must list package ids`);
    else for (const id of d.packages) if (!ids.has(id)) err(`${t}.packages: unknown package id "${id}"`);
  });

  for (const k of ['includes', 'excludes', 'documents', 'booking_steps']) {
    if (!bilArr(a[k])) err(`${k}.ar and ${k}.fr must be non-empty lists of text`);
    else if (a[k].ar.length !== a[k].fr.length) warn(`${k}: Arabic has ${a[k].ar.length} items, French ${a[k].fr.length}: are they the same list?`);
  }
  if (!bilArr(a.payment_methods)) err('payment_methods.ar/fr must be non-empty lists');
  if (!bil(a.documents_note)) err('documents_note.ar/fr required (the reply tells the customer the agency confirms the list)');
  if (!bil(a.seats_note)) err('seats_note.ar/fr required (the assistant never states seat availability by itself)');

  if (!isPosInt(a.deposit_dzd)) err('deposit_dzd must be a positive integer (per person)');
  else if (Array.isArray(a.packages) && a.packages.some((p) => isPosInt(p.price_dzd) && a.deposit_dzd >= p.price_dzd)) err('deposit_dzd must be lower than every package price');
  if (!isPosInt(a.balance_days_before)) err('balance_days_before must be a positive integer');

  // anything still looking like an unfilled placeholder (the blank template is full of them)
  (function scan(o, path) {
    if (typeof o === 'string') { if (PLACEHOLDER.test(o)) (status === 'REAL' ? err : warn)(`unfilled placeholder at ${path}: "${o.slice(0, 40)}"`); return; }
    if (Array.isArray(o)) { o.forEach((v, i) => scan(v, `${path}[${i}]`)); return; }
    if (o && typeof o === 'object') for (const [k, v] of Object.entries(o)) scan(v, path ? `${path}.${k}` : k);
  })(Object.fromEntries(Object.entries(a).filter(([k]) => k !== '_note')), '');

  if (status === 'REAL' && /SIMULATION|fictive|exemple|example|وهمي|مثال/i.test(JSON.stringify(a.name))) err('status is REAL but the agency name still says fictional/example');
  return { ok: errors.length === 0, errors, warnings, status };
}

function validateFile(file) {
  let data;
  try { data = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { return { ok: false, errors: [`cannot read/parse ${file}: ${e.message}`], warnings: [], status: null }; }
  return validate(data);
}

if (require.main === module) {
  const file = process.argv[2];
  if (!file) { console.error('usage: node validate_agency.js agency.json'); process.exit(2); }
  const r = validateFile(file);
  for (const w of r.warnings) console.log('WARNING:', w);
  for (const e of r.errors) console.log('ERROR:  ', e);
  console.log(r.ok ? `OK (${r.status}): usable` : `FAIL: ${r.errors.length} error(s)`);
  process.exit(r.ok ? 0 : 1);
}
module.exports = { validate, validateFile };
