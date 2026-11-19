// Access profile panel (mockup). Plain JS, no build step, no imports.
// Works as an ES module (panel_custom module_url) and as a classic <script> (preview.html).
// HA passes `hass`, `narrow`, `panel`; data comes from hass.callApi("GET", "access_profile/profiles").
(() => {
  "use strict";
  if (customElements.get("access-profile-panel")) return;

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  const STYLE = `
    :host { display: block; min-height: 100%; background: var(--primary-background-color, #fafafa);
      color: var(--primary-text-color, #212121); font-family: var(--ha-font-family-body, Roboto, sans-serif); }
    .toolbar { display: flex; align-items: center; gap: 12px; height: var(--header-height, 56px); padding: 0 16px;
      background: var(--app-header-background-color, var(--primary-color, #03a9f4));
      color: var(--app-header-text-color, var(--text-primary-color, #fff)); font-size: 20px; font-weight: 400;
      border-bottom: var(--app-header-border-bottom, none); box-sizing: border-box; }
    .toolbar button { background: none; border: 0; color: inherit; font-size: 22px; cursor: pointer; padding: 8px; }
    .toolbar .tag { font-size: 12px; padding: 2px 8px; border-radius: 10px; border: 1px solid currentColor; opacity: .8; }
    .content { max-width: 1040px; margin: 0 auto; padding: 16px; box-sizing: border-box; }
    h2 { font-size: 16px; font-weight: 500; margin: 24px 4px 8px; color: var(--secondary-text-color, #727272);
      text-transform: none; }
    .card { background: var(--ha-card-background, var(--card-background-color, #fff));
      border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, none);
      border: 1px solid var(--ha-card-border-color, var(--divider-color, #e0e0e0)); overflow: hidden; }
    .card-content { padding: 16px; }
    .card-actions { border-top: 1px solid var(--divider-color, #e0e0e0); padding: 8px; display: flex;
      justify-content: flex-end; gap: 8px; }
    .muted { color: var(--secondary-text-color, #727272); }
    .small { font-size: 12px; }
    p { margin: 0 0 8px; line-height: 1.5; }
    a { color: var(--primary-color, #03a9f4); }

    /* Chip styled like the app "Rating" ha-assist-chip (filled, white label, badge colours). */
    .chip { display: inline-flex; align-items: center; gap: 6px; height: 32px; padding: 0 14px 0 8px;
      border: 0; border-radius: var(--ha-assist-chip-container-shape, 16px); cursor: pointer;
      font: 500 14px/20px var(--ha-font-family-body, Roboto, sans-serif); letter-spacing: .1px;
      color: var(--text-primary-color, #fff); background: var(--primary-color, #03a9f4); white-space: nowrap; }
    .chip:focus-visible { outline: 2px solid var(--primary-text-color, #000); outline-offset: 2px; }
    .chip .ico { font-size: 14px; line-height: 1; }
    .chip.green { background: var(--label-badge-green, #0da035); }
    .chip.blue { background: var(--label-badge-blue, #039be5); }
    .chip.orange { background: var(--orange-color, #ff9800); }
    .chip.red { background: var(--label-badge-red, #df4c1e); }
    .chip.plain { background: var(--secondary-background-color, #e5e5e5); color: var(--primary-text-color, #212121); cursor: default; }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; }

    .filters { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; margin: 24px 0 8px; }
    .filters input { font: inherit; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--divider-color, #ccc);
      background: var(--card-background-color, #fff); color: var(--primary-text-color); min-width: 200px; }
    .filter-chips .chip.dim { opacity: 0.55; }
    .legend { display: grid; grid-template-columns: max-content 1fr; gap: 8px 12px; align-items: center; margin-top: 12px; }

    /* Mock repository page header (HACS / Marketplace) */
    .mock-label { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; margin: 24px 4px 8px; }
    .mock-label h2 { margin: 0; }
    select { font: inherit; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--divider-color, #ccc);
      background: var(--card-background-color, #fff); color: var(--primary-text-color, #212121); }
    .repo-head { display: flex; gap: 16px; align-items: flex-start; }
    .logo { flex: none; width: 56px; height: 56px; border-radius: 12px; display: grid; place-items: center;
      font-size: 26px; font-weight: 500; background: var(--secondary-background-color, #e5e5e5); color: var(--secondary-text-color, #727272); }
    .repo-main { flex: 1; min-width: 0; }
    .repo-title { font-size: 22px; font-weight: 400; margin: 0 0 2px; }
    .repo-meta { font-size: 14px; margin-bottom: 12px; }
    .btn { font: 500 14px var(--ha-font-family-body, Roboto, sans-serif); border-radius: 18px; padding: 8px 18px;
      cursor: pointer; border: 1px solid var(--divider-color, #ccc); background: transparent; color: var(--primary-color, #03a9f4); }
    .btn.primary { background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); border-color: transparent; }
    .repo-actions { display: flex; gap: 8px; flex: none; }
    .why { margin-top: 12px; font-size: 14px; }
    .annot { margin-top: 12px; font-size: 12px; padding: 6px 10px; border-left: 3px solid var(--primary-color, #03a9f4);
      background: var(--secondary-background-color, #f2f2f2); border-radius: 4px; }
    @media (max-width: 600px) { .repo-head { flex-wrap: wrap; } .repo-actions { width: 100%; } }

    /* Integration cards */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
    .grid .card { display: flex; flex-direction: column; }
    .grid .card-content { flex: 1; }
    .name { font-size: 18px; margin: 0; }
    .sub { font-size: 13px; margin: 2px 0 12px; }
    ul.reasons { margin: 12px 0 0; padding-left: 18px; font-size: 14px; }
    ul.reasons li { margin-bottom: 4px; }
    .note { margin-top: 12px; padding: 8px 10px; border-radius: 8px; font-size: 14px;
      background: var(--secondary-background-color, #f2f2f2); }
    .note b { display: block; font-size: 12px; font-weight: 500; margin-bottom: 2px; }
    .note .sample { display: block; margin-top: 4px; font-size: 11px; font-style: italic; color: var(--secondary-text-color, #727272); }
    .hosts { margin-top: 12px; font-size: 13px; overflow-wrap: anywhere; }
    .footer { font-size: 12px; color: var(--secondary-text-color, #727272); margin-top: 12px; }

    /* Dialog, mirroring the app info "more info" alert dialog */
    dialog { border: 0; padding: 0; border-radius: var(--ha-dialog-border-radius, 24px); width: min(560px, calc(100vw - 32px));
      max-height: calc(100vh - 64px); background: var(--ha-dialog-surface-background, var(--card-background-color, #fff));
      color: var(--primary-text-color, #212121); box-shadow: 0 8px 32px rgba(0,0,0,.3); }
    dialog::backdrop { background: rgba(0,0,0,.45); }
    .dlg-head { padding: 24px 24px 8px; }
    .dlg-head h3 { margin: 8px 0 0; font-size: 22px; font-weight: 400; }
    .dlg-body { padding: 0 24px 8px; overflow: auto; max-height: calc(100vh - 240px); font-size: 14px; }
    .dlg-body h4 { margin: 16px 0 6px; font-size: 14px; font-weight: 500; }
    .reason { margin-bottom: 12px; }
    .reason .lvl { font-size: 12px; }
    .reason ul { margin: 4px 0 0; padding-left: 18px; }
    .reason code { font-size: 12px; }
    .dlg-actions { display: flex; justify-content: flex-end; padding: 8px 16px 16px; }
  `;

  class AccessProfilePanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._data = null;
      this._error = null;
      this._mock = null; // repo shown in the page-header mock
      this._narrow = false;
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      if (first) this._load();
    }
    get hass() { return this._hass; }
    set narrow(v) { this._narrow = !!v; if (this._data || this._error) this._render(); }
    set panel(v) { this._panel = v; }

    async _load() {
      this._render();
      try {
        this._data = await this._hass.callApi("GET", "access_profile/profiles");
        const list = this._data.integrations || [];
        this._mock = (list.find((i) => i.level === "review") || list[0] || {}).repo;
      } catch (err) {
        this._error = (err && (err.body?.message || err.message)) || String(err);
      }
      this._render();
    }

    _level(id) { return (this._data.levels || []).find((l) => l.id === id) || { label: id, emoji: "", color: "" }; }
    _byRepo(repo) { return this._data.integrations.find((i) => i.repo === repo); }

    _chip(i) {
      const l = this._level(i.level);
      return `<button class="chip ${esc(l.color)}" data-repo="${esc(i.repo)}" title="Access profile: ${esc(l.label)}. Click for details."
        aria-haspopup="dialog"><span class="ico" aria-hidden="true">${esc(l.emoji)}</span>${esc(l.label)}</button>`;
    }

    _version(i) {
      const v = i.version || "?";
      const tag = i.tag && i.tag.replace(/^v/, "") !== v.replace(/^v/, "") ? ` (release ${esc(i.tag)})` : "";
      return `${esc(v)}${tag}`;
    }

    _note(i, withSample) {
      if (!i.author_note) return "";
      return `<div class="note"><b>Author's explanation</b>${esc(i.author_note.text)}
        ${withSample && i.author_note.sample ? `<span class="sample">${esc(i.author_note.source)}</span>` : ""}</div>`;
    }

    _render() {
      const menu = this._narrow
        ? `<button id="menu" aria-label="Open sidebar" title="Open sidebar">&#9776;</button>` : "";
      let body;
      if (this._error) {
        body = `<div class="card"><div class="card-content">Could not load profiles: ${esc(this._error)}</div></div>`;
      } else if (!this._data) {
        body = `<p class="muted">Loading...</p>`;
      } else {
        body = this._intro() + this._mockHeader() + this._cards();
      }
      this.shadowRoot.innerHTML = `<style>${STYLE}</style>
        <div class="toolbar">${menu}<span>Access profile</span><span class="tag">Mockup</span></div>
        <div class="content">${body}</div>
        <dialog id="dlg" aria-labelledby="dlg-title"></dialog>`;
      this._wire();
    }

    _intro() {
      const legend = this._data.levels
        .map((l) => `<span><span class="chip ${esc(l.color)}" style="cursor:default"><span class="ico">${esc(l.emoji)}</span>${esc(l.label)}</span></span>
          <span>${esc(l.meaning)}</span>`).join("");
      return `<div class="card"><div class="card-content">
        <p>Each release of a custom integration gets one <b>Access profile</b> level, set by the most serious thing an automated
        scan finds. Levels are not added up, and an author's explanation never lowers the level. Click a chip for the reasons and code links.</p>
        <div class="legend">${legend}</div>
        <p class="footer">${esc(this._data.footer)} Data: prototype scan of ${this._data.integrations.length} HACS integrations
        (${(this._data.samples || []).map((s) => `${esc(s.label)}: ${s.count}`).join("; ")}).
        Author explanations shown here are sample text written by us, not by the authors.</p>
      </div></div>`;
    }

    _mockHeader() {
      const list = this._data.integrations;
      const i = this._byRepo(this._mock) || list[0];
      const options = list.map((x) => `<option value="${esc(x.repo)}" ${x.repo === i.repo ? "selected" : ""}>${esc(x.name)}</option>`).join("");
      const top = i.reasons[0];
      const [owner] = i.repo.split("/");
      return `<div class="mock-label"><h2>In context: HACS / Marketplace repository page (mock)</h2>
          <label class="small muted">Show <select id="mock-pick" aria-label="Integration shown in the mock">${options}</select></label></div>
        <div class="card"><div class="card-content">
          <div class="repo-head">
            <div class="logo" aria-hidden="true">${esc(i.name.charAt(0))}</div>
            <div class="repo-main">
              <p class="repo-title">${esc(i.name)}</p>
              <div class="repo-meta muted">by ${esc(owner)} &middot; ${esc(i.downloads || "")} downloads &middot; ${this._version(i)}</div>
              <div class="chips">
                <span class="chip plain">Integration</span>
                ${this._chip(i)}
              </div>
              <div class="why">${top ? `${esc(top.text)}${top.count_text ? ` (${esc(top.count_text)})` : ""}${i.reasons.length > 1 ? ` and ${i.reasons.length - 1} more` : ""}.`
                : "No flags found in this release."}</div>
              <div class="footer">${esc(this._data.footer)}</div>
            </div>
            <div class="repo-actions"><button class="btn" tabindex="-1">Repository</button><button class="btn primary" tabindex="-1">Download</button></div>
          </div>
          <div class="annot">Mock only: the chip sits beside the type tag, above the fold and next to the Download button, so it is seen before installing.
          ${i.level === "review" ? " Under the proposal, “Needs review” would block inclusion and updates until a HACS reviewer clears it." : ""}</div>
        </div></div>`;
    }

    _filtered() {
      const q = (this._q || "").toLowerCase();
      return this._data.integrations.filter((i) =>
        (!this._fLevel || this._fLevel === "all" || i.level === this._fLevel)
        && (!this._fSample || this._fSample === "all" || i.sample === this._fSample)
        && (!q || i.name.toLowerCase().includes(q) || i.repo.toLowerCase().includes(q)));
    }

    _filters() {
      const inSample = this._data.integrations.filter((i) =>
        !this._fSample || this._fSample === "all" || i.sample === this._fSample);
      const counts = this._data.levels.map((l) => {
        const n = inSample.filter((i) => i.level === l.id).length;
        const pct = inSample.length ? Math.round((100 * n) / inSample.length) : 0;
        const on = this._fLevel === l.id;
        const dim = this._fLevel && this._fLevel !== "all" && !on;
        return `<button class="chip ${esc(l.color)} ${dim ? "dim" : ""}" data-flevel="${esc(l.id)}" aria-pressed="${on}"
          title="Show only ${esc(l.label)}"><span class="ico">${esc(l.emoji)}</span>${esc(l.label)} &middot; ${n} (${pct}%)</button>`;
      }).join("");
      const sopts = [`<option value="all">All samples (${this._data.integrations.length})</option>`]
        .concat((this._data.samples || []).map((s) =>
          `<option value="${esc(s.id)}" ${this._fSample === s.id ? "selected" : ""}>${esc(s.label)} (${s.count})</option>`)).join("");
      return `<div class="filters">
          <label class="small muted">Sample <select id="f-sample">${sopts}</select></label>
          <input id="f-q" type="search" placeholder="Search name or repo" value="${esc(this._q || "")}" aria-label="Search">
          <button class="btn" id="f-clear">Show all levels</button>
        </div><div class="chips filter-chips">${counts}</div>`;
    }

    _cards() {
      return `${this._filters()}<div id="cards">${this._cardGrid()}</div>`;
    }

    _cardGrid() {
      const list = this._filtered();
      const LIMIT = 300;  // keep the page responsive with the full catalog; filters narrow the list
      const cards = list.slice(0, LIMIT).map((i) => {
        const reasons = i.reasons.length
          ? `<ul class="reasons">${i.reasons.map((r) => `<li>${esc(r.text)}${r.count_text ? ` <span class="muted">(${esc(r.count_text)})</span>` : ""}</li>`).join("")}</ul>`
          : `<p class="muted" style="margin-top:12px">No flags found in this release.</p>`;
        const hosts = i.hosts.length
          ? `<div class="hosts"><span class="muted">Contacts:</span> ${i.hosts.map(esc).join(", ")}</div>`
          : `<div class="hosts muted">No hard-coded internet hosts found.</div>`;
        return `<div class="card"><div class="card-content">
            <p class="name">${esc(i.name)}</p>
            <div class="sub muted">${esc(i.repo)} &middot; ${this._version(i)}</div>
            ${this._chip(i)}
            ${reasons}${this._note(i, false)}${hosts}
            <div class="footer">${esc(this._data.footer)}</div>
          </div>
          <div class="card-actions"><button class="btn" data-repo="${esc(i.repo)}">Details</button></div></div>`;
      }).join("");
      const more = list.length > LIMIT ? ` &middot; first ${LIMIT} shown, use the level chips or search to narrow` : "";
      return `<h2>Integrations (${list.length} of ${this._data.integrations.length}${more})</h2><div class="grid">${cards}</div>`;
    }

    _openDialog(repo) {
      const i = this._byRepo(repo);
      if (!i) return;
      const l = this._level(i.level);
      const reasons = i.reasons.length
        ? i.reasons.map((r) => {
            const rl = this._level(r.level);
            const links = r.links.map((k) =>
              `<li><a href="${esc(k.url)}" target="_blank" rel="noopener noreferrer"><code>${esc(k.label)}</code></a>
               <span class="muted small">${esc(k.detail)}</span></li>`).join("");
            const hostItems = r.check === "hosts" ? i.hosts.map((h) => `<li>${esc(h)}</li>`).join("") : "";
            const more = !hostItems && r.count > r.links.length ? `<li class="muted small">and ${r.count - r.links.length} more</li>` : "";
            return `<div class="reason"><div>${esc(r.text)}${r.count_text ? ` <span class="muted">(${esc(r.count_text)})</span>` : ""}</div>
              <div class="lvl muted">${esc(rl.emoji)} ${esc(rl.label)}</div>
              ${links || more || hostItems ? `<ul>${links}${hostItems}${more}</ul>` : ""}</div>`;
          }).join("")
        : `<p>No flags found in this release.</p>`;
      const hosts = i.hosts.length ? i.hosts.map(esc).join(", ") : "None found.";
      const dlg = this.shadowRoot.getElementById("dlg");
      dlg.innerHTML = `
        <div class="dlg-head">${this._chip(i).replace("<button", '<button disabled style="cursor:default"')}
          <h3 id="dlg-title">Access profile: ${esc(l.label)}</h3>
          <div class="muted small">${esc(i.name)} ${this._version(i)} &middot; <a href="${esc(i.repo_url)}" target="_blank" rel="noopener noreferrer">${esc(i.repo)}</a></div></div>
        <div class="dlg-body">
          <p>${esc(l.meaning)} The level is set by the most serious finding below.</p>
          <h4>Reasons</h4>${reasons}
          ${this._note(i, true)}
          <h4>Internet hosts in the code</h4><p>${hosts}</p>
          <p class="footer">${esc(this._data.footer)}</p>
        </div>
        <div class="dlg-actions"><button class="btn" id="dlg-ok">OK</button></div>`;
      dlg.querySelector("#dlg-ok").addEventListener("click", () => dlg.close());
      dlg.showModal();
      dlg.querySelector("#dlg-ok").focus();
    }

    _wire() {
      const root = this.shadowRoot;
      root.getElementById("menu")?.addEventListener("click", () =>
        this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })));
      root.querySelectorAll("button[data-repo]").forEach((b) =>
        b.addEventListener("click", () => this._openDialog(b.dataset.repo)));
      root.getElementById("mock-pick")?.addEventListener("change", (ev) => {
        this._mock = ev.target.value;
        this._render();
      });
      root.getElementById("f-sample")?.addEventListener("change", (ev) => {
        this._fSample = ev.target.value;
        this._render();
      });
      root.querySelectorAll("button[data-flevel]").forEach((b) => b.addEventListener("click", () => {
        this._fLevel = this._fLevel === b.dataset.flevel ? "all" : b.dataset.flevel;
        this._render();
      }));
      root.getElementById("f-clear")?.addEventListener("click", () => { this._fLevel = "all"; this._render(); });
      root.getElementById("f-q")?.addEventListener("input", (ev) => {
        this._q = ev.target.value;  // update only the card grid so the search box keeps focus
        root.getElementById("cards").innerHTML = this._cardGrid();
        root.querySelectorAll("#cards button[data-repo]").forEach((b) =>
          b.addEventListener("click", () => this._openDialog(b.dataset.repo)));
      });
      const dlg = root.getElementById("dlg");
      dlg.addEventListener("click", (ev) => { if (ev.target === dlg) dlg.close(); });
    }
  }

  customElements.define("access-profile-panel", AccessProfilePanel);
})();
