"""
Azure Event Grid platform for notify component.

For more details about this platform, please refer to the documentation at
TBD

Created by Eduard van Valkenburg
"""

import logging
import json
import base64
import voluptuous as vol
from datetime import datetime
import pytz
import uuid

from homeassistant.const import (CONF_HOST, CONF_PLATFORM, CONF_NAME)
from homeassistant.components.notify import (ATTR_DATA, PLATFORM_SCHEMA, BaseNotificationService)
import homeassistant.helpers.config_validation as cv
from homeassistant.remote import JSONEncoder

REQUIREMENTS = ['azure.eventgrid==0.1.0', 'msrest==0.4.29']

_LOGGER = logging.getLogger(__name__)

CONF_TOPIC_KEY = 'topic key'
CONF_SUBJECT = 'subject'
CONF_EVENT_TYPE = 'eventtype'
CONF_EVENT_TYPE_DEFAULT = 'HomeAssistant'
CONF_DATA_VERSION = 'dataversion'
CONF_DATA_VERSION_DEFAULT = 1

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Inclusive(CONF_TOPIC_KEY,'authentication'): cv.string
})

def get_service(hass, config, discovery_info=None):
    from azure.eventgrid import EventGridClient
    from msrest.authentication import TopicCredentials

    credentials = TopicCredentials(config[CONF_TOPIC_KEY])
    event_grid_client = EventGridClient(credentials)

    return AzureEventGrid(config[CONF_HOST], event_grid_client)

class AzureEventGrid(BaseNotificationService):
    """Implement the notification service for the azure event grid."""

    def __init__(self, endpoint, event_grid_client):
        """Initialize the service."""
        self.endpoint = endpoint
        self.client = event_grid_client

    def send_message(self, message="", **kwargs):
        data = kwargs.get(ATTR_DATA)
        subject = data.get(CONF_SUBJECT)
        eventType = data.get(CONF_EVENT_TYPE, CONF_EVENT_TYPE_DEFAULT)
        dataVersion = data.get(CONF_DATA_VERSION, CONF_DATA_VERSION_DEFAULT)

        #create the payload, with subject, data and type coming in from the notify platform
        payload = {
            'id' : str(uuid.uuid4()),
            'subject': subject,
            'data': message,
            'event_type': eventType,
            'event_time': datetime.utcnow().replace(tzinfo=pytz.UTC),
            'data_version': dataVersion
        }

        #Send the event to event grid
        try:
            self.client.publish_events(
                self.endpoint,
                events=[payload]
            )
        except HomeAssistantError as err:
            _LOGGER.error("Unable to send event to Event Grid: %s", err)
