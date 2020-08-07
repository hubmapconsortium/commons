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
from hubmap_commons.metadata import Metadata
from hubmap_commons.test_helper import load_config
from hubmap_commons.hm_auth import AuthHelper, AuthCache


class TestMetadata(unittest.TestCase):


    def setUp(self):
        self.config = load_config_file()
        self.conn = Neo4jConnection(self.config['NEO4J_SERVER'], self.config['NEO4J_USERNAME'], self.config['NEO4J_PASSWORD'])
        self.driver = self.conn.get_driver()
        self.entity = Entity(self.config['APP_CLIENT_ID'], self.config['APP_CLIENT_SECRET'], self.config['UUID_WEBSERVICE_URL'])
        self.donor_list = Entity.get_entities_by_type(self.driver, 'Donor')


    def test_get_metadata(self):
        # walk through the first 5 donors and test them
        for x in range(6):
            metadata_by_source_obj = Metadata.get_metadata_by_source(self.driver, self.donor_list[x])
            metadata_obj = Metadata.get_metadata(self.driver, metadata_by_source_obj[0]['uuid'])
            self.assertIsNotNone(metadata_obj, 'Error: cannot find metadata for uuid: ' + self.donor_list[x])


    def test_get_metadata_by_source(self): 
        # walk through the first 5 donors and test them
        for x in range(6):
            metadata_by_source_obj = Metadata.get_metadata_by_source(self.driver, self.donor_list[x])
            self.assertIsNotNone(metadata_by_source_obj, 'Error: cannot find metadata for uuid: ' + self.donor_list[x])


    def tearDown(self):
        if self.conn != None:
            self.conn.close()
        if self.driver != None:
            if self.driver.closed() == False:
                self.driver.close()

        

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
    
    
    
