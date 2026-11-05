// Prints what factory_loop.js's demand gate decides for one injected gate answer.
// Used by tests/test_factory_loop_demand_gate.js. The gate runner is stubbed: no Python, no network, and
// the slot counter is redirected by GF_DEMAND_SLOTS_PATH, so no live file is touched.
const path = require('path');
const fl = require(path.join(__dirname, '..', '..', 'factory_loop.js'));

const mode = process.env.PROBE_GATE;
const runner = () => {
  if (mode === 'open') return JSON.stringify({ open: true, daily_cap: Number(process.env.PROBE_CAP || 3), signals: { SALE: 1 }, why: 'x' });
  if (mode === 'closed') return JSON.stringify({ open: false, daily_cap: 0, signals: {}, why: 'x' });
  if (mode === 'garbage') return 'not json';
  throw new Error('python missing');
};
fl.readDemandGate(Date.now(), runner);
const slots = [];
for (let i = 0; i < Number(process.env.PROBE_SLOTS || 0); i++) slots.push(fl.takeDemandSlot());
process.stdout.write(JSON.stringify({ frozen: fl.isProductFrozen(), slots }));
process.exit(0);
