"""Async client for the Vendee Eau customer portal."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import logging
from typing import Any
from urllib.parse import urljoin

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import (
    ABONNEMENT_AJAX_PATH,
    ABONNEMENT_MANAGEMENT_PATH,
    BASE_URL,
    CONSUMPTION_PATH,
    LOGIN_PATH,
    SYNTHESIS_PATH_TEMPLATE,
)
from .discovery import (
    PortalContext,
    discover_ids_from_text,
)

_LOGGER = logging.getLogger(__name__)


class VendeeEauError(Exception):
    """Base error for Vendee Eau."""


class VendeeEauAuthError(VendeeEauError):
    """Raised when authentication fails."""


class VendeeEauConnectionError(VendeeEauError):
    """Raised when the portal cannot be reached."""


class VendeeEauDataError(VendeeEauError):
    """Raised when portal data is missing or unexpected."""


@dataclass
class LoginForm:
    """Parsed login form."""

    action: str
    fields: dict[str, str]


class _LoginFormParser(HTMLParser):
    """Minimal parser for the first HTML form and its input fields."""

    def __init__(self) -> None:
        super().__init__()
        self.in_form = False
        self.form_found = False
        self.action = LOGIN_PATH
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)

        if tag == "form" and not self.form_found:
            self.in_form = True
            self.form_found = True
            self.action = attrs_dict.get("action") or LOGIN_PATH
            return

        if tag != "input" or not self.in_form:
            return

        name = attrs_dict.get("name")
        if name:
            self.fields[name] = attrs_dict.get("value") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self.in_form:
            self.in_form = False


def _parse_login_form(html: str) -> LoginForm:
    parser = _LoginFormParser()
    parser.feed(html)
    if not parser.form_found:
        _LOGGER.debug("No login form found, using default login endpoint and fields")
        return LoginForm(action=urljoin(BASE_URL, LOGIN_PATH), fields={})

    return LoginForm(action=urljoin(BASE_URL, parser.action), fields=parser.fields)


def _pick_field(payload: dict[str, str], candidates: list[str], fallback: str) -> str:
    return next((candidate for candidate in candidates if candidate in payload), fallback)


class VendeeEauClient:
    """Client for the Vendee Eau portal."""

    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
        point_installation_id: str | None = None,
        equipement_id: str | None = None,
        abonnement_id: str | None = None,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._point_installation_id = point_installation_id
        self._equipement_id = equipement_id
        self._abonnement_id = abonnement_id
        self._context = PortalContext(
            abonnement_id=abonnement_id,
            point_installation_id=point_installation_id,
            equipement_id=equipement_id,
        )
        self._logged_in = False

    async def authenticate(self) -> None:
        """Authenticate against the portal."""
        try:
            response = await self._session.get(
                urljoin(BASE_URL, LOGIN_PATH),
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "User-Agent": "HomeAssistant vendee-eau/0.1",
                },
                timeout=20,
            )
            response.raise_for_status()
            form = _parse_login_form(await response.text())

            payload = dict(form.fields)
            user_field = _pick_field(
                payload,
                ["UserName", "Username", "Login", "Email", "Identifiant"],
                "Login",
            )
            password_field = _pick_field(
                payload,
                ["Password", "MotDePasse", "MotPasse"],
                "Password",
            )
            payload[user_field] = self._username
            payload[password_field] = self._password

            login_response = await self._session.post(
                form.action,
                data=payload,
                allow_redirects=True,
                timeout=20,
            )
            login_response.raise_for_status()
            body = await login_response.text()
        except (ClientError, TimeoutError, ClientResponseError) as err:
            raise VendeeEauConnectionError("Unable to connect to Vendee Eau") from err

        if not _looks_authenticated(body):
            raise VendeeEauAuthError("Authentication failed")

        self._context = self._context.with_fallback(discover_ids_from_text(body))
        self._logged_in = True

    async def async_get_data(self) -> dict[str, Any]:
        """Return all currently supported account data."""
        if not self._logged_in:
            await self.authenticate()

        context = await self.async_discover_context()

        data: dict[str, Any] = {}
        data["context"] = context.as_dict()

        if context.point_installation_id and context.equipement_id:
            data["consumption"] = await self.async_get_consumption()
        else:
            _LOGGER.debug("Consumption skipped: point/equipment ids were not found")
            data["consumption"] = {}

        return data

    async def async_discover_context(self) -> PortalContext:
        """Discover portal identifiers required by AJAX endpoints."""
        manual_context = PortalContext(
            abonnement_id=self._abonnement_id,
            point_installation_id=self._point_installation_id,
            equipement_id=self._equipement_id,
        )
        context = self._context.with_fallback(manual_context)
        if context.is_complete:
            return context

        management_html = await self._async_get_portal_page(ABONNEMENT_MANAGEMENT_PATH)
        context = context.with_fallback(discover_ids_from_text(management_html))

        if not context.abonnement_id:
            ajax_text = await self._async_post_portal_page(
                ABONNEMENT_AJAX_PATH,
                data=_legacy_datatable_payload(),
                referer=ABONNEMENT_MANAGEMENT_PATH,
            )
            context = context.with_fallback(discover_ids_from_text(ajax_text))

        if context.abonnement_id and not context.is_complete:
            synthesis_html = await self._async_get_portal_page(
                SYNTHESIS_PATH_TEMPLATE.format(abonnement_id=context.abonnement_id),
                referer=ABONNEMENT_MANAGEMENT_PATH,
            )
            context = context.with_fallback(discover_ids_from_text(synthesis_html))

        self._context = context
        return context

    async def _async_get_portal_page(
        self, path: str, referer: str | None = None
    ) -> str:
        """Fetch an authenticated portal page."""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        if referer:
            headers["Referer"] = urljoin(BASE_URL, referer)

        try:
            response = await self._session.get(
                urljoin(BASE_URL, path),
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type:
                raise VendeeEauDataError(
                    f"Unexpected portal response type: {content_type}"
                )
            return await response.text()
        except VendeeEauDataError:
            raise
        except ClientResponseError as err:
            raise VendeeEauDataError(
                f"Unable to fetch portal page {path}: HTTP {err.status}"
            ) from err
        except (ClientError, TimeoutError) as err:
            self._logged_in = False
            raise VendeeEauConnectionError(
                f"Unable to fetch portal page {path}"
            ) from err

    async def _async_post_portal_page(
        self,
        path: str,
        data: dict[str, str] | None = None,
        referer: str | None = None,
    ) -> str:
        """Post to an authenticated portal endpoint and return its body."""
        headers = {
            "Accept": "application/json, text/html, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }
        if referer:
            headers["Referer"] = urljoin(BASE_URL, referer)

        try:
            response = await self._session.post(
                urljoin(BASE_URL, path),
                data=data or {},
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            return await response.text()
        except ClientResponseError as err:
            raise VendeeEauDataError(
                f"Unable to post portal page {path}: HTTP {err.status}"
            ) from err
        except (ClientError, TimeoutError) as err:
            self._logged_in = False
            raise VendeeEauConnectionError(
                f"Unable to post portal page {path}"
            ) from err

    async def async_get_consumption(self) -> dict[str, Any]:
        """Fetch consumption graph data."""
        context = self._context
        if not context.point_installation_id or not context.equipement_id:
            raise VendeeEauDataError("Consumption identifiers are missing")

        params = {
            "pointDInstallationId": context.point_installation_id,
            "equipementId": context.equipement_id,
        }
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }

        if context.abonnement_id:
            headers["Referer"] = urljoin(
                BASE_URL,
                SYNTHESIS_PATH_TEMPLATE.format(abonnement_id=context.abonnement_id),
            )

        try:
            response = await self._session.post(
                urljoin(BASE_URL, CONSUMPTION_PATH),
                params=params,
                json={},
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type:
                text = await response.text()
                raise VendeeEauDataError(
                    f"Unexpected consumption response type: {content_type}; {text[:120]}"
                )
            payload = await response.json()
        except VendeeEauDataError:
            raise
        except (ClientError, TimeoutError, ClientResponseError) as err:
            self._logged_in = False
            raise VendeeEauConnectionError("Unable to fetch consumption data") from err

        if not isinstance(payload, dict):
            raise VendeeEauDataError("Unexpected consumption payload")

        return payload


def _looks_authenticated(html: str) -> bool:
    """Return True when the portal page looks like an authenticated session."""
    return "Déconnexion" in html or "Deconnexion" in html or "Logout" in html


def _legacy_datatable_payload() -> dict[str, str]:
    """Return the legacy DataTables payload used by the subscription table."""
    legacy = {
        "sEcho": "1",
        "iColumns": "8",
        "sColumns": "",
        "iDisplayStart": "0",
        "iDisplayLength": "100",
        "mDataProp_0": "0",
        "mDataProp_1": "1",
        "mDataProp_2": "2",
        "mDataProp_3": "3",
        "mDataProp_4": "4",
        "mDataProp_5": "5",
        "mDataProp_6": "6",
        "mDataProp_7": "7",
        "sSearch": "",
        "bRegex": "false",
        "iSortCol_0": "0",
        "sSortDir_0": "asc",
        "iSortingCols": "1",
    }
    for index in range(8):
        legacy[f"sSearch_{index}"] = ""
        legacy[f"bRegex_{index}"] = "false"
        legacy[f"bSearchable_{index}"] = "true"
        legacy[f"bSortable_{index}"] = "true"

    return legacy
