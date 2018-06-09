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
import uuid
import pytz

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
from homeassistant.const import CONF_HOST, CONF_PAYLOAD, CONF_ENTITY_ID
from datetime import datetime

REQUIREMENTS = ['azure.eventgrid==0.1.0', 'msrest==0.4.29']

#_LOGGER = logging.getLogger(__name__)
LOGGER = logging.getLogger('homeassistant.components.azure_event_grid')

DOMAIN = "azure_event_grid" 

SERVICE_AZURE_EVENT_GRID__PUBLISH_MESSAGE = "publish_Message"

CONF_TOPIC_KEY = 'topic key'

ATTR_SUBJECT = 'subject'
ATTR_EVENT_TYPE = 'eventtype'
ATTR_DATA_VERSION = 'dataversion'
ATTR_PAYLOAD = 'payload'
ATTR_PAYLOAD_TEMPLATE = 'payload_template'
# { "subject": "subject", "eventtype":"eventtype","payload":{} }

DEFAULT_EVENT_TYPE = 'HomeAssistant'
DEFAULT_DATA_VERSION = 1 

TOPIC_CONFIG_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOPIC_KEY): cv.string
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        cv.slug: TOPIC_CONFIG_SCHEMA,
    }),
}, extra=vol.ALLOW_EXTRA)

MQTT_PUBLISH_SCHEMA = vol.Schema({
    vol.Required(CONF_ENTITY_ID): cv.entity_id,
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

        topics = config.get(DOMAIN) 
        all_event_grids = {}

        @asyncio.coroutine
        def async_handle_event_grid_service(service_call):
            """Handle calls to event grid services."""
            topic_ids = service.extract_entity_ids(hass, service_call)
            LOGGER.debug("receiving service call for: %s", topic_ids)

            for topic_id in topic_ids:
                eventGrid = all_event_grids[topic_id]
                if service_call.service == SERVICE_AZURE_EVENT_GRID__PUBLISH_MESSAGE:
                    eventGrid.event_grid_publish_message(service_call)

        for entity_id, topic in topics.items():
            LOGGER.debug("setting up topic: %s",entity_id)
            eventGrid = AzureEventGrid(hass, topic[CONF_HOST], entity_id, topic[CONF_TOPIC_KEY])
            all_event_grids[entity_id] = eventGrid

        hass.services.async_register(
            DOMAIN, SERVICE_AZURE_EVENT_GRID__PUBLISH_MESSAGE, async_handle_event_grid_service,
            schema=MQTT_PUBLISH_SCHEMA)

    except Exception  as err:
        LOGGER.error("Error async_setup: %s", err)

    return True

class AzureEventGrid(object):
    """Implement the notification service for the azure event grid."""

    def __init__(self, hass, host, name, key):

        LOGGER.debug("Subscribing to %s", name)

        from azure.eventgrid import EventGridClient
        from msrest.authentication import TopicCredentials

        self.host = host
        self.name = name
        self.hass = hass 
        self.client = EventGridClient(TopicCredentials(key)) 

    def event_grid_publish_message(self, call):
        """Service to publish message to event grid."""
       
        try:
            data = call.data[ATTR_PAYLOAD]
            subject = call.data[ATTR_SUBJECT]
        
            eventType = call.data[ATTR_EVENT_TYPE]
            if eventType is None:
                eventType = DEFAULT_EVENT_TYPE
        
            dataVersion = call.data[ATTR_DATA_VERSION]
            if dataVersion is None:
                dataVersion = DEFAULT_DATA_VERSION
    
            #create the payload, with subject, data and type coming in from the notify platform
            payload = {
                'id' : str(uuid.uuid4()),
                'subject': subject,
                'data': data,
                'event_type': eventType,
                'event_time': datetime.utcnow().replace(tzinfo=pytz.UTC),
                'data_version': dataVersion
            }
 
            self.client.publish_events(self.host,events=[payload])

        except HomeAssistantError as err:
            LOGGER.error("Unable to send event to Event Grid: %s", err)
