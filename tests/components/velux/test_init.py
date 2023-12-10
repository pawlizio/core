"""Tests for the Velux component initialisation."""
import pytest

from homeassistant.components.velux.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component


@pytest.mark.usefixtures("pyvlx")
async def test_async_setup(hass: HomeAssistant, config_type: ConfigType) -> None:
    """Test if velux is setup from configuration yaml."""
    assert await async_setup_component(hass=hass, domain=DOMAIN, config=config_type)
