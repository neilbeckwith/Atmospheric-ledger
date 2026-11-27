# Atmospheric Ledger — CO₂ in the air, and the warming it drives

A static web app: atmospheric CO₂ from Mauna Loa and the global network,
1959–2025, and the global temperature anomaly it drives — explained by the
carbon budget, the greenhouse effect and radiative forcing, and observed
through the 16 GCOS atmospheric Essential Climate Variables.

## What it shows

- **The active ledger (live counter)** — tonnes of CO₂ added to the air
  since the page opened, and a live running cumulative total since 1959.
  This spreads the latest observed annual growth (2025: +2.84 ppm
  globally, 22.12 GtCO₂/yr, about 702 tonnes a second) evenly across the
  year; it is an estimate, not a measurement.
- **Historic trend** — Mauna Loa CO₂ and the GISTEMP temperature anomaly
  on one chart, 1959–2025: CO₂ from 315.98 ppm to 427.35 ppm, temperature
  from near the 1951–1980 average to +1.19 °C. Record growth year 2024
  (+3.53 ppm at Mauna Loa); warmest year 2024 (+1.28 °C).
- **The processes** — the science behind the numbers: emissions (11.79
  GtC in 2024), the airborne fraction (42.3% mean since 1959, 67.2% in
  2024), the greenhouse effect (CO₂ forcing +2.16 W/m² since 1750,
  doubling +3.93 W/m²), the land and ocean sinks (1.94 and 3.39 GtC in
  2024), methane (1,935.95 ppb in 2025, +0.54 W/m²), aerosols (about
  −1.1 W/m², masking a third of the greenhouse warming), and the budget
  identity that has to close.
- **The forcing ledger** — effective radiative forcing 1750–2019 by agent
  (IPCC AR6): CO₂ +2.16, CH₄ +0.54, N₂O +0.21, halogens +0.41, ozone
  +0.47, aerosols −1.06, total anthropogenic +2.72 W/m².
- **Every year** — annual means 1959–2025: global and Mauna Loa CO₂,
  both growth rates, temperature anomaly and airborne fraction, sortable,
  with CSV download.
- **Compare decades** — three pickers, side by side. Growth averaged
  0.86 ppm/yr in the 1960s, 1.64 in the 1980s, 2.40 in the 2010s and 2.58
  in 2015–2024; temperature 0.03 °C below baseline in the 1960s, 0.98 °C
  above in 2015–2024.
- **Accumulated carbon** — 237.7 GtC added to the air 1959–2025 (111.9
  ppm), 43.1% of the 537.3 GtC humans emitted 1959–2024; the ocean took
  27.2% and the land 22.0%. Since pre-industrial times CO₂ is up 147.6
  ppm (+53.1%) and CH₄ up 1,214 ppb.
- **GCOS atmospheric Essential Climate Variables** — all 16 ECVs by GCOS
  group (Surface, Upper-air, Atmospheric Composition), with each
  variable's role in the ledger. Groups follow the live GCOS list
  (accessed 2026-11-27): Clouds sits under Atmospheric Composition and
  Lightning under Upper-air.
- **CSV downloads** — annual series and decade table.

## Data

- CO₂: NOAA Global Monitoring Laboratory annual means — global
  425.63 ppm in 2025 (+2.84 ppm vs 2024), Mauna Loa 427.35 ppm (+2.74).
  Global series starts 1979; Mauna Loa starts 1959 (monthly from 1958).
  Latest monthly reading: October 2026 trend, 429.98 ppm.
- CH₄: NOAA GML global annual mean, 1,935.95 ppb in 2025 (+6.48 ppb),
  up from 722 ppb pre-industrial. Series starts 1984.
- Temperature: NASA GISTEMP v4 annual (J-D) anomaly vs 1951–1980,
  +1.19 °C in 2025; +1.41 °C warmer than the 1880–1899 mean. Warmest year
  2024 (+1.28 °C); 2025 is the second-warmest.
- Budget: Global Carbon Budget 2025 — 2024 emissions 11.79 GtC,
  atmospheric growth 7.92 GtC, land sink 1.94 GtC, ocean sink 3.39 GtC,
  airborne fraction 67.2% in 2024 (record), 42.3% mean 1959–2024. The
  budget series ends in 2024; 2025 budget quantities do not exist yet.
- Forcing: IPCC AR6 WG1, Chapter 7 (effective radiative forcing
  1750–2019, central estimates).
- Variables: GCOS ECV list (gcos.wmo.int), atmospheric domain, accessed
  2026-11-27.

No values on this page are read from a chart. Every figure is computed
from a downloaded data file by `scripts/fetch_data.py`, or is a cited
paper value.

`data.json` is built by `scripts/fetch_data.py` from the NOAA GML trend
files, the NASA GISTEMP table and the Global Carbon Budget 2025
spreadsheet. Re-run it to refresh the data when a new Global Carbon
Budget is published or the annual means are updated. Note: the ICOS
download endpoint stalls in this sandbox (connection hangs before any
bytes arrive), so the GCB spreadsheet in this folder is the identical
file (same SHA-256) already fetched from that URL by the sibling
Terrestrial-ledger build; the script reuses it when present and only
attempts the download when it is missing. Sources are credited in the
captions on the page and in the Methods section.

## Run locally

```bash
cd atmospheric-ledger
python3 -m http.server 8000
# open http://127.0.0.1:8000/
```

No build step, no dependencies. `index.html` + `styles.css` + `app.js` + `data.json`.

## Deploy

- **GitHub Pages:** publish this folder as-is to a new public repo
  (`Atmospheric-ledger`) with Pages enabled. A workflow like the
  carbon-ledge one (`.github/workflows/deploy-pages.yml`) can publish it
  on push.
- **Any static host** (Vercel, Netlify, etc.): publish this folder as-is.

This repo is not created yet — build locally, present to Neil, push only
after he approves that specific push.
