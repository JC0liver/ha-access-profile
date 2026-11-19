# Access profile for HACS integrations (prototype)

A prototype of an automated per-release **Access profile** for Home Assistant custom integrations listed in HACS and the core Marketplace. Each release gets one of four levels, set by the most serious thing a static scan finds:

| Level | Meaning |
|---|---|
| 🟢 Standard | Talks to its device or service and creates entities |
| 🔵 Extended | Reaches beyond its own device |
| 🟠 High access | Can affect the whole system or the user's browser |
| 🔴 Needs review | Can't be checked automatically; a person has to look |

> Automated check of a release. Not a security review, and not an endorsement by the Open Home Foundation. A finding says the code *could* do something; many are by design.

## What's here

| Path | What it is |
|---|---|
| `proposal.md` | The proposal: how the app (add-on) rating works, why it doesn't transfer, signals, existing tools, the level model, where it would run, test results, open questions |
| `prior-art.md` | Existing efforts in Home Assistant and comparable plugin ecosystems |
| `marshal-test.md` | Comparison with the community app Marshal on the same integrations |
| `prototype/scan.py` | Static scanner. Parses Python with `ast` and never imports or runs the scanned code. `scan_v1`–`v3` are earlier rule versions |
| `prototype/deps.py` | Looks up exactly pinned requirements in OSV, merging aliases |
| `prototype/levels.py` | Maps findings to levels and writes `ui/data/profiles.json` |
| `prototype/run100*/` | Random samples (seeded lists) and hand-check write-ups. Scan outputs are not included |
| `prototype/full/` | Full-catalog list and sparse clone script |
| `ui/custom_components/access_profile/` | Mockup integration: adds the Access profile line to the core Marketplace repository page, plus an overview panel at `/access-profile` |
| `testbed/` | Throwaway Home Assistant 2026.11.2 in Docker (localhost only) to run the mockup |

## Running it

1. Fetch the HACS catalog, `https://data-v2.hacs.xyz/integration/data.json`, into `untrusted/catalog-full/integration.json`. Write the repository list to `prototype/full/sample.tsv` (one `owner/repo<TAB>tag` per line).
2. Clone into `untrusted/repos-full/` with `prototype/full/clone.sh` (sparse, shallow, at the release tag). Treat everything cloned as untrusted and never run it.
3. `python -I prototype/scan.py untrusted/repos-full/* > prototype/full/scan-results.json`
4. `python -I prototype/deps.py prototype/full/scan-results.json`
5. `python -I prototype/levels.py`, which writes `ui/data/profiles.json`
6. `testbed/start.ps1`, then `testbed/onboard.py`. Open `http://127.0.0.1:8124`, then Marketplace and any integration.

No scan results are committed. Re-run the steps above to produce them.

## Limits

- **What it scans:** the source at the release tag, not a `zip_release` asset HACS may install.
- **What it can't see:** frontend JavaScript isn't analysed, and code built or downloaded at runtime is invisible. Requirements of requirements aren't checked.
- **Accuracy:** the rules were checked by hand on random samples of 100 (see `proposal.md` section 7). Full-catalog results are not hand-checked.
