"""Config flow for Velux integration."""

import asyncio
from collections.abc import Sequence
from typing import Any

from pyvlx import PyVLX, PyVLXException
from pyvlx.discovery import VeluxDiscovery, VeluxHost
import voluptuous as vol

from homeassistant.components import zeroconf
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import DOMAIN, LOGGER


class VeluxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for velux."""

    VERSION = 1
    MINOR_VERSION = 2
    _task: asyncio.Task | None = None
    hosts: list[VeluxHost] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""

        return self.async_show_menu(
            step_id="user",
            menu_options=["discover", "auth"],
        )

    async def async_step_discover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Discover a KLF200.

        This step has been added, as the KLF200 does not reliably respond on mdns requests used by zeroconf,
        probably this is the case if one multicast massage contains several requests for more than 1 service_type.
        """
        aiozc = await zeroconf.async_get_async_instance(self.hass)
        vd: VeluxDiscovery = VeluxDiscovery(zeroconf=aiozc)
        if not await vd.async_discover_hosts(timeout=3, expected_hosts=1):
            return self.async_abort(reason="no_hosts_found")

        for new_host in vd.hosts:
            if not any(host.hostname == new_host.hostname for host in self.hosts):
                self.hosts.append(new_host)

        return await self.async_step_auth()

    async def async_step_auth(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Authenticate to a KLF200."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            title: str = user_input[CONF_HOST]
            if self.hosts:
                for host in self.hosts:
                    if user_input[CONF_HOST] == host.ip_address:
                        await self.async_set_unique_id(
                            host.hostname,
                            raise_on_progress=False,
                        )
                        self._abort_if_unique_id_configured()
                        title = (
                            f"{host.hostname.replace('LAN_', '')} ({host.ip_address})"
                        )
            pyvlx = PyVLX(
                host=user_input[CONF_HOST], password=user_input[CONF_PASSWORD]
            )
            try:
                await pyvlx.connect()
                await pyvlx.disconnect()
            except (PyVLXException, ConnectionError) as err:
                errors["base"] = "cannot_connect"
                LOGGER.debug("Cannot connect: %s", err)
            except Exception as err:  # noqa: BLE001
                LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )

        if self.hosts:
            options: Sequence[SelectOptionDict] = [
                {
                    "label": f"{host.hostname.replace("LAN_", "")} ({host.ip_address})",
                    "value": host.ip_address,
                }
                for host in self.hosts
            ]
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_HOST): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            custom_value=False,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )
        else:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_HOST): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )

        return self.async_show_form(
            step_id="auth",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery by zeroconf."""
        LOGGER.debug("Discovered via Zeroconf with info: %s", discovery_info)
        hostname = discovery_info.hostname.replace(".local.", "").upper()
        await self.async_set_unique_id(hostname)
        self._abort_if_unique_id_configured(
            updates={
                CONF_HOST: discovery_info.host,
            }
        )

        # Check if config_entry exists already without unigue_id configured.
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data[CONF_HOST] == discovery_info.host and entry.unique_id is None:
                self.hass.config_entries.async_update_entry(
                    entry=entry,
                    unique_id=hostname,
                )
                return self.async_abort(reason="already_configured")

        if not any(host.hostname == hostname for host in self.hosts):
            self.hosts.append(
                VeluxHost(hostname=hostname, ip_address=discovery_info.host)
            )

        return await self.async_step_auth()

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery by DHCP."""
        LOGGER.debug("Discovered via DHCP with info: %s", discovery_info)
        hostname = discovery_info.hostname.upper()
        mac = format_mac(discovery_info.macaddress)
        await self.async_set_unique_id(hostname)
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: discovery_info.ip, "mac": mac},
        )

        # Check if config_entry exists already without unigue_id configured.
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data[CONF_HOST] == discovery_info.ip and entry.unique_id is None:
                self.hass.config_entries.async_update_entry(
                    entry=entry,
                    unique_id=hostname,
                    data={**entry.data, "mac": mac},
                )
                return self.async_abort(reason="already_configured")

        if not any(host.hostname == hostname for host in self.hosts):
            self.hosts.append(
                VeluxHost(hostname=hostname, ip_address=discovery_info.ip)
            )

        return await self.async_step_auth()
