#!/usr/bin/env python3
"""
rollup.py - Build the organization landing dashboard (profile/README.md) from
every competition tracker in the org.

Discovery is by REPO TOPIC, not by name: any repo tagged `competition` that
contains a competition.yml is included, so trackers can be named anything.

Env:
  GITHUB_TOKEN  (required)  provided automatically inside GitHub Actions
  ORG           (optional)  defaults to BudakGPT
  TOPIC         (optional)  defaults to "competition"

Only the region between AUTO:START / AUTO:END in profile/README.md is replaced;
the manual header and footer around it are preserved.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required:  pip install pyyaml")

ORG = os.environ.get("ORG", "BudakGPT")
TOPIC = os.environ.get("TOPIC", "competition")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "profile" / "README.md"

AUTO_START = "<!-- AUTO:START -->"
AUTO_END = "<!-- AUTO:END -->"

# Display order and label for each status group.
STATUS_ORDER = ["active", "submitted", "upcoming", "won", "lost", "archived"]
STATUS_LABEL = {
    "active": "Active", "submitted": "Submitted", "upcoming": "Upcoming",
    "won": "Awarded", "lost": "Concluded", "archived": "Archived",
}
SECTION_TITLE = {
    "active": "Active",
    "submitted": "Submitted, awaiting results",
    "upcoming": "Upcoming",
    "won": "Awarded",
    "lost": "Past competitions",
    "archived": "Archive",
}


def api_get(path: str):
    req = urllib.request.Request(API + path)
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("User-Agent", "budakgpt-rollup")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def list_competition_repos() -> list[dict]:
    repos, page = [], 1
    while True:
        batch = api_get(f"/orgs/{ORG}/repos?per_page=100&page={page}&type=all")
        if not batch:
            break
        repos.extend(r for r in batch if TOPIC in (r.get("topics") or []))
        if len(batch) < 100:
            break
        page += 1
    return repos


def fetch_config(repo: str) -> dict | None:
    data = api_get(f"/repos/{ORG}/{repo}/contents/competition.yml")
    if not data or "content" not in data:
        return None
    try:
        return yaml.safe_load(base64.b64decode(data["content"]).decode("utf-8")) or {}
    except yaml.YAMLError:
        return None


def parse_date(value):
    if not value:
        return None
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        return None


def next_deadline(timeline):
    today = dt.date.today()
    best = None
    for m in timeline or []:
        if m.get("done"):
            continue
        d = parse_date(m.get("date"))
        if d and (best is None or d < best[1]):
            best = (m.get("milestone", "Milestone"), d)
    if not best:
        return None
    return (best[0], best[1], (best[1] - today).days)


def progress(deliverables):
    items = deliverables or []
    if not items:
        return (0, 0, 0)
    done = sum(1 for d in items if d.get("done"))
    return (done, len(items), round(100 * done / len(items)))


def bar(pct: int) -> str:
    filled = round(pct / 10)
    return "`" + "█" * filled + "░" * (10 - filled) + f"` {pct}%"


def deadline_cell(nd) -> str:
    if nd is None:
        return "Complete"
    name, date, days = nd
    if days < 0:
        return f"Overdue: {name}"
    if days == 0:
        return f"Today: {name}"
    unit = "day" if days == 1 else "days"
    return f"{name}, {days} {unit} ({date.isoformat()})"


def build_rows(entries: list[dict]) -> str:
    rows = ["| Competition | Status | Next milestone | Progress | Code |",
            "| :--- | :--- | :--- | :--- | :--- |"]
    for e in entries:
        cfg = e["cfg"]
        name = cfg.get("name", e["repo"])
        organizer = cfg.get("organizer", "")
        title = f"**[{name}]({e['url']})**"
        if organizer:
            title += f"<br><sub>{organizer}</sub>"
        status = STATUS_LABEL.get(cfg.get("status", "active"), "Active")
        nd = next_deadline(cfg.get("timeline"))
        done, total, pct = progress(cfg.get("deliverables"))
        prog = bar(pct) if total else "n/a"
        code = (cfg.get("links") or {}).get("code") or ""
        code_cell = f"[Open]({code})" if code else "Private"
        rows.append(f"| {title} | {status} | {deadline_cell(nd)} | {prog} | {code_cell} |")
    return "\n".join(rows)


def summary_strip(entries: list[dict]) -> str:
    active_n = sum(1 for e in entries if e["cfg"].get("status") == "active")

    # nearest deadline across every pending milestone
    nearest = None
    for e in entries:
        nd = next_deadline(e["cfg"].get("timeline"))
        if nd and nd[2] >= 0 and (nearest is None or nd[2] < nearest[0]):
            nearest = (nd[2], e["cfg"].get("name", e["repo"]), nd[1])
    if nearest:
        days, cname, ddate = nearest
        unit = "day" if days == 1 else "days"
        nearest_cell = f"**{cname}**<br><sub>{days} {unit} ({ddate.isoformat()})</sub>"
    else:
        nearest_cell = "None pending"

    # overall deliverable progress across all competitions
    tot_done = tot_all = 0
    for e in entries:
        d, t, _ = progress(e["cfg"].get("deliverables"))
        tot_done += d
        tot_all += t
    pct = round(100 * tot_done / tot_all) if tot_all else 0
    overall = f"{bar(pct)}<br><sub>{tot_done} of {tot_all} deliverables</sub>"

    return (
        '<div align="center">\n\n'
        "| Active | Nearest deadline | Overall progress |\n"
        "| :---: | :---: | :---: |\n"
        f"| **{active_n}** | {nearest_cell} | {overall} |\n\n"
        "</div>"
    )


def build_auto_block(repos: list[dict]) -> str:
    entries = []
    for r in repos:
        cfg = fetch_config(r["name"])
        if cfg is not None:
            entries.append({"repo": r["name"], "url": r["html_url"], "cfg": cfg})

    groups: dict[str, list] = {}
    for e in entries:
        groups.setdefault(e["cfg"].get("status", "active"), []).append(e)

    def sort_key(e):
        nd = next_deadline(e["cfg"].get("timeline"))
        return nd[1] if nd else dt.date.max
    for st in groups:
        groups[st].sort(key=sort_key)

    today = dt.date.today().isoformat()
    parts = [AUTO_START,
             "<!-- Generated by scripts/rollup.py. Do not edit inside this block. -->",
             ""]

    if not entries:
        parts += ["No competitions are being tracked yet. Create one with "
                  "`ops/new-competition.ps1`.", ""]
    else:
        parts += [
            summary_strip(entries),
            "",
            f'<div align="center"><sub>{len(entries)} tracked &nbsp;·&nbsp; '
            f"updated {today}</sub></div>",
            "",
            "---",
            "",
        ]
        for st in STATUS_ORDER:
            if groups.get(st):
                parts += [f"### {SECTION_TITLE.get(st, st.title())}", "",
                          build_rows(groups[st]), ""]

    parts += [AUTO_END]
    return "\n".join(parts)


def splice(existing: str, block: str) -> str:
    if AUTO_START in existing and AUTO_END in existing:
        return existing.split(AUTO_START)[0] + block + existing.split(AUTO_END, 1)[1]
    return existing.rstrip() + "\n\n" + block + "\n"


def main() -> None:
    repos = list_competition_repos()
    print(f"Found {len(repos)} repo(s) tagged '{TOPIC}' in {ORG}")
    block = build_auto_block(repos)
    existing = PROFILE.read_text(encoding="utf-8") if PROFILE.exists() else ""
    PROFILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE.write_text(splice(existing, block), encoding="utf-8")
    print("Wrote profile/README.md")


if __name__ == "__main__":
    main()
