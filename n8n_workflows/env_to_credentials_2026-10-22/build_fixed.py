"""Builds fixed n8n workflow JSON from the live exports. No secrets are written:
nodes reference credentials by id/name; the chat id is a placeholder that the
apply step fills from .env and refuses to proceed without."""
import json, os, sys, copy
SP = os.path.dirname(os.path.abspath(__file__))
HDR = {"id": "GFinternalTokn01", "name": "GF Internal Service Token (X-Internal-Token)"}
TG = {"id": "GFtelegramBot001", "name": "GF Telegram Bot"}
CHAT_PLACEHOLDER = "__GF_TELEGRAM_CHAT_ID__"
KEEP = ("id", "name", "active", "nodes", "connections", "settings", "staticData", "pinData", "meta", "description")

def internal_token_auth(node):
    p = node["parameters"]
    hp = p.get("headerParameters", {}).get("parameters", [])
    rest = [h for h in hp if h.get("name", "").lower() != "x-internal-token"]
    assert len(rest) < len(hp), (node["name"], "no X-Internal-Token header to replace")
    if rest:
        p["headerParameters"]["parameters"] = rest
    else:
        p.pop("headerParameters", None); p.pop("sendHeaders", None)
    p["authentication"] = "genericCredentialType"
    p["genericAuthType"] = "httpHeaderAuth"
    node["credentials"] = {"httpHeaderAuth": dict(HDR)}

def telegram_node(node):
    assert "api.telegram.org" in node["parameters"].get("url", "")
    return {"parameters": {"resource": "message", "operation": "sendMessage",
                           "chatId": CHAT_PLACEHOLDER, "text": "={{ $json.message }}",
                           "additionalFields": {"appendAttribution": False}},
            "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
            "position": node["position"], "id": node["id"], "name": node["name"],
            "credentials": {"telegramApi": dict(TG)}}

out = {}
for fn in sorted(os.listdir(os.path.join(SP, "live"))):
    w = json.load(open(os.path.join(SP, "live", fn), encoding="utf-8"))
    w = {k: w[k] for k in KEEP if k in w}
    changes = []
    nodes = []
    for n in w["nodes"]:
        n = copy.deepcopy(n)
        s = json.dumps(n.get("parameters", {}))
        if n["type"] == "n8n-nodes-base.httpRequest" and "api.telegram.org" in s:
            n = telegram_node(n); changes.append(f"{n['name']}: HTTP+$env -> Telegram node + credential")
        elif n["type"] == "n8n-nodes-base.httpRequest" and "INTERNAL_SERVICE_TOKEN" in s:
            internal_token_auth(n); changes.append(f"{n['name']}: $env header -> Header Auth credential")
        if n["type"] == "n8n-nodes-base.httpRequest" and n["parameters"].get("url", "") != n["parameters"].get("url", "").strip():
            n["parameters"]["url"] = n["parameters"]["url"].strip(); changes.append(f"{n['name']}: stripped trailing whitespace from URL")
        nodes.append(n)
    w["nodes"] = nodes
    left = [n["name"] for n in nodes if "$env" in json.dumps(n.get("parameters", {}))]
    assert not left, (fn, "still uses $env", left)
    json.dump(w, open(os.path.join(SP, "fixed", fn), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    out[w["name"]] = changes
print(json.dumps(out, ensure_ascii=False, indent=1))
