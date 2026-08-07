"""Global Search (new, ADR-185, 2026-08-07) -- the founder's Executive
Mission Control directive: "Search everything... Products, Customers,
Knowledge, Files, Agents, Logs, Revenue, Ideas, Competitors, Tasks."

A real, honest, substring search across already-real, already-persisted
sources -- never a fabricated "AI-powered semantic search" claim this
factory can't back up. Primary source is the real knowledge graph
snapshot (data/knowledge_graph_snapshot.json, 4308+ real nodes across
Niche/Decision/MarketAnalysis/ProductionRun/PublishChannel/AIProvider/
Lesson/ADR/Proposal/ExecutiveDirective/CouncilRecommendation --
knowledge_graph/build.py, regenerated once daily), covering most of the
directive's named categories in one already-built structure. Two real
sources not yet in the graph are searched directly: competitors
(data/competitor_database.json) and real generated products
(books/_generation_log.jsonl).

Customers/Files/Agents/Logs/Tasks are honestly NOT indexed here: this
factory has zero real customer records (confirmed elsewhere this
session), no real per-agent process model to search (agents are
stateless prompt calls), and file/log search would mean indexing the
whole repo -- a much larger, separate undertaking, not attempted as a
side effect of this feature. Disclosed in the result set's own
`sources_searched` field, never silently omitted."""

import json
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
_KG_SNAPSHOT_PATH = _FACTORY_ROOT / "data" / "knowledge_graph_snapshot.json"
_COMPETITOR_DB_PATH = _FACTORY_ROOT / "data" / "competitor_database.json"
_GENERATION_LOG_PATH = _FACTORY_ROOT / "books" / "_generation_log.jsonl"

SOURCES_SEARCHED = ("knowledge_graph", "competitors", "generated_products")
SOURCES_NOT_INDEXED = ("customers (0 real records exist)", "files", "agents (no real process model)", "logs", "tasks")


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path):
    records = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _search_knowledge_graph(query_lower):
    snapshot = _read_json(_KG_SNAPSHOT_PATH, {})
    nodes = snapshot.get("nodes") or []
    matches = []
    for n in nodes:
        label = str(n.get("label") or "")
        if query_lower in label.lower() or query_lower in str(n.get("id") or "").lower():
            matches.append({
                "source": "knowledge_graph", "type": n.get("type"), "id": n.get("id"), "label": label,
            })
    return matches, snapshot.get("generated_at")


def _search_competitors(query_lower):
    db = _read_json(_COMPETITOR_DB_PATH, {})
    matches = []
    if isinstance(db, dict):
        for niche, entries in db.items():
            if query_lower in niche.lower():
                matches.append({"source": "competitors", "type": "Niche", "id": niche, "label": niche, "competitor_count": len(entries) if isinstance(entries, list) else None})
    return matches


def _search_generated_products(query_lower):
    records = _read_jsonl(_GENERATION_LOG_PATH)
    seen_titles = set()
    matches = []
    for r in records:
        title = str(r.get("title") or r.get("topic") or "")
        if not title or title in seen_titles:
            continue
        if query_lower in title.lower():
            seen_titles.add(title)
            matches.append({
                "source": "generated_products", "type": "Product", "id": r.get("file"), "label": title,
                "price": r.get("price"), "product_type": r.get("product_type"),
            })
    return matches


def search(query, limit=50):
    """Real, case-insensitive substring search. Never ranks by an
    invented relevance score -- results are grouped by source, each
    group in the order its underlying file already has them (knowledge
    graph: build order; generated products: chronological)."""
    query = (query or "").strip()
    if not query:
        return {"query": query, "results": [], "total": 0, "sources_searched": list(SOURCES_SEARCHED), "sources_not_indexed": list(SOURCES_NOT_INDEXED)}

    query_lower = query.lower()
    kg_matches, kg_as_of = _search_knowledge_graph(query_lower)
    competitor_matches = _search_competitors(query_lower)
    product_matches = _search_generated_products(query_lower)

    all_matches = kg_matches + competitor_matches + product_matches
    return {
        "query": query,
        "results": all_matches[:limit],
        "total": len(all_matches),
        "truncated": len(all_matches) > limit,
        "sources_searched": list(SOURCES_SEARCHED),
        "sources_not_indexed": list(SOURCES_NOT_INDEXED),
        "knowledge_graph_as_of": kg_as_of,
    }
