## 5. Discussion

### 5.1 Summary of Findings

The central finding of this analysis is stark: 4,717,140 New Yorkers---more than the entire population of Los Angeles---live in census tracts with no ADA-accessible subway station within a 10-minute walk. This figure represents 55% of the city's residents. The problem is not uniformly distributed: Queens alone accounts for 1,752,073 residents in gap tracts, and Staten Island, while smaller in absolute numbers, has only 9% tract coverage. Manhattan, with 77% coverage, is the exception rather than the rule.

The reliability analysis introduces a dimension largely absent from prior accessibility research. Nominal ADA designation does not guarantee functional access. Of the 157 accessible stations, 49 operated below 95% elevator uptime over the 12-month observation window, with several major stations---including 59 St-Columbus Circle (0.0% uptime), 42 St-Port Authority Bus Terminal (13.6%), and 34 St-Herald Square (51.3%)---effectively or partially inaccessible for extended periods. When coverage is weighted by actual elevator reliability, Manhattan drops from 77% to 71%. The implication is clear: capital investment in ADA station upgrades without matching investment in elevator maintenance creates a gap between official accessibility statistics and the lived experience of disabled riders.

### 5.2 Connections to Prior Research

The finding that Queens is the most underserved borough corroborates Baghestani et al. (2024), who identified Queens as a pronounced outlier in subway accessibility using an independent methodology (gravity index with service frequency weighting). Where that study focused on spatial and racial dimensions of *service quality*, the present analysis focuses on *physical access*---whether a station can be entered at all by someone who cannot use stairs. The convergence of findings across different accessibility constructs strengthens the conclusion that Queens faces compounding transit disadvantages: fewer stations, less frequent service, *and* less ADA infrastructure.

The spatial clustering detected by Moran's *I* aligns with the "transit desert" concept advanced by Zhang et al. (2024), who found that economically disadvantaged neighborhoods in the New York metropolitan area were more likely to fall in transit deserts. The present results extend this finding by showing that accessibility gaps are not only associated with demographic disadvantage at the tract level (*R*² = .202) but are also geographically clustered (*I* = .23 for gap scores), suggesting that entire corridors of the city---not just isolated tracts---are systematically underserved.

The treatment-control balance check provides tentative evidence that the MTA's Capital Program is directing ADA upgrades toward higher-need tracts: treatment tracts have modestly but significantly higher disability rates (*d* = 0.27) and poverty rates (*d* = 0.29) than control tracts. This is directionally correct for vertical equity, though the effect sizes are small and the simulated upgrade timeline prevents causal attribution.

### 5.3 Limitations and Skepticism

Several features of this analysis warrant explicit skepticism.

**The Euclidean catchment overstates coverage.** An 800 m straight-line radius does not account for the realities of urban walking: street network detours, elevation changes, construction barriers, or the absence of curb cuts. For a wheelchair user navigating a neighborhood with poor sidewalk infrastructure, the effective walking radius may be substantially less than 800 m. Our coverage estimates should therefore be interpreted as upper bounds.

**The ACS data are stale.** The 2023 five-year ACS estimates reflect survey data collected between 2019 and 2023. As of April 2026, these data are at least three years old. Post-pandemic demographic shifts---including changes in disability prevalence, poverty rates, and residential mobility patterns---may have altered the spatial distribution of need in ways not captured here.

**The simulated upgrade timeline is the critical methodological weakness.** The DiD panel is specified but not causally interpretable because station ADA upgrade years are hash-derived from current status rather than from actual MTA Capital Program records. Real upgrade dates---obtainable via Freedom of Information Law (FOIL) requests or the MTA's capital dashboard---are necessary for credible causal identification. Without them, the panel demonstrates the analytical framework but cannot estimate the actual effect of gaining an accessible station.

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
2. **Actual upgrade dates.** Obtain real MTA Capital Program station upgrade dates via FOIL request to enable credible DiD estimation with causally interpretable treatment effects.
3. **Multi-vintage ACS data.** Fetch actual multi-year ACS vintages (e.g., 2017--2023) via the Census Bureau API to introduce genuine temporal variation in demographic covariates.
4. **Local spatial association.** Compute Local Indicators of Spatial Association (LISA; Anselin, 1995) to identify specific hot spots and cold spots of accessibility gaps at the tract level.
5. **Geographically weighted regression.** Estimate spatially varying coefficients (GWR; Fotheringham et al., 2002) to identify neighborhoods where the gap-demographics relationship is strongest.
6. **Outcome variables.** Link the panel to ridership data (MTA turnstile counts), property values (NYC ACRIS), or population change (ACS inter-censal estimates) to estimate the causal effect of ADA upgrades on neighborhood outcomes.
7. **First-and-last-mile analysis.** Incorporate curb cut data, sidewalk condition ratings, and pedestrian infrastructure quality to assess whether the path *to* an accessible station is itself accessible.
