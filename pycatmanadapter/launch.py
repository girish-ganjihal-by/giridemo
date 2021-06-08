import os

from pycatmanadapter.connect.cps import build_cps_provider, adapter_cps_provider
from pycatmanadapter.connectors.jms import adapter_jms_connection
from pycatmanadapter.log import logger
from pycatmanadapter.process import handle_message

cps_config_path = os.path.join(os.path.dirname(__file__), 'connect/cps/adapter-cps.json')
build_cps_provider(adapter_cps_provider, cps_config_path)
cps_props = adapter_cps_provider.get_properties()

# todo: get listeners from configuration
listeners = [
    {
        "type": "jms",
        "queue": str(cps_props["jms.queue"])
    }
]


# initialize listeners
logger.info("Initializing listeners")

listener_threads = []
for l in listeners:
    logger.info("Initializing listener type=%s" % l["type"])
    target = None
    args = []

    if l["type"] == "jms":
        target = adapter_jms_connection.initialize_listener
        args = [
            l["queue"],
            
            handle_message
        ]

    # stomp listeners create their own daemon thread, so we don't need to manage
    # threading ourselves unless any new listeners that don't manage their own
    # threads are introduced
    #
    # listener_thread = threading.Thread(target=target, daemon=True, args=args)
    # listener_thread.start()
    # listener_threads.append(listener_thread)

    target(*args)

# main thread loop, 
# prefer to keep this simple until more is needed
# (see note above)
while True:
    pass