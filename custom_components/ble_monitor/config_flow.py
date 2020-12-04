"""Config flow for BLE Monitor."""
import asyncio
import logging
import re
import voluptuous as vol

from homeassistant.core import callback
from homeassistant import data_entry_flow
from homeassistant.helpers import config_validation as cv
from homeassistant import config_entries
from homeassistant.const import (
    CONF_DEVICES,
    CONF_DISCOVERY,
    CONF_MAC,
    CONF_NAME,
    CONF_TEMPERATURE_UNIT,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

from .const import (
    DEFAULT_ROUNDING,
    DEFAULT_DECIMALS,
    DEFAULT_PERIOD,
    DEFAULT_LOG_SPIKES,
    DEFAULT_USE_MEDIAN,
    DEFAULT_ACTIVE_SCAN,
    DEFAULT_HCI_INTERFACE,
    DEFAULT_BATT_ENTITIES,
    DEFAULT_REPORT_UNKNOWN,
    DEFAULT_DISCOVERY,
    DEFAULT_RESTORE_STATE,
    CONF_ROUNDING,
    CONF_DECIMALS,
    CONF_PERIOD,
    CONF_LOG_SPIKES,
    CONF_USE_MEDIAN,
    CONF_ACTIVE_SCAN,
    CONF_HCI_INTERFACE,
    CONF_BATT_ENTITIES,
    CONF_REPORT_UNKNOWN,
    CONF_RESTORE_STATE,
    CONF_ENCRYPTION_KEY,
    CONFIG_IS_FLOW,
    DOMAIN,
    MAC_REGEX,
    AES128KEY_REGEX,
)

OPTION_LIST_DEVICE = "--Devices--"
OPTION_ADD_DEVICE = "Add device..."


DEVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_MAC, default=""): cv.string,
        vol.Optional(CONF_ENCRYPTION_KEY, default=""): cv.string,
        vol.Optional(CONF_TEMPERATURE_UNIT, default=TEMP_CELSIUS): vol.In([TEMP_CELSIUS, TEMP_FAHRENHEIT]),
    }
)

DOMAIN_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_HCI_INTERFACE, default=[DEFAULT_HCI_INTERFACE]
        ): cv.multi_select({"0": "0", "1": "1", "2": "2"}),
        vol.Optional(CONF_PERIOD, default=DEFAULT_PERIOD): cv.positive_int,
        vol.Optional(CONF_DISCOVERY, default=DEFAULT_DISCOVERY): cv.boolean,
        vol.Optional(CONF_ACTIVE_SCAN, default=DEFAULT_ACTIVE_SCAN): cv.boolean,
        vol.Optional(
            CONF_REPORT_UNKNOWN, default=DEFAULT_REPORT_UNKNOWN
        ): cv.boolean,
        vol.Optional(
            CONF_BATT_ENTITIES, default=DEFAULT_BATT_ENTITIES
        ): cv.boolean,
        vol.Optional(CONF_ROUNDING, default=DEFAULT_ROUNDING): cv.boolean,
        vol.Optional(CONF_DECIMALS, default=DEFAULT_DECIMALS): cv.positive_int,
        vol.Optional(CONF_LOG_SPIKES, default=DEFAULT_LOG_SPIKES): cv.boolean,
        vol.Optional(CONF_USE_MEDIAN, default=DEFAULT_USE_MEDIAN): cv.boolean,
        vol.Optional(CONF_RESTORE_STATE, default=DEFAULT_RESTORE_STATE): cv.boolean,
        vol.Optional(CONF_DEVICES, default=[]): vol.All(
            cv.ensure_list, [DEVICE_SCHEMA]
        ),
    }
)

_LOGGER = logging.getLogger(__name__)


class BLEMonitorFlow(data_entry_flow.FlowHandler):
    """BLEMonitor flow"""
    def __init__(self):
        """Initialize flow instance."""
        self._devices = []
        self._sel_device = {}

    def validate_regex(self, value: str, regex: str):
        """Validate that the value is a string that matches a regex."""
        compiled = re.compile(regex)
        if not compiled.match(value):
            return False

        return True

    def validate_mac(self, value: str, errors: list):
        """mac validation"""
        if not self.validate_regex(value, MAC_REGEX):
            errors[CONF_MAC] = "invalid_mac"

    def validate_key(self, value: str, errors: list):
        """key validation"""
        if not value or value == "-":
            return

        if not self.validate_regex(value, AES128KEY_REGEX):
            errors[CONF_ENCRYPTION_KEY] = "invalid_key"

    def _show_main_form(self, errors=None):
        _LOGGER.error("_show_main_form: shouldn't be here")

    async def async_get_device_list(self):
        device_list = []
        device_list.append(OPTION_LIST_DEVICE)
        device_list.append(OPTION_ADD_DEVICE)
        for device in self._devices:
            device_list.append(device.get(CONF_MAC))
        return device_list

    @callback
    def _show_user_form(self, step_id=None, schema=None, errors=None):
        option_devices = asyncio.run_coroutine_threadsafe(
            async_get_device_list(self), hass.loop
        ).result()
#        option_devices = []
#        option_devices.append(OPTION_LIST_DEVICE)
#        option_devices.append(OPTION_ADD_DEVICE)
#        for device in self._devices:
#            option_devices.append(device.get(CONF_MAC))
        config_schema = schema.extend({
            vol.Optional(CONF_DEVICES, default=OPTION_LIST_DEVICE): vol.In(option_devices),
        })
        return self.async_show_form(
            step_id=step_id, data_schema=config_schema, errors=errors or {}
        )

    async def async_step_add_device(self, user_input=None):
        """add device step"""
        errors = {}
        if user_input is not None:
            _LOGGER.debug("async_step_add_device: %s", user_input)
            if user_input[CONF_MAC] and user_input[CONF_MAC] != "-":
                self.validate_mac(user_input[CONF_MAC], errors)
                self.validate_key(user_input[CONF_ENCRYPTION_KEY], errors)

                if not errors:
                    if user_input[CONF_ENCRYPTION_KEY] == "-":
                        user_input[CONF_ENCRYPTION_KEY] = None
                    if (not self._sel_device):  # new device
                        self._devices.append(user_input)
                    else:
                        for idx in range(0, len(self._devices)):
                            if self._devices[idx].get(CONF_MAC) == self._sel_device.get(CONF_MAC):
                                self._devices[idx] = user_input
                                if self._devices[idx][CONF_ENCRYPTION_KEY] == "-":
                                    self._devices[idx].pop(CONF_ENCRYPTION_KEY, None)
                                self._sel_device = {}  # prevent deletion
                                break

            if errors:
                RETRY_DEVICE_OPTION_SCHEMA = vol.Schema(
                    {
                        vol.Optional(CONF_MAC, default=user_input[CONF_MAC]): str,
                        vol.Optional(CONF_ENCRYPTION_KEY, default=user_input[CONF_ENCRYPTION_KEY]): str,
                        vol.Optional(CONF_TEMPERATURE_UNIT, default=user_input[CONF_TEMPERATURE_UNIT]): vol.In([TEMP_CELSIUS, TEMP_FAHRENHEIT]),
                    }
                )
                return self.async_show_form(
                    step_id="add_device",
                    data_schema=RETRY_DEVICE_OPTION_SCHEMA,
                    errors=errors,
                )

            if (self._sel_device):
                for idx in range(0, len(self._devices)):
                    if self._devices[idx].get(CONF_MAC) == self._sel_device.get(CONF_MAC):
                        self._devices.pop(idx)
                        break

            return self._show_main_form(errors)

        DEVICE_OPTION_SCHEMA = vol.Schema(
            {
                vol.Optional(CONF_MAC, default=self._sel_device.get(CONF_MAC) if self._sel_device.get(CONF_MAC) else ""): str,
                vol.Optional(CONF_ENCRYPTION_KEY, default=self._sel_device.get(CONF_ENCRYPTION_KEY) if self._sel_device.get(CONF_ENCRYPTION_KEY) else ""): str,
                vol.Optional(CONF_TEMPERATURE_UNIT, default=self._sel_device.get(CONF_TEMPERATURE_UNIT) if self._sel_device.get(CONF_TEMPERATURE_UNIT) else TEMP_CELSIUS): vol.In([TEMP_CELSIUS, TEMP_FAHRENHEIT]),
            }
        )

        return self.async_show_form(
            step_id="add_device",
            data_schema=DEVICE_OPTION_SCHEMA,
            errors=errors,
        )


class BLEMonitorConfigFlow(BLEMonitorFlow, config_entries.ConfigFlow, domain=DOMAIN):
    """BLEMonitor config flow"""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return BLEMonitorOptionsFlow(config_entry)

    def _show_main_form(self, errors=None):
        return self._show_user_form("user", DOMAIN_SCHEMA, errors or {})

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        _LOGGER.debug("async_step_user: %s", user_input)
        errors = {}
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if self.hass.data.get(DOMAIN):
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            if CONF_DEVICES not in user_input:
                user_input[CONF_DEVICES] = {}
            elif user_input[CONF_DEVICES] == OPTION_ADD_DEVICE:
                self._sel_device = {}
                return await self.async_step_add_device()
            for dev in self._devices:
                if dev.get(CONF_MAC) == user_input[CONF_DEVICES]:
                    self._sel_device = dev
                    return await self.async_step_add_device()

            title = "Bluetooth Low Energy Monitor"
            await self.async_set_unique_id(title)
            self._abort_if_unique_id_configured()
            user_input[CONF_DEVICES] = self._devices

            return self.async_create_entry(title=title, data=user_input)

        return self._show_main_form(errors)

    async def async_step_import(self, user_input=None):
        """Handle import."""
        _LOGGER.debug("async_step_import: %s", user_input)
        return await self.async_step_user(user_input)


class BLEMonitorOptionsFlow(BLEMonitorFlow, config_entries.OptionsFlow):
    """Handle BLE Monitor options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__()
        self.config_entry = config_entry

    def _show_main_form(self, errors=None):
        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_HCI_INTERFACE, default=self.config_entry.options.get(CONF_HCI_INTERFACE, DEFAULT_HCI_INTERFACE)
                ): cv.multi_select({"0": "0", "1": "1", "2": "2"}),
                vol.Optional(CONF_DISCOVERY, default=self.config_entry.options.get(CONF_DISCOVERY, DEFAULT_DISCOVERY)): cv.boolean,
                vol.Optional(CONF_ACTIVE_SCAN, default=self.config_entry.options.get(CONF_ACTIVE_SCAN, DEFAULT_ACTIVE_SCAN)): cv.boolean,
                vol.Optional(
                    CONF_REPORT_UNKNOWN, default=self.config_entry.options.get(CONF_REPORT_UNKNOWN, DEFAULT_REPORT_UNKNOWN)
                ): cv.boolean,
                vol.Optional(
                    CONF_BATT_ENTITIES, default=self.config_entry.options.get(CONF_BATT_ENTITIES, DEFAULT_BATT_ENTITIES)
                ): cv.boolean,
                vol.Optional(CONF_ROUNDING, default=self.config_entry.options.get(CONF_ROUNDING, DEFAULT_ROUNDING)): cv.boolean,
                vol.Optional(CONF_DECIMALS, default=self.config_entry.options.get(CONF_DECIMALS, DEFAULT_DECIMALS)): cv.positive_int,
                vol.Optional(CONF_PERIOD, default=self.config_entry.options.get(CONF_PERIOD, DEFAULT_PERIOD)): cv.positive_int,
                vol.Optional(CONF_LOG_SPIKES, default=self.config_entry.options.get(CONF_LOG_SPIKES, DEFAULT_LOG_SPIKES)): cv.boolean,
                vol.Optional(CONF_USE_MEDIAN, default=self.config_entry.options.get(CONF_USE_MEDIAN, DEFAULT_USE_MEDIAN)): cv.boolean,
                vol.Optional(CONF_RESTORE_STATE, default=self.config_entry.options.get(CONF_RESTORE_STATE, DEFAULT_RESTORE_STATE)): cv.boolean,
            }
        )
        return self._show_user_form("init", options_schema, errors or {})

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        _LOGGER.debug("async_step_init user_input: %s", user_input)

        if user_input is not None:
            _LOGGER.debug("async_step_init (after): %s", user_input)
            if CONFIG_IS_FLOW in self.config_entry.options and not self.config_entry.options[CONFIG_IS_FLOW]:
                return self.async_abort(reason="not_in_use")

            if user_input[CONF_DEVICES] == OPTION_ADD_DEVICE:
                self._sel_device = {}
                return await self.async_step_add_device()
            for dev in self._devices:
                if dev.get(CONF_MAC) == user_input[CONF_DEVICES]:
                    self._sel_device = dev
                    return await self.async_step_add_device()

            user_input[CONF_DEVICES] = self._devices
            return self.async_create_entry(title="", data=user_input)

        _LOGGER.debug("async_step_init (before): %s", self.config_entry.options)

        if CONFIG_IS_FLOW in self.config_entry.options and not self.config_entry.options[CONFIG_IS_FLOW]:
            options_schema = vol.Schema({vol.Optional("not_in_use", default=""): str})
            return self.async_show_form(
                step_id="init", data_schema=options_schema, errors=errors or {}
            )
        else:
            self._devices = self.config_entry.options.get(CONF_DEVICES)

        return self._show_main_form(errors)
