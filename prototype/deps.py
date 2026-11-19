"""v4: known vulnerabilities in exactly pinned requirements (manifest.json "pkg==x.y").

Reads scan-results files, asks OSV (api.osv.dev) about each pinned package/version, and adds
"vulnerable_dependency" (any HIGH/CRITICAL advisory) or "vulnerable_dependency_low" findings in place.
Only package names and versions are sent. Each advisory is counted once (OSV ids, deduplicated).
Unpinned requirements are skipped: the version pip picks is not known until install time.
Usage: python -I deps.py <scan-results.json> [...]
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

PIN = re.compile(r"^\s*([A-Za-z0-9_.\-\[\]]+?)(?:\[[^\]]*\])?\s*==\s*([A-Za-z0-9_.+!\-]+)\s*(?:;.*)?$")
UA = {"User-Agent": "access-profile-prototype", "Content-Type": "application/json"}


def post(url: str, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=UA, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def get(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def severity(vuln: dict) -> str:
    sev = (vuln.get("database_specific") or {}).get("severity") or ""
    for aff in vuln.get("affected", []):
        sev = sev or (aff.get("database_specific") or {}).get("severity") or ""
    return sev.upper()


def main(paths: list[str]) -> int:
    files = {p: json.loads(Path(p).read_text(encoding="utf-8")) for p in paths}
    pins: set[tuple[str, str]] = set()
    for rows in files.values():
        for r in rows:
            for m in r["manifest"].values():
                for req in (m or {}).get("requirements") or []:
                    if mt := PIN.match(req):
                        pins.add((mt.group(1).lower(), mt.group(2)))
    pins_l = sorted(pins)
    hits: dict[tuple[str, str], list[str]] = {}
    for i in range(0, len(pins_l), 500):
        chunk = pins_l[i:i + 500]
        res = post("https://api.osv.dev/v1/querybatch",
                   {"queries": [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in chunk]})
        for (n, v), out in zip(chunk, res.get("results", [])):
            ids = sorted({x["id"] for x in out.get("vulns", [])})
            if ids:
                hits[(n, v)] = ids
    details: dict[str, str] = {}
    aliases: dict[str, set[str]] = {}
    for vid in sorted({i for ids in hits.values() for i in ids}):
        try:
            v = get(f"https://api.osv.dev/v1/vulns/{vid}")
            details[vid] = severity(v)
            aliases[vid] = set(v.get("aliases", [])) | {vid}
        except OSError:
            details[vid] = ""
            aliases[vid] = {vid}
    # One flaw is often listed under several ids (GHSA, CVE, PYSEC): merge ids that share an alias
    for key, ids in list(hits.items()):
        groups: list[tuple[set[str], list[str]]] = []
        for i in ids:
            for names, members in groups:
                if names & aliases[i]:
                    names |= aliases[i]
                    members.append(i)
                    break
            else:
                groups.append((set(aliases[i]), [i]))
        hits[key] = [sorted(m, key=lambda x: (not x.startswith("GHSA"), x))[0] for _, m in groups]
        for _, members in groups:  # a merged flaw takes the highest severity of its ids
            rep = sorted(members, key=lambda x: (not x.startswith("GHSA"), x))[0]
            if any(details.get(m) in ("HIGH", "CRITICAL") for m in members):
                details[rep] = details[rep] if details.get(rep) in ("HIGH", "CRITICAL") else "HIGH"
    print(f"pinned packages: {len(pins_l)}, with known vulnerabilities: {len(hits)}, distinct advisories: {sum(len(v) for v in hits.values())}")

    for path, rows in files.items():
        for r in rows:
            r["findings"] = [f for f in r["findings"] if not f["check"].startswith("vulnerable_dependency")]
            for domain, m in r["manifest"].items():
                for req in (m or {}).get("requirements") or []:
                    mt = PIN.match(req)
                    key = (mt.group(1).lower(), mt.group(2)) if mt else None
                    if key not in hits:
                        continue
                    ids = hits[key]
                    sevs = [details.get(i, "") for i in ids]
                    serious = any(s in ("HIGH", "CRITICAL") for s in sevs)
                    r["findings"].append({
                        "check": "vulnerable_dependency" if serious else "vulnerable_dependency_low",
                        "sev": "high" if serious else "medium",
                        "file": f"custom_components/{domain}/manifest.json", "line": 0,
                        "detail": f"{req}: {len(ids)} advisories "
                                  f"({sum(s in ('HIGH', 'CRITICAL') for s in sevs)} high/critical), e.g. {', '.join(ids[:3])}"})
        Path(path).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    for (n, v), ids in sorted(hits.items()):
        print(f"  {n}=={v}: {len(ids)} advisories, {sum(details.get(i) in ('HIGH', 'CRITICAL') for i in ids)} high/critical")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
