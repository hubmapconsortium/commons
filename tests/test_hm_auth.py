'''
Created on Jan 15, 2020

@author: chb69
'''
import unittest
import configparser
import sys
import os

from hubmap_commons.test_helper import load_config
from hubmap_commons.hm_auth import AuthHelper, AuthCache


class TestHmAuth(unittest.TestCase):


    def setUp(self):
        self.config = load_config_file()
        if AuthHelper.isInitialized() == False:
            self.authcache = AuthHelper.create(
                self.config['APP_CLIENT_ID'], self.config['APP_CLIENT_SECRET'])
        else:
            self.authcache = AuthHelper.instance()


    def tearDown(self):
        pass

    def test_getHuBMAPGroupInfo(self):
        groups = self.authcache.getHuBMAPGroupInfo()
        self.assertGreaterEqual(len(groups), 1, 'error: could not find any groups using getHMGroups()')

    def test_getProcessSecret(self):
        secret_key = self.authcache.getProcessSecret()
        self.assertGreater(len(secret_key), 0, 'error: could not find process secret')

    def test_getApplicationKey(self):
        secret_key = self.authcache.getApplicationKey()
        self.assertGreater(len(secret_key), 0, 'error: could not find application secret')

    def test_getHMGroups(self):
        groups = AuthCache.getHMGroups()
        self.assertGreaterEqual(len(groups), 1, 'error: could not find any groups using getHMGroups()')
        
    def test_getHMRoles(self):
        roles = AuthCache.getHMRoles()
        self.assertGreaterEqual(len(roles), 1, 'error: could not find any groups using getHMRoles()')

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
    
    
    
