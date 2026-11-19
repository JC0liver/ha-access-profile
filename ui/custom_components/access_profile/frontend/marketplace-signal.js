// Access profile mockup: adds an "Access profile" line to the core Marketplace repository page,
// directly under the open issues line in the details card. Clicking it expands the reasons in place.
// Mockup only: it patches the rendered page. A real build would add this as one more entry in
// _signals() of ha-marketplace-repository-dashboard.ts, fed by a field in the catalog data.
(() => {
  if (window.__accessProfileSignal) return;
  window.__accessProfileSignal = true;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // mdi:shield-search
  const ICON = "M15.5,12C18,12 20,14 20,16.5C20,17.38 19.75,18.21 19.31,18.9L22.39,22L21,23.39L17.88,20.32C17.19,20.75 16.37,21 15.5,21C13,21 11,19 11,16.5C11,14 13,12 15.5,12M15.5,14A2.5,2.5 0 0,0 13,16.5A2.5,2.5 0 0,0 15.5,19A2.5,2.5 0 0,0 18,16.5A2.5,2.5 0 0,0 15.5,14M12,1L21,5V11C21,11.9 20.9,12.78 20.71,13.65C19.6,11.5 17.72,10 15.5,10A5.5,5.5 0 0,0 10,15.5C10,17.54 11.07,19.36 12.71,20.36C12.47,20.45 12.24,20.53 12,20.59C6.84,19.33 3,14.17 3,11V5L12,1Z";
  const STYLE = `
    li.ap-signal { cursor: pointer; flex-wrap: wrap; }
    li.ap-signal:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; border-radius: 4px; }
    .ap-chip { display: inline-flex; align-items: center; gap: 4px; padding: 1px 10px; border-radius: 12px;
      color: #fff; font-weight: 500; font-size: 0.9em; margin-left: 4px; }
    .ap-chip.green { background: var(--label-badge-green, #0da035); }
    .ap-chip.blue { background: var(--label-badge-blue, #039be5); }
    .ap-chip.orange { background: var(--orange-color, #ff9800); }
    .ap-chip.red { background: var(--label-badge-red, #df4c1e); }
    .ap-chip.grey { background: var(--disabled-text-color, #9e9e9e); }
    .ap-caret { margin-left: auto; color: var(--secondary-text-color); transition: transform .15s; }
    li.ap-signal[aria-expanded="true"] .ap-caret { transform: rotate(180deg); }
    li.ap-details { display: block !important; padding: 4px 0 4px 40px; color: var(--primary-text-color); }
    li.ap-details[hidden] { display: none !important; }
    .ap-details p { margin: 4px 0 8px; color: var(--secondary-text-color); }
    .ap-reason { margin: 8px 0; }
    .ap-reason .lvl { font-size: 0.85em; color: var(--secondary-text-color); }
    .ap-reason ul { margin: 2px 0 0; padding-left: 18px; }
    .ap-reason a { color: var(--primary-color); }
    .ap-reason code { font-size: 0.85em; }
    .ap-note { background: var(--secondary-background-color, #f2f2f2); border-radius: 8px; padding: 8px 10px; margin: 8px 0; }
    .ap-note b { display: block; font-size: 0.85em; }
    .ap-note small { display: block; color: var(--secondary-text-color); margin-top: 2px; }
    .ap-footer { font-size: 0.8em; color: var(--secondary-text-color); margin-top: 8px; }
  `;

  let data = null;
  let loading = false;
  const expanded = new Set();

  const hass = () => document.querySelector("home-assistant")?.hass;

  async function load() {
    if (data || loading || !hass()) return;
    loading = true;
    try { data = await hass().callApi("GET", "access_profile/profiles"); }
    catch (e) { console.warn("Access profile: no data", e); }
    loading = false;
  }

  // Walk open shadow roots to find the Marketplace repository page.
  function findDashboard(root, depth = 0) {
    if (!root || depth > 25) return null;
    const hit = root.querySelector?.("ha-marketplace-repository-dashboard");
    if (hit) return hit;
    for (const el of root.querySelectorAll?.("*") || []) {
      if (el.shadowRoot) {
        const found = findDashboard(el.shadowRoot, depth + 1);
        if (found) return found;
      }
    }
    return null;
  }

  const level = (id) => (data?.levels || []).find((l) => l.id === id) || { label: "Not checked", color: "grey", meaning: "" };

  function detailsHtml(p) {
    const l = level(p.level);
    const reasons = p.reasons.length
      ? p.reasons.map((r) => {
          const rl = level(r.level);
          const links = r.links.map((k) => `<li><a href="${esc(k.url)}" target="_blank" rel="noreferrer"><code>${esc(k.label)}</code></a></li>`).join("");
          const more = r.count > r.links.length ? `<li>and ${r.count - r.links.length} more</li>` : "";
          return `<div class="ap-reason"><div>${esc(r.text)}${r.count_text ? ` (${esc(r.count_text)})` : ""}</div>
            <div class="lvl">${esc(rl.emoji)} ${esc(rl.label)}</div>${links || more ? `<ul>${links}${more}</ul>` : ""}</div>`;
        }).join("")
      : `<p>No flags found in this release.</p>`;
    const note = p.author_note ? `<div class="ap-note"><b>Author's explanation</b>${esc(p.author_note.text)}
      ${p.author_note.sample ? `<small>${esc(p.author_note.source)}</small>` : ""}</div>` : "";
    const hosts = p.hosts.length ? `<p>Contacts: ${p.hosts.map(esc).join(", ")}</p>` : "";
    return `<p>${esc(l.meaning)} The level is set by the most serious finding.</p>${reasons}${note}${hosts}
      <div class="ap-footer">${esc(data.footer)} Checked release ${esc(p.tag)}.</div>`;
  }

  function patch() {
    const dash = findDashboard(document);
    const repo = dash?._repository;
    const ul = dash?.shadowRoot?.querySelector("ha-card.details ul.signals");
    if (!dash || !repo || !ul) return;
    if (!dash.shadowRoot.querySelector("style.ap-style")) {
      const st = document.createElement("style");
      st.className = "ap-style";
      st.textContent = STYLE;
      dash.shadowRoot.appendChild(st);
    }
    const key = (repo.full_name || "").toLowerCase();
    const existing = ul.querySelector("li.ap-signal");
    if (existing && existing.dataset.repo === key) return;  // already in place for this repository
    ul.querySelectorAll("li.ap-signal, li.ap-details").forEach((n) => n.remove());

    const p = (data?.integrations || []).find((i) => i.repo.toLowerCase() === key);
    const l = p ? level(p.level) : level(null);
    const li = document.createElement("li");
    li.className = "ap-signal";
    li.dataset.repo = key;
    li.tabIndex = 0;
    li.setAttribute("role", "button");
    const open = !!p && expanded.has(key);
    li.setAttribute("aria-expanded", String(open));
    li.innerHTML = `<ha-svg-icon></ha-svg-icon><span>Access profile:<span class="ap-chip ${esc(l.color)}">${esc(l.emoji || "")} ${esc(l.label)}</span></span>
      ${p ? `<span class="ap-caret">&#9662;</span>` : ""}`;
    li.querySelector("ha-svg-icon").path = ICON;
    ul.appendChild(li);
    if (!p) { li.title = "This release was not part of the prototype scan."; return; }

    const details = document.createElement("li");
    details.className = "ap-details";
    details.hidden = !open;
    details.innerHTML = detailsHtml(p);
    ul.appendChild(details);
    const toggle = () => {
      const now = details.hidden;
      details.hidden = !now;
      li.setAttribute("aria-expanded", String(now));
      if (now) expanded.add(key); else expanded.delete(key);
    };
    li.addEventListener("click", toggle);
    li.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); toggle(); } });
  }

  setInterval(async () => {
    if (!location.pathname.startsWith("/marketplace/repository/")) return;
    await load();
    if (data) patch();
  }, 500);
})();
