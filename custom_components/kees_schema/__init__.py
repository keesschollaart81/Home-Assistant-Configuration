import asyncio
from itertools import groupby
from typing import Optional, Any, Union, Callable, List, cast  # noqa: F401
from operator import attrgetter
import logging
import os
import socket
import time
import ssl
import re
import requests.certs
import attr
import uuid
import pytz

import voluptuous as vol

from homeassistant.components import (http)
from homeassistant.helpers.typing import HomeAssistantType, ConfigType,  ServiceDataType
from homeassistant.core import callback, Event, ServiceCall
from homeassistant.setup import async_prepare_setup_platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.loader import bind_hass
from homeassistant.helpers import template, config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util.async_ import (run_coroutine_threadsafe, run_callback_threadsafe)
from homeassistant.const import CONF_HOST, CONF_PAYLOAD, CONF_NAME
from datetime import datetime
from homeassistant.config import async_check_ha_config_file, find_config_file, load_yaml_config_file, merge_packages_config
from homeassistant.const import (
    ATTR_FRIENDLY_NAME, ATTR_HIDDEN, ATTR_ASSUMED_STATE,
    CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME, CONF_PACKAGES, CONF_UNIT_SYSTEM,
    CONF_TIME_ZONE, CONF_ELEVATION, CONF_UNIT_SYSTEM_METRIC,
    CONF_UNIT_SYSTEM_IMPERIAL, CONF_TEMPERATURE_UNIT, TEMP_CELSIUS,
    __version__, CONF_CUSTOMIZE, CONF_CUSTOMIZE_DOMAIN, CONF_CUSTOMIZE_GLOB,
    CONF_WHITELIST_EXTERNAL_DIRS, CONF_AUTH_PROVIDERS, CONF_AUTH_MFA_MODULES,
    CONF_TYPE, CONF_ID)
from homeassistant.core import callback, DOMAIN as CONF_CORE, HomeAssistant
# from . import luscious

LOGGER = logging.getLogger('homeassistant.components.kees_schema')

DOMAIN = "kees_schema" 
# REQUIREMENTS = ['genson==1.0.2', 'msrest==0.4.29']

async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    try:
        LOGGER.debug("async_setup")

        hass.http.register_view(kees_schema_view())

    except Exception  as err:
        LOGGER.error("Error async_setup: %s", err)

    return True
 
class kees_schema_view(http.HomeAssistantView):

    url = '/api/kees_schema'
    name = 'api:kees_schema'

    @asyncio.coroutine
    async def post(self, request):
      
        hass = request.app['hass']

        data = await request.json() 
        path = find_config_file(hass.config.config_dir) 
        config = load_yaml_config_file(path)
        core_config = config.get(CONF_CORE, {})
        merge_packages_config(hass, config, core_config.get(CONF_PACKAGES, {}))


        # config = await async_check_ha_config_file(request.app['hass'])

        return self.json(config)