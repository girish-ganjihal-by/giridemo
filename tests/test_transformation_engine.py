import json
import os
import unittest
from argparse import Namespace

from pycatmanadapter.process.transformation.transformation_engine import TransformationEngine
current_dir = os.path.dirname(os.path.realpath(__file__))

class TestTransformationEngine(unittest.TestCase):

    def test_basic(self):
        file_path = current_dir + '/test_data/' + 'bydm-location-sample.json'
        payload = json.dumps(json.load(open(file_path, 'r')), indent=4)
        output = json.loads(TransformationEngine(payload).transform,  object_hook=lambda d: Namespace(**d))

        # fail this in a more specific way so we know what failed
        assert output is not None

        payload = output[0].payload[0]
        self.assertEqual(output[0].model, "product")
        self.assertEqual(payload.upc, "11")
        self.assertEqual(payload.id, "AG-3")
        self.assertEqual(payload.name, "Agricultura..AG-3")
        self.assertEqual(payload.width, 1.365)
        # the following line isn't needed. if it passed the above assertions, it passed
        # assert True

        # else:
        #     assert False

    def test_entity_not_supported(self):
        file_path = current_dir + '/test_data/' + 'notsuported-entity-sample.json'
        payload = json.dumps(json.load(open(file_path, 'r')), indent=4)
        self.assertRaises(FileNotFoundError, TransformationEngine, payload)
        # try:
        #     output = json.loads(TransformationEngine(payload).transform,  object_hook=lambda d: Namespace(**d))
        # except FileNotFoundError as FileNotFound:
        #     assert True
        # except Exception as Exp:
        #     assert False


if __name__ == "__main__":
    unittest.main()