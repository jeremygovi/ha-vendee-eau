"""Tests for Vendee Eau consumption parsing."""

from __future__ import annotations

import importlib.util
from pathlib import Path

CONSUMPTION_PATH = (
    Path(__file__).parents[1] / "custom_components" / "vendee_eau" / "consumption.py"
)
spec = importlib.util.spec_from_file_location("vendee_eau_consumption", CONSUMPTION_PATH)
assert spec is not None
consumption = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(consumption)

consumption_points_count = consumption.consumption_points_count
consumption_rows = consumption.consumption_rows
consumption_total = consumption.consumption_total
latest_consumption = consumption.latest_consumption
latest_consumption_date = consumption.latest_consumption_date


def test_consumption_helpers_parse_vendee_eau_chart_payload() -> None:
    """The official chart payload is parsed into dated consumption rows."""
    payload = {
        "Id": 0,
        "labels": ["01/11/2023 (R)", "31/01/2024 (R)", "02/02/2024 (R)"],
        "datasets": [
            {
                "Id": 0,
                "label": "Consommation EAU",
                "data": [48, 27, 0],
            }
        ],
        "graphWidth": 0,
    }

    assert consumption_rows(payload) == [
        {"date": "01/11/2023", "value": 48, "label": "Consommation EAU"},
        {"date": "31/01/2024", "value": 27, "label": "Consommation EAU"},
        {"date": "02/02/2024", "value": 0, "label": "Consommation EAU"},
    ]
    assert latest_consumption(payload) == 0
    assert latest_consumption_date(payload) == "02/02/2024"
    assert consumption_points_count(payload) == 3
    assert consumption_total(payload) == 75


def test_consumption_helpers_handle_empty_payload() -> None:
    """Empty or unexpected payloads do not crash sensors."""
    payload = {}

    assert consumption_rows(payload) == []
    assert latest_consumption(payload) is None
    assert latest_consumption_date(payload) is None
    assert consumption_points_count(payload) == 0
    assert consumption_total(payload) is None
