"use strict";
/* Clip-OS — de werkomgeving in je browser. Geen externe bibliotheken; alles draait lokaal. */

const SLEUTEL = document.querySelector('meta[name="clipos-sleutel"]').content;
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function opslag(k, v) {
  try {
    if (v === undefined) return localStorage.getItem("clipos-" + k);
    localStorage.setItem("clipos-" + k, v);
  } catch (e) { return null; }
  return null;
}

const S = {
  staat: null, briefs: [], config: null, kw: null, les: "",
  taal: opslag("taal") || "alle", trends: null, trendTaal: opslag("trendtaal") || "beide", bewerk: null, open: new Set(), concept: {}, vuil: false,
  laatsteHtml: "", offline: false, vorigeTaken: {},
};

const api = {
  async get(pad) {
    const r = await fetch(pad, { cache: "no-store" });
    if (!r.ok) throw new Error("Server antwoordt niet");
    return r.json();
  },
  async post(pad, body = {}) {
    const r = await fetch(pad, {
      method: "POST", headers: { "Content-Type": "application/json", "X-ClipOS-Sleutel": SLEUTEL }, body: JSON.stringify(body),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.fout || "Er ging iets mis");
    return d;
  },
};

/* ---------- iconen ---------- */
const ICONEN = {
  home: "M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  idee: "M9 18h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.7.5 1.1 1.3 1.1 2.2v.5h5V16c0-.9.4-1.7 1.1-2.2A6 6 0 0 0 12 3z",
  studio: "M4 6h16v12H4zM4 10h16M8 6l-2 4M13 6l-2 4M18 6l-2 4",
  send: "M21 3 10 14M21 3l-6.5 18-4.5-7-7-4.5z",
  chart: "M4 20V11M10 20V5M16 20v-6M3 20h18",
  flag: "M5 21V4M5 4h12l-2.5 4.5L17 13H5",
  bot: "M12 3v3M6 7h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2zM9.5 12h.01M14.5 12h.01M9 16h6",
  boek: "M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 19V5M8 7h7",
  gear: "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M14 4v4M8 10v4M16 16v4",
  shield: "M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6zM9 12l2 2 4-4",
  download: "M12 4v11M7 10l5 5 5-5M5 20h14",
  copy: "M9 9h10v10H9zM5 15V5h10",
  check: "M5 12.5l4.5 4.5L19 7",
  x: "M6 6l12 12M18 6 6 18",
  play: "M8 5v14l11-7z",
  refresh: "M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6",
  stop: "M7 7h10v10H7z",
  maan: "M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z",
  zon: "M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  pin: "M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21zM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
  plus: "M12 5v14M5 12h14",
  sparkle: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z",
  vuur: "M12 3c.5 3 4.5 5 4.5 10a4.5 4.5 0 0 1-9 0c0-2.2 1-3.8 2.3-5 .2 1.8 1 2.8 2.2 3.2C11.6 8.6 11 6 12 3z",
  extern: "M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
};
const icoon = (n, extra = "") => `<svg class="i ${extra}" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONEN[n]}"/></svg>`;

/* ---------- hulpjes ---------- */
const VLAG = { en: "🇬🇧", nl: "🇳🇱" };
const vlag = t => VLAG[t] || "🌐";
const taalNaam = t => (S.staat?.talen || {})[t] || (t ? t.toUpperCase() : "Onbekend");
const taalBadge = t => `<span class="badge ${t === "en" || t === "nl" ? t : ""}">${esc(taalNaam(t))}</span>`;
const inTaal = v => S.taal === "alle" || (v.taal || "?") === S.taal;
const zichtbaar = () => (S.staat?.voorstellen || []).filter(inTaal);
const aantal = st => zichtbaar().filter(v => st.includes(v.status)).length;
const getal = n => Number(n || 0).toLocaleString("nl-NL");
const cv = (k, d = "") => (k in S.concept ? S.concept[k] : d);
function talen() {
  const set = new Set(Object.keys(S.staat?.talen || {}));
  (S.staat?.voorstellen || []).forEach(v => v.taal && set.add(v.taal));
  return [...set];
}
function relTijd(iso) {
  if (!iso) return "";
  const d = new Date(iso), s = (Date.now() - d) / 1000;
  if (s < 60) return "zojuist";
  if (s < 3600) return `${Math.floor(s / 60)} min geleden`;
  if (s < 86400) return `${Math.floor(s / 3600)} uur geleden`;
  if (s < 172800) return "gisteren";
  return d.toLocaleDateString("nl-NL", { day: "numeric", month: "short" });
}
const ytTitel = t => (/#shorts/i.test(t) || t.length > 90 ? t : `${t} #Shorts`);
const beschrijving = v => ((v.beschrijving || "").trim() + ((v.hashtags || []).length ? "\n\n" + v.hashtags.join(" ") : "")).trim();
const leeg = (emoji, titel, tekst, knop = "") => `<div class="leeg"><div class="groot-icoon">${emoji}</div><b>${esc(titel)}</b>${esc(tekst)}${knop ? `<div style="margin-top:14px">${knop}</div>` : ""}</div>`;

function toast(tekst, soort = "ok") {
  const el = document.createElement("div");
  el.className = `toast ${soort}`;
  el.textContent = tekst;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

/* ---------- pagina's ---------- */
const PAGINAS = [
  { id: "vandaag", naam: "Vandaag", icoon: "home", sub: "Overzicht van je clipfabriek" },
  { id: "trends", naam: "Trends", icoon: "vuur", sub: "Marktonderzoek: wat is nu trending en wat kun je clippen" },
  { id: "ideeen", naam: "Ideeën", icoon: "idee", sub: "Claude's voorstellen: geef akkoord of wijs af", teller: () => aantal(["idee"]), heet: true },
  { id: "studio", naam: "Studio", icoon: "studio", sub: "Video's die nu gemaakt worden", teller: () => aantal(["akkoord", "bezig", "fout"]) },
  { id: "plaatsen", naam: "Plaatsen", icoon: "send", sub: "Klaar om te plaatsen op YouTube en je clipplatform", teller: () => aantal(["klaar"]), heet: true },
  { id: "resultaten", naam: "Resultaten", icoon: "chart", sub: "Views per video en per taal" },
  { kop: "Systeem" },
  { id: "campagnes", naam: "Campagnes", icoon: "flag", sub: "Bronnen en eisen per campagne" },
  { id: "claude", naam: "Claude", icoon: "bot", sub: "Je agents aan het werk: gratis via je Pro-account", teller: () => (S.staat?.taken || []).filter(t => ["wacht", "bezig"].includes(t.status)).length },
  { id: "lessen", naam: "Lessenboek", icoon: "boek", sub: "Wat Claude heeft geleerd van je resultaten" },
  { id: "instellingen", naam: "Instellingen", icoon: "gear", sub: "Talen, accounts, thema en de kostenwacht" },
];
const huidig = () => {
  const id = (location.hash.match(/^#\/([a-z]+)/) || [])[1];
  return PAGINAS.some(p => p.id === id) ? id : "vandaag";
};

function renderZijbalk() {
  const p = huidig();
  const kwOk = S.staat?.kostenwacht_ok !== false;
  $("#zijbalk").innerHTML = `
    <div class="merk"><div class="merk-logo"><svg viewBox="0 0 24 24"><path d="M7 4.5v15l12-7.5z"/></svg></div>
      <div><b>Clip-OS</b><small>jouw clipfabriek</small></div></div>
    ${PAGINAS.map(x => x.kop ? `<div class="nav-kop">${x.kop}</div>` : (() => {
      const n = x.teller ? x.teller() : 0;
      return `<a class="nav ${x.id === p ? "aan" : ""}" href="#/${x.id}">${icoon(x.icoon)}<span class="naam">${x.naam}</span>${n ? `<span class="teller ${x.heet ? "heet" : ""}">${n}</span>` : ""}</a>`;
    })()).join("")}
    <div class="zijbalk-voet">
      <a class="chip-status ${kwOk ? "ok" : "fout"}" href="#/instellingen">${icoon("shield")}
        <div><b>${kwOk ? "Kostenwacht actief" : "Kostenstop!"}</b>${kwOk ? "€0 · alleen je Pro-abonnement" : "Bekijk Instellingen"}</div></a>
    </div>`;
}

function renderTopbalk() {
  const p = PAGINAS.find(x => x.id === huidig());
  const taken = S.staat?.taken || [];
  const bezig = taken.find(t => t.status === "bezig");
  const wacht = taken.filter(t => t.status === "wacht").length;
  const claudePil = S.offline
    ? `<span class="pil"><span class="stip fout"></span>Verbinding kwijt: draait start.bat nog?</span>`
    : bezig ? `<a class="pil" href="#/claude"><span class="stip bezig"></span>Claude werkt: ${esc(bezig.titel)}${wacht ? ` (+${wacht})` : ""}</a>`
    : `<a class="pil" href="#/claude"><span class="stip ok"></span>Claude staat klaar</a>`;
  const thema = opslag("thema") || "auto";
  $("#topbalk").innerHTML = `
    <div><h1>${esc(p.naam)}</h1><div class="sub">${esc(p.sub)}</div></div>
    <div class="rechts">
      <div class="segment" role="group" aria-label="Taal">
        <button class="${S.taal === "alle" ? "aan" : ""}" data-actie="taal" data-taal="alle">Alle</button>
        ${talen().map(t => `<button class="${S.taal === t ? "aan" : ""}" data-actie="taal" data-taal="${esc(t)}">${vlag(t)} ${esc(t.toUpperCase())}</button>`).join("")}
      </div>
      ${claudePil}
      <button class="knop zacht icoon" data-actie="thema-wissel" title="Thema: ${thema}" aria-label="Thema wisselen">${icoon(thema === "licht" ? "zon" : "maan")}</button>
    </div>`;
}

function kpi(label, ic, statussen, naar, accent = false) {
  const n = aantal(statussen);
  const verdeling = S.taal === "alle" ? talen().map(t => `${vlag(t)} ${(S.staat.voorstellen || []).filter(v => (v.taal || "?") === t && statussen.includes(v.status)).length}`).join(" · ") : taalNaam(S.taal);
  return `<a class="tegel ${accent && n ? "accent" : ""}" href="#/${naar}"><div class="label">${icoon(ic)}${label}</div><div class="getal">${getal(n)}</div><div class="verdeling">${verdeling}</div></a>`;
}

function briefOpties(gekozen = "") {
  const actief = S.briefs.filter(b => !b.voorbeeld);
  return `<option value="">Zonder campagne (taal automatisch)</option>` +
    actief.map(b => `<option value="${esc(b.bestand)}" ${b.bestand === gekozen ? "selected" : ""}>${vlag(b.taal)} ${esc(b.naam)}</option>`).join("");
}

function nieuweVideoKaart() {
  return `<div class="kaart stapel">
    <div><h3>Nieuwe video laten uitwerken</h3>
    <p class="zacht klein">Plak een link. Claude downloadt en transcribeert de video en bedenkt de sterkste clips. Die verschijnen daarna bij Ideeën.</p></div>
    <input class="invoer" id="nv-link" data-concept="nv-link" placeholder="https://www.youtube.com/watch?v=…" value="${esc(cv("nv-link"))}">
    <div class="rij"><select class="invoer" id="nv-brief" data-concept="nv-brief" style="flex:1;min-width:180px">${briefOpties(cv("nv-brief"))}</select>
    <button class="knop primair" data-actie="claude-video">${icoon("sparkle")}Laat Claude beginnen</button></div>
  </div>`;
}

function paginaVandaag() {
  const uur = new Date().getHours();
  const groet = uur < 12 ? "Goedemorgen" : uur < 18 ? "Goedemiddag" : "Goedenavond";
  const datum = new Date().toLocaleDateString("nl-NL", { weekday: "long", day: "numeric", month: "long" });
  const m = (S.staat.meldingen || [])[0];
  const views = zichtbaar().filter(v => v.status === "geplaatst").reduce((a, v) => a + (v.views || 0), 0);
  const laatsteRun = (S.staat.taken || []).find(t => t.soort === "dagelijks");

  const events = [];
  zichtbaar().forEach(v => (v.historie || []).forEach(([tijd, st]) => {
    const t = { idee: "💡 Nieuw idee", akkoord: "👍 Akkoord", klaar: "✅ Video klaar", geplaatst: "📤 Geplaatst", afgewezen: "🗑️ Afgewezen", fout: "⚠️ Fout bij maken" }[st];
    if (t) events.push({ tijd, tekst: `${t}: ${v.titel || v.hook}`, taal: v.taal });
  }));
  (S.staat.taken || []).forEach(t => t.klaar && events.push({ tijd: t.klaar, tekst: `🤖 ${t.titel}: ${({ klaar: "klaar", fout: "mislukt", gestopt: "gestopt" })[t.status] || t.status}` }));
  events.sort((a, b) => (b.tijd > a.tijd ? 1 : -1));

  return `
  <section class="hero">
    <div class="flauw klein">${esc(datum.charAt(0).toUpperCase() + datum.slice(1))}</div>
    <h2>${groet}! 👋</h2>
    <div class="zacht">${aantal(["idee"]) ? `Er wachten <b>${aantal(["idee"])}</b> ideeën op je akkoord` : "Geen ideeën die op je wachten"}${aantal(["klaar"]) ? ` en <b>${aantal(["klaar"])}</b> video's staan klaar om te plaatsen.` : "."}</div>
    ${m ? `<div class="bericht"><div class="avatar">C</div><div><div class="wie">Claude · ${esc(relTijd(m.tijd))}</div><div class="tekst">${esc(m.tekst)}</div></div></div>`
        : `<div class="bericht"><div class="avatar">C</div><div><div class="wie">Claude</div><div class="tekst">Nog geen bericht. Plak hieronder een link of start de dagelijkse run, dan ga ik aan de slag.</div></div></div>`}
  </section>
  <div class="raster-4">
    ${kpi("Ideeën wachten", "idee", ["idee"], "ideeen", true)}
    ${kpi("In de studio", "studio", ["akkoord", "bezig"], "studio")}
    ${kpi("Klaar om te plaatsen", "send", ["klaar"], "plaatsen", true)}
    <a class="tegel" href="#/resultaten"><div class="label">${icoon("chart")}Views (geplaatst)</div><div class="getal">${getal(views)}</div><div class="verdeling">${aantal(["geplaatst"])} video's geplaatst</div></a>
  </div>
  <div class="raster-2" style="margin-top:16px">
    <div class="stapel">
      ${nieuweVideoKaart()}
      <div class="kaart rij tussen">
        <div><h3>Weet je niet wat je moet plaatsen?</h3><div class="zacht klein">Laat Claude marktonderzoek doen naar wat nu trending is.</div></div>
        <a class="knop zacht" href="#/trends">${icoon("vuur")}Naar Trends</a>
      </div>
      <div class="kaart rij tussen">
        <div><h3>Dagelijkse run</h3><div class="zacht klein">Nieuwe video's van je campagnes zoeken en ideeën bedenken.
          ${laatsteRun ? `Laatste: ${esc(relTijd(laatsteRun.klaar || laatsteRun.gemaakt))} (${esc(laatsteRun.status)}).` : "Nog niet gedraaid."}</div></div>
        <button class="knop zacht" data-actie="claude-dagelijks">${icoon("play")}Nu starten</button>
      </div>
    </div>
    <div class="kaart"><h3>Activiteit</h3>
      ${events.length ? `<div class="feed">${events.slice(0, 9).map(e => `<div><span>${esc(e.tekst)}</span><time>${esc(relTijd(e.tijd))}</time></div>`).join("")}</div>`
        : `<p class="zacht klein">Hier verschijnt alles wat er gebeurt.</p>`}
    </div>
  </div>`;
}

function paginaIdeeen() {
  const lijst = zichtbaar().filter(v => v.status === "idee").sort((a, b) => (b.score || 0) - (a.score || 0));
  const afgewezen = zichtbaar().filter(v => v.status === "afgewezen");
  const kaarten = lijst.map(v => {
    const score = Number(v.score) || 0;
    return `<article class="kaart idee" data-kaart="${esc(v.id)}">
      <div class="idee-kop">
        <div class="bron">${esc(v.bron_titel)}${v.bron_kanaal ? ` · ${esc(v.bron_kanaal)}` : ""}</div>
        ${taalBadge(v.taal)}<span class="badge">${esc(v.duur)} sec</span>
        ${score ? `<div class="score" style="--p:${score * 10}" title="Score van Claude"><span>${score}</span></div>` : ""}
      </div>
      <label class="veld">Hook · eerste 3 seconden in beeld
        <textarea class="invoer groot" rows="2" data-veld="hook" data-concept="hook-${esc(v.id)}">${esc(cv("hook-" + v.id, v.hook))}</textarea></label>
      <label class="veld">Titel
        <input class="invoer" data-veld="titel" data-concept="titel-${esc(v.id)}" value="${esc(cv("titel-" + v.id, v.titel))}"></label>
      ${v.citaat ? `<blockquote class="citaat">“${esc(v.citaat)}”</blockquote>` : ""}
      ${v.reden ? `<div class="waarom">💡 <span>${esc(v.reden)}</span></div>` : ""}
      <div class="acties">
        <button class="knop primair breed" data-actie="akkoord" data-id="${esc(v.id)}">${icoon("check")}Akkoord, maak video</button>
        <button class="knop gevaar" data-actie="afwijzen" data-id="${esc(v.id)}" title="Afwijzen" aria-label="Afwijzen">${icoon("x")}</button>
      </div>
    </article>`;
  }).join("");
  return `
    ${lijst.length ? `<div class="raster">${kaarten}</div>`
      : leeg("💡", "Geen nieuwe ideeën", "Laat Claude een video uitwerken of start de dagelijkse run.", `<a class="knop primair" href="#/vandaag">${icoon("sparkle")}Nieuwe video</a>`)}
    ${afgewezen.length ? `<div class="sectie"><h2>Afgewezen</h2><span>${afgewezen.length} · Claude leert hiervan</span></div>
      <div class="kaart"><div class="feed">${afgewezen.slice(-15).reverse().map(v => `<div><span>${taalBadge(v.taal)} ${esc(v.hook)}</span>
        <button class="knop zacht klein" data-actie="terug" data-id="${esc(v.id)}" style="margin-left:auto">Terugzetten</button></div>`).join("")}</div></div>` : ""}`;
}

const ytId = url => (String(url).match(/(?:v=|youtu\.be\/)([\w-]{6,})/) || [])[1];

function paginaTrends() {
  const r = S.trends;
  const taak = (S.staat.taken || []).find(t => t.soort === "trends" && ["wacht", "bezig"].includes(t.status));
  const zoeker = `<div class="kaart stapel">
    <div><h3>Marktonderzoek laten doen</h3>
    <p class="zacht klein">Claude zoekt op internet wat er deze week speelt rond geld, business en AI. Clip-OS zoekt daarna op YouTube de podcasts en interviews met de snelst stijgende views. Gratis via je Pro-account; duurt een paar minuten.</p></div>
    <div class="rij">
      <div class="segment" role="group" aria-label="Taal">${[["beide", "🌍 Beide"], ["en", "🇬🇧 Engels"], ["nl", "🇳🇱 Nederlands"]].map(([k, n]) =>
        `<button class="${S.trendTaal === k ? "aan" : ""}" data-actie="trend-taal" data-taal="${k}">${n}</button>`).join("")}</div>
      <input class="invoer" id="tr-onderwerp" data-concept="tr-onderwerp" style="flex:1;min-width:200px" placeholder="Onderwerp (optioneel), bijv. AI, vastgoed, beleggen" value="${esc(cv("tr-onderwerp"))}">
      <button class="knop primair" data-actie="claude-trends" ${taak ? "disabled" : ""}>${icoon("vuur")}${taak ? "Onderzoek loopt…" : "Zoek wat trending is"}</button>
    </div>
    ${taak ? `<div class="rij flauw klein"><div class="draaier"></div>Claude is bezig met het onderzoek. Volg het live bij <a href="#/claude">Claude</a>.</div>` : ""}
  </div>`;
  if (!r) return zoeker + leeg("🔥", "Nog geen marktonderzoek", "Klik hierboven op ‘Zoek wat trending is’. Het resultaat verschijnt hier.");
  const videos = (r.videos || []).filter(v => S.taal === "alle" || !v.taal || v.taal === S.taal);
  const kaart = v => {
    const id = ytId(v.url), mag = v.toestemming === "campagne";
    return `<article class="kaart trend">
      <a class="duim" href="${esc(v.url)}" target="_blank" rel="noopener">${id ? `<img src="https://i.ytimg.com/vi/${esc(id)}/mqdefault.jpg" alt="" loading="lazy">` : ""}<span class="badge">${esc(v.duur_min)} min</span></a>
      <div class="stapel" style="gap:9px">
        <div class="rij" style="gap:8px">${v.taal ? taalBadge(v.taal) : ""}
          ${mag ? `<span class="badge ok">${icoon("check")}Campagne: ${esc(v.campagne)}</span>` : `<span class="badge warn">Toestemming onbekend</span>`}
          ${v.onderwerp ? `<span class="badge">${esc(v.onderwerp)}</span>` : ""}</div>
        <div><b>${esc(v.titel)}</b><div class="flauw klein">${esc(v.kanaal)}${v.geupload ? ` · ${esc(v.geupload)}` : ""}</div></div>
        <div class="rij klein" style="gap:14px"><span>👁 ${getal(v.views)} views</span><span style="color:var(--accent-tekst);font-weight:650">📈 ${getal(v.per_dag)} per dag</span></div>
        ${v.waarom ? `<div class="waarom">💡 <span>${esc(v.waarom)}</span></div>` : ""}
        <div class="acties">
          ${mag ? `<button class="knop primair" data-actie="trend-uitwerken" data-url="${esc(v.url)}" data-brief="${esc(v.campagne)}">${icoon("sparkle")}Maak ideeën</button>`
                : `<button class="knop zacht" data-actie="trend-uitwerken" data-url="${esc(v.url)}" data-brief="">Ik heb toestemming, uitwerken</button>`}
          <a class="knop zacht" href="${esc(v.url)}" target="_blank" rel="noopener">${icoon("extern")}Bekijk op YouTube</a>
        </div>
        ${mag ? "" : `<div class="tip">Alleen uitwerken en plaatsen als deze maker clippen toestaat, bijvoorbeeld via een campagne op Whop, Vyro of ClipArmy.</div>`}
      </div>
    </article>`;
  };
  return `${zoeker}
    <div class="sectie"><h2>Laatste onderzoek</h2><span>${esc(relTijd(r.gemaakt))}${r.taal ? ` · ${esc(r.taal)}` : ""}</span></div>
    ${r.samenvatting ? `<div class="bericht" style="margin:0 0 14px"><div class="avatar">C</div><div><div class="wie">Claude · marktonderzoek</div><div class="tekst">${esc(r.samenvatting)}</div></div></div>` : ""}
    ${(r.onderwerpen || []).length ? `<div class="rij" style="gap:8px;margin-bottom:16px">${r.onderwerpen.map(o => `<span class="badge accent" title="${esc(o.waarom)}">🔥 ${esc(o.onderwerp)}</span>`).join("")}</div>` : ""}
    ${videos.length ? `<div class="stapel">${videos.map(kaart).join("")}</div>` : leeg("🔎", "Geen video's in deze taal", "Kies bovenin een andere taal of doe een nieuw onderzoek.")}`;
}

function paginaStudio() {
  const bezig = zichtbaar().filter(v => ["akkoord", "bezig"].includes(v.status));
  const fout = zichtbaar().filter(v => v.status === "fout");
  const kaart = v => `<article class="kaart stapel">
      <div class="rij tussen">${taalBadge(v.taal)}<span class="badge ${v.status === "bezig" ? "accent" : ""}">${v.status === "bezig" ? "Wordt gemaakt" : "In de wachtrij"}</span></div>
      <div><b>${esc(v.titel)}</b><div class="zacht klein">${esc(v.hook)}</div></div>
      ${v.status === "bezig" ? `<div class="voortgang"><i></i></div><div class="flauw klein">Knippen · 9:16 · gezicht volgen · ondertitels · geluid</div>` : `<div class="rij flauw klein"><div class="draaier"></div>Wacht op de editor…</div>`}
    </article>`;
  return `
    ${bezig.length ? `<div class="raster">${bezig.map(kaart).join("")}</div>`
      : leeg("🎬", "De studio is leeg", "Geef akkoord op een idee en de video wordt hier automatisch gemaakt, zonder Claude-gebruik.", `<a class="knop zacht" href="#/ideeen">Naar ideeën</a>`)}
    ${fout.length ? `<div class="sectie"><h2>Mislukt</h2><span>${fout.length}</span></div><div class="raster">${fout.map(v => `
      <article class="kaart stapel"><div class="rij tussen">${taalBadge(v.taal)}<span class="badge fout">Fout</span></div>
      <b>${esc(v.titel)}</b><div class="foutblok">${esc(v.fout)}</div>
      <div class="acties"><button class="knop zacht" data-actie="opnieuw" data-id="${esc(v.id)}">${icoon("refresh")}Opnieuw proberen</button></div></article>`).join("")}</div>` : ""}`;
}

function paginaPlaatsen() {
  const lijst = zichtbaar().filter(v => v.status === "klaar");
  if (!lijst.length) return leeg("📤", "Niets om te plaatsen", "Zodra een video klaar is, staat hij hier met titel, beschrijving en checklist.");
  const accounts = S.staat.accounts || {};
  return `<div class="stapel">${lijst.map(v => {
    const id = esc(v.id);
    const fouten = (v.controle || []).filter(c => !c[0]);
    return `<article class="kaart plaats" data-kaart="${id}">
      <div class="video-9x16"><video controls preload="metadata" src="/video/${encodeURIComponent(v.id)}"></video></div>
      <div class="stapel">
        <div class="rij">${taalBadge(v.taal)}<span class="badge">${esc(v.duur)} sec</span>
          ${v.controle_ok ? `<span class="badge ok">${icoon("check")}Controles OK</span>` : `<span class="badge fout">${fouten.length} controle(s) mislukt</span>`}
          <span class="flauw klein" style="margin-left:auto">${esc(v.bron_titel)}</span></div>
        <div class="doel">${icoon("pin")}Plaats op: ${esc(accounts[v.taal] || "je YouTube-kanaal")}</div>
        ${fouten.length ? `<div class="controles">${fouten.map(c => `<div class="nee">✗ ${esc(c[1])}</div>`).join("")}</div>` : ""}
        ${v.notitie ? `<div class="waarom">📝 <span>${esc(v.notitie)}</span></div>` : ""}
        <label class="veld">YouTube-titel<div class="kopieerveld"><input class="invoer" readonly id="t-${id}" value="${esc(ytTitel(v.titel))}">
          <button class="knop zacht" data-actie="kopieer" data-doel="t-${id}">${icoon("copy")}Kopieer</button></div></label>
        <label class="veld">Beschrijving + hashtags<div class="kopieerveld"><textarea class="invoer" readonly id="b-${id}">${esc(beschrijving(v))}</textarea>
          <button class="knop zacht" data-actie="kopieer" data-doel="b-${id}">${icoon("copy")}Kopieer</button></div></label>
        <ul class="checklist">
          <li><input type="checkbox" data-bewaar="c1-${id}" ${opslag("c1-" + v.id) ? "checked" : ""}><span>Upload als Short (YouTube-app of Studio → Maken → Short)</span></li>
          <li><input type="checkbox" data-bewaar="c2-${id}" ${opslag("c2-" + v.id) ? "checked" : ""}><span>Synthetische content: <b>Nee</b> (echte beelden, alleen ondertitels toegevoegd)</span></li>
          <li><input type="checkbox" data-bewaar="c3-${id}" ${opslag("c3-" + v.id) ? "checked" : ""}><span>Link indienen bij de campagne (als die er is)</span></li>
        </ul>
        <div class="rij"><input class="invoer" style="flex:1;min-width:200px" data-concept="link-${id}" id="l-${id}" placeholder="Link na plaatsen (optioneel)" value="${esc(cv("link-" + v.id))}">
          <button class="knop ok" data-actie="geplaatst" data-id="${id}">${icoon("check")}Geplaatst</button></div>
        <div class="rij"><a class="knop zacht klein" href="/video/${encodeURIComponent(v.id)}?download=1">${icoon("download")}Download mp4</a>
          <button class="knop zacht klein" data-actie="opnieuw" data-id="${id}">${icoon("refresh")}Opnieuw maken</button>
          <span class="flauw klein">${esc(v.map)}</span></div>
      </div>
    </article>`;
  }).join("")}</div>`;
}

function grafiek(lijst) {
  const top = [...lijst].filter(v => v.views).sort((a, b) => b.views - a.views).slice(0, 10);
  if (!top.length) return `<p class="zacht klein">Vul de views in (hieronder), dan verschijnt hier je top 10.</p>`;
  const max = Math.max(...top.map(v => v.views)), rij = 34, breedte = 1000, labelB = 330, balkB = breedte - labelB - 100;
  const kort = t => (t.length > 40 ? t.slice(0, 39) + "…" : t);
  return `<svg class="grafiek" viewBox="0 0 ${breedte} ${top.length * rij}" role="img" aria-label="Top video's op views">
    ${top.map((v, i) => {
      const w = Math.max(3, (v.views / max) * balkB), y = i * rij;
      return `<text x="0" y="${y + 21}">${esc(vlag(v.taal))} ${esc(kort(v.titel || v.hook))}</text>
        <rect class="balk ${v.taal === "en" || v.taal === "nl" ? v.taal : ""}" x="${labelB}" y="${y + 7}" width="${w}" height="20" rx="5"></rect>
        <text class="waarde" x="${labelB + w + 8}" y="${y + 21}">${getal(v.views)}</text>`;
    }).join("")}</svg>`;
}

function paginaResultaten() {
  const lijst = zichtbaar().filter(v => v.status === "geplaatst");
  if (!lijst.length) return leeg("📈", "Nog niets geplaatst", "Klik bij Plaatsen op ‘Geplaatst’ en vul na 1 tot 3 dagen de views in. Claude leert daarvan.");
  const totaal = lijst.reduce((a, v) => a + (v.views || 0), 0), metViews = lijst.filter(v => v.views);
  const perTaal = talen().map(t => {
    const l = (S.staat.voorstellen || []).filter(v => v.status === "geplaatst" && (v.taal || "?") === t);
    const views = l.reduce((a, v) => a + (v.views || 0), 0);
    return `<div class="tegel"><div class="label">${esc(taalNaam(t))}</div><div class="getal">${getal(views)}</div><div class="verdeling">${l.length} video's · gem. ${getal(l.filter(v => v.views).length ? Math.round(views / l.filter(v => v.views).length) : 0)}</div></div>`;
  }).join("");
  const rijen = [...lijst].sort((a, b) => ((b.geplaatst_op || "") > (a.geplaatst_op || "") ? 1 : -1)).map(v => `<tr data-kaart="${esc(v.id)}">
      <td>${v.link ? `<a href="${esc(v.link)}" target="_blank" rel="noopener">${esc(v.titel)}</a>` : esc(v.titel)}<div class="flauw klein">${esc(v.hook)}</div></td>
      <td>${taalBadge(v.taal)}</td><td class="flauw">${esc(relTijd(v.geplaatst_op))}</td>
      <td><div class="views-invoer"><input class="invoer" inputmode="numeric" id="v-${esc(v.id)}" data-concept="views-${esc(v.id)}" value="${esc(cv("views-" + v.id, v.views ?? ""))}" placeholder="views">
        <button class="knop zacht klein" data-actie="views" data-id="${esc(v.id)}">Opslaan</button></div></td></tr>`).join("");
  return `
    <div class="raster-4">
      <div class="tegel accent"><div class="label">${icoon("chart")}Totaal views</div><div class="getal">${getal(totaal)}</div><div class="verdeling">${lijst.length} geplaatst · ${metViews.length} met views</div></div>
      ${S.taal === "alle" ? perTaal : ""}
    </div>
    <div class="sectie"><h2>Top 10</h2><span>op views</span></div>
    <div class="kaart">${grafiek(lijst)}</div>
    <div class="sectie"><h2>Alle geplaatste video's</h2><span>vul views in na 1-3 dagen</span></div>
    <div class="kaart tabel-wrap"><table class="tabel"><thead><tr><th>Video</th><th>Taal</th><th>Geplaatst</th><th class="num">Views</th></tr></thead><tbody>${rijen}</tbody></table></div>`;
}

function paginaCampagnes() {
  if (S.bewerk) return campagneEditor();
  const echte = S.briefs.filter(b => !b.voorbeeld), voorbeelden = S.briefs.filter(b => b.voorbeeld);
  const kaart = b => `<article class="kaart stapel">
      <div class="rij tussen"><div class="rij" style="gap:8px">${taalBadge(b.taal)}${b.platform ? `<span class="badge">${esc(b.platform)}</span>` : ""}
        ${b.voorbeeld ? `<span class="badge warn">voorbeeld</span>` : ""}</div>
        ${b.voorbeeld ? "" : `<label class="schakelaar" title="Actief in de dagelijkse run"><input type="checkbox" data-actie-wijzig="brief-actief" data-bestand="${esc(b.bestand)}" ${b.actief !== false ? "checked" : ""}><span></span></label>`}</div>
      <div><h3>${esc(b.naam)}</h3><div class="zacht klein">${esc(b.cpm || "Geen tarief opgegeven")} · ${esc(b.min_seconden ?? 15)}–${esc(b.max_seconden ?? 60)} sec</div></div>
      <div class="flauw klein">${(b.bron_kanalen || []).length} kanaal/kanalen · ${(b.bron_links || []).length} losse link(s)${(b.verplichte_hashtags || []).length ? ` · ${esc(b.verplichte_hashtags.join(" "))}` : ""}</div>
      ${(b.geblokkeerde_bronnen || []).length ? `<div class="waarschuwing">⚠️ Niet toegestaan door de kostenwacht: ${esc(b.geblokkeerde_bronnen.join(", "))}. Voeg de site toe aan toegestane_sites.txt als het een gratis videosite is.</div>` : ""}
      <div class="acties"><button class="knop zacht klein" data-actie="bewerk" data-bestand="${esc(b.bestand)}">Bewerken</button>
        ${!b.voorbeeld && (b.bron_links || [])[0] ? `<button class="knop zacht klein" data-actie="claude-video-brief" data-bestand="${esc(b.bestand)}">${icoon("sparkle")}Nu uitwerken</button>` : ""}</div>
    </article>`;
  return `
    <div class="kaart stapel">
      <div><h3>Nieuwe campagne</h3><p class="zacht klein">Plak de campagnetekst van ClipArmy, Klippie, Whop of Vyro. Claude haalt er de taal, lengte, hashtags en bronnen uit. Of vul het zelf in.</p></div>
      <textarea class="invoer" id="nc-tekst" data-concept="nc-tekst" placeholder="Plak hier de campagnetekst…">${esc(cv("nc-tekst"))}</textarea>
      <div class="rij"><button class="knop primair" data-actie="claude-campagne">${icoon("sparkle")}Laat Claude invullen</button>
        <button class="knop zacht" data-actie="bewerk" data-bestand="__nieuw__">${icoon("plus")}Zelf invullen</button></div>
    </div>
    <div class="sectie"><h2>Jouw campagnes</h2><span>${echte.length} · de schakelaar bepaalt of de dagelijkse run ze meeneemt</span></div>
    ${echte.length ? `<div class="raster">${echte.map(kaart).join("")}</div>` : leeg("🎯", "Nog geen campagnes", "Voeg er hierboven een toe. Engels en Nederlands kunnen naast elkaar.")}
    ${voorbeelden.length ? `<div class="sectie"><h2>Voorbeelden</h2><span>worden nooit automatisch gebruikt</span></div><div class="raster">${voorbeelden.map(kaart).join("")}</div>` : ""}`;
}

function campagneEditor() {
  const nieuw = S.bewerk === "__nieuw__";
  const b = nieuw ? { naam: "", taal: "en", platform: "", cpm: "", min_seconden: 20, max_seconden: 60, actief: true } : S.briefs.find(x => x.bestand === S.bewerk) || {};
  const lijst = k => esc((b[k] || []).join("\n"));
  const taalOpties = [...new Set([...Object.keys(S.staat.talen || {}), "en", "nl", b.taal].filter(Boolean))];
  return `<div class="kaart" data-formulier>
    <div class="rij tussen" style="margin-bottom:14px"><h3>${nieuw ? "Nieuwe campagne" : `Campagne bewerken: ${esc(b.naam)}`}</h3>
      <button class="knop zacht klein" data-actie="annuleer">${icoon("x")}Annuleren</button></div>
    <div class="formulier">
      <label class="veld">Naam<input class="invoer" id="f-naam" value="${esc(b.naam)}" placeholder="Bijv. Diary of a CEO (Vyro)"></label>
      ${nieuw ? `<label class="veld">Bestandsnaam<input class="invoer" id="f-bestand" placeholder="bijv. doac-vyro (kleine letters, streepjes)"></label>` : `<label class="veld">Bestand<input class="invoer" value="briefs/${esc(b.bestand)}.json" disabled></label>`}
      <label class="veld">Taal<select class="invoer" id="f-taal">${taalOpties.map(t => `<option value="${esc(t)}" ${t === b.taal ? "selected" : ""}>${esc(taalNaam(t))}</option>`).join("")}</select></label>
      <label class="veld">Platform<input class="invoer" id="f-platform" value="${esc(b.platform)}" placeholder="ClipArmy, Vyro, Whop… (leeg = alleen je eigen kanaal)"></label>
      <label class="veld">Tarief<input class="invoer" id="f-cpm" value="${esc(b.cpm)}" placeholder="$3 per 1.000 views"></label>
      <div class="rij" style="gap:10px"><label class="veld" style="flex:1">Min. seconden<input class="invoer" type="number" id="f-min" value="${esc(b.min_seconden ?? 15)}"></label>
        <label class="veld" style="flex:1">Max. seconden<input class="invoer" type="number" id="f-max" value="${esc(b.max_seconden ?? 60)}"></label></div>
      <label class="veld breed">Bronkanalen (één per regel): de dagelijkse run haalt hier nieuwe video's<textarea class="invoer" id="f-kanalen" placeholder="https://www.youtube.com/@kanaal">${lijst("bron_kanalen")}</textarea></label>
      <label class="veld breed">Losse video-links (één per regel)<textarea class="invoer" id="f-links">${lijst("bron_links")}</textarea></label>
      <label class="veld">Verplichte hashtags (komma of regel)<textarea class="invoer" id="f-hashtags">${lijst("verplichte_hashtags")}</textarea></label>
      <label class="veld">Verplichte tekst in beschrijving<textarea class="invoer" id="f-tekst">${lijst("verplichte_tekst")}</textarea></label>
      <label class="veld">Verboden woorden/onderwerpen<textarea class="invoer" id="f-verboden">${lijst("verboden")}</textarea></label>
      <label class="veld">Hoe indienen<textarea class="invoer" id="f-indienen">${esc(b.indienen)}</textarea></label>
      <label class="veld breed">Notities<textarea class="invoer" id="f-notities">${esc(b.notities)}</textarea></label>
      <label class="rij breed"><span class="schakelaar"><input type="checkbox" id="f-actief" ${b.actief !== false ? "checked" : ""}><span></span></span> Actief in de dagelijkse run</label>
    </div>
    <div class="rij" style="margin-top:16px"><button class="knop primair" data-actie="brief-opslaan">${icoon("check")}Opslaan</button>
      <span class="tip">Links moeten van sites uit toegestane_sites.txt komen (kostenwacht).</span></div>
  </div>`;
}

const AGENTEN = [
  { id: "regisseur", emoji: "🎬", naam: "Regisseur", wie: "Claude", rol: "Stuurt de rest aan en schrijft je dagelijkse bericht" },
  { id: "scout", emoji: "🔭", naam: "Scout", wie: "Claude + code", rol: "Leest campagnes en vindt nieuwe video's" },
  { id: "bron", emoji: "📥", naam: "Bron", wie: "Code", rol: "Downloadt en transcribeert, lokaal en gratis" },
  { id: "trend", emoji: "🔥", naam: "Trendonderzoeker", wie: "Claude + code", rol: "Zoekt wat nu trending is en welke video's goede clips geven" },
  { id: "hookjager", emoji: "🎣", naam: "Hook-jager", wie: "Claude", rol: "Kiest de sterkste momenten, met score" },
  { id: "copywriter", emoji: "✍️", naam: "Copywriter", wie: "Claude", rol: "Titels, beschrijving en hashtags per taal" },
  { id: "editor", emoji: "✂️", naam: "Editor", wie: "Code", rol: "9:16, gezicht volgen, ondertitels, hook, geluid" },
  { id: "controleur", emoji: "🛡️", naam: "Controleur", wie: "Code + Claude", rol: "Checkt de techniek, de eisen en het beeld" },
  { id: "analist", emoji: "📊", naam: "Analist", wie: "Claude", rol: "Leert van je views en houdt het lessenboek bij" },
];

function actieveAgenten() {
  const actief = new Set();
  const taak = (S.staat.taken || []).find(t => t.status === "bezig");
  if (taak) {
    actief.add("regisseur");
    const recent = (taak.log || []).slice(-4).join("\n");
    [["clip-trendonderzoeker", "trend"], ["clip-hookjager", "hookjager"], ["clip-copywriter", "copywriter"], ["clip-controleur", "controleur"], ["clip-analist", "analist"], ["clip-scout", "scout"]]
      .forEach(([s, id]) => recent.includes(s) && actief.add(id));
    if (/clipos (dag|nieuw|transcribeer)/.test(recent)) actief.add("bron");
  }
  if ((S.staat.voorstellen || []).some(v => v.status === "bezig")) actief.add("editor");
  return actief;
}

function paginaClaude() {
  const actief = actieveAgenten();
  const taken = S.staat.taken || [];
  const geenClaude = S.kw && !S.kw.claude_gevonden;
  const statusBadge = t => ({ wacht: `<span class="badge">In de wachtrij</span>`, bezig: `<span class="badge accent"><span class="stip bezig"></span>Bezig</span>`,
    klaar: `<span class="badge ok">Klaar</span>`, fout: `<span class="badge fout">Mislukt</span>`, gestopt: `<span class="badge warn">Gestopt</span>` })[t.status] || "";
  const detail = t => t.soort === "video" ? `${esc(t.data.link)}${t.data.brief ? ` · campagne ${esc(t.data.brief)}` : ""}` : t.soort === "campagne" ? esc((t.data.tekst || "").slice(0, 120)) + "…" : "Nieuwe video's zoeken, ideeën bedenken, lessen bijwerken";
  return `
    ${geenClaude ? `<div class="waarschuwing" style="margin-bottom:14px">⚠️ Claude Code is niet gevonden op deze computer. Installeer het en log in met je Pro-account (typ <b>claude</b> en daarna <b>/login</b>). Daarna werken deze knoppen.</div>` : ""}
    <div class="sectie" style="margin-top:0"><h2>Je team</h2><span>oplichtend = nu aan het werk</span></div>
    <div class="agenten">${AGENTEN.map(a => `<div class="agent ${actief.has(a.id) ? "actief" : ""}"><div class="emoji">${a.emoji}</div>
      <div><b>${a.naam}</b><small>${esc(a.rol)}</small><small style="margin-top:3px">${a.wie === "Code" ? "⚙️ gewone code · geen Claude-gebruik" : "🧠 " + a.wie}</small></div></div>`).join("")}</div>
    <div class="sectie"><h2>Taak starten</h2><span>gratis via je Pro-account · max 80 stappen per taak</span></div>
    <div class="raster-2">${nieuweVideoKaart()}
      <div class="stapel">
        <div class="kaart rij tussen"><div><h3>Dagelijkse run</h3><div class="zacht klein">Wat 's ochtends automatisch gebeurt, nu meteen.</div></div>
          <button class="knop zacht" data-actie="claude-dagelijks">${icoon("play")}Start</button></div>
        <div class="kaart rij tussen"><div><h3>Campagne toevoegen</h3><div class="zacht klein">Plak een campagnetekst en Claude maakt de brief.</div></div>
          <a class="knop zacht" href="#/campagnes">${icoon("flag")}Naar campagnes</a></div>
      </div>
    </div>
    <div class="sectie"><h2>Taken</h2><span>live logboek</span></div>
    ${taken.length ? `<div class="stapel">${taken.map(t => {
      const toon = t.status === "bezig" || S.open.has(t.id);
      return `<article class="kaart">
        <div class="rij tussen"><div class="rij" style="gap:10px"><b>${esc(t.titel)}</b>${statusBadge(t)}<span class="flauw klein">${esc(relTijd(t.gemaakt))}</span></div>
          <div class="rij" style="gap:8px">${["wacht", "bezig"].includes(t.status) ? `<button class="knop gevaar klein" data-actie="claude-stop" data-id="${esc(t.id)}">${icoon("stop")}Stoppen</button>` : ""}
          ${t.status !== "wacht" ? `<button class="knop zacht klein" data-actie="log" data-id="${esc(t.id)}">${toon ? "Logboek verbergen" : "Logboek tonen"}</button>` : ""}</div></div>
        <div class="zacht klein" style="margin-top:4px;overflow-wrap:anywhere">${detail(t)}</div>
        ${t.fout ? `<div class="foutblok" style="margin-top:10px">${esc(t.fout)}</div>` : ""}
        ${toon ? `<pre class="log">${esc((t.log || []).join("\n") || "Nog geen uitvoer…")}</pre>` : ""}
      </article>`;
    }).join("")}</div>` : leeg("🤖", "Nog geen taken", "Start hierboven een taak. Je ziet hier live wat Claude en de agents doen.")}`;
}

function markdown(tekst) {
  const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>");
  let html = "", inLijst = false;
  for (const r of tekst.split("\n")) {
    const lijst = /^\s*[-*] /.test(r);
    if (inLijst && !lijst) { html += "</ul>"; inLijst = false; }
    if (/^# /.test(r)) html += `<h1>${inline(r.slice(2))}</h1>`;
    else if (/^##+ /.test(r)) html += `<h2>${inline(r.replace(/^##+ /, ""))}</h2>`;
    else if (lijst) { if (!inLijst) { html += "<ul>"; inLijst = true; } html += `<li>${inline(r.replace(/^\s*[-*] /, ""))}</li>`; }
    else if (r.trim()) html += `<p>${inline(r)}</p>`;
  }
  return html + (inLijst ? "</ul>" : "");
}
const paginaLessen = () => `<div class="kaart proza">${S.les ? markdown(S.les) : "<p class='zacht'>Laden…</p>"}</div>`;

function paginaInstellingen() {
  if (!S.config || !S.kw) return `<div class="laden">Laden…</div>`;
  const c = S.config, kw = S.kw, thema = opslag("thema") || "auto";
  const regel = (ok, tekst, waarsch = false) => `<div class="regel">${ok ? `<span class="badge ok">${icoon("check")}</span>` : `<span class="badge ${waarsch ? "warn" : "fout"}">!</span>`}<span>${tekst}</span></div>`;
  const handmatig = (k, tekst) => `<li><input type="checkbox" data-bewaar="${k}" ${opslag(k) ? "checked" : ""}><span>${tekst}</span></li>`;
  return `<div class="raster-2">
    <div class="kaart stapel" data-formulier>
      <h3>Talen en accounts</h3>
      <p class="zacht klein">Per taal: waar je plaatst, en hoeveel nieuwe bronvideo's de dagelijkse run maximaal pakt. Meer is meer Pro-gebruik, maar nooit geld.</p>
      <div class="tabel-wrap"><table class="tabel"><thead><tr><th>Taal</th><th>Naam</th><th>Account (waar je plaatst)</th><th class="num">Max/dag</th></tr></thead><tbody>
        ${Object.entries(c.talen || {}).map(([code, t]) => `<tr><td>${vlag(code)} <b>${esc(code)}</b></td>
          <td><input class="invoer" data-taal-veld="label" data-code="${esc(code)}" value="${esc(t.label)}"></td>
          <td><input class="invoer" data-taal-veld="account" data-code="${esc(code)}" value="${esc(t.account)}"></td>
          <td><input class="invoer" type="number" min="0" max="5" style="width:80px" data-taal-veld="max_nieuwe_bronnen_per_dag" data-code="${esc(code)}" value="${esc(t.max_nieuwe_bronnen_per_dag)}"></td></tr>`).join("")}
      </tbody></table></div>
      <div class="formulier">
        <label class="veld">Max. ideeën per bronvideo<input class="invoer" type="number" min="1" max="12" id="s-ideeen" value="${esc(c.max_ideeen_per_bron)}"></label>
        <label class="veld">Spraakmodel (sneller ↔ nauwkeuriger)<select class="invoer" id="s-model">${(c.whisper_modellen || []).map(m => `<option ${m === c.whisper_model ? "selected" : ""}>${esc(m)}</option>`).join("")}</select></label>
      </div>
      <div class="rij"><button class="knop primair" data-actie="config-opslaan">${icoon("check")}Opslaan</button><span class="tip">Tip: "medium" is nauwkeuriger voor Nederlands, maar trager.</span></div>
      <h3 style="margin-top:10px">Thema</h3>
      <div class="segment">${[["auto", "Automatisch"], ["donker", "Donker"], ["licht", "Licht"]].map(([k, n]) => `<button class="${thema === k ? "aan" : ""}" data-actie="thema" data-thema="${k}">${n}</button>`).join("")}</div>
    </div>
    <div class="kaart stapel">
      <div class="rij" style="gap:10px"><span style="color:var(--ok)">${icoon("shield")}</span><h3>Kostenwacht</h3></div>
      <p class="zacht klein">De harde stop die ervoor zorgt dat Clip-OS nooit geld kost.</p>
      ${regel(!kw.sleutels.length, kw.sleutels.length ? `Betaalde sleutels gevonden: ${esc(kw.sleutels.join(", "))}` : "Geen betaalde API-sleutels op deze computer")}
      ${regel(!kw.code.length, kw.code.length ? `Betaalde dienst in de code: ${esc(kw.code.join("; "))}` : "Code bevat geen betaalde diensten")}
      ${regel(kw.claude_gevonden, kw.claude_gevonden ? "Claude Code gevonden (draait op je Pro-login)" : "Claude Code niet gevonden: installeer het en log in met je Pro-account", true)}
      ${regel(true, "Claude-taken starten zonder betaalde sleutels en met maximaal 80 stappen")}
      <div><div class="flauw klein" style="margin:6px 0">Alleen deze sites mogen (toegestane_sites.txt):</div><div class="rij" style="gap:6px">${kw.toegestaan.map(s => `<span class="badge">${esc(s)}</span>`).join("")}</div></div>
      <div><div class="flauw klein" style="margin:6px 0">Altijd geblokkeerd:</div><div class="rij" style="gap:6px">${kw.zwarte_lijst.map(s => `<span class="badge fout">${esc(s)}</span>`).join("")}</div></div>
      <div class="waarschuwing">Twee dingen kan alleen jij instellen. Vink ze af als het klopt:</div>
      <ul class="checklist">${handmatig("hand-extra", "Op claude.ai → Instellingen → Gebruik staat <b>“Extra gebruik” UIT</b>")}${handmatig("hand-login", "Claude Code is ingelogd met mijn <b>Pro-account</b> (niet met een API-sleutel)")}</ul>
    </div>
  </div>`;
}

const RENDER = { vandaag: paginaVandaag, trends: paginaTrends, ideeen: paginaIdeeen, studio: paginaStudio, plaatsen: paginaPlaatsen, resultaten: paginaResultaten,
  campagnes: paginaCampagnes, claude: paginaClaude, lessen: paginaLessen, instellingen: paginaInstellingen };

function renderPagina(forceer = false) {
  if (!S.staat) return;
  const html = RENDER[huidig()]();
  if (!forceer && html === S.laatsteHtml) return;
  S.laatsteHtml = html;
  $("#pagina").innerHTML = html;
  document.querySelectorAll(".log").forEach(el => { el.scrollTop = el.scrollHeight; });
}

function magNietVerversen() {
  const a = document.activeElement;
  if (a && $("#pagina").contains(a) && a.matches("input, textarea, select")) return true;
  if (S.vuil || huidig() === "instellingen" || (huidig() === "campagnes" && S.bewerk)) return true;
  return [...document.querySelectorAll("#pagina video")].some(v => !v.paused);
}

/* ---------- gegevens ---------- */
async function laadBriefs() { S.briefs = await api.get("/api/briefs"); }
async function laadConfig() { S.config = await api.get("/api/config"); }
async function laadKw() { S.kw = await api.get("/api/kostenwacht"); }
async function laadTrends() { S.trends = (await api.get("/api/trends")).rapport; }
async function laadLes() { S.les = (await api.get("/api/lessenboek")).tekst; }

async function ververs() {
  try {
    S.staat = await api.get("/api/staat");
    S.offline = false;
  } catch (e) {
    S.offline = true;
    renderTopbalk();
    return;
  }
  for (const t of S.staat.taken || []) {  // na een afgeronde Claude-taak kunnen er nieuwe campagnes/lessen zijn
    const vorig = S.vorigeTaken[t.id];
    if (vorig && vorig !== t.status && t.status === "klaar") {
      toast(`🤖 ${t.titel}: klaar`);
      laadBriefs().catch(() => {});
      laadLes().catch(() => {});
      laadTrends().catch(() => {});
    }
    S.vorigeTaken[t.id] = t.status;
  }
  renderZijbalk();
  renderTopbalk();
  if (!magNietVerversen()) renderPagina();
}

async function naarPagina() {
  S.bewerk = null; S.vuil = false;
  const p = huidig();
  try {
    if (p === "instellingen") await Promise.all([laadConfig(), laadKw()]);
    if (p === "lessen") await laadLes();
    if (p === "trends") await laadTrends();
    if (p === "campagnes" || p === "vandaag" || p === "claude") await laadBriefs();
    if (p === "claude") await laadKw();
  } catch (e) { toast(e.message, "fout"); }
  renderZijbalk(); renderTopbalk(); renderPagina(true);
  window.scrollTo(0, 0);
}

/* ---------- acties ---------- */
function veld(kaartId, naam) {
  const k = document.querySelector(`[data-kaart="${CSS.escape(kaartId)}"]`);
  return k ? k.querySelector(`[data-veld="${naam}"]`)?.value ?? "" : "";
}
function vergeet(...sleutels) { sleutels.forEach(k => delete S.concept[k]); }

function thema(k) {
  opslag("thema", k);
  if (k === "auto") delete document.documentElement.dataset.thema; else document.documentElement.dataset.thema = k;
}

async function kopieer(id) {
  const el = document.getElementById(id);
  try { await navigator.clipboard.writeText(el.value); } catch (e) { el.select(); document.execCommand("copy"); }
  el.style.boxShadow = "0 0 0 3px var(--ok-zacht)"; setTimeout(() => (el.style.boxShadow = ""), 700);
  toast("Gekopieerd");
}

function briefUitFormulier() {
  const w = id => document.getElementById(id)?.value ?? "";
  return {
    naam: w("f-naam"), taal: w("f-taal"), platform: w("f-platform"), cpm: w("f-cpm"),
    min_seconden: w("f-min"), max_seconden: w("f-max"),
    bron_kanalen: w("f-kanalen"), bron_links: w("f-links"), verplichte_hashtags: w("f-hashtags"),
    verplichte_tekst: w("f-tekst"), verboden: w("f-verboden"), indienen: w("f-indienen"), notities: w("f-notities"),
    actief: document.getElementById("f-actief")?.checked ?? true,
  };
}
const slug = s => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 50);

const ACTIES = {
  async akkoord(el) {
    const id = el.dataset.id;
    await api.post(`/api/akkoord/${encodeURIComponent(id)}`, { hook: veld(id, "hook"), titel: veld(id, "titel") });
    vergeet("hook-" + id, "titel-" + id);
    toast("👍 Akkoord! De video wordt nu gemaakt. Kijk bij Studio.");
  },
  async afwijzen(el) { await api.post(`/api/afwijzen/${encodeURIComponent(el.dataset.id)}`); toast("Afgewezen. Claude leert hiervan."); },
  async terug(el) { await api.post(`/api/terug/${encodeURIComponent(el.dataset.id)}`); toast("Teruggezet bij Ideeën"); },
  async opnieuw(el) { await api.post(`/api/opnieuw/${encodeURIComponent(el.dataset.id)}`); toast("Wordt opnieuw gemaakt"); },
  async geplaatst(el) {
    const id = el.dataset.id;
    await api.post(`/api/geplaatst/${encodeURIComponent(id)}`, { link: document.getElementById("l-" + id)?.value || "" });
    vergeet("link-" + id);
    toast("📤 Top! Vul over 1-3 dagen de views in bij Resultaten.");
  },
  async views(el) {
    const id = el.dataset.id;
    await api.post(`/api/views/${encodeURIComponent(id)}`, { views: document.getElementById("v-" + id)?.value || "" });
    vergeet("views-" + id);
    toast("Views opgeslagen");
  },
  kopieer: el => kopieer(el.dataset.doel),
  async "claude-video"() {
    const link = $("#nv-link")?.value.trim(), brief = $("#nv-brief")?.value || "";
    await api.post("/api/claude/video", { link, brief });
    vergeet("nv-link");
    toast("🤖 Claude is begonnen. Volg het live bij Claude.");
  },
  async "claude-video-brief"(el) {
    const b = S.briefs.find(x => x.bestand === el.dataset.bestand);
    await api.post("/api/claude/video", { link: b.bron_links[0], brief: b.bestand });
    toast("🤖 Claude werkt de eerste link van deze campagne uit.");
  },
  async "claude-trends"() {
    await api.post("/api/claude/trends", { taal: S.trendTaal, onderwerp: $("#tr-onderwerp")?.value || "" });
    toast("🔥 Claude start het marktonderzoek. Dit duurt een paar minuten.");
  },
  "trend-taal"(el) { S.trendTaal = el.dataset.taal; opslag("trendtaal", S.trendTaal); renderPagina(true); },
  async "trend-uitwerken"(el) {
    await api.post("/api/claude/video", { link: el.dataset.url, brief: el.dataset.brief || "" });
    toast("🤖 Claude werkt deze video uit. De ideeën verschijnen bij Ideeën.");
  },
  async "claude-dagelijks"() { await api.post("/api/claude/dagelijks"); toast("🤖 Dagelijkse run gestart"); },
  async "claude-campagne"() {
    await api.post("/api/claude/campagne", { tekst: $("#nc-tekst")?.value || "" });
    vergeet("nc-tekst");
    toast("🤖 Claude maakt de campagne aan. Hij verschijnt zo in de lijst.");
  },
  async "claude-stop"(el) { await api.post(`/api/claude/stop/${el.dataset.id}`); toast("Taak gestopt"); },
  log(el) { const id = el.dataset.id; S.open.has(id) ? S.open.delete(id) : S.open.add(id); renderPagina(true); },
  taal(el) { S.taal = el.dataset.taal; opslag("taal", S.taal); renderZijbalk(); renderTopbalk(); renderPagina(true); },
  thema(el) { thema(el.dataset.thema); renderTopbalk(); renderPagina(true); },
  "thema-wissel"() {
    const donker = document.documentElement.dataset.thema === "donker" || (!document.documentElement.dataset.thema && !matchMedia("(prefers-color-scheme: light)").matches);
    thema(donker ? "licht" : "donker"); renderTopbalk(); if (huidig() === "instellingen") renderPagina(true);
  },
  bewerk(el) { S.bewerk = el.dataset.bestand; S.vuil = false; renderPagina(true); window.scrollTo(0, 0); },
  annuleer() { S.bewerk = null; S.vuil = false; renderPagina(true); },
  async "brief-opslaan"() {
    const b = briefUitFormulier();
    const bestand = S.bewerk === "__nieuw__" ? (slug(document.getElementById("f-bestand")?.value || "") || slug(b.naam)) : S.bewerk;
    if (!bestand || bestand.length < 2) throw new Error("Geef de campagne een naam");
    if (S.bewerk === "__nieuw__" && S.briefs.some(x => x.bestand === bestand)) throw new Error(`Er bestaat al een campagne '${bestand}'`);
    await api.post(`/api/briefs/${bestand}`, b);
    S.bewerk = null; S.vuil = false;
    await laadBriefs();
    toast("Campagne opgeslagen");
  },
  async "config-opslaan"() {
    const talen = JSON.parse(JSON.stringify(S.config.talen || {}));
    document.querySelectorAll("[data-taal-veld]").forEach(el => { talen[el.dataset.code][el.dataset.taalVeld] = el.value; });
    S.config = (await api.post("/api/config", {
      talen, max_ideeen_per_bron: $("#s-ideeen").value, whisper_model: $("#s-model").value,
    })).config;
    await laadConfig();
    S.vuil = false;
    toast("Instellingen opgeslagen");
  },
};

document.addEventListener("click", async e => {
  const el = e.target.closest("[data-actie]");
  if (!el) return;
  const actie = ACTIES[el.dataset.actie];
  if (!actie) return;
  e.preventDefault();
  if (el.tagName === "BUTTON") el.disabled = true;
  try {
    await actie(el);
    await ververs();
    if (["brief-opslaan", "annuleer", "bewerk", "config-opslaan"].includes(el.dataset.actie)) renderPagina(true);
  } catch (err) {
    toast(err.message, "fout");
  } finally {
    if (el.isConnected && el.tagName === "BUTTON") el.disabled = false;
  }
});

document.addEventListener("change", async e => {
  const el = e.target;
  if (el.dataset.bewaar) { opslag(el.dataset.bewaar, el.checked ? "1" : ""); return; }
  if (el.dataset.actieWijzig === "brief-actief") {
    const b = S.briefs.find(x => x.bestand === el.dataset.bestand);
    try {
      await api.post(`/api/briefs/${b.bestand}`, { ...b, actief: el.checked });
      await laadBriefs();
      toast(el.checked ? "Campagne staat aan" : "Campagne staat uit");
      renderPagina(true);
    } catch (err) { toast(err.message, "fout"); el.checked = !el.checked; }
  }
});

document.addEventListener("input", e => {
  const el = e.target;
  if (el.dataset.concept) S.concept[el.dataset.concept] = el.value;
  if (el.closest("[data-formulier]")) S.vuil = true;
});

document.addEventListener("keydown", e => {
  if (e.key === "Enter" && e.target.id === "nv-link") { e.preventDefault(); document.querySelector('[data-actie="claude-video"]')?.click(); }
});

document.addEventListener("error", e => { if (e.target.tagName === "IMG") e.target.remove(); }, true);

window.addEventListener("hashchange", naarPagina);

/* ---------- start ---------- */
(async function start() {
  const t = opslag("thema");
  if (t && t !== "auto") document.documentElement.dataset.thema = t;
  if (!location.hash) history.replaceState(null, "", "#/vandaag");
  await ververs();
  await naarPagina();
  setInterval(ververs, 3000);
})();
