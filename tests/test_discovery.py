"""Tests for Vendee Eau portal identifier discovery."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

DISCOVERY_PATH = (
    Path(__file__).parents[1] / "custom_components" / "vendee_eau" / "discovery.py"
)
spec = importlib.util.spec_from_file_location("vendee_eau_discovery", DISCOVERY_PATH)
assert spec is not None
discovery = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = discovery
spec.loader.exec_module(discovery)

discover_ids_from_text = discovery.discover_ids_from_text


def test_discover_ids_from_portal_links() -> None:
    """Portal IDs are discovered from subscription and consumption links."""
    html = """
    <a href="/Portail/fr-FR/Usager/Abonnement/Synthese/73859">Synthese</a>
    <script>
      "/GetMiniGraphRelevesData?pointDInstallationId=57692&amp;equipementId=114220"
    </script>
    """

    context = discover_ids_from_text(html)

    assert context.abonnement_id == "73859"
    assert context.point_installation_id == "57692"
    assert context.equipement_id == "114220"
    assert context.is_complete
    assert context.as_dict() == {
        "abonnement_id": "73859",
        "point_installation_id": "57692",
        "equipement_id": "114220",
    }


def test_discover_ids_from_url_encoded_return_url() -> None:
    """URL-encoded portal links are normalized before discovery."""
    html = (
        "ReturnUrl=%2FPortail%2Ffr-FR%2FUsager%2FAbonnement%2FSynthese%2F73859"
        "%3FpointDInstallationId%3D57692%26equipementId%3D114220"
    )

    context = discover_ids_from_text(html)

    assert context.abonnement_id == "73859"
    assert context.point_installation_id == "57692"
    assert context.equipement_id == "114220"


def test_discover_ids_from_javascript_object() -> None:
    """Portal IDs are discovered from JS objects and alternate field names."""
    html = """
    <script>
      const model = {
        abonnementId: 73859,
        pointDInstallationId: 57692,
        equipementId: 114220
      };
    </script>
    """

    context = discover_ids_from_text(html)

    assert context.abonnement_id == "73859"
    assert context.point_installation_id == "57692"
    assert context.equipement_id == "114220"


def test_discover_subscription_id_from_modal_link() -> None:
    """Subscription IDs can be exposed by modal action links."""
    html = '<a href="/Portail/fr-FR/Usager/Abonnement/AfficherAbonnementModal/73859">'

    context = discover_ids_from_text(html)

    assert context.abonnement_id == "73859"


def test_discover_subscription_id_from_datatables_json() -> None:
    """Subscription IDs can be hidden in legacy DataTables aaData rows."""
    payload = """
    {
      "sEcho": "1",
      "iTotalRecords": 1,
      "aaData": [["", "VE18000635", "", "21/03/2024", "", "73859"]],
      "sMessage": "1 contrat(s) dont 0 inactif(s)"
    }
    """

    context = discover_ids_from_text(payload)

    assert context.abonnement_id == "73859"


def test_portal_context_with_fallback_keeps_existing_values() -> None:
    """Manual values stay authoritative when discovery fills missing fields."""
    manual = discovery.PortalContext(abonnement_id="manual", equipement_id="manual-eq")
    discovered = discovery.PortalContext(
        abonnement_id="73859",
        point_installation_id="57692",
        equipement_id="114220",
    )

    context = manual.with_fallback(discovered)

    assert context.abonnement_id == "manual"
    assert context.point_installation_id == "57692"
    assert context.equipement_id == "manual-eq"

