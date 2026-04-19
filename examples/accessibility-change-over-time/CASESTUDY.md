<!-- Author: Blaise Albis-Burdige | https://blaiseab.com | Creator of subway-access -->

> **Note from Blaise:** This case study is an example of more advanced statistical analysis using the [subway-access](https://github.com/random-walks/subway-access) library and the NYC open data ecosystem. The central question is almost comical: do accessibility initiatives actually increase equity if the elevator is never running? On a more serious note, the findings highlight a gap in investment follow-through when it comes to ADA infrastructure. Current accessibility classifications may succeed in incentivizing initial capital commitments, but without robust maintenance funding, many stations that are "accessible" on paper are not accessible in practice.

# Assessing ADA Accessibility Gaps in the New York City Subway System: A Spatial Equity Analysis

**By [Blaise Albis-Burdige](https://blaiseab.com)** | Author, [subway-access](https://github.com/random-walks/subway-access)

*April 2026*

---

## Abstract

The Americans with Disabilities Act (ADA) of 1990 mandates equal access to public transportation, yet more than three decades later, the New York City subway system remains largely noncompliant. This study provides a tract-level spatial equity analysis of ADA accessibility across all five NYC boroughs using April 2026 station data from the Metropolitan Transportation Authority (MTA). Of the system's 493 active stations, only 157 (31.8%) are ADA-accessible. We define coverage using an 800-meter Euclidean catchment radius from each accessible station and overlay American Community Survey (ACS) 2023 five-year demographic estimates for 2,317 census tracts (total study population: 8,507,596). A composite need score---the unweighted mean of tract-level disability, senior, and poverty rates---identifies communities where inaccessibility imposes the greatest burden. We extend nominal coverage with a reliability-weighted measure that discounts station coverage by actual elevator uptime over a 12-month observation window (May 2025--April 2026), finding that 49 accessible stations operated below 95% uptime and that Manhattan's effective coverage drops from 77% to 71% under reliability weighting. Results indicate that 4,717,140 New Yorkers (55.4%) reside in tracts with no ADA-accessible station within walking distance, with Queens bearing the largest absolute gap (1,752,073 residents, 22% tract coverage). An OLS equity regression identifies senior population rate as the strongest demographic predictor of gap score (*R*² = .202, *F*(3, 2313) = 108.83, *P* < .001). Global Moran's *I* statistics confirm significant spatial clustering of gap scores (*I* = .23, *z* = 40.87, *P* < .001), need scores (*I* = .20, *z* = 33.91, *P* < .001), and disability rates (*I* = .28, *z* = 48.92, *P* < .001), indicating that accessibility deficits concentrate in identifiable geographic corridors rather than distributing randomly across the city. A difference-in-differences (DiD) panel framework with tract and period fixed effects is constructed using a substantially sourced upgrade timeline: 101 of 157 stations (64.3%) have upgrade years traced to MTA press releases, Capital Program records, and news coverage spanning 1987--2026, with the remaining 56 stations using approximate dates pending a FOIL request for Key Station Program completion records. These findings suggest that capital investment in new ADA stations without commensurate maintenance funding produces nominal compliance that does not translate to functional access, and that spatially targeted intervention in high-need clusters would yield greater equity returns than system-wide uniform upgrades.

*Keywords:* ADA accessibility, public transit equity, spatial autocorrelation, difference-in-differences, New York City subway, elevator reliability


## 1. Introduction

The New York City subway system is the largest rapid transit network in the United States, serving approximately 3.6 million riders on an average weekday across 493 stations and 36 routes (Metropolitan Transportation Authority [MTA], 2026). As of the April 9, 2026 data pull used in this study, only 157 stations (31.8%) meet ADA accessibility standards---meaning they have elevators or ramps that permit use by people in wheelchairs, with strollers, or who otherwise cannot navigate stairs. The remaining 336 stations are functionally inaccessible to a substantial and growing segment of the population.

This accessibility deficit is not merely an inconvenience. For the estimated 895,000 New Yorkers with ambulatory disabilities (U.S. Census Bureau, 2024), and for the 1.15 million residents aged 65 and older whose mobility may be limited, a station without an elevator is a station that does not exist. The problem extends to parents with strollers, travelers with luggage, and anyone with a temporary injury---populations that are large but largely invisible in accessibility planning.

Recent scholarship has examined spatial and racial dimensions of subway accessibility in New York City. Baghestani et al. (2024) employed a gravity index incorporating both distance and service frequency to assess equitable access across boroughs and racial groups, finding that Queens exhibited the most pronounced accessibility deficit and that the non-Hispanic Black population in Queens faced disproportionate barriers. Their analysis focused on the spatial distribution of service quality rather than physical station accessibility, leaving the question of ADA compliance---and the reliability of nominally compliant stations---unexamined. The broader transit equity literature distinguishes between horizontal equity, in which services are distributed according to aggregate travel demand, and vertical equity, in which services are distributed according to the needs of vulnerable populations (Delbosc & Currie, 2011; Lucas & Jones, 2012). This study operates primarily within the vertical equity framework, asking whether ADA infrastructure reaches the communities that need it most.

Transportation equity has received renewed policy attention in New York City following the June 2024 launch of the Manhattan congestion pricing program, which charges vehicles entering below 60th Street a peak toll of $9 (MTA, 2024). The program's equity logic assumes that drivers priced off the road will shift to public transit---an assumption that fails for the approximately 68% of subway stations that cannot be used by people with mobility impairments. If congestion pricing generates revenue earmarked for transit capital improvements but those improvements do not include ADA upgrades, the policy risks compounding existing inequities rather than alleviating them.

This study asks four questions:

1. What is the current scale of ADA inaccessibility across NYC boroughs, measured at the census-tract level?
2. How does elevator reliability affect the effective coverage of nominally accessible stations?
3. What demographic factors predict the spatial distribution of accessibility gaps?
4. Is there significant spatial clustering of gap tracts that could inform geographically targeted investment?

We address these questions using a combination of descriptive spatial analysis, reliability-weighted coverage modeling, OLS regression with robust standard errors, and global spatial autocorrelation testing. We also specify---but do not estimate---a difference-in-differences panel model for future causal analysis once actual MTA Capital Program upgrade dates become available.


## 2. Background

### 2.1 Study Area

New York City comprises five boroughs---Manhattan, Brooklyn, Queens, the Bronx, and Staten Island---spanning approximately 783 km² with a resident population of 8,507,596 (U.S. Census Bureau, 2024). The city's subway system, operated by the MTA, is the primary mode of public transportation, carrying over 1.1 billion annual riders prior to the COVID-19 pandemic (MTA, 2020a). Station density varies dramatically by borough: Manhattan has 151 stations concentrated in 59 km², while Queens has 82 stations distributed across 283 km², the largest borough by area. This geographic asymmetry is a structural driver of accessibility inequality.

### 2.2 ADA Compliance and the MTA Capital Program

The Americans with Disabilities Act of 1990 requires that public transit systems be accessible to individuals with disabilities, but the statute was interpreted to require accessibility only at "key stations" rather than system-wide compliance. As a result, the NYC subway operated for decades with minimal accessibility investment. The NYC Council Data Team (2019) identified 283 non-accessible stations (57% of the system at that time) with no funded plan for upgrades. The MTA's 2020--2024 Capital Program committed $5.2 billion to 67 station ADA upgrades, representing a contract award pace five times pre-2020 levels (MTA, 2020b). Despite this acceleration, full system accessibility remains decades away at current rates.

### 2.3 Related Literature

Accessibility research has evolved through three broad methodological traditions: count-based opportunity measures, gravity indexes, and utility-based measures (Ding et al., 2018; Liu & Zhu, 2004). Count-based measures assess the number of opportunities (e.g., transit stops) within a fixed distance or travel-time threshold. Gravity indexes weight opportunities by a distance-decay function and an attractiveness factor such as service frequency (Bartzokas-Tsiompras & Photis, 2019; Souche et al., 2016). Utility-based measures model traveler choice among competing destinations and modes (Berjisian & Habibian, 2017).

Equity assessment typically employs Gini coefficients and Lorenz curves to quantify distributional inequality across populations or geographic units (Giannotti et al., 2021). Baghestani et al. (2024) applied a gravity index to NYC subway access at the census-block level, incorporating both distance and service frequency, and used Gini coefficients to measure spatial and racial inequality. They found wide disparities across boroughs and identified Queens as the most underserved, with particular disadvantage for non-Hispanic Black residents. Zhang et al. (2024) examined transit deserts in the New York metropolitan area using multinomial logistic regression and found higher transit desert rates in economically disadvantaged neighborhoods. Gu and Zheng (2024) used difference-in-differences on individual residential trajectories in Shenzhen to estimate the causal effect of new subway stations on residential location choices, finding attraction effects in lower-rent neighborhoods without displacement.

The present study departs from prior work in three respects. First, it focuses specifically on *physical* ADA accessibility---the presence of elevators and ramps---rather than on proximity to stations or service frequency, since a nearby station without an elevator is useless to a wheelchair user. Second, it introduces a reliability-weighted coverage measure that accounts for actual elevator uptime, distinguishing between nominal and functional accessibility. Third, it specifies a panel econometric framework (DiD with spatial autoregressive extension) for future causal estimation of the effects of ADA upgrades on neighborhood outcomes.


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


## 4. Results

### 4.1 System-Wide Coverage

Of the 493 active subway stations in the MTA system, 157 (31.8%) are designated ADA-accessible. At the tract level, 901 of 2,317 tracts (38.9%) have at least one accessible station within the 800 m catchment, while 1,416 tracts (61.1%) fall in the accessibility gap. The population residing in gap tracts totals 4,717,140---55.4% of the study population of 8,507,596 (see [Table 1, auto-generated report](reports/accessibility-change-report.md#table-1-system-wide-snapshot); [Figure 5](reports/figures/figure-5-choropleth-coverage-status.png)).

### 4.2 Borough Disparities

Coverage varies dramatically across boroughs. Manhattan, with 151 stations (61 ADA-accessible) concentrated in 59 km², achieves 77% tract coverage with a mean distance to the nearest accessible station of 584 m. Queens, the largest borough by area (283 km²), has only 82 stations (26 ADA-accessible) and achieves 22% tract coverage, leaving 1,752,073 residents without accessible coverage at a mean distance of 1,966 m. Staten Island has the lowest coverage rate (9%, 6 ADA stations, mean distance 2,983 m) but a smaller absolute gap population of 446,127. Brooklyn (41% coverage, 1,467,660 gap population) and the Bronx (46% coverage, 690,126 gap population) fall between these extremes (see [Table 2](reports/accessibility-change-report.md#table-2-borough-comparison); [Figure 1](reports/figures/figure-1-coverage-by-borough.png); [Figure 2](reports/figures/figure-2-gap-population.png)).

**Table 2. Borough Comparison**

| Borough | Stations | ADA stations | Tracts | Covered tracts (%) | Gap population | Mean distance (m) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Manhattan | 151 | 61 | 309 | 238 (77%) | 361,154 | 584 |
| Brooklyn | 169 | 43 | 800 | 326 (41%) | 1,467,660 | 1,007 |
| Queens | 82 | 26 | 723 | 159 (22%) | 1,752,073 | 1,966 |
| Bronx | 70 | 21 | 360 | 167 (46%) | 690,126 | 980 |
| Staten Island | 21 | 6 | 125 | 11 (9%) | 446,127 | 2,983 |

The geographic pattern is visible in the coverage choropleth ([Figure 5](reports/figures/figure-5-choropleth-coverage-status.png)): Manhattan appears as an island of coverage surrounded by large swaths of inaccessibility in the outer boroughs. The gap score map ([Figure 4](reports/figures/figure-4-choropleth-gap-score.png)) further shows that high-need tracts without coverage concentrate in specific corridors rather than distributing uniformly.

### 4.3 Reliability Analysis

Among the 157 ADA-accessible stations, 49 operated below 95% elevator uptime during the May 2025--April 2026 observation window. The most extreme cases include 59 St-Columbus Circle (0.0% uptime---effectively non-functional for the entire year), Lexington Av/53 St (9.3%), 42 St-Port Authority Bus Terminal (13.6%), 34 St-Hudson Yards (32.8%), and 34 St-Herald Square (51.3%). These are among the highest-ridership stations in the system (see [Table 3](reports/accessibility-change-report.md#table-3-most-fragile-accessible-stations); [Figure 3](reports/figures/figure-3-reliability-nominal-vs-effective.png)).

When coverage is recomputed using reliability weighting, Manhattan's tract coverage drops from 77% nominal to 71% effective---a 6-percentage-point reduction attributable entirely to elevator downtime. This is the *best-performing* borough; the implication is that system-wide effective coverage is meaningfully lower than the nominal 38.9% figure suggests.

### 4.4 Temporal Progression

The temporal panel shows coverage expanding from 16.8% of tracts in 2017 (389 tracts, 1,620,306 residents) to 35.9% in 2023 (831 tracts, 3,519,151 residents), representing the sourced and modeled rollout of ADA upgrades over seven periods (see [Table 4](reports/accessibility-change-report.md#table-4-coverage-progression); [Figure 6](reports/figures/figure-6-coverage-progression.png)). The higher 2017 baseline compared to a fully synthetic timeline reflects the large number of stations that were already accessible before the study window---including Archer Avenue line stations (1988), 63rd Street line stations (1989), and numerous Key Station Program completions from the 1990s--2000s. The progression is monotonically increasing by construction, as stations do not lose ADA status once upgraded.

### 4.5 Treatment-Control Balance

Welch's *t*-tests (unequal variance) comparing treatment (*n* = 831) and control (*n* = 1,486) tracts reveal statistically significant differences across all three primary demographic indicators:

- **Disability rate:** Treatment *M* = .049, Control *M* = .039, difference = +.010, *t* = 6.40, *P* < .001, Cohen's *d* = 0.29 (small).
- **Senior rate:** Treatment *M* = .150, Control *M* = .162, difference = −.012, *t* = −3.34, *P* < .001, Cohen's *d* = −0.14 (negligible).
- **Poverty rate:** Treatment *M* = .074, Control *M* = .056, difference = +.018, *t* = 6.42, *P* < .001, Cohen's *d* = 0.28 (small).

All effect sizes are small to negligible by conventional benchmarks (Cohen, 1988), but the consistent direction---treatment tracts have higher disability and poverty rates---indicates that ADA upgrades are reaching higher-need neighborhoods. This is directionally consistent with equity objectives. However, the imbalance means that a naive before-after comparison would overstate the benefit of ADA station access; the DiD specification with tract and period fixed effects is necessary to absorb baseline differences (see [Table 5](reports/accessibility-change-report.md#table-5-balance-check); [Figure 7](reports/figures/figure-7-treatment-vs-control-balance.png)).

### 4.6 Model Diagnostics

Distribution diagnostics for the three primary analytic variables are reported in full in the [model specification supplement](reports/supplementary/model-specification.md) and summarized here:

**Table 3. Distribution Diagnostics**

| Statistic | Need score | Distance (m) | Gap score |
| :--- | ---: | ---: | ---: |
| *N* | 2,317 | 2,317 | 1,346 |
| Mean | 0.088 | 1,353 | 0.090 |
| Median | 0.085 | 995 | 0.085 |
| *SD* | 0.041 | 1,255 | 0.037 |
| Skewness | 0.73 | 2.31 | 1.34 |
| Kurtosis (excess) | 2.41 | 6.12 | 4.24 |
| Jarque-Bera | 769.9 | 5,672.3 | 1,408.2 |
| Jarque-Bera *P* | < .001 | < .001 | < .001 |

The Jarque-Bera test rejects the null hypothesis of normality for all three variables (*P* < .001 in each case). However, the practical significance of this rejection warrants careful interpretation. The need score distribution exhibits moderate positive skewness (0.73) and mild leptokurtosis (excess kurtosis = 2.41)---departures that are common in demographic rate data and are unlikely to distort inference at *N* = 2,317, where the Central Limit Theorem provides asymptotic normality for parameter estimates. The distance distribution is more severely right-skewed (skewness = 2.31, excess kurtosis = 6.12), reflecting the heavy tail of tracts far from any accessible station; a log transformation would be appropriate if distance enters a regression model as a predictor. The gap score distribution (skewness = 1.34, excess kurtosis = 4.24) is intermediate, reflecting its compositional dependence on both need scores and coverage status.

The distance-decay curve ([Figure 9](reports/figures/figure-9-distance-decay.png)) validates the 800 m catchment: coverage is near-total within 800 m and drops sharply beyond it, confirming that the threshold captures the empirical break in accessibility. The gap-distance scatter ([Figure 10](reports/figures/figure-10-gap-vs-distance-scatter.png)) shows that high-population tracts appear at every distance range, not only at the urban periphery---this is a systemic problem affecting the urban core as well as outlying areas.

### 4.7 Correlation and Equity Regression

Pearson and Spearman rank correlation matrices were computed for all demographic and accessibility variables (see [correlation analysis supplement](reports/supplementary/correlation-analysis.md); [Figure 11](reports/figures/figure-11-correlation-heatmap.png)). The two matrices show strong agreement, supporting the appropriateness of linear association as a first approximation. Key correlations (Pearson) include:

- Need score and gap score: *r* = .42, *P* < .001
- Senior rate and gap score: *r* = .40, *P* < .001
- Disability rate and poverty rate: *r* = .70, *P* < .001
- Gap score and distance to nearest station: *r* = .42, *P* < .001

Variance inflation factors for the three demographic predictors are all below 2.3 (disability VIF = 2.28, poverty VIF = 2.24, senior VIF = 1.17), indicating no problematic multicollinearity.

An OLS regression of gap score on demographic predictors with HC1 robust standard errors yielded:

**Table 4. OLS Regression: Gap Score on Demographic Predictors**

| Variable | *b* | *SE* | *t* | *P* | |
| :--- | ---: | ---: | ---: | ---: | :--- |
| Constant | −0.000 | 0.003 | −0.00 | .999 | |
| Poverty rate | 0.164 | 0.033 | 4.99 | < .001 | \*\*\* |
| Disability rate | 0.013 | 0.063 | 0.21 | .84 | |
| Senior rate | 0.263 | 0.017 | 15.93 | < .001 | \*\*\* |

*N* = 2,317. *R*² = .202, Adjusted *R*² = .201. *F*(3, 2313) = 108.83, *P* < .001.

Senior rate is the strongest predictor of gap score by a wide margin (|*t*| = 15.93), followed by poverty rate (|*t*| = 4.99). Disability rate is not a statistically significant predictor when the other two variables are included (*t* = 0.21, *P* = .84). This does not mean disability is unrelated to accessibility gaps---it reflects the high collinearity between disability and poverty (*r* = .70), which absorbs the shared variance. The model explains approximately 20% of the variance in gap scores, leaving 80% attributable to geographic, infrastructural, and historical factors not captured by tract demographics alone.

### 4.8 Spatial Autocorrelation

Global Moran's *I* statistics confirm statistically significant positive spatial autocorrelation for all tested variables:

**Table 5. Global Moran's *I* Results**

| Variable | Moran's *I* | *E*[*I*] | *z* | *P* | |
| :--- | ---: | ---: | ---: | ---: | :--- |
| Gap score | .2271 | −.0004 | 40.87 | < .001 | \*\*\* |
| Need score | .1991 | −.0004 | 33.91 | < .001 | \*\*\* |
| Disability rate | .2757 | −.0004 | 48.92 | < .001 | \*\*\* |

All three variables exhibit strong spatial clustering: tracts with high gap scores are surrounded by other high-gap-score tracts, and similarly for need scores and disability rates (see [spatial diagnostics supplement](reports/supplementary/spatial-diagnostics.md)). The geographic comparison maps ([Figure 14](reports/figures/figure-14-gap-vs-poverty-map.png); [Figure 15](reports/figures/figure-15-gap-vs-disability-map.png)) visually confirm that high-poverty and high-disability tracts overlap spatially with high-gap-score tracts.

This spatial dependence has two implications for inference. First, OLS standard errors are likely underestimated because the independence assumption is violated; spatial HAC standard errors or the SAR panel specification should be used for formal hypothesis testing. Second, for policy, the clustering indicates that accessibility gaps are concentrated in identifiable neighborhood corridors---targeted investment in these clusters would yield greater coverage gains per dollar than spatially uniform upgrades.


## 5. Discussion

### 5.1 Summary of Findings

The central finding of this analysis is stark: 4,717,140 New Yorkers---more than the entire population of Los Angeles---live in census tracts with no ADA-accessible subway station within a 10-minute walk. This figure represents 55% of the city's residents. The problem is not uniformly distributed: Queens alone accounts for 1,752,073 residents in gap tracts, and Staten Island, while smaller in absolute numbers, has only 9% tract coverage. Manhattan, with 77% coverage, is the exception rather than the rule.

The reliability analysis introduces a dimension largely absent from prior accessibility research. Nominal ADA designation does not guarantee functional access. Of the 157 accessible stations, 49 operated below 95% elevator uptime over the 12-month observation window, with several major stations---including 59 St-Columbus Circle (0.0% uptime), 42 St-Port Authority Bus Terminal (13.6%), and 34 St-Herald Square (51.3%)---effectively or partially inaccessible for extended periods. When coverage is weighted by actual elevator reliability, Manhattan drops from 77% to 71%. The implication is clear: capital investment in ADA station upgrades without matching investment in elevator maintenance creates a gap between official accessibility statistics and the lived experience of disabled riders.

### 5.2 Connections to Prior Research

The finding that Queens is the most underserved borough corroborates Baghestani et al. (2024), who identified Queens as a pronounced outlier in subway accessibility using an independent methodology (gravity index with service frequency weighting). Where that study focused on spatial and racial dimensions of *service quality*, the present analysis focuses on *physical access*---whether a station can be entered at all by someone who cannot use stairs. The convergence of findings across different accessibility constructs strengthens the conclusion that Queens faces compounding transit disadvantages: fewer stations, less frequent service, *and* less ADA infrastructure.

The spatial clustering detected by Moran's *I* aligns with the "transit desert" concept advanced by Zhang et al. (2024), who found that economically disadvantaged neighborhoods in the New York metropolitan area were more likely to fall in transit deserts. The present results extend this finding by showing that accessibility gaps are not only associated with demographic disadvantage at the tract level (*R*² = .202) but are also geographically clustered (*I* = .23 for gap scores), suggesting that entire corridors of the city---not just isolated tracts---are systematically underserved.

The treatment-control balance check provides tentative evidence that the MTA's Capital Program is directing ADA upgrades toward higher-need tracts: treatment tracts have modestly but significantly higher disability rates and poverty rates than control tracts. This is directionally correct for vertical equity. The sourced upgrade timeline---covering 101 of 157 accessible stations with dates traced to MTA press releases, Capital Program records, and news coverage---lends greater credibility to this finding than the previously synthetic timeline, though the 56 stations with approximate dates introduce residual uncertainty in treatment timing.

### 5.3 Limitations and Skepticism

Several features of this analysis warrant explicit skepticism.

**The Euclidean catchment overstates coverage.** An 800 m straight-line radius does not account for the realities of urban walking: street network detours, elevation changes, construction barriers, or the absence of curb cuts. For a wheelchair user navigating a neighborhood with poor sidewalk infrastructure, the effective walking radius may be substantially less than 800 m. Our coverage estimates should therefore be interpreted as upper bounds.

**The ACS data are stale.** The 2023 five-year ACS estimates reflect survey data collected between 2019 and 2023. As of April 2026, these data are at least three years old. Post-pandemic demographic shifts---including changes in disability prevalence, poverty rates, and residential mobility patterns---may have altered the spatial distribution of need in ways not captured here.

**The upgrade timeline is partially approximate.** Of the 157 accessible stations, 101 have upgrade years sourced from official MTA announcements, press releases, and documented construction completions spanning 1987--2026. The remaining 56---primarily Key Station Program stations from the 1990s--2010s---use approximate dates because per-station completion records were not publicly available. A FOIL request to the MTA for the complete Key Station Program schedule would close this gap and enable fully credible causal identification. The panel is substantially more reliable than a fully synthetic timeline but should not yet be treated as definitive for the ~36% of stations with approximate dates.

**The panel lacks an outcome variable.** The current panel contains treatment indicators and demographic covariates but no outcome variable such as transit ridership, property values, or population change. Defining and linking an appropriate outcome is a prerequisite for DiD estimation.

**The 800 m catchment may be too generous for the target population.** The 80 m/min walking speed assumption reflects an average pedestrian; for individuals with mobility impairments---the population most affected by ADA inaccessibility---effective walking speed and tolerable distance are likely lower. A sensitivity analysis using 400 m and 600 m catchment radii would provide more conservative estimates.

**Centroid-based coverage is a spatial simplification.** A tract classified as "covered" because its centroid falls within 800 m of a station may contain residents who live well beyond walking distance. Area-weighted or population-weighted coverage measures would improve precision.

**Equal weighting of need score components is arbitrary.** The need score assigns equal weight to disability, senior, and poverty rates. Alternative weighting schemes---for example, weighting disability more heavily on the grounds that wheelchair users face the most absolute barrier---would change tract rankings and gap scores. The choice of equal weights should be understood as a baseline, not as a normative claim about the relative importance of each demographic dimension.

**OLS standard errors are likely underestimated.** The significant Moran's *I* values for gap score, need score, and disability rate indicate spatial dependence that violates the OLS independence assumption. While HC1 robust standard errors address heteroskedasticity, they do not correct for spatial autocorrelation. Spatial HAC standard errors (Conley, 1999) or a spatial regression model would provide more reliable inference. The *R*² of .202 and the regression coefficients should be interpreted with this caveat in mind.

### 5.4 Policy Implications for 2026

These findings arrive at a consequential moment for New York City transit policy. The Manhattan congestion pricing program, which began charging tolls in June 2024, generates revenue earmarked for MTA capital improvements. If ADA station upgrades are not prioritized within this funding stream, congestion pricing risks deepening the accessibility divide: drivers who cannot use the subway because of physical barriers are charged for driving without gaining a viable transit alternative.

The MTA's 2025--2029 Capital Plan represents the next opportunity for accelerated ADA investment. The pace of 67 stations over a five-year capital cycle, while historically unprecedented, would still leave the majority of the system inaccessible for decades. At the current rate (approximately 13 stations per year), full system accessibility would not be achieved until the mid-2050s. Meanwhile, the reliability data suggest that stations already upgraded are not being maintained at levels that ensure functional access---a pattern that, if it persists, will erode the gains of new capital investment.

The spatial clustering of accessibility gaps has a direct policy implication: geographically targeted investment in high-gap corridors---particularly in southeastern Queens, central Brooklyn, and the northern Bronx---would yield greater coverage gains per dollar than a spatially uniform upgrade schedule. The Moran's *I* results confirm that these gaps are not random but form identifiable geographic patterns amenable to targeted intervention.

Federal ADA enforcement remains relevant. While the MTA has historically operated under a negotiated "key station" standard, advocacy organizations have increasingly challenged the adequacy of this approach. A 2022 settlement required the MTA to make 95% of stations accessible by 2055---a timeline that the present analysis suggests is at risk given current elevator reliability performance.

### 5.5 Future Research

Several extensions would strengthen the present analysis:

1. **Network distance.** Replace Euclidean catchments with street-network walking distances computed via OpenStreetMap (OSMnx; Boeing, 2017) to produce more realistic coverage estimates.
2. **Complete upgrade dates.** The current timeline covers 101 of 157 stations with sourced dates. A FOIL request to the MTA for Key Station Program completion records would close the remaining 56-station gap and enable fully credible DiD estimation.
3. **Multi-vintage ACS data.** Fetch actual multi-year ACS vintages (e.g., 2017--2023) via the Census Bureau API to introduce genuine temporal variation in demographic covariates.
4. **Local spatial association.** Compute Local Indicators of Spatial Association (LISA; Anselin, 1995) to identify specific hot spots and cold spots of accessibility gaps at the tract level.
5. **Geographically weighted regression.** Estimate spatially varying coefficients (GWR; Fotheringham et al., 2002) to identify neighborhoods where the gap-demographics relationship is strongest.
6. **Outcome variables.** Link the panel to ridership data (MTA turnstile counts), property values (NYC ACRIS), or population change (ACS inter-censal estimates) to estimate the causal effect of ADA upgrades on neighborhood outcomes.
7. **First-and-last-mile analysis.** Incorporate curb cut data, sidewalk condition ratings, and pedestrian infrastructure quality to assess whether the path *to* an accessible station is itself accessible.


## References

Anselin, L. (1995). Local indicators of spatial association---LISA. *Geographical Analysis*, *27*(2), 93--115. https://doi.org/10.1111/j.1538-4632.1995.tb00338.x

Baghestani, A., Nikbakht, M., Kucheva, Y., & Afshar, A. (2024). Assessing spatial and racial equity of subway accessibility: Case study of New York City. *Cities*, *155*, 105489. https://doi.org/10.1016/j.cities.2024.105489

Bartzokas-Tsiompras, A., & Photis, Y. N. (2019). Measuring rapid transit accessibility and equity in migrant communities across 17 European cities. *International Journal of Transport Development and Integration*, *3*(3), 245--258.

Berjisian, E., & Habibian, M. (2017). Walking accessibility: Gravity-based versus utility-based measurement. *Proceedings of the Transportation Research Board 96th Annual Meeting*, Washington, DC.

Boeing, G. (2017). OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks. *Computers, Environment and Urban Systems*, *65*, 126--139. https://doi.org/10.1016/j.compenvurbsys.2017.05.004

bunten, d. m., Fu, E., Rolheiser, L., & Severen, C. (2023). The problem has existed over endless years: Racialized difference in commuting, 1980--2019. *Journal of Urban Economics*, *138*, 103602. https://doi.org/10.1016/j.jue.2023.103602

Cohen, J. (1988). *Statistical power analysis for the behavioral sciences* (2nd ed.). Lawrence Erlbaum Associates.

Conley, T. G. (1999). GMM estimation with cross sectional dependence. *Journal of Econometrics*, *92*(1), 1--45. https://doi.org/10.1016/S0304-4076(98)00084-0

Delbosc, A., & Currie, G. (2011). Using Lorenz curves to assess public transport equity. *Journal of Transport Geography*, *19*(6), 1252--1259. https://doi.org/10.1016/j.jtrangeo.2011.02.008

Ding, C., Wang, D., Liu, C., Zhang, Y., & Yang, J. (2018). Exploring the influence of built environment on travel mode choice considering the mediating effects of car ownership and travel distance. *Transportation Research Part A: Policy and Practice*, *100*, 65--80. https://doi.org/10.1016/j.tra.2017.04.008

El-Geneidy, A., Grimsrud, M., Wasfi, R., Tétreault, P., & Surprenant-Legault, J. (2014). New evidence on walking distances to transit stops: Identifying redundancies and gaps using variable service areas. *Transportation*, *41*(1), 193--210. https://doi.org/10.1007/s11116-013-9508-z

Fotheringham, A. S., Brunsdon, C., & Charlton, M. (2002). *Geographically weighted regression: The analysis of spatially varying relationships*. Wiley.

Giannotti, M., Barros, J., Tomasiello, D. B., Smith, D., Pizzol, B., Santos, B. M., Zhong, C., Shen, Y., Marques, E., & Batty, M. (2021). Inequalities in transit accessibility: Contributions from a comparative study between Global South and North metropolitan regions. *Cities*, *109*, 103016. https://doi.org/10.1016/j.cities.2020.103016

Gu, Y., & Zheng, S. (2024). Residential location responses to new subway stations: Evidence from Shenzhen. *Journal of Urban Economics*, *141*, 103636. https://doi.org/10.1016/j.jue.2024.103636

Jeong, H., & Lee, L.-F. (2024). Maximum likelihood estimation of spatial autoregressive models for origin-destination flows. *Journal of Econometrics*, *240*(1), 105668. https://doi.org/10.1016/j.jeconom.2024.105668

Liu, S., & Zhu, X. (2004). Accessibility analyst: An integrated GIS tool for accessibility analysis in urban transportation planning. *Environment and Planning B: Planning and Design*, *31*(1), 105--124. https://doi.org/10.1068/b305

Lucas, K., & Jones, P. (2012). Social impacts and equity issues in transport: An introduction. *Journal of Transport Geography*, *21*, 1--3. https://doi.org/10.1016/j.jtrangeo.2012.01.032

Metropolitan Transportation Authority. (2020a). *MTA annual ridership statistics*. https://new.mta.info/agency/new-york-city-transit/subway-bus-ridership

Metropolitan Transportation Authority. (2020b). *2020--2024 Capital Program: Accessibility*. https://new.mta.info/capital

Metropolitan Transportation Authority. (2024). *Congestion pricing program overview*. https://new.mta.info/congestion-relief-zone

Metropolitan Transportation Authority. (2026). *MTA subway stations dataset* [Data set]. Open Data NY. https://data.ny.gov/Transportation/MTA-Subway-Stations/39hk-dx4f

NYC Council Data Team. (2019). *Accessibility at MTA subway stations*. New York City Council.

Souche, S., Mercier, A., & Ovtracht, N. (2016). The impacts of urban pricing on social and spatial inequalities: The case study of Lyon (France). *Urban Studies*, *53*(2), 373--399. https://doi.org/10.1177/0042098014563484

U.S. Census Bureau. (2024). *American Community Survey 5-year estimates, 2019--2023* [Data set]. https://data.census.gov

Zhang, M., Zhao, P., & Qiao, S. (2024). Transit deserts and gentrification in the New York metropolitan area. *Transportation Research Record*, *2678*(4), 345--358.


## Appendix A. Factor Pipeline Architecture

All accessibility classification in this study runs through the `subway_access.factors` system, a composable pipeline inspired by Quantopian's Zipline framework. Built-in factors---`NeedScoreFactor`, `CoverageFactor`, `GapScoreFactor`, `NearestStationDistanceFactor`, `StationCountFactor`, and `ReliabilityWeightedCoverageFactor`---are composed into a `Pipeline` object that evaluates every factor for every census tract in a single pass:

```python
from subway_access.factors import Pipeline, NeedScoreFactor, CoverageFactor

pipe = Pipeline().add(NeedScoreFactor()).add(CoverageFactor())
result = pipe.run(contexts)   # one pass over all tracts
result.to_records()            # tuple of dicts
result.to_dataframe()          # pandas DataFrame (optional dependency)
```

Custom factors can be added by subclassing `Factor` and implementing `compute(context) -> value`. The pipeline applies every registered factor to every tract and returns a columnar result set.

## Appendix B. Panel Dataset Schema

Each row in `artifacts/panel-dataset.csv` represents a single tract-year observation:

| Column | Type | Description |
| :--- | :--- | :--- |
| `unit_id` | str | Census tract GEOID |
| `period` | str | ACS vintage year (2017--2023) |
| `has_accessible_station` | bool | Treatment indicator |
| `treatment_year` | int | Year first accessible station opened in catchment |
| `disability_rate` | float | ACS estimate |
| `senior_rate` | float | ACS estimate |
| `poverty_rate` | float | ACS estimate |
| `total_population` | int | ACS estimate |
| `accessible_station_count` | int | Number of ADA stations within 800 m catchment |
| `nearest_accessible_distance_m` | float | Haversine distance to nearest ADA station (meters) |
| `need_score` | float | mean(disability_rate, senior_rate, poverty_rate) |

## Appendix C. Supplementary Analyses

The following supplementary reports provide full diagnostic detail:

- [Correlation analysis](reports/supplementary/correlation-analysis.md) --- Pearson and Spearman matrices with significance levels, variance inflation factors, bivariate scatter plots, and OLS equity regression with robust standard errors.
- [Model specification](reports/supplementary/model-specification.md) --- Full DiD and SAR panel equations, identifying assumptions, balance tests with *t*-statistics and *P*-values, and distribution diagnostics.
- [Spatial diagnostics](reports/supplementary/spatial-diagnostics.md) --- Spatial weights matrix properties, Global Moran's *I* with *z*-scores and permutation *P*-values, bivariate geographic comparison maps, and recommendations for LISA and GWR extensions.
- [Engine audit](reports/supplementary/engine-audit.md) --- Auto-generated cross-check of the headline results against five [`factor-factory`](https://github.com/random-walks/factor-factory) engine fits. See Appendix D for methodology.


## Appendix D. Engine Audit (factor-factory cross-check)

This appendix is an **auto-generated cross-check**, not a replacement for the primary results. When the optional `[factor-factory]` + `[tearsheets]` extras are installed, `main.py` re-runs the analysis through the [`factor-factory`](https://github.com/random-walks/factor-factory) engine registry and writes a jellycell tearsheet. The goal is registry parity and methodological triangulation: each factor-factory engine implements a peer-reviewed estimator, and directional agreement with the primary analysis (Sections 4.6--4.8) raises confidence in the headline findings; disagreement would surface a specification issue.

The appendix is additive. If the extras are not installed, it is silently skipped and the primary report is unchanged.

### D.1 Design

Five engine fits are produced:

1. **`did.twfe`** --- Two-way fixed-effects DiD on `gap_score` with the existing cohort-based treatment definition. Provides a registry-native re-run of the hand-rolled fixed-effects panel specified in Section 3.5.
2. **`did.sa`** (Sun-Abraham IW, Sun & Abraham 2021) --- Staggered-rollout-robust interaction-weighted estimator. Important here because the ADA upgrade rollout is staggered over 1987--2026 across 101 press-release-sourced stations plus 56 hash-fallback stations. The two-way-fixed-effects DiD is known to be biased under heterogeneous treatment effects with staggered timing (Goodman-Bacon, 2021); the Sun-Abraham estimator provides a robustness check.
3. **`scm.augmented`** (Ben-Michael, Feller & Rothstein, 2021) --- Augmented synthetic control on a single treated tract whose treatment year falls in the interior of the panel window. This is a **single-unit** cross-check: one tract's gap-score trajectory is compared to a synthetic control built from never-treated tracts. The SCM is not meant to substitute for the panel DiD but to show the post-treatment trajectory of one well-sourced upgrade explicitly.
4. **`rdd.rd_robust`** (Calonico, Cattaneo & Titiunik, 2014) --- Regression discontinuity on the `distance_to_nearest_accessible_station` forcing variable at the 800 m threshold. By construction, `gap_score` is zero for covered tracts (those within the 800 m catchment of at least one accessible station) and equals `need_score` for uncovered tracts. An RDD at 800 m with `gap_score` as the outcome therefore detects a mechanical discontinuity of approximately `-mean(need_score)`. This is a **specification check**, not a causal test: a null estimate would indicate catchment-radius drift or a data pipeline bug.
5. **`spatial.morans_i`** --- Global Moran's *I* via the factor-factory spatial registry with KNN spatial weights (*k* = 5). This differs from the 2 km distance-threshold weights used in Section 4.8 of the primary analysis (47.9 mean neighbors), so the *I* point estimate and *z*-score are not expected to match exactly. The audit confirms directional agreement (positive, significant clustering) and registry parity.

### D.2 Interpretation guardrails

Results from this appendix should be read against the following interpretive guidance:

- **Directional agreement is the confirmation target.** The primary analysis (Sections 4.6--4.8) reports specific point estimates under specific spatial-weight and identifying-assumption choices. The engine-audit fits use different (peer-reviewed) specifications --- KNN spatial weights for Moran's *I*, doubly-robust Sun-Abraham IW for DiD, augmented SCM for a single treated tract, `rdrobust` with MSE-optimal bandwidth for RDD. Agreement in sign and significance across specifications is the intended signal.
- **The SCM fit is a single-unit illustration.** It is not a system-wide causal estimate. Use it as a worked example of the pattern, not as a borough- or city-level claim.
- **The RDD fit is mechanical.** See D.1 point 4. Report it to verify the 800 m catchment is consistently applied; do not interpret the point estimate as a causal effect of the boundary on outcomes.
- **The Sun-Abraham fit can contradict TWFE under heterogeneous treatment effects.** If the two disagree, trust Sun-Abraham for the ATT magnitude --- the TWFE estimand becomes an uninterpretable weighted average of cohort-level effects under staggered timing. Document any disagreement in the narrative and flag the heterogeneity-robustness concern.

If any engine fit produces a finding that is **directionally inconsistent** with the primary analysis --- e.g. a positive Moran's *I* is rejected by the registry fit, or the Sun-Abraham ATT has the opposite sign of the TWFE point estimate --- the contributor must **surface the discrepancy** in a PR comment and in this appendix rather than silently updating the primary narrative. Triangulation is only informative if discordant results are reported honestly.

### D.3 Output artifacts

When the engine audit runs successfully, the following artifacts are written:

- `engine-audit/artifacts/did_results.json` --- TWFE + Sun-Abraham point estimates, SEs, 95% CIs, and cohort-level ATTs where available.
- `engine-audit/artifacts/rdd_results.json` --- RDD point estimate, bandwidth, effective sample size.
- `engine-audit/artifacts/scm_results.json` --- Augmented-SCM point estimate with pre/post-period RMSPE, donor weights, and the focal treated tract.
- `engine-audit/artifacts/spatial_results.json` --- Moran's *I*, *z*-score, permutation *p*-value with the KNN(*k* = 5) weights specification.
- `engine-audit/manuscripts/FINDINGS.md` --- Rendered jellycell tearsheet consuming the four JSON files via the shipped `findings.md.j2` template.
- [`reports/supplementary/engine-audit.md`](reports/supplementary/engine-audit.md) --- Compact summary table of all five fits, linked from Appendix C.

### D.4 Reproducibility

Run the full pipeline (including the engine audit) with:

```bash
pip install "subway-access[all,factor-factory,tearsheets]"
cd examples/accessibility-change-over-time
python main.py --skip-download     # assumes cache/ is populated
```

To skip the engine audit even when the extras are installed, pass `--skip-engine-audit`. The primary report numbers (Sections 4.1--4.8, Tables 1--5) are produced entirely by Steps 1--10 of `main.py` and are independent of the engine-audit appendix.

### D.5 Citations

- Sun, L., & Abraham, S. (2021). Estimating dynamic treatment effects in event studies with heterogeneous treatment effects. *Journal of Econometrics*, *225*(2), 175--199. https://doi.org/10.1016/j.jeconom.2020.09.006
- Goodman-Bacon, A. (2021). Difference-in-differences with variation in treatment timing. *Journal of Econometrics*, *225*(2), 254--277. https://doi.org/10.1016/j.jeconom.2021.03.014
- Ben-Michael, E., Feller, A., & Rothstein, J. (2021). The augmented synthetic control method. *Journal of the American Statistical Association*, *116*(536), 1789--1803. https://doi.org/10.1080/01621459.2021.1929245
- Calonico, S., Cattaneo, M. D., & Titiunik, R. (2014). Robust nonparametric confidence intervals for regression-discontinuity designs. *Econometrica*, *82*(6), 2295--2326. https://doi.org/10.3982/ECTA11757
