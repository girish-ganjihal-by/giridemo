import json

from pycatmanadapter.connect.cps.cps_provider import CPSProvider

def build_cps_provider(cps_provider, config_path):
    # load config from path
    # configured once, includes options like
    # usecaching, host, port, environment, label, categories
    config = {}

    # load config from file
    with open(config_path) as json_file:
        config = json.load(json_file)

    # initialize singleton instance of provider
    cps_provider.initialize_provider(config)

adapter_cps_provider = CPSProvider()