"""Configuration for Velux tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.components.velux.config_flow import VeluxConfigFlow
from homeassistant.components.zeroconf import HaAsyncZeroconf
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.velux.async_setup_entry", return_value=True
    ) as mock_entry:
        yield mock_entry


@pytest.fixture
def mock_velux_discovery() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "pyvlx.discovery.VeluxDiscovery._async_discover_hosts",
        autospec=True,
    ) as mock_discovery:
        yield mock_discovery


@pytest.fixture
def mock_async_zeroconf() -> Generator[HaAsyncZeroconf]:
    """Mock AsyncZeroconf."""
    with patch(
        "homeassistant.components.zeroconf.HaAsyncZeroconf", spec=HaAsyncZeroconf
    ) as mock_aiozc:
        yield mock_aiozc


@pytest.fixture
def config_flow(hass: HomeAssistant) -> VeluxConfigFlow:
    """Fixture to initialize the Velux config flow."""
    flow = VeluxConfigFlow()
    flow.hass = hass
    return flow
