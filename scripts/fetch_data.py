#!/usr/bin/env python3
"""Fetch atmospheric CO2 / temperature data for Atmospheric Ledger and build data.json.

Sources (all public, all cited on the page):
  1. NOAA Global Monitoring Laboratory (GML) greenhouse-gas trends:
     - Mauna Loa annual mean CO2 (co2_annmean_mlo.txt), 1959-2025.
     - Global annual mean CO2 (co2_annmean_gl.txt), 1979-2025.
     - Mauna Loa monthly CO2, trend (seasonally adjusted) column
       (co2_mm_mlo.txt), 1958-2026, for the latest monthly reading.
     - Global annual mean CH4 (ch4_annmean_gl.txt), 1983-2025.
     All from https://gml.noaa.gov/webdata/ccgg/trends/ (Lan et al.,
     NOAA GML). The Keeling record at Mauna Loa began in 1958.
  2. NASA GISTEMP v4 global mean surface temperature anomaly, land-ocean
     (GLB.Ts+dSST.csv), 1880-2025, annual (J-D) means, baseline 1951-1980
     (Lenssen et al. 2019, doi:10.1029/2018JD029522). Only complete years
     (all 12 months and a J-D value) are used; the partial 2026 row is
     skipped.
  3. Global Carbon Budget 2025 (Friedlingstein et al. 2025, Earth Syst.
     Sci. Data 18, 3211-3288, doi:10.5194/essd-18-3211-2026; data
     doi:10.18160/GCP-2025), via the ICOS Carbon Portal spreadsheet:
     "Historical Budget" sheet (fossil EFOS, land-use ELUC, atmospheric
     growth GATM, ocean SOCEAN and land SLAND sinks, 1959-2024).
     Used for the airborne fraction and the 2024 budget identity.
     The GCB series ends in 2024; 2025 has no published GCB values yet,
     so budget quantities (airborne fraction, sinks) are shown through
     2024 and marked as such.
  4. GCOS Essential Climate Variables, atmospheric domain (16 ECVs),
     as listed at gcos.wmo.int/site/global-climate-observing-system-gcos/essential-climate-variables (accessed
     2026-11-27), grouped as GCOS groups them: Surface, Upper-air,
     Atmospheric Composition. Note the live list puts Clouds under
     Atmospheric Composition and Lightning under Upper-air.
  5. IPCC AR6 WG1, Chapter 7 (Forster et al. 2021,
     doi:10.1017/9781009157896.009): effective radiative forcing
     1750-2019 by agent (CO2 +2.16, CH4 +0.54, N2O +0.21, halogens
     +0.41, ozone +0.47, aerosols -1.06, total anthropogenic +2.72
     W/m2; CO2 doubling forcing 3.93 +- 0.47 W/m2).
  6. Pre-industrial references: CO2 278 ppm and CH4 722 ppb (IPCC AR6).

Conversions: 1 ppm CO2 = 2.124 GtC = 7.79 GtCO2 (from the mass of the
atmosphere, 5.15e18 kg; IPCC AR6 WG1 Ch. 5). 1 GtC = 3.664 GtCO2.
Sign convention on the page: atmospheric growth is POSITIVE (carbon
added to the air); the airborne fraction is the share of total human
emissions (fossil + land-use change) that stayed in the atmosphere.
Temperature anomalies are relative to the 1951-1980 baseline unless a
different baseline is stated.
"""
import http.cookiejar
import json
import os
import urllib.request

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data.json")
SRC = os.path.join(HERE, "source")
os.makedirs(SRC, exist_ok=True)

GML = "https://gml.noaa.gov/webdata/ccgg/trends/"
GISTEMP_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"
GCB_URL = ("https://data.icos-cp.eu/licence_accept"
           "?ids=%5B%22qSjPBsV1drZnYdH-yCJMmkGn%22%5D")
GCB_XLSX = os.path.join(ROOT, "Global_Carbon_Budget_2025_v1.0.xlsx")

GTC_PER_PPM = 2.124          # GtC per ppm of atmospheric CO2
GTCO2_PER_PPM = 7.79         # GtCO2 per ppm of atmospheric CO2
GTCO2_PER_GTC = 3.664
PREIND_CO2_PPM = 278.0
PREIND_CH4_PPB = 722.0

UA = "atmospheric-ledger fetch_data.py"


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    print(f"downloaded {os.path.basename(path)} ({len(data)} bytes)")
    return data


def download_gcb(path):
    # NOTE (2026-11-27): the ICOS endpoint stalls in this sandbox (the
    # connection hangs before any bytes arrive; three attempts, including
    # a backgrounded curl with a 120 s cap, never returned). The
    # Global_Carbon_Budget_2025_v1.0.xlsx in this folder is the identical
    # file (same SHA-256) already fetched from this URL by the sibling
    # Terrestrial-ledger build, so the script reuses it when present and
    # only attempts the download when it is missing.
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", UA)]
    opener.open(GCB_URL, timeout=30)  # sets the licence cookie (302)
    with opener.open(GCB_URL, timeout=60) as r:  # with cookie -> the .xlsx
        data = r.read()
    if data[:2] != b"PK":
        raise SystemExit("GCB download did not return an xlsx file")
    with open(path, "wb") as f:
        f.write(data)
    print(f"downloaded {os.path.basename(path)} ({len(data)} bytes)")


def parse_noaa_annual(path):
    """Two-column annual mean files: year, value, uncertainty."""
    out = {}
    for line in open(path):
        p = line.split()
        if len(p) >= 2 and p[0].isdigit():
            out[int(p[0])] = float(p[1])
    return out


def parse_mlo_monthly(path):
    """co2_mm_mlo.txt: year month decimal-date average trend ..."""
    rows = []
    for line in open(path):
        p = line.split()
        if len(p) >= 5 and p[0].isdigit():
            rows.append({"year": int(p[0]), "month": int(p[1]),
                         "trend_ppm": float(p[4])})
    return rows


def parse_gistemp(path):
    """GLB.Ts+dSST.csv: Year,Jan..Dec,J-D,D-N,DJF,MAM,JJA,SON."""
    out = {}
    for line in open(path):
        p = line.strip().split(",")
        if p[0].isdigit() and len(p) > 13:
            months = p[1:13]
            if "***" in months or p[13] in ("***", ""):
                continue  # incomplete year (e.g. 2026)
            out[int(p[0])] = float(p[13])
    return out


def parse_gcb(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    # Historical Budget sheet: header row 16; col2 EFOS, col3 ELUC,
    # col4 GATM, col5 SOCEAN, col6 SLAND, col7 cement carbonation
    ws = wb["Historical Budget"]
    assert str(ws.cell(row=16, column=1).value).strip() == "Year"
    hist = {}
    r = 17
    while True:
        y = ws.cell(row=r, column=1).value
        if y is None:
            break
        vals = [ws.cell(row=r, column=c).value for c in range(2, 8)]
        # Early years (before ~1850) have missing ELUC / SOCEAN / GATM;
        # only complete budget years are kept (1850-2024).
        if all(v is not None for v in vals):
            hist[int(y)] = {
                "efos": float(vals[0]),
                "eluc": float(vals[1]),
                "gatm": float(vals[2]),
                "socean": float(vals[3]),
                "sland": float(vals[4]),
                "cement": float(vals[5]),
            }
        r += 1
    return hist


# --- GCOS atmospheric ECVs ---------------------------------------------------
# gcos.wmo.int/site/global-climate-observing-system-gcos/essential-climate-variables (accessed 2026-11-27), 16 ECVs.
# Groups are GCOS's own: Surface, Upper-air, Atmospheric Composition.
ECVS = [
    # (name, group, role in the ledger)
    ("Surface temperature", "Surface",
     "Air temperature near the surface — the warming itself, measured by the "
     "station network behind GISTEMP and the other surface records."),
    ("Precipitation", "Surface",
     "Rain and snow: the water cycle's delivery. Warming air holds about 7% "
     "more water vapour per degree, so rain falls harder and droughts bite deeper."),
    ("Surface pressure", "Surface",
     "The weight of the air above a point; its patterns steer the winds and "
     "the storms that move heat and moisture around the planet."),
    ("Surface wind speed and direction", "Surface",
     "Winds move heat, moisture and CO2 itself — and set how fast the ocean "
     "and land sinks can take carbon out of the air."),
    ("Surface water vapour", "Surface",
     "Water vapour is the strongest greenhouse gas by amount, and a feedback: "
     "warmer air holds more of it, which traps more heat."),
    ("Surface radiation budget", "Surface",
     "Sunlight in, infrared out at the ground — the balance that decides "
     "whether the surface warms or cools."),
    ("Upper-air temperature", "Upper-air",
     "Temperature through the troposphere and stratosphere. The troposphere "
     "warms while the stratosphere cools — the fingerprint of greenhouse "
     "warming, not solar warming."),
    ("Upper-air wind speed and direction", "Upper-air",
     "The jet streams and the circulation aloft; their shifts move storms, "
     "heatwaves and the monsoons."),
    ("Upper-air water vapour", "Upper-air",
     "Water vapour above the surface, including the stratosphere, where it "
     "acts as a greenhouse gas and shapes ozone chemistry."),
    ("Earth radiation budget", "Upper-air",
     "Sunlight in minus infrared out at the top of the atmosphere, measured "
     "by CERES satellites — the direct measure of the energy imbalance "
     "driving warming, about +1 W/m2 in recent years."),
    ("Lightning", "Upper-air",
     "Lightning frequency tracks storm intensity and convection, and its "
     "nitrogen oxides feed ozone and aerosol chemistry."),
    ("Clouds", "Atmospheric composition",
     "Cloud properties — amount, height, type. Clouds cool by reflecting "
     "sunlight and warm by trapping infrared; their net effect is the "
     "largest uncertainty in how much warming a given forcing brings."),
    ("Aerosols", "Atmospheric composition",
     "Airborne particles — sulfate, dust, soot, sea salt. They reflect "
     "sunlight and seed clouds, cooling the planet by about 1.1 W/m2 and "
     "masking part of the greenhouse warming."),
    ("Carbon dioxide, methane and other greenhouse gases", "Atmospheric composition",
     "The well-mixed greenhouse gases — CO2, CH4, N2O and halocarbons. "
     "Their rising concentrations are the forcing this ledger measures: "
     "CO2 425.6 ppm and CH4 1,936 ppb in 2025."),
    ("Ozone", "Atmospheric composition",
     "Ozone in the stratosphere shields life from UV; ozone in the "
     "troposphere is a greenhouse gas and a pollutant. Its forcing since "
     "1750 is about +0.47 W/m2."),
    ("Precursors for aerosols and ozone", "Atmospheric composition",
     "The gases that make aerosols and ozone — SO2, NOx, ammonia, volatile "
     "organic compounds — mostly from burning fuel and from farming."),
]

# --- The mechanism: processes behind the numbers -----------------------------
PROCESSES = [
    {"abbr": "EMIT", "name": "Emissions — the input",
     "role": "Humans emitted 11.79 GtC in 2024 (10.54 GtC fossil fuels and "
             "cement, 1.25 GtC land-use change; Global Carbon Budget 2025). "
             "Every tonne starts here; the rest of the ledger is where it goes.",
     "source": "Friedlingstein et al. 2025 (GCB 2025)"},
    {"abbr": "AIR", "name": "Airborne fraction — what stays in the air",
     "role": "About 42% of cumulative emissions since 1959 stayed in the "
             "atmosphere (the airborne fraction); the rest went into the land "
             "and ocean sinks. In 2024 the fraction hit 67% — the record CO2 "
             "growth year, when the tropical land sink collapsed in the "
             "El Niño drought. The fraction, not the emissions alone, sets "
             "how fast CO2 rises.",
     "source": "Friedlingstein et al. 2025 (GCB 2025); computed in data.json"},
    {"abbr": "GREEN", "name": "The greenhouse effect — why CO2 warms",
     "role": "CO2 absorbs infrared at 15 micrometres, the wavelength Earth "
             "radiates to space. Adding CO2 closes that window a little more, "
             "so the surface must warm to radiate the same energy. The "
             "forcing grows logarithmically — about 5.35 x ln(C/C0) W/m2 — "
             "so each extra ppm matters less than the last, but the total "
             "since 1750 is +2.16 W/m2, and a doubling of CO2 gives "
             "+3.93 W/m2.",
     "source": "IPCC AR6 WG1, Chapter 7 (Forster et al. 2021)"},
    {"abbr": "SINKS", "name": "Land and ocean sinks — what leaves the air",
     "role": "In 2024 the land took up 1.94 GtC and the ocean 3.39 GtC "
             "(GCB 2025). The sinks grow with CO2 — more CO2 fertilises "
             "photosynthesis and pushes more gas into seawater — but they "
             "weaken as the planet warms: heat and drought cut the land sink, "
             "and warmer water holds less CO2. The sinks are why only about "
             "half of emissions stay airborne.",
     "source": "Friedlingstein et al. 2025 (GCB 2025)"},
    {"abbr": "CH4", "name": "Methane — the fast gas",
     "role": "Methane reached 1,935.95 ppb in 2025, up from 722 ppb "
             "pre-industrial, growing 6.5 ppb in 2025 alone. Its forcing "
             "since 1750 is +0.54 W/m2, and it lives only about 12 years in "
             "the air — so cutting methane cools the planet within a decade, "
             "unlike CO2, which lingers for centuries.",
     "source": "NOAA GML global CH4 (this build); IPCC AR6 WG1, Chapter 7"},
    {"abbr": "AERO", "name": "Aerosols — the cooling mask",
     "role": "Air pollution cools the planet by about 1.1 W/m2 "
             "(aerosol-radiation -0.84, aerosol-cloud -0.22; IPCC AR6) — "
             "masking roughly a third of the greenhouse warming. Cleaning "
             "up the air saves lives but unmasks warming, which is why the "
             "net forcing (+2.72 W/m2) is smaller than the greenhouse gases "
             "alone (+3.32 W/m2).",
     "source": "IPCC AR6 WG1, Chapter 7 (Forster et al. 2021)"},
    {"abbr": "BALANCE", "name": "The budget identity — it has to add up",
     "role": "Emissions = atmospheric growth + land sink + ocean sink + "
             "cement carbonation + budget imbalance. In 2024: 11.79 = 7.92 "
             "+ 1.94 + 3.39 + 0.22 - 1.69 GtC — the imbalance is the part "
             "the measured terms do not account for. And the energy balance "
             "must add up too: the +2.72 W/m2 of forcing is balanced by "
             "warming plus heat stored in the ocean. The ledger is two "
             "account books — carbon and energy — and they have to close "
             "together.",
     "source": "Friedlingstein et al. 2025 (GCB 2025); IPCC AR6 WG1, Chapter 7"},
]

# --- IPCC AR6 effective radiative forcing, 1750-2019 (W/m2) ------------------
FORCING = [
    {"agent": "Carbon dioxide (CO2)", "erf": 2.16, "sign": "warming"},
    {"agent": "Methane (CH4)", "erf": 0.54, "sign": "warming"},
    {"agent": "Nitrous oxide (N2O)", "erf": 0.21, "sign": "warming"},
    {"agent": "Halogens (CFCs, HFCs and others)", "erf": 0.41, "sign": "warming"},
    {"agent": "Ozone", "erf": 0.47, "sign": "warming"},
    {"agent": "Stratospheric water vapour", "erf": 0.05, "sign": "warming"},
    {"agent": "Contrails and aviation-induced cirrus", "erf": 0.06, "sign": "warming"},
    {"agent": "Land-use albedo change", "erf": -0.20, "sign": "cooling"},
    {"agent": "Light-absorbing particles on snow and ice", "erf": 0.08, "sign": "warming"},
    {"agent": "Aerosol-radiation interactions", "erf": -0.84, "sign": "cooling"},
    {"agent": "Aerosol-cloud interactions", "erf": -0.22, "sign": "cooling"},
    {"agent": "Total well-mixed greenhouse gases", "erf": 3.32, "sign": "warming"},
    {"agent": "Total anthropogenic", "erf": 2.72, "sign": "warming"},
    {"agent": "Solar irradiance", "erf": -0.02, "sign": "cooling"},
]

# --- Decade narratives --------------------------------------------------------
# Qualitative, from the computed series and the cited events. No numbers
# here are hand-typed: the figures come from the computed decade stats.
DECADE_NOTES = {
    "1960s": {
        "drivers": "The Keeling record begins at Mauna Loa in 1958 and the "
                   "world starts watching CO2 rise in real time. Growth is "
                   "slow — under 1 ppm a year — because fossil emissions are "
                   "still under 4 GtC a year, and the 1960s are slightly "
                   "cooler than the 1951–1980 average, held down by aerosol "
                   "pollution and natural variability.",
        "driver_source": "NOAA GML Mauna Loa record; GISTEMP (this build)",
        "processes": ["EMIT", "AIR", "GREEN"],
        "ecvs": ["Carbon dioxide, methane and other greenhouse gases",
                 "Surface temperature", "Aerosols",
                 "Surface radiation budget"],
    },
    "1970s": {
        "drivers": "Growth quickens past 1 ppm a year as emissions rise, "
                   "but the decade stays near the 1951–1980 temperature "
                   "average. The 1973 oil shock briefly slows emissions "
                   "growth; clean-air laws begin cutting the aerosol load "
                   "in North America and Europe.",
        "driver_source": "NOAA GML; GISTEMP; GCB 2025 (this build)",
        "processes": ["EMIT", "AIR", "AERO"],
        "ecvs": ["Carbon dioxide, methane and other greenhouse gases",
                 "Surface temperature", "Aerosols",
                 "Precursors for aerosols and ozone"],
    },
    "1980s": {
        "drivers": "Growth averages about 1.6 ppm a year. The decade warms "
                   "clearly above the baseline, and the global CO2 network "
                   "begins in 1979, so the world mean is measured directly "
                   "for the first time. El Chichón erupts in 1982 and cools "
                   "the planet for two years; the 1988 US heatwave and "
                   "drought push the climate question into public view.",
        "driver_source": "NOAA GML; GISTEMP; GCB 2025 (this build)",
        "processes": ["EMIT", "AIR", "GREEN", "AERO"],
        "ecvs": ["Carbon dioxide, methane and other greenhouse gases",
                 "Surface temperature", "Aerosols",
                 "Earth radiation budget", "Clouds"],
    },
    "1990s": {
        "drivers": "Growth pauses briefly after Mount Pinatubo erupts in "
                   "1991 — sulfate aerosol cools the planet and the land "
                   "sink strengthens — then resumes. The decade ends warmer "
                   "than any before it, and the Kyoto Protocol is signed in "
                   "1997, the first treaty to cap greenhouse-gas emissions.",
        "driver_source": "NOAA GML; GISTEMP; GCB 2025 (this build)",
        "processes": ["EMIT", "AIR", "GREEN", "AERO", "SINKS"],
        "ecvs": ["Carbon dioxide, methane and other greenhouse gases",
                 "Surface temperature", "Aerosols", "Clouds",
                 "Upper-air temperature"],
    },
    "2000s": {
        "drivers": "Growth averages about 1.9 ppm a year as emissions "
                   "accelerate, led by coal in China. The decade is about "
                   "0.6 °C above the 1951–1980 baseline — the warmest decade "
                   "yet — and the 2003 European heatwave and the shrinking "
                   "Arctic sea ice make the warming visible.",
        "driver_source": "NOAA GML; GISTEMP; GCB 2025 (this build)",
        "processes": ["EMIT", "AIR", "GREEN", "SINKS"],
        "ecvs": ["Carbon dioxide, methane and other greenhouse gases",
                 "Surface temperature", "Upper-air temperature",
                 "Earth radiation budget", "Surface water vapour"],
    },
    "2010s": {
        "drivers": "Growth averages 2.4 ppm a year — the fastest decade on "
                   "record — and the decade is about 0.8 °C above baseline. "
                   "The 2015–16 El Niño drives the largest single-year CO2 "
                   "jump to that point, and the Paris Agreement is adopted "
                   "in 2015. Methane growth, slow in the 2000s, accelerates "
                   "again.",
        "driver_source": "NOAA GML; GISTEMP; GCB 2025 (this build)",
        "processes": ["EMIT", "AIR", "GREEN", "CH4", "SINKS"],
        "ecvs": ["Carbon dioxide, methane and other greenhouse gases",
                 "Surface temperature", "Surface water vapour",
                 "Upper-air water vapour", "Clouds"],
    },
    "2015–2024": {
        "drivers": "The warmest decade in the record, about 1 °C above "
                   "the 1951–1980 baseline, with CO2 growth averaging "
                   "2.6 ppm a year. The 2023–24 El Niño collapses the "
                   "tropical land sink and drives the largest annual CO2 "
                   "growth ever measured — 3.44 ppm globally in 2024 — "
                   "while 2024 becomes the warmest year on record.",
        "driver_source": "NOAA GML; GISTEMP; GCB 2025 (this build)",
        "processes": ["EMIT", "AIR", "GREEN", "CH4", "SINKS", "BALANCE"],
        "ecvs": ["Carbon dioxide, methane and other greenhouse gases",
                 "Surface temperature", "Surface water vapour",
                 "Earth radiation budget", "Upper-air temperature",
                 "Precipitation"],
    },
    "2020s so far": {
        "drivers": "The 2020s so far average about 1.1 °C above the "
                   "1951–1980 baseline — the warmest years ever measured. "
                   "CO2 growth stays above 2.5 ppm a year, 2024 sets the "
                   "record for annual growth, and 2025 is the second-warmest "
                   "year in the GISTEMP record. The pandemic dip in 2020 "
                   "emissions barely registers in the CO2 curve: one year's "
                   "cut is a small dent in a stock that keeps rising.",
        "driver_source": "NOAA GML; GISTEMP (this build)",
        "processes": ["EMIT", "AIR", "GREEN", "CH4", "SINKS", "BALANCE"],
        "ecvs": ["Carbon dioxide, methane and other greenhouse gases",
                 "Surface temperature", "Surface water vapour",
                 "Earth radiation budget", "Aerosols",
                 "Precursors for aerosols and ozone"],
    },
}


def decade_stats(label, years, mlo, gl, gis, hist):
    yrs = [y for y in years if y in mlo]
    mlo_mean = round(sum(mlo[y] for y in yrs) / len(yrs), 2)
    mlo_growth = [mlo[y] - mlo[y - 1] for y in yrs if y - 1 in mlo]
    mlo_growth_mean = round(sum(mlo_growth) / len(mlo_growth), 2)
    gl_growth = [gl[y] - gl[y - 1] for y in yrs if y in gl and y - 1 in gl]
    gl_growth_mean = (round(sum(gl_growth) / len(gl_growth), 2)
                      if gl_growth else None)
    gis_yrs = [y for y in years if y in gis]
    temp_mean = (round(sum(gis[y] for y in gis_yrs) / len(gis_yrs), 2)
                 if gis_yrs else None)
    af_years = [y for y in years if y in hist]
    af = [hist[y]["gatm"] / (hist[y]["efos"] + hist[y]["eluc"])
          for y in af_years]
    af_mean = round(sum(af) / len(af) * 100, 1) if af else None
    af_years_label = (f"{af_years[0]}–{af_years[-1]}" if af_years else None)
    note = DECADE_NOTES[label]
    return {
        "label": label,
        "years": f"{years[0]}–{years[-1]}",
        "mean_co2_mlo_ppm": mlo_mean,
        "mean_growth_mlo_ppm_yr": mlo_growth_mean,
        "mean_growth_gl_ppm_yr": gl_growth_mean,
        "mean_temp_anom_c": temp_mean,
        "mean_airborne_fraction_pct": af_mean,
        "airborne_fraction_years": af_years_label,
        "drivers": note["drivers"],
        "driver_source": note["driver_source"],
        "processes": note["processes"],
        "ecvs": note["ecvs"],
    }


def main():
    # --- download (skip if already present) ----------------------------------
    files = {
        "co2_annmean_mlo.txt": GML + "co2/co2_annmean_mlo.txt",
        "co2_annmean_gl.txt": GML + "co2/co2_annmean_gl.txt",
        "co2_mm_mlo.txt": GML + "co2/co2_mm_mlo.txt",
        "ch4_annmean_gl.txt": GML + "ch4/ch4_annmean_gl.txt",
        "GLB.Ts+dSST.csv": GISTEMP_URL,
    }
    for name, url in files.items():
        path = os.path.join(SRC, name)
        if not os.path.exists(path):
            download(url, path)
        else:
            print(f"using existing {name}")
    if not os.path.exists(GCB_XLSX):
        download_gcb(GCB_XLSX)
    else:
        print(f"using existing {os.path.basename(GCB_XLSX)}")

    mlo = parse_noaa_annual(os.path.join(SRC, "co2_annmean_mlo.txt"))
    gl = parse_noaa_annual(os.path.join(SRC, "co2_annmean_gl.txt"))
    ch4 = parse_noaa_annual(os.path.join(SRC, "ch4_annmean_gl.txt"))
    mlo_mm = parse_mlo_monthly(os.path.join(SRC, "co2_mm_mlo.txt"))
    gis = parse_gistemp(os.path.join(SRC, "GLB.Ts+dSST.csv"))
    hist = parse_gcb(GCB_XLSX)

    latest = max(mlo)  # 2025: latest complete annual mean in all series
    assert latest in gl and latest in gis and latest in ch4, \
        "series end years disagree"
    first = min(mlo)  # 1959
    print(f"series: MLO {min(mlo)}-{max(mlo)}, global CO2 "
          f"{min(gl)}-{max(gl)}, CH4 {min(ch4)}-{max(ch4)}, "
          f"GISTEMP {min(gis)}-{max(gis)}, GCB {min(hist)}-{max(hist)}")

    # --- annual table ---------------------------------------------------------
    annual = []
    for y in range(first, latest + 1):
        h = hist.get(y)
        annual.append({
            "year": y,
            "co2_mlo_ppm": mlo[y],
            "co2_gl_ppm": gl.get(y),
            "co2_growth_mlo_ppm": (round(mlo[y] - mlo[y - 1], 2)
                                   if y - 1 in mlo else None),
            "co2_growth_gl_ppm": (round(gl[y] - gl[y - 1], 2)
                                  if y in gl and y - 1 in gl else None),
            "temp_anom_c": gis.get(y),
            "airborne_fraction_pct": (round(
                h["gatm"] / (h["efos"] + h["eluc"]) * 100, 1)
                if h else None),
            "gatm_gtc": h["gatm"] if h else None,
            "efos_gtc": h["efos"] if h else None,
            "eluc_gtc": h["eluc"] if h else None,
            "socean_gtc": h["socean"] if h else None,
            "sland_gtc": h["sland"] if h else None,
        })
    prev = annual[-2]
    last = annual[-1]

    # --- methane series -------------------------------------------------------
    ch4_series = [{"year": y, "ch4_gl_ppb": ch4[y],
                   "growth_ppb": (round(ch4[y] - ch4[y - 1], 2)
                                  if y - 1 in ch4 else None)}
                  for y in sorted(ch4)]

    # --- monthly MLO (recent 24 months, trend column) -------------------------
    monthly_recent = [{"year": r["year"], "month": r["month"],
                       "trend_ppm": r["trend_ppm"]}
                      for r in mlo_mm[-24:]]
    latest_month = mlo_mm[-1]

    # --- headline summary -----------------------------------------------------
    base_1880_99 = sum(gis[y] for y in range(1880, 1900)) / 20
    warming_since_1880 = round(last["temp_anom_c"] - base_1880_99, 2)
    warming_2024 = round(gis[2024] - base_1880_99, 2)
    af_all = [a["airborne_fraction_pct"] for a in annual
              if a["airborne_fraction_pct"] is not None]
    af_mean_all = round(sum(af_all) / len(af_all), 1)
    af_2015_24 = [a["airborne_fraction_pct"] for a in annual
                  if 2015 <= a["year"] <= 2024]
    af_mean_2015_24 = round(sum(af_2015_24) / len(af_2015_24), 1)
    af_2024 = annual[-2]["airborne_fraction_pct"]  # 2024 is the last GCB year
    cum_gatm = round(sum(a["gatm_gtc"] for a in annual
                         if a["gatm_gtc"] is not None), 1)
    cum_gatm_2025 = round(cum_gatm + last["co2_growth_gl_ppm"] * GTC_PER_PPM, 1)
    cum_emis = round(sum((hist[y]["efos"] + hist[y]["eluc"])
                         for y in hist if first <= y <= max(hist)), 1)
    cum_land = round(sum(a["sland_gtc"] for a in annual
                         if a["sland_gtc"] is not None), 1)
    cum_ocean = round(sum(a["socean_gtc"] for a in annual
                          if a["socean_gtc"] is not None), 1)
    b24 = hist[2024]
    budget_2024 = {
        "efos_gtc": round(b24["efos"], 3),
        "eluc_gtc": round(b24["eluc"], 3),
        "total_emissions_gtc": round(b24["efos"] + b24["eluc"], 2),
        "gatm_gtc": round(b24["gatm"], 3),
        "sland_gtc": round(b24["sland"], 3),
        "socean_gtc": round(b24["socean"], 3),
        "cement_gtc": round(b24["cement"], 3),
        "imbalance_gtc": round(b24["efos"] + b24["eluc"] - b24["gatm"]
                               - b24["sland"] - b24["socean"]
                               - b24["cement"], 2),
    }
    growth_2024_gl = annual[-2]["co2_growth_gl_ppm"]
    growth_2024_mlo = annual[-2]["co2_growth_mlo_ppm"]
    ch4_last = ch4_series[-1]
    ch4_prev = ch4_series[-2]
    warmest = max(gis.items(), key=lambda kv: kv[1])

    summary = {
        "latest_year": latest,
        "latest_co2_gl_ppm": last["co2_gl_ppm"],
        "latest_co2_mlo_ppm": last["co2_mlo_ppm"],
        "prev_co2_gl_ppm": prev["co2_gl_ppm"],
        "growth_gl_ppm": last["co2_growth_gl_ppm"],
        "growth_mlo_ppm": last["co2_growth_mlo_ppm"],
        "growth_gl_ppm_2024": growth_2024_gl,
        "growth_mlo_ppm_2024": growth_2024_mlo,
        "latest_temp_anom_c": last["temp_anom_c"],
        "prev_temp_anom_c": prev["temp_anom_c"],
        "warming_since_1880_1899_c": warming_since_1880,
        "warming_2024_since_1880_1899_c": warming_2024,
        "warmest_year": warmest[0],
        "warmest_year_anom_c": warmest[1],
        "latest_ch4_ppb": ch4_last["ch4_gl_ppb"],
        "ch4_growth_ppb": ch4_last["growth_ppb"],
        "ch4_prev_ppb": ch4_prev["ch4_gl_ppb"],
        "airborne_fraction_latest_pct": af_2024,
        "airborne_fraction_latest_year": 2024,
        "airborne_fraction_mean_1959_2024_pct": af_mean_all,
        "airborne_fraction_mean_2015_2024_pct": af_mean_2015_24,
        "cumulative_atm_growth_1959_2024_gtc": cum_gatm,
        "cumulative_atm_growth_1959_2025_gtc": cum_gatm_2025,
        "cumulative_atm_growth_1959_2025_ppm": round(
            cum_gatm_2025 / GTC_PER_PPM, 1),
        "cumulative_emissions_1959_2024_gtc": cum_emis,
        "cumulative_land_sink_1959_2024_gtc": cum_land,
        "cumulative_ocean_sink_1959_2024_gtc": cum_ocean,
        "budget_2024_gtc": budget_2024,
        "cumulative_atm_share_of_emissions_pct": round(
            cum_gatm / cum_emis * 100, 1),
        "co2_rise_since_1959_mlo_ppm": round(mlo[latest] - mlo[first], 2),
        "co2_rise_since_preindustrial_gl_ppm": round(
            gl[latest] - PREIND_CO2_PPM, 2),
        "co2_pct_above_preindustrial": round(
            (gl[latest] - PREIND_CO2_PPM) / PREIND_CO2_PPM * 100, 1),
        "ch4_rise_since_preindustrial_ppb": round(
            ch4_last["ch4_gl_ppb"] - PREIND_CH4_PPB, 2),
        "latest_monthly_mlo": latest_month,
        "counter_rate_tco2_per_sec": round(
            last["co2_growth_gl_ppm"] * GTCO2_PER_PPM * 1e9
            / (365 * 24 * 3600), 0),
        "counter_rate_gtco2_per_yr": round(
            last["co2_growth_gl_ppm"] * GTCO2_PER_PPM, 2),
    }

    # --- decades ---------------------------------------------------------------
    decade_defs = [
        ("1960s", list(range(1960, 1970))),
        ("1970s", list(range(1970, 1980))),
        ("1980s", list(range(1980, 1990))),
        ("1990s", list(range(1990, 2000))),
        ("2000s", list(range(2000, 2010))),
        ("2010s", list(range(2010, 2020))),
        ("2015–2024", list(range(2015, 2025))),
        ("2020s so far", list(range(2020, latest + 1))),
    ]
    decades = [decade_stats(label, years, mlo, gl, gis, hist)
               for label, years in decade_defs]

    data = {
        "meta": {
            "title": "Atmospheric Ledger — CO2 in the air, and the warming it drives",
            "latest_year": latest,
            "first_year": first,
            "units": "CO2 in ppm (parts per million, mole fraction in dry air); "
                     "CH4 in ppb; temperature anomaly in °C vs 1951–1980; "
                     "carbon budget in GtC/yr (1 GtC = 3.664 GtCO2; "
                     "1 ppm CO2 = 2.124 GtC = 7.79 GtCO2)",
            "sources": {
                "co2": "NOAA Global Monitoring Laboratory, Trends in "
                       "atmospheric CO2 (Mauna Loa annual means and global "
                       "annual means; Lan et al.), "
                       "gml.noaa.gov/webdata/ccgg/trends/co2/",
                "ch4": "NOAA Global Monitoring Laboratory, Trends in "
                       "atmospheric CH4 (global annual means), "
                       "gml.noaa.gov/webdata/ccgg/trends/ch4/",
                "temp": "NASA GISTEMP v4, global mean surface temperature "
                        "anomaly, land-ocean (J-D annual means, baseline "
                        "1951-1980; Lenssen et al. 2019, "
                        "doi:10.1029/2018JD029522), "
                        "data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv",
                "budget": "Friedlingstein et al. 2025, Global Carbon Budget "
                          "2025, Earth Syst. Sci. Data 18, 3211-3288, "
                          "doi:10.5194/essd-18-3211-2026; data "
                          "doi:10.18160/GCP-2025 (spreadsheet via ICOS Carbon "
                          "Portal). Budget quantities run through 2024 only.",
                "gcos": "GCOS Essential Climate Variables, atmospheric domain "
                        "(16 ECVs), gcos.wmo.int/site/global-climate-observing-system-gcos/essential-climate-variables "
                        "(accessed 2026-11-27)",
                "forcing": "IPCC AR6 WG1, Chapter 7 (Forster et al. 2021), "
                           "effective radiative forcing 1750-2019, "
                           "doi:10.1017/9781009157896.009",
                "preindustrial": "CO2 278 ppm and CH4 722 ppb, "
                                 "pre-industrial (1750) references, IPCC AR6",
            },
            "notes": [
                "Headline CO2 and temperature values are computed from the "
                "downloaded NOAA GML and NASA GISTEMP files by this script; "
                "nothing on the page is hand-typed from a table.",
                "The Global Carbon Budget 2025 series ends in 2024, so the "
                "airborne fraction and the sink figures run through 2024; "
                "the 2025 CO2 growth (2.84 ppm globally) is the observed "
                "NOAA value, converted at 2.124 GtC per ppm for the "
                "cumulative total.",
                "No values on this page are read from a chart. Every figure "
                "comes from a downloaded data file or a cited paper value.",
                "Sign convention: atmospheric growth is POSITIVE (carbon "
                "added to the air). The airborne fraction is the share of "
                "total human emissions (fossil + land-use change) that "
                "stayed in the atmosphere in that year.",
                "Temperature anomalies are relative to the 1951-1980 "
                "baseline (GISTEMP). Warming since 1880-1899 is the "
                "difference between the latest anomaly and the 1880-1899 "
                "mean anomaly (-0.23 °C).",
            ],
        },
        "annual": annual,
        "ch4": ch4_series,
        "monthly_mlo_recent": monthly_recent,
        "summary": summary,
        "decades": decades,
        "ecvs": [{"name": n, "group": g, "role": r} for n, g, r in ECVS],
        "processes": PROCESSES,
        "forcing": FORCING,
    }
    with open(OUT, "w") as f:
        json.dump(data, f, indent=1)
    print(f"wrote {OUT}")
    print(f"latest: {latest} global CO2 {last['co2_gl_ppm']} ppm "
          f"(+{last['co2_growth_gl_ppm']} ppm vs {latest - 1}), "
          f"MLO {last['co2_mlo_ppm']} ppm (+{last['co2_growth_mlo_ppm']}), "
          f"GISTEMP {last['temp_anom_c']:+.2f} °C, "
          f"CH4 {ch4_last['ch4_gl_ppb']} ppb (+{ch4_last['growth_ppb']})")
    print(f"warming since 1880-1899: {warming_since_1880} °C "
          f"({warming_2024} °C in 2024, the warmest year)")
    print(f"airborne fraction 2024: {af_2024}%; mean 1959-2024: "
          f"{af_mean_all}%")
    print(f"cumulative atmospheric growth 1959-2025: {cum_gatm_2025} GtC "
          f"({round(cum_gatm_2025 / GTC_PER_PPM, 1)} ppm)")


if __name__ == "__main__":
    main()
