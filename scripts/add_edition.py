#!/usr/bin/env python3
"""Merge one edition of Sector Brief content into the site's data files.

Usage:
    python3 scripts/add_edition.py payload.json

payload.json is one JSON object with any of these keys (each a map of id -> document):
    stories        {"2026-10-20-01": {date, order, sector, subindustry, tags, companies,
                                       headline, summary, soWhat, numbers, sources}, ...}
    quizzes        {"2026-10-20": {date, questions: [...10], extra: [...]}, ...}
    companies      {"bank-of-america": {name, sector, subindustry, ticker, hq, size,
                                         businessModel, competitors, updated}, ...}
    subindustries  {"banking": {sector, profileUpdated, overview, marketSize, trends,
                                players, operatingModel, threats, kpis}, ...}
    sectors        {"tmt": {overview?, recap?, recapUpdated?}, ...}

Stories and quizzes are filed into monthly files (data/stories/YYYY-MM.json,
data/quizzes/YYYY-MM.json). Companies, sub-industries and sectors are merged
field by field into data/reference.json, so a partial update only changes the
fields it names. data/index.json is rebuilt at the end.

The script validates ids and required fields and exits with an error message
(writing nothing) if anything is wrong.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

TAXONOMY = {
    "macro": ["macro"],
    "energy-materials": ["oil-gas-upstream", "midstream-lng", "refining-chemicals",
                         "power-utilities", "renewables-transition", "metals-mining"],
    "financial-services": ["banking", "insurance", "asset-wealth", "payments-fintech"],
    "tmt": ["semiconductors", "software-cloud", "internet-platforms",
            "media-entertainment", "telecom"],
    "healthcare": ["pharma-biotech", "medtech", "payers-providers"],
    "consumer-retail": ["retail-ecommerce", "cpg", "agriculture-food", "travel-hospitality"],
    "advanced-industries": ["automotive-mobility", "aerospace-defense", "industrial-machinery"],
    "infrastructure-logistics": ["transport-logistics", "real-estate-construction",
                                 "public-sector"],
}
SUB_TO_SECTOR = {sub: sec for sec, subs in TAXONOMY.items() for sub in subs}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STORY_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
STORY_FIELDS = ["date", "order", "sector", "subindustry", "headline", "summary"]


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def validate(p):
    errors = []
    for sid, s in p.get("stories", {}).items():
        if not STORY_ID_RE.match(sid):
            errors.append(f"story id {sid!r} must look like YYYY-MM-DD-NN")
        for k in STORY_FIELDS:
            if k not in s:
                errors.append(f"story {sid}: missing {k}")
        if s.get("date") and not sid.startswith(s["date"]):
            errors.append(f"story {sid}: id does not start with its date {s.get('date')}")
        sub = s.get("subindustry")
        if sub not in SUB_TO_SECTOR:
            errors.append(f"story {sid}: unknown subindustry {sub!r}")
        elif s.get("sector") != SUB_TO_SECTOR[sub]:
            errors.append(f"story {sid}: sector should be {SUB_TO_SECTOR[sub]!r} for {sub!r}")
    for date, q in p.get("quizzes", {}).items():
        if not DATE_RE.match(date):
            errors.append(f"quiz id {date!r} must be YYYY-MM-DD")
        for i, item in enumerate((q.get("questions") or []) + (q.get("extra") or [])):
            opts = item.get("options") or []
            if len(opts) != 4:
                errors.append(f"quiz {date} item {i}: needs exactly 4 options")
            if item.get("answer") not in (0, 1, 2, 3):
                errors.append(f"quiz {date} item {i}: answer must be 0-3")
            if not item.get("id") or not item.get("prompt"):
                errors.append(f"quiz {date} item {i}: missing id or prompt")
    for cid, c in p.get("companies", {}).items():
        if not SLUG_RE.match(cid):
            errors.append(f"company id {cid!r} must be lowercase-hyphenated")
        if "subindustry" in c and c["subindustry"] not in SUB_TO_SECTOR:
            errors.append(f"company {cid}: unknown subindustry {c['subindustry']!r}")
    for sid in p.get("subindustries", {}):
        if sid not in SUB_TO_SECTOR:
            errors.append(f"unknown subindustry profile id {sid!r}")
    for sid in p.get("sectors", {}):
        if sid not in TAXONOMY:
            errors.append(f"unknown sector id {sid!r}")
    return errors


def merge_fields(target, updates):
    for key, doc in updates.items():
        cur = target.get(key, {})
        cur.update(doc)
        target[key] = cur


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1]) as f:
        payload = json.load(f)
    errors = validate(payload)
    if errors:
        sys.exit("Payload rejected:\n  " + "\n  ".join(errors))

    # Stories and quizzes, filed by month
    by_month = {}
    for sid, s in payload.get("stories", {}).items():
        by_month.setdefault(("stories", s["date"][:7]), {})[sid] = s
    for date, q in payload.get("quizzes", {}).items():
        q = dict(q, date=date)
        by_month.setdefault(("quizzes", date[:7]), {})[date] = q
    for (kind, month), docs in by_month.items():
        path = os.path.join(DATA, kind, f"{month}.json")
        cur = load(path, {})
        cur.update(docs)
        save(path, cur)

    # Reference data, merged field by field
    ref_path = os.path.join(DATA, "reference.json")
    ref = load(ref_path, {"sectors": {}, "subindustries": {}, "companies": {}})
    for key in ("sectors", "subindustries", "companies"):
        merge_fields(ref.setdefault(key, {}), payload.get(key, {}))
    save(ref_path, ref)

    # Index
    def months(kind):
        d = os.path.join(DATA, kind)
        return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json")) if os.path.isdir(d) else []
    story_months = months("stories")
    latest = None
    if story_months:
        latest = max(v["date"] for v in load(os.path.join(DATA, "stories", story_months[-1] + ".json"), {}).values())
    save(os.path.join(DATA, "index.json"), {
        "latest": latest,
        "months": story_months,
        "quizMonths": months("quizzes"),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    n_s = len(payload.get("stories", {}))
    n_q = len(payload.get("quizzes", {}))
    print(f"Merged {n_s} stories, {n_q} quiz(zes), {len(payload.get('companies', {}))} companies, "
          f"{len(payload.get('subindustries', {}))} profiles, {len(payload.get('sectors', {}))} sectors. "
          f"Latest edition: {latest}")


if __name__ == "__main__":
    main()
