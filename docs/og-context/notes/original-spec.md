# `subway-access` — MTA Station Accessibility Analyzer

## Resume variants: 🏛️ Civic (primary), 📊 Econ (secondary)

---

## One-liner

Spatial analysis toolkit that measures how accessible NYC's subway system
actually is — combining station ADA data, elevator/escalator outage feeds,
walking-distance catchment areas, and neighborhood demographics to produce
equity-focused accessibility scores.

---

## Why this matters to real users

NYC's subway has 472 stations. Only about 130 are ADA-accessible. And even
"accessible" stations frequently lose their elevators — the MTA publishes
real-time outage data, but no one systematically analyzes it. For the ~1 million
New Yorkers with mobility disabilities, plus every parent with a stroller and
every person carrying heavy loads, this is a daily quality-of-life issue.

The policy conversation around subway accessibility is active right now (the MTA
committed to making more stations accessible under a federal consent decree),
but the data to evaluate progress is scattered across multiple feeds with no
unified analysis tool.

**Who would actually use this:**

- MTA planners deciding which stations to prioritize for accessibility upgrades
- Disability rights advocates building cases for specific stations
- City Council members evaluating transit equity in their districts
- Urban studies and transportation researchers
- Journalists covering MTA capital programs
- NYC Comptroller's office (they audit MTA spending)

---

## What the end product looks like

### Core library (`subway_access`)

1. **Data ingestors:**
   - MTA GTFS static feed (station locations, routes, schedules)
   - MTA real-time elevator/escalator outage API
   - NYC Open Data: ADA-accessible station list
   - Census ACS: disability prevalence, age distribution, income by tract
   - NYC CSCL / pedestrian network for walk-distance calculations

2. **Analysis modules:**
   - **Catchment area generator:** For each station, compute the walk-distance
     polygon (not Euclidean — actual street network) at 5-min, 10-min, 15-min
     thresholds. Uses the pedestrian network, not just crow-flies buffers.
   - **Accessibility scorer:** Each station gets a composite score: ADA status ×
     elevator reliability (from historical outage data) × catchment population ×
     demographic weight (disability prevalence, age 65+, poverty rate in
     catchment)
   - **Gap analyzer:** Identifies census tracts with high need (high disability
     rate, high age, low income) but low accessibility (no ADA station within
     15-min walk, or ADA station with poor elevator reliability)
   - **Temporal reliability:** How often is each "accessible" station _actually_
     accessible over a 30/60/90-day window? Based on historical outage data.

3. **Outputs:**
   - GeoJSON of all catchment areas (for mapping)
   - Station-level CSV with all scores and component metrics
   - Tract-level CSV of accessibility gaps
   - Summary statistics by borough, community district, council district
   - Interactive Folium/deck.gl map

### Example notebook

Walk through the full analysis for one borough, produce the gap analysis, and
render an interactive map showing "transit deserts" for mobility-impaired New
Yorkers. Include a written interpretation of the findings, as if presenting to a
city council committee.

---

## Key technical decisions

**Street network routing:** Use `osmnx` to pull the pedestrian network from
OpenStreetMap. Compute isochrone polygons with `networkx`. Don't use Euclidean
buffers — they dramatically overestimate accessibility in areas with rivers,
highways, or large blocks.

**Elevator reliability:** The MTA publishes outage data but doesn't provide
historical archives in a clean format. Build a simple scraper/poller that logs
outages over time to a local SQLite DB. For the initial release, seed with
whatever historical data is available and document the collection methodology.

**Demographic weighting:** Pull Census ACS 5-year estimates at the tract level
via `cenpy` or direct Census API. The key variables are: disability status
(S1810), age 65+ (B01001), poverty rate (S1701), zero-vehicle households
(B08201). Weight these into a "need score" per tract.

**No proprietary dependencies.** Everything runs on `osmnx`, `geopandas`,
`networkx`, `folium`, `cenpy`. No ESRI, no Mapbox tokens required for the core
analysis.

---

## MVP scope (weekend 1)

- [ ] Ingest MTA GTFS stations + ADA status
- [ ] Generate Euclidean catchment buffers (simpler first pass — swap for
      network later)
- [ ] Join Census disability/age data at tract level
- [ ] Compute basic accessibility gap score per tract
- [ ] Folium map showing gaps by color
- [ ] README with methodology, screenshot, data sources
- [ ] Notebook walkthrough for one borough

## Stretch scope (weekend 2+)

- [ ] Street-network isochrone catchments via osmnx
- [ ] Real-time elevator outage integration
- [ ] Historical reliability scoring
- [ ] Council district / community district aggregations
- [ ] Comparison over time (if historical data available)
- [ ] Static site generator for a public-facing dashboard

---

## README must communicate

1. **The problem:** 1M+ NYers with mobility disabilities face an accessibility
   lottery every day, and the data to measure it is scattered
2. **The methodology:** not just "which stations have elevators" but "which
   neighborhoods have reliable accessible transit weighted by who lives there"
3. **A map:** the gap analysis map is the hero image — it should be immediately
   legible
4. **Policy relevance:** explicitly connect to the MTA's ADA consent decree and
   capital plan
5. **Reproducibility:** anyone can re-run the analysis with
   `python -m subway_access --borough manhattan`

---

## What this proves on your resume

- You think about spatial analysis as a tool for equity and policy, not just
  visualization
- You can combine multiple open data sources (MTA, Census, OSM) into a unified
  analysis
- You understand network-based spatial analysis (isochrones, not buffers)
- You can frame technical work in terms non-technical stakeholders care about
- You have domain knowledge about NYC transit — a perennial topic in city
  government
