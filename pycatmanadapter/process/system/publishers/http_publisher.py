import json
import requests
from retry.api import retry_call

from pycatmanadapter.connect.cps import adapter_cps_provider
from pycatmanadapter.process.Exception.api_connection_error import ApiConnectionError
from pycatmanadapter.process.Exception.internal_server_error import InternalServerError


"""
This should be just a light wrapper around requests module,
for basic http functionality, include OAuth handling
Should use the workflow configuration to know method, path, etc by entity
Use the publisher configuration to know base endpoint config like host/port/protocol

workflow_configuration allows config to be injectable (sub workflow case)

oauth happens in this class if configured
"""
def get_error_message(json_data):
    return json_data["errors"][0]['errorMessage']

class HttpPublisher:
    def __init__(self, publisher_name, cps_props):
            self.api_retry_count = int(cps_props["api.retryCount"])
            self.retry_delay = int(cps_props["api.retryDelay"])
            self.api_timeout = int(cps_props["api.timeout"])
            self.disable_ssl_cert_verification = False
            if "publishers.%s.disable_ssl_cert_verification" % publisher_name in cps_props:
                if cps_props["publishers.%s.disable_ssl_cert_verification" % publisher_name].lower() == str(True).lower():
                    self.disable_ssl_cert_verification = True

            self.catman_base_url = "%s://%s:%s" % (
                cps_props["publishers.%s.protocol" % publisher_name],
                cps_props["publishers.%s.host" % publisher_name],
                cps_props["publishers.%s.port" % publisher_name]
            )

            self.token_gen_url = "%s://%s:%s%s" % (
                cps_props["publishers.%s.protocol" % publisher_name],
                cps_props["publishers.%s.host" % publisher_name],
                cps_props["publishers.%s.authorisation.port" % publisher_name],
                cps_props["publishers.%s.authorisation.resourcePath" % publisher_name]
            )

            self.auth_context = {
                'username':  cps_props['publishers.%s.authorisation.username' % publisher_name],
                'client_id': cps_props['publishers.%s.authorisation.client_id' % publisher_name],
                'password': cps_props['publishers.%s.authorisation.password' % publisher_name],
                'grant_type': cps_props['publishers.%s.authorisation.grantType' % publisher_name],
                'scope': cps_props['publishers.%s.authorisation.scope' % publisher_name]        
            }

            self.api_version = "v1"
            self.token = self.token_req()            
            self.token = retry_call(self.token_req,
                                    exceptions=(ApiConnectionError, InternalServerError),
                                    tries=self.api_retry_count, delay=self.retry_delay)            

    def _make_request(self, method, path, message=None, headers={}):
        cps_props = adapter_cps_provider.get_properties()
        url = self.catman_base_url + path
        
        headers.update({
            "Accept": 'application/json',
            "Authorization": self.token,
            "Content-Type": 'application/json-patch+json'
        })  

        rkwargs = {
            "headers": headers
        }

        if message is not None:
            rkwargs["json"] = message

        if self.disable_ssl_cert_verification == True:
            rkwargs["verify"] = False

        try:
            response = requests.request(method, url, **rkwargs)
            if len(response.content):
                res_json_data = response.json()
            else:
                res_json_data = ""
        except ConnectionError as Ex:
            # Raise api connection error such that it can be retried
            raise ApiConnectionError(Ex)

        if str(response.status_code)[0:1] == '5':
            # Raise server error such that it can be retried
            raise InternalServerError(get_error_message(res_json_data))
        elif str(response.status_code) == '404':
            # don't raise an exception for 404,
            # at least in case of catman
            # it means the request was fine but
            # the resource was not found
            pass
        elif str(response.status_code)[0:1] != '2':
            raise Exception(get_error_message(res_json_data))                      
        return res_json_data        

    # for the simplest case
    def publish_message(self, message, message_type):
        cps_props = adapter_cps_provider.get_properties()
        path = cps_props["workflows.%s.publisherOptions.path" % message_type]

        return self._make_request("POST", path, message=message)

    def get_entity(self, path):
        response_value = None
        response = self._make_request("GET", path)

        if "value" in response:
            response_value = response["value"]
        
        return response_value

    def update_entity(self, path, message):
        return self._make_request("PUT", path, message=message)

    def add_entity(self, message, message_type):
        cps_props = adapter_cps_provider.get_properties()
        path = cps_props["workflows.%s.publisherOptions.path" % message_type]
        
        return self._make_request("POST", path, message=message)          

    def token_req(self):
        headers = {}
        headers.update({
            "content-type": 'application/x-www-form-urlencoded'
        })

        data = self.auth_context
        print('data',data)
        request_kwargs = {
            "headers": headers
        }
        method = 'post'
        request_kwargs["data"] = data

        if self.disable_ssl_cert_verification == True:
            request_kwargs["verify"] = False        

        try:
            response = requests.request(
                method,
                self.token_gen_url,
                **request_kwargs
            )
            json_data = response.json()
        except ConnectionError as Ex:
            # Raise api connection error such that it can be retried
            raise ApiConnectionError(Ex)
        if str(response.status_code)[0:1] == '5':
            # Raise server error such that it can be retried
            raise InternalServerError(self.get_error_message(json_data))
        elif str(response.status_code)[0:1] != '2':
            raise Exception(get_error_message(json_data))

        access_token = None
        json_data = response.json()
        if json_data:
            fetched_access_token = json_data['access_token']
            access_token = "Bearer " + fetched_access_token
        return access_token


