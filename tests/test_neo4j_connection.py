import unittest
import configparser
import sys
import os

from hubmap_commons.neo4j_connection import Neo4jConnection


class TestNeo4jConnection(unittest.TestCase):

    def setUp(self):
        self.config = load_config_file()
        self.conn = Neo4jConnection(self.config['neo4juri'], self.config['neo4jusername'], self.config['neo4jpassword'])
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


def load_config_file():
    entity_config = {}
    config = configparser.ConfigParser()
    try:
        config.read(os.path.join(os.path.dirname(__file__), '..', 'app.properties'))
        entity_config['neo4juri'] = config.get('NEO4J', 'server')
        entity_config['neo4jusername'] = config.get('NEO4J', 'username')
        entity_config['neo4jpassword'] = config.get('NEO4J', 'password')
        entity_config['APP_CLIENT_ID'] = config.get('GLOBUS', 'APP_CLIENT_ID')
        entity_config['APP_CLIENT_SECRET'] = config.get(
            'GLOBUS', 'APP_CLIENT_SECRET')
        entity_config['STAGING_ENDPOINT_UUID'] = config.get(
            'GLOBUS', 'STAGING_ENDPOINT_UUID')
        entity_config['PUBLISH_ENDPOINT_UUID'] = config.get(
            'GLOBUS', 'PUBLISH_ENDPOINT_UUID')
        entity_config['SECRET_KEY'] = config.get('GLOBUS', 'SECRET_KEY')
        entity_config['UUID_UI_URL'] = config.get('HUBMAP', 'UUID_UI_URL')
        return entity_config
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
