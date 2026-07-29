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
LESSONS_LEARNED_DIR = os.path.join(FACTORY_DIR, 'OpenClaw_Brain', '19_Lessons_Learned')
GOVERNANCE_DIR = os.path.join(FACTORY_DIR, 'OpenClaw_Brain', '00_Governance')
EVOLUTION_QUEUE_STATE_FILE = os.path.join(FACTORY_DIR, 'data', 'evolution_queue_state.json')
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
        nodes.append(_node(f"adr:{match.group(1)}", "ADR", label=title, source_file=filename))
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


def build_graph(decisions_path=None, analyses_path=None, ledger_path=None, ai_cost_log_path=None,
                 evidence_path=None, lessons_dir=None, governance_dir=None, evolution_queue_state_path=None):
    decisions = _read_jsonl(decisions_path or DECISIONS_FILE)
    analyses = _read_jsonl(analyses_path or MARKET_INTELLIGENCE_ANALYSES_FILE)
    ledger = _read_jsonl(ledger_path or SALES_LEDGER_FILE)
    ai_costs = _read_jsonl(ai_cost_log_path or AI_COST_LOG_FILE)
    evidence = _read_jsonl(evidence_path or MARKET_EVIDENCE_FILE)

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
