"""OpenClaw Factory — Economics Engine v1

Single source of truth for unit economics. Replaces the $30 price floor.
Constitution §16 (Butter Principle) = a PROFIT floor, not a price floor.

Standalone module — zero imports from the rest of the factory. Reads its
config from config/economics.json (edit that file, not this code — see
V3.0: "Prefer configuration over hardcoded values").
"""

import sys
import json


class EconomicsConfigError(Exception):
    """Raised when config/economics.json is missing or malformed. A missing
    config is a deployment bug, not a runtime condition — this never
    silently falls back to hardcoded defaults."""
    pass


def load_config(path="config/economics.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise EconomicsConfigError(f"economics config not found at: {path}")
    except (json.JSONDecodeError, ValueError) as e:
        raise EconomicsConfigError(f"economics config at {path} is malformed: {e}")
    except OSError as e:
        raise EconomicsConfigError(f"economics config at {path} could not be read: {e}")


def _platform_config(platform, config):
    platforms = config.get("platforms", {})
    if platform not in platforms:
        raise ValueError(f"unknown platform: {platform}")
    return platforms[platform]


def royalty_rate(price, platform, config):
    pconf = _platform_config(platform, config)

    if "royalty_tiers" in pconf:
        for tier in pconf["royalty_tiers"]:
            if tier["min_price"] <= price <= tier["max_price"]:
                return tier["rate"]
        raise ValueError(f"no royalty tier matched price {price} for platform {platform}")

    if "royalty_rate" in pconf:
        return pconf["royalty_rate"]

    raise ValueError(f"platform {platform} has neither royalty_tiers nor royalty_rate in config")


def net_profit(price, platform, config, page_count=None):
    pconf = _platform_config(platform, config)

    if platform == "kdp_ebook":
        rate = royalty_rate(price, platform, config)
        gross = price * rate
        if rate in pconf.get("applies_delivery_cost_to_tier", []):
            gross -= pconf["delivery_cost_per_mb_usd"] * pconf["assumed_file_size_mb"]
        return round(max(0.0, gross), 4)

    if platform == "kdp_paperback":
        if page_count is None:
            raise ValueError("page_count required")
        rate = pconf["royalty_rate"]
        print_cost = pconf["printing_cost_base_usd"] + (pconf["printing_cost_per_page_usd"] * page_count)
        return round(max(0.0, price * rate - print_cost), 4)

    if platform == "gumroad_digital":
        rate = pconf["royalty_rate"]
        return round(price * rate - pconf.get("flat_fee_usd", 0.0), 4)

    raise ValueError(f"unknown platform: {platform}")


def in_dead_zone(price, platform, config):
    dead_zones = config.get("dead_zone", {})
    if platform not in dead_zones:
        return False
    dz = dead_zones[platform]
    if not dz.get("enabled", False):
        return False
    return dz["min_price"] <= price <= dz["max_price"]


def evaluate(price, platform, config, page_count=None):
    floor = config["min_net_profit_per_unit_usd"]
    rate = royalty_rate(price, platform, config)
    net = net_profit(price, platform, config, page_count=page_count)
    dead = in_dead_zone(price, platform, config)

    if dead:
        approved = False
        reason = f"dead_zone: ${price:.2f} nets less than a $9.99 ebook and sells less"
    elif net < floor:
        approved = False
        reason = f"weak_margin: net ${net:.2f} below floor ${floor:.2f}"
    else:
        approved = True
        reason = f"ok: net ${net:.2f} clears floor ${floor:.2f}"

    return {
        "price": price,
        "platform": platform,
        "royalty_rate": rate,
        "net_profit": net,
        "min_required": floor,
        "in_dead_zone": dead,
        "approved": approved,
        "reason": reason,
    }


def price_landscape(platform, config, candidate_prices=None):
    """Deliberately does NOT return a single "best" price. With zero sales
    recorded anywhere in this factory (see Task 12/13-A's finance audit),
    there is no demand model — per-unit net profit alone cannot tell you
    which price sells more units, so ranking candidates and picking #1 is
    just the old $30 rule wearing a spreadsheet. This function surfaces the
    two genuinely different questions ("best inside the high-volume 70%
    tier" vs. "best net margin overall, unproven") side by side and forces
    the caller to read the warning rather than blindly take a top pick."""
    if candidate_prices is None:
        defaults = {
            "kdp_ebook": [2.99, 4.99, 6.99, 7.99, 8.99, 9.99, 19.99, 24.99, 29.99],
        }
        candidate_prices = defaults.get(platform, [])

    ranked = []
    for price in candidate_prices:
        try:
            result = evaluate(price, platform, config)
        except Exception as e:
            result = {"price": price, "platform": platform, "error": str(e), "approved": False, "net_profit": -1}
        ranked.append(result)

    approved_ranked = sorted(
        [r for r in ranked if r.get("approved")],
        key=lambda r: r["net_profit"],
        reverse=True,
    )

    volume_tier_ranked = [r for r in approved_ranked if r.get("royalty_rate") == 0.70]
    volume_tier_best = volume_tier_ranked[0] if volume_tier_ranked else None
    margin_tier_best = approved_ranked[0] if approved_ranked else None

    def _entry(result, rationale):
        if result is None:
            return None
        return {"price": result["price"], "net_profit": result["net_profit"], "rationale": rationale}

    same_price = (
        volume_tier_best is not None
        and margin_tier_best is not None
        and volume_tier_best["price"] == margin_tier_best["price"]
    )

    volume_tier_optimum = _entry(
        volume_tier_best,
        "highest net profit inside KDP's 70% tier — the high-volume band",
    )
    margin_tier_optimum = _entry(
        margin_tier_best,
        "highest net profit at 35% tier — requires proven demand at this price",
    )
    if same_price:
        # Same object for both, per spec, and the warning says so explicitly.
        margin_tier_optimum = volume_tier_optimum

    warning = "NO DEMAND MODEL EXISTS. Zero sales recorded. Per-unit profit does not equal total profit. Do not choose a price from this output alone."
    if same_price:
        warning += " (volume_tier_optimum and margin_tier_optimum are the same price.)"

    return {
        "platform": platform,
        "volume_tier_optimum": volume_tier_optimum,
        "margin_tier_optimum": margin_tier_optimum,
        "approved_prices": sorted(ranked, key=lambda r: r.get("net_profit", -1), reverse=True),
        "warning": warning,
    }


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw.strip() else {}
            if not isinstance(payload, dict):
                payload = {}
        except (json.JSONDecodeError, ValueError):
            emit({"error": "invalid JSON on stdin", "approved": False})
            return

        price = payload.get("price")
        platform = payload.get("platform")
        page_count = payload.get("page_count")

        if price is None or platform is None:
            emit({"error": "price and platform are required", "approved": False})
            return

        config = load_config()
        result = evaluate(float(price), str(platform), config, page_count=page_count)
        emit(result)
    except Exception as e:
        emit({"error": str(e), "approved": False})


if __name__ == "__main__":
    main()
