'''
Created on May 15, 2019

@author: chb69
'''
#from neo4j.exceptions import TransactionError, CypherError
import json
import sys
import os
from pprint import pprint
import configparser
import requests
import traceback
from hubmap_commons.hubmap_const import HubmapConst 
from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.uuid_generator import UUID_Generator
from hubmap_commons.hm_auth import AuthHelper, AuthCache
from hubmap_commons.entity import Entity

class Metadata(object):

    md_config = {}
    
    def __init__(self, app_client_id, app_client_secret, uuid_webservice_url):
        self.md_config['APP_CLIENT_ID'] = app_client_id
        self.md_config['APP_CLIENT_SECRET'] = app_client_secret
        self.md_config['UUID_WEBSERVICE_URL'] = uuid_webservice_url

    @staticmethod
    # NOTE: This will return a metadata object using its identifier
    def get_metadata(driver, identifier): 
        try:
            return Entity.get_entity(driver, identifier)
        except BaseException as be:
            pprint(be)
            raise be

    @staticmethod
    # NOTE: This will return the metadata for a specific instance of an entity, activity, or agent
    def get_metadata_by_source(driver, identifier): 
        try:
            return Entity.get_entities_by_relationship(driver, identifier, HubmapConst.HAS_METADATA_REL)
        except BaseException as be:
            pprint(be)
            raise be


    @staticmethod
    # NOTE: This will return a metadata object using the source's type
    def get_metadata_by_source_type(driver, general_type_attribute, type_code): 
        with driver.session() as session:
            return_list = []


            try:
                stmt = "MATCH (a {{{type_attrib}: '{type_code}'}})-[:{metadata_rel}]-(b) RETURN properties(b) as properties".format(
                    type_attrib=general_type_attribute, type_code=type_code, metadata_rel=HubmapConst.HAS_METADATA_REL)

                for record in session.run(stmt):
                    dataset_record = record['properties']
                    return_list.append(dataset_record)
                return return_list                    
            except Exception as e:
                print ('An exception occurred in get_metadata_by_source_type: ' + str(e))
                for x in sys.exc_info():
                    print (x)
                raise

    def get_group_by_identifier(self, identifier):
        if len(identifier) == 0:
            raise ValueError("identifier cannot be blank")
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.md_config['APP_CLIENT_ID'], self.md_config['APP_CLIENT_SECRET'])
        else:
            authcache = AuthHelper.instance()
        groupinfo = authcache.getHuBMAPGroupInfo()
        # search through the keys for the identifier, return the value
        for k in groupinfo.keys():
            if str(k).lower() == str(identifier).lower():
                group = groupinfo.get(k)
                return group
            else:
                group = groupinfo.get(k)
                if str(group['uuid']).lower() == str(identifier).lower():
                    return group
        raise ValueError("cannot find a Hubmap group matching: [" + identifier + "]")

    def get_create_metadata_statement(self, current_token, metadata_record):
        metadata_uuid_record_list = None
        metadata_uuid_record = None
        ug = UUID_Generator(self.md_config['UUID_WEBSERVICE_URL'])
        try:
            metadata_uuid_record_list = ug.getNewUUID(current_token, HubmapConst.METADATA_TYPE_CODE)
            if (metadata_uuid_record_list == None) or (len(metadata_uuid_record_list) != 1):
                raise ValueError("UUID service did not return a value")
            metadata_uuid_record = metadata_uuid_record_list[0]
        except requests.exceptions.ConnectionError as ce:
            raise ConnectionError("Unable to connect to the UUID service: " + str(ce.args[0]))
        
        metadata_record[HubmapConst.UUID_ATTRIBUTE] = metadata_uuid_record[HubmapConst.UUID_ATTRIBUTE]
        
        stmt = Neo4jConnection.get_create_statement(
            metadata_record, HubmapConst.METADATA_NODE_NAME, HubmapConst.METADATA_TYPE_CODE, True)
        # NOTE: I need to return a list of the newly created uud plus the stmt: {'uuid':'', 'doi':'', 'display_doi':'', 'stmt':stmt}
        # otherwise, the new uuid might get lost 
        return {'uuid_data': metadata_uuid_record_list, 'stmt':stmt}

    @staticmethod
    def load_config_file():
        config = configparser.ConfigParser()
        confdata = {}
        try:
            config.read(os.path.join(os.path.dirname(__file__), '..', 'app.properties'))
            confdata['neo4juri'] = config.get('NEO4J', 'server')
            confdata['neo4jusername'] = config.get('NEO4J', 'username')
            confdata['neo4jpassword'] = config.get('NEO4J', 'password')
            confdata['appclientid'] = config.get('GLOBUS', 'APP_CLIENT_ID')
            confdata['appclientsecret'] = config.get(
                'GLOBUS', 'APP_CLIENT_SECRET')
            confdata['localstoragedirectory'] = config.get(
                'FILE_SYSTEM', 'GLOBUS_STORAGE_DIRECTORY_ROOT')
            confdata['UUID_WEBSERVICE_URL'] = config.get('HUBMAP', 'UUID_WEBSERVICE_URL')
            return confdata
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
            traceback.print_exc()
            exit(0)

if __name__ == "__main__":
    confdata = Metadata.load_config_file()
    conn = Neo4jConnection(confdata['neo4juri'], confdata['neo4jusername'], confdata['neo4jpassword'])
    driver = conn.get_driver()
    uuid = "cafd03e784d2fd091dd2bafc71db911d"
    record = Metadata.get_metadata_by_source(driver, uuid)
    pprint(record)
    
    record_list = Metadata.get_metadata_by_source_type(driver, 'entitytype', 'Donor')
    pprint(record_list)

    record_list = Metadata.get_metadata_by_source_type(driver, 'entitytype', 'Tissue Sample')
    pprint(record_list)

    
    record_list = Metadata.get_metadata_by_source_type(driver, 'entitytype', 'bad entity')
    pprint(record_list)
    
    #pprint(AuthCache.getHMGroups())

    conn.close()
        
