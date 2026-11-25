// Tests for services/umrah_assistant/onboarding.html (local agency-data form, Phase 2.5).
//
//   node --test tests/test_umrah_onboarding.js
//
// The form is a static, offline page; these tests check that it is self-contained
// and that the object shape it produces is accepted by the authoritative validator.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { validate } = require('../services/umrah_assistant/validate_agency.js');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'services', 'umrah_assistant', 'onboarding.html'), 'utf8');

function validAgency() {
  return {
    _status: 'REAL',
    name: { ar: 'وكالة النور للعمرة', fr: 'Agence Ennour Omra' },
    city: { ar: 'الجزائر', fr: 'Alger' },
    phone: '0551234567',
    hours: { ar: '9 صباحاً - 5 مساءً', fr: '9h - 17h' },
    currency: { ar: 'دج', fr: 'DA' },
    packages: [{
      id: 'eco',
      names: { ar: 'اقتصادية', fr: 'Économique' },
      aliases: [],
      days: 10,
      price_dzd: 285000,
      room: { ar: 'ثلاثية', fr: 'Triple' },
      makkah: { stars: 3, distance_m: 800 },
      madinah: { stars: 3, distance_m: 500 },
      meals: { ar: 'فطور وعشاء', fr: 'Petit-déjeuner et dîner' }
    }],
    departures: [{ date: '2027-01-15', packages: ['eco'] }],
    flight: { ar: 'الخطوط السعودية', fr: 'Saudia' },
    includes: { ar: ['تذكرة الطيران', 'الإقامة'], fr: ['Billet', 'Hébergement'] },
    excludes: { ar: ['تأشيرة'], fr: ['Visa'] },
    documents: { ar: ['جواز السفر'], fr: ['Passeport'] },
    documents_note: {
      ar: 'الشروط تحددها الجهات الرسمية وقد تتغير، والوكالة تؤكدها لك عند الحجز.',
      fr: "Les conditions sont fixées par les autorités et peuvent changer, l'agence vous les confirme à la réservation."
    },
    deposit_dzd: 50000,
    balance_days_before: 20,
    payment_methods: { ar: ['نقداً'], fr: ['Espèces'] },
    booking_steps: { ar: ['اتصل بالوكالة'], fr: ["Appelez l'agence"] },
    seats_note: {
      ar: 'عدد المقاعد المتبقية يؤكده لك صاحب الوكالة وقت الحجز.',
      fr: 'Le nombre de places restantes vous est confirmé par le responsable au moment de la réservation.'
    }
  };
}

test('the form is a self-contained RTL page with no network calls', () => {
  assert.match(HTML, /dir="rtl"/);
  assert.doesNotMatch(HTML, /https?:\/\//, 'the form must not reference any external URL');
});

test('the form names the authoritative validate and build commands', () => {
  assert.match(HTML, /validate_agency\.js/);
  assert.match(HTML, /build_demo\.js/);
});

test('the form covers every top-level key of the agency schema', () => {
  for (const key of [
    '_status', 'name', 'city', 'phone', 'hours', 'currency', 'packages', 'departures',
    'flight', 'includes', 'excludes', 'documents', 'documents_note', 'deposit_dzd',
    'balance_days_before', 'payment_methods', 'booking_steps', 'seats_note'
  ]) {
    assert.ok(HTML.includes(key), 'missing key in form: ' + key);
  }
});

test('the embedded script parses (no syntax error)', () => {
  const m = HTML.match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(m, 'no inline script found');
  assert.doesNotThrow(() => new Function(m[1]));
});

test('an object shaped like the form output passes the authoritative validator', () => {
  const r = validate(validAgency());
  assert.equal(r.ok, true, r.errors.join('; '));
  assert.equal(r.errors.length, 0);
  assert.equal(r.status, 'REAL');
});

test('the authoritative validator still refuses an incomplete agency', () => {
  const bad = validAgency();
  bad.phone = '';
  bad.packages[0].price_dzd = 0;
  const r = validate(bad);
  assert.equal(r.ok, false);
  assert.ok(r.errors.length >= 2);
});

test('REAL data whose name still says example is refused', () => {
  const bad = validAgency();
  bad.name.fr = 'Agence exemple';
  const r = validate(bad);
  assert.equal(r.ok, false);
  assert.ok(r.errors.some((e) => /fictional|example/i.test(e)));
});
