"""Portal identifier discovery helpers for Vendee Eau."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import json
import re
from urllib.parse import unquote


@dataclass(frozen=True)
class PortalContext:
    """Technical identifiers needed by Vendee Eau portal endpoints."""

    abonnement_id: str | None = None
    point_installation_id: str | None = None
    equipement_id: str | None = None

    @property
    def is_complete(self) -> bool:
        """Return True when all supported identifiers are known."""
        return bool(
            self.abonnement_id and self.point_installation_id and self.equipement_id
        )

    def as_dict(self) -> dict[str, str | None]:
        """Return context as a serializable dictionary."""
        return {
            "abonnement_id": self.abonnement_id,
            "point_installation_id": self.point_installation_id,
            "equipement_id": self.equipement_id,
        }

    def with_fallback(self, fallback: "PortalContext") -> "PortalContext":
        """Return this context completed by fallback values."""
        return PortalContext(
            abonnement_id=self.abonnement_id or fallback.abonnement_id,
            point_installation_id=(
                self.point_installation_id or fallback.point_installation_id
            ),
            equipement_id=self.equipement_id or fallback.equipement_id,
        )


def discover_ids_from_text(text: str) -> PortalContext:
    """Discover Vendee Eau technical identifiers from portal HTML or JS."""
    normalized = unquote(unescape(text))
    json_context = _discover_ids_from_json(normalized)
    text_context = PortalContext(
        abonnement_id=_first_match(
            normalized,
            (
                r"/Usager/Abonnement/Synthese/(\d+)",
                r"/Abonnement/Synthese/(\d+)",
                r"\bSynthese/(\d+)",
                r"/Usager/Abonnement/[A-Za-z]+AbonnementModal/(\d+)",
                r"/Abonnement/[A-Za-z]+AbonnementModal/(\d+)",
                r"\bAfficherAbonnementModal/(\d+)",
                r"\bGetDetacherAbonnementModal/(\d+)",
                r"\babonnementId\s*[=:]\s*[\"']?(\d+)",
                r"\bidAbonnement\s*[=:]\s*[\"']?(\d+)",
                r"\bAbonnementId[\"']?\s*:\s*[\"']?(\d+)",
            ),
        ),
        point_installation_id=_first_match(
            normalized,
            (
                r"\bpointDInstallationId\s*=\s*[\"']?(\d+)",
                r"\bpointDInstallationId[\"']?\s*:\s*[\"']?(\d+)",
                r"\bidPointDInstallation\s*[=:]\s*[\"']?(\d+)",
            ),
        ),
        equipement_id=_first_match(
            normalized,
            (
                r"\bequipementId\s*=\s*[\"']?(\d+)",
                r"\bequipementId[\"']?\s*:\s*[\"']?(\d+)",
                r"\bidEquipement\s*[=:]\s*[\"']?(\d+)",
            ),
        ),
    )

    return text_context.with_fallback(json_context)


def _discover_ids_from_json(text: str) -> PortalContext:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return PortalContext()

    context = _discover_named_ids(payload)
    if context.abonnement_id:
        return context

    if isinstance(payload, dict) and isinstance(payload.get("aaData"), list):
        abonnement_id = _discover_subscription_id_from_aa_data(payload["aaData"])
        return PortalContext(abonnement_id=abonnement_id)

    return context


def _discover_named_ids(value: object) -> PortalContext:
    if isinstance(value, dict):
        context = PortalContext(
            abonnement_id=_string_id_from_mapping(
                value,
                ("abonnementId", "AbonnementId", "idAbonnement", "IdAbonnement"),
            ),
            point_installation_id=_string_id_from_mapping(
                value,
                (
                    "pointDInstallationId",
                    "PointDInstallationId",
                    "idPointDInstallation",
                    "IdPointDInstallation",
                ),
            ),
            equipement_id=_string_id_from_mapping(
                value,
                ("equipementId", "EquipementId", "idEquipement", "IdEquipement"),
            ),
        )
        if context.is_complete or any(context.as_dict().values()):
            return context

        for child in value.values():
            context = _discover_named_ids(child)
            if any(context.as_dict().values()):
                return context

    if isinstance(value, list):
        for child in value:
            context = _discover_named_ids(child)
            if any(context.as_dict().values()):
                return context

    return PortalContext()


def _string_id_from_mapping(
    value: dict[object, object],
    keys: tuple[str, ...],
) -> str | None:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, int):
            return str(candidate)
        if isinstance(candidate, str) and candidate.isdigit():
            return candidate
    return None


def _discover_subscription_id_from_aa_data(rows: list[object]) -> str | None:
    for row in rows:
        if not isinstance(row, list):
            continue

        for cell in row:
            if isinstance(cell, str):
                context = discover_ids_from_text(cell)
                if context.abonnement_id:
                    return context.abonnement_id

        numeric_cells = [
            str(cell)
            for cell in row
            if (isinstance(cell, int) and cell > 999)
            or (isinstance(cell, str) and cell.isdigit() and int(cell) > 999)
        ]
        if numeric_cells:
            return numeric_cells[-1]

    return None


def _first_match(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
