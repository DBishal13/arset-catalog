(() => {
  "use strict";

  const app = document.getElementById("app");
  const C = window.CATALOG;
  if (!C) {
    app.innerHTML = '<div class="empty">No catalog data found. Run <code>python -m arset build</code>.</div>';
    return;
  }

  // ---------- data ----------
  const KINDS = {
    training: "trainings", instructor: "instructors", satellite: "satellites",
    dataset: "datasets", tool: "tools", application: "applications",
  };
  const idx = {};
  for (const folder of Object.values(KINDS)) idx[folder] = new Map((C[folder] || []).map((r) => [r.id, r]));

  const LANG = { en: "English", es: "Spanish", fr: "French", pt: "Portuguese", ar: "Arabic" };
  const LEVELS = ["fundamentals", "introductory", "intermediate", "advanced"];
  const STATE_LABEL = {
    "in-progress": "In progress", upcoming: "Upcoming", "self-paced": "Self-paced",
    past: "Past", unscheduled: "Unscheduled",
  };
  const FORMAT_LABEL = {
    "online-instructor-led": "Online, instructor-led", "online-self-paced": "Online, self-paced",
    "in-person": "In person", other: "Other",
  };
  const TYPE_LABEL = {
    slides: "Slides", homework: "Homework", exercise: "Exercise", notebook: "Notebook",
    transcript: "Transcript", qa: "Q&A", data: "Data", other: "Link",
  };

  // ---------- helpers ----------
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : "");
  const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
  const nameOf = (folder, id) => {
    const r = idx[folder].get(id);
    return r ? r.name || r.title : id;
  };
  const href = (kind, id) => `#/${kind}/${encodeURIComponent(id)}`;

  function fmtDate(iso, withYear = true) {
    if (!iso) return "";
    const d = new Date(`${iso}T00:00:00Z`);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: withYear ? "numeric" : undefined, timeZone: "UTC",
    });
  }
  function dateRange(t) {
    if (!t.start_date) return "";
    if (!t.end_date || t.end_date === t.start_date) return fmtDate(t.start_date);
    const sameYear = t.start_date.slice(0, 4) === t.end_date.slice(0, 4);
    return `${fmtDate(t.start_date, !sameYear)} – ${fmtDate(t.end_date)}`;
  }

  function chipLinks(kind, ids) {
    if (!ids || !ids.length) return "";
    return `<div class="chips">${ids.map((id) =>
      `<a class="chip" href="${href(kind, id)}">${esc(nameOf(KINDS[kind], id))}</a>`).join("")}</div>`;
  }

  function badges(t) {
    const b = [];
    if (t.state) b.push(`<span class="badge ${esc(t.state)}">${esc(STATE_LABEL[t.state] || t.state)}</span>`);
    if (t.level) b.push(`<span class="badge">${esc(cap(t.level))}</span>`);
    if (t.format) b.push(`<span class="badge">${esc(FORMAT_LABEL[t.format] || t.format)}</span>`);
    for (const l of t.languages || []) b.push(`<span class="badge">${esc(LANG[l] || l)}</span>`);
    if (t.status === "draft") b.push('<span class="badge draft" title="Machine-generated, not reviewed yet">Draft</span>');
    return `<div class="badges">${b.join("")}</div>`;
  }

  function trainingCard(t) {
    const apps = (t.applications || []).slice(0, 4)
      .map((id) => `<span class="chip">${esc(nameOf("applications", id))}</span>`).join("");
    const people = (t.instructors || []).map((id) => nameOf("instructors", id));
    return `<a class="card" href="${href("training", t.id)}">
      ${badges(t)}
      <h3>${esc(t.title)}</h3>
      ${t.start_date ? `<div class="meta">${esc(dateRange(t))}</div>` : ""}
      ${t.summary ? `<div class="summary">${esc(t.summary)}</div>` : ""}
      ${apps ? `<div class="chips">${apps}</div>` : ""}
      <div class="foot"><span>${plural(t.video_count || 0, "video")}</span>
        <span>${esc(people.slice(0, 2).join(", "))}${people.length > 2 ? ` +${people.length - 2}` : ""}</span></div>
    </a>`;
  }

  function facts(rows) {
    const shown = rows.filter(([, v]) => v);
    if (!shown.length) return "";
    return `<dl class="facts">${shown.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl>`;
  }

  function setTitle(text) {
    document.title = text ? `${text} · ARSET Catalog` : "ARSET Catalog";
  }

  function notFound(what) {
    setTitle("Not found");
    app.innerHTML = `<div class="empty"><h1>Not found</h1><p>${esc(what || "That page")} isn't in the catalog.</p>
      <a href="#/">Back to trainings</a></div>`;
  }

  // ---------- trainings list ----------
  const GROUPS = [
    ["now", "Happening now & upcoming", (t) => t.state === "in-progress" || t.state === "upcoming"],
    ["self", "Self-paced, available any time", (t) => t.state === "self-paced"],
    ["past", "Past trainings", (t) => t.state === "past"],
    ["other", "Not scheduled", (t) => t.state === "unscheduled"],
  ];
  const haystack = new Map();
  for (const t of C.trainings) {
    const parts = [t.title, t.summary, t.description, t.level, ...(t.objectives || []), ...(t.tags || [])];
    for (const [field, folder] of [["instructors", "instructors"], ["satellites", "satellites"],
      ["datasets", "datasets"], ["tools", "tools"], ["applications", "applications"]]) {
      for (const id of t[field] || []) parts.push(nameOf(folder, id), id);
    }
    for (const s of t.sessions || []) parts.push(s.title, ...(s.agenda || []));
    haystack.set(t.id, parts.filter(Boolean).join(" \n ").toLowerCase());
  }

  function sortTrainings(list, group) {
    const by = (a, b) => (a || "").localeCompare(b || "");
    if (group === "now") return list.sort((a, b) => by(a.start_date, b.start_date));
    if (group === "past") return list.sort((a, b) => by(b.start_date, a.start_date));
    return list.sort((a, b) => by(b.published, a.published) || by(a.title, b.title));
  }

  function options(folder, field, selected) {
    const used = new Map();
    for (const t of C.trainings) for (const id of t[field] || []) used.set(id, (used.get(id) || 0) + 1);
    return [...used.keys()]
      .sort((a, b) => nameOf(folder, a).localeCompare(nameOf(folder, b)))
      .map((id) => `<option value="${esc(id)}"${id === selected ? " selected" : ""}>${esc(nameOf(folder, id))} (${used.get(id)})</option>`)
      .join("");
  }

  function renderTrainings(params) {
    setTitle("");
    const langs = [...new Set(C.trainings.flatMap((t) => t.languages || []))].sort();
    const levels = LEVELS.filter((l) => C.trainings.some((t) => t.level === l));
    const states = Object.keys(STATE_LABEL).filter((s) => C.trainings.some((t) => t.state === s));
    const opt = (value, label, sel) => `<option value="${esc(value)}"${value === sel ? " selected" : ""}>${esc(label)}</option>`;

    app.innerHTML = `
      <div class="page-head">
        <div><h1>Trainings</h1>
        <p class="muted" style="margin:0">${plural(C.trainings.length, "training")} ·
          ${plural(C.trainings.reduce((n, t) => n + (t.video_count || 0), 0), "recording")} ·
          ${plural(C.instructors.length, "instructor")}</p></div>
      </div>
      <div class="filters" role="search">
        <input class="search" type="search" id="f-q" aria-label="Search trainings"
          placeholder="Search titles, topics, instructors, satellites…" value="${esc(params.q || "")}">
        <select id="f-app" aria-label="Application"><option value="">All applications</option>${options("applications", "applications", params.app)}</select>
        <select id="f-sat" aria-label="Satellite"><option value="">All satellites</option>${options("satellites", "satellites", params.sat)}</select>
        <select id="f-level" aria-label="Level"><option value="">All levels</option>${levels.map((l) => opt(l, cap(l), params.level)).join("")}</select>
        <select id="f-lang" aria-label="Language"><option value="">All languages</option>${langs.map((l) => opt(l, LANG[l] || l, params.lang)).join("")}</select>
        <select id="f-state" aria-label="When"><option value="">Any time</option>${states.map((s) => opt(s, STATE_LABEL[s], params.state)).join("")}</select>
      </div>
      <div class="result-line"><span id="result-count" class="muted small" aria-live="polite"></span>
        <button type="button" class="linkish small" id="f-clear">Clear filters</button></div>
      <div id="results"></div>`;

    const fields = { q: "f-q", app: "f-app", sat: "f-sat", level: "f-level", lang: "f-lang", state: "f-state" };
    const read = () => Object.fromEntries(Object.entries(fields).map(([k, id]) => [k, document.getElementById(id).value.trim()]));

    function update() {
      const f = read();
      const terms = f.q.toLowerCase().split(/\s+/).filter(Boolean);
      const hits = C.trainings.filter((t) =>
        (!f.app || (t.applications || []).includes(f.app)) &&
        (!f.sat || (t.satellites || []).includes(f.sat)) &&
        (!f.level || t.level === f.level) &&
        (!f.lang || (t.languages || []).includes(f.lang)) &&
        (!f.state || t.state === f.state) &&
        terms.every((term) => haystack.get(t.id).includes(term)));

      const active = Object.values(f).some(Boolean);
      document.getElementById("f-clear").hidden = !active;
      document.getElementById("result-count").textContent =
        active ? `${plural(hits.length, "training")} match` : `Showing all ${plural(hits.length, "training")}`;

      const html = GROUPS.map(([key, label, test]) => {
        const list = sortTrainings(hits.filter(test), key);
        return list.length
          ? `<h2 class="section-title">${esc(label)} · ${list.length}</h2><div class="grid">${list.map(trainingCard).join("")}</div>`
          : "";
      }).join("");
      document.getElementById("results").innerHTML =
        html || '<div class="empty">No trainings match these filters.</div>';

      const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString();
      history.replaceState(null, "", qs ? `#/?${qs}` : "#/");
    }

    for (const id of Object.values(fields)) {
      document.getElementById(id).addEventListener(id === "f-q" ? "input" : "change", update);
    }
    document.getElementById("f-clear").addEventListener("click", () => {
      for (const id of Object.values(fields)) document.getElementById(id).value = "";
      update();
    });
    update();
  }

  // ---------- training detail ----------
  function videoHtml(v) {
    const id = esc(v.youtube);
    const title = esc(v.title || v.youtube);
    const lang = v.language && v.language !== "en" ? ` <span class="badge">${esc(LANG[v.language] || v.language)}</span>` : "";
    return `<figure class="video">
      <button type="button" data-yt="${id}" aria-label="Play ${title}"
        style="background-image:url('https://i.ytimg.com/vi/${id}/hqdefault.jpg')"></button>
      <figcaption>${title}${lang}
        · <a class="small" href="https://www.youtube.com/watch?v=${id}" target="_blank" rel="noopener">YouTube ↗</a></figcaption>
    </figure>`;
  }
  const videosHtml = (vs) => (vs && vs.length ? `<div class="videos">${vs.map(videoHtml).join("")}</div>` : "");
  const materialsHtml = (ms) => (ms && ms.length
    ? `<ul class="materials">${ms.map((m) => `<li><a href="${esc(safeUrl(m.url))}" target="_blank" rel="noopener">
        <span class="type">${esc(TYPE_LABEL[m.type] || m.type)}</span>${esc(m.title || m.url)}</a></li>`).join("")}</ul>`
    : "");

  function sidePanel(title, body) {
    return body ? `<div class="panel"><h3>${esc(title)}</h3>${body}</div>` : "";
  }

  function renderTraining(id) {
    const t = idx.trainings.get(id);
    if (!t) return notFound("That training");
    setTitle(t.title);

    const sessions = (t.sessions || []).map((s) => `
      <section class="panel session">
        <div class="session-head">
          <h3><span class="part">Part ${esc(s.part)}</span>${esc(s.title)}</h3>
          <span class="muted small">${esc(fmtDate(s.date))}</span>
        </div>
        ${videosHtml(s.videos)}
        ${materialsHtml(s.materials)}
        ${s.agenda && s.agenda.length ? `<details class="agenda"><summary>Agenda (${s.agenda.length})</summary>
          <ul>${s.agenda.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></details>` : ""}
        ${!(s.videos || []).length && !(s.materials || []).length
          ? '<p class="muted small" style="margin:10px 0 0">No recording or materials yet.</p>' : ""}
      </section>`).join("");
    const extra = (t.videos || []).length || (t.materials || []).length
      ? `<section class="panel session"><div class="session-head"><h3>Other resources</h3></div>
          ${videosHtml(t.videos)}${materialsHtml(t.materials)}</section>` : "";

    const people = (t.instructors || []).map((pid) => {
      const p = idx.instructors.get(pid) || { name: pid };
      return `<li><a href="${href("instructor", pid)}">${esc(p.name)}</a>
        <span class="muted">${esc([p.title, p.affiliation].filter(Boolean).join(" · "))}</span></li>`;
    }).join("");
    const prereqs = (t.prerequisites || []).map((pid) => idx.trainings.has(pid)
      ? `<li><a href="${href("training", pid)}">${esc(nameOf("trainings", pid))}</a></li>`
      : `<li><a href="https://www.earthdata.nasa.gov/learn/trainings/${encodeURIComponent(pid)}" target="_blank"
           rel="noopener">${esc(pid.replace(/-/g, " "))} ↗</a> <span class="muted small">(not in catalog)</span></li>`).join("");

    app.innerHTML = `
      <div class="crumbs"><a href="#/">Trainings</a></div>
      <div class="detail">
        <article>
          ${badges(t)}
          <h1>${esc(t.title)}</h1>
          ${t.summary ? `<p class="lead">${esc(t.summary)}</p>` : ""}
          ${sessions || extra ? `<h2>Sessions</h2>${sessions}${extra}` : ""}
          ${t.description ? `<h2>About this training</h2>${t.description.split(/\n\s*\n/).map((p) => `<p>${esc(p)}</p>`).join("")}` : ""}
          ${t.objectives && t.objectives.length ? `<h2>Objectives</h2><ul>${t.objectives.map((o) => `<li>${esc(o)}</li>`).join("")}</ul>` : ""}
          ${t.audience && t.audience.length ? `<h2>Who it's for</h2><ul>${t.audience.map((o) => `<li>${esc(o)}</li>`).join("")}</ul>` : ""}
          ${t.notes ? `<h2>Notes</h2><p>${esc(t.notes)}</p>` : ""}
        </article>
        <aside class="side">
          <div class="panel">
            <a class="button" style="display:block;margin-bottom:14px" href="${esc(safeUrl(t.source_url))}" target="_blank" rel="noopener">View on NASA Earthdata ↗</a>
            ${facts([
              ["Dates", esc(dateRange(t))],
              ["Level", esc(cap(t.level))],
              ["Format", esc(FORMAT_LABEL[t.format] || t.format || "")],
              ["Languages", esc((t.languages || []).map((l) => LANG[l] || l).join(", "))],
              ["Recordings", esc(String(t.video_count || 0))],
              ["Published", esc(fmtDate(t.published))],
              ["Updated", esc(fmtDate(t.last_updated))],
            ])}
          </div>
          ${sidePanel("Instructors", people && `<ul class="people">${people}</ul>`)}
          ${sidePanel("Satellites", chipLinks("satellite", t.satellites))}
          ${sidePanel("Datasets", chipLinks("dataset", t.datasets))}
          ${sidePanel("Tools", chipLinks("tool", t.tools))}
          ${sidePanel("Applications", chipLinks("application", t.applications))}
          ${sidePanel("Prerequisites", prereqs && `<ul style="margin:0;padding-left:1.1em">${prereqs}</ul>`)}
        </aside>
      </div>`;
  }

  // ---------- other record types ----------
  const list = (xs) => esc((xs || []).join(", "));
  const ENTITY = {
    instructor: {
      label: "Instructors",
      sub: (r) => [r.title, r.affiliation].filter(Boolean).join(" · "),
      facts: (r) => [["Role", esc(r.title)], ["Affiliation", esc(r.affiliation)], ["Expertise", list(r.expertise)]],
    },
    satellite: {
      label: "Satellites",
      sub: (r) => r.full_name || "",
      facts: (r) => [
        ["Full name", esc(r.full_name)], ["Agencies", list(r.agencies)],
        ["Launched", esc(fmtDate(r.launch_date))], ["Status", esc(cap(r.status))],
        ["Orbit", esc(cap((r.orbit || "").replace(/-/g, " ")))],
        ["Instruments", esc((r.instruments || []).map((i) => i.name).join(", "))],
      ],
    },
    dataset: {
      label: "Datasets",
      sub: (r) => [r.short_name, r.provider].filter(Boolean).join(" · "),
      facts: (r) => [
        ["Short name", esc(r.short_name)], ["Provider", esc(r.provider)],
        ["Satellites", (r.satellites || []).map((s) => `<a href="${href("satellite", s)}">${esc(nameOf("satellites", s))}</a>`).join(", ")],
        ["Variables", list(r.variables)], ["Resolution", esc(r.resolution)],
      ],
    },
    tool: {
      label: "Tools",
      sub: (r) => [cap((r.kind || "").replace(/-/g, " ")), r.open_source ? "open source" : ""].filter(Boolean).join(" · "),
      facts: (r) => [
        ["Kind", esc(cap((r.kind || "").replace(/-/g, " ")))],
        ["Open source", r.open_source === undefined ? "" : r.open_source ? "Yes" : "No"],
      ],
    },
    application: {
      label: "Applications",
      sub: (r) => r.description || "",
      facts: (r) => [["Part of", r.parent ? `<a href="${href("application", r.parent)}">${esc(nameOf("applications", r.parent))}</a>` : ""]],
    },
  };

  function renderEntityList(kind) {
    const cfg = ENTITY[kind];
    const rows = [...C[KINDS[kind]]].sort((a, b) =>
      (b.trainings || []).length - (a.trainings || []).length || (a.name || "").localeCompare(b.name || ""));
    setTitle(cfg.label);
    app.innerHTML = `
      <div class="page-head"><h1>${esc(cfg.label)}</h1><span class="muted">${rows.length} in the catalog</span></div>
      <div class="grid tight">${rows.map((r) => `
        <a class="card" href="${href(kind, r.id)}">
          ${r.status === "draft" ? '<div class="badges"><span class="badge draft">Draft</span></div>' : ""}
          <h3>${esc(r.name)}</h3>
          ${cfg.sub(r) ? `<div class="meta">${esc(cfg.sub(r))}</div>` : ""}
          <div class="foot"><span>${plural((r.trainings || []).length, "training")}</span></div>
        </a>`).join("")}</div>`;
  }

  function renderEntity(kind, id) {
    const cfg = ENTITY[kind];
    const r = idx[KINDS[kind]].get(id);
    if (!r) return notFound(`That ${kind}`);
    setTitle(r.name);
    const trainings = (r.trainings || []).map((tid) => idx.trainings.get(tid)).filter(Boolean);
    let related = "";
    if (kind === "satellite") {
      const ds = C.datasets.filter((d) => (d.satellites || []).includes(id)).map((d) => d.id);
      if (ds.length) related = `<h2>Datasets</h2>${chipLinks("dataset", ds)}`;
    }
    if (kind === "application") {
      const kids = C.applications.filter((a) => a.parent === id).map((a) => a.id);
      if (kids.length) related = `<h2>Narrower areas</h2>${chipLinks("application", kids)}`;
    }
    const factHtml = facts(cfg.facts(r));
    const links = [r.url, ...(r.links || [])].filter(Boolean);

    app.innerHTML = `
      <div class="crumbs"><a href="#/${KINDS[kind]}">${esc(cfg.label)}</a></div>
      ${r.status === "draft" ? '<div class="badges"><span class="badge draft">Draft</span></div>' : ""}
      <h1>${esc(r.name)}</h1>
      ${cfg.sub(r) ? `<p class="lead">${esc(cfg.sub(r))}</p>` : ""}
      ${factHtml || links.length || r.notes ? `<div class="panel" style="max-width:720px">
        ${factHtml}
        ${r.notes ? `<p class="small muted" style="margin:10px 0 0">${esc(r.notes)}</p>` : ""}
        ${links.map((u) => `<p class="small" style="margin:10px 0 0"><a href="${esc(safeUrl(u))}" target="_blank" rel="noopener">${esc(u)} ↗</a></p>`).join("")}
      </div>` : ""}
      ${related}
      <h2>Trainings (${trainings.length})</h2>
      ${trainings.length ? `<div class="grid">${trainings.map(trainingCard).join("")}</div>`
        : '<div class="empty">No trainings reference this yet.</div>'}`;
  }

  // ---------- review queue ----------
  const drafts = () => ({
    trainings: C.trainings.filter((t) => t.status === "draft"),
    instructors: C.instructors.filter((p) => p.status === "draft"),
    videos: C.inbox_videos || [],
  });

  function renderReview() {
    setTitle("Review");
    const d = drafts();
    const table = (head, rows) => rows.length
      ? `<div class="table-wrap"><table class="table"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>
         <tbody>${rows.join("")}</tbody></table></div>`
      : '<div class="empty">Nothing here.</div>';
    app.innerHTML = `
      <div class="page-head"><div><h1>Review queue</h1>
        <p class="muted" style="margin:0">Records the tracker created that nobody has checked yet.
        Edit the YAML in <code>data/</code> and set <code>status: reviewed</code>.</p></div></div>
      <h2>Draft trainings (${d.trainings.length})</h2>
      ${table(["Training", "Dates", "Tags to check", "File"], d.trainings.map((t) => `<tr>
        <td><a href="${href("training", t.id)}">${esc(t.title)}</a></td>
        <td class="small">${esc(dateRange(t) || STATE_LABEL[t.state] || "")}</td>
        <td class="small">${esc(["applications", "satellites", "datasets", "tools"].map((f) => `${(t[f] || []).length} ${f}`).join(", "))}</td>
        <td class="small muted"><code>data/trainings/${esc(t.id)}.yaml</code></td></tr>`))}
      <h2>Draft instructors (${d.instructors.length})</h2>
      ${table(["Name", "Role", "Affiliation"], d.instructors.map((p) => `<tr>
        <td><a href="${href("instructor", p.id)}">${esc(p.name)}</a></td>
        <td class="small">${esc(p.title)}</td><td class="small">${esc(p.affiliation)}</td></tr>`))}
      <h2>Unassigned videos (${d.videos.length})</h2>
      <p class="muted small">ARSET uploads that no training references. Move each into a training's session in
        <code>data/trainings/</code>, then delete it from <code>inbox/videos.yaml</code>.</p>
      ${table(["Published", "Title", "Channel"], d.videos.map((v) => `<tr>
        <td class="small">${esc(fmtDate(v.published))}</td>
        <td><a href="${esc(safeUrl(v.url))}" target="_blank" rel="noopener">${esc(v.title)} ↗</a>
          <div class="small muted"><code>${esc(v.youtube)}</code></div></td>
        <td class="small">${esc(v.channel)}</td></tr>`))}`;
  }

  // ---------- shell ----------
  const NAV = [
    ["trainings", "Trainings", "#/"], ["instructors", "Instructors"], ["satellites", "Satellites"],
    ["datasets", "Datasets"], ["tools", "Tools"], ["applications", "Applications"], ["review", "Review"],
  ];
  function renderNav(active) {
    const d = drafts();
    const pending = d.trainings.length + d.instructors.length + d.videos.length;
    document.getElementById("nav").innerHTML = NAV.map(([key, label, url]) =>
      `<a href="${url || `#/${key}`}"${key === active ? ' class="active" aria-current="page"' : ""}>${label}${
        key === "review" && pending ? `<span class="count">${pending}</span>` : ""}</a>`).join("");
  }

  document.getElementById("footer").innerHTML =
    `Catalog built ${esc(fmtDate(C.generated))} from NASA Earthdata training pages and YouTube.
     Independent project; not an official NASA site.`;

  function router() {
    const raw = location.hash.replace(/^#\/?/, "");
    const [path, qs = ""] = raw.split("?");
    const [kind, ...rest] = path.split("/");
    const id = decodeURIComponent(rest.join("/"));
    let active = kind;

    if (!kind || kind === "trainings") {
      active = "trainings";
      renderTrainings(Object.fromEntries(new URLSearchParams(qs)));
    } else if (kind === "training") {
      active = "trainings";
      renderTraining(id);
    } else if (kind === "review") {
      renderReview();
    } else if (ENTITY[kind]) {
      active = KINDS[kind];
      renderEntity(kind, id);
    } else {
      const single = Object.keys(KINDS).find((k) => KINDS[k] === kind);
      if (single && ENTITY[single]) renderEntityList(single);
      else notFound();
    }
    renderNav(active);
    window.scrollTo(0, 0);
  }

  // Swap a video thumbnail for the player only when clicked.
  app.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-yt]");
    if (!btn) return;
    const frame = document.createElement("iframe");
    frame.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(btn.dataset.yt)}?autoplay=1&rel=0`;
    frame.title = btn.getAttribute("aria-label") || "Video";
    frame.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    frame.allowFullscreen = true;
    frame.referrerPolicy = "strict-origin-when-cross-origin";
    btn.replaceWith(frame);
  });

  window.addEventListener("hashchange", router);
  router();
})();
