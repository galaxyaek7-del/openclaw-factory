// Builds the single-file phone demo: services/umrah_assistant/demo/index.html
// (engine + fictional agency data + chat page, no network, works offline).
//
//   node services/umrah_assistant/build_demo.js
//
// Deterministic: same inputs give the same file.
const fs = require('node:fs');
const path = require('node:path');

const dir = __dirname;
const template = fs.readFileSync(path.join(dir, 'demo.template.html'), 'utf8');
const engine = fs.readFileSync(path.join(dir, 'engine.js'), 'utf8');
const agency = fs.readFileSync(path.join(dir, 'agency_example.json'), 'utf8');

if (engine.includes('</script')) throw new Error('engine.js must not contain </script');
// JSON inside a <script> block: "<" is escaped so "</script" or "<!--" can never close or open anything
const agencyJson = JSON.stringify(JSON.parse(agency)).replace(/</g, '\\u003c');

const html = template
  .replace('/*AGENCY_JSON*/', () => agencyJson)
  .replace('/*ENGINE_JS*/', () => engine);

for (const marker of ['/*AGENCY_JSON*/', '/*ENGINE_JS*/']) {
  if (html.includes(marker)) throw new Error('marker not replaced: ' + marker);
}
const outDir = path.join(dir, 'demo');
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'index.html'), html, 'utf8');
console.log('wrote', path.join(outDir, 'index.html'), html.length, 'bytes');
