import unittest
import configparser
import sys
import os

from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.test_helper import load_config


class TestNeo4jConnection(unittest.TestCase):

    def setUp(self):
        self.config = load_config_file()
        self.conn = Neo4jConnection(self.config['NEO4J_SERVER'], self.config['NEO4J_USERNAME'], self.config['NEO4J_PASSWORD'])
        self.driver = self.conn.get_driver()

    def tearDown(self):
        if self.driver != None:
            if self.driver.closed() == False:
                self.driver.close()

    
    def test_basic_connection(self):
        with self.driver.session() as session:
            tx = None
            try:
                tx = session.begin_transaction()
                result = tx.run("CALL db.schema()")
                
                for record in result:
                    self.assertEqual(len(record), 2)
                tx.close()
            except Exception as e:
                raise e

    def test_stored_procedures(self):
        with self.driver.session() as session:
            tx = None
            try:
                tx = session.begin_transaction()
                result = tx.run("CALL dbms.procedures() YIELD name, signature WITH * WHERE name STARTS WITH 'apoc.path.subgraphAll'  RETURN name, signature")
                
                for record in result:
                    self.assertEqual(len(record), 2)
                tx.close()
            except Exception as e:
                raise e


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

if __name__ == '__main__':
    unittest.main()
