"""Tests for the Velux component initialisation."""
from unittest.mock import AsyncMock, patch

from homeassistant.components.velux.const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component


async def test_async_setup(hass: HomeAssistant, config_type: ConfigType) -> None:
    """Test velux setup via configuration.yaml."""
    assert await async_setup_component(hass=hass, domain=DOMAIN, config=config_type)
    await hass.async_block_till_done()


async def test_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Test velux setup via configuration.yaml."""
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    with patch("homeassistant.components.velux.PyVLX.connect", new=AsyncMock), patch(
        "homeassistant.components.velux.PyVLX.load_nodes", new=AsyncMock
    ), patch("homeassistant.components.velux.PyVLX.load_scenes", new=AsyncMock):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        assert len(hass.config_entries.async_entries(DOMAIN)) == 0
        # assert config_entry.state == ConfigEntryState.LOADED

    # assert await hass.config_entries.async_unload(config_entry.entry_id)
    # await hass.async_block_till_done()

    # assert config_entry.state == ConfigEntryState.NOT_LOADED
    # assert not hass.data.get(DOMAIN)
