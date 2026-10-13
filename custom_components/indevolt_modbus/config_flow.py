"""Configure an Indevolt device over Modbus TCP."""

from typing import Any

import probatio
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from modbus_connection import ModbusError, ModbusTcpParams

from .const import (
    CONF_FAST_POLL_INTERVAL,
    CONF_MESSAGE_SPACING,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
    MESSAGE_SPACING,
    SCAN_INTERVAL,
)
from .transport import async_get_temporary_unit
from .vendor.indevolt_modbus import IndevoltDevice

SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): TextSelector(),
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): probatio.All(
            NumberSelector(
                NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
            ),
            probatio.Coerce(int),
        ),
        probatio.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): probatio.All(
            NumberSelector(
                NumberSelectorConfig(min=1, max=247, mode=NumberSelectorMode.BOX)
            ),
            probatio.Coerce(int),
        ),
    }
)


class IndevoltConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle setup and changes to connection details."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> IndevoltOptionsFlow:
        """Expose polling settings for each device."""
        return IndevoltOptionsFlow()

    _discovered_host: str | None = None

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Offer an HTTP-advertised host as a candidate for Modbus setup."""
        # The built-in HTTP integration uses this advertisement. It does not
        # establish Modbus availability, its port, or a verified hardware ID.
        await self._async_handle_discovery_without_unique_id()
        self._discovered_host = str(discovery_info.ip_address)
        self.context["title_placeholders"] = {"host": self._discovered_host}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm connection settings and validate Modbus before setup."""
        errors = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip().lower()
            self._async_abort_entries_match(user_input)
            if error := await self._validate(user_input):
                errors["base"] = error
            else:
                return self.async_create_entry(title="Indevolt", data=user_input)
        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=self.add_suggested_values_to_schema(
                SCHEMA,
                user_input
                or {
                    CONF_HOST: self._discovered_host,
                    CONF_PORT: DEFAULT_PORT,
                    CONF_UNIT_ID: DEFAULT_UNIT_ID,
                },
            ),
            errors=errors,
        )

    async def _validate(self, data: dict[str, Any]) -> str | None:
        try:
            async with async_get_temporary_unit(
                self.hass,
                ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT]),
                data[CONF_UNIT_ID],
            ) as unit:
                await IndevoltDevice.async_detect(unit)
        except ValueError:
            return "invalid_device"
        except ModbusError, HomeAssistantError:
            return "cannot_connect"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate the endpoint before creating an entry."""
        errors = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip().lower()
            self._async_abort_entries_match(user_input)
            if error := await self._validate(user_input):
                errors["base"] = error
            else:
                # No documented hardware identity register with a known length.
                # The entry id provides stable entity ids across reconfiguration.
                return self.async_create_entry(title="Indevolt", data=user_input)
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update the endpoint while preserving entity identities."""
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip().lower()
            if any(
                other.entry_id != entry.entry_id and dict(other.data) == user_input
                for other in self._async_current_entries()
            ):
                return self.async_abort(reason="already_configured")
            if error := await self._validate(user_input):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data=user_input)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, entry.data),
            errors=errors,
        )


class IndevoltOptionsFlow(OptionsFlowWithReload):
    """Configure regular reads, optional fast battery reads and request pacing."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save polling settings and reload to apply the new schedule."""
        if user_input is not None:
            return self.async_create_entry(
                data={**self.config_entry.options, **user_input}
            )
        return self.async_show_form(
            step_id="init",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, SCAN_INTERVAL
                        ),
                    ): probatio.All(
                        NumberSelector(
                            NumberSelectorConfig(
                                min=5,
                                max=3600,
                                step=1,
                                unit_of_measurement="s",
                                mode=NumberSelectorMode.BOX,
                            )
                        ),
                        probatio.Coerce(int),
                    ),
                    probatio.Required(
                        CONF_FAST_POLL_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_FAST_POLL_INTERVAL, 0
                        ),
                    ): probatio.All(
                        NumberSelector(
                            NumberSelectorConfig(
                                min=0,
                                max=3600,
                                step=1,
                                unit_of_measurement="s",
                                mode=NumberSelectorMode.BOX,
                            )
                        ),
                        probatio.Coerce(int),
                    ),
                    probatio.Required(
                        CONF_MESSAGE_SPACING,
                        default=self.config_entry.options.get(
                            CONF_MESSAGE_SPACING, MESSAGE_SPACING
                        ),
                    ): probatio.All(
                        NumberSelector(
                            NumberSelectorConfig(
                                min=1,
                                max=60,
                                step=1,
                                unit_of_measurement="s",
                                mode=NumberSelectorMode.BOX,
                            )
                        ),
                        probatio.Coerce(int),
                    ),
                }
            ),
        )
