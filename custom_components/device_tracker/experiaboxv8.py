"""
Support for Arcadyan V7519 router.
"""
import base64
import hashlib
import logging
import re
from datetime import datetime

import requests
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (
    DOMAIN, PLATFORM_SCHEMA, DeviceScanner)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_USERNAME): cv.string
})


def get_scanner(hass, config):
    """Validate the configuration and return a Arcadyan AP scanner."""
    try:
        return ArcadyanDeviceScanner(config[DOMAIN])
    except ConnectionError:
        return None


class ArcadyanDeviceScanner(DeviceScanner):
    """This class queries a wireless router running Arcadyan firmware."""

    def __init__(self, config):
        """Initialize the scanner."""
        host = config[CONF_HOST]
        username, password = config[CONF_USERNAME], config[CONF_PASSWORD]

        self.parse_macs = re.compile('[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}')

        self.host = host
        self.username = username
        self.password = password

        self.last_results = {}
        self.success_init = self._update_info()

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()
        return self.last_results

    # pylint: disable=no-self-use
    def get_device_name(self, device):
        """Get firmware doesn't save the name of the wireless device."""
        return None

    def _update_info(self):
        """Ensure the information from the Arcadyan router is up to date.
        Return boolean if scanning successful.
        """
        _LOGGER.info("Loading wireless clients...")

        login_url_initial = 'http://{}/login.stm'.format(self.host)
        page_initial = requests.get(login_url_initial)

        httoken_search = re.search("var _httoken = '(.*)';", page_initial.text)
        authenticity_token = httoken_search.group(1)

        login_payload = {
            "user": self.username, 
            "pws": self.password, 
            "httoken": authenticity_token
        }

        clear_payload = {
            "securityclear.y": "8",
            "securityclear.x": "57",
            "httoken": authenticity_token
        }

        login_url = 'http://{}/cgi-bin/login.exe'.format(self.host)
        start_page = requests.post(login_url, data = login_payload)

        clear_url = 'http://{}/cgi-bin/statusprocess.exe'.format(self.host)
        clear_log = requests.post(clear_url, data = clear_payload)

        data_url = 'http://{}/status_main.stm'.format(self.host)
        data_page = requests.get(data_url)

        result = self.parse_macs.findall(data_page.text)

        logout_url = 'http://{}/cgi-bin/logout.exe?_tn='.format(self.host) + authenticity_token
        log_out_page = requests.get(logout_url)

        if result:
            self.last_results = [mac.replace("-", ":") for mac in result]
            return True

        return False