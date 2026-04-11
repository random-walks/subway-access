## 3. Data and Methods

### 3.1 Data Sources

Four primary data sources were assembled for this analysis. Table 1 summarizes coverage and vintage.

**Table 1. Data Sources**

| Source | Description | *N* | Coverage |
| :--- | :--- | ---: | :--- |
| MTA Subway Station Catalog | Station locations, routes, ADA status | 493 stations | All active stations; fetched April 9, 2026 via Open Data NY Socrata API (MTA, 2026) |
| MTA Elevator & Escalator Availability | Monthly outage and uptime records | 6,765 rows | May 2025--April 2026, 12-month rolling window (MTA, 2026) |
| American Community Survey (ACS) | Tract-level disability, senior, and poverty rates | 2,317 tracts | 2023 vintage, 5-year estimates covering survey period 2019--2023 (U.S. Census Bureau, 2024) |
| NYC Census Tract Boundaries | Tract polygon geometries | 2,325 tracts | 2020 vintage, via nyc-geo-toolkit |

Station data were retrieved programmatically from the MTA's Socrata-hosted open data portal. Elevator and escalator availability records were aggregated to station-level uptime percentages over the 12-month window. ACS demographic variables---disability rate (percent of population with any disability), senior rate (percent aged 65+), and poverty rate (percent below federal poverty line)---were matched to census tracts by GEOID. Of 2,325 tract geometries, 2,317 successfully matched to ACS demographic records and form the analytic sample.

### 3.2 Accessibility Model

A census tract is classified as "covered" if its geographic centroid falls within an 800-meter Euclidean radius of at least one ADA-accessible subway station. The 800 m threshold approximates a 10-minute walk at 80 m/min, a standard pedestrian speed assumption in transportation planning (El-Geneidy et al., 2014). This is intentionally a first-pass measure: Euclidean distance overstates true walking coverage because it ignores street network topology, elevation changes, and sidewalk conditions. The centroid-based approach further simplifies by treating each tract as a point rather than an area, meaning that some residents of "covered" tracts may in practice reside beyond walking distance.

### 3.3 Need and Gap Scores

Each tract receives a composite need score defined as the unweighted arithmetic mean of its disability rate, senior rate, and poverty rate:

```
NeedScore_i = (disability_rate_i + senior_rate_i + poverty_rate_i) / 3
```

The gap score operationalizes unmet need: for uncovered tracts, the gap score equals the need score; for covered tracts, the gap score is zero. This formulation assigns the highest gap scores to uncovered tracts where disability, age, and economic vulnerability concentrate simultaneously.

### 3.4 Reliability-Weighted Coverage

Nominal coverage treats all ADA-designated stations as fully accessible. Reliability-weighted coverage discounts each station's contribution by its observed elevator uptime fraction over the observation window:

```
EffectiveCoverage_i = max_j(Uptime_j)    for all ADA stations j within 800 m of tract i
```

A station with 50% elevator uptime over the 12-month period contributes 0.50 effective coverage rather than 1.00. This measure captures the distinction between *de jure* and *de facto* accessibility---a station that appears accessible in the MTA database but whose elevators are non-functional half the time provides only half the access.

### 3.5 Temporal Panel and Difference-in-Differences Specification

To enable future causal analysis, we construct a balanced panel of 2,317 tracts across 7 periods (2017--2023), yielding 16,219 tract-year observations. ADA upgrade years are sourced from a station-by-station research effort that compiled actual completion dates from MTA press releases, Governor's announcements, MTA Capital Program records, Wikipedia station articles, and news coverage. Of the 157 currently accessible stations, 101 (64.3%) have sourced upgrade years spanning 1987--2026; the remaining 56 stations---primarily Key Station Program stations from the 1990s--2010s where per-station completion dates were not publicly documented---use a deterministic hash-based fallback that distributes them across the study window. All sourced dates and citations are maintained in per-station research files (`seeds/enhanced/research/`). Tracts are classified as:

- **Treatment** (*n* = 831): tracts that gained an accessible station during the panel window.
- **Control** (*n* = 1,486): tracts that were never covered in any period.

The DiD specification is:

```
Y_it = α + β · Treatment_it + γ · X_it + δ_i + τ_t + ε_it
```

| Symbol | Description |
| :--- | :--- |
| *Y*_it | Outcome variable (e.g., population change, housing cost) |
| Treatment_it | 1 if tract *i* has an accessible station by period *t*, 0 otherwise |
| *X*_it | Time-varying covariates: disability rate, senior rate, poverty rate |
| δ_i | Tract fixed effects (absorb time-invariant tract characteristics) |
| τ_t | Period fixed effects (absorb city-wide temporal trends) |
| β | Causal estimate: average treatment effect of gaining an accessible station |

For spatial dependence, the model extends to a spatial autoregressive (SAR) panel:

```
Y_it = ρ · W · Y_it + β · X_it + δ_i + τ_t + ε_it
```

where *W* is the row-standardized distance-based spatial weights matrix (2,317 units, mean 47.9 neighbors, 2 km threshold).

**Data provenance caveat.** The upgrade timeline is substantially---but not entirely---sourced from public records. Of the 157 accessible stations, 101 have dates traced to official MTA announcements, press releases, or documented construction completions. The remaining 56 use a deterministic hash-based fallback because per-station completion records for the MTA's Key Station Program (1994--2020) were not publicly available at the time of analysis. Consequently, β estimates from this panel should be interpreted with caution: the treatment timing is accurate for the majority of stations but approximate for roughly one-third. A FOIL request to the MTA for the complete Key Station Program completion schedule would close this gap. Three identifying assumptions merit explicit discussion:

1. **Parallel trends.** In the absence of treatment, treated and control tracts would follow the same outcome trajectory. Pre-treatment outcome data under the sourced upgrade dates would enable formal testing of this assumption.
2. **No anticipation.** Units do not change behavior in anticipation of treatment. Since ADA station upgrades are capital projects announced years in advance, household sorting based on announced plans could violate this assumption.
3. **SUTVA.** One unit's treatment does not affect another unit's outcome. Spatial spillovers---e.g., a new accessible station increasing property values in adjacent tracts---could violate this assumption. The SAR extension partially addresses this concern.

### 3.6 Spatial Analysis

Spatial dependence was assessed using Global Moran's *I* with a distance-based spatial weights matrix (2 km threshold). The weights matrix covers 2,317 units, of which 2,315 have at least one neighbor (2 islands excluded). Each unit's neighbors within 2 km receive equal row-standardized weight. The mean number of neighbors per unit is 47.9 (median: 51, range: 0--86).

An OLS regression of gap score on demographic predictors was estimated with heteroskedasticity-consistent (HC1) robust standard errors. Variance inflation factors (VIF) were computed to assess multicollinearity. Pearson and Spearman rank correlation matrices were computed across all demographic and accessibility variables.
