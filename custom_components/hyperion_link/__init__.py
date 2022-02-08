"""The hyperion_link integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from hyperion_link import hyperion_link
from .const import DOMAIN


# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [
    # Platform.LIGHT
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up hyperion_link from a config entry."""
    hpl = hyperion_link(
        entry.data["ip_addr"],
        entry.data["port"],
    )
    lights = entry.data["lights"]

    def led_recv(leds):
        for direction in lights.keys():
            hass.services.call(
                "light",
                "turn_on",
                {
                    "entity_id": lights[direction],
                    "rgb_color": leds[direction],
                },
                blocking=False,
            )

    hpl.led_reciever = led_recv
    hpl.led_info = entry.data["led_assignment"]
    hpl.connect()

    if DOMAIN not in hass.data.keys():
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = hpl
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    #
    ## Create services
    #

    def start_service(call):
        hpl.start_led_listener()

    def stop_service(call):
        hpl.stop_led_listener()

    def change_lights_to_controll(call):
        print(call)

    hass.services.async_register(DOMAIN, "Start", start_service)
    hass.services.async_register(DOMAIN, "Stop", stop_service)
    hass.services.async_register(DOMAIN, "change_lights", change_lights_to_controll)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN][entry.entry_id].disconnect()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
