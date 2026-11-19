# Marshal test run, 2026-11-19

Marshal is cyberjunky's Home Assistant app (`cyberjunky/home-assistant-apps/app-marshal`). I tested it at commit `7ee612d5b072e17ea6a4cd96808fd5f7d3330cfd` (v0.2.3), at Josh's request.

## How it was run

- **Code read first:** before running anything I read `tools/survey.py`, `tools/mock.py`, the Dockerfile and requirements, and grepped `src/` for execution, file writes and network calls. Downloaded archives are read in memory and never extracted or run. Network calls go only to the hosts its DOCS list.
- **Sandbox:**
  - Docker image `python:3.14-slim` plus only `aiohttp` and `packaging`.
  - Run as uid 65534 with `--cap-drop ALL`, `no-new-privileges` and `--read-only` (tmpfs `/tmp`).
  - Marshal's code and the scanned repos were mounted read-only; output went to `untrusted/marshal-out/`.
- **Command:** `python -m tools.survey --local /scan --out /out` (its own dev tool: scans folders, writes `report.html` and `report.json`).
- **Network allowed:** Marshal fetched the HACS catalog, HA install counts, OSV and PyPI, as documented.
- **Inputs:** the same clones as our scanner: the popular 10, run100b and run100c (210 integrations). All scanned; no failures.

## Results

Marshal grades across the 210: A 190, B 8, C 5, D 5, F 2.

| Our level | Marshal grades |
|---|---|
| Standard (166) | A 160, B 2, C 2, D 2 (the Ds are pinned vulnerable dependencies) |
| Extended (26) | A 22, B 2, D 1, F 1 |
| High access (16) | A 8, B 4, C 1, D 2, F 1 |
| Needs review (2) | C 2 (dreame-vacuum, WebRTC) |

### What Marshal misses that we catch

- **dreame-vacuum: C 77.** Only "endpoint that needs no login" fired. It found nothing for the obfuscated `frontend.py`, the encrypted payload from the author's server, or the JavaScript added to every dashboard. Its DOCS say front-end JS is counted, not analysed.
- **WebRTC: C 77.** Only "starts other programs" (medium) fired. Downloading the go2rtc binary, making it executable and running it with no hash check isn't flagged.
- **TLS off rated low:** certificate checks turned off count as low for integrations that declare themselves local. That accounts for most of our High access integrations getting an A. One example is mcp-assist (B 88), which always disables verification while sending a bearer token.

### What Marshal catches that we miss

- **Known-vulnerable pinned requirements (OSV):**
  - dte_rates pins `pypdf==5.4.0` (about 60 published CVEs, mostly DoS on crafted PDFs);
  - predistribuce pins `lxml==5.3.0` (an XXE CVE);
  - voip_stack pins `dnspython==2.8.0` (2 CPU-exhaustion CVEs).
  - The count shown is inflated: dte_rates shows "x115" because each CVE is listed twice.
- **Runtime package install through HA's own installer:** pyscript calls `homeassistant.requirements.async_process_requirements` (`requirements.py:198`). Our check only knows `install_package`.
- **Credential and data-access checks:** HA auth/token APIs, `.storage` names, reading all config entries, reading all states while naming internet hosts.
- **Performance checks:** listeners on every state change, blocking calls in the event loop.

### Where its grade misleads

- **Spook: F 44.** This is Frenck's integration. The grade comes from auth/user references, reading all config entries and all-events listeners, which is what Spook does by design (it finds broken references). Alarmo D 51 and OIDC D 55 are the same story: they touch HA auth because that's their job.
- **Real weaknesses graded well:** recalbox, with a shell command built from the configured host and an unauthenticated endpoint that changes entity state, gets B 80, and mcp-assist gets B 88. A "B" reads as fine.
- **A grade mixes very different things:** performance (15%) and upkeep (10%) sit in the same number as security, so a slow but harmless integration and a risky one can land on the same grade.

## Takeaways for the proposal

1. **Borrow:** OSV checks on pinned requirements, the `async_process_requirements` runtime-install check, and the credential/data-access checks. Add them as reasons; auth access probably belongs at Extended with author explanations.
2. **Keep our model:** levels set by the worst finding, with a Needs review gate. A weighted grade let the two most concerning integrations in the whole set score C, and gave a core maintainer's integration an F.
3. **Neither tool reads frontend JavaScript.** It's the blind spot both share, and dreame-vacuum shows why it matters.
4. Marshal is one day old and changing fast (five releases on 2026-11-19), so these results are a snapshot of v0.2.3.
