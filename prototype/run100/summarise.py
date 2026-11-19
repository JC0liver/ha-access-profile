"""Apply levels.py rules to a scan-results file and print a summary. Usage: python -I summarise.py <scan-results.json>"""
import collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from levels import CHECKS, RANK  # our own code
rows = json.load(open(sys.argv[1]))
lv = collections.Counter(); by_check = collections.Counter(); repos_check = collections.defaultdict(set)
nocc = []
out = []
for r in rows:
    if not r["domains"]:
        nocc.append(r["repo"]); continue
    trig = sorted({f["check"] for f in r["findings"] if f["check"] in CHECKS}, key=lambda c: -RANK[CHECKS[c][0]])
    level = CHECKS[trig[0]][0] if trig else "standard"
    lv[level] += 1
    for c in trig: repos_check[c].add(r["repo"])
    out.append((level, r["repo"], trig, r["py_lines"], r["parse_errors"][:1]))
print("levels:", dict(lv), "no custom_components:", len(nocc), nocc)
print("repos per check:", {c: len(s) for c, s in sorted(repos_check.items(), key=lambda x: -len(x[1]))})
for o in sorted(out, key=lambda o: -RANK[o[0]]):
    if o[0] in ("review", "high"): print(o)
