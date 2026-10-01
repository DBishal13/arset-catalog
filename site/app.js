(() => {
  "use strict";

  const app = document.getElementById("app");
  const C = window.CATALOG;
  if (!C) {
    app.innerHTML = '<div class="wrap page"><div class="empty">No catalog data found. Run <code>python -m arset build</code>.</div></div>';
    return;
  }

  // ================= data =================
  const KINDS = {
    training: "trainings", instructor: "instructors", satellite: "satellites",
    dataset: "datasets", tool: "tools", application: "applications",
  };
  const idx = {};
  for (const folder of Object.values(KINDS)) idx[folder] = new Map((C[folder] || []).map((r) => [r.id, r]));

  const LANG = { en: "English", es: "Spanish", fr: "French", pt: "Portuguese", ar: "Arabic" };
  const LEVELS = ["fundamentals", "introductory", "intermediate", "advanced"];
  const STATE_LABEL = {
    "in-progress": "Happening now", upcoming: "Upcoming", "self-paced": "Self-paced",
    past: "Past", unscheduled: "Unscheduled",
  };
  const FORMAT_LABEL = {
    "online-instructor-led": "Live online", "online-self-paced": "Self-paced online",
    "in-person": "In person", other: "Other",
  };
  const TYPE_LABEL = {
    slides: "Slides", homework: "Homework", exercise: "Exercise", notebook: "Notebook",
    transcript: "Transcript", qa: "Q&A", data: "Data", other: "Link",
  };
  const ORBIT_LABEL = {
    "sun-synchronous": "Sun-synchronous", geostationary: "Geostationary",
    "non-sun-synchronous": "Inclined orbit", iss: "Space Station",
  };

  // ================= icons =================
  const ICONS = {
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    play: '<path d="M7 4.5v15l13-7.5z" fill="currentColor" stroke="none"/>',
    calendar: '<rect x="3" y="4.5" width="18" height="16" rx="2.5"/><path d="M3 9.5h18M8 2.5v4M16 2.5v4"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    satellite: '<path d="m13.5 6.5-3-3-4 4 3 3"/><path d="m17.5 10.5 3 3-4 4-3-3"/><path d="m8.5 11.5 4 4 5-5-4-4z"/><path d="M4.5 19.5a5 5 0 0 1 0-7"/><path d="M7.5 16.5a1 1 0 0 1 0-1.4"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14a6.5 6.5 0 0 1 3.5 6"/>',
    slides: '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M12 16v4M8 20h8M7 8h6M7 11h10"/>',
    homework: '<rect x="5" y="3.5" width="14" height="18" rx="2"/><path d="M9 3.5h6v3H9zM9 11h6M9 15h4"/>',
    notebook: '<path d="M5 3.5h12a2 2 0 0 1 2 2v15H7a2 2 0 0 1-2-2z"/><path d="M5 18.5a2 2 0 0 1 2-2h12M9 7.5h6"/>',
    link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    database: '<ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 5.5v13c0 1.7 3.6 3 8 3s8-1.3 8-3v-13M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    tool: '<path d="M14.7 6.3a4 4 0 0 0 5 5L21 10a6 6 0 0 1-7.6-7.6z"/><path d="M14.7 6.3 4 17a2.1 2.1 0 0 0 3 3L17.7 9.3"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    video: '<rect x="2.5" y="6" width="13" height="12" rx="2"/><path d="m15.5 10.5 6-3.5v10l-6-3.5z"/>',
    inbox: '<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5.5 5h13L21 13v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-6z"/>',
    filter: '<path d="M3 5h18l-7 8.5V20l-4-2v-4.5z"/>',
    grid: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
    list: '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
    download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    hourglass: '<path d="M6 3h12M6 21h12M7 3c0 5 10 5 10 9s-10 4-10 9M17 3c0 5-10 5-10 9"/>',
    sprout: '<path d="M12 21v-9"/><path d="M12 12c0-4 3-7 8-7 0 4-3 7-8 7z"/><path d="M12 14c0-3-2.5-5.5-7-5.5 0 3 2.5 5.5 7 5.5z"/>',
    droplet: '<path d="M12 3s6.5 7 6.5 11.5a6.5 6.5 0 0 1-13 0C5.5 10 12 3 12 3z"/>',
    alert: '<path d="M12 3.5 2.5 20h19z"/><path d="M12 10v4.5M12 17.5h.01"/>',
    wind: '<path d="M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h8"/>',
    leaf: '<path d="M5 19c0-9 5-14 15-15-1 10-6 15-15 15z"/><path d="M5 19 13 11"/>',
    flame: '<path d="M12 21a6 6 0 0 0 6-6c0-4-3-6-4-10-2 2-3 4-3 6-1-1-2-2-2-4-2 2-3 5-3 8a6 6 0 0 0 6 6z"/>',
    thermo: '<path d="M10 14.5V5a2 2 0 1 1 4 0v9.5a4 4 0 1 1-4 0z"/><path d="M12 9v7"/>',
    waves: '<path d="M2 8c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2M2 13c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2M2 18c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2"/>',
  };
  const icon = (name, cls = "") => `<svg viewBox="0 0 24 24" aria-hidden="true"${cls ? ` class="${cls}"` : ""}>${ICONS[name] || ICONS.globe}</svg>`;

  const APP_STYLE = {
    agriculture: ["#4ade80", "sprout"], "water-resources": ["#38bdf8", "droplet"], disasters: ["#f87171", "alert"],
    "health-air-quality": ["#c084fc", "wind"], "ecological-conservation": ["#2dd4bf", "leaf"],
    "wildland-fires": ["#fb923c", "flame"], "climate-resilience": ["#fbbf24", "thermo"], drought: ["#d9a066", "sun"],
  };

  // ================= helpers =================
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : "");
  const plural = (n, word) => `${n.toLocaleString()} ${word}${n === 1 ? "" : "s"}`;
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
  const nameOf = (folder, id) => { const r = idx[folder].get(id); return r ? r.name || r.title : id; };
  const href = (kind, id) => `#/${kind}/${encodeURIComponent(id)}`;
  const hueOf = (s) => [...String(s)].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7);
  const initials = (name) => name.split(/\s+/).filter(Boolean).map((w) => w[0]).filter((c) => /[A-Za-z]/.test(c)).slice(0, 2).join("").toUpperCase();
  const appStyle = (id) => APP_STYLE[id] ? { c: APP_STYLE[id][0], icon: APP_STYLE[id][1] } : { c: `hsl(${hueOf(id)} 70% 62%)`, icon: "globe" };
  const colorOf = (t) => ((t.applications || []).length ? appStyle(t.applications.find((a) => APP_STYLE[a]) || t.applications[0]).c : "#4cc3ff");
  const thumb = (id, q = "mqdefault") => `https://i.ytimg.com/vi/${encodeURIComponent(id)}/${q}.jpg`;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const parseDay = (iso) => new Date(`${iso}T00:00:00`);
  const daysUntil = (iso) => Math.round((parseDay(iso) - today) / 86400000);

  function fmtDate(iso, opts = {}) {
    if (!iso) return "";
    const d = parseDay(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: opts.noYear ? undefined : "numeric" });
  }
  function dateRange(t) {
    if (!t.start_date) return "";
    if (!t.end_date || t.end_date === t.start_date) return fmtDate(t.start_date);
    const sameYear = t.start_date.slice(0, 4) === t.end_date.slice(0, 4);
    return `${fmtDate(t.start_date, { noYear: sameYear })} – ${fmtDate(t.end_date)}`;
  }
  function relative(t) {
    if (t.state === "upcoming" && t.start_date) {
      const d = daysUntil(t.start_date);
      return d <= 0 ? "Starts today" : d === 1 ? "Starts tomorrow" : d < 60 ? `Starts in ${d} days` : `Starts ${fmtDate(t.start_date)}`;
    }
    return STATE_LABEL[t.state] || "";
  }

  const allVideos = [];
  for (const t of C.trainings) {
    for (const s of t.sessions || []) for (const v of s.videos || []) allVideos.push({ v, t, s, date: s.date || t.start_date || t.published || "" });
    for (const v of t.videos || []) allVideos.push({ v, t, s: null, date: t.start_date || t.published || "" });
  }
  allVideos.sort((a, b) => b.date.localeCompare(a.date));

  // ================= building blocks =================
  function levelBars(level) {
    const n = LEVELS.indexOf(level) + 1;
    if (!n) return "";
    return `<span class="level" title="${esc(cap(level))}"><i>${[1, 2, 3, 4].map((i) => `<b class="${i <= n ? "on" : ""}"></b>`).join("")}</i>${esc(cap(level))}</span>`;
  }
  function avatar(id, size = "") {
    const p = idx.instructors.get(id) || { name: id };
    return `<span class="avatar ${size}" style="--h:${hueOf(p.name)}" title="${esc(p.name)}">${esc(initials(p.name) || "?")}</span>`;
  }
  function stateBadge(t) {
    if (!t.state) return "";
    const live = t.state === "upcoming" || t.state === "in-progress";
    return `<span class="badge${live ? " live" : ""}">${esc(relative(t))}</span>`;
  }
  function cover(t, { big = false } = {}) {
    const first = allVideos.find((x) => x.t === t);
    const c = colorOf(t);
    const glyph = appStyle((t.applications || [])[0] || "x").icon;
    const count = t.video_count || 0;
    const over = `<div class="over"><span>${stateBadge(t)}</span>${t.status === "draft" ? '<span class="badge draft">Draft</span>' : ""}</div>
      ${count ? `<span class="vids">${icon("play")} ${plural(count, "video")}</span>` : ""}`;
    if (first) {
      return `<div class="cover" style="--c:${c}"><img loading="lazy" alt="" src="${thumb(first.v.youtube, big ? "hqdefault" : "mqdefault")}">${over}</div>`;
    }
    return `<div class="cover pattern" style="--c:${c}">${icon(glyph, "glyph")}${over}</div>`;
  }
  function appChips(ids, link = false, max = 3) {
    const list = (ids || []).slice(0, max);
    if (!list.length) return "";
    return `<div class="chips">${list.map((id) => {
      const st = appStyle(id);
      const inner = `<span class="dot"></span>${esc(nameOf("applications", id))}`;
      return link ? `<a class="chip" style="--c:${st.c}" href="${href("application", id)}">${inner}</a>`
        : `<span class="chip" style="--c:${st.c}">${inner}</span>`;
    }).join("")}${(ids || []).length > max ? `<span class="chip">+${ids.length - max}</span>` : ""}</div>`;
  }
  function trainingCard(t) {
    const people = t.instructors || [];
    return `<a class="tcard reveal" href="${href("training", t.id)}">
      ${cover(t)}
      <div class="body">
        <h3>${esc(t.title)}</h3>
        <div class="metaline">
          ${t.start_date ? `<span>${icon("calendar")}${esc(dateRange(t))}</span>` : ""}
          ${(t.languages || []).length ? `<span>${icon("globe")}${esc(t.languages.map((l) => LANG[l] || l).join(" · "))}</span>` : ""}
        </div>
        ${t.summary ? `<p class="summary">${esc(t.summary)}</p>` : ""}
        ${appChips(t.applications)}
        <div class="foot">${levelBars(t.level) || '<span></span>'}
          <span class="avatars">${people.slice(0, 4).map((p) => avatar(p)).join("")}</span></div>
      </div>
    </a>`;
  }
  function videoCard({ v, t, s }) {
    const sub = [t.title, s ? `Part ${s.part}` : ""].filter(Boolean).join(" · ");
    const lang = v.language && v.language !== "en" ? `<span class="badge lang">${esc(LANG[v.language] || v.language)}</span>` : "";
    return `<button type="button" class="vcard" data-play="${esc(v.youtube)}" data-title="${esc(v.title || t.title)}"
        data-sub="${esc(sub)}" data-training="${esc(t.id)}">
      <span class="thumb"><img loading="lazy" alt="" src="${thumb(v.youtube)}">${lang}</span>
      <span class="t">${esc(v.title || "Recording")}</span>
      <span class="s">${esc(sub)}</span>
    </button>`;
  }
  const MAT_ICON = { slides: "slides", homework: "homework", notebook: "notebook", exercise: "homework", data: "database", transcript: "notebook", qa: "users", other: "link" };
  function materials(ms) {
    if (!ms || !ms.length) return "";
    return `<div class="materials">${ms.map((m) => `<a class="material" href="${esc(safeUrl(m.url))}" target="_blank" rel="noopener">
      <span class="mi">${icon(MAT_ICON[m.type] || "link")}</span>
      <span><small>${esc(TYPE_LABEL[m.type] || m.type)}${m.language && m.language !== "en" ? ` · ${esc(LANG[m.language] || m.language)}` : ""}</small>${esc(m.title || "Open")}</span></a>`).join("")}</div>`;
  }
  function facts(rows) {
    const shown = rows.filter(([, v]) => v);
    return shown.length ? `<dl class="facts">${shown.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl>` : "";
  }
  function entityChips(kind, ids, iconName) {
    if (!ids || !ids.length) return "";
    return `<div class="chips">${ids.map((id) => `<a class="chip" href="${href(kind, id)}">${icon(iconName)}${esc(nameOf(KINDS[kind], id))}</a>`).join("")}</div>`;
  }
  function setTitle(text) { document.title = text ? `${text} · EO Training Atlas` : "EO Training Atlas — an independent guide to Earth-observation trainings"; }
  function notFound(what) {
    setTitle("Not found");
    app.innerHTML = `<div class="wrap page"><div class="empty"><h2>Lost in orbit</h2><p>${esc(what || "That page")} isn't in the catalog.</p>
      <a class="btn" href="#/">Back to home</a></div></div>`;
  }
  function sortTrainings(list, how) {
    const by = (a, b) => (a || "").localeCompare(b || "");
    if (how === "soonest") return list.sort((a, b) => by(a.start_date, b.start_date));
    if (how === "oldest") return list.sort((a, b) => by(a.start_date || a.published, b.start_date || b.published));
    if (how === "az") return list.sort((a, b) => by(a.title, b.title));
    return list.sort((a, b) => by(b.start_date || b.published, a.start_date || a.published) || by(a.title, b.title));
  }

  // ================= home =================
  function orbitArt() {
    const ring = (rx, ry) => `M ${300 - rx},300 a ${rx},${ry} 0 1,0 ${2 * rx},0 a ${rx},${ry} 0 1,0 ${-2 * rx},0`;
    const orbits = [[250, 80, -22, 16, "SMAP"], [215, 120, 58, 22, "GPM"], [285, 58, 12, 30, "NISAR"]];
    return `<div class="orbit-art" aria-hidden="true"><svg viewBox="0 0 600 600">
      <defs>
        <radialGradient id="planet" cx="38%" cy="32%" r="75%">
          <stop offset="0" stop-color="#5fd0ff"/><stop offset=".45" stop-color="#1f6fb8"/><stop offset=".85" stop-color="#0b2a55"/><stop offset="1" stop-color="#061634"/>
        </radialGradient>
        <radialGradient id="atmo" cx="50%" cy="50%" r="50%">
          <stop offset=".78" stop-color="#4cc3ff" stop-opacity="0"/><stop offset=".86" stop-color="#4cc3ff" stop-opacity=".35"/><stop offset="1" stop-color="#8b7bff" stop-opacity="0"/>
        </radialGradient>
        <clipPath id="clip"><circle cx="300" cy="300" r="140"/></clipPath>
      </defs>
      <circle cx="300" cy="300" r="182" fill="url(#atmo)"/>
      <circle cx="300" cy="300" r="140" fill="url(#planet)"/>
      <g clip-path="url(#clip)"><g class="spin">
        ${[-100, -60, -20, 20, 60, 100].map((y) => `<ellipse class="grid" cx="300" cy="${300 + y}" rx="${Math.sqrt(140 * 140 - y * y)}" ry="${Math.max(4, 24 - Math.abs(y) / 6)}"/>`).join("")}
        ${[30, 70, 110].map((rx) => `<ellipse class="grid" cx="300" cy="300" rx="${rx}" ry="140"/>`).join("")}
      </g></g>
      ${orbits.map(([rx, ry, rot, dur, label], i) => `<g transform="rotate(${rot} 300 300)">
        <path class="ring${i === 0 ? " solid" : ""}" d="${ring(rx, ry)}"/>
        <g><circle class="sat" r="${i === 0 ? 5 : 4}"/><text class="label" x="10" y="-8">${label}</text>
          <animateMotion dur="${dur}s" repeatCount="indefinite" path="${ring(rx, ry)}" begin="-${i * 5}s"/></g>
      </g>`).join("")}
    </svg></div>`;
  }

  function stars(canvas) {
    const draw = () => {
      const r = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
      canvas.width = r.width * dpr; canvas.height = r.height * dpr;
      const ctx = canvas.getContext("2d");
      ctx.scale(dpr, dpr);
      let seed = 7;
      const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
      for (let i = 0; i < Math.round((r.width * r.height) / 2600); i++) {
        ctx.globalAlpha = .15 + rnd() * .75;
        ctx.fillStyle = rnd() > .85 ? "#b9d8ff" : "#ffffff";
        ctx.beginPath(); ctx.arc(rnd() * r.width, rnd() * r.height, rnd() * 1.2 + .2, 0, Math.PI * 2); ctx.fill();
      }
    };
    draw();
    let tmr; window.addEventListener("resize", () => { clearTimeout(tmr); tmr = setTimeout(() => canvas.isConnected && draw(), 200); });
  }

  function countUp(root) {
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    root.querySelectorAll("[data-count]").forEach((el) => {
      const end = +el.dataset.count;
      if (reduce || end < 5) { el.textContent = end.toLocaleString(); return; }
      const t0 = performance.now();
      const step = (now) => {
        const p = Math.min(1, (now - t0) / 1100);
        el.textContent = Math.round(end * (1 - Math.pow(1 - p, 3))).toLocaleString();
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }

  function renderHome() {
    setTitle("");
    const next = sortTrainings(C.trainings.filter((t) => t.state === "in-progress" || t.state === "upcoming"), "soonest");
    const featured = next[0];
    const apps = [...C.applications].filter((a) => (a.trainings || []).length).sort((a, b) => b.trainings.length - a.trainings.length);
    const sats = [...C.satellites].filter((s) => (s.trainings || []).length).sort((a, b) => b.trainings.length - a.trainings.length);
    const recentPast = sortTrainings(C.trainings.filter((t) => t.state === "past"), "newest").slice(0, 6);
    const stat = (n, label) => `<div class="stat"><b data-count="${n}">${n.toLocaleString()}</b><span>${label}</span></div>`;
    const hints = ["SAR", "flood", "air quality", "Landsat", "Earth Engine"];

    let featuredHtml = "";
    if (featured) {
      const d = featured.start_date ? daysUntil(featured.start_date) : 0;
      featuredHtml = `<section class="wrap section">
        <div class="section-head"><div><div class="eyebrow">${featured.state === "in-progress" ? "Happening now" : "Next up"}</div><h2>Don't miss the next live training</h2></div>
          <a href="#/trainings?state=upcoming">All upcoming ${icon("arrow")}</a></div>
        <a class="featured reveal" href="${href("training", featured.id)}">
          ${cover(featured, { big: true })}
          <div class="featured-body">
            <div class="badges"><span class="badge">${esc(FORMAT_LABEL[featured.format] || "")}</span>${levelBars(featured.level)}</div>
            <h3>${esc(featured.title)}</h3>
            <p class="muted" style="margin:0">${esc(featured.summary || "")}</p>
            ${featured.state === "upcoming" ? `<div class="countdown">
              <div><b>${Math.max(0, d)}</b><span>days</span></div>
              <div><b>${(featured.sessions || []).length || "–"}</b><span>parts</span></div>
              <div><b>${(featured.languages || []).length}</b><span>${(featured.languages || []).length === 1 ? "language" : "languages"}</span></div>
            </div>` : ""}
            <div class="metaline"><span>${icon("calendar")}${esc(dateRange(featured))}</span></div>
            <div class="avatars">${(featured.instructors || []).map((p) => avatar(p, "md")).join("")}</div>
          </div>
        </a>
        ${next.length > 1 ? `<div class="grid" style="margin-top:18px">${next.slice(1, 4).map(trainingCard).join("")}</div>` : ""}
      </section>`;
    }

    app.innerHTML = `
      <section class="hero">
        <canvas aria-hidden="true"></canvas>
        <div class="wrap hero-inner">
          <div>
            <div class="eyebrow">An independent guide · not affiliated with NASA</div>
            <h1>Find the right<br><span class="grad-text">Earth-observation training.</span></h1>
            <p class="lead">An index of NASA ARSET's free trainings, with every recording, slide deck and homework link, organized by topic, satellite and dataset. Registration and full details stay on NASA Earthdata.</p>
            <form class="hero-search" id="hero-search" role="search">
              ${icon("search")}
              <input name="q" type="search" placeholder="Try &ldquo;flood mapping&rdquo;, &ldquo;SMAP&rdquo; or an instructor…" aria-label="Search trainings">
              <button class="btn primary" type="submit">Search</button>
            </form>
            <div class="hero-hints"><span>Popular:</span>${hints.map((h) => `<a href="#/trainings?q=${encodeURIComponent(h)}">${esc(h)}</a>`).join("")}</div>
            <div class="stats">
              ${stat(C.trainings.length, "trainings")}${stat(allVideos.length, "recordings")}${stat(C.instructors.length, "instructors")}
              ${stat(sats.length, "satellites used")}${stat(C.datasets.length, "datasets")}
            </div>
          </div>
          ${orbitArt()}
        </div>
      </section>
      ${featuredHtml}
      <section class="wrap section">
        <div class="section-head"><div><div class="eyebrow">Explore by topic</div><h2>What do you want to monitor?</h2></div>
          <a href="#/applications">All applications ${icon("arrow")}</a></div>
        <div class="grid sm">${apps.map((a) => { const st = appStyle(a.id); return `
          <a class="ecard app-tile reveal" style="--c:${st.c}" href="${href("application", a.id)}">
            <div class="row"><span class="icon">${icon(st.icon)}</span><span class="big">${a.trainings.length}</span></div>
            <h3>${esc(a.name)}</h3><p class="sub">${esc(a.description || "")}</p></a>`; }).join("")}</div>
      </section>
      ${allVideos.length ? `<section class="wrap section">
        <div class="section-head"><div><div class="eyebrow">Watch</div><h2>Latest recordings</h2></div>
          <a href="#/trainings?sort=newest">Browse trainings ${icon("arrow")}</a></div>
        <div class="rail">${allVideos.slice(0, 12).map(videoCard).join("")}</div>
      </section>` : ""}
      ${recentPast.length ? `<section class="wrap section">
        <div class="section-head"><div><div class="eyebrow">Catch up</div><h2>Recently completed</h2></div>
          <a href="#/trainings?state=past">All past trainings ${icon("arrow")}</a></div>
        <div class="grid">${recentPast.map(trainingCard).join("")}</div>
      </section>` : ""}
      ${sats.length ? `<section class="wrap section">
        <div class="section-head"><div><div class="eyebrow">The fleet</div><h2>Satellites you'll learn to use</h2></div>
          <a href="#/satellites">Fleet timeline ${icon("arrow")}</a></div>
        <div class="chips">${sats.map((s) => `<a class="chip" href="${href("satellite", s.id)}">${icon("satellite")}${esc(s.name)} <span class="muted">${s.trainings.length}</span></a>`).join("")}</div>
      </section>` : ""}`;

    stars(app.querySelector(".hero canvas"));
    countUp(app);
    app.querySelector("#hero-search").addEventListener("submit", (e) => {
      e.preventDefault();
      const q = new FormData(e.target).get("q").trim();
      location.hash = q ? `#/trainings?q=${encodeURIComponent(q)}` : "#/trainings";
    });
  }

  // ================= trainings browser =================
  const haystack = new Map();
  for (const t of C.trainings) {
    const parts = [t.title, t.summary, t.description, t.level, ...(t.objectives || []), ...(t.tags || [])];
    for (const [field, folder] of [["instructors", "instructors"], ["satellites", "satellites"], ["datasets", "datasets"], ["tools", "tools"], ["applications", "applications"]]) {
      for (const id of t[field] || []) parts.push(nameOf(folder, id), id);
    }
    for (const s of t.sessions || []) parts.push(s.title, ...(s.agenda || []));
    haystack.set(t.id, parts.filter(Boolean).join(" \n ").toLowerCase());
  }
  const counts = (field) => {
    const m = new Map();
    for (const t of C.trainings) for (const id of [].concat(t[field] || [])) m.set(id, (m.get(id) || 0) + 1);
    return m;
  };

  function renderTrainings(params) {
    setTitle("Trainings");
    const f = { q: params.q || "", state: params.state || "", level: params.level || "", app: params.app || "",
      lang: params.lang || "", sat: params.sat || "", sort: params.sort || "recommended", view: params.view || "grid" };

    const facetDefs = [
      ["state", "When", Object.keys(STATE_LABEL).filter((s) => C.trainings.some((t) => t.state === s)).map((s) => [s, STATE_LABEL[s]]), "state"],
      ["level", "Level", LEVELS.filter((l) => C.trainings.some((t) => t.level === l)).map((l) => [l, cap(l)]), "level"],
      ["app", "Application", [...counts("applications").keys()].sort((a, b) => nameOf("applications", a).localeCompare(nameOf("applications", b))).map((id) => [id, nameOf("applications", id)]), "applications"],
      ["lang", "Language", [...counts("languages").keys()].sort().map((l) => [l, LANG[l] || l]), "languages"],
      ["sat", "Satellite", [...counts("satellites").entries()].sort((a, b) => b[1] - a[1]).map(([id]) => [id, nameOf("satellites", id)]), "satellites"],
    ];
    const countFor = (field, value) => C.trainings.filter((t) => [].concat(t[field] || []).includes(value)).length;

    app.innerHTML = `<div class="wrap page">
      <div class="page-head"><div class="eyebrow">Catalog</div><h1>Trainings</h1>
        <p>${plural(C.trainings.length, "training")} with ${plural(allVideos.length, "recording")}. Filter by topic, satellite, level or language.</p></div>
      <div class="browser">
        <aside class="facets" id="facets" aria-label="Filters">
          ${facetDefs.map(([key, label, opts, field]) => opts.length ? `<div class="facet"><h4>${label}</h4><div class="opts">
            ${opts.map(([value, text]) => { const c = key === "app" ? appStyle(value).c : ""; return `<button type="button" class="pill" data-facet="${key}" data-value="${esc(value)}"
              aria-pressed="${f[key] === value}"${c ? ` style="--c:${c}"` : ""}>${c ? '<span class="dot"></span>' : ""}${esc(text)} <span class="n">${countFor(field === "state" ? "state" : field === "level" ? "level" : field, value)}</span></button>`; }).join("")}
          </div></div>` : "").join("")}
        </aside>
        <div>
          <div class="toolbar">
            <label class="searchbox">${icon("search")}<input id="f-q" type="search" value="${esc(f.q)}" placeholder="Search titles, topics, instructors, satellites…" aria-label="Search trainings"></label>
            <button type="button" class="btn facets-toggle" id="facets-toggle" aria-expanded="false" aria-controls="facets">${icon("filter")}Filters</button>
            <select class="select" id="f-sort" aria-label="Sort">
              ${[["recommended", "Recommended"], ["newest", "Newest first"], ["oldest", "Oldest first"], ["az", "A–Z"]].map(([v, l]) => `<option value="${v}"${f.sort === v ? " selected" : ""}>${l}</option>`).join("")}
            </select>
            <div class="seg" role="group" aria-label="View">
              <button type="button" data-view="grid" aria-pressed="${f.view === "grid"}" aria-label="Grid view">${icon("grid")}</button>
              <button type="button" data-view="list" aria-pressed="${f.view === "list"}" aria-label="Timeline view">${icon("list")}</button>
            </div>
          </div>
          <div class="resultline"><span id="result-count" aria-live="polite"></span><button type="button" class="linkish" id="f-clear">Clear all</button></div>
          <div id="results"></div>
        </div>
      </div></div>`;

    const $ = (sel) => app.querySelector(sel);
    const tlRow = (t) => {
      const d = t.start_date ? parseDay(t.start_date) : null;
      return `<a class="tl-row reveal" href="${href("training", t.id)}">
        <div class="datebox">${d ? `<span>${d.toLocaleDateString("en-US", { month: "short" })}</span><b>${d.getDate()}</b><span>${d.getFullYear()}</span>`
          : `<span>Any</span><b>${icon("hourglass")}</b><span>time</span>`}</div>
        <div><h3>${esc(t.title)}</h3><div class="metaline">${stateBadge(t)}${levelBars(t.level)}
          <span>${icon("video")}${t.video_count || 0}</span>${t.status === "draft" ? '<span class="badge draft">Draft</span>' : ""}</div></div>
        <div>${appChips(t.applications, false, 2)}</div></a>`;
    };

    function update() {
      const terms = f.q.toLowerCase().split(/\s+/).filter(Boolean);
      const hits = C.trainings.filter((t) =>
        (!f.app || (t.applications || []).includes(f.app)) && (!f.sat || (t.satellites || []).includes(f.sat)) &&
        (!f.level || t.level === f.level) && (!f.lang || (t.languages || []).includes(f.lang)) &&
        (!f.state || t.state === f.state) && terms.every((term) => haystack.get(t.id).includes(term)));
      const active = ["q", "state", "level", "app", "lang", "sat"].some((k) => f[k]);
      $("#f-clear").hidden = !active;
      $("#result-count").textContent = active ? `${plural(hits.length, "training")} match` : `All ${plural(hits.length, "training")}`;
      const render = f.view === "list" ? (list) => `<div class="tl">${list.map(tlRow).join("")}</div>` : (list) => `<div class="grid">${list.map(trainingCard).join("")}</div>`;
      let html;
      if (f.sort === "recommended") {
        html = [
          ["Happening now & upcoming", (t) => t.state === "in-progress" || t.state === "upcoming", "soonest"],
          ["Self-paced — start any time", (t) => t.state === "self-paced", "newest"],
          ["Past trainings", (t) => t.state === "past", "newest"],
          ["Not scheduled", (t) => t.state === "unscheduled", "az"],
        ].map(([label, test, how]) => { const list = sortTrainings(hits.filter(test), how); return list.length ? `<div class="group-title">${esc(label)} · ${list.length}</div>${render(list)}` : ""; }).join("");
      } else {
        html = render(sortTrainings([...hits], f.sort));
      }
      $("#results").innerHTML = html || `<div class="empty">No trainings match. <button type="button" class="linkish" data-clear>Clear filters</button></div>`;
      app.querySelectorAll(".pill").forEach((p) => p.setAttribute("aria-pressed", String(f[p.dataset.facet] === p.dataset.value)));
      app.querySelectorAll("[data-view]").forEach((b) => b.setAttribute("aria-pressed", String(f.view === b.dataset.view)));
      const qs = new URLSearchParams(Object.entries(f).filter(([k, v]) => v && !(k === "sort" && v === "recommended") && !(k === "view" && v === "grid"))).toString();
      history.replaceState(null, "", qs ? `#/trainings?${qs}` : "#/trainings");
    }
    const clear = () => { for (const k of ["q", "state", "level", "app", "lang", "sat"]) f[k] = ""; $("#f-q").value = ""; update(); };

    $("#f-q").addEventListener("input", (e) => { f.q = e.target.value.trim(); update(); });
    $("#f-sort").addEventListener("change", (e) => { f.sort = e.target.value; update(); });
    $("#f-clear").addEventListener("click", clear);
    $("#facets-toggle").addEventListener("click", (e) => {
      const open = $("#facets").classList.toggle("open");
      e.currentTarget.setAttribute("aria-expanded", String(open));
    });
    browser = { f, update, clear };
    update();
  }
  let browser = null; // state of the trainings page while it is shown
  app.addEventListener("click", (e) => {
    if (!browser || !app.querySelector("#results")) return;
    const { f, update, clear } = browser;
    const pill = e.target.closest(".pill");
    if (pill) { f[pill.dataset.facet] = f[pill.dataset.facet] === pill.dataset.value ? "" : pill.dataset.value; update(); }
    const view = e.target.closest("[data-view]");
    if (view) { f.view = view.dataset.view; update(); }
    if (e.target.closest("[data-clear]")) clear();
  });

  // ================= training detail =================
  function ics(t) {
    const escI = (s) => String(s).replace(/[\\;,]/g, (c) => `\\${c}`).replace(/\n/g, "\\n");
    const day = (iso) => iso.replace(/-/g, "");
    const next = (iso) => { const d = parseDay(iso); d.setDate(d.getDate() + 1); return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`; };
    const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+/, "");
    const events = (t.sessions || []).filter((s) => s.date).map((s) => [`part${s.part}`, s.date, `ARSET: ${t.title} (Part ${s.part})`, s.title]);
    if (!events.length && t.start_date) events.push(["all", t.start_date, `ARSET: ${t.title}`, t.summary || ""]);
    const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//EO Training Atlas//EN", "CALSCALE:GREGORIAN"];
    for (const [key, date, summary, desc] of events) {
      lines.push("BEGIN:VEVENT", `UID:${t.id}-${key}@eo-training-atlas`, `DTSTAMP:${stamp}`, `DTSTART;VALUE=DATE:${day(date)}`,
        `DTEND;VALUE=DATE:${next(date)}`, `SUMMARY:${escI(summary)}`, `DESCRIPTION:${escI(`${desc}\nTimes and registration: ${t.source_url}`)}`,
        `URL:${t.source_url}`, "END:VEVENT");
    }
    lines.push("END:VCALENDAR");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([lines.join("\r\n")], { type: "text/calendar" }));
    a.download = `${t.id.slice(0, 60)}.ics`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  function renderTraining(id) {
    const t = idx.trainings.get(id);
    if (!t) return notFound("That training");
    setTitle(t.title);
    const vids = allVideos.filter((x) => x.t === t).sort((a, b) => (a.s ? a.s.part : 99) - (b.s ? b.s.part : 99));
    const first = vids[0];
    const c = colorOf(t);
    const canCal = (t.state === "upcoming" || t.state === "in-progress") && t.start_date;
    const parts = (t.sessions || []).length;

    const sessions = (t.sessions || []).map((s) => {
      const sv = vids.filter((x) => x.s === s);
      const done = s.date && daysUntil(s.date) < 0;
      return `<section class="session${done ? " done" : ""}">
        <span class="node">${esc(s.part)}</span>
        <div class="session-head"><h3>${esc(s.title)}</h3>${s.date ? `<span class="when">${icon("calendar")}${esc(fmtDate(s.date))}</span>` : ""}</div>
        ${sv.length ? `<div class="rail">${sv.map(videoCard).join("")}</div>` : ""}
        ${materials(s.materials)}
        ${!sv.length && !(s.materials || []).length ? `<p class="pending">${icon("hourglass")}${done ? "Recording and materials not posted yet." : "Recording and slides appear here after the session."}</p>` : ""}
        ${(s.agenda || []).length ? `<details class="agenda"><summary>Agenda · ${s.agenda.length} items</summary><ol>${s.agenda.map((a) => `<li>${esc(a)}</li>`).join("")}</ol></details>` : ""}
      </section>`;
    }).join("");
    const extraVids = vids.filter((x) => !x.s);
    const extra = extraVids.length || (t.materials || []).length ? `<section class="session"><span class="node">+</span>
      <div class="session-head"><h3>More resources</h3></div>
      ${extraVids.length ? `<div class="rail">${extraVids.map(videoCard).join("")}</div>` : ""}${materials(t.materials)}</section>` : "";

    const people = (t.instructors || []).map((pid) => {
      const p = idx.instructors.get(pid) || { name: pid };
      return `<li>${avatar(pid, "md")}<div><a href="${href("instructor", pid)}">${esc(p.name)}</a>
        <span class="muted">${esc([p.title, p.affiliation].filter(Boolean).join(" · "))}</span></div></li>`;
    }).join("");
    const prereqs = (t.prerequisites || []).map((pid) => idx.trainings.has(pid)
      ? `<li><a href="${href("training", pid)}">${esc(nameOf("trainings", pid))}</a></li>`
      : `<li><a href="https://www.earthdata.nasa.gov/learn/trainings/${encodeURIComponent(pid)}" target="_blank" rel="noopener">${esc(cap(pid.replace(/-/g, " ")))} ↗</a></li>`).join("");
    const panel = (title, body) => (body ? `<div class="panel"><h4>${esc(title)}</h4>${body}</div>` : "");

    app.innerHTML = `
      <section class="thero" style="--c:${c}">
        ${first ? `<div class="bg" style="background-image:url('${thumb(first.v.youtube, "hqdefault")}')"></div>` : '<div class="bg pattern"></div>'}
        <div class="wrap thero-inner">
          <div>
            <nav class="crumbs" aria-label="Breadcrumb"><a href="#/">Home</a>/<a href="#/trainings">Trainings</a></nav>
            <div class="badges">${stateBadge(t)}${t.format ? `<span class="badge">${esc(FORMAT_LABEL[t.format] || t.format)}</span>` : ""}
              ${t.status === "draft" ? '<span class="badge draft" title="Machine-generated; not reviewed yet">Draft</span>' : ""}</div>
            <h1>${esc(t.title)}</h1>
            ${t.summary ? `<p class="lead">${esc(t.summary)}</p>` : ""}
            <div class="keyfacts">
              ${t.start_date ? `<span>${icon("calendar")}${esc(dateRange(t))}</span>` : ""}
              ${parts ? `<span>${icon("layers")}${plural(parts, "part")}</span>` : ""}
              ${vids.length ? `<span>${icon("video")}${plural(vids.length, "recording")}</span>` : ""}
              ${(t.languages || []).length ? `<span>${icon("globe")}${esc(t.languages.map((l) => LANG[l] || l).join(", "))}</span>` : ""}
              ${t.level ? `<span>${levelBars(t.level)}</span>` : ""}
            </div>
            <div class="btn-row">
              ${first ? `<button type="button" class="btn primary" data-play="${esc(first.v.youtube)}" data-title="${esc(first.v.title || t.title)}" data-sub="${esc(t.title)}" data-training="${esc(t.id)}">${icon("play")}Watch${first.s ? ` Part ${esc(first.s.part)}` : ""}</button>` : ""}
              ${canCal ? `<button type="button" class="btn${first ? "" : " primary"}" id="add-cal">${icon("calendar")}Add to calendar</button>` : ""}
              <a class="btn" href="${esc(safeUrl(t.source_url))}" target="_blank" rel="noopener">${icon("external")}${t.state === "upcoming" ? "Register on Earthdata" : "View on Earthdata"}</a>
            </div>
          </div>
          ${first ? `<button type="button" class="hero-video" data-play="${esc(first.v.youtube)}" data-title="${esc(first.v.title || t.title)}" data-sub="${esc(t.title)}" data-training="${esc(t.id)}" aria-label="Play ${esc(first.v.title || "recording")}">
              <img alt="" src="${thumb(first.v.youtube, "hqdefault")}">
              <span class="play">${icon("play")}</span><span class="cap">${esc(first.v.title || "")}</span></button>`
            : `<div class="hero-art">${cover(t, { big: true })}</div>`}
        </div>
      </section>
      <div class="wrap detail">
        <article class="prose">
          ${sessions || extra ? `<h2 style="margin-top:0">Sessions</h2><div class="sessions">${sessions}${extra}</div>` : ""}
          <div class="panel source-card">
            <div><h4>Full details on NASA Earthdata</h4>
              <p>The complete description, learning objectives, target audience, schedule, registration and certificate
                requirements are on the official training page.</p></div>
            <a class="btn" href="${esc(safeUrl(t.source_url))}" target="_blank" rel="noopener">${icon("external")}Open the training page</a>
          </div>
          ${t.notes ? `<h2>Notes</h2><p>${esc(t.notes)}</p>` : ""}
        </article>
        <aside class="side">
          ${panel("Instructors", people && `<ul class="people">${people}</ul>`)}
          ${panel("At a glance", facts([
            ["Dates", esc(dateRange(t))], ["Level", esc(cap(t.level))], ["Format", esc(FORMAT_LABEL[t.format] || "")],
            ["Languages", esc((t.languages || []).map((l) => LANG[l] || l).join(", "))], ["Recordings", String(vids.length)],
            ["Published", esc(fmtDate(t.published))], ["Updated", esc(fmtDate(t.last_updated))],
          ]))}
          ${panel("Satellites", entityChips("satellite", t.satellites, "satellite"))}
          ${panel("Datasets", entityChips("dataset", t.datasets, "database"))}
          ${panel("Tools", entityChips("tool", t.tools, "tool"))}
          ${panel("Applications", appChips(t.applications, true, 99))}
          ${panel("Before you start", prereqs && `<ul style="margin:0;padding-left:1.1em">${prereqs}</ul>`)}
        </aside>
      </div>`;
    const cal = app.querySelector("#add-cal");
    if (cal) cal.addEventListener("click", () => ics(t));
  }

  // ================= other record types =================
  const list = (xs) => esc((xs || []).join(", "));
  const ENTITY = {
    instructor: {
      label: "Instructors", icon: "user", eyebrow: "Instructor",
      intro: "The scientists and trainers who teach ARSET courses.",
      sub: (r) => [r.title, r.affiliation].filter(Boolean).join(" · "),
      facts: (r) => [["Role", esc(r.title)], ["Affiliation", esc(r.affiliation)], ["Expertise", list(r.expertise)]],
    },
    satellite: {
      label: "Satellites", icon: "satellite", eyebrow: "Satellite",
      intro: "Missions whose data ARSET trainings teach you to use, placed by launch date.",
      sub: (r) => r.full_name || "",
      facts: (r) => [["Full name", esc(r.full_name)], ["Agencies", list(r.agencies)], ["Launched", esc(fmtDate(r.launch_date))],
        ["Status", esc(cap(r.status))], ["Orbit", esc(ORBIT_LABEL[r.orbit] || r.orbit || "")],
        ["Instruments", esc((r.instruments || []).map((i) => i.name).join(", "))]],
    },
    dataset: {
      label: "Datasets", icon: "database", eyebrow: "Dataset",
      intro: "Data products used in ARSET trainings, and where to get them.",
      sub: (r) => [r.short_name, r.provider].filter(Boolean).join(" · "),
      facts: (r) => [["Short name", r.short_name ? `<code>${esc(r.short_name)}</code>` : ""], ["Provider", esc(r.provider)],
        ["Satellites", (r.satellites || []).map((s) => `<a href="${href("satellite", s)}">${esc(nameOf("satellites", s))}</a>`).join(", ")],
        ["Variables", list(r.variables)], ["Resolution", esc(r.resolution)]],
    },
    tool: {
      label: "Tools", icon: "tool", eyebrow: "Tool",
      intro: "Software and platforms used in hands-on demonstrations.",
      sub: (r) => [cap((r.kind || "").replace(/-/g, " ")), r.open_source ? "open source" : ""].filter(Boolean).join(" · "),
      facts: (r) => [["Kind", esc(cap((r.kind || "").replace(/-/g, " ")))], ["Open source", r.open_source === undefined ? "" : r.open_source ? "Yes" : "No"]],
    },
    application: {
      label: "Applications", icon: "globe", eyebrow: "Application area",
      intro: "The problems ARSET trainings help you tackle with Earth observations.",
      sub: (r) => r.description || "",
      facts: (r) => [["Part of", r.parent ? `<a href="${href("application", r.parent)}">${esc(nameOf("applications", r.parent))}</a>` : ""]],
    },
  };

  function fleetTimeline() {
    const sats = C.satellites.filter((s) => s.launch_date).sort((a, b) => a.launch_date.localeCompare(b.launch_date));
    if (!sats.length) return "";
    const y0 = +sats[0].launch_date.slice(0, 4) - 1, y1 = today.getFullYear() + 1;
    const W = 1000, pad = 20, x = (iso) => pad + ((+iso.slice(0, 4) + (+iso.slice(5, 7) - 1) / 12 - y0) / (y1 - y0)) * (W - 2 * pad);
    const lanes = [];
    const placed = sats.map((s) => {
      const px = x(s.launch_date);
      let lane = lanes.findIndex((end) => end < px - 4);
      if (lane < 0) { lane = lanes.length; lanes.push(0); }
      lanes[lane] = px + s.name.length * 7.2 + 18;
      return { s, px, lane };
    });
    const axisY = 24 + lanes.length * 24 + 10, H = axisY + 30;
    const ticks = [];
    for (let y = Math.ceil(y0 / 5) * 5; y <= y1; y += 5) ticks.push(y);
    return `<div class="fleet"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Satellite launch timeline">
      <line class="axis" x1="${pad}" x2="${W - pad}" y1="${axisY}" y2="${axisY}"/>
      ${ticks.map((y) => { const px = x(`${y}-01`); return `<line class="axis" x1="${px}" x2="${px}" y1="${axisY}" y2="${axisY + 5}"/><text class="tick" x="${px}" y="${axisY + 20}" text-anchor="middle">${y}</text>`; }).join("")}
      ${placed.map(({ s, px, lane }) => { const y = 24 + lane * 24; return `<a href="${href("satellite", s.id)}">
        <line class="stem" x1="${px}" x2="${px}" y1="${y}" y2="${axisY}" stroke-dasharray="2 3"/>
        <circle class="pt${s.status === "inactive" ? " off" : ""}" cx="${px}" cy="${y}" r="5"/>
        <text x="${px + 9}" y="${y + 4}">${esc(s.name)}</text><title>${esc(s.name)} · launched ${esc(fmtDate(s.launch_date))}</title></a>`; }).join("")}
    </svg></div>`;
  }

  function miniOrbit(r) {
    const rot = { "sun-synchronous": 78, geostationary: 0, iss: 52, "non-sun-synchronous": 30 }[r.orbit] ?? 30;
    const [rx, ry] = r.orbit === "geostationary" ? [86, 86] : [80, 24];
    const path = `M ${90 - rx},60 a ${rx},${ry} 0 1,0 ${2 * rx},0 a ${rx},${ry} 0 1,0 ${-2 * rx},0`;
    return `<div class="mini-orbit" aria-hidden="true"><svg viewBox="0 0 180 120">
      <defs><radialGradient id="mp" cx="38%" cy="32%" r="75%"><stop offset="0" stop-color="#5fd0ff"/><stop offset=".6" stop-color="#1f6fb8"/><stop offset="1" stop-color="#0b2a55"/></radialGradient></defs>
      <circle cx="90" cy="60" r="${r.orbit === "geostationary" ? 18 : 34}" fill="url(#mp)"/>
      <g transform="rotate(${rot} 90 60)"><path d="${path}" fill="none" stroke="rgba(76,195,255,.45)" stroke-dasharray="3 4"/>
        <circle r="4" fill="#fff"><animateMotion dur="${r.orbit === "geostationary" ? 24 : 7}s" repeatCount="indefinite" path="${path}"/></circle></g>
    </svg></div>`;
  }

  function entityCard(kind, r) {
    const n = (r.trainings || []).length;
    const foot = `<div class="foot"><span>${plural(n, "training")}</span>${icon("arrow")}</div>`;
    const draft = r.status === "draft" ? '<span class="badge draft">Draft</span>' : "";
    if (kind === "instructor") {
      return `<a class="ecard reveal" href="${href(kind, r.id)}"><div class="row">${avatar(r.id, "md")}<div><h3>${esc(r.name)}</h3>
        <p class="sub">${esc(r.title || "")}</p></div></div><p class="sub">${esc(r.affiliation || "")}</p>${draft}${foot}</a>`;
    }
    if (kind === "application") {
      const st = appStyle(r.id);
      return `<a class="ecard app-tile reveal" style="--c:${st.c}" href="${href(kind, r.id)}"><div class="row"><span class="icon">${icon(st.icon)}</span>
        <span class="big">${n}</span></div><h3>${esc(r.name)}</h3><p class="sub">${esc(r.description || "")}</p></a>`;
    }
    const cfg = ENTITY[kind];
    const extra = kind === "satellite"
      ? `<div class="badges">${r.launch_date ? `<span class="badge">${esc(r.launch_date.slice(0, 4))}</span>` : ""}${r.orbit ? `<span class="badge">${esc(ORBIT_LABEL[r.orbit] || r.orbit)}</span>` : ""}${r.status === "inactive" ? '<span class="badge">Retired</span>' : ""}</div>`
      : "";
    return `<a class="ecard reveal" href="${href(kind, r.id)}"><div class="row"><span class="icon">${icon(cfg.icon)}</span>
      <div style="min-width:0"><h3>${esc(r.name)}</h3><p class="sub">${esc(cfg.sub(r))}</p></div></div>${extra}${draft}${foot}</a>`;
  }

  function renderEntityList(kind) {
    const cfg = ENTITY[kind];
    const rows = [...C[KINDS[kind]]].sort((a, b) => (b.trainings || []).length - (a.trainings || []).length || (a.name || "").localeCompare(b.name || ""));
    setTitle(cfg.label);
    app.innerHTML = `<div class="wrap page">
      <div class="page-head"><div class="eyebrow">Catalog</div><h1>${esc(cfg.label)}</h1><p>${esc(cfg.intro)} ${plural(rows.length, cfg.eyebrow.toLowerCase())} in the catalog.</p></div>
      ${kind === "satellite" ? fleetTimeline() : ""}
      <div class="grid sm">${rows.map((r) => entityCard(kind, r)).join("")}</div></div>`;
  }

  function renderEntity(kind, id) {
    const cfg = ENTITY[kind];
    const r = idx[KINDS[kind]].get(id);
    if (!r) return notFound(`That ${kind}`);
    setTitle(r.name);
    const trainings = sortTrainings((r.trainings || []).map((tid) => idx.trainings.get(tid)).filter(Boolean), "newest");
    const vids = allVideos.filter((x) => trainings.includes(x.t)).slice(0, 16);
    const st = kind === "application" ? appStyle(id) : null;
    let related = "";
    if (kind === "satellite") {
      const ds = C.datasets.filter((d) => (d.satellites || []).includes(id)).map((d) => d.id);
      if (ds.length) related = `<div class="panel"><h4>Datasets from ${esc(r.name)}</h4>${entityChips("dataset", ds, "database")}</div>`;
    }
    if (kind === "application") {
      const kids = C.applications.filter((a) => a.parent === id).map((a) => a.id);
      if (kids.length) related = `<div class="panel"><h4>Narrower areas</h4>${appChips(kids, true, 99)}</div>`;
    }
    const factHtml = facts(cfg.facts(r));
    const links = [r.url, ...(r.links || [])].filter(Boolean);
    const art = kind === "instructor" ? avatar(id, "lg") : kind === "satellite" ? miniOrbit(r)
      : `<span class="icon-xl"${st ? ` style="--c:${st.c}"` : ""}>${icon(st ? st.icon : cfg.icon)}</span>`;

    app.innerHTML = `<div class="wrap">
      <div class="ehero"${st ? ` style="--c:${st.c}"` : ""}>
        <div>
          <nav class="crumbs" aria-label="Breadcrumb"><a href="#/">Home</a>/${kind === "instructor"
            ? '<a href="#/trainings">Trainings</a>' : `<a href="#/${KINDS[kind]}">${esc(cfg.label)}</a>`}</nav>
          <div class="eyebrow">${esc(cfg.eyebrow)}</div>
          <h1 style="margin:8px 0 10px">${esc(r.name)}</h1>
          ${cfg.sub(r) ? `<p class="lead muted" style="font-size:1.05rem;max-width:44em">${esc(cfg.sub(r))}</p>` : ""}
          <div class="badges">${r.status === "draft" ? '<span class="badge draft">Draft</span>' : ""}<span class="badge">${plural(trainings.length, "training")}</span>
            ${vids.length ? `<span class="badge">${plural(vids.length, "recording")}</span>` : ""}</div>
        </div>
        ${art}
      </div>
      ${factHtml || links.length || r.notes || related ? `<div class="grid" style="margin:18px 0 8px">
        ${factHtml || links.length || r.notes ? `<div class="panel"><h4>Details</h4>${factHtml}
          ${r.notes ? `<p class="small muted" style="margin:12px 0 0">${esc(r.notes)}</p>` : ""}
          ${links.map((u) => `<p class="small" style="margin:12px 0 0"><a href="${esc(safeUrl(u))}" target="_blank" rel="noopener">${esc(u.replace(/^https?:\/\//, ""))} ↗</a></p>`).join("")}</div>` : ""}
        ${related}</div>` : ""}
      ${vids.length ? `<section class="section" style="padding-top:28px"><div class="section-head"><h2>Recordings</h2></div><div class="rail">${vids.map(videoCard).join("")}</div></section>` : ""}
      <section class="section" style="padding-top:28px"><div class="section-head"><h2>Trainings</h2></div>
        ${trainings.length ? `<div class="grid">${trainings.map(trainingCard).join("")}</div>` : '<div class="empty">No trainings reference this yet.</div>'}</section>
    </div>`;
  }

  // ================= review =================
  const drafts = () => ({
    trainings: C.trainings.filter((t) => t.status === "draft"),
    instructors: C.instructors.filter((p) => p.status === "draft"),
    videos: C.inbox_videos || [],
  });
  function renderReview() {
    setTitle("Review");
    const d = drafts();
    const table = (head, rows) => rows.length
      ? `<div class="table-wrap"><table class="table"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`
      : '<div class="empty">All clear.</div>';
    app.innerHTML = `<div class="wrap page">
      <div class="page-head"><div class="eyebrow">Maintainers</div><h1>Review queue</h1>
        <p>Records the tracker created that nobody has checked yet. Edit the YAML in <code>data/</code> and set <code>status: reviewed</code>.</p></div>
      <div class="stats" style="margin:0 0 28px;max-width:520px;grid-template-columns:repeat(3,1fr)">
        <div class="stat"><b>${d.trainings.length}</b><span>draft trainings</span></div>
        <div class="stat"><b>${d.instructors.length}</b><span>draft instructors</span></div>
        <div class="stat"><b>${d.videos.length}</b><span>unassigned videos</span></div></div>
      <h2>Draft trainings</h2>
      ${table(["Training", "Dates", "Tags", "File"], sortTrainings([...d.trainings], "newest").map((t) => `<tr>
        <td><a href="${href("training", t.id)}">${esc(t.title)}</a></td><td class="small">${esc(dateRange(t) || STATE_LABEL[t.state] || "")}</td>
        <td class="small">${esc(["applications", "satellites", "datasets", "tools"].map((f) => `${(t[f] || []).length} ${f}`).join(" · "))}</td>
        <td class="small muted"><code>data/trainings/${esc(t.id)}.yaml</code></td></tr>`))}
      <h2 style="margin-top:36px">Draft instructors</h2>
      ${table(["Name", "Role", "Affiliation"], d.instructors.map((p) => `<tr>
        <td><a href="${href("instructor", p.id)}">${esc(p.name)}</a></td><td class="small">${esc(p.title)}</td><td class="small">${esc(p.affiliation)}</td></tr>`))}
      <h2 style="margin-top:36px">Unassigned videos</h2>
      <p class="muted small">ARSET uploads no training references. Move each into a training's session, then delete it from <code>inbox/videos.yaml</code>.</p>
      ${table(["Published", "Title", "Channel"], d.videos.map((v) => `<tr>
        <td class="small">${esc(fmtDate(v.published))}</td>
        <td><a href="${esc(safeUrl(v.url))}" target="_blank" rel="noopener">${esc(v.title)} ↗</a><div class="small muted"><code>${esc(v.youtube)}</code></div></td>
        <td class="small">${esc(v.channel)}</td></tr>`))}
    </div>`;
  }

  // ================= video player =================
  const player = document.getElementById("player");
  let lastFocus = null;
  function openPlayer(el) {
    lastFocus = document.activeElement;
    const id = el.dataset.play, tid = el.dataset.training;
    document.getElementById("player-title").textContent = el.dataset.title || "Recording";
    document.getElementById("player-sub").textContent = el.dataset.sub || "";
    document.getElementById("player-frame").innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0"
      title="${esc(el.dataset.title || "Video")}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>`;
    const onTraining = location.hash.startsWith(`#/training/${encodeURIComponent(tid)}`);
    document.getElementById("player-foot").innerHTML = `<a href="https://www.youtube.com/watch?v=${encodeURIComponent(id)}" target="_blank" rel="noopener">${icon("external")} Open on YouTube</a>
      ${tid && !onTraining ? `<a class="btn" href="${href("training", tid)}" data-close>Go to training ${icon("arrow")}</a>` : ""}`;
    player.hidden = false;
    document.body.style.overflow = "hidden";
    player.querySelector("button[data-close]").focus();
  }
  function closePlayer() {
    if (player.hidden) return;
    player.hidden = true;
    document.getElementById("player-frame").innerHTML = "";
    document.body.style.overflow = "";
    if (lastFocus && lastFocus.isConnected) lastFocus.focus();
  }
  player.addEventListener("click", (e) => { if (e.target.closest("[data-close]")) closePlayer(); });
  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-play]");
    if (el && !player.contains(el)) { e.preventDefault(); openPlayer(el); }
  });

  // ================= command palette =================
  const palette = document.getElementById("palette");
  const pq = document.getElementById("palette-q");
  const presults = document.getElementById("palette-results");
  const PAL_KINDS = [["training", "Trainings"], ["instructor", "Instructors"], ["satellite", "Satellites"], ["dataset", "Datasets"], ["tool", "Tools"], ["application", "Applications"]];
  const palIndex = PAL_KINDS.flatMap(([kind]) => C[KINDS[kind]].map((r) => {
    const title = r.title || r.name;
    const sub = kind === "training" ? [relative(r), dateRange(r)].filter(Boolean).join(" · ") : ENTITY[kind].sub(r);
    const ic = kind === "training" ? appStyle((r.applications || [])[0] || "x") : kind === "application" ? appStyle(r.id) : { icon: ENTITY[kind].icon, c: "" };
    const hay = [title, sub, r.short_name, ...(r.aliases || []), kind === "training" ? haystack.get(r.id) : ""].filter(Boolean).join(" ").toLowerCase();
    return { kind, id: r.id, title, sub, ic, hay, t: title.toLowerCase() };
  }));
  let palSel = 0;
  function renderPalette() {
    const q = pq.value.trim().toLowerCase();
    const terms = q.split(/\s+/).filter(Boolean);
    let items;
    if (!terms.length) {
      items = sortTrainings(C.trainings.filter((t) => t.state === "upcoming" || t.state === "in-progress"), "soonest").slice(0, 5)
        .map((t) => palIndex.find((p) => p.kind === "training" && p.id === t.id));
      items = [...items, ...palIndex.filter((p) => p.kind === "application")];
    } else {
      items = palIndex.filter((p) => terms.every((term) => p.hay.includes(term)))
        .map((p) => ({ ...p, score: (p.t.startsWith(q) ? 3 : 0) + (p.t.includes(q) ? 2 : 0) + (terms.every((term) => p.t.includes(term)) ? 1 : 0) }))
        .sort((a, b) => b.score - a.score);
    }
    const groups = PAL_KINDS.map(([kind, label]) => [label, items.filter((p) => p.kind === kind).slice(0, terms.length ? 6 : 8)]).filter(([, l]) => l.length);
    let i = 0;
    presults.innerHTML = groups.length ? groups.map(([label, l]) => `<li class="grp">${!terms.length && label === "Trainings" ? "Coming up" : label}</li>` + l.map((p) =>
      `<li><a href="${href(p.kind, p.id)}" role="option" data-i="${i++}"${p.ic.c ? ` style="--c:${p.ic.c}"` : ""}><span class="pi">${icon(p.ic.icon)}</span>
        <span class="pt"><b>${esc(p.title)}</b>${p.sub ? `<span>${esc(p.sub)}</span>` : ""}</span></a></li>`).join("")).join("")
      : `<li class="none">No matches for “${esc(pq.value)}”.</li>`;
    palSel = 0;
    highlight();
  }
  function highlight() {
    presults.querySelectorAll("a[data-i]").forEach((a) => {
      const on = +a.dataset.i === palSel;
      a.setAttribute("aria-selected", String(on));
      if (on) a.scrollIntoView({ block: "nearest" });
    });
  }
  function openPalette() {
    lastFocus = document.activeElement;
    palette.hidden = false; document.body.style.overflow = "hidden";
    pq.value = ""; renderPalette(); pq.focus();
  }
  function closePalette() {
    if (palette.hidden) return;
    palette.hidden = true; document.body.style.overflow = "";
    if (lastFocus && lastFocus.isConnected) lastFocus.focus();
  }
  pq.addEventListener("input", renderPalette);
  pq.addEventListener("keydown", (e) => {
    const n = presults.querySelectorAll("a[data-i]").length;
    if (e.key === "ArrowDown") { e.preventDefault(); palSel = Math.min(n - 1, palSel + 1); highlight(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); palSel = Math.max(0, palSel - 1); highlight(); }
    else if (e.key === "Enter") { const a = presults.querySelector(`a[data-i="${palSel}"]`); if (a) { e.preventDefault(); location.hash = a.getAttribute("href"); closePalette(); } }
  });
  palette.addEventListener("click", (e) => { if (e.target.closest("[data-close]") || e.target.closest("#palette-results a")) closePalette(); });
  document.getElementById("open-palette").addEventListener("click", openPalette);
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); palette.hidden ? openPalette() : closePalette(); }
    else if (e.key === "/" && palette.hidden && player.hidden && !/input|textarea|select/i.test(document.activeElement.tagName)) { e.preventDefault(); openPalette(); }
    else if (e.key === "Escape") { closePalette(); closePlayer(); }
  });

  // ================= theme =================
  const themeBtn = document.getElementById("theme-toggle");
  const isLight = () => document.documentElement.dataset.theme === "light";
  const paintTheme = () => { themeBtn.innerHTML = icon(isLight() ? "moon" : "sun"); themeBtn.setAttribute("aria-label", isLight() ? "Switch to dark theme" : "Switch to light theme"); };
  themeBtn.addEventListener("click", () => {
    document.documentElement.dataset.theme = isLight() ? "dark" : "light";
    try { localStorage.setItem("arset-theme", document.documentElement.dataset.theme); } catch (e) { /* storage unavailable */ }
    paintTheme();
  });
  paintTheme();

  // ================= shell =================
  const NAV = [["home", "Home", "#/"], ["trainings", "Trainings"], ["satellites", "Satellites"],
    ["datasets", "Datasets"], ["tools", "Tools"], ["applications", "Applications"], ["review", "Review"]];
  function renderNav(active) {
    const d = drafts();
    const pending = d.trainings.length + d.instructors.length + d.videos.length;
    document.getElementById("nav").innerHTML = NAV.map(([key, label, url]) =>
      `<a href="${url || `#/${key}`}"${key === active ? ' class="active" aria-current="page"' : ""}>${label}${key === "review" && pending ? `<span class="count">${pending}</span>` : ""}</a>`).join("");
  }
  document.getElementById("footer").innerHTML = `<div class="wrap">
    <span><b>EO Training Atlas</b> is an independent, non-commercial project. It is not affiliated with or endorsed by NASA or the ARSET program.
      Trainings, recordings and materials belong to their authors and are linked from
      <a href="https://www.earthdata.nasa.gov/data/projects/arset" target="_blank" rel="noopener">NASA Earthdata</a> and YouTube, not hosted here.</span>
    <span>Index built ${esc(fmtDate(C.generated))} · ${plural(C.trainings.length, "training")} · ${plural(allVideos.length, "recording")}</span></div>`;

  function router() {
    const raw = location.hash.replace(/^#\/?/, "");
    const [path, qs = ""] = raw.split("?");
    const [kind, ...rest] = path.split("/");
    const id = decodeURIComponent(rest.join("/"));
    let active = kind;
    closePlayer(); closePalette();
    if (!kind) { active = "home"; renderHome(); }
    else if (kind === "trainings") renderTrainings(Object.fromEntries(new URLSearchParams(qs)));
    else if (kind === "training") { active = "trainings"; renderTraining(id); }
    else if (kind === "review") renderReview();
    else if (ENTITY[kind]) { active = kind === "instructor" ? "trainings" : KINDS[kind]; renderEntity(kind, id); }
    else {
      const single = Object.keys(KINDS).find((k) => KINDS[k] === kind);
      if (single && ENTITY[single]) renderEntityList(single); else notFound();
    }
    renderNav(active);
    window.scrollTo(0, 0);
  }
  window.addEventListener("hashchange", router);
  router();
})();
