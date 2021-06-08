import json
import os
from pycatmanadapter.connect import cps
from pycatmanadapter.process.system import publishers
from pycatmanadapter.connect.cps import adapter_cps_provider
import requests
from pycatmanadapter.log import logger
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# static interface
# may be moved to queue/api later
def publish_message(message, message_header):
    # get message type
    message_type = message_header["type"]
    cps_props = adapter_cps_provider.get_properties()
        
    # get publisher configuration for message type
    publisher_name = get_workflow_publisher_for_message_type(cps_props, message_type)

    # logic to instantiate/dynamically call publisher for this message

    # for now bypass the above and just call the catman api publisher
    from pycatmanadapter.process.system.publishers.catman_api_publisher import CatmanApiPublisher
    publisher = CatmanApiPublisher(publisher_name, cps_props)
    publisher.publish_message(message, message_header)

def get_workflow_publisher_for_message_type(props, message_type):
    return props["workflows.%s.publisher" % message_type]