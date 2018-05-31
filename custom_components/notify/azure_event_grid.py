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
from homeassistant.components.notify import (ATTR_DATA, ATTR_TITLE, ATTR_TITLE_DEFAULT, PLATFORM_SCHEMA, BaseNotificationService)
import homeassistant.helpers.config_validation as cv
from homeassistant.remote import JSONEncoder

REQUIREMENTS = ['azure.eventgrid==0.1.0', 'msrest==0.4.29']

_LOGGER = logging.getLogger(__name__)

CONF_TOPIC_KEY = 'topic key'
CONF_CONTEXT = 'context'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOPIC_KEY): cv.string,
    vol.Optional(CONF_CONTEXT, default=dict()): vol.Coerce(dict)
})

def get_service(hass, config, discovery_info=None):
    from azure.eventgrid import EventGridClient
    from msrest.authentication import TopicCredentials

    #create the context dict, puts the HASS config in there as well as a custom piece if configured.
    context = {
        'hass': json.loads(json.dumps(hass.config.as_dict(), cls=JSONEncoder)),
        'custom': config[CONF_CONTEXT]
        }
    #create credentials from the key, and create the event_grid_client with the creds.
    credentials = TopicCredentials(config[CONF_TOPIC_KEY])
    event_grid_client = EventGridClient(credentials)

    return AzureEventGrid(config[CONF_HOST], event_grid_client, context)

class AzureEventGrid(BaseNotificationService):
    """Implement the notification service for the azure event grid."""

    def __init__(self, endpoint, event_grid_client, context):
        """Initialize the service."""
        self.endpoint = endpoint
        self.client = event_grid_client
        self.context = context

    def send_message(self, message="", **kwargs):
        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
        data = kwargs.get(ATTR_DATA)

        #create the payload, with Title, Message and Data coming in from the notify platform
        payload = {
            'id' : str(uuid.uuid4()),
            'subject': title,
            'data': {
                'message': message,
                'data': data,
                'context': self.context
            },
            'event_type': 'HassEventType',
            'event_time': datetime.utcnow().replace(tzinfo=pytz.UTC),
            'data_version': 1
        }

        #Send the event to event grid
        try:
            self.client.publish_events(
                self.endpoint,
                events=[payload]
            )
        except:
            _LOGGER.error("Unable to send event to Event Grid")