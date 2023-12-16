"""Fixtures for the Velbus tests."""
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pyvlx import PyVLX
from pyvlx.nodes import Nodes
from pyvlx.scenes import Scenes

from homeassistant.components.velux.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import HOST, PASSWORD

from tests.common import MockConfigEntry


class PyVLXMock(AsyncMock):
    """Pyvlx mock class."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize pyvlx mock."""
        super().__init__(*args, **kwargs)
        self.nodes = AsyncMock(spec=Nodes)
        self.scenes = AsyncMock(spec=Scenes)


@pytest.fixture(name="pyvlx")
def mock_pyvlx() -> Generator[AsyncMock, None, None]:
    """Mock a successful velux gateway."""
    with patch("homeassistant.components.velux.PyVLX", spec=PyVLX) as pyvlx:
        yield pyvlx


@pytest.fixture(name="config_entry")
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create and register mock config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PASSWORD: PASSWORD},
    )
    config_entry.add_to_hass(hass)
    return config_entry


@pytest.fixture(name="config_type")
def config_type(hass: HomeAssistant) -> ConfigType:
    """Create and register mock config entry."""
    config_type = ConfigType(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PASSWORD: PASSWORD},
    )
    return config_type
