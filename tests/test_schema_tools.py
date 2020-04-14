import unittest
import configparser
import sys
import os

from pathlib import Path

from hubmap_commons.provenance import Provenance
from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.entity import Entity
from hubmap_commons import schema_tools


class MyTestCase(unittest.TestCase):
    def setUp(self):
        base_path = str(Path(__file__).resolve().parent.parent / 'tests' / 'test_files')

        base_uri = 'http://schemata.hubmapconsortium.org/'

        sample_json = {
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
        bad_json = {
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

        for lbl, jsondata in [('correct', sample_json), ('incorrect', bad_json)]:
            try:
                schema_tools.assert_json_matches_schema(jsondata, 'dataset_metadata_schema.yml')
                print('assertion passed for {}'.format(lbl))
            except AssertionError as e:
                print('assertion failed for {}: {}'.format(lbl, e))

            try:
                schema_tools.check_json_matches_schema(jsondata, 'dataset_metadata_schema.json')
                print('check passed for {}'.format(lbl))
            except (schema_tools.SchemaError, schema_tools.ValidationError) as e:
                print('check failed for {}: {}'.format(lbl, e))

    def tearDown(self):
        pass

    def test_something(self):
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
