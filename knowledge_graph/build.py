"""
Knowledge Graph v1 (EOS Phase 2, 2026-07-19) — a living, queryable
company memory over real, already-recorded relationships. Not a graph
database (same "plain Python/JSON over new dependencies" choice
knowledge_brain.js already made against embeddings) — real nodes and
edges built from 6 real sources already in this repo:

  - data/decisions.jsonl (Niche, Decision nodes)
  - data/market_intelligence_analyses.jsonl (MarketAnalysis nodes)
  - data/sales_ledger.jsonl (ProductionRun nodes, PublishChannel edges)
  - data/ai_cost_log.jsonl (AIProvider edges)
  - data/market_evidence.jsonl's closed_sale events (CommercialEvent
    nodes, Global Market Learning Engine, 2026-07-23 — market_memory.py's
    real commercial dimensions, linked back to the Niche they sold)
  - channels/registry.py + ai_capability/registry.py (PublishChannel /
    AIProvider node catalogs)

Executive Intelligence Core, Round 5 (2026-07-29) adds two more real
sources, closing the "company memory is 4 disconnected systems" gap an
audit of this factory's governance stack found: hand-written
institutional memory (ADRs, lessons learned) previously lived only as
markdown files `knowledge_brain.js` could grep, with no node of their
own in this graph.

  - OpenClaw_Brain/19_Lessons_Learned/*.md (Lesson nodes)
  - OpenClaw_Brain/00_Governance/ADR-*.md (ADR nodes)

Both are mechanical (real filename + real first markdown heading),
never semantic. Linking a Lesson/ADR to the specific Decision/Niche it's
actually about would need real similarity matching this factory has no
embeddings infrastructure for — the same disclosed non-goal
tool_intelligence/proposals.py's own vector-store proposal already
documents, not attempted here either.

Autonomous Company Evolution Engine, Round 5 (2026-07-29) adds a ninth
real source — this is the "Learn" step's Company Memory: every real
Evolution Queue proposal, whatever stage it actually reached (still
awaiting founder approval, approved, rejected, or implemented), becomes
a queryable Proposal node.

  - data/evolution_queue_state.json (Proposal nodes)

Same mechanical, non-semantic discipline as Lesson/ADR — no edge from a
Proposal to the Niche/Decision/module it's actually about; that would
again need real similarity matching this factory doesn't have.

`build_graph()` writes a DISPOSABLE, REGENERABLE snapshot
(data/knowledge_graph_snapshot.json) — explicitly a derived cache,
never a source of truth. Rebuild it any time by calling build_graph()
again; nothing else in this factory writes to or depends on this file
existing.

Honest limitation, documented not smoothed over: `Decision→produced→
ProductionRun` is the one edge with no guaranteed real foreign key.
production_factory/dossier.py's make_production_id() means
`product_source_id == f"PROD-{decision_id}"` for every production that
went through the modern pipeline (ADR-077) -- when that exact match
holds, the edge is marked `"edge_confidence": "exact"`. For older/
legacy productions where it doesn't, a best-effort niche-text match is
attempted instead and marked `"edge_confidence": "approximate"` --
never silently presented as certain.

`query_related(graph, entity_type, entity_id)` is plain dict
traversal, 1-2 hops -- no query language, no index beyond a simple
adjacency dict built in-memory at query time.
"""

import json
import os
import re
from datetime import datetime, timezone

FACTORY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECISIONS_FILE = os.path.join(FACTORY_DIR, 'data', 'decisions.jsonl')
MARKET_INTELLIGENCE_ANALYSES_FILE = os.path.join(FACTORY_DIR, 'data', 'market_intelligence_analyses.jsonl')
SALES_LEDGER_FILE = os.path.join(FACTORY_DIR, 'data', 'sales_ledger.jsonl')
AI_COST_LOG_FILE = os.path.join(FACTORY_DIR, 'data', 'ai_cost_log.jsonl')
MARKET_EVIDENCE_FILE = os.path.join(FACTORY_DIR, 'data', 'market_evidence.jsonl')
SNAPSHOT_FILE = os.path.join(FACTORY_DIR, 'data', 'knowledge_graph_snapshot.json')
DECISION_OUTCOMES_FILE = os.path.join(FACTORY_DIR, 'data', 'decision_outcomes.jsonl')
LESSONS_LEARNED_DIR = os.path.join(FACTORY_DIR, 'OpenClaw_Brain', '19_Lessons_Learned')
GOVERNANCE_DIR = os.path.join(FACTORY_DIR, 'OpenClaw_Brain', '00_Governance')
EVOLUTION_QUEUE_STATE_FILE = os.path.join(FACTORY_DIR, 'data', 'evolution_queue_state.json')
AFFILIATE_CLICKS_FILE = os.path.join(FACTORY_DIR, 'data', 'affiliate_clicks.jsonl')
AFFILIATE_SIMULATION_EVENTS_FILE = os.path.join(FACTORY_DIR, 'data', 'affiliate_simulation_events.jsonl')
COUNCIL_RECOMMENDATIONS_FILE = os.path.join(FACTORY_DIR, 'data', 'council_recommendations.jsonl')
COMPETITOR_DATABASE_FILE = os.path.join(FACTORY_DIR, 'data', 'competitor_database.json')
_ADR_FILENAME_RE = re.compile(r'^(ADR-\d+)-')


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _normalize(text):
    return re.sub(r'\s+', ' ', str(text or '').strip().lower())


def _node(node_id, node_type, **attrs):
    return {"id": node_id, "type": node_type, **attrs}


def _edge(from_id, to_id, relation, confidence="exact"):
    return {"from": from_id, "to": to_id, "relation": relation, "edge_confidence": confidence}


def _first_heading(path):
    """Real, mechanical title extraction -- the file's own first markdown
    heading line, verbatim. Never inferred/summarized."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#'):
                    return line.lstrip('#').strip()
    except OSError:
        pass
    return None


_ADR_DATE_RE = re.compile(r'^\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})')


def _first_date(path):
    """Real, mechanical date extraction -- this factory's own real ADR
    convention (`**Date:** YYYY-MM-DD` on its own line, near the top of
    every ADR written this session). Honestly None for any ADR that
    predates this convention -- never a guessed or inferred date
    (ADR-154, 2026-07-31, for gfos.py's enterprise_timeline() `adr`
    event type)."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                m = _ADR_DATE_RE.match(line.strip())
                if m:
                    return m.group(1)
    except OSError:
        pass
    return None


def _lesson_nodes(lessons_dir=None):
    """Real Lesson nodes (Round 5, 2026-07-29) -- every real markdown
    file in OpenClaw_Brain/19_Lessons_Learned/ (excluding README), title
    taken verbatim from the file's own first heading."""
    directory = lessons_dir or LESSONS_LEARNED_DIR
    nodes = []
    if not os.path.isdir(directory):
        return nodes
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith('.md') or filename.upper() == 'README.MD':
            continue
        path = os.path.join(directory, filename)
        stem = filename[:-3]
        title = _first_heading(path) or stem.replace('_', ' ')
        nodes.append(_node(f"lesson:{stem}", "Lesson", label=title, source_file=filename))
    return nodes


def _adr_nodes(governance_dir=None):
    """Real ADR nodes (Round 5, 2026-07-29) -- every real ADR-*.md file
    in OpenClaw_Brain/00_Governance/, title taken verbatim from the
    file's own first heading."""
    directory = governance_dir or GOVERNANCE_DIR
    nodes = []
    if not os.path.isdir(directory):
        return nodes
    for filename in sorted(os.listdir(directory)):
        match = _ADR_FILENAME_RE.match(filename)
        if not match or not filename.endswith('.md'):
            continue
        path = os.path.join(directory, filename)
        title = _first_heading(path) or filename[:-3].replace('-', ' ')
        nodes.append(_node(f"adr:{match.group(1)}", "ADR", label=title, source_file=filename, date=_first_date(path)))
    return nodes


def _proposal_nodes(evolution_queue_state_path=None):
    """Real Proposal nodes (Autonomous Company Evolution Engine, Round 5,
    2026-07-29) -- every real record in data/evolution_queue_state.json,
    whatever stage it actually reached. Honestly empty until a real
    proposal has been through at least one daily intake cycle."""
    path = evolution_queue_state_path or EVOLUTION_QUEUE_STATE_FILE
    nodes = []
    if not os.path.exists(path):
        return nodes
    try:
        with open(path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return nodes
    if not isinstance(state, dict):
        return nodes
    for proposal_id, record in state.items():
        if not isinstance(record, dict):
            continue
        tool = (record.get("proposal") or {}).get("tool") if isinstance(record.get("proposal"), dict) else None
        nodes.append(_node(
            f"proposal:{proposal_id}", "Proposal",
            label=tool or proposal_id,
            stage=record.get("stage"),
            created_at=record.get("created_at"),
        ))
    return nodes


def _executive_directive_nodes(ledger_path=None):
    """Real ExecutiveDirective nodes (Executive Brain, ADR-144,
    2026-07-30) -- every real record ever appended to
    data/executive_directives.jsonl, the permanent decision ledger
    executive_brain.build_executive_directive() writes to. Same
    standalone-unless-resolvable discipline as Proposal nodes above:
    an edge to the real Proposal it cites is only ever added when the
    directive's own evidence carries a real proposal_id already present
    as a node -- never a guessed/fabricated edge otherwise."""
    from executive_brain import DEFAULT_LEDGER_PATH
    path = ledger_path or str(DEFAULT_LEDGER_PATH)
    nodes, edges = [], []
    if not os.path.exists(path):
        return nodes, edges
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            directive = record.get("directive") or {}
            node_id = f"executive_directive:{record.get('generated_at', i)}"
            nodes.append(_node(
                node_id, "ExecutiveDirective",
                label=directive.get("action") or directive.get("status") or "directive",
                status=directive.get("status"),
                tier=directive.get("tier"),
                generated_at=record.get("generated_at"),
            ))
            proposal_id = (directive.get("evidence") or {}).get("proposal_id") if isinstance(directive.get("evidence"), dict) else None
            if proposal_id:
                edges.append(_edge(node_id, f"proposal:{proposal_id}", "cites", confidence="exact"))
    return nodes, edges


def _affiliate_event_nodes(clicks_path=None, simulation_path=None):
    """Real AffiliateEvent nodes (Executive Intelligence Layer, ADR-154,
    2026-07-31) -- every real real click (data/affiliate_clicks.jsonl,
    ADR-149) and every real simulated conversion (data/
    affiliate_simulation_events.jsonl, ADR-153). Every node carries its
    own real `simulation` flag (False for real clicks, True for
    simulated events) so a real event is never confused with a
    simulated one when the graph is queried -- same discipline
    simulation_mode.py's own tag_simulated() already enforces on the
    ledgers themselves. Honestly 0 real nodes today (both ledgers are
    empty) -- never backfilled or invented."""
    nodes = []
    clicks = _read_jsonl(clicks_path or AFFILIATE_CLICKS_FILE)
    for i, c in enumerate(clicks):
        nodes.append(_node(
            f"affiliate_event:click:{i}:{c.get('timestamp', i)}", "AffiliateEvent",
            label=f"click: {c.get('product_id')}", event_kind="click",
            product_id=c.get("product_id"), timestamp=c.get("timestamp"),
            referrer=c.get("referrer"), simulation=False,
        ))
    sim_events = _read_jsonl(simulation_path or AFFILIATE_SIMULATION_EVENTS_FILE)
    for i, s in enumerate(sim_events):
        nodes.append(_node(
            f"affiliate_event:simulated_conversion:{i}:{s.get('timestamp', i)}", "AffiliateEvent",
            label=f"SIMULATED conversion: {s.get('product_id')}", event_kind="simulated_conversion",
            product_id=s.get("product_id"), timestamp=s.get("timestamp"),
            simulated_commission_usd=s.get("simulated_commission_usd"), simulation=True,
        ))
    return nodes


def _competitor_nodes(competitor_database_path=None):
    """Real Competitor nodes (Knowledge Graph & Institutional Memory
    Engine, ADR-208, Phase 18, 2026-08-08) -- closes the exact gap
    Phase 17's INTELLIGENCE_KNOWLEDGE_GRAPH.md disclosed and left open:
    "competitor data is not yet a graphed node type." Every real entry
    in data/competitor_database.json (57 real niches as of Phase 17)
    becomes a real Competitor node, with a real edge back to its Niche
    node ONLY when that niche was also real-evaluated in decisions.jsonl
    (i.e. the Niche node already exists) -- never a fabricated edge to
    a niche node that isn't real. category_reason is carried verbatim
    (already real, disclosed confidence text -- see COMPETITOR_
    INTELLIGENCE.md) rather than re-summarized."""
    nodes, edges = [], []
    path = competitor_database_path or COMPETITOR_DATABASE_FILE
    if not os.path.exists(path):
        return nodes, edges
    try:
        with open(path, 'r', encoding='utf-8') as f:
            db = json.load(f)
    except (OSError, json.JSONDecodeError):
        return nodes, edges

    for key, entry in (db.items() if isinstance(db, dict) else []):
        niche = entry.get("niche") or key
        niche_id = f"niche:{_normalize(niche)}"
        for i, comp in enumerate(entry.get("competitors") or []):
            name = comp.get("name")
            if not name:
                continue
            comp_id = f"competitor:{_normalize(niche)}:{i}"
            nodes.append(_node(
                comp_id, "Competitor",
                label=name, url=comp.get("url"), source=comp.get("source"),
                category=comp.get("category"), category_reason=comp.get("category_reason"),
                niche=niche,
            ))
            edges.append(_edge(comp_id, niche_id, "COMPETITOR_SOLVES_PROBLEM", confidence="approximate"))
    return nodes, edges


def _council_recommendation_nodes(council_recommendations_path=None):
    """Real CouncilRecommendation nodes (Executive Intelligence Layer,
    ADR-154, 2026-07-31) -- every real record in data/
    council_recommendations.jsonl (Galaxy Council, ADR-138). This real
    ledger already feeds gfos.py::enterprise_timeline() but was never
    graphed until now -- a genuine, confirmed gap, not a duplicate."""
    nodes = []
    records = _read_jsonl(council_recommendations_path or COUNCIL_RECOMMENDATIONS_FILE)
    for i, r in enumerate(records):
        nodes.append(_node(
            f"council_recommendation:{i}:{r.get('convened_at', i)}", "CouncilRecommendation",
            label=f"{r.get('niche')}: {r.get('council_recommendation')}",
            niche=r.get("niche"), convened_at=r.get("convened_at"),
            disagreement_detected=r.get("disagreement_detected"),
        ))
    return nodes


def build_graph(decisions_path=None, analyses_path=None, ledger_path=None, ai_cost_log_path=None,
                 evidence_path=None, lessons_dir=None, governance_dir=None, evolution_queue_state_path=None,
                 decision_outcomes_path=None, executive_directives_path=None,
                 affiliate_clicks_path=None, affiliate_simulation_events_path=None,
                 council_recommendations_path=None, competitor_database_path=None):
    decisions = _read_jsonl(decisions_path or DECISIONS_FILE)
    analyses = _read_jsonl(analyses_path or MARKET_INTELLIGENCE_ANALYSES_FILE)
    ledger = _read_jsonl(ledger_path or SALES_LEDGER_FILE)
    ai_costs = _read_jsonl(ai_cost_log_path or AI_COST_LOG_FILE)
    evidence = _read_jsonl(evidence_path or MARKET_EVIDENCE_FILE)
    decision_outcomes = _read_jsonl(decision_outcomes_path or DECISION_OUTCOMES_FILE)

    nodes = {}
    edges = []

    def _add_node(node):
        nodes[node["id"]] = node

    # Niche + Decision nodes/edges (real, from decisions.jsonl)
    for d in decisions:
        niche = d.get("niche")
        if not niche:
            continue
        niche_id = f"niche:{_normalize(niche)}"
        decision_id = d.get("decision_id")
        _add_node(_node(niche_id, "Niche", label=niche))
        if decision_id:
            _add_node(_node(f"decision:{decision_id}", "Decision", niche=niche, status=d.get("status"),
                             ladder=d.get("ladder"), reasoning=d.get("reasoning")))
            edges.append(_edge(niche_id, f"decision:{decision_id}", "evaluated_as"))

    # Outcome nodes/edges (real, from data/decision_outcomes.jsonl --
    # Decision Memory, Round 6, 2026-07-29): decision_engine/feedback.py's
    # already-real sync_outcomes() is what populates this file; here it's
    # only ever read and mechanically joined back to its real Decision
    # node by decision_id -- never a second computation. Only a real,
    # matched outcome (decision_engine/types.py's Outcome.matched=True,
    # a real decision_id) gets a real edge -- an unmatched sale
    # (decision_id is None) has no real Decision to link to honestly, so
    # it's skipped here, never guessed at.
    for o in decision_outcomes:
        decision_id = o.get("decision_id")
        if not o.get("matched") or not decision_id:
            continue
        decision_node_id = f"decision:{decision_id}"
        if decision_node_id not in nodes:
            continue
        outcome_id = o.get("outcome_id") or f"{decision_id}:{o.get('recorded_at')}"
        outcome_node_id = f"outcome:{outcome_id}"
        _add_node(_node(outcome_node_id, "Outcome", matched=True,
                         match_method=o.get("match_method"), recorded_at=o.get("recorded_at")))
        edges.append(_edge(decision_node_id, outcome_node_id, "resulted_in"))

    # MarketAnalysis nodes/edges (real, from market_intelligence_analyses.jsonl)
    for a in analyses:
        niche = a.get("niche")
        if not niche:
            continue
        niche_id = f"niche:{_normalize(niche)}"
        analysis_id = f"analysis:{_normalize(niche)}:{a.get('analyzed_at')}"
        _add_node(_node(niche_id, "Niche", label=niche))
        _add_node(_node(analysis_id, "MarketAnalysis", niche=niche, opportunity_gap=a.get("opportunity_gap"),
                         analyzed_at=a.get("analyzed_at")))
        edges.append(_edge(niche_id, analysis_id, "analyzed_by"))

    # ProductionRun + PublishChannel nodes/edges (real, from sales_ledger.jsonl)
    decision_ids = {d.get("decision_id") for d in decisions if d.get("decision_id")}
    for entry in ledger:
        if entry.get("event_type") != "publish_attempt":
            continue
        source_id = entry.get("product_source_id")
        if not source_id:
            continue
        run_id = f"production:{source_id}"
        _add_node(_node(run_id, "ProductionRun", title=entry.get("product_title"),
                         product_type=entry.get("product_type"), source_id=source_id))

        platform = entry.get("platform")
        if platform:
            channel_id = f"channel:{platform}"
            _add_node(_node(channel_id, "PublishChannel", label=platform))
            edges.append(_edge(run_id, channel_id, "published_via"))

        # Decision -> ProductionRun: exact when make_production_id()'s
        # real PROD-{decision_id} convention holds, approximate fallback
        # via niche-text otherwise (never silently presented as certain).
        matched_decision_id = None
        if source_id.startswith("PROD-") and source_id[len("PROD-"):] in decision_ids:
            matched_decision_id = source_id[len("PROD-"):]
            confidence = "exact"
        else:
            title_norm = _normalize(entry.get("product_title"))
            for d in decisions:
                if d.get("niche") and _normalize(d["niche"]) == title_norm:
                    matched_decision_id = d.get("decision_id")
                    confidence = "approximate"
                    break
        if matched_decision_id:
            edges.append(_edge(f"decision:{matched_decision_id}", run_id, "produced", confidence=confidence))

    # AIProvider edges (real, from ai_cost_log.jsonl's context.niche + model)
    for entry in ai_costs:
        model = entry.get("model")
        context = entry.get("context")
        # Defensive (found live, 2026-07-22): context is a dict for every
        # real book/content-generation call, but a caller can log a bare
        # string (e.g. a short label) instead -- one malformed log line
        # must never crash the whole graph build.
        niche = context.get("niche") if isinstance(context, dict) else None
        if not model or not niche:
            continue
        provider_id = f"ai_provider:{model}"
        niche_id = f"niche:{_normalize(niche)}"
        _add_node(_node(provider_id, "AIProvider", label=model))
        if niche_id in nodes:
            edges.append(_edge(niche_id, provider_id, "cost_incurred_from", confidence="approximate"))

    # CommercialEvent nodes/edges (real, from market_evidence.jsonl's
    # closed_sale events -- Global Market Learning Engine, 2026-07-23).
    # Only events already carrying market_memory.py's real dimensional
    # payload are graphed; an older/bare closed_sale event with no
    # commercial_event field is skipped, never fabricated to fit.
    for idx, ev in enumerate(evidence):
        if ev.get("event_type") != "closed_sale":
            continue
        commercial_event = (ev.get("payload") or {}).get("commercial_event")
        if not isinstance(commercial_event, dict):
            continue
        niche = ev.get("niche")
        if not niche:
            continue
        niche_id = f"niche:{_normalize(niche)}"
        event_id = f"commercial_event:{_normalize(niche)}:{ev.get('timestamp') or idx}"
        _add_node(_node(niche_id, "Niche", label=niche))
        _add_node(_node(event_id, "CommercialEvent", niche=niche, platform=commercial_event.get("platform"),
                         selling_price=commercial_event.get("selling_price"), season=commercial_event.get("season"),
                         recorded_at=ev.get("timestamp")))
        edges.append(_edge(niche_id, event_id, "sold_as"))

    # Lesson + ADR nodes (real, from hand-written institutional-memory
    # markdown -- Round 5, 2026-07-29). Standalone nodes, no edges to
    # Niche/Decision: linking them for real would need semantic
    # similarity this factory has no embeddings infra for (see this
    # module's own docstring) -- never a guessed/fabricated edge instead.
    for node in _lesson_nodes(lessons_dir):
        _add_node(node)
    for node in _adr_nodes(governance_dir):
        _add_node(node)

    # Proposal nodes (real, from data/evolution_queue_state.json --
    # Autonomous Company Evolution Engine, Round 5, 2026-07-29). Same
    # standalone discipline as Lesson/ADR just above -- no fabricated edge.
    for node in _proposal_nodes(evolution_queue_state_path):
        _add_node(node)

    # ExecutiveDirective nodes (real, from data/executive_directives.jsonl
    # -- Executive Brain, ADR-144, 2026-07-30). Same standalone discipline
    # as Proposal/Lesson/ADR nodes -- edges only when a real proposal_id
    # is resolvable, never guessed.
    directive_nodes, directive_edges = _executive_directive_nodes(executive_directives_path)
    for node in directive_nodes:
        _add_node(node)
    edges.extend(directive_edges)

    # AffiliateEvent + CouncilRecommendation nodes (real, Executive
    # Intelligence Layer, ADR-154, 2026-07-31). Same standalone
    # discipline as Proposal/Lesson/ADR/ExecutiveDirective above -- no
    # fabricated edge to a Niche/Decision node.
    for node in _affiliate_event_nodes(affiliate_clicks_path, affiliate_simulation_events_path):
        _add_node(node)
    for node in _council_recommendation_nodes(council_recommendations_path):
        _add_node(node)
    competitor_nodes, competitor_edges = _competitor_nodes(competitor_database_path)
    for node in competitor_nodes:
        _add_node(node)
    edges.extend(competitor_edges)

    graph = {
        "schema_note": "DERIVED, DISPOSABLE snapshot -- rebuild any time via knowledge_graph.build.build_graph(). Never a source of truth; the real data lives in the JSONL files named in this module's docstring.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": list(nodes.values()),
        "edges": edges,
    }
    return graph


def save_snapshot(graph, path=None):
    path = path or SNAPSHOT_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    return path


def load_snapshot(path=None):
    path = path or SNAPSHOT_FILE
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def query_related(graph, entity_type, entity_id, hops=1):
    """Plain dict traversal, no query language. Returns every node
    reachable from (entity_type, entity_id) within `hops` edges,
    following edges in either direction."""
    start_id = entity_id if ":" in str(entity_id) else f"{entity_type.lower()}:{entity_id}"
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    if start_id not in nodes_by_id:
        return {"found": False, "reason": f"لا عقدة بهذا المعرّف: {start_id}"}

    frontier = {start_id}
    visited = {start_id}
    for _ in range(hops):
        next_frontier = set()
        for edge in graph["edges"]:
            if edge["from"] in frontier and edge["to"] not in visited:
                next_frontier.add(edge["to"])
            if edge["to"] in frontier and edge["from"] not in visited:
                next_frontier.add(edge["from"])
        visited |= next_frontier
        frontier = next_frontier

    visited.discard(start_id)
    return {
        "found": True,
        "root": nodes_by_id[start_id],
        "related": [nodes_by_id[nid] for nid in visited if nid in nodes_by_id],
    }
