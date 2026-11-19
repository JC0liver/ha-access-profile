# Proposal: security signals for HACS integrations

2026-11-19. Idea 01, raised by Josh. Draft for the Security group.

## Summary

1. Don't copy the app 1–8 number. App ratings score declared sandbox settings. A custom integration has no sandbox, so a number would claim more than it can measure.
2. Instead, give each release an **Access profile**: one of four levels (Standard, Extended, High access, Needs review), set by the most serious thing found. Under it, plain reasons such as "runs shell commands" or "adds JavaScript to dashboards", plus maintenance facts. No points, no "safe" wording.
3. Add one hard gate to HACS default-list inclusion and to each new release: obfuscated code or runtime code download means manual review.
4. Compute it in the existing HACS catalog pipeline (`data-v2.hacs.xyz`, regenerated every 2 h). Both HACS and the new core Marketplace already read that catalog. Owners: ludeeus (pipeline), Frenck (Marketplace display), Security group (rules).
5. The prototype was tested on 310 integrations: 10 popular ones plus three random samples of 100, with every High access and Needs review result checked by hand. On the last clean sample 2 of 9 High access levels were wrong.
   - It found dreame-vacuum (obfuscated code that phones home and adds JavaScript to every dashboard) and WebRTC (downloads and runs a binary with no checksum).
   - It also found a few real weaknesses in third-party integrations.
   - By-design hits (pyscript, OIDC login pages, Spook's user services) need an author explanation.
   - A community app built today, Marshal, uses a weighted A–F grade. Run on the same 210 integrations, it rated dreame-vacuum and WebRTC "C" and Spook "F". That supports levels over a grade. Its dependency, runtime-install and credential checks were added here (section 7).

---

## 1. How the app (add-on) rating works today

Source: `home-assistant/supervisor` tag `2026.11.0` (commit `c1c6f0a7`).

- `supervisor/apps/utils.py:26-97` `rating_security()`: starts at **5**, clamped to **1–8**.
  - AppArmor: disabled −1, custom profile +1 (`:35-38`)
  - Ingress +2; otherwise no host network and no published ports +2; otherwise `auth_api` +1 (`:41-48`)
  - Signed +1 (`:51-52`). This never applies: `apps/model.py:836-838` `signed` always returns `False` ("Currently no signing support").
  - Any of the capabilities BPF, CHECKPOINT_RESTORE, DAC_READ_SEARCH, NET_ADMIN, NET_RAW, PERFMON, SYS_ADMIN, SYS_MODULE, SYS_PTRACE or SYS_RAWIO, or kernel modules: −1 once (`:55-73`)
  - `hassio_role` manager −1 / admin −2 (`:76-79`); `host_network` −1 (`:82-83`); `host_pid` −2 (`:86-87`); `host_uts` + SYS_ADMIN −1 (`:90-91`)
  - `docker_api` or `full_access`: rating forced to **1** (`:94-95`)
- Exposed as `rating` in `api/store.py:156` and `api/apps.py:252`.
- Shown in the frontend (`home-assistant/frontend` tag `20261028.6`, `src/panels/config/apps/app-view/info/supervisor-app-info.ts:315-334`) as a "Rating" chip: green ≥6, yellow 3–5, red ≤2. Help text: "This shows the security rating of the app on a scale from 1 to {max}. Higher is better."
- **What it claims:** only how much host access the app's *declared config* asks for. It never looks at the code inside the container, and it says nothing about vulnerabilities or trustworthiness.
- **Docs drift:** developer docs (`developers.home-assistant.io` `docs/apps/presentation.md:205-224`, commit `8da484e`) say the scale is "1 to 6". They also leave out the "+2 for no exposed ports" rule and four of the ten capabilities. That's a small docs fix worth raising.

## 2. Why it doesn't transfer

- An app runs in a container. The rating works because Supervisor *enforces* what config declares (AppArmor, capabilities, network namespace). Declared config is the security boundary.
- A custom integration runs in Core's Python process with full access: every token, the file system, the network, `subprocess`, and the ability to add HTTP views and frontend JS. `manifest.json` declares nothing that is enforced. There is no boundary to score.
- **What a score can mean:** "automated checks found or didn't find these risky patterns in this release, and the repo follows these practices."
- **What it can't mean:** safe, reviewed, or endorsed. A malicious author can avoid every pattern check (see the gaming notes in section 5). A clean result is weak evidence. A hit is a pointer for review, not a verdict.

## 3. Available signals and how reliable they are

| Signal | Source | Reliability |
|---|---|---|
| Repo archived, release practice, last update, open issues | catalog / GitHub API | High as facts, weak as security signals. 364 of 5,404 catalog integrations have a `last_updated` older than a year, and 53 have no releases at all. |
| `requirements` pinning | manifest.json | **Misleading.** Hassfest tells custom integrations *not* to pin packages Core ships (`script/hassfest/requirements.py:564-580` @ core `2026.11.2`). Pin status can't be scored naively. |
| Known-vulnerable requirements | OSV | **Useful for exact pins only.** Across the 310 integrations, 68 distinct packages are pinned with `==`, and 5 of those pins have known advisories (for example `pypdf==5.4.0`: 67 distinct advisories, 20 high or critical). OSV lists one flaw under several ids (GHSA, CVE, PYSEC), so counts must be merged by alias; Marshal shows 115 for that pin. Unpinned requirements get whatever pip picks at install time, and requirements of requirements aren't checked. |
| Credential and data access (HA auth API, every config entry, `.storage`, `secrets.yaml`, Supervisor token) | AST scan | Precise. Almost always by design (user-management, auth and config tools), so it informs rather than alarms. Changing users or reading the config-entries file is High access; reading users is Extended. |
| Runtime package install (`install_package`, `async_process_requirements`) | AST scan | Precise. Rare: pyscript installs packages users ask for. |
| subprocess / shell, eval/exec, pickle/unsafe YAML, TLS off | AST scan | Good precision once tuned. Many hits are by design (pyscript is an interpreter). |
| Unauthenticated `HomeAssistantView`, webhooks | AST scan | Precise to detect. Whether a hit matters depends on what the view serves; auth integrations need unauth login pages. |
| Frontend JS injection (`add_extra_js_url`, Lovelace resource creation) | AST scan | Precise. A high-value signal: it runs third-party JS in every user's browser session. |
| Obfuscation (renamed imports, encoded string hiding, huge base64) | heuristics | Medium. Large base64 blobs are often images; this needs a tuned allowlist. |
| Hard-coded remote hosts | string literals | Noisy as a score input (cloud integrations need them). Useful as a disclosed list. |
| Bundled binaries | file magic / extension | Precise. None found in the sample. |
| Repo practices (branch protection, token permissions, pinned actions, security policy) | OpenSSF Scorecard | Mature, but only 2 of 11 sampled repos had public Scorecard data. It would have to be run ourselves (it uses the GitHub API only and never executes repo code). |

**Blind spot:** HACS can install a release asset instead of the source tree (`hacs.json` `zip_release` + `filename`, validated in `custom_components/hacs/validate/hacsjson.py:33-35` @ HACS `2.0.5`). The scan must run on what HACS actually installs, or a repo can show clean source and ship a different zip. It also only covers the default list. Users can add any repo as a custom repository.

## 4. What already exists

- **HACS action** (`hacs/action` `22.5.0`): metadata checks only (archived, brands, description, hacs.json, images, information, issues, topics). It also validates the manifest schema (`validate/integration_manifest.py`). No security checks. Note: `action.yml` at the tag still runs `ghcr.io/hacs/action:main`, so pinning the action tag doesn't pin the code.
- **hacs/default inclusion CI** (`.github/workflows/checks.yml` @ `cb45ca3`): owner, editable, releases, removed, existing, core-domain-conflict, hassfest (`:236-262`, image `hassfest:latest`) and the HACS action (`:264-271`). It runs **once at inclusion**. Later releases install with no check at all.
- **hassfest** for a single integration runs `INTEGRATION_PLUGINS` (`script/hassfest/plugins.py:8-33` @ core `2026.11.2`). For custom integrations that means compatibility, not security: requirements must not conflict with or pin Core's packages (`requirements.py:491-582`). The quality-scale checks skip non-core integrations (`quality_scale.py:2040`).
- **Integration quality scale:** core only, and about code quality, not security.
- **Kill switch that already exists:** the HACS `critical` list. HACS checks it every 6 h (`base.py:651`). Any listed repo that is installed gets uninstalled automatically (`base.py:1026-1076`, uninstall at `:1071`). The core Marketplace has the same mechanism and raises a CRITICAL repair (`homeassistant/components/marketplace/critical.py`). The list holds only a `test/test` entry, so it has never been used for real.
- **Core Marketplace** (PR #183502 by Frenck, merged 2026-10-01, present in `2026.11.0`) reads the same catalog as HACS, `https://data-v2.hacs.xyz` (`marketplace/profiles.py:92`). Its schema **drops unknown keys** (`marketplace/utils/validate.py:188-192`). A new catalog field won't break anything, but displaying it needs a core change.
- **Second kill switch in Core:** `BLOCKED_CUSTOM_INTEGRATIONS` (`homeassistant/loader.py:138` @ `2026.11.2`) stops listed custom integrations below a set version from loading. It also covers manual installs, but so far it has only been used for stability blocks.
- **HACS's current position:** "HACS does not perform security assessments, code audits, or vulnerability reviews of the repositories listed in its store" (hacs/integration#5175, closed 2026-03). This proposal would change that position, so ludeeus has to agree to it.
- **Prior art** (details and sources in `prior-art.md`):
  - Nothing equivalent exists for HA. A few small community tools scan on the user's own instance: jrx-code/hassio-security-sandbox, DrMurx/haxsec, psewar/marketplace-guard.
  - Closest outside model: Obsidian Community (May 2026). Its plugins are also in-process and unsandboxed. It scans every version and shows word labels, not a number.
  - **Marshal** (cyberjunky/home-assistant-apps, app-marshal, first released 2026-11-19): a Home Assistant app that scans the integrations installed on the user's own machine.
    - It gives a weighted 0–100 score and an A–F grade across five areas: data 30%, code 25%, network 20%, performance 15%, upkeep 10%.
    - Its checks are a superset of ours, apart from download-and-run and frontend JavaScript.
    - It needs read access to the whole config folder, including `secrets.yaml` and `.storage`.
    - Test results are in `marshal-test.md` and section 7.
  - Closest check engine: grafana/plugin-validator. It uses Semgrep, ClamAV and OSV, and it diffs the release archive against the source, which would close the `zip_release` blind spot.
- **Off-the-shelf scanners:** Bandit and Semgrep (Python SAST), OSV/pip-audit (dependencies), OpenSSF Scorecard (repo practice). Use these instead of a home-grown engine. My prototype is AST-only to keep it dependency-free, and the HA-specific checks (views, webhooks, JS injection) would be custom Semgrep rules.

## 5. Scoring models

### Recommended: Access profile (four levels)

Builds on Model A below. Each release gets one level, set by the **highest** trigger found. Levels are not added up, so nothing can average a serious finding away.

| Level | Meaning | Triggered by |
|---|---|---|
| 🟢 **Standard** | Talks to its device or service and creates entities | No flags |
| 🔵 **Extended** | Reaches beyond its own device | Webhooks, authenticated web pages (or pages that check the login in their own code, or serve static files), dynamic imports, its own bundled dashboard card, running a fixed program such as ffmpeg, reading HA user accounts, reading every integration's configuration, using `.storage` directly, pinned packages with low/moderate advisories |
| 🟠 **High access** | Can affect the whole system or the user's browser | Runs shell or built-up commands, executes dynamic code, unsafe deserialisation, unauthenticated web pages, adds remote or inline JavaScript to dashboards, TLS verification off, changes HA users or logins, names secret files (`secrets.yaml`, `core.config_entries`, Supervisor token), pinned packages with high/critical advisories |
| 🔴 **Needs review** | Can't be checked automatically | Obfuscated code, runtime code or package download (including HA's own installer), download-and-run (a file made executable), bundled binaries or unchecked `.pyc`, release zip differs from tagged source |

- **Name:** "Access profile". It's neutral, describes what the integration reaches, and sits naturally beside the app "Rating" chip. Avoid "safe", "secure" or "trusted"; they read as an OHF endorsement. Other names considered: "What this integration does", "Code check", "Risk profile".
- **Reasons:** under the level, show each reason in plain language with links to the code ("Runs shell commands (2 places)"), plus maintenance facts (last release, archived, security policy).
- **Author explanations:** an author can attach a short explanation to a flag ("pyscript runs your scripts, that's its purpose"). It is shown beside the flag but never lowers the level.
- **Gate:** "Needs review" blocks default-list inclusion and release updates until a HACS reviewer clears it.
- **Footer, always shown:** "Automated check of this release. Not a security review by the Open Home Foundation."

Applied to the prototype sample (section 7):

| Level | Integrations |
|---|---|
| Standard | ha-solarman, smartthinq-sensors, Xiaomi Cloud Map Extractor |
| Extended | alarmo (authenticated views, `.storage`), midea_ac_lan (`.storage`) |
| High access | hass-oidc-auth (unauthenticated login pages, replaces HA's auth providers), spook (services that enable/disable users), thewatchman (reads `core.config_entries`), all by design |
| Needs review | dreame-vacuum (obfuscation, remote payload, dashboard JavaScript), pyscript (installs packages at runtime through HA's installer, by design) |

Hard-coded hosts never set the level (decided 2026-11-19). They are listed under "Contacts" on each card. Extended uses blue rather than yellow so it can't be confused with High access (orange).

### Model A: capability flags, no grade

Show these per release in HACS and the Marketplace:

- **Behaviour flags**, each with file:line links: runs shell/subprocess · executes dynamic code · unsafe deserialisation · disables TLS verification · unauthenticated web endpoint · registers webhooks · injects dashboard JavaScript · contacts these hosts: … · bundled binaries
- **Review triggers** (red, and they block default-list inclusion or a release update until a HACS reviewer clears them): obfuscated code · runtime code or package download · release asset differs from tagged source
- **Hygiene facts:** last release date, archived, Scorecard checks (Maintained, Token-Permissions, Dangerous-Workflow), known-vulnerable resolved deps
- Fixed caption: "Automated checks of this release. Not a security review or endorsement by the Open Home Foundation."

Trade-offs: most honest, hardest to game into a false "8/8", easy to explain in a closure ("the panel says it runs shell commands"). Users get no single number to compare.

### Model B: a points score like the app rating

Start at 5 and clamp to 1–8, mirroring the app rating.

| Input | Δ |
|---|---|
| Obfuscation or runtime code download | forced to 1 (like `full_access`) |
| Unauth view serving non-static data, or `shell=True` | −2 |
| Dashboard JS injection, `exec`/`eval`, unsafe deserialisation, TLS off | −1 each, max −3 |
| Bundled binary | −2 |
| Known-vulnerable resolved dependency | −1 |
| Scorecard Token-Permissions and Dangerous-Workflow pass | +1 |
| Release in last 12 months, not archived | +1 |
| Security policy (SECURITY.md or private reporting on) | +1 |

Trade-offs: familiar from apps. But a 7 reads as "safe", which is exactly the OHF endorsement risk. Authors will optimise for the number (moving code into a dependency hides it from the scan). And by-design integrations like pyscript are scored as "bad" forever.

### Cross-cutting risks

- **False positives:** in the tuned sample, about half the hits were by design (pyscript's interpreter, OIDC login views, alarmo's authenticated views). Each flag needs an author-supplied "why" that a reviewer can accept.
- **Gaming:** pattern checks only catch honest or lazy code. Moving logic into a PyPI dependency or a downloaded payload evades them. That's why obfuscation and code download are gates, not deductions, and why dependencies need at least a name and download-count sanity check.
- **Maintainer burden:** low for authors (zero config). The real cost is HACS reviewer time on the gate queue.
- **Endorsement:** both models put OHF's name near a third-party verdict. Model A's flags state facts; B's number implies a judgement.

## 6. Where it runs, who owns it

- **Runs in:** the HACS data pipeline (`hacs/integration` `.github/workflows/generate-hacs-data.yml`, cron every 2 h, `:27`). Scan only new `(repo, version)` pairs and cache results. Publish them as a field in `data-v2`.
- **Gate at inclusion:** add a job to `hacs/default` `checks.yml`.
- **Display:** HACS frontend (ludeeus) and core Marketplace (Frenck, `@home-assistant/core` codeowners). The Marketplace needs a schema and UI change to show the field.
- **Rules owner:** the Security group (what is flagged, what is a gate, the wording). Use the `critical` list as the response path for confirmed-bad repos.
- Nobody has been contacted.

## 7. Prototype results

`prototype/scan.py` (AST-only, reads files, never imports or runs them). Results are in `prototype/scan-results.json`. Repos were cloned at their latest release tag into `untrusted/repos/` (not run).

| Integration (downloads) | Py LOC | Flags after tuning | Verdict on hits |
|---|---|---|---|
| alarmo (85k) | 5.5k | 6 HTTP views (all auth) | info only |
| spook (70k) | 46.7k | 6 non-constant `import_module` | benign (own modules) |
| Xiaomi Cloud Map Extractor (65k) | 3.5k | none | — |
| ha-solarman (63k) | 6.0k | none | — |
| midea_ac_lan (57k) | 15.4k | none | — |
| thewatchman (51k) | 4.7k | none (an earlier false positive on a SafeLoader subclass was fixed) | — |
| **dreame-vacuum (50k)** | 47.0k | 2 unauth views, 2 JS injection, embedded V8 `eval`, obfuscation in 5 files | **real concern, see below** |
| smartthinq-sensors (49k) | 15.9k | none | — |
| pyscript (22k) | 10.6k | `exec`/`compile` plus 11 interpreter `eval`s, 2 webhooks | by design |
| hass-oidc-auth (22k) | 3.6k | 6 unauth views | by design (login flow); TLS verify is a user option, correctly not flagged |

**dreame-vacuum `v2.0.3` (`fec086ca`), `custom_components/dreame_vacuum/frontend.py`.** Read statically, not run:
- The code is deliberately obfuscated: 30 imports renamed to 1–2 letters (`base64 as b6`, `HomeAssistantView as Hv`), file names and storage keys hidden as `bytes.fromhex(b64decode(...))`, and keys built by XOR-ing byte strings.
- It hashes its own source files, then POSTs to `https://api.tasshack.com/get` (`:302-306`). The request carries the user's key, the device model in clear, and an encrypted token built from the device serial number and MAC. I haven't fully traced what goes into the token.
- The reply is AES-GCM encrypted and Ed25519-signed by the author. It is re-encrypted and served to the browser through an authenticated view (`:349-366`; how the browser uses it not confirmed).
- A 240 KB base64 JavaScript bundle (`const.py:81`) is served **unauthenticated** at `/dreame_vacuum/frontend.js` (`:83-92`). It is added automatically as a Lovelace resource on every dashboard, or through `add_extra_js_url` in YAML mode (`:373-420`).
- `dreame/map.py:14055` runs a further base64-embedded JS file in an embedded V8 (`mini-racer`).
- The README links a "get DVC" page, so this looks like a licensing scheme for a paid card. I didn't confirm what the downloaded payload is. This is exactly the pattern the gate is meant to catch, and today nothing flags it.

**Noise lessons:**
1. My first pass missed dreame's unauth view because `HomeAssistantView` was aliased. Checks must resolve aliases.
2. The short-alias heuristic first fired on spook's standard `er`/`dr`/`ir`. It needs an allowlist of HA naming conventions.
3. YAML `BaseLoader` and `SafeLoader` subclasses were flagged until I fixed it. Checks need light cross-file resolution.
4. A method named `eval` gives 11 hits in pyscript.

After those fixes there were 0 false positives on unremarkable integrations, and all remaining hits were explainable in a minute each. Dependency and Scorecard checks added little on this sample.

### Random 100 (noise test)

100 integrations drawn at random from the catalog (seed 20261119). Every High access and Needs review hit was checked by hand. Details are in `prototype/run100/results.md`.

| Rules | Standard | Extended | High access | Needs review | Wrong levels (by hand) |
|---|---|---|---|---|---|
| v1 (as first written) | 70 | 4 | 23 | 3 | 6 of 26 High/Review, including all 3 Needs review |
| v2 (tuned) | 73 | 18 | 9 | 0 | 1 of 9 High access |

- **v1 noise came from routine patterns:** 13 integrations load their own bundled dashboard card. Others are inline SVG images and generated protobuf code read as obfuscation, `.bin` data files counted as binaries, TLS settings that are off only in shipped test files, a pinned CA, and views that check the login in their own code.
- **v2 changes:**
  - a local bundled card, a fixed program like ffmpeg, and a view that checks the login itself are now **Extended**;
  - tests are skipped;
  - the long-line rule is gone, and image base64 and `.bin` data are ignored;
  - the original 10 keep their levels.
- **Real findings in the 100:** one weakness (TLS verification off to a fixed internet API) and three LAN devices with TLS off. Nothing like dreame-vacuum.
- **Caveat:** v2 was tuned on this same sample. The honest noise test is a fresh random 100.

### Fresh 100 (holdout, v2 rules unchanged)

A second random 100 with no overlap (seed 20261120). Details are in `prototype/run100b/results.md`.

- **Levels:** 80 Standard, 11 Extended, 6 High access, 3 Needs review.
- **Wrong by hand check:** 5 of the 9 High/Review levels:
  - all 3 Needs review were false positives: committed `.pyc` caches twice, and a published crypto constant in hex;
  - one High access was static frontend files;
  - one integration was **under-rated**: AlexxIT WebRTC downloads the go2rtc binary from the author's GitHub at runtime, marks it executable and runs it with no hash check. That should be Needs review.
- **Takeaways:**
  - High access is mostly right (5 of 6).
  - Needs review is not yet trustworthy; it has been 0 of 6 on random samples.
  - The download-and-run pattern needs its own check.
  - Four v3 fixes are listed in the results file, but they need another fresh sample to measure.

### Second fresh 100 (holdout for v3)

**v3 changes:**
- only `.pyc` files Python runs without its source count as binaries;
- hex constants are not treated as base64;
- a new Needs review check for download-and-run: a file made executable in code that also downloads;
- unauthenticated GET-only views that return files become Extended.

The first 10 are unchanged, and WebRTC is now Needs review. A third random 100 (seed 20261121) was then checked with v3 unchanged. Details are in `prototype/run100c/results.md`.

- **Levels:** 79 Standard, 12 Extended, 9 High access, 0 Needs review.
- **Wrong by hand check:** 2 of 9. Both are unauthenticated views serving allowlisted or generated static content. No misses were found in the Standard repos.
- **Real weaknesses found:**
  - recalbox: `ping` runs through a shell with the configured host, and an unauthenticated POST endpoint updates entity state;
  - mcp-assist: certificate checks are always off while it sends a bearer token.
  - The other five were accurate low-concern or by-design.
- **Noise trend on fresh data:** v2 got 5 of 9 wrong; v3 got 2 of 9.
- **Still untested:** Needs review hasn't fired on a clean sample yet. Its only true positives (dreame-vacuum, WebRTC) came from samples that shaped the rules.

### Comparison with Marshal, and v4 checks

At Josh's request I ran Marshal v0.2.3 (commit `7ee612d5`) on the same 210 integrations (popular 10, run100b, run100c). It ran in a locked-down container: unprivileged, read-only, with only its two dependencies. Details are in `marshal-test.md`.

- **Its grades:** 190 A, 8 B, 5 C, 5 D, 2 F.
- **It misses our two strongest cases:**
  - dreame-vacuum gets C 77 (no flag for the obfuscation, the remote payload or the dashboard JavaScript);
  - WebRTC gets C 77 (no flag for download-and-run).
- **It catches things we missed:**
  - pinned packages with known CVEs;
  - pyscript's runtime installs through `async_process_requirements`;
  - access to HA auth, every config entry and `.storage`.
- **Where its grade misleads:** Spook gets an F and Alarmo and OIDC get Ds for by-design auth/config access, while recalbox (shell command, open endpoint) gets a B. Folding performance and upkeep into one grade with security blurs what the number means.

**v4 adds those checks** (`scan.py`, `deps.py`, `levels.py`; v3 kept as `scan_v3.py`):
- runtime install through HA's installer → Needs review;
- reading users, every config entry or `.storage` → Extended;
- changing users or logins, or naming secret files → High access;
- exact pins with OSV advisories, merged by alias → High access if any are high or critical, otherwise Extended.

**v4 levels:**

| Sample | Standard | Extended | High access | Needs review |
|---|---|---|---|---|
| Popular 10 | 3 | 2 | 3 | 2 |
| run100 | 70 | 21 | 9 | 0 |
| run100b | 77 | 17 | 5 | 1 |
| run100c | 74 | 15 | 11 | 0 |

**Effect of the new checks:**
- **High access:** they moved Spook and thewatchman up (both accurate and by design), plus sberdevices (`Authlib==1.2.1`, 9 high/critical advisories), DTE Rates (`pypdf==5.4.0`) and PREdistribuce (`lxml==5.3.0`).
- **Needs review:** pyscript moved up (runtime installs, by design).
- **Extended:** most other changes are Standard → Extended for `.storage` use or reading users. They're accurate, but `.storage` use is common and low-signal. Consider showing it as a note rather than letting it set the level.
- **Not hand-checked yet:** v4 hasn't been tested on a fresh sample.

## Open questions for Josh

1. Access profile (four levels, recommended), Model A (flags only) or Model B (1–8 number)? And is "Access profile" the right name?
2. Should obfuscation or runtime code download block default-list inclusion and updates, or only be shown?
3. Should a scan also gate *updates* to already-listed integrations, which today install with no check?
4. Does the Security group own the rules while ludeeus owns the pipeline? Who reviews the gate queue?
5. Should the Marketplace display be part of this, which brings Frenck into scope now?
6. Raise the dreame-vacuum obfuscation/phone-home pattern with HACS now, separately from this proposal?
7. Raise the app-rating docs drift (scale "1 to 6" vs code 1–8, missing rules) as a docs fix?
8. Should `.storage` use and reading user accounts set the level (Extended), or only show as a note?
9. Should a pinned package with high/critical advisories make an integration High access, or should it be a separate "outdated dependency" note, since it's about patching rather than access?
10. Talk to Marshal's author about a shared catalog signal, or keep the two separate?
