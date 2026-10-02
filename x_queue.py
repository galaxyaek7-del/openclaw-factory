"""Queued X-post executor: fires due posts through distributor (protection +
ledger enforced). --once prints one JSON line. Silent unless a post sent.
Queue file: data/x_post_queue.json [{text, status}]. Idempotent: sent posts
never re-fire (status flipped before publish returns... no — flipped only
on verified ok; on failure the post stays queued and protection backs off).
Never bypasses publish_protection or safe_mode."""
import json
import os

QUEUE_PATH = "data/x_post_queue.json"

# Placeholders resolved at fire time from env (memory only, never stored):
#   {{SYSTEME_URL}} -> systeme_affiliate.get_affiliate_url()
# The tracked URL is NEVER written to the queue file or any log.
PLACEHOLDERS = ("{{SYSTEME_URL}}",)


def _resolve_placeholders(text):
    if "{{SYSTEME_URL}}" not in text:
        return text
    import systeme_affiliate as SA

    return text.replace("{{SYSTEME_URL}}", SA.get_affiliate_url())


def _load_dotenv():
    try:
        with open(".env", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() and k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()
    except OSError:
        pass


def main():
    _load_dotenv()
    try:
        queue = json.load(open(QUEUE_PATH))
    except (OSError, ValueError):
        print(json.dumps({"checked": 0, "action": "no-queue"}))
        return
    import safe_mode as SM
    import distributor
    import schemas.product as S
    from channels import publish_protection as P

    for post in queue:
        if post.get("status") != "queued":
            continue
        if SM.is_subsystem_safe_mode("marketplace_publishing"):
            print(json.dumps({"checked": 1, "action": "safe-mode-hold"}))
            return
        gate = P.check_publish_allowed("x")
        if not gate.get("allowed"):
            print(json.dumps({"checked": 1, "action": "protection-hold",
                              "reason": str(gate.get("reason"))[:120]}))
            return
        job = S.Product(
            title="", subtitle="", description=_resolve_placeholders(post["text"]),
            price_usd=39.0,
            file_path="", cover_path="", tags=[], language="en",
            source_id=post.get("id", "X-QUEUED-01"), raw_price_hint=None,
            needs_pricing=False, price_source="queued-post",
        )
        res = distributor.distribute(job, arm_names=["x"], dry_run=False)[0]
        r = res.get("result")
        if r and r.ok and r.url:
            post["status"] = "sent"
            post["url"] = r.url
            post["sent_at"] = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat()
            json.dump(queue, open(QUEUE_PATH, "w"), indent=1)
            print(json.dumps({"checked": 1, "action": "sent", "url": r.url}))
        else:
            err = str((r.error if r else res.get("skip_reason")))[:150]
            # Non-retryable: payment/quota errors must not loop forever.
            if any(k in err for k in ("402", "credits depleted", "Payment Required",
                                      "403", "401", "Forbidden", "Unauthorized")):
                post["status"] = "blocked-payment"
                post["block_reason"] = err
                json.dump(queue, open(QUEUE_PATH, "w"), indent=1)
                print(json.dumps({"checked": 1, "action": "blocked-payment",
                                  "err": err}))
            else:
                print(json.dumps({"checked": 1, "action": "failed-held",
                                  "err": err}))
        return
    print(json.dumps({"checked": len(queue), "action": "silent"}))


if __name__ == "__main__":
    main()
