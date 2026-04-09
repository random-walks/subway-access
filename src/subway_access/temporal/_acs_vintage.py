"""Multi-vintage ACS fetching for panel data construction."""

from __future__ import annotations

import json
from urllib.request import urlopen

NYC_COUNTY_CODES = ("005", "047", "061", "081", "085")

_ACS_COUNTS_VARIABLES = (
    "NAME",
    "B01003_001E",
    "B01001_020E",
    "B01001_021E",
    "B01001_022E",
    "B01001_023E",
    "B01001_024E",
    "B01001_025E",
    "B01001_044E",
    "B01001_045E",
    "B01001_046E",
    "B01001_047E",
    "B01001_048E",
    "B01001_049E",
)
_ACS_SUBJECT_VARIABLES = (
    "NAME",
    "S1810_C02_001E",
    "S1701_C02_001E",
)
_SENIOR_VARIABLES = _ACS_COUNTS_VARIABLES[2:]

# Available ACS 5-year vintage years (each covers a 5-year window ending in that year).
AVAILABLE_VINTAGE_YEARS: tuple[int, ...] = (2017, 2018, 2019, 2020, 2021, 2022, 2023)


def _read_census_rows(url: str) -> tuple[list[str], list[list[str]]]:
    with urlopen(url, timeout=30.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list) or not payload:
        message = f"Expected a tabular Census API payload from {url!r}."
        raise TypeError(message)
    header = payload[0]
    if not isinstance(header, list):
        message = f"Expected the first Census API row to be a header list for {url!r}."
        raise TypeError(message)
    rows = [row for row in payload[1:] if isinstance(row, list)]
    return [str(value) for value in header], [
        [str(value) for value in row] for row in rows
    ]


def _counts_url(county_code: str, *, year: int) -> str:
    variables = ",".join(_ACS_COUNTS_VARIABLES)
    return (
        f"https://api.census.gov/data/{year}/acs/acs5"
        f"?get={variables}"
        f"&for=tract:*&in=state:36+county:{county_code}"
    )


def _subject_url(county_code: str, *, year: int) -> str:
    variables = ",".join(_ACS_SUBJECT_VARIABLES)
    return (
        f"https://api.census.gov/data/{year}/acs/acs5/subject"
        f"?get={variables}"
        f"&for=tract:*&in=state:36+county:{county_code}"
    )


def _as_int(raw_value: str) -> int:
    return int(raw_value)


def _as_percent(raw_value: str) -> float:
    return float(raw_value) / 10_000.0


def fetch_acs_tract_estimates_for_year(
    year: int,
    *,
    tract_geoids: tuple[str, ...] | None = None,
) -> dict[str, dict[str, object]]:
    """Fetch ACS tract-level estimates for a specific vintage year.

    Args:
        year: ACS 5-year vintage year (e.g. 2020).
        tract_geoids: Optional tuple of tract GEOIDs to filter to.
            If None, fetches all NYC tracts.

    Returns:
        Mapping of tract GEOID to estimate dict with keys: tract_id,
        tract_name, total_population, senior_rate, poverty_rate,
        disability_rate.

    Example:
        >>> estimates = fetch_acs_tract_estimates_for_year(2020)
        >>> len(estimates)
        2168
    """

    requested_geoids = set(tract_geoids or ())
    county_codes = (
        sorted({geoid[2:5] for geoid in requested_geoids})
        if requested_geoids
        else list(NYC_COUNTY_CODES)
    )
    estimates: dict[str, dict[str, object]] = {}

    for county_code in county_codes:
        count_header, count_rows = _read_census_rows(
            _counts_url(county_code, year=year)
        )
        subject_header, subject_rows = _read_census_rows(
            _subject_url(county_code, year=year)
        )
        subject_lookup = {
            f"{row[subject_header.index('state')]}{row[subject_header.index('county')]}{row[subject_header.index('tract')]}": row
            for row in subject_rows
        }

        for row in count_rows:
            row_map = {name: row[index] for index, name in enumerate(count_header)}
            geoid = f"{row_map['state']}{row_map['county']}{row_map['tract']}"
            if requested_geoids and geoid not in requested_geoids:
                continue
            subject_row = subject_lookup.get(geoid)
            if subject_row is None:
                continue
            subject_map = {
                name: subject_row[index] for index, name in enumerate(subject_header)
            }
            total_population = _as_int(row_map["B01003_001E"])
            senior_population = sum(
                _as_int(row_map[name]) for name in _SENIOR_VARIABLES
            )
            estimates[geoid] = {
                "tract_id": geoid,
                "tract_name": row_map["NAME"],
                "total_population": total_population,
                "senior_rate": 0.0
                if total_population == 0
                else senior_population / total_population,
                "poverty_rate": _as_percent(subject_map["S1701_C02_001E"]),
                "disability_rate": _as_percent(subject_map["S1810_C02_001E"]),
            }

    return estimates


def fetch_multi_vintage_estimates(
    years: tuple[int, ...] | None = None,
    *,
    tract_geoids: tuple[str, ...] | None = None,
) -> dict[int, dict[str, dict[str, object]]]:
    """Fetch ACS estimates for multiple vintage years.

    Args:
        years: Tuple of vintage years to fetch. Defaults to all available.
        tract_geoids: Optional tuple of tract GEOIDs to filter to.

    Returns:
        Nested mapping: year -> tract_geoid -> estimate dict.

    Example:
        >>> multi = fetch_multi_vintage_estimates(years=(2019, 2020, 2021))
        >>> sorted(multi.keys())
        [2019, 2020, 2021]
    """

    vintage_years = years or AVAILABLE_VINTAGE_YEARS
    result: dict[int, dict[str, dict[str, object]]] = {}
    for year in vintage_years:
        result[year] = fetch_acs_tract_estimates_for_year(
            year, tract_geoids=tract_geoids
        )
    return result
