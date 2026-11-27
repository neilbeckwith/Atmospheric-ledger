/* Atmospheric Ledger — CO2 in the air, and the warming it drives.
   Data: data.json, built by scripts/fetch_data.py from NOAA GML (Mauna
   Loa and global CO2, global CH4), NASA GISTEMP v4 (global temperature
   anomaly) and the Global Carbon Budget 2025 (airborne fraction, sinks).
   Units: CO2 in ppm, CH4 in ppb, temperature anomaly in degC vs 1951-1980,
   carbon budget in GtC/yr (1 ppm CO2 = 2.124 GtC = 7.79 GtCO2).
   Live counter: spreads the latest observed annual CO2 growth (2025:
   +2.84 ppm globally) evenly across the year. It is an estimate, not a
   measurement. */
let DATA = null;
let selectedDecade = null;

const $ = (id) => document.getElementById(id);
const fmt = (n, d = 0) => n == null || isNaN(n) ? "—" : Number(n).toLocaleString("en-CA", { maximumFractionDigits: d, minimumFractionDigits: d });
const pct = (n) => n == null || isNaN(n) ? "—" : (n > 0 ? "+" : "") + n.toFixed(1) + "%";
const sgn = (n, d = 2) => n == null || isNaN(n) ? "—" : (n > 0 ? "+" : "") + n.toFixed(d);

function drawChart() {
  const svg = $("worldChart");
  const W = 900, H = 320, PL = 56, PR = 56, PT = 18, PB = 34;
  const annual = DATA.annual;
  const minY = annual[0].year, maxY = annual[annual.length - 1].year;
  const cMin = 300, cMax = 440;      // CO2, ppm (left axis)
  const tMin = -0.4, tMax = 1.4;     // temp anomaly, degC (right axis)
  const x = (y) => PL + (y - minY) / (maxY - minY) * (W - PL - PR);
  const yC = (v) => PT + (1 - (v - cMin) / (cMax - cMin)) * (H - PT - PB);
  const yT = (v) => PT + (1 - (v - tMin) / (tMax - tMin)) * (H - PT - PB);
  let s = "";
  for (let v = 300; v <= 440; v += 20) {
    s += `<line x1="${PL}" y1="${yC(v)}" x2="${W - PR}" y2="${yC(v)}" stroke="#e3e8eb"/><text x="${PL - 8}" y="${yC(v) + 4}" text-anchor="end" font-size="11" fill="#5a6b78">${v}</text>`;
  }
  for (const tv of [-0.2, 0.2, 0.6, 1.0, 1.4]) {
    s += `<text x="${W - PR + 8}" y="${yT(tv) + 4}" font-size="11" fill="#b35c1e">${tv > 0 ? "+" : ""}${tv.toFixed(1)}</text>`;
  }
  for (const yr of [1960, 1975, 1990, 2005, 2025]) {
    s += `<text x="${x(yr)}" y="${H - 10}" text-anchor="middle" font-size="11" fill="#5a6b78">${yr}</text>`;
  }
  s += `<text x="${PL}" y="${PT - 4}" font-size="11" fill="#5a6b78">CO₂, ppm</text>`;
  s += `<text x="${W - PR}" y="${PT - 4}" text-anchor="end" font-size="11" fill="#b35c1e">°C vs 1951–1980</text>`;
  s += `<path d="${annual.map((w, i) => (i ? "L" : "M") + x(w.year).toFixed(1) + "," + yT(w.temp_anom_c).toFixed(1)).join(" ")}" fill="none" stroke="#b35c1e" stroke-width="2"/>`;
  s += `<path d="${annual.map((w, i) => (i ? "L" : "M") + x(w.year).toFixed(1) + "," + yC(w.co2_mlo_ppm).toFixed(1)).join(" ")}" fill="none" stroke="#1f5f8b" stroke-width="2.5"/>`;
  svg.innerHTML = s;
  const v = (yr, k) => (annual.find((w) => w.year === yr) || {})[k];
  const ssum = DATA.summary;
  const growths = annual.filter((w) => w.co2_growth_mlo_ppm != null);
  const recordGrowth = growths.reduce((a, b) => b.co2_growth_mlo_ppm > a.co2_growth_mlo_ppm ? b : a);
  $("worldStats").innerHTML =
    `<span>1959: ${fmt(v(1959, "co2_mlo_ppm"), 2)} ppm</span><span>1979: first global mean ${fmt(v(1979, "co2_gl_ppm"), 2)} ppm</span>` +
    `<span>2000: ${fmt(v(2000, "co2_mlo_ppm"), 2)} ppm</span><span>2025: ${fmt(v(2025, "co2_mlo_ppm"), 2)} ppm (+${fmt(v(2025, "co2_growth_mlo_ppm"), 2)} ppm/yr)</span>` +
    `<span>Record growth: ${recordGrowth.year} (+${fmt(recordGrowth.co2_growth_mlo_ppm, 2)} ppm)</span>` +
    `<span>Warmest year: ${ssum.warmest_year} (+${fmt(ssum.warmest_year_anom_c, 2)} °C)</span>` +
    `<span>2025: +${fmt(v(2025, "temp_anom_c"), 2)} °C (${sgn(ssum.latest_temp_anom_c - ssum.prev_temp_anom_c)} °C vs 2024)</span>` +
    `<span>Warming since 1880–1899: +${fmt(ssum.warming_since_1880_1899_c, 2)} °C</span>`;
}

function renderProcesses() {
  $("pumpGrid").innerHTML = DATA.processes.map((p) => {
    const wide = p.abbr === "BALANCE" ? " wide" : "";
    return `<div class="pump${wide}"><div class="abbr">${p.abbr}</div><h3>${p.name}</h3><p>${p.role}</p><p class="caption">Source: ${p.source}</p></div>`;
  }).join("");
}

function renderForcing() {
  $("forcingBody").innerHTML = DATA.forcing.map((f) => {
    const cls = f.erf > 0 ? "neg" : "pos";
    const total = f.agent.startsWith("Total");
    return `<tr><td>${total ? "<strong>" + f.agent + "</strong>" : f.agent}</td><td class="${cls}">${sgn(f.erf)}</td><td>${f.sign}</td></tr>`;
  }).join("");
}

function renderTable() {
  const sort = $("sort").value;
  let rows = DATA.annual.slice();
  const numDesc = (k) => (a, b) => (b[k] == null ? -1 : a[k] == null ? 1 : b[k] - a[k]);
  if (sort === "yearAsc") rows.sort((a, b) => a.year - b.year);
  else if (sort === "growth") rows.sort(numDesc("co2_growth_gl_ppm"));
  else if (sort === "temp") rows.sort(numDesc("temp_anom_c"));
  else if (sort === "af") rows.sort(numDesc("airborne_fraction_pct"));
  else rows.sort((a, b) => b.year - a.year);
  $("tbody").innerHTML = rows.map((w) =>
    `<tr><td>${w.year}</td><td>${fmt(w.co2_gl_ppm, 2)}</td><td>${fmt(w.co2_mlo_ppm, 2)}</td>` +
    `<td>${fmt(w.co2_growth_gl_ppm, 2)}</td><td>${fmt(w.co2_growth_mlo_ppm, 2)}</td>` +
    `<td>${w.temp_anom_c == null ? "—" : sgn(w.temp_anom_c)}</td><td>${fmt(w.airborne_fraction_pct, 1)}</td></tr>`
  ).join("");
}

function renderDecadeTable() {
  $("decadeBody").innerHTML = DATA.decades.map((d) =>
    `<tr data-decade="${d.label}"><td>${d.label}</td><td>${fmt(d.mean_co2_mlo_ppm, 2)}</td>` +
    `<td>${fmt(d.mean_growth_mlo_ppm_yr, 2)}</td><td>${sgn(d.mean_temp_anom_c)}</td>` +
    `<td>${fmt(d.mean_airborne_fraction_pct, 1)}</td></tr>`
  ).join("");
  document.querySelectorAll("#decadeBody tr").forEach((tr) =>
    tr.addEventListener("click", () => selectDecade(tr.dataset.decade)));
}

function processLong(abbr) {
  const p = DATA.processes.find((x) => x.abbr === abbr);
  return p ? `${p.abbr} — ${p.name}` : abbr;
}

function selectDecade(label) {
  selectedDecade = label;
  const d = DATA.decades.find((x) => x.label === label);
  if (!d) return;
  const ecvTags = (d.ecvs || []).map((e) => `<span class="eov-tag">${e}</span>`).join("");
  const procs = (d.processes || []).map(processLong).join("; ");
  const afNote = d.airborne_fraction_years && d.airborne_fraction_years !== d.years
    ? ` The airborne fraction mean covers ${d.airborne_fraction_years} only — the budget series ends in 2024.`
    : "";
  const glNote = d.mean_growth_gl_ppm_yr == null
    ? " The global-mean CO₂ series starts in 1979, so no global growth mean exists for this decade — Mauna Loa growth is shown instead."
    : "";
  $("detail").innerHTML =
    `<h3>${d.label} (${d.years})</h3>` +
    `<p>Mean CO₂ (Mauna Loa) <strong>${fmt(d.mean_co2_mlo_ppm, 2)} ppm</strong>, growing ` +
    `<strong>${fmt(d.mean_growth_mlo_ppm_yr, 2)} ppm/yr</strong>` +
    (d.mean_growth_gl_ppm_yr != null ? ` (${fmt(d.mean_growth_gl_ppm_yr, 2)} ppm/yr globally)` : "") +
    `, mean temperature anomaly <strong>${sgn(d.mean_temp_anom_c)} °C</strong> vs 1951–1980, ` +
    `mean airborne fraction <strong>${fmt(d.mean_airborne_fraction_pct, 1)}%</strong>.</p>` +
    `<p class="caption">${afNote}${glNote}</p>` +
    `<h3>Why CO₂ grew as fast as it did</h3><p>${d.drivers}</p>` +
    `<p class="caption">Drivers source: ${d.driver_source}</p>` +
    `<h3>Processes behind it</h3><p>${procs}</p>` +
    `<p class="caption">Process framing: the seven atmospheric processes above. No published source splits a decade's growth into process shares; the attribution above is qualitative.</p>` +
    `<h3>GCOS variables that watch this decade</h3><p>${ecvTags}</p>` +
    `<p class="caption">ECV names and groups: GCOS Essential Climate Variables, atmospheric domain.</p>` +
    `<h3>The four numbers (${d.years} mean)</h3>` +
    `<div class="table-wrap"><table><thead><tr><th>Mean CO₂, Mauna Loa (ppm)</th><th>Mean growth, Mauna Loa (ppm/yr)</th><th>Mean temp anomaly (°C)</th><th>Mean airborne fraction (%)</th></tr></thead><tbody><tr><td>${fmt(d.mean_co2_mlo_ppm, 2)}</td><td>${fmt(d.mean_growth_mlo_ppm_yr, 2)}</td><td>${sgn(d.mean_temp_anom_c)}</td><td>${fmt(d.mean_airborne_fraction_pct, 1)}</td></tr></tbody></table></div>` +
    `<p class="caption">Temperature anomalies are vs the 1951–1980 baseline. The airborne fraction is the share of total human emissions that stayed in the atmosphere.</p>`;
  $("detail").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderCompare() {
  const labels = DATA.decades.map((d) => d.label);
  for (const id of ["cmp1", "cmp2", "cmp3"]) {
    const sel = $(id);
    sel.innerHTML = `<option value="">—</option>` + labels.map((n) => `<option value="${n}">${n}</option>`).join("");
  }
  $("cmp1").value = "2015–2024";
  $("cmp2").value = "2000s";
  $("cmp3").value = "1980s";
  const draw = () => {
    const picks = ["cmp1", "cmp2", "cmp3"].map((id) => $(id).value).filter(Boolean);
    $("compareGrid").innerHTML = picks.map((label) => {
      const d = DATA.decades.find((x) => x.label === label);
      return `<div class="compare-card"><h3>${d.label}</h3>` +
        `<div class="kv"><span>Mean CO₂, Mauna Loa</span><span>${fmt(d.mean_co2_mlo_ppm, 2)} ppm</span></div>` +
        `<div class="kv"><span>Mean growth, Mauna Loa</span><span>${fmt(d.mean_growth_mlo_ppm_yr, 2)} ppm/yr</span></div>` +
        `<div class="kv"><span>Mean growth, global</span><span>${fmt(d.mean_growth_gl_ppm_yr, 2)} ppm/yr</span></div>` +
        `<div class="kv"><span>Mean temp anomaly</span><span>${sgn(d.mean_temp_anom_c)} °C</span></div>` +
        `<div class="kv"><span>Mean airborne fraction</span><span>${fmt(d.mean_airborne_fraction_pct, 1)}%</span></div>` +
        `<div class="kv"><span>Dominant processes</span><span>${(d.processes || []).join(" + ")}</span></div>` +
        `<p class="sub" style="margin-top:10px">${d.drivers}</p>` +
        `<p class="caption">Drivers: ${d.driver_source}</p></div>`;
    }).join("");
  };
  for (const id of ["cmp1", "cmp2", "cmp3"]) $(id).addEventListener("change", draw);
  draw();
}

function renderECV() {
  const order = ["Surface", "Upper-air", "Atmospheric composition"];
  const rows = [];
  for (const grp of order) {
    DATA.ecvs.filter((e) => e.group === grp).forEach((e) => {
      rows.push(`<tr><td>${e.name}</td><td>${e.group}</td><td>${e.role}</td></tr>`);
    });
  }
  $("eovBody").innerHTML = rows.join("");
}

function downloadCSV(filename, text) {
  const blob = new Blob([text], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function startCounter() {
  // 2025 global growth rate, spread evenly. 2025 is not a leap year;
  // the counter applies the annual rate over the current year (2026, 365 days).
  const ratePerSec = DATA.summary.counter_rate_tco2_per_sec; // t CO2/s
  const cumulativeEnd2025GtC = DATA.summary.cumulative_atm_growth_1959_2025_gtc;
  const start2026 = Date.UTC(2026, 0, 1);
  const openedAt = Date.now();
  $("rateLine").textContent = `${fmt(ratePerSec, 0)} tonnes of CO₂ per second (2025 global growth rate, spread evenly)`;
  function tick() {
    const now = Date.now();
    const sinceOpenedT = ratePerSec * (now - openedAt) / 1000;
    $("sinceOpened").textContent = `${fmt(sinceOpenedT, 1)} t`;
    const elapsed2026Sec = Math.max(0, (now - start2026) / 1000);
    const cumGtC = cumulativeEnd2025GtC + (ratePerSec / 3.664) * elapsed2026Sec / 1e9;
    $("cumulativeLive").textContent = `${fmt(cumGtC, 2)} GtC`;
    $("cumulativeSub").textContent = `237.7 GtC at end-2025 + ${fmt((ratePerSec / 3.664) * elapsed2026Sec / 1e9, 2)} GtC estimated in 2026 to date (2025 growth is the observed NOAA value; the budget series ends in 2024 — see Methods)`;
  }
  tick();
  setInterval(tick, 250);
}

async function init() {
  const res = await fetch("data.json");
  DATA = await res.json();
  const s = DATA.summary;
  $("latestYear").textContent = s.latest_year;
  $("co2Global").textContent = `${fmt(s.latest_co2_gl_ppm, 2)} ppm`;
  $("co2GlobalYoY").textContent = `+${fmt(s.growth_gl_ppm, 2)} ppm vs ${s.latest_year - 1} · Mauna Loa ${fmt(s.latest_co2_mlo_ppm, 2)} ppm`;
  $("tempAnom").textContent = `${sgn(s.latest_temp_anom_c)} °C`;
  $("tempSub").textContent = `vs 1951–1980 · +${fmt(s.warming_since_1880_1899_c, 2)} °C since 1880–1899 · warmest year ${s.warmest_year} (+${fmt(s.warmest_year_anom_c, 2)} °C)`;
  $("airborne").textContent = `${fmt(s.airborne_fraction_latest_pct, 1)}%`;
  $("airborneSub").textContent = `of ${s.airborne_fraction_latest_year} emissions stayed in the air — the record growth year · long-term mean ${fmt(s.airborne_fraction_mean_1959_2024_pct, 1)}%`;
  const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const lm = s.latest_monthly_mlo;
  $("monthlyMlo").textContent = `${fmt(lm.trend_ppm, 2)} ppm`;
  $("monthlySub").textContent = `Mauna Loa, ${months[lm.month - 1]} ${lm.year}, trend (seasonally adjusted)`;
  drawChart();
  renderProcesses();
  renderForcing();
  renderTable();
  renderDecadeTable();
  renderCompare();
  renderECV();
  startCounter();
  $("sort").addEventListener("change", renderTable);
  $("pickDecade").addEventListener("click", () => selectDecade("2015–2024"));
  $("csvAnnual").addEventListener("click", () => {
    const head = "Year,Global CO2 (ppm),Mauna Loa CO2 (ppm),Growth global (ppm/yr),Growth Mauna Loa (ppm/yr),Temp anomaly (C vs 1951-1980),Airborne fraction (%),Atmospheric growth (GtC/yr),Fossil emissions (GtC/yr),Land-use emissions (GtC/yr),Ocean sink (GtC/yr),Land sink (GtC/yr)\n";
    const body = DATA.annual.map((w) => {
      const v = (x) => x == null ? "" : x;
      return `${w.year},${v(w.co2_gl_ppm)},${v(w.co2_mlo_ppm)},${v(w.co2_growth_gl_ppm)},${v(w.co2_growth_mlo_ppm)},${v(w.temp_anom_c)},${v(w.airborne_fraction_pct)},${v(w.gatm_gtc)},${v(w.efos_gtc)},${v(w.eluc_gtc)},${v(w.socean_gtc)},${v(w.sland_gtc)}`;
    }).join("\n");
    downloadCSV("atmospheric-ledger-annual-series.csv", head + body + "\n");
  });
  $("csvDecades").addEventListener("click", () => {
    const head = "Decade,Mean CO2 Mauna Loa (ppm),Mean growth Mauna Loa (ppm/yr),Mean growth global (ppm/yr),Mean temp anomaly (C vs 1951-1980),Mean airborne fraction (%),Airborne fraction years\n";
    const body = DATA.decades.map((d) => {
      const v = (x) => x == null ? "" : x;
      return `"${d.label}",${d.mean_co2_mlo_ppm},${d.mean_growth_mlo_ppm_yr},${v(d.mean_growth_gl_ppm_yr)},${d.mean_temp_anom_c},${v(d.mean_airborne_fraction_pct)},"${d.airborne_fraction_years || ""}"`;
    }).join("\n");
    downloadCSV("atmospheric-ledger-decades.csv", head + body + "\n");
  });
}
init().catch((e) => { document.querySelector("main").insertAdjacentHTML("afterbegin", `<p class="note">Could not load data.json — ${e.message}. Serve this folder over HTTP (not file://) or check the data file.</p>`); });
