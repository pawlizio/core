"""Test the Velux config flow."""

from __future__ import annotations

from copy import deepcopy
from ipaddress import ip_address
from typing import Any
from unittest.mock import PropertyMock, patch

import pytest
from pyvlx import PyVLXException
from pyvlx.discovery import VeluxHost

from homeassistant.components import zeroconf
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.components.velux import DOMAIN
from homeassistant.components.velux.config_flow import VeluxConfigFlow
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import SOURCE_DHCP, SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .const import HOST, HOSTNAME, PASSWORD

DUMMY_DATA: dict[str, Any] = {
    CONF_HOST: HOST,
    CONF_PASSWORD: PASSWORD,
}

PYVLX_CONFIG_FLOW_CONNECT_FUNCTION_PATH = (
    "homeassistant.components.velux.config_flow.PyVLX.connect"
)
PYVLX_CONFIG_FLOW_CLASS_PATH = "homeassistant.components.velux.config_flow.PyVLX"

error_types_to_test: list[tuple[Exception, str]] = [
    (PyVLXException("DUMMY"), "cannot_connect"),
    (Exception("DUMMY"), "unknown"),
]

pytestmark = pytest.mark.usefixtures(
    "mock_setup_entry",
    "mock_async_zeroconf",
    "mock_velux_discovery",
    "config_flow",
)


async def test_async_step_user(hass: HomeAssistant) -> None:
    """Test the initial step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=None
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "user"
    assert result["menu_options"] == ["discover", "auth"]


async def test_async_step_auth_success(hass: HomeAssistant) -> None:
    """Test the auth step of the config flow with successful authentication."""
    with (
        patch(PYVLX_CONFIG_FLOW_CLASS_PATH, autospec=True) as client_mock,
        patch.object(
            VeluxConfigFlow,
            "hosts",
            new_callable=PropertyMock,
            return_value=[VeluxHost(hostname=HOSTNAME, ip_address=HOST)],
        ),
    ):
        result: dict[str, Any] = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "auth"}, data=None
        )
        assert result["type"] == FlowResultType.FORM

        result2: dict[str, Any] = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=deepcopy(DUMMY_DATA)
        )
        client_mock.return_value.disconnect.assert_called_once()
        client_mock.return_value.connect.assert_called_once()
        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["data"] == DUMMY_DATA
        assert len(hass.config_entries.async_entries(DOMAIN)) == 1
        assert hass.config_entries.async_entries(DOMAIN)[0].unique_id == HOSTNAME


@pytest.mark.parametrize(("error", "error_name"), error_types_to_test)
async def test_async_step_auth_errors(
    hass: HomeAssistant, error: Exception, error_name: str
) -> None:
    """Test the auth step of the config flow with errors."""
    with patch(
        PYVLX_CONFIG_FLOW_CONNECT_FUNCTION_PATH, side_effect=error
    ) as connect_mock:
        result: dict[str, Any] = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "auth"}, data=deepcopy(DUMMY_DATA)
        )

        connect_mock.assert_called_once()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "auth"
        assert result["errors"] == {"base": error_name}


async def test_zeroconf_discovery(hass: HomeAssistant) -> None:
    """Test we can setup from zeroconf discovery."""
    assert not hass.data.get(DOMAIN)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("127.0.0.1"),
            ip_addresses=[ip_address("127.0.0.1")],
            hostname="VELUX_KLF_LAN_ABCD",
            port="",
            type="",
            name="VELUX_KLF_LAN_ABCD",
            properties="",
        ),
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "auth"


async def test_zeroconf_discovery_abort(hass: HomeAssistant) -> None:
    """Test a wrong ZeroconfServiceInfo."""
    # Setup entry.
    with patch(PYVLX_CONFIG_FLOW_CLASS_PATH, autospec=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "auth"},
            data=DUMMY_DATA,
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
    assert hass.config_entries.async_entries(DOMAIN)[0].unique_id is None
    await hass.async_block_till_done()

    # Set unique_id for already configured entry.
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address(HOST),
            ip_addresses=[ip_address(HOST)],
            hostname=HOSTNAME,
            port="",
            type="",
            name="VELUX_KLF_LAN_ABCD",
            properties="",
        ),
    )
    assert hass.config_entries.async_entries(DOMAIN)[0].unique_id == HOSTNAME
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert result["type"] == FlowResultType.ABORT


async def test_zeroconf_discovery_new_ip(hass: HomeAssistant) -> None:
    """Test a wrong ZeroconfServiceInfo."""
    # Setup entry.
    with patch(PYVLX_CONFIG_FLOW_CLASS_PATH, autospec=True) as pyvlx:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "auth"},
            data=DUMMY_DATA,
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == HOST
    assert result["data"] == {
        CONF_HOST: HOST,
        CONF_PASSWORD: PASSWORD,
    }
    pyvlx.assert_called_once_with(host=HOST, password=PASSWORD)
    assert hass.config_entries.async_entries(DOMAIN)[0].data[CONF_HOST] == HOST

    # Set unique_id from zeroconf.
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=zeroconf.ZeroconfServiceInfo(
            ip_address=ip_address(HOST),
            ip_addresses=[ip_address(HOST)],
            hostname=HOSTNAME,
            port="",
            type="",
            name="VELUX_KLF_LAN_ABCD",
            properties="",
        ),
    )
    assert hass.config_entries.async_entries(DOMAIN)[0].unique_id == HOSTNAME
    assert result["type"] == FlowResultType.ABORT

    # Update ip address of already configured unique_id.
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("127.1.1.2"),
            ip_addresses=[ip_address("127.1.1.2")],
            hostname="VELUX_KLF_LAN_ABCD",
            port="",
            type="",
            name="VELUX_KLF_LAN_ABCD",
            properties="",
        ),
    )
    assert hass.config_entries.async_entries(DOMAIN)[0].data[CONF_HOST] == "127.1.1.2"
    assert result["type"] == FlowResultType.ABORT


async def test_dhcp_discovery(hass: HomeAssistant) -> None:
    """Test we can setup from dhcp discovery."""
    with patch.object(
        VeluxConfigFlow,
        "hosts",
        new_callable=PropertyMock,
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_DHCP},
            data=DhcpServiceInfo(
                ip="127.0.0.1",
                hostname="VELUX_KLF_LAN_ABCD",
                macaddress="6461800122",
            ),
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "auth"


async def test_dhcp_discovery_already_configured(hass: HomeAssistant) -> None:
    """Test dhcp discovery when already configured."""
    # Setup entry.
    with patch(PYVLX_CONFIG_FLOW_CLASS_PATH, autospec=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "auth"},
            data=DUMMY_DATA,
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
    assert hass.config_entries.async_entries(DOMAIN)[0].unique_id is None
    await hass.async_block_till_done()

    # Set unique_id for already configured entry.
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DhcpServiceInfo(
            ip=DUMMY_DATA[CONF_HOST],
            hostname="VELUX_KLF_LAN_ABCD",
            macaddress="00:11:22:33:44:55",
        ),
    )
    assert result["type"] == FlowResultType.ABORT
    assert hass.config_entries.async_entries(DOMAIN)[0].unique_id == HOSTNAME
    assert result["reason"] == "already_configured"

    # Update ip address of already configured unique_id.
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DhcpServiceInfo(
            ip="127.1.1.2",
            hostname="VELUX_KLF_LAN_ABCD",
            macaddress="00:11:22:33:44:55",
        ),
    )
    assert hass.config_entries.async_entries(DOMAIN)[0].data[CONF_HOST] == "127.1.1.2"
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
