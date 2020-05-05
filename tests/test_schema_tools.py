import unittest
from pathlib import Path

from hubmap_commons import schema_tools
from jsonschema import exceptions as jsonschema_exceptions


class SchemaToolsTestCase(unittest.TestCase):
    def setUp(self):
        self.sample_json = {
            'files': [
                {'rel_path': './trig_rnaseq_10x.py', 'type': 'unknown', 'size': 2198,
                 'sha1sum': '8cbba27b76806091ec1041bc7994dfc89c60a4e2'},
                {'rel_path': './utils.py', 'filetype': 'unknown', 'size': 5403,
                 'sha1sum': 'd910cf4a1d2b6ef928b449b906d79cab5dad1692'},
                {'rel_path': './scan_and_begin_processing.py', 'filetype': 'unknown', 'size': 6977,
                 'sha1sum': 'c5b981ec9ddb922c84ba67127485cfa6819f79da'},
                {'rel_path': './mock_ingest_vanderbilt.py', 'filetype': 'unknown', 'size': 3477,
                 'sha1sum': 'bf6fbb87e4dc1425525f91ce4c2238a2cc851d01'},
                {'rel_path': './mock_ingest_rnaseq_10x.py', 'filetype': 'unknown', 'size': 3654,
                 'sha1sum': '93f204cf3878e3095a83651d2046d5393008844c'}
            ],
            'dag_provenance': {'trig_codex.py': '0123456789abcdefABCDEF'}
        }
        self.bad_json = {
            'files': [
                {'rel_path': './trig_rnaseq_10x.py', 'type': 'unknown', 'size': 2198,
                 'sha1sum': '8cbba27b76806091ec1041bc7994dfc89c60a4e2'},
                {'rel_path': './utils.py', 'filetype': 'unknown', 'size': 5403,
                 'sha1sum': 'd910cf4a1d2b6ef928b449b906d79cab5dad1692'},
                {'rel_path': './scan_and_begin_processing.py', 'filetype': 'unknown', 'size': 6977,
                 'sha1sum': 'c5b981ec9ddb922c84ba67127485cfa6819f79da'},
                {'rel_path': './mock_ingest_vanderbilt.py', 'filetype': 'dubious', 'size': 3477,
                 'sha1sum': 'bf6fbb87e4dc1425525f91ce4c2238a2cc851d01'},
                {'rel_path': './mock_ingest_rnaseq_10x.py', 'filetype': 'unknown', 'size': 3654,
                 'sha1sum': '93f204cf3878e3095a83651d2046d5393008844'}
            ],
            'dag_provenance': {'trig_codex.py': '0123456789abcdefABCDEFG'}
        }

    def tearDown(self):
        from hubmap_commons import schema_tools
        schema_tools._SCHEMA_BASE_PATH = None
        schema_tools._SCHEMA_BASE_URI = None

    def test_assertion_json_matches_schema(self):
        base_path = str(Path(__file__).resolve().parent.parent / 'tests' / 'test_files')
        base_uri = 'http://schemata.hubmapconsortium.org/'

        lbl, jsondata = 'correct', self.sample_json
        try:
            result = schema_tools.assert_json_matches_schema(jsondata=jsondata,
                                                             base_path=base_path,
                                                             base_uri=base_uri,
                                                             schema_filename='dataset_metadata_schema.yml')
            self.assertTrue(result)
            print('assertion passed for {}'.format(lbl))
        except AssertionError as e:
            print('assertion failed for {}: {}'.format(lbl, e))

        lbl, jsondata = 'incorrect', self.bad_json
        with self.assertRaises(AssertionError):
            schema_tools.assert_json_matches_schema(jsondata=jsondata,
                                                    base_path=base_path,
                                                    base_uri=base_uri,
                                                    schema_filename='dataset_metadata_schema.yml')

    def test_assertion_json_matches_schema_optional_args_missing(self):
        lbl, jsondata = 'correct', self.sample_json
        with self.assertRaises(jsonschema_exceptions.SchemaError):
            schema_tools.assert_json_matches_schema(jsondata=jsondata,
                                                    schema_filename='dataset_metadata_schema.yml')

        lbl, jsondata = 'incorrect', self.bad_json
        with self.assertRaises(jsonschema_exceptions.SchemaError):
            schema_tools.assert_json_matches_schema(jsondata=jsondata,
                                                    schema_filename='dataset_metadata_schema.yml')

    def test_check_json_matches_schema(self):
        base_path = str(Path(__file__).resolve().parent.parent / 'tests' / 'test_files')
        base_uri = 'http://schemata.hubmapconsortium.org/'

        lbl, jsondata = 'correct', self.sample_json
        try:
            result = schema_tools.check_json_matches_schema(jsondata=jsondata,
                                                            base_path=base_path,
                                                            base_uri=base_uri,
                                                            schema_filename='dataset_metadata_schema.json')
            self.assertTrue(result)
            print('check passed for {}'.format(lbl))
        except (schema_tools.SchemaError, schema_tools.ValidationError) as e:
            print('check failed for {}: {}'.format(lbl, e))

        lbl, jsondata = ('incorrect', self.bad_json)
        with self.assertRaises(schema_tools.ValidationError):
            schema_tools.check_json_matches_schema(jsondata=jsondata,
                                                   base_path=base_path,
                                                   base_uri=base_uri,
                                                   schema_filename='dataset_metadata_schema.json')

    def test_check_json_matches_schema_optional_args_missing(self):
        lbl, jsondata = 'correct', self.sample_json
        with self.assertRaises(jsonschema_exceptions.SchemaError):
            schema_tools.check_json_matches_schema(jsondata=jsondata,
                                                   schema_filename='dataset_metadata_schema.json')

        lbl, jsondata = ('incorrect', self.bad_json)
        with self.assertRaises(jsonschema_exceptions.SchemaError):
            schema_tools.check_json_matches_schema(jsondata=jsondata,
                                                   schema_filename='dataset_metadata_schema.json')


if __name__ == '__main__':
    unittest.main()
