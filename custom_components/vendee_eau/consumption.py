"""Consumption helpers for Vendee Eau."""

from __future__ import annotations

import re
from typing import Any


def consumption_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return official consumption rows from the Vendee Eau chart payload."""
    labels = payload.get("labels")
    datasets = payload.get("datasets")

    if not isinstance(labels, list) or not isinstance(datasets, list):
        return []

    dataset = next(
        (
            item
            for item in datasets
            if isinstance(item, dict) and isinstance(item.get("data"), list)
        ),
        None,
    )
    if dataset is None:
        return []

    values = dataset["data"]
    dataset_label = dataset.get("label")
    return [
        {
            "date": _clean_reading_label(labels[index]),
            "value": values[index],
            "label": dataset_label,
        }
        for index in range(min(len(labels), len(values)))
    ]


def latest_consumption(payload: dict[str, Any]) -> int | float | None:
    """Return latest official consumption value."""
    rows = consumption_rows(payload)
    if not rows:
        return None
    value = rows[-1].get("value")
    return value if isinstance(value, (int, float)) else None


def latest_consumption_date(payload: dict[str, Any]) -> str | None:
    """Return latest official consumption reading date."""
    rows = consumption_rows(payload)
    if not rows:
        return None
    value = rows[-1].get("date")
    return str(value) if value is not None else None


def consumption_points_count(payload: dict[str, Any]) -> int:
    """Return number of official consumption points."""
    return len(consumption_rows(payload))


def consumption_total(payload: dict[str, Any]) -> int | float | None:
    """Return total of official consumption values exposed by the portal."""
    values = [
        row.get("value")
        for row in consumption_rows(payload)
        if isinstance(row.get("value"), (int, float))
    ]
    if not values:
        return None
    return sum(values)


def _clean_reading_label(value: Any) -> str:
    """Return a display-friendly official reading label."""
    return re.sub(r"\s*\([A-Z]\)\s*$", "", str(value)).strip()
