"""Config flow for Velux integration."""

from pyvlx import PyVLX, PyVLXException
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.const import CONF_HOST, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, LOGGER

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


class VeluxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for velux."""

    VERSION = 1
    MINOR_VERSION = 2

    host: str | None = None

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})

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
                    title=user_input[CONF_HOST],
                    data=user_input,
                )

        data_schema = self.add_suggested_values_to_schema(
            DATA_SCHEMA, user_input or {CONF_HOST: self.context[CONF_HOST]}
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_unignore(self, user_input: dict[str, Any]) -> FlowResult:
        """Rediscover a previously ignored discover."""
        unique_id = user_input["unique_id"]
        await self.async_set_unique_id(unique_id)
        return await self.async_step_user()

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle discovery by zeroconf."""
        hostname = discovery_info.hostname.replace(".local.", "")
        await self.async_set_unique_id(hostname)
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.host})

        # Check if config_entry exists already without unigue_id configured.
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data[CONF_HOST] == discovery_info.host and entry.unique_id is None:
                entry.unique_id = hostname
                return self.async_abort(reason="already_configured")

        self.context[CONF_HOST] = discovery_info.host
        return await self.async_step_user()
