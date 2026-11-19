"""Turn scan-results.json into Access profile levels for the UI mockup.

Stdlib only. Reads prototype/scan-results.json, writes ui/data/profiles.json and
refreshes the inlined copy in ui/preview.html. Never fetches anything.
Usage: python -I levels.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCAN = HERE / "scan-results.json"
UI = HERE.parent / "ui"
OUT = UI / "data" / "profiles.json"
PREVIEW = UI / "preview.html"

FOOTER = "Automated check of this release. Not a security review by the Open Home Foundation."

# Levels, lowest to highest (proposal section 5).
LEVELS = [
    {"id": "standard", "label": "Standard", "emoji": "\U0001f7e2", "color": "green",
     "meaning": "Talks to its device or service and creates entities."},
    {"id": "extended", "label": "Extended", "emoji": "\U0001f535", "color": "blue",
     "meaning": "Reaches beyond its own device."},
    {"id": "high", "label": "High access", "emoji": "\U0001f7e0", "color": "orange",
     "meaning": "Can affect the whole system or the user's browser."},
    {"id": "review", "label": "Needs review", "emoji": "\U0001f534", "color": "red",
     "meaning": "Can't be checked automatically. A HACS reviewer has to look at it."},
]
RANK = {lvl["id"]: i for i, lvl in enumerate(LEVELS)}

# check -> (level, plain-English reason). Mapping is exactly the proposal table.
CHECKS = {
    "obfuscation": ("review", "Hides parts of its code (obfuscation)"),
    "bundled_binary": ("review", "Ships compiled or binary files that can't be read"),
    "runtime_pkg_install": ("review", "Downloads and installs packages while running"),
    "subprocess": ("high", "Runs shell commands or other programs"),
    "dynamic_code": ("high", "Executes code built at runtime"),
    "unsafe_deserialise": ("high", "Loads data in a format that can run code"),
    "http_view_no_auth": ("high", "Adds web pages that open without logging in"),
    "frontend_injection": ("high", "Adds remote or inline JavaScript to your dashboards"),
    "tls_verify_off": ("high", "Turns off certificate checks on secure connections"),
    "webhook": ("extended", "Registers webhooks that other services can call"),
    "http_view": ("extended", "Adds web pages for logged-in users"),
    "dynamic_import": ("extended", "Loads Python modules chosen at runtime"),
    # v2 checks (rule tuning after the 100-integration run)
    "subprocess_fixed": ("extended", "Runs a fixed external program (for example ffmpeg)"),
    "http_view_selfauth": ("extended", "Adds web pages that check the login in their own code"),
    "frontend_card": ("extended", "Adds its own card or panel JavaScript to dashboards"),
    # v3 checks (after the holdout run)
    "make_executable": ("review", "Makes a file executable while running (download-and-run)"),
    "http_view_static": ("extended", "Serves static files without login"),
    # v4 checks (from the Marshal comparison)
    "auth_read": ("extended", "Reads Home Assistant user accounts"),
    "auth_write": ("high", "Changes Home Assistant users, logins or login internals"),
    "all_config_entries": ("extended", "Reads every integration's configuration"),
    "private_storage": ("extended", "Uses Home Assistant's private storage folder directly"),
    "secret_files": ("high", "Names Home Assistant's secret files or tokens"),
    "vulnerable_dependency": ("high", "Pins a package version with known vulnerabilities"),
    "vulnerable_dependency_low": ("extended", "Pins a package version with known low or moderate vulnerabilities"),
}
# Hard-coded hosts are listed under "Contacts" only; they never set the level.

# Per-repo facts not in scan-results.json, typed in by hand.
# Release tag and display name: HACS catalog data (last_version, manifest_name),
# matching the tags the repos were cloned at (proposal section 7).
# Downloads: proposal section 7.
REPOS = {
    "nielsfaber_alarmo": ("Alarmo", "v1.10.19", "85k"),
    "frenck_spook": ("Spook", "v5.11.1", "70k"),
    "PiotrMachowski_Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor":
        ("Xiaomi Cloud Map Extractor", "v2.2.5", "65k"),
    "davidrapan_ha-solarman": ("Solarman", "v25.08.16", "63k"),
    "wuwentao_midea_ac_lan": ("Midea AC LAN", "v2026.10.0", "57k"),
    "dummylabs_thewatchman": ("Watchman", "v0.8.4", "51k"),
    "Tasshack_dreame-vacuum": ("Dreame Vacuum", "v2.0.3", "50k"),
    "ollo69_ha-smartthinq-sensors": ("SmartThinQ LGE Sensors", "v0.43.0", "49k"),
    "custom-components_pyscript": ("Pyscript Python scripting", "2.1.1", "22k"),
    "christiaangoossens_hass-oidc-auth": ("OIDC Authentication", "v1.2.1", "22k"),
}

# Sample author explanations. Written by us for the mockup, NOT by the authors.
SAMPLE_NOTES = {
    "custom-components_pyscript": "pyscript runs your Python scripts; executing code is its purpose",
    "christiaangoossens_hass-oidc-auth": "Login pages must be reachable before sign-in",
}

# Sample levels the proposal lists (section 5). Used only to report mismatches.
EXPECTED = {  # v4 levels, as in the proposal sample table
    "Tasshack_dreame-vacuum": "review",
    "custom-components_pyscript": "review",
    "christiaangoossens_hass-oidc-auth": "high",
    "dummylabs_thewatchman": "high",
    "frenck_spook": "high",
    "nielsfaber_alarmo": "extended",
    "wuwentao_midea_ac_lan": "extended",
}


def link(repo: str, tag: str, domain: str, f: dict) -> dict:
    url = f"https://github.com/{repo}/blob/{tag}/{f['file']}"
    if f["line"]:
        url += f"#L{f['line']}"
    short = f["file"].removeprefix(f"custom_components/{domain}/")
    return {"label": f"{short}:{f['line']}" if f["line"] else short,
            "url": url, "detail": f["detail"]}


def pick_links(findings: list[dict], n: int = 3) -> list[dict]:
    """Up to n findings, one per file first, then further lines."""
    chosen, files = [], set()
    findings = sorted(findings, key=lambda f: f["line"] == 0)  # prefer real line numbers
    for f in findings:
        if f["file"] not in files:
            chosen.append(f)
            files.add(f["file"])
    chosen += [f for f in findings if f not in chosen]
    return chosen[:n]


def count_text(findings: list[dict]) -> str:
    n, files = len(findings), len({f["file"] for f in findings})
    places = f"{n} place{'s' if n != 1 else ''}"
    return places if files == 1 or n == files else f"{places} in {files} files"


# Samples shown in the UI: (id, label, scan results relative to HERE, sample list or None)
SAMPLES = [
    ("popular", "Popular 10", "scan-results.json", None),
    ("run100", "Random 100 (used to tune rules)", "run100/scan-results.json", "run100/sample.tsv"),
    ("run100b", "Random 100 (holdout 1, shaped v3)", "run100b/scan-results.json", "run100b/sample.tsv"),
    ("run100c", "Random 100 (holdout 2, clean test)", "run100c/scan-results.json", "run100c/sample.tsv"),
]
CATALOG = HERE.parent / "untrusted" / "catalog" / "integration.json"  # HACS catalog data (JSON, read only)
# Full-catalog run: when its results exist, the UI shows it instead of the samples
FULL = ("full", "Full catalog", "full/scan-results.json", "full/sample.tsv")
CATALOG_FULL = HERE.parent / "untrusted" / "catalog-full" / "integration.json"


def load_catalog() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in (CATALOG, CATALOG_FULL):  # the fresher full-run catalog wins
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            out.update({v["full_name"].lower(): v for v in data.values()})
    return out


def load_tags(rel: str | None) -> dict[str, str]:
    if not rel:
        return {}
    tags = {}
    for line in (HERE / rel).read_text(encoding="utf-8").splitlines():
        repo, _, tag = line.partition("\t")
        tags[repo.replace("/", "_", 1)] = tag.strip() or "HEAD"
    return tags


def fmt_downloads(n: int | None) -> str:
    if not n:
        return ""
    return f"{n / 1000:.0f}k" if n >= 1000 else str(n)


CAT: dict[str, dict] = {}
TAGS: dict[str, str] = {}


def profile(r: dict, sample: str = "popular") -> dict:
    owner, _, name = r["repo"].partition("_")
    repo = f"{owner}/{name}"
    if r["repo"] in REPOS:
        display, tag, downloads = REPOS[r["repo"]]
    else:
        cat = CAT.get(repo.lower(), {})
        display = cat.get("manifest_name") or name
        tag = TAGS.get(r["repo"]) or cat.get("last_version") or "HEAD"
        downloads = fmt_downloads(cat.get("downloads"))
    domain = r["domains"][0]
    by_check: dict[str, list[dict]] = {}
    for f in r["findings"]:
        by_check.setdefault(f["check"], []).append(f)

    reasons = []
    for check, fs in by_check.items():
        if check not in CHECKS:
            continue
        lvl, text = CHECKS[check]
        if check == "dynamic_code" and all("embedded interpreter" in f["detail"] for f in fs):
            text = "Executes code in an embedded interpreter"
        reasons.append({"check": check, "level": lvl, "text": text, "count": len(fs),
                        "count_text": count_text(fs),
                        "links": [link(repo, tag, domain, f) for f in pick_links(fs)]})
    reasons.sort(key=lambda x: (-RANK[x["level"]], -x["count"]))
    level = reasons[0]["level"] if reasons else "standard"

    note = None
    if r["repo"] in SAMPLE_NOTES:
        note = {"text": SAMPLE_NOTES[r["repo"]], "sample": True,
                "source": "Sample text written by the Security group for this mockup, not by the author."}

    return {"repo": repo, "name": display, "domain": domain,
            "version": (r["manifest"].get(domain) or {}).get("version"),
            "tag": tag, "downloads": downloads, "level": level, "reasons": reasons,
            "hosts": r["hosts"], "author_note": note, "sample": sample,
            "repo_url": f"https://github.com/{repo}/tree/{tag}"}


def main() -> int:
    CAT.update(load_catalog())
    scans = json.loads(SCAN.read_text(encoding="utf-8"))
    all_profiles, samples = [], []
    for sid, label, rel, tsv in ([FULL] if (HERE / FULL[2]).is_file() else SAMPLES):
        path = HERE / rel
        if not path.is_file():
            continue
        TAGS.clear()
        TAGS.update(load_tags(tsv))
        rows = json.loads(path.read_text(encoding="utf-8"))
        all_profiles += [profile(r, sid) for r in rows if r["domains"]]
        samples.append({"id": sid, "label": label, "count": len(rows)})
    profiles = sorted(all_profiles, key=lambda p: (-RANK[p["level"]], p["name"].lower()))
    TAGS.clear()
    data = {"generated_from": [s[2] for s in SAMPLES], "footer": FOOTER,
            "levels": LEVELS, "samples": samples, "integrations": profiles}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=1, ensure_ascii=False)
    OUT.write_text(text + "\n", encoding="utf-8")

    if PREVIEW.is_file():  # keep the inlined preview copy in sync
        html = PREVIEW.read_text(encoding="utf-8")
        block = text.replace("</", "<\\/")
        html, n = re.subn(r'(<script id="profiles" type="application/json">).*?(</script>)',
                          lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), html, flags=re.S)
        if n:
            PREVIEW.write_text(html, encoding="utf-8")

    mismatches = 0
    for r in scans:
        key, got = r["repo"], profile(r)["level"]
        want = EXPECTED.get(key, "standard")
        flag = "" if got == want else f"   MISMATCH: proposal says {want}"
        mismatches += bool(flag)
        print(f"{key:80} {got}{flag}")
    print(f"wrote {OUT}", file=sys.stderr)
    if mismatches:
        print(f"{mismatches} level(s) differ from the proposal sample; rules left as written.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
