'''
Created on Jan 15, 2020

@author: chb69
'''
import unittest
import configparser
import sys
import os

from hubmap_commons.provenance import Provenance
from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.entity import Entity
from hubmap_commons.test_helper import load_config
from hubmap_commons.hm_auth import AuthHelper, AuthCache


class TestProvenance(unittest.TestCase):


    def setUp(self):
        self.config = load_config_file()
        self.conn = Neo4jConnection(self.config['NEO4J_SERVER'], self.config['NEO4J_USERNAME'], self.config['NEO4J_PASSWORD'])
        self.driver = self.conn.get_driver()
        self.prov = Provenance(self.config['APP_CLIENT_ID'], self.config['APP_CLIENT_SECRET'], self.config['UUID_WEBSERVICE_URL'])


    def tearDown(self):
        if self.driver != None:
            if self.driver.closed() == False:
                self.driver.close()


    def test_get_provenance_history(self):
        # in general, the display id (ex: TEST0010-LK-1-1-1) will dictate the corresponding
        # number of entity entries returned.  Basically, the entity entry count should equal the number of hyphens 
        # in the display id plus one.  For example, TEST0010 will have 1 entity entry.  TEST0010-LK will have two: one for the donor TEST0010
        # and one for the organ TEST0010-LK.
        driver = self.driver
        donor_list = Entity.get_entities_by_type(driver, 'Donor')
        
        # walk through the first 5 donors and test them
        for x in range(6):
            history_data_str = self.prov.get_provenance_history(driver, donor_list[x])
            history_data = eval(history_data_str)
            self.assertEqual(len(history_data['entity']), 1)

        sample_list = Entity.get_entities_by_type(driver, 'Sample')
        # walk through the first 20 samples and test them
        for x in range(20):
            sample_item = Entity.get_entity(driver, sample_list[x])
            history_data_str = self.prov.get_provenance_history(driver, sample_list[x])
            history_data = eval(history_data_str)
            display_id = sample_item['hubmap_identifier']
            hypen_count = str(display_id).count('-')
            self.assertEqual(len(history_data['entity']), hypen_count+1)

    def test_load_group_data(self):
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.config['APP_CLIENT_ID'], self.config['APP_CLIENT_SECRET'])
        else:
            authcache = AuthHelper.instance()
        group_data = self.prov.groupsById
        self.assertGreaterEqual(len(group_data), 1, 'test_load_group_data failed.  Could not find any group data')

    def test_load_group_info(self):
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.config['APP_CLIENT_ID'], self.config['APP_CLIENT_SECRET'])
        else:
            authcache = AuthHelper.instance()
        group_data = self.prov.groups
        self.assertGreaterEqual(len(group_data), 1, 'test_load_group_info failed.  Could not find any group data')

    def test_groups_by_tmc_prefix(self):
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.config['APP_CLIENT_ID'], self.config['APP_CLIENT_SECRET'])
        else:
            authcache = AuthHelper.instance()
        group_data = self.prov.groups_by_tmc_prefix
        self.assertGreaterEqual(len(group_data), 1, 'test_groups_by_tmc_prefix failed.  Could not find any group data')


    def test_get_group_by_identifier(self):
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.config['APP_CLIENT_ID'], self.config['APP_CLIENT_SECRET'])
        else:
            authcache = AuthHelper.instance()
        group_data = self.prov.groupsById
        for group_id in group_data.keys():
            group_info = self.prov.get_group_by_identifier(group_id)
            self.assertNotEqual(group_info, None, 'test_load_group_data failed.  Could not find any group data for identifier: ' + group_id)


def load_config_file():
    entity_config = {}
    file_path = os.path.join(os.path.dirname(__file__), '../../ingest-ui/src/ingest-api/instance')
    filename = 'app.cfg'
    try:
        config = load_config(file_path, filename)
        return config
        #app.config['DEBUG'] = True
    except OSError as err:
        msg = "OS error.  Check config.ini file to make sure it exists and is readable: {0}".format(
            err)
        print(msg + "  Program stopped.")
        exit(0)
    except configparser.NoSectionError as noSectError:
        msg = "Error reading the config.ini file.  Check config.ini file to make sure it matches the structure in config.ini.example: {0}".format(
            noSectError)
        print(msg + "  Program stopped.")
        exit(0)
    except configparser.NoOptionError as noOptError:
        msg = "Error reading the config.ini file.  Check config.ini file to make sure it matches the structure in config.ini.example: {0}".format(
            noOptError)
        print(msg + "  Program stopped.")
        exit(0)
    except SyntaxError as syntaxError:
        msg = "Error reading the config.ini file.  Check config.ini file to make sure it matches the structure in config.ini.example: {0}".format(
            syntaxError)
        msg = msg + "  Cannot read line: {0}".format(syntaxError.text)
        print(msg + "  Program stopped.")
        exit(0)
    except AttributeError as attrError:
        msg = "Error reading the config.ini file.  Check config.ini file to make sure it matches the structure in config.ini.example: {0}".format(
            attrError)
        msg = msg + "  Cannot read line: {0}".format(attrError.text)
        print(msg + "  Program stopped.")
        exit(0)
    except:
        msg = "Unexpected error:", sys.exc_info()[0]
        print(msg + "  Program stopped.")
        exit(0)
            


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()