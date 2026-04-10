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
| `period` | str | Simulated ACS vintage year (2017--2023) |
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
