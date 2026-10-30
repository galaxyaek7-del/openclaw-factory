// factory_loop.timedActions(): every action recorded by runTick() carries the
// time its step took (since the previous record), so a slow daily step that
// makes ticks overlap can be named from factory_loop.log. Pure: a fake clock,
// no tick is run.
'use strict';
const assert = require('assert');
const fl = require('../factory_loop.js');

let failures = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   - ' + name); } catch (e) { failures += 1; console.log('  FAIL - ' + name + ': ' + e.message); }
}

test('each pushed action gets the time since the previous one', () => {
  let t = 1000;
  const actions = fl.timedActions(() => t);
  t = 1500; actions.push({ step: 'a' });
  t = 4500; actions.push({ step: 'b' });
  assert.deepStrictEqual(actions.map((x) => x.elapsed_ms), [500, 3000]);
});

test('an action that reports its own elapsed_ms keeps it', () => {
  let t = 0;
  const actions = fl.timedActions(() => t);
  t = 10; actions.push({ step: 'a', elapsed_ms: 7 });
  t = 30; actions.push({ step: 'b' });
  assert.deepStrictEqual(actions.map((x) => x.elapsed_ms), [7, 20]);
});

test('it is still an array: length, map, JSON and non-object items', () => {
  const actions = fl.timedActions();
  assert.strictEqual(actions.push({ step: 'a' }, 'x'), 2);
  assert.ok(Array.isArray(actions));
  assert.strictEqual(JSON.parse(JSON.stringify(actions)).length, 2);
});

console.log(failures ? `\n${failures} failed` : '\nall passed');
process.exit(failures ? 1 : 0);
