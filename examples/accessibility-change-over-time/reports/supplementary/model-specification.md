# Model Specification

*Auto-generated: April 9, 2026*

This supplementary report details the difference-in-differences (DiD) panel model specification, its identifying assumptions, and pre-estimation diagnostics.

## Difference-in-differences specification

```
Y_it = alpha + beta * Treatment_it + gamma * X_it + delta_i + tau_t + epsilon_it
```

| Symbol | Description |
| :--- | :--- |
| Y_it | Outcome: population change, demographic composition, or housing cost |
| Treatment_it | 1 if tract *i* has an accessible station by period *t* |
| X_it | Time-varying covariates: disability rate, senior rate, poverty rate |
| delta_i | Tract fixed effects (absorb time-invariant tract characteristics) |
| tau_t | Period fixed effects (absorb city-wide trends) |
| beta | **Causal estimate:** effect of gaining an accessible station |

## Identifying assumptions

### 1. Parallel trends

In the absence of treatment, treated and control tracts would have followed the same outcome trajectory. This is the core identifying assumption of DiD. It cannot be directly tested, but pre-treatment outcome trends should be parallel.

**Status:** Cannot be verified with the current simulated upgrade timeline. With real MTA Capital Program upgrade dates, plot pre-treatment outcome trends for treatment vs control groups to visually assess parallelism.

### 2. No anticipation

Units do not change behavior in anticipation of treatment. Since ADA station upgrades are infrastructure projects announced years in advance, this assumption could be violated if households sort based on announced plans.

### 3. SUTVA (Stable Unit Treatment Value Assumption)

One unit's treatment does not affect another unit's outcome. Spatial spillovers (e.g., a new accessible station increasing property values in adjacent tracts) could violate SUTVA. The SAR extension below addresses this.

## Balance check with hypothesis tests

| Variable | Treatment | Control | Diff | Cohen's d | t-stat | p-value | |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| Disability rate | 0.0484 | 0.0389 | +0.0095 | 0.270 | 6.22 | < 0.001 | *** |
| Senior rate | 0.1512 | 0.1623 | -0.0111 | -0.133 | -3.16 | 0.002 | ** |
| Poverty rate | 0.0739 | 0.0555 | +0.0184 | 0.292 | 6.75 | < 0.001 | *** |
| Need score | 0.0912 | 0.0856 | +0.0056 | 0.136 | 3.18 | 0.001 | ** |

**Welch's t-test** (unequal variance) used for all comparisons. Cohen's d: |d| < 0.2 = negligible, 0.2-0.5 = small, 0.5-0.8 = medium, > 0.8 = large.

## Distribution diagnostics

| Statistic | Need score | Distance (m) | Gap score |
| :--- | ---: | ---: | ---: |
| N | 2,317 | 2,317 | 1,346 |
| Mean | 0.0878 | 1353 | 0.0900 |
| Median | 0.0849 | 995 | 0.0853 |
| Std dev | 0.0411 | 1255 | 0.0367 |
| Skewness | 0.73 | 2.31 | 1.34 |
| Kurtosis (excess) | 2.41 | 6.12 | 4.24 |
| Jarque-Bera | 769.9 (p < 0.001) | 5672.3 (p < 0.001) | 1408.2 (p < 0.001) |
| Min | 0.0000 | 20 | 0.0001 |
| Max | 0.3336 | 8499 | 0.3336 |

## Spatial autoregressive (SAR) extension

```
Y_it = rho * W * Y_it + beta * X_it + delta_i + tau_t + epsilon_it
```

Where *W* is the row-standardized distance-based spatial weights matrix (2,317 units, 2,315 with neighbors, mean 47.9 neighbors, 2 km threshold).

If significant spatial autocorrelation is detected (see [spatial diagnostics](./spatial-diagnostics.md)), the SAR model should be preferred over standard DiD to avoid biased coefficients.

## Limitations of current panel

- **Simulated upgrade timeline:** Station ADA upgrade years are hash-derived from current ADA status, not from actual MTA Capital Program records. This means the treatment assignment is artificial and **DiD coefficients would not be causally interpretable**.
- **Repeated demographics:** ACS estimates are repeated across vintage years (the same 2023 estimates appear in all periods). Production use should fetch actual multi-vintage ACS data via `fetch_multi_vintage_estimates()`.
- **No outcome variable:** The panel currently has treatment indicators and covariates but no outcome variable (e.g., property values, transit ridership, population change). Defining the outcome requires linking to additional data sources.
