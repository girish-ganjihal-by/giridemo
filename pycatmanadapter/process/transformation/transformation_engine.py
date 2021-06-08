import json
import os
from types import SimpleNamespace as Namespace
import yaml

from pycatmanadapter.log import logger
from pycatmanadapter.process.transformation import constants
from pycatmanadapter.process.transformation.model_transformer import ModelTransformer

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
current_dir = os.path.dirname(os.path.realpath(__file__))


class TransformationEngine:

    # TransformationEngine Constructor
    # Parameters:
    #
    # payload : Input payload

    def __init__(self, payload):
        self.transform = self.__transformation_driver(payload)

    # Responsible for invoking transformation
    #
    # Parameters:
    #
    # input : Payload

    def __transformation_driver(self, input):
        output = None
        output_list = []

        # Load input payload
        payload = self.__load_input_payload(input)
        logger.debug("Input payload loaded as object")

        # Set input model type
        entity_type = payload.header.type
        logger.debug("Source Model Type : " + entity_type)

        # Load model config yaml file
        config = self.__load_config_file(entity_type)
        logger.debug("Model config yaml loaded as object")

        # for mappings in config file create output object
        logger.debug("Started processing each mapping")
        for core_map in config.get(constants.MAPPING_ROOT):
            output_dict = dict()
            output_dict[constants.OUTPUT_MODEL_TAG] = core_map.get(constants.MODEL_MAPPING_FIELD).get(
                constants.TARGET_MODEL_FIELD)
            action_code = eval('payload.' + entity_type + '[0].documentActionCode').lower()
            output_dict[constants.OUTPUT_ACTION_TAG] = action_code
            data = eval('payload.' + entity_type)
            output_dict[constants.OUTPUT_PAYLOAD_TAG] = ModelTransformer(data, core_map.get(
                constants.MODEL_MAPPING_FIELD)).map
            output_list.append(output_dict)
        logger.debug("Processing complete using mapping file")

        # Dump output object
        output = json.dumps(output_list, indent=4)
        return output

    # Responsible for loading configuration files
    #
    # Parameters:
    #
    # model_name : Target model name for which configuration needs to be fetched

    def __load_config_file(self, model_name):
        config_path = current_dir + constants.CONFIG_FOLDER + model_name + constants.CONFIG_FILE_SUFIX
        config = yaml.safe_load(open(config_path, 'r'))
        return config

    # Responsible for loading input payload as objects
    #
    # Parameters:
    #
    # input : Payload

    def __load_input_payload(self, input):
        payload = json.loads(input, object_hook=lambda d: Namespace(**d))
        return payload
