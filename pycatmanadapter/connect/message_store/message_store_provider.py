import json
import requests
import socket

from retry.api import retry_call

from pycatmanadapter.log import logger
from pycatmanadapter.connect.cps import adapter_cps_provider
from pycatmanadapter.process.Exception.api_connection_error import ApiConnectionError
from pycatmanadapter.process.Exception.internal_server_error import InternalServerError


class MessageStoreProvider:
    request_format = "application/json"
    required_config_fields = [
        "store.protocol",
        "store.host",
        "store.port",
        "store.basePath",
        "store.clientId",
        "store.clientSecret",
        "store.serviceType",
        "store.serviceName",
        "store.serviceInstance",
        "store.serviceVersion",
        "store.endpointType",
        "store.endpointName"
    ]

    def __init__(self):
        self.is_initialized = False

    def _form_request_body(self, message):
        cps_props = adapter_cps_provider.get_properties()

        message_json = json.loads(message)
        message_header = message_json['header']
        message_body = message_json[str(message_header['type'])]

        if message_header['type'] == "item":
            document_id = message_body[0]["itemId"]["additionalTradeItemId"][0]["value"]
        elif message_header['type'] == "location":
            document_id = message_body[0]["locationId"]
        else:
            document_id = "DEFAULT"
        # todo: temp until header parsing is in
        import uuid
        random_id = uuid.uuid4()

        return json.dumps({
            "service": {
                "type": cps_props["store.serviceType"],
                "name": cps_props["store.serviceName"],
                "instance": cps_props["store.serviceInstance"],
                "hostName": socket.gethostname(),
                "namedVersion": cps_props["store.serviceVersion"]
            },
            "endpoint": {
                "type": cps_props["store.endpointType"],
                "name": cps_props["store.endpointName"]
            },
            "model": {
                "type": "BYDM" # todo: what goes here
            },
            "message": { # todo: needs message header parsing, also need to know if this is bydm or gs1
                "category": "Notification",
                "type": str(message_json['header']['type']),
                "format": "json",
                "namedVersion": str(message_header['messageVersion']),
                "id": str(random_id),
                "documentId": document_id,
                "customId" : "custom",
                "timeStamp": "2016-02-28T16:40:57.090Z",
                "sender":"SAP-GLOBAL",
                "receivers": ["CATMANA.GLOBAL"],
                "body": message
            },
            "sourceMessageRef": {
                "sender": str(message_header['sender']),
                "messageId": str(message_header['messageId']),
                "documentId": document_id
            },
            "event": {
                "status": "Received",
                "isReplayable": False
            },
            "testMessage":False
        })

    def _make_message_store_request(self, method, path, **kwargs):
        cps_props = adapter_cps_provider.get_properties()

        url = "%s://%s:%s%s" % (
            cps_props["store.protocol"],
            cps_props["store.host"],
            cps_props["store.port"],
            path
        )

        headers = {}
        if "headers" in kwargs:
            headers = kwargs["headers"]
        headers.update({
            "accept": MessageStoreProvider.request_format,
            "client_id": cps_props["store.clientId"],
            "client_secret": cps_props["store.clientSecret"],
            "content-type": MessageStoreProvider.request_format
        })

        request_kwargs = {
            "headers": headers
        }

        if "data" in kwargs:
            request_kwargs["data"] = kwargs["data"]
        try:
            response = requests.request(
                method,
                url,
                **request_kwargs
            )
        except Exception as Ex:
            # Raise api connection error such that it can be retried
            raise ApiConnectionError(Ex)
        if str(response.status_code)[0:1] == '5':
            # Raise server error such that it can be retried
            raise InternalServerError("Message Store request failed with status=%s message=%s" % (response.status_code, response.content))
        elif str(response.status_code)[0:1] != '2':
            raise Exception("Message Store request failed with status=%s message=%s" % (response.status_code, response.content))

        return json.loads(response.content)

    def initialize_provider(self):
        # get props from CPS
        cps_props = adapter_cps_provider.get_properties()
        
        # validate we have the stuff we need
        missing_fields = [f for f in MessageStoreProvider.required_config_fields if f not in cps_props]
        if len(missing_fields) > 0:
            raise Exception("Missing required fields: %s" % ", ".join(missing_fields))

        self.is_initialized = True

    def add_message(self, message):
        cps_props = adapter_cps_provider.get_properties()

        api_retry_count = int(cps_props["api.retryCount"])
        retry_delay = int(cps_props["api.retryDelay"])

        if cps_props["store.enabled"] == str(False):
            logger.info("Message store is disabled. Skipping add message operation")
            return

        if not self.is_initialized:
            self.initialize_provider()

        data = self._form_request_body(message)

        response = retry_call(self._make_message_store_request,
                              fargs=["POST", cps_props["store.basePath"] + "/messages"], fkwargs= {"data" : data},
                              exceptions=(ApiConnectionError, InternalServerError),
                              tries=api_retry_count, delay=retry_delay)
        return response

    def add_message_event(self, msg_ref, status, error=None, is_replayable=False):

        cps_props = adapter_cps_provider.get_properties()
        api_retry_count = int(cps_props["api.retryCount"])
        retry_delay = int(cps_props["api.retryDelay"])

        if cps_props["store.enabled"] == str(False):
            logger.info("Message store is disabled. Skipping add event operation")
            return

        if not self.is_initialized:
            self.initialize_provider()

        request_body = {
            "status": status,
            "isReplayable": is_replayable
        }

        if error is not None:
            # TODO: Error codes for adapter
            error_body = {
                "code" : "CATMANA-ERROR",
                "desc" : str(error)
            }
            request_body["error"] = error_body

        # "{'id': 8, 'meta': {'self': '/messagestore/api/v3/messages/8'}}"
        if 'meta' not in msg_ref or 'self' not in msg_ref['meta']:
            raise Exception("Invalid msg ref passed")

        request_body = json.dumps(request_body)

        response = retry_call(self._make_message_store_request,
                              fargs=["POST", msg_ref["meta"]["self"] + "/events"], fkwargs={"data": request_body},
                              exceptions=(ApiConnectionError, InternalServerError),
                              tries=api_retry_count, delay=retry_delay)
        return response


def get_message_header(message):        
    message_json = json.loads(message)
    message_header = message_json['header']
    return message_header