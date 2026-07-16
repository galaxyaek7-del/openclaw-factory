"""
Real-world signal intake (ADR-056) — reads real external signals already
present in this factory and shapes each into the (niche, external_signal)
contract orchestrator.run_cycle()/profit_oracle.opportunity_score() already
accept (ADR-038) — reusing that exact, existing contract, never inventing
a new signal shape.

Two real sources, both already produced by this factory's existing
research work, neither invented for this layer:
  OPPORTUNITIES.md            parsed via profit_oracle._read_opportunities()
                               itself (reused directly — the same real
                               parser profit_oracle.run_oracle() already
                               uses), not a second implementation of its
                               line format.
  tier1_intake/candidates/*.json  real Tier-1 research files (ADR-035/036),
                                   each already carrying a real source
                                   block (GitHub stars / HN points) in
                                   exactly the external_signal shape.
"""

import json
from pathlib import Path

import profit_oracle

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TIER1_CANDIDATES_DIR = _FACTORY_ROOT / "tier1_intake" / "candidates"


def intake_from_opportunities_md():
    """Reuses profit_oracle._read_opportunities() directly — no second
    parser for OPPORTUNITIES.md's line format."""
    niches = profit_oracle._read_opportunities()
    return [{"niche": n, "external_signal": None, "source": "OPPORTUNITIES.md"} for n in niches]


def intake_from_tier1_candidates(candidates_dir=None):
    directory = Path(candidates_dir) if candidates_dir else DEFAULT_TIER1_CANDIDATES_DIR
    if not directory.is_dir():
        return []

    signals = []
    for path in sorted(directory.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        niche = data.get("niche")
        if not niche:
            continue

        source = data.get("source") or {}
        external_signal = None
        if source.get("platform") == "github" and source.get("stars") is not None:
            external_signal = {"source": "github", "stars": source["stars"], "created_at": source.get("created_at")}
        elif source.get("platform") == "hacker_news" and source.get("points") is not None:
            external_signal = {"source": "hacker_news", "points": source["points"], "created_at": source.get("created_at")}

        signals.append({"niche": niche, "external_signal": external_signal, "source": path.name})

    return signals


def collect_all_real_signals(candidates_dir=None):
    return intake_from_opportunities_md() + intake_from_tier1_candidates(candidates_dir=candidates_dir)
