'''
Created on Jan 15, 2020

@author: chb69
'''
import unittest
import configparser
import sys
import os

from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.entity import Entity
from hubmap_commons.test_helper import load_config
from hubmap_commons.hm_auth import AuthHelper, AuthCache


class TestEntity(unittest.TestCase):


    def setUp(self):
        self.config = load_config_file()
        self.conn = Neo4jConnection(self.config['NEO4J_SERVER'], self.config['NEO4J_USERNAME'], self.config['NEO4J_PASSWORD'])
        self.driver = self.conn.get_driver()
        self.entity = Entity(self.config['APP_CLIENT_ID'], self.config['APP_CLIENT_SECRET'], self.config['UUID_WEBSERVICE_URL'])
        self.group_list = AuthCache.getHMGroups()


    def tearDown(self):
        if self.conn != None:
            self.conn.close()
        if self.driver != None:
            if self.driver.closed() == False:
                self.driver.close()

    def test_get_entities_by_type(self): 
        entity_test_list = Entity.get_entity_type_list(self.driver)
        for entity_type in entity_test_list:
            entity_list = Entity.get_entities_by_type(self.driver, entity_type)
            self.assertGreaterEqual(len(entity_list), 1)

    def test_get_entity(self): 
        donor_list = Entity.get_entities_by_type(self.driver, 'Donor')
        
        # walk through the first 5 donors and test them
        for x in range(6):
            donor_record = self.entity.get_entity(self.driver, donor_list[x])
            self.assertGreaterEqual(len(donor_record.keys()), 1)
        
    def test_get_entity_type_list(self): 
        entity_test_list = Entity.get_entity_type_list(self.driver)
        self.assertGreaterEqual(len(entity_test_list), 1)

    def test_does_identifier_exist(self): 
        donor_list = Entity.get_entities_by_type(self.driver, 'Donor')
        
        # walk through the first 5 donors and test them
        for x in range(6):
            does_exist = Entity.does_identifier_exist(self.driver, donor_list[x])
            self.assertEqual(does_exist, True)
            
    def test_get_group_by_identifier(self):
        for group_name in self.group_list:
            group_info = self.group_list[group_name]
            current_group = self.entity.get_group_by_identifier(group_info['uuid'])
            self.assertIsNotNone(current_group, 'error: could not find group information for: '  + str(group_info))

    def test_get_group_by_name(self):
        for group_name in self.group_list:
            current_group = self.entity.get_group_by_identifier(group_name)
            self.assertIsNotNone(current_group, 'error: could not find group information for: '  + str(group_name))

    def test_get_entities_by_types(self): 
        entity_type_list = Entity.get_entity_type_list(self.driver)
        all_entities = Entity.get_entities_by_types(self.driver, entity_type_list)
        self.assertGreater(len(all_entities), 1, 'error: could not find entities in this list: ' + str(entity_type_list))

    def test_get_entity_count_by_type(self): 
        entity_test_list = Entity.get_entity_type_list(self.driver)
        for entity_type in entity_test_list:
            entity_count = Entity.get_entity_count_by_type(self.driver, entity_type)
            self.assertGreaterEqual(len(entity_count), 1)

    def test_get_entity_metadata(self):
        donor_list = Entity.get_entities_by_type(self.driver, 'Donor')
        
        # walk through the first 5 donors and test them
        for x in range(6):
            donor_record = self.entity.get_entity_metadata(self.driver, donor_list[x])
            self.assertGreaterEqual(len(donor_record.keys()), 1)
        

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
    
    
    
