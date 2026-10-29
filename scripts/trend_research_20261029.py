"""Record the 2026-10-29 trend research and evaluate the six initial candidates.

Every source below was read in this session through a web-search index summary
(access_method WEB_SEARCH_INDEX), not by opening Pinterest or Etsy pages, and not
through any API. Figures are restated as the source gave them; listing prices are
competitor list prices, not sales. No Pinterest Trends index reading was taken:
the tool needs a signed-in session, so no first-party search-volume figure exists
here and the demand dimension says so.

Idempotent: sources/signals dedupe by id; an opportunity is re-recorded only if
its signal set changed. Writes data/trend_to_product/*.jsonl and the dashboard
state data/trend_to_product_state.json. Fetches nothing, publishes nothing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trend_to_product import ideation, linkage, records, scoring  # noqa: E402

DAY = "2026-10-29"
WSI = "WEB_SEARCH_INDEX"


def S(url, kw, topic, st, title, notes=None, use="CITATION_ONLY"):
    return records.record_source(url, DAY, kw, topic, st, WSI, use, title=title, notes=notes)["source_id"]


def G(t, topic, claim, srcs, value=None, label="OBSERVED"):
    return records.record_signal(t, topic, claim, srcs, DAY, value=value, label=label)["signal_id"]


def main():
    # ---- platform rules
    terms = S("https://conductatlas.com/platform/pinterest/pinterest-terms-of-service/provision/CA-P-023734/"
              "prohibition-on-unauthorized-data-scraping/", "pinterest scraping terms", "platform_rules",
              "THIRD_PARTY_ESTIMATE", "Pinterest ToS provision record (third-party restatement)",
              "restates the ToS clause; not a legal determination")
    forum = S("https://community.pinterest.biz/t/inquiry-about-using-pinterest-images-and-obtaining-official-"
              "permission/39124", "pinterest images permission", "platform_rules", "PLATFORM_TERMS",
              "Pinterest developer community reply (Sept 2025)")
    help_ = S("https://help.pinterest.com/business/article/pinterest-trends", "pinterest trends method",
              "platform_rules", "OFFICIAL_PLATFORM_REPORT", "Pinterest Trends help page")
    G("PLATFORM_RULE", "platform_rules", "Pinterest terms prohibit collecting content by automated means "
      "without express prior permission; systematically finding and using Pinterest images falls under it.",
      [terms, forum])
    G("PLATFORM_RULE", "platform_rules", "Pinterest Trends values are relative (ratio to all searches, peak "
      "indexed to 100), not search counts; reading them needs the Trends tool.", [help_])

    # ---- Pinterest Predicts 2026 (secondary coverage of the official report)
    smt = S("https://www.socialmediatoday.com/news/pinterest-publishes-2026-trend-predictions-report/807452/",
            "pinterest predicts 2026", "pinterest_predicts_2026", "SECONDARY_COVERAGE",
            "Social Media Today on Pinterest Predicts 2026", use="SIGNAL_ONLY")
    ped = S("https://www.pedestrian.tv/style/pinterest-predicts-2026/", "pinterest predicts 2026 crochet",
            "pinterest_predicts_2026", "SECONDARY_COVERAGE", "Pedestrian.tv on Pinterest Predicts 2026",
            use="SIGNAL_ONLY")
    fr = S("https://jai-un-pote-dans-la.com/pinterest-predicts-2026/", "pinterest predicts 2026 crochet",
           "pinterest_predicts_2026", "SECONDARY_COVERAGE", "French summary of Pinterest Predicts 2026",
           use="SIGNAL_ONLY")
    crochet_trend = G("TREND_DIRECTION", "crochet", "Pinterest Predicts 2026 'Laced Up' trend lists crochet "
                      "as a keyword (crochet hats, crocheted phone cases, crochet-collar bombers). No crochet "
                      "search-growth figure was published in the coverage read; the cited +215%/+150% figures "
                      "are lace searches.", [smt, ped, fr])
    kids_trend = G("TREND_DIRECTION", "crochet", "Pinterest Predicts 2026 nostalgic/kids coverage mentions "
                   "crocheted play mats (no figure).", [ped, fr])

    # ---- crochet patterns
    rh1 = S("https://www.rankhero.com/keywords/crochet-pattern", "crochet pattern", "crochet_patterns",
            "THIRD_PARTY_ESTIMATE", "RankHero keyword page: crochet pattern")
    rh2 = S("https://www.rankhero.com/keywords/crochet-patterns", "crochet patterns", "crochet_patterns",
            "THIRD_PARTY_ESTIMATE", "RankHero keyword page: crochet patterns")
    stq = S("https://sellertoolshq.com/guides/etsy-crochet-pattern-selling-guide/", "sell crochet patterns etsy",
            "crochet_patterns", "THIRD_PARTY_ESTIMATE", "SellerToolsHQ crochet pattern guide 2026")
    pat_price = G("PRICE_OBSERVATION", "crochet_patterns", "Etsy 'crochet pattern' listings: median about "
                  "$5.99, range $1.20-$27.99; a second tracker: median $5.80, 91% under $10.", [rh1, rh2],
                  {"currency": "USD", "low": 1.20, "high": 27.99, "median": 5.99})
    pat_comp = G("COMPETITION_DENSITY", "crochet_patterns", "About 726,887 Etsy listings for 'crochet pattern' "
                 "(third-party tracker).", [rh1], {"listings": 726887})
    pat_fmt = G("COMPETING_FORMAT", "crochet_patterns", "Seller guides place beginner patterns at $4-7, "
                "advanced garments at $9-15; amigurumi at the low end.", [stq], {"free_alternatives": False})

    # ---- crochet/craft project planners
    ilc = S("https://www.ilikecrochet.com/wp-content/uploads/ILC-Project-planner-2025.pdf",
            "crochet project planner", "craft_planners", "MARKETPLACE_LISTING", "Free crochet planner PDF")
    cozy = S("https://cozyberrystd.gumroad.com/l/crochethobbytracker", "crochet hobby tracker notion",
             "craft_planners", "MARKETPLACE_LISTING", "Free Notion crochet tracker (Gumroad)")
    bdd = S("https://bddesignsproducts.gumroad.com/l/juypp", "crochet planner sellers", "craft_planners",
            "MARKETPLACE_LISTING", "Canva crochet planner for sellers ($10)")
    plan_fmt = G("COMPETING_FORMAT", "craft_planners", "Free crochet planners with row counters, yarn stash "
                 "and hook charts exist (PDF and Notion); paid ones add seller pages (sales log, pricing "
                 "worksheet).", [ilc, cozy, bdd], {"free_alternatives": True})
    plan_price = G("PRICE_OBSERVATION", "craft_planners", "Paid crochet planners observed at $9.99-$10 "
                   "(one editable outlier at $150).", [bdd], {"currency": "USD", "low": 9.99, "high": 150})

    # ---- handmade seller pricing calculators
    cb = S("https://craftybase.com/etsy-pricing-calculator-spreadsheet", "etsy pricing calculator spreadsheet",
           "maker_pricing", "MARKETPLACE_LISTING", "Craftybase free Etsy pricing spreadsheet")
    cp = S("https://www.craftprofessional.com/etsy-pricing-calculator.html", "etsy pricing calculator",
           "maker_pricing", "MARKETPLACE_LISTING", "Craft Professional free pricing worksheet")
    fl = S("https://flevy.com/browse/marketplace/handmade-product-pricing-calculator-for-etsy-sellers-12511",
           "handmade pricing calculator", "maker_pricing", "MARKETPLACE_LISTING", "Flevy Excel dashboard ($45)")
    et1 = S("https://www.etsy.com/listing/4583388910", "etsy pricing calculator spreadsheet", "maker_pricing",
            "MARKETPLACE_LISTING", "Etsy listing: pricing calculator spreadsheet")
    mp_fmt = G("COMPETING_FORMAT", "maker_pricing", "Free pricing spreadsheets/worksheets exist (Craftybase, "
               "Craft Professional). Craftybase's own notes say it covers materials, labour and Etsy fees, "
               "with overhead and shipping tracked separately.", [cb, cp], {"free_alternatives": True})
    mp_price = G("PRICE_OBSERVATION", "maker_pricing", "Paid pricing calculators observed from about $2.24 "
                 "(Etsy sale price) to $45 (Flevy).", [fl, et1], {"currency": "USD", "low": 2.24, "high": 45})

    # ---- reading journals
    rj1 = S("https://www.etsy.com/listing/1819826640", "reading journal printable", "reading_journals",
            "MARKETPLACE_LISTING", "Etsy: reading journal printable ($10.74)")
    rj2 = S("https://www.rankhero.com/keywords/reading-log", "reading log", "reading_journals",
            "THIRD_PARTY_ESTIMATE", "RankHero keyword page: reading log")
    rj3 = S("https://myintentionalbliss.gumroad.com/l/readingjournalprintable", "reading journal printable",
            "reading_journals", "MARKETPLACE_LISTING", "Gumroad reading journal")
    rj_price = G("PRICE_OBSERVATION", "reading_journals", "Paid reading journals/trackers observed at "
                 "$0.71 (sale) to $10.74; most $3-$11.", [rj1, rj3], {"currency": "USD", "low": 0.71, "high": 10.74})
    rj_fmt = G("COMPETING_FORMAT", "reading_journals", "Free printable book trackers are widely available.",
               [rj2], {"free_alternatives": True})

    # ---- printable miniatures
    mi1 = S("https://www.etsy.com/listing/4356370517", "dollhouse miniature printable", "printable_miniatures",
            "MARKETPLACE_LISTING", "Etsy: 1:12 printable props ($4.84, personal use only)")
    mi2 = S("https://www.etsy.com/listing/4464063112", "paper dollhouse printable", "printable_miniatures",
            "MARKETPLACE_LISTING", "Etsy: 3D paper dollhouse ($2.32)")
    mi_price = G("PRICE_OBSERVATION", "printable_miniatures", "Printable miniatures observed at $2.32-$7.82; "
                 "several listings are licensed for personal use only.", [mi1, mi2],
                 {"currency": "USD", "low": 2.32, "high": 7.82})

    # ---- content planning / small-business systems (Notion)
    n1 = S("https://kimdoesbusiness.gumroad.com/l/contenttemplate", "notion content planner", "content_planning",
           "MARKETPLACE_LISTING", "Gumroad Notion content planner ($7)")
    n2 = S("https://dongeo.gumroad.com/l/plugandpost", "content system notion", "content_planning",
           "MARKETPLACE_LISTING", "Gumroad content system ($50, page shows 0 sales)")
    n3 = S("https://www.etsy.com/listing/4544023108", "notion content planner small business",
           "content_planning", "MARKETPLACE_LISTING", "Etsy Notion content planner")
    cp_price = G("PRICE_OBSERVATION", "content_planning", "Notion content planners observed at $7-$50 "
                 "(Etsy up to $34.95); the $50 listing shows 0 sales.", [n1, n2, n3],
                 {"currency": "USD", "low": 7, "high": 50})

    # ---- evaluate the six candidates (one topic x one format each)
    cands = [
        ("Crochet and craft project planning (printable planner)", "craft_planners", "guide_printable",
         [crochet_trend, plan_fmt, plan_price], None),
        ("Original crochet patterns", "crochet_patterns", "craft_pattern",
         [crochet_trend, kids_trend, pat_price, pat_comp, pat_fmt], None),
        ("Handmade seller pricing and profitability calculator", "maker_pricing", "excel_tool",
         [mp_fmt, mp_price],
         {"differentiation": {"score": 3, "label": "INFERRED", "signal_ids": [mp_fmt],
                              "basis": "the leading free sheet leaves overhead and shipping out; a tool that "
                                       "includes them is a stated gap, not a proven demand"}}),
        ("Reading journal and hobby tracker", "reading_journals", "guide_printable", [rj_price, rj_fmt], None),
        ("Printable miniature crafts", "printable_miniatures", "guide_printable", [mi_price], None),
        ("Content planning and small-business operating system (Notion)", "content_planning",
         "notion_template", [cp_price], None),
    ]
    have = {(o["name"], tuple(sorted(o["signal_ids"]))) for o in scoring.latest_opportunities()}
    ops = {}
    for name, topic, fmt, sigs, assess in cands:
        if (name, tuple(sorted(sigs))) not in have:
            scoring.record_opportunity(name, topic, fmt, sigs, assessments=assess,
                                       idea_text=f"{name}: an original product built by the factory")
    for o in scoring.latest_opportunities():
        ops[o["name"]] = o

    # ---- specs for the two candidates with the most recorded evidence
    reg = ideation.load_registry()
    calc = ideation.build_spec(
        ops["Handmade seller pricing and profitability calculator"], "excel_tool",
        "Handmade Order Costing & Pricing Workbook",
        target_customer="makers selling handmade goods online or at markets",
        problem_statement="prices set from materials alone leave out labour, overhead, shipping and platform fees",
        value_proposition="one sheet per product that shows the floor price and margin after every cost",
        differentiation="includes overhead allocation and shipping, which the leading free sheet leaves out",
        deliverables=["XLSX workbook", "PDF quick-start guide"],
        acceptance_tests=["every formula recomputed independently (batch 14 method)",
                          "fee rates cite the platform fee page and its date",
                          "zero Excel error cells", "worked example matches a hand calculation"],
        proposed_price_usd=12, registry=reg)
    pattern = ideation.build_spec(
        ops["Original crochet patterns"], "craft_pattern", "Lace-Edge Crochet Phone Pouch Pattern",
        target_customer="intermediate crocheters following the 2026 lace trend",
        problem_statement="trend coverage names crocheted phone cases; buyers need a tested pattern",
        value_proposition="an original, tested pattern with stitch counts per row",
        differentiation="original design; no third-party pattern or photo used",
        deliverables=["PDF pattern", "stitch-count table"],
        acceptance_tests=["stitch counts per row recomputed by code",
                          "physical test make matches stated gauge and size",
                          "photos are of the factory's own test make"],
        proposed_price_usd=6, registry=reg)
    doc = linkage.write_state()
    print({"sources": doc["counts"], "specs": [(calc["status"], calc["duplication"]["verdict"]),
                                               (pattern["status"], pattern["duplication"]["verdict"])]})


if __name__ == "__main__":
    main()
