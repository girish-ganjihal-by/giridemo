import json
import os
import requests

from pycatmanadapter.log import logger

class CPSProvider:
    required_config_fields = [
        "PROTOCOL", 
        "HOST", 
        "PORT", 
        "ENVIRONMENT", 
        "APPLICATION_NAME", 
        "CATEGORIES", 
        "BASE_API_PATH"
    ]

    def __init__(self):
        # set up some defaults for optional fields
        self.config = {
            "USE_CACHING": True
        }

        self.is_initialized = False
        self.properties = None
        self.resources = {}

    def _initialization_check(self):
        if not self.is_initialized:
            raise Exception("Provider cannot get properties without first being initialized.")

    def _make_cps_request(self, method, path, headers={}):
        url = "%s://%s:%s%s%s" % (
            self.config["PROTOCOL"],
            self.config["HOST"],
            self.config["PORT"],
            self.config["BASE_API_PATH"],
            path
        )
        
        logger.debug("Calling CPS with URL=%s" % url)

        response = requests.request(
            method,
            url,
            headers=headers)

        return response

    def initialize_provider(self, config):
        missing_fields = [f for f in CPSProvider.required_config_fields if f not in config]
        if len(missing_fields) > 0:
            raise Exception("Missing required fields: %s" % ", ".join(missing_fields))

        logger.info("Initializing CPS Provider with config=%s" % config)

        self.config.update(config)
        self.is_initialized = True

    def get_resource(self, resource_name, media_type):
        logger.debug("Called CPS get resource for resource=%s" % resource_name)
        if not self.config["USE_CACHING"] or resource_name not in self.resources:
            self._initialization_check()

            logger.info("Fetching resource from CPS, resource=%s" % resource_name)

            path = "/application/%s/resources/%s?environment=%s" % (
                self.config["APPLICATION_NAME"],
                resource_name,
                self.config["ENVIRONMENT"]
            )
            
            if "LABEL" in self.config:
                path = path + "&label=" + self.config["LABEL"]

            headers = {
                "accept": media_type
            }
            
            response = self._make_cps_request("GET", path, headers=headers)
            self.resources[resource_name] = response.text
        else:
            logger.info("Returning CPS resource from local cache")
        # keep this generic as text instead of parsing for file formats, 
        # let the caller load the text as json, xml, etc..
        return self.resources[resource_name]

    def get_properties(self):
        if not self.config["USE_CACHING"] or self.properties is None:
            self._initialization_check()

            if "USE_LOCAL_MODE" not in self.config or self.config["USE_LOCAL_MODE"] is False:
                logger.info("Loading CPS properties from CPS service")

                path = "/application/%s/properties?environment=%s" % (
                    self.config["APPLICATION_NAME"],
                    self.config["ENVIRONMENT"]
                )

                if "LABEL" in self.config:
                    path = path + "&label=" + self.config["LABEL"]
                if "CATEGORIES" in self.config:
                    path = path + "&categories=" + self.config["CATEGORIES"]

                response = self._make_cps_request("GET", path)

                response_dict = json.loads(response.text)
                if "properties" in response_dict:
                    logger.debug("Fetched %s properties from CPS", len(response_dict["properties"]))
                    self.properties = response_dict["properties"]
                else:
                    raise Exception("Unexpected response format when getting properties")
            elif self.config["USE_LOCAL_MODE"] is True:
                logger.info("Loading CPS properties from local files")
                local_file_directory = self.config["LOCAL_FILES_DIRECTORY"]

                dirname = os.path.dirname(__file__)

                filenames =[ 
                    os.path.join(
                        dirname, 
                        local_file_directory, 
                        self.config["APPLICATION_NAME"],
                        self.config["ENVIRONMENT"],
                        self.config["LABEL"],
                        self.config["APPLICATION_NAME"] + ".yaml"
                    )
                ]

                if "CATEGORIES" in self.config:
                    categories = self.config["CATEGORIES"].split(",")
                    for category in categories:
                        if len(category) == 0:
                            continue

                        filenames.append(
                            os.path.join(
                                dirname, 
                                local_file_directory, 
                                self.config["APPLICATION_NAME"],
                                self.config["ENVIRONMENT"],
                                self.config["LABEL"],
                                "%s-%s.yaml" % (self.config["APPLICATION_NAME"], category)
                            )                            
                        )

                self.properties = {}
                for filename in filenames:
                    try:
                        with open(filename) as cpsf:
                            import yaml
                            y = yaml.safe_load(cpsf)
                            def flatten(d):
                                out = {}
                                for key, val in d.items():
                                    if isinstance(val, dict):
                                        val = [val]
                                    if isinstance(val, list):
                                        for subdict in val:
                                            deeper = flatten(subdict).items()
                                            out.update({key + '.' + key2: str(val2) for key2, val2 in deeper})
                                    else:
                                        out[key] = val
                                return out
                            self.properties.update(flatten(y))
                    except FileNotFoundError as exc:
                        logger.error("Could not find expected CPS file: %s" % exc)
                
                
        return self.properties