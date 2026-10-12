"""Fixtures for the custom integration against a real Home Assistant runtime."""

import sys
from pathlib import Path

import pytest
from modbus_connection.mock import MockModbusConnection

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Allow loading the repository's integration."""


@pytest.fixture
def unit():
    """A protocol V1.9 device using real model decoding."""
    connection = MockModbusConnection()
    unit = connection.for_unit(1)
    unit.holding.update(
        {70: 14501, 7534: 19, 2250: 1234, 7599: 765, 1142: 20, 1144: 1, 1143: 0}
    )
    return unit
