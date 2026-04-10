# Spatial Diagnostics

*Auto-generated: April 10, 2026*

## Spatial weights matrix

| Property | Value |
| :--- | ---: |
| Units | 2,317 |
| Distance threshold | 2,000 m |
| Units with neighbors | 2,315 |
| Islands (no neighbors) | 2 |
| Mean neighbors | 47.9 |
| Min neighbors | 0 |
| Max neighbors | 86 |
| Median neighbors | 51 |

Row-standardized distance-based weights: each unit's neighbors (within 2 km) receive equal weight summing to 1. Units with no neighbors (islands) are excluded from spatial analysis.

## Global Moran's I

Moran's I tests whether a variable is spatially clustered (I > E[I]) or dispersed (I < E[I]). Under the null hypothesis of spatial randomness, I converges to E[I] = -1/(N-1).

| Variable | Moran's I | E[I] | z-score | p-value | |
| :--- | ---: | ---: | ---: | ---: | :--- |
| Gap Score | 0.2271 | -0.0004 | 40.87 | 0.001 | ** |
| Need Score | 0.1991 | -0.0004 | 33.91 | 0.001 | ** |
| Disability Rate | 0.2757 | -0.0004 | 48.92 | 0.001 | ** |

**Interpretation:** Statistically significant spatial autocorrelation detected. Key variables are not randomly distributed across space -- similar values cluster together. This has two implications:

1. **For the DiD model:** Standard errors may be underestimated if spatial dependence is ignored. The SAR panel extension or spatial HAC standard errors should be used.
2. **For policy:** The clustering suggests that accessibility gaps are concentrated in specific neighborhoods, not uniformly distributed. Targeted investment in these clusters would be more efficient than system-wide uniform upgrades.

## Bivariate geographic comparison

![Figure 14](../figures/figure-14-gap-vs-poverty-map.png)

Side-by-side maps allow visual comparison of gap score spatial distribution (left) with poverty rate (right). Where both are dark, high-poverty neighborhoods also lack accessible transit.

![Figure 15](../figures/figure-15-gap-vs-disability-map.png)

Gap score vs disability rate. Where gap scores are high in tracts with high disability prevalence, the equity burden is most acute.

## Future work

- **Local indicators of spatial association (LISA):** Identify specific clusters of high-gap / high-need tracts using local Moran's I. Requires `esda` package.
- **Spatial lag model estimation:** Estimate the SAR panel with `spreg` or `pysal` once a suitable outcome variable is available.
- **Geographically weighted regression (GWR):** Allow coefficients to vary across space to identify neighborhoods where the gap-demographics relationship is strongest.

