import json, datetime
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
records = [
    {"asset": "nostr:46e6a952193bb7e2", "channel": "nostr", "classification": "OBSERVED", "evidence_type": "public_existence", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "data/nostr_service_post.json: Trademark kit post 1/2 relays", "timestamp": now, "verification_status": "verified"},
    {"asset": "telegra.ph GPSR guide + FTC guide", "channel": "telegraph", "classification": "OBSERVED", "evidence_type": "liveness_check", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "HEAD 200 x2", "timestamp": now, "verification_status": "verified"},
    {"asset": "gumroad 14-product sweep", "channel": "gumroad", "classification": "OBSERVED", "evidence_type": "liveness_check", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "data/gumroad_url_validation.json: 14/14 HTTP 200", "timestamp": now, "verification_status": "verified"},
]
with open("data/commercial_evidence.jsonl", "a", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")
cyc = {"cycle_id": "S3-EXEC-05-CONT-02", "at": now, "publications": ["nostr:46e6a952193bb7e2 (Trademark)"], "maintenance": ["telegraph x2 live", "gumroad 14/14 live"], "sales": 0, "revenue": 0, "cost_usd": 0, "founder_interventions": 0, "next": "monitor window to 2026-10-05"}
with open("data/production_cycles.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(cyc) + "\n")
print(f"logged {len(records)} records")
