'''
Created on Jan 15, 2020

@author: chb69
'''
import unittest
import configparser
import sys
import os
from neo4j import TransactionError, CypherError
import traceback

from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.entity import Entity
from hubmap_commons.test_helper import load_config
from hubmap_commons.hm_auth import AuthHelper, AuthCache
from hubmap_commons.hubmap_const import HubmapConst


class TestDataIntegrity(unittest.TestCase):


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

    
    """
    to both fixes.  Please continue to monitor PROD for the string timestamps.  
    I’m thinking we should put together a script of various things to check nightly.
      Simple at first- all timestamps present and int, all data_access_level 
      filled in db and ES, all samples and datasets have an organ set in ES, 
      all datasets with phi = yes have data_access_level as protected (db and ES)…
       probably more folks could think of.
       -check all entities (donor, sample, dataset) have a metadata node
    """    

    def test_timestamp_are_ints(self):
        stmt = 'MATCH (e) WHERE e.{prov_timestamp} = toString(e.{prov_timestamp}) RETURN count(e) AS record_count'.format(prov_timestamp=HubmapConst.PROVENANCE_CREATE_TIMESTAMP_ATTRIBUTE)
        with self.driver.session() as session:

            try:
                for record in session.run(stmt):
                    record_count = int(record['record_count'])
                    self.assertEqual(record_count, 0, 'error: found ' + str(record_count) + ' records with string values for ' + HubmapConst.PROVENANCE_CREATE_TIMESTAMP_ATTRIBUTE)

            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except:
                print ('A general error occurred: ')
                traceback.print_exc()
                raise
        
        
        
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