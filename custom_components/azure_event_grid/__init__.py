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

from homeassistant.components import (http)
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
from datetime import datetime

REQUIREMENTS = ['azure.eventgrid==1.1.0', 'msrest==0.4.29']

#_LOGGER = logging.getLogger(__name__)
LOGGER = logging.getLogger('homeassistant.components.azure_event_grid')

DOMAIN = "azure_event_grid" 
EVENT_GRID_HTTP_ENDPOINT = '/api/event_grid/{topic_name}'

SERVICE_AZURE_EVENT_GRID__PUBLISH_MESSAGE = "publish_message"

CONF_TOPIC_KEY = 'topic key'

ATTR_SUBJECT = 'subject'
ATTR_EVENT_TYPE = 'eventtype'
ATTR_DATA_VERSION = 'dataversion'
ATTR_PAYLOAD = 'payload'
ATTR_PAYLOAD_TEMPLATE = 'payload_template'
# { "subject": "subject", "eventtype":"eventtype","payload":{}, "name": "second" }

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
    vol.Required(CONF_NAME): cv.string,
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
            topic_name = service_call.data[CONF_NAME]
            eventGrid = all_event_grids[topic_name]
            
            if service_call.service == SERVICE_AZURE_EVENT_GRID__PUBLISH_MESSAGE:
                eventGrid.event_grid_publish_message(service_call)

        for name, topic in topics.items():
            LOGGER.debug("setting up topic: %s", name)
            eventGrid = AzureEventGrid(hass, topic[CONF_HOST], name, topic[CONF_TOPIC_KEY])
            all_event_grids[name] = eventGrid

        hass.services.async_register(
            DOMAIN, SERVICE_AZURE_EVENT_GRID__PUBLISH_MESSAGE, async_handle_event_grid_service,
            schema=MQTT_PUBLISH_SCHEMA)

        hass.http.register_view(EventGridView())

    except Exception  as err:
        LOGGER.error("Error async_setup: %s", err)

    return True

class AzureEventGrid(object):
    """Implement the notification service for the azure event grid."""
    
    def __init__(self, hass, host, name, key):
        from azure.eventgrid import EventGridClient
        from msrest.authentication import TopicCredentials

        self.host = host
        self.name = name
        self.hass = hass 
        self.client = EventGridClient(TopicCredentials(key)) 

    def event_grid_publish_message(self, call):
        try:
            data = call.data[ATTR_PAYLOAD]
            subject = call.data[ATTR_SUBJECT]
        
            eventType = call.data[ATTR_EVENT_TYPE]
            if eventType is None:
                eventType = DEFAULT_EVENT_TYPE
        
            dataVersion = call.data[ATTR_DATA_VERSION]
            if dataVersion is None:
                dataVersion = DEFAULT_DATA_VERSION
    
            payload = {
                'id' : str(uuid.uuid4()),
                'subject': subject,
                'data': data,
                'event_type': eventType,
                'event_time': datetime.utcnow().replace(tzinfo=pytz.UTC),
                'data_version': dataVersion
            }
 
            self.client.publish_events(self.host,events=[payload])
            LOGGER.debug("message published for topic %s", self.name)

        except HomeAssistantError as err:
            LOGGER.error("Unable to send event to Event Grid: %s", err)

class EventGridView(http.HomeAssistantView):

    url = EVENT_GRID_HTTP_ENDPOINT
    name = 'api:event_grid'

    @asyncio.coroutine
    async def post(self, request, topic_name):
        from azure.eventgrid.models import SubscriptionValidationResponse

        data = await request.json() 

        for eventHubRequestEntry in data:
            LOGGER.debug("Processing EventGrid message")

            if eventHubRequestEntry['eventType'] == 'Microsoft.EventGrid.SubscriptionValidationEvent':
                #[{'id': '58f9787a-xxxx-xxxx-xxxx-4fbb31c69398', 'topic': '/subscriptions/f2da982c-fc6f-xxxx-ad1e-46a186f9fa84/resourceGroups/eventgridtest/providers/Microsoft.EventGrid/topics/keestesttopic', 'subject': '', 'data': {'validationCode': '09E2E428-xxxx-xxxx-xxxx-BCD800D109A3', 'validationUrl': 'https://rp-westeurope.eventgrid.azure.net/eventsubscriptions/test/validate?id=09E2E428-xxxx-xxxx-xxxx-BCD800D109A3&t=2018-06-10T12:23:49.7126308Z&apiVersion=2018-05-01-preview&token=xxxx%2fXT1Uy8ndIfaro1mo%3d'}, 'eventType': 'Microsoft.EventGrid.SubscriptionValidationEvent', 'eventTime': '2018-06-10T12:23:49.7126308Z', 'metadataVersion': '1', 'dataVersion': '2'}]

                return self.json({  
                    'validationResponse': eventHubRequestEntry['data']['validationCode']
                })

            else 
                # [{'id': '0919d8a2-85d5-4966-xxxx-4f477c4f86e5', 'subject': 'subject', 'data': {}, 'eventType': 'eventtype', 'eventTime': '2018-06-10T13:08:42.761632Z', 'dataVersion': '1', 'metadataVersion': '1', 'topic': '/subscriptions/f2da982c-xxxx-xxxx-xxxx-46a186f9fa84/resourceGroups/eventgridtest/providers/Microsoft.EventGrid/topics/keestesttopic'}]
                
                # Todo do simething with this message

        raise Exception('Unknown request on EventGrid api')