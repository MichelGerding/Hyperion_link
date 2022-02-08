"""Config flow for hyperion_link integration."""
from __future__ import annotations

import logging

# from os import link
from typing import Any
from ipaddress import ip_address

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from hyperion_link import hyperion_link
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            "host",
            default="192.168.1.50",
            msg="ip of hyperion server",
        ): str,
        vol.Required(
            "port",
            default=8090,
            msg="port of the hyperion web interface",
        ): int,
        vol.Optional(
            "access_key",
            msg="optional authentification key (not implemented)",
        ): str,
    }
)

STEP_HYPERION_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Required(
            "left",
            default=1,
        ): int,
        vol.Required(
            "top",
            default=1,
        ): int,
        vol.Required(
            "right",
            default=1,
        ): int,
        vol.Required(
            "bottom",
            default=1,
        ): int,
    }
)


async def validate_connection_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    # check if ip and port are valid
    try:
        ip_address(data["host"])
    except ValueError:
        raise InvalidIp from HomeAssistantError

    if not 1 <= data["port"] <= 65535:
        raise InvalidPort

    # check if we can connect to hyperion by requisting server info
    print(data["host"], data["port"])
    hub = hyperion_link(data["host"], data["port"])

    server_info = await hass.async_add_executor_job(hub.get_server_info)

    if not server_info:
        raise CannotConnect
    if not server_info["success"]:
        raise CannotConnect
    # get the correct instance

    return {
        "hostname": server_info["info"]["hostname"],
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for hyperion_link."""

    VERSION = 1
    next_form = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}
        try:
            info = await validate_connection_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidIp:
            errors["base"] = "invalid_ip"
        except InvalidPort:
            errors["base"] = "invalid_port"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            print("success")

            # print(eval(user_input["access_key"]))
            entities = self.hass.data["entity_info"]

            lights = {i: entities[i] for i in entities.keys() if i.startswith("light.")}
            light_check = vol.In({i for i in lights})

            if len(lights.keys()) < 1:
                return self.async_abort(reason="no_lights_found")

            self.next_form = vol.Schema(
                {
                    vol.Optional(
                        "left",
                        description="lights left of hyperion display",
                    ): light_check,
                    vol.Optional(
                        "top",
                        description="lights top of hyperion display",
                    ): light_check,
                    vol.Optional(
                        "right",
                        description="lights right of hyperion display",
                    ): light_check,
                    vol.Optional(
                        "bottom",
                        description="lights bottom of hyperion display",
                    ): light_check,
                }
            )

            # go to step 2 to configure the entities/groups
            self.init_data = {
                "hostname": info["hostname"],
                "port": user_input["port"],
                "ip_addr": user_input["host"],
            }

            return await self.async_step_ligth_groups()
            # return self.async_create_entry(title=info["hostname"], data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_ligth_groups(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the flow to select which lights to controll"""
        error = {}

        if user_input is not None:
            self.init_data["lights"] = user_input

            if len(user_input.keys()) >= 1:
                return await self.async_step_hyperion_settings()
            else:
                error["base"] = "no_lights_entered"
        return self.async_show_form(
            step_id="ligth_groups", data_schema=self.next_form, errors=error
        )

    async def async_step_hyperion_settings(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Config flow to get the led assignments"""
        errors = {}
        if user_input is not None:
            print(user_input)

            # vlaidate data
            print(sum([user_input[i] for i in user_input.keys()]))
            if sum([user_input[i] for i in user_input.keys()]) < 1:
                errors["base"] = "no_lights_assigned"
            else:
                self.init_data["led_assignment"] = user_input
                print(self.init_data)
                return self.async_create_entry(
                    title=self.init_data["hostname"], data=self.init_data
                )

        return self.async_show_form(
            step_id="hyperion_settings",
            data_schema=STEP_HYPERION_SETTINGS_SCHEMA,
            errors=errors,
        )


class InvalidIp(HomeAssistantError):
    """Error to indicate the ip is invallid."""


class InvalidPort(HomeAssistantError):
    """Error to indicate the passed port is invallid."""


class CannotConnect(HomeAssistantError):
    """Error to indicate a mistake during connection"""
