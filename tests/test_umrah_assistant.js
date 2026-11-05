// Tests for services/umrah_assistant/engine.js (Umrah agency assistant demo, SIMULATION data).
//
//   node --test tests/test_umrah_assistant.js

const test = require('node:test');
const assert = require('node:assert/strict');
const A = require('../services/umrah_assistant/engine.js');
const AGENCY = require('../services/umrah_assistant/agency_example.json');

function chat(messages) {
  const s = A.newSession();
  const out = messages.map((m) => ({ in: m, ...A.respond(AGENCY, s, m) }));
  return { s, out, last: out[out.length - 1] };
}

test('the data file says it is a simulation, in the three languages', () => {
  assert.equal(AGENCY._status, 'SIMULATION');
  assert.match(AGENCY._note, /مثال/);
  assert.match(AGENCY._note, /EXEMPLE/);
  assert.match(AGENCY.name.fr, /exemple/);
});

test('normalize: arabic forms, diacritics, arabic-indic digits, french accents', () => {
  assert.equal(A.normalize('الأسعَار'), 'الاسعار');
  assert.equal(A.normalize('عمرة'), 'عمره');
  assert.equal(A.normalize('٠٥٥٥'), '0555');
  assert.equal(A.normalize('Réservation, DÉPART!'), 'reservation depart');
});

test('language detection: french, arabic, darija (arabic script), arabizi', () => {
  const cases = [
    ['Bonjour, je voudrais les prix', 'fr'],
    ['Quels documents faut-il pour la omra ?', 'fr'],
    ['السلام عليكم، ما هي أسعار العمرة؟', 'ar'],
    ['شحال سعر العمرة؟', 'dz'],
    ['واش لازم من وثائق', 'dz'],
    ['nheb nehjez omra', 'dz'],
    ['chhal ta3 omra', 'dz'],
    ['wach lazem men wra9', 'dz'],
    ['salam, kifach ndir', 'dz'],
  ];
  for (const [text, want] of cases) assert.equal(A.detectLang(text), want, text);
});

test('classification across the three languages', () => {
  const cases = [
    // price
    ['Quel est le prix ?', 'price'], ['ما هو سعر الباقة', 'price'], ['شحال سعر العمرة', 'price'], ['chhal ta3 omra', 'price'], ['9edach el omra', 'price'],
    ['quelle est la formule la moins chère', 'price'], ['ما هي أرخص باقة', 'price'],
    // dates
    ['Quand est le prochain départ ?', 'dates'], ['متى موعد السفر', 'dates'], ['وقتاش السفر', 'dates'], ['waqtach el depart', 'dates'],
    // documents
    ['Quels documents dois-je fournir ?', 'documents'], ['ما هي الوثائق المطلوبة', 'documents'], ['واش نحتاج من اوراق', 'documents'], ['wach lazem men wra9', 'documents'],
    ['faut-il un vaccin ?', 'documents'],
    // includes / hotel
    ['Quel hôtel et à quelle distance du Haram ?', 'includes'], ['واش تشمل الباقة فندق', 'includes'], ['ما تشمله الباقة', 'includes'],
    // duration
    ['combien de jours dure le séjour', 'duration'], ['كم يوم الرحلة', 'duration'], ['شحال من نهار', 'duration'],
    // payment
    ["Comment payer, y a-t-il un acompte ?", 'payment'], ['كيف ندفع التسبيق', 'payment'], ['wach 3andkom baridimob', 'payment'],
    // how to book (a question, not a booking)
    ['Comment réserver ?', 'booking_how'], ['كيفاش نحجز', 'booking_how'], ['ما هي طريقة الحجز', 'booking_how'], ['kifach nehjez', 'booking_how'],
    // payment question that mentions booking is still a payment question
    ['شحال التسبيق باش نحجز', 'payment'],
    // ready to book
    ['Je veux réserver', 'ready_to_book'], ['نحب نحجز', 'ready_to_book'], ['أريد حجز مقعدين', 'ready_to_book'], ['nheb nehjez', 'ready_to_book'],
    // human, complaint, negotiation
    ['je voudrais parler au responsable', 'human'], ['نحب نكلم صاحب الوكالة', 'human'], ['donnez-moi votre numéro', 'human'],
    ['c\'est une arnaque', 'complaint'], ['عندي مشكل مع الحجز', 'complaint'],
    ['Pouvez-vous faire une remise ?', 'negotiation'], ['غالي بزاف تنقصو؟', 'negotiation'], ['c\'est trop cher', 'negotiation'],
    // religious
    ['est-ce permis de faire ça pendant le rituel ?', 'religious'], ['هل يجوز ... مناسك', 'religious'],
    // small talk
    ['merci beaucoup', 'thanks'], ['شكرا', 'thanks'], ['bonjour', 'greeting'], ['السلام عليكم', 'greeting'],
    // not understood
    ['blabla xyz', 'unknown'], ['la météo à Paris', 'unknown'],
  ];
  const wrong = [];
  for (const [text, want] of cases) {
    const got = A.classify(text);
    if (got !== want) wrong.push(`${JSON.stringify(text)} -> ${got} (wanted ${want})`);
  }
  assert.deepEqual(wrong, []);
});

test('first bot message says it is an automated assistant, in the customer language, once', () => {
  for (const [msg, re] of [['Bonjour', /assistant automatique/], ['السلام عليكم', /المساعد الآلي/], ['salam', /المساعد الآلي/]]) {
    const c = chat([msg, 'merci']);
    assert.match(c.out[0].text, re, msg);
    assert.doesNotMatch(c.out[1].text, /assistant automatique|المساعد الآلي/, 'disclosure only on the first reply');
  }
  // disclosure is also there when the first message is already a question
  assert.match(chat(['Quel est le prix ?']).out[0].text, /assistant automatique/);
});

test('every number in an informational reply comes from the agency data (nothing invented)', () => {
  const allowed = new Set();
  const add = (n) => { allowed.add(String(n)); };
  for (const p of AGENCY.packages) {
    add(p.days); add(p.price_dzd); add(p.makkah.stars); add(p.makkah.distance_m); add(p.madinah.stars); add(p.madinah.distance_m);
    add(String(p.price_dzd).replace(/\B(?=(\d{3})+(?!\d))/g, ' '));
  }
  add(AGENCY.deposit_dzd); add(String(AGENCY.deposit_dzd).replace(/\B(?=(\d{3})+(?!\d))/g, ' '));
  add(AGENCY.balance_days_before); add(AGENCY.packages.length);
  for (const d of AGENCY.departures) { const [y, m, dd] = d.date.split('-').map(Number); add(y); add(dd); }
  const texts = [].concat(AGENCY.documents.ar, AGENCY.documents.fr, AGENCY.booking_steps.ar, AGENCY.booking_steps.fr, AGENCY.includes.ar, AGENCY.includes.fr,
    AGENCY.hours.ar, AGENCY.hours.fr, [AGENCY.phone, AGENCY.documents_note.ar, AGENCY.documents_note.fr]);
  for (const t of texts) for (const n of (t.match(/\d+/g) || [])) add(n);
  for (let i = 1; i <= 6; i += 1) add(i); // numbered steps
  const questions = ['Quel est le prix ?', 'Quand partir ?', 'Quels documents ?', 'Quel hôtel, quelle distance ?', 'Combien de jours ?', 'Comment payer ?', 'Comment réserver ?',
    'شحال السعر', 'وقتاش السفر', 'واش لازم من وثائق', 'واش تشمل الباقة', 'شحال من نهار', 'كيف ندفع', 'كيفاش نحجز', 'chhal ta3 omra', 'waqtach el depart', 'wach lazem men wra9',
    'quel prix pour la formule confort ?', 'سعر الباقة الاقتصادية', 'visa ?'];
  const bad = [];
  for (const q of questions) {
    const text = A.respond(AGENCY, A.newSession(), q).text;
    for (const n of (text.replace(/(\d) (\d{3})/g, '$1 $2').match(/\d+(?: \d{3})*/g) || [])) {
      if (!allowed.has(n) && !n.split(' ').every((x) => allowed.has(x) || allowed.has(n))) bad.push(`${q} -> ${n}`);
    }
  }
  assert.deepEqual(bad, []);
});

test('price answers use the agency prices exactly, and name a package when one is mentioned', () => {
  assert.match(chat(['quel prix pour la formule confort ?']).last.text, /345 000 DA/);
  assert.match(chat(['سعر الباقة الاقتصادية']).last.text, /285 000 دج/);
  assert.match(chat(['9edach premium']).last.text, /520 000 دج/);
});

test('booking flow in french: package, persons, name, phone, then a lead card', () => {
  const c = chat(['Bonjour', 'je veux réserver la formule confort', '3', 'Mansour Benali', '0555 12 34 56']);
  const card = c.last.handoff;
  assert.ok(card, 'a hand-off card is produced');
  assert.equal(card.reason, 'ready_to_book');
  assert.equal(card.package, 'Confort');
  assert.equal(card.persons, 3);
  assert.equal(card.name, 'Mansour Benali');
  assert.equal(card.phone, '0555123456');
  assert.equal(card.estimate_dzd, 345000 * 3);
  assert.equal(card.lang, 'fr');
  assert.match(card.delivery, /NOT CONNECTED/);
  assert.equal(c.s.handoffs.length, 1);
  assert.match(c.last.text, /1 035 000 DA/);
});

test('booking flow in darija: asks for the package when none was named', () => {
  const c = chat(['نحب نحجز', 'الاقتصادية', 'جوج', 'أحمد منصور', '٠٦٦١٢٣٤٥٦٧']);
  assert.equal(c.out[0].intent, 'handoff_start');
  assert.match(c.out[0].text, /أنهي باقة/);
  const card = c.last.handoff;
  assert.equal(card.package, 'Économique');
  assert.equal(card.persons, 2);
  assert.equal(card.name, 'أحمد منصور', 'a name that contains the keyword "صور" must still be accepted');
  assert.equal(card.phone, '0661234567');
});

test('a package named earlier is remembered when the customer is ready to book', () => {
  const c = chat(['شحال الباقة المميزة', 'نحب نحجز']);
  assert.equal(c.last.intent, 'handoff_start');
  assert.match(c.last.text, /شحال من واحد|كم عدد/, 'goes straight to the number of people');
});

test('a question during the booking flow is answered, then the pending question is asked again', () => {
  const c = chat(['Je veux réserver', 'confort', 'Quels documents faut-il ?']);
  assert.equal(c.last.intent, 'collecting');
  assert.match(c.last.text, /passeport/);
  assert.match(c.last.text, /Combien de personnes/);
  assert.equal(c.s.handoffs.length, 0);
});

test('phone numbers: algerian formats are normalised, junk is refused, three failures still end cleanly', () => {
  for (const [raw, want] of [['0555 12 34 56', '0555123456'], ['+213 661 23 45 67', '0661234567'], ['0771-23-45-67', '0771234567'], ['00213555123456', '0555123456'], ['٠٦٦١٢٣٤٥٦٧', null]]) {
    if (want) assert.equal(A.parsePhone(raw), want, raw);
  }
  assert.equal(A.parsePhone('12345'), null);
  assert.equal(A.parsePhone('0455123456'), null, 'landline-like / not a mobile prefix');
  const c = chat(['Je veux réserver', 'eco', '2', 'Karim', 'pas de numéro', 'non', 'je ne sais pas']);
  assert.ok(c.last.handoff, 'ends with a card instead of looping forever');
  assert.equal(c.last.handoff.phone, null);
});

test('cancelling the booking flow stops it', () => {
  const c = chat(['Je veux réserver', 'annule']);
  assert.equal(c.last.intent, 'cancel');
  assert.equal(c.s.state, 'idle');
});

test('price negotiation is never answered with a discount, only offered to the owner', () => {
  for (const msg of ['Pouvez-vous faire une remise ?', 'غالي بزاف تنقصو؟', 'c\'est trop cher']) {
    const c = chat([msg]);
    assert.equal(c.last.intent, 'negotiation', msg);
    assert.doesNotMatch(c.last.text, /%|خصم|remise de|réduction de/, msg);
    assert.equal(c.s.handoffs.length, 0, 'nothing is handed over before the customer agrees');
    assert.equal(c.s.pendingOffer.reason, 'negotiation');
  }
  const c = chat(['c\'est trop cher', 'oui', 'Nadia', '0661 11 22 33']);
  assert.equal(c.out[1].intent, 'handoff_start');
  assert.equal(c.last.handoff.reason, 'negotiation');
});

test('a "no" after the offer drops it and the conversation goes on normally', () => {
  const c = chat(['c\'est trop cher', 'non merci, quels sont les documents ?']);
  assert.equal(c.last.intent, 'documents');
  assert.equal(c.s.pendingOffer, null);
});

test('a complaint goes to the owner at once and is not argued with', () => {
  const c = chat(['عندي مشكل مع الحجز', 'سليم', '0550 00 11 22']);
  assert.equal(c.out[0].intent, 'complaint');
  assert.match(c.out[0].text, /لا أعالجها آلياً|ما نعالجهاش/);
  assert.equal(c.last.handoff.reason, 'complaint');
});

test('questions about religious rulings are not answered', () => {
  const c = chat(['est-ce permis de faire cela pendant le rituel ?']);
  assert.equal(c.last.intent, 'religious');
  assert.match(c.last.text, /ne réponds pas|guide religieux/);
  assert.equal(c.s.pendingOffer.reason, 'human_requested');
});

test('asking for a human starts a call-back request with the agency phone', () => {
  const c = chat(['je voudrais parler au responsable']);
  assert.equal(c.last.intent, 'human');
  assert.match(c.last.text, /05 XX XX XX XX/);
  assert.match(c.last.text, /nom complet/);
});

test('an unknown question is never guessed; the second one in a row goes to the owner', () => {
  const c = chat(['blabla xyz', 'la météo à Paris']);
  assert.equal(c.out[0].intent, 'unknown');
  assert.match(c.out[0].text, /préfère ne pas deviner/);
  assert.equal(c.out[1].intent, 'handoff_start');
  assert.equal(c.s.state, 'collecting');
});

test('the language follows the customer and stays during hand-off answers', () => {
  const c = chat(['Bonjour', 'nheb nehjez', 'eco', '2']);
  assert.equal(c.out[0].lang, 'fr');
  assert.equal(c.out[1].lang, 'dz');
  assert.equal(c.out[3].lang, 'dz', 'a bare number keeps the session language');
});

test('the engine has no network or model dependency', () => {
  const src = require('node:fs').readFileSync(require.resolve('../services/umrah_assistant/engine.js'), 'utf8');
  for (const bad of ['require(', 'fetch(', 'XMLHttpRequest', 'groq', 'openai', 'process.env']) assert.ok(!src.includes(bad), bad);
});
