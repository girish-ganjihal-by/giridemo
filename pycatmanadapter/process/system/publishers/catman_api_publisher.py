import json
import requests
from retry.api import retry_call

from pycatmanadapter.connect.cps import adapter_cps_provider
from pycatmanadapter.log import logger
from pycatmanadapter.process.Exception.api_connection_error import ApiConnectionError
from pycatmanadapter.process.Exception.internal_server_error import InternalServerError
from pycatmanadapter.process.system.publishers.http_publisher import HttpPublisher
from pycatmanadapter.process.system.publishers.http_publisher import get_error_message


class CatmanApiPublisher:
    def __init__(self, publisher_name, cps_props):
        self.base_publisher = HttpPublisher(publisher_name, cps_props)

    def publish_message(self, message, message_header):
        # load publisher config for this entity

        message_type = message_header["type"]
        api_retry_count = self.base_publisher.api_retry_count
        retry_delay = self.base_publisher.retry_delay

        input_ = json.loads(message)
        for item in input_:
            payload = item['payload']
            if len(payload) == 1:
                if message_type == "location":
                    api_response = retry_call(self._upsert_store, fargs=[payload[0], message_type],
                                            exceptions=(ApiConnectionError, InternalServerError),
                                            tries=api_retry_count, delay=retry_delay)                    
                else:
                    # todo: add the retry
                    api_response = self._upsert_entity(payload[0], message_type)
            else:
                dbkey = retry_call(self.file_upload, fargs=payload,
                                   exceptions=(ApiConnectionError, InternalServerError),
                                   tries=api_retry_count, delay=retry_delay)
                dbkey_afer_import = retry_call(self.data_transfer_request_for_import, fargs=[message_type, dbkey],
                                               exceptions=(ApiConnectionError, InternalServerError),
                                               tries=api_retry_count, delay=retry_delay)
                api_response = retry_call(self.data_transfer_req_process, fargs=dbkey_afer_import,
                                          exceptions=(ApiConnectionError, InternalServerError),
                                          tries=api_retry_count, delay=retry_delay)
                logger.debug("Post Batch Prod Api calls - dbkey :"+str(dbkey)+" dbkey afer file import :"+str(dbkey_afer_import)+" api response :"+str(api_response))

        return api_response

    def create_dummy_floorplan(self,dbkey):
        data = {
            "value1": dbkey,			# Store Number
            "name": "Elkjøp Ullevål",	# Store Name
            "desc1": "NO",			# Store Country
            "desc2": "SNA ",		# Company
            "desc3": "BIG",			# Format
            "desc6": "Stoa Vest",		# Address1
            "desc7": "ARENDAL",		# City
            "desc8": "4848",		# Postal Code
            "desc9": "37022400",		# Phone
            #below was assigned null in the storeplan doc .. have changed it to "" as was hitting parsing exception
            "desc10": "",			# Region
            "desc11": "20150121",		# Date Effective From
            "desc12": "00000000",		# Date Effective To
            "width": 1000,			# Hard coded value. Config setting?
            "ceilingHeight": 360,		# Hard coded value.
            "depth": 1000,               # Hard coded value.
            "drawFloor" : 1,             # Hard coded value.
            "floorColor": 16777215       # Hard coded value.
        }
        return data

    def _get_db_key_to_update(self, message, message_type):
        cps_props = adapter_cps_provider.get_properties()
        entity_url_path = cps_props["workflows.%s.publisherOptions.path" % message_type]

        db_key = None

        entity_filter = cps_props["workflows.%s.publisherOptions.filter" % message_type]
        entity_filter_field = cps_props["workflows.%s.publisherOptions.filterField" % message_type]

        if entity_filter_field not in message:
            raise Exception("Filter field does not exist on object")
        filter_value = message[entity_filter_field]
        db_keys = self.base_publisher.get_entity(entity_url_path + entity_filter % filter_value)

        if db_keys:
            
            last_ele = db_keys[len(db_keys) - 1]

            # double check that this logic below is needed...
            # seems like it was different between product and store
            if "dbKey" in last_ele:
                db_key = last_ele['dbKey']
            elif "dbkey" in last_ele:
                db_key = last_ele['dbkey']
            else:
                # todo: clean this up, this is here for 
                # get user role that won't give a db key
                # for some reason
                db_key = last_ele

        return db_key

    def _update_entity(self, message, message_type, db_key):
        cps_props = adapter_cps_provider.get_properties()
        entity_url_path = cps_props["workflows.%s.publisherOptions.path" % message_type]

        # documentation says the object to be PUT should be updated with the dbkey
        # do we need to do that?

        # this varies from one environment to the other
        # one is entity/<dbkey>
        # other is entity?dbKey=<dbkey>
        update_path = "%s/%s" % (entity_url_path, db_key)
        return self.base_publisher.update_entity(update_path, message)

    def _upsert_entity(self, message, message_type):
        cps_props = adapter_cps_provider.get_properties()
        entity_url_path = cps_props["workflows.%s.publisherOptions.path" % message_type]

        # first try getting the object
        db_key = self._get_db_key_to_update(message, message_type)
        if db_key is not None:
            # if it's found, update it
            result = self._update_entity(message, message_type, db_key)
        else:
            # if it's not found, insert it
            result = self.base_publisher.add_entity(message, message_type)

        return result

    def _upsert_store(self, message, message_type):
        cps_props = adapter_cps_provider.get_properties()
        result = None

        # todo: move below to configuration?
        store_num = message["storenumber"]
        filter_get_fp="?$filter=value1 eq %s" % (store_num)
        floorplan_url = cps_props["workflows.floorplan.publisherOptions.path"]

        # Check for existence - get
        db_key = self._get_db_key_to_update(message, message_type)
        
        if db_key: # store exists
            # update store
            store_result = self._update_entity(message, message_type, db_key)

            #Fetch Floor Plan

            print("floorplan_url",floorplan_url+filter_get_fp)
            response = self.base_publisher.get_entity(floorplan_url + filter_get_fp)
            print("FloorPlan Response", response)
            
            # revisit this when there has been a floorplan created for this store

        else: # store does not exist yet
            # if no store is available execute below sequence for creating new stores and other relations
            # this call fails on md1npdvjdapc01, had to use md1npdvcatman1 to get past this
            result = self.base_publisher.add_entity(message, message_type)
            # clean this up later
            if result: 
                dbkey = result['dbKey']

                #Create a dummy floor plan for the store
                dummy_floorplan = self.create_dummy_floorplan(dbkey)
                dummy_floorplan_result = self.base_publisher.add_entity(dummy_floorplan, "floorplan")

                if dummy_floorplan_result:
                    dummy_floorplan_db_key = dummy_floorplan_result['dbKey']
                    print("Response DBKey",dummy_floorplan_db_key)

                    # warning there is a gap here.
                    # see documentation 5.c. about 
                    # creating association between store and floorplan

                    #User Api calls need to be added here
                    
                    # Check the existence of role ELK_role_stores
                    # how does this get associated with the store? 
                    # todo: move this out of this function
                    store_users_role = {
                        "roleID": 0,
                        "role": "ELK_role_stores-test1",
                        "name": "Store Users (ROLE)",
                        "description": "Store Users (ROLE)",
                        "businessObject": "null",
                        "objectDescription": "null",
                        "securityLevel": 0
                    }

                    user_role_db_key = self._get_db_key_to_update(store_users_role, "userRole")
                    # note: for some reason in this env, it won't let you select dbkey
                    # so for now, this is just returning the object
                    if not user_role_db_key: # role is not found, we need to create it
                        user_role_result = self.base_publisher.add_entity(store_users_role, "userRole")
                    
                    # now that role is created, create a store user
                    # ????? should this go in the if above?
                    # not clear in document, but doesn't make sense to create a user every time
                    # also this call is resulting in 500s
                    store_user = {
                        "password": "testpwd23423",
                        "userName": "12346@elkjop.no",
                        "email": "12346@elkjop.no",
                        "isWindowsUser": 0,
                        "isLocked": 0
                    }
                    store_user_result = self.base_publisher.add_entity(store_user, "user")

                    # assign the store user to to the role
                    # GAP (see document)

        return result

    def file_upload(self, input_):
        url = self.catman_base_url + "/Files/api/" + self.api_version + "/odata/files/upload"
        headers = {}

        headers.update({
            "Accept": 'application/json',
            "Authorization": self.token
        })
        data = {
            'FolderType': '1',
            'FileName': 'testFile4'
        }

        files = {'file': json.dumps(input_, indent=4)}

        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            json_data = response.json()
        except ConnectionError as Ex:
            # Raise api connection error such that it can be retried
            raise ApiConnectionError(Ex)
        if str(response.status_code)[0:1] == '5':
            # Raise server error such that it can be retried
            raise InternalServerError(get_error_message(json_data))
        elif str(response.status_code)[0:1] != '2':
            raise Exception(get_error_message(json_data))

        db_key = None
        if json_data:
            db_key = json_data['dbKey']
        return db_key

    def data_transfer_request_for_import(self, message_type, db_key):
        url = self.catman_base_url + "/DataTransfer/api/" + self.api_version + "/odata/Requests"
        headers = {}
        headers.update({
            "Accept": 'application/json',
            "Authorization": self.token,
            "Content-Type": 'application/json-patch+json'
        })

        db_parent_prc_key = self.cps_props["workflows.%s.publisherOptions.db_parent_prc_key"]

        data = {
            "dbParentFileKey": db_key,
            "dbParentProcessKey": db_parent_prc_key,
            "dbParentAccountKey": "0"
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            json_data = response.json()
        except ConnectionError as Ex:
            # Raise api connection error such that it can be retried
            raise ApiConnectionError(Ex)
        if str(response.status_code)[0:1] == '5':
            # Raise server error such that it can be retried
            raise InternalServerError(get_error_message(json_data))
        elif str(response.status_code)[0:1] != '2':
            raise Exception(get_error_message(json_data))

        dbkey_after_import = None
        if json_data:
            dbkey_after_import = json_data['dbKey']
        return dbkey_after_import

    def data_transfer_req_process(self, db_key):
        value = ''
        url = self.catman_base_url + "/DataTransfer/api/" + self.api_version + "/odata/Requests/" + str(db_key) + "/Process"

        headers = {}
        headers.update({
            "Accept": 'application/json',
            "Authorization": self.token
        })

        try:
            response = requests.post(url, headers=headers)
            json_data = response.json()
        except ConnectionError as Ex:
            # Raise api connection error such that it can be retried
            raise ApiConnectionError(Ex)
        if str(response.status_code)[0:1] == '5':
            # Raise server error such that it can be retried
            raise InternalServerError(get_error_message(json_data))
        elif str(response.status_code)[0:1] != '2':
            raise Exception(get_error_message(json_data))


        if json_data:
            value = json_data['value']
        return str(value)