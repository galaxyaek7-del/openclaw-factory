// Builds the single-file phone demo (engine + agency data + chat page, no network, works offline).
//
//   node services/umrah_assistant/build_demo.js
//       -> services/umrah_assistant/demo/index.html   (fictional example agency)
//   node services/umrah_assistant/build_demo.js --agency services/umrah_assistant/agencies/ennour.json --out services/umrah_assistant/agencies/ennour_demo
//       -> <out>/index.html   (a prospect's own prices; refuses to build if the data file has errors)
//
// Deterministic: same inputs give the same file.
const fs = require('node:fs');
const path = require('node:path');
const { validate } = require('./validate_agency.js');

function arg(name) {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : null;
}

function build({ agencyFile, outDir }) {
  const dir = __dirname;
  const template = fs.readFileSync(path.join(dir, 'demo.template.html'), 'utf8');
  const engine = fs.readFileSync(path.join(dir, 'engine.js'), 'utf8');
  const agency = JSON.parse(fs.readFileSync(agencyFile, 'utf8'));

  const check = validate(agency);
  if (!check.ok) {
    const e = new Error('agency data not usable:\n  - ' + check.errors.join('\n  - '));
    e.validation = check;
    throw e;
  }
  if (engine.includes('</script')) throw new Error('engine.js must not contain </script');
  // JSON inside a <script> block: "<" is escaped so "</script" or "<!--" can never close or open anything
  const agencyJson = JSON.stringify(agency).replace(/</g, '\\u003c');

  const html = template
    .replace('/*AGENCY_JSON*/', () => agencyJson)
    .replace('/*ENGINE_JS*/', () => engine);
  for (const marker of ['/*AGENCY_JSON*/', '/*ENGINE_JS*/']) {
    if (html.includes(marker)) throw new Error('marker not replaced: ' + marker);
  }
  fs.mkdirSync(outDir, { recursive: true });
  const out = path.join(outDir, 'index.html');
  fs.writeFileSync(out, html, 'utf8');
  return { out, bytes: html.length, warnings: check.warnings, status: check.status };
}

if (require.main === module) {
  const agencyFile = path.resolve(arg('--agency') || path.join(__dirname, 'agency_example.json'));
  const outDir = path.resolve(arg('--out') || path.join(__dirname, 'demo'));
  try {
    const r = build({ agencyFile, outDir });
    for (const w of r.warnings) console.log('WARNING:', w);
    console.log('wrote', r.out, r.bytes, 'bytes', '(' + r.status + ')');
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
}
module.exports = { build };
