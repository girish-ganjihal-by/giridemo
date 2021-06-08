from stomp import Connection11, ConnectionListener
from stomp.exception import ConnectFailedException
import requests

from pycatmanadapter.connect.cps import adapter_cps_provider
from pycatmanadapter.log import logger


class AdapterListener(ConnectionListener):
    def __init__(self, callback):
        self.callback = callback
    def on_error(self, frame):
        print('received an error "%s"' % frame.body)
    def on_message(self, headers, body):
        logger.info("Received message in jms listener")

        if not hasattr(self, 'callback'):
            logger.warn("No callback configured for this listener")
        else:
            self.callback(body)

class AdapterConnection():
    def __init__(self):
        self.conn = None

    def _check_connection(self):
        cps_props = adapter_cps_provider.get_properties()
        if self.conn is None:
            self.conn = Connection11([(cps_props["jms.host"], cps_props["jms.port"])])
        if not self.conn.is_connected():
            try:
                self.conn.connect(cps_props["jms.username"], cps_props["jms.password"], wait=True)
            except ConnectFailedException as exc:
                logger.error("Failed to connect to activemq")
                raise exc

    def initialize_listener(self, queue_name, message_handler):
        self._check_connection()

        self.conn.set_listener('', AdapterListener(message_handler))
        self.conn.subscribe(queue_name, 123)

    def publish_message(self, queue_name, message):
        self._check_connection()
        self.conn.send(queue_name, message)

adapter_jms_connection = AdapterConnection()


