"""Core abstractions for the composable factor pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ..models import (
        CatchmentDataset,
        StationDataset,
        TractDemographics,
    )


@dataclass(frozen=True, slots=True)
class FactorContext:
    """Row-level context passed to each Factor during pipeline execution.

    Args:
        tract: Demographic summary for the tract being evaluated.
        stations: All stations in the study area.
        catchments: Generated catchment geometries for all stations.
        extras: Extensible slot for external data (housing costs, etc.).

    Example:
        >>> ctx = FactorContext(tract=tract, stations=stations, catchments=catchments)
        >>> factor.compute(ctx)
        0.42
    """

    tract: TractDemographics
    stations: StationDataset
    catchments: CatchmentDataset
    extras: dict[str, Any] | None = None


class Factor(ABC):
    """Base class for a single computed column in the accessibility pipeline.

    Subclass this and implement ``compute`` to create custom factors.
    Each factor produces one value per tract when the pipeline runs.

    Attributes:
        name: Column name for this factor in pipeline output.
        dtype: Data type of the computed value.

    Example:
        >>> class MyFactor(Factor):
        ...     name = "my_metric"
        ...     dtype = "float"
        ...     def compute(self, context: FactorContext) -> float:
        ...         return context.tract.disability_rate * 2
    """

    name: str
    dtype: Literal["float", "str", "bool", "int"]

    @abstractmethod
    def compute(self, context: FactorContext) -> float | str | bool | int:
        """Compute this factor's value for a single tract.

        Args:
            context: Row-level context with tract demographics, stations,
                catchments, and optional external data.

        Returns:
            The computed value for this tract.
        """


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Output of a Pipeline run -- one column per factor, one row per tract.

    Args:
        columns: Mapping of factor name to tuple of computed values.
        tract_ids: Tuple of tract identifiers, one per row.

    Example:
        >>> result = pipeline.run(contexts)
        >>> result.columns["need_score"]
        (0.12, 0.34, 0.56)
    """

    columns: dict[str, tuple[Any, ...]]
    tract_ids: tuple[str, ...]

    def to_records(self) -> tuple[dict[str, Any], ...]:
        """Convert to a tuple of row dicts.

        Returns:
            One dict per tract with tract_id plus all factor columns.
        """

        records: list[dict[str, Any]] = []
        for i, tract_id in enumerate(self.tract_ids):
            row: dict[str, Any] = {"tract_id": tract_id}
            for col_name, values in self.columns.items():
                row[col_name] = values[i]
            records.append(row)
        return tuple(records)

    def to_dataframe(self) -> Any:
        """Convert to a pandas DataFrame.

        Returns:
            A DataFrame with tract_id index and one column per factor.

        Raises:
            ImportError: If pandas is not installed.
        """

        try:
            import pandas as pd
        except ImportError as exc:
            message = (
                "pandas is required for to_dataframe(). "
                "Install it with: pip install subway-access[panel]"
            )
            raise ImportError(message) from exc

        data = {"tract_id": self.tract_ids, **self.columns}
        return pd.DataFrame(data).set_index("tract_id")


class Pipeline:
    """Composable factor pipeline -- add factors, run across a dataset.

    Pipelines are immutable: ``add`` returns a new Pipeline instance.

    Args:
        factors: Initial tuple of factors.

    Example:
        >>> from subway_access.factors import Pipeline, NeedScoreFactor, CoverageFactor
        >>> pipe = Pipeline().add(NeedScoreFactor()).add(CoverageFactor())
        >>> result = pipe.run(contexts)
    """

    __slots__ = ("_factors",)

    def __init__(self, factors: tuple[Factor, ...] = ()) -> None:
        self._factors = factors

    @property
    def factors(self) -> tuple[Factor, ...]:
        """Return the factors registered in this pipeline."""

        return self._factors

    def add(self, factor: Factor) -> Pipeline:
        """Return a new Pipeline with the given factor appended.

        Args:
            factor: The factor to add.

        Returns:
            A new Pipeline instance containing all previous factors plus this one.
        """

        return Pipeline((*self._factors, factor))

    def run(self, contexts: Iterable[FactorContext]) -> PipelineResult:
        """Execute all factors across the provided contexts.

        Args:
            contexts: One FactorContext per tract to evaluate.

        Returns:
            A PipelineResult with one column per factor and one row per tract.
        """

        context_list = list(contexts)
        tract_ids: list[str] = []
        columns: dict[str, list[Any]] = {f.name: [] for f in self._factors}

        for ctx in context_list:
            tract_ids.append(ctx.tract.tract_id)
            for factor in self._factors:
                columns[factor.name].append(factor.compute(ctx))

        return PipelineResult(
            columns={name: tuple(values) for name, values in columns.items()},
            tract_ids=tuple(tract_ids),
        )
