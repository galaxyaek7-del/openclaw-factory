// Extracted from server.js (Phase 10 red-team follow-up, MEDIUM finding)
// so it can be unit-tested in isolation without booting a server or
// touching the real finance_data.json. A bare Date.now() id let two
// sales added within the same millisecond collide; DELETE
// /finance/delete/:id then silently deleted both. Keeps the id an
// integer (DELETE's parseInt(req.params.id, 10) contract is unchanged)
// — just guarantees it's actually unique among existing sales.
function nextSaleId(existingSales) {
  const ids = new Set(existingSales.map(s => s.id));
  let id = Date.now();
  while (ids.has(id)) id++;
  return id;
}

module.exports = { nextSaleId };
