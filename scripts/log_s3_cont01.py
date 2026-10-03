import json, datetime
now = datetime.datetime.now(datetime.timezone.utc).isoformat()

records = [
    {"asset": "nostr:58ab41906d349b59", "channel": "nostr", "classification": "OBSERVED", "evidence_type": "public_existence", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "data/nostr_service_post.json: FTC compliance post (relay rotation)", "timestamp": now, "verification_status": "verified"},
    {"asset": "nostr:5bc427e14c99137a", "channel": "nostr", "classification": "OBSERVED", "evidence_type": "public_existence", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "data/nostr_service_post.json: Turo dispute toolkit post 2/2 relays", "timestamp": now, "verification_status": "verified"},
    {"asset": "telegra.ph/FTC-Consumer-Review-Rule-Compliance-Guide-for-Small-Businesses-2026-10-02", "channel": "telegraph", "classification": "OBSERVED", "evidence_type": "public_existence", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "data/telegraph_ftc_article.json", "timestamp": now, "verification_status": "verified"},
]

with open("data/commercial_evidence.jsonl", "a", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")

cyc = {"cycle_id": "S3-EXEC-05-CONT-01", "at": now, "publications": ["nostr:58ab41906d349b59 (FTC)", "nostr:5bc427e14c99137a (Turo)", "telegraph:FTC guide"], "sales": 0, "revenue": 0, "cost_usd": 0, "founder_interventions": 0, "diagnosis": "DISTRIBUTION_GAP CONFIRMED + MEASUREMENT_GAP CONFIRMED", "next": "monitor window to 2026-10-05", "commit": "pending"}
with open("data/production_cycles.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(cyc) + "\n")

print(f"logged {len(records)} evidence records")
