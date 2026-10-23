"""Galaxy Forge social distribution engine (GF-DISTRIBUTION-ENGINE-v1.0, 2026-10-23).

Offers from every business arm -> platform-native drafts for LinkedIn, TikTok,
Instagram and X -> content QA -> human approval -> publication through a gated
adapter OR a manual hand-off package -> verification -> measurement.

Builds on what already exists and does not duplicate it:
  product_registry.py                      stable product ids and verified listing states
  content_generation/repurposing_engine.py  deterministic copy from real fields
  channels/write_gate.py                    the factory's live-write switch
  affiliate/registry.py, affiliate/content_qa.py, brand_dna.py
Nothing here posts by default; no adapter has a real transport.
"""
