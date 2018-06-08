"""
Support for Azure Event Grid message handling.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/azure_event_grid/
"""
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

import voluptuous as vol

from homeassistant.helpers.typing import HomeAssistantType, ConfigType, \
    ServiceDataType
from homeassistant.core import callback, Event, ServiceCall
from homeassistant.setup import async_prepare_setup_platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.loader import bind_hass
from homeassistant.helpers import template, config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util.async_ import (
    run_coroutine_threadsafe, run_callback_threadsafe)
from homeassistant.const import CONF_HOST, CONF_PAYLOAD, CONF_NAME

REQUIREMENTS = ['azure.eventgrid==0.1.0', 'msrest==0.4.29']

#_LOGGER = logging.getLogger(__name__)
LOGGER = logging.getLogger('homeassistant.components.azure_event_grid')

DOMAIN = "azure_event_grid" 

SERVICE_AZURE_EVENT_GRID__PUBLISH_MESSAGE = "event_grid_publish_Message"

CONF_TOPICS = "topics"
CONF_TOPIC_NAME = "name"
CONF_TOPIC_KEY = 'topic key'

ATTR_SUBJECT = 'subject'
ATTR_EVENT_TYPE = 'eventtype'
ATTR_DATA_VERSION = 'dataversion'
ATTR_PAYLOAD = 'payload'
ATTR_PAYLOAD_TEMPLATE = 'payload_template'

DEFAULT_EVENT_TYPE = 'HomeAssistant'
DEFAULT_DATA_VERSION = 1 

TOPIC_CONFIG_SCHEMA = vol.Schema({
    vol.Required(CONF_TOPIC_NAME) : cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOPIC_KEY): cv.string
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_TOPICS):
            vol.All(cv.ensure_list, [TOPIC_CONFIG_SCHEMA]),
    }),
}, extra=vol.ALLOW_EXTRA)

# Service call validation schema
MQTT_PUBLISH_SCHEMA = vol.Schema({
    vol.Required(ATTR_SUBJECT): cv.string,
    vol.Exclusive(ATTR_PAYLOAD, CONF_PAYLOAD): object,
    vol.Exclusive(ATTR_PAYLOAD_TEMPLATE, CONF_PAYLOAD): cv.string,
    vol.Optional(ATTR_EVENT_TYPE, default=DEFAULT_EVENT_TYPE): cv.string,
    vol.Optional(ATTR_DATA_VERSION, default=DEFAULT_DATA_VERSION): cv.string,
}, required=True)


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up the Azure Event Grid platform."""
    try:
        LOGGER.debug("async_setup")

        conf = config.get(DOMAIN)
        if conf is None:
            conf = {}

        hass.data[DOMAIN] = {}

        # User has configured topic
        if CONF_TOPICS in conf:
            topics = conf[CONF_TOPICS]
    
        #if not topics:
        #    return True

        for topic_conf in topics:
            name = topic_conf[CONF_TOPIC_NAME]
        
            LOGGER.debug("setting up topic: %s",name)

            # Store config in hass.data so the config entry can find it
            hass.data[DOMAIN][name] = topic_conf

            topic = AzureEventGrid(hass, topic_conf)
            await topic.async_setup()

    except Exception  as err:
        LOGGER.error("Error async_setup: %s", err)

    return True

class AzureEventGrid(object):
    """Implement the notification service for the azure event grid."""

    def __init__(self, hass, config_entry):
        """Initialize the system."""
        self.config_entry = config_entry
        self.hass = hass

    @property
    def host(self):
        """Return the host of this bridge."""
        return self.config_entry.data[CONF_HOST]
    
    async def async_setup(self):
        """Set up this event grid based on host parameter."""
        try:
            from azure.eventgrid import EventGridClient
            from msrest.authentication import TopicCredentials
            
            self.name = TopicCredentials(self.config_entry.data[CONF_TOPIC_NAME])
        
            LOGGER.debug("Subscribing to %s", self.name)

            credentials = TopicCredentials(self.config_entry.data[CONF_TOPIC_KEY])
            self.client = EventGridClient(credentials) 

            self.hass.services.async_register(DOMAIN, SERVICE_AZURE_EVENT_GRID__PUBLISH_MESSAGE, self.event_grid_publish_message, schema=MQTT_PUBLISH_SCHEMA)
        except Exception  as err:
            LOGGER.error("Error while setting up the client: %s", err)

    async def event_grid_publish_message(self, call, updated=False):
        """Service to publish message to event grid."""
       
        try:
            data = call.data[ATTR_DATA]
            subject = call.data[CONF_SUBJECT]
        
            eventType = call.data[CONF_EVENT_TYPE]
            if eventType is None:
                eventType = CONF_EVENT_TYPE_DEFAULT
        
            dataVersion = call.data[CONF_DATA_VERSION]
            if dataVersion is None:
                dataVersion = CONF_DATA_VERSION_DEFAULT
    
            #create the payload, with subject, data and type coming in from the notify platform
            payload = {
                'id' : str(uuid.uuid4()),
                'subject': subject,
                'data': data,
                'event_type': eventType,
                'event_time': datetime.utcnow().replace(tzinfo=pytz.UTC),
                'data_version': dataVersion
            }

            #Send the event to event grid
            self.client.publish_events(
                self.host,
                events=[payload]
            )
        except HomeAssistantError as err:
            LOGGER.error("Unable to send event to Event Grid: %s", err)
