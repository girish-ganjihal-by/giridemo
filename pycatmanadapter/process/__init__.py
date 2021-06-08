from pycatmanadapter.connect.message_store import adapter_message_store
from pycatmanadapter.connect.message_store.message_store_provider import get_message_header
from pycatmanadapter.log import logger
from pycatmanadapter.process.system import publish_message
from pycatmanadapter.process.Exception.api_connection_error import ApiConnectionError
from pycatmanadapter.process.Exception.internal_server_error import InternalServerError
from pycatmanadapter.process.transformation import transform_engine


def handle_message(message):

    msg_ref = None
    try:
        logger.info(
            "Received message in message handler. Truncated preview=%s" % message if len(message) < 100 else message[
                                                                                                             :100] + "...")
        # MS - Store Message (todo: add bulk pattern)
        logger.info("Extracting Message Header")
        message_header = get_message_header(message)

        logger.info("Adding inbound message to message store")
        msg_ref = adapter_message_store.add_message(message)
        adapter_message_store.add_message_event(msg_ref, "Accepted")

        # call transformation engine
        logger.info("Calling transformation engine")
        payload = transform_engine(message)

        if payload is not None:
            logger.info("Calling outbound endpoints")
            # this just calls to an interface
            # relying on the system api / layer to 
            # handle logic of how/where to publish
            # Catmanapi(payload, message_header)
            publish_message(payload, message_header)
            logger.info("All endpoints called successfully")
        adapter_message_store.add_message_event(msg_ref, "Processed")

    except BaseException as Ex:
        if msg_ref is not None:
            adapter_message_store.add_message_event(msg_ref, "ProcessedWithErrors", str(Ex))
        logger.error(Ex)
