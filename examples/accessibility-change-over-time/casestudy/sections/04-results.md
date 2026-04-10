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

The simulated temporal panel shows coverage expanding from 8.4% of tracts in 2017 (195 tracts, 860,421 residents) to 39.2% in 2023 (908 tracts, 3,824,813 residents), representing the modeled rollout of ADA upgrades over seven periods (see [Table 4](reports/accessibility-change-report.md#table-4-coverage-progression); [Figure 6](reports/figures/figure-6-coverage-progression.png)). The progression is monotonically increasing by construction, as stations do not lose ADA status once upgraded. While the trajectory illustrates the pace of coverage expansion, the simulated nature of the upgrade timeline limits inference about actual historical trends.

### 4.5 Treatment-Control Balance

Welch's *t*-tests (unequal variance) comparing treatment (*n* = 908) and control (*n* = 1,409) tracts reveal statistically significant differences across all four demographic indicators:

- **Disability rate:** Treatment *M* = .048, Control *M* = .039, difference = +.010, *t* = 6.22, *P* < .001, Cohen's *d* = 0.27 (small).
- **Senior rate:** Treatment *M* = .151, Control *M* = .162, difference = −.011, *t* = −3.16, *P* = .002, Cohen's *d* = −0.13 (negligible).
- **Poverty rate:** Treatment *M* = .074, Control *M* = .056, difference = +.018, *t* = 6.75, *P* < .001, Cohen's *d* = 0.29 (small).
- **Need score:** Treatment *M* = .091, Control *M* = .086, difference = +.006, *t* = 3.18, *P* = .001, Cohen's *d* = 0.14 (negligible).

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
