import unittest
import configparser
import sys
import os
from flask import session


import requests
import json
from requests.exceptions import TooManyRedirects
from pprint import pprint
from hubmap_commons.type_client import TypeClient
from hubmap_commons.type_client import _AssayType as TCAssayType


class TestTypeClientUninitialized(unittest.TestCase):

    def setUp(self):
        self.config = load_config_file()
 
    def tearDown(self):
        try:
            tc = TypeClient()
            if hasattr(self,'app_config'):
                del tc.app_config  # undo initialization
        except RuntimeError:
            pass

    def test000_singleton_nature(self):  # must happen first
        with self.assertRaises(RuntimeError):
            tc = TypeClient()
            print(dir(tc))
        tc = TypeClient(self.config['typeserviceurl'])
        tc2 = TypeClient()
        self.assertIs(tc, tc2)

    def test_assay_name_lists(self):
        try:
            tc = TypeClient()
        except RuntimeError:        
            tc = TypeClient(self.config['typeserviceurl'])
        all_nm_l = [elt for elt in tc.iterAssayNames()]
        self.assertTrue(len(all_nm_l) > 1
                        and all([isinstance(elt, str) for elt in all_nm_l])
                        )
        primary_nm_l = [elt for elt in tc.iterAssayNames(primary=True)]
        self.assertTrue(len(primary_nm_l) > 1
                        and all([isinstance(elt, str) for elt in primary_nm_l])
                        )
        nonprimary_nm_l = [elt for elt in tc.iterAssayNames(primary=False)]
        self.assertTrue(len(nonprimary_nm_l) > 1
                        and all([isinstance(elt, str) for elt in nonprimary_nm_l])
                        )
        for elt in primary_nm_l:
            self.assertTrue(elt in all_nm_l)
            self.assertFalse(elt in nonprimary_nm_l)
        for elt in nonprimary_nm_l:
            self.assertTrue(elt in all_nm_l)
            self.assertFalse(elt in primary_nm_l)
        self.assertTrue(len(primary_nm_l) + len(nonprimary_nm_l) == len(all_nm_l))

    def test_assay_lists(self):
        try:
            tc = TypeClient()
        except RuntimeError:        
            tc = TypeClient(self.config['typeserviceurl'])
        all_l = [elt for elt in tc.iterAssays()]
        self.assertTrue(len(all_l) > 1
                        and all([isinstance(elt, TCAssayType) for elt in all_l])
                        )
        primary_l = [elt for elt in tc.iterAssays(primary=True)]
        self.assertTrue(len(primary_l) > 1
                        and all([isinstance(elt, TCAssayType) for elt in primary_l])
                        )
        nonprimary_l = [elt for elt in tc.iterAssays(primary=False)]
        self.assertTrue(len(nonprimary_l) > 1
                        and all([isinstance(elt, TCAssayType) for elt in nonprimary_l])
                        )
        for elt in primary_l:
            self.assertTrue(elt in all_l)
            self.assertFalse(elt in nonprimary_l)
        for elt in nonprimary_l:
            self.assertTrue(elt in all_l)
            self.assertFalse(elt in primary_l)
        self.assertTrue(len(primary_l) + len(nonprimary_l) == len(all_l))

    def test_single_assays(self):
        try:
            tc = TypeClient()
        except RuntimeError:        
            tc = TypeClient(self.config['typeserviceurl'])
        cases = [('codex', False, None, 'should be uppercase'),
                 ('CODEX', True, True, 'this one is valid'),
                 ('codex_cytokit', True, False, 'this one is valid'),
                 ('salmon_rnaseq_bulk', True, False, 'this is an alt-name'),
                 #(['PAS', 'Image Pyramid'], True, False, 'complex alt-name'),
                 #(['IMC', 'foo'], False, False, 'invalid complex name')
                 ]
        for name, valid, is_primary, note in cases:
            if valid:
                assay = tc.getAssayType(name)
            else:
                print('This is an expected failure...')
                with self.assertRaises(Exception):
                    assay = tc.getAssayType(name)
                print('... that was expected')
    
    def test_comparators(self):
        try:
            tc = TypeClient()
        except RuntimeError:        
            tc = TypeClient(self.config['typeserviceurl'])
        all_l = [elt for elt in tc.iterAssays()]
        self.assertTrue(len(all_l) > 1)
        samp1 = all_l[0]
        samp2 = all_l[-1]
        samp3 = tc.getAssayType(samp1.name)
        self.assertTrue(samp1 == samp3)
        self.assertFalse(samp1 == samp2)        

    
    def test_to_json(self):
        try:
            tc = TypeClient()
        except RuntimeError:        
            tc = TypeClient(self.config['typeserviceurl'])
        all_nm_l = [elt for elt in tc.iterAssayNames(primary=True)]
        samp = tc.getAssayType(all_nm_l[0])
        dct = samp.to_json()
        self.assertTrue('name' in dct and dct['name'] == all_nm_l[0])
        self.assertTrue('description' in dct and isinstance(dct['description'], str))
        self.assertTrue('primary' in dct and dct['primary'] == True)


def load_config_file():
    entity_config = {}
    config = configparser.ConfigParser()
    config_fname = 'app.properties'
    try:
        config.read(os.path.join(os.path.dirname(__file__), '..', config_fname))
        entity_config['typeserviceurl'] = config.get('HUBMAP', 'TYPE_WEBSERVICE_URL')
        return entity_config
        #app.config['DEBUG'] = True
    except OSError as err:
        msg = f"OS error.  Check {config_fname} file to make sure it exists and is readable: {0}".format(
            err)
        print(msg + "  Program stopped.")
        exit(0)
    except configparser.NoSectionError as noSectError:
        msg = f"Error reading the {config_fname} file.  Check {config_fname} file to make sure it matches the structure in {config_fname}.example: {0}".format(
            noSectError)
        print(msg + "  Program stopped.")
        exit(0)
    except configparser.NoOptionError as noOptError:
        msg = f"Error reading the {config_fname} file.  Check {config_fname} file to make sure it matches the structure in {config_fname}.example: {0}".format(
            noOptError)
        print(msg + "  Program stopped.")
        exit(0)
    except SyntaxError as syntaxError:
        msg = f"Error reading the {config_fname} file.  Check {config_fname} file to make sure it matches the structure in {config_fname}.example: {0}".format(
            syntaxError)
        msg = msg + "  Cannot read line: {0}".format(syntaxError.text)
        print(msg + "  Program stopped.")
        exit(0)
    except AttributeError as attrError:
        msg = f"Error reading the {config_fname} file.  Check {config_fname} file to make sure it matches the structure in {config_fname}.example: {0}".format(
            attrError)
        msg = msg + "  Cannot read line: {0}".format(attrError.text)
        print(msg + "  Program stopped.")
        exit(0)
    except:
        msg = "Unexpected error:", sys.exc_info()[0]
        print(msg + "  Program stopped.")
        exit(0)


if __name__ == '__main__':
    unittest.main()
