"""Constants for the Vendee Eau integration."""

from datetime import timedelta

DOMAIN = "vendee_eau"

CONF_POINT_INSTALLATION_ID = "point_installation_id"
CONF_EQUIPEMENT_ID = "equipement_id"
CONF_ABONNEMENT_ID = "abonnement_id"

DEFAULT_NAME = "Vendee Eau"
DEFAULT_SCAN_INTERVAL = timedelta(hours=6)

BASE_URL = "https://agence.vendee-eau.fr"
LOGIN_PATH = "/Portail/fr-FR/Connexion/Login"
ABONNEMENT_MANAGEMENT_PATH = "/Portail/fr-FR/Usager/Abonnement/Gestion"
ABONNEMENT_AJAX_PATH = "/Portail/fr-FR/Usager/Abonnement/Ajax"
CONSUMPTION_PATH = "/Portail/fr-FR/Usager/Abonnement/GetMiniGraphRelevesData"
SYNTHESIS_PATH_TEMPLATE = "/Portail/fr-FR/Usager/Abonnement/Synthese/{abonnement_id}"

ATTRIBUTION = "Data provided by Vendee Eau"
