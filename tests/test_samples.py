from __future__ import annotations

from subway_access import samples


def test_sample_loaders_return_packaged_datasets() -> None:
    assert len(samples.load_sample_stations().stations) == 3
    assert len(samples.load_sample_accessibility().statuses) == 3
    assert len(samples.load_sample_demographics().tracts) == 4
    assert len(samples.load_sample_outages().records) == 3
    assert len(samples.load_sample_pedestrian_network().connections) == 3
