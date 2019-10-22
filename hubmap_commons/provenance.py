'''
Created on Sep 1, 2019

@author: chb69
'''
from neo4j import TransactionError, CypherError
import os
import sys
import configparser
import requests
import traceback
from pprint import pprint
import json
import prov
from prov.model import ProvDocument
import datetime
from pytz import timezone
import pytz


from hubmap_commons.hubmap_const import HubmapConst 
from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.uuid_generator import UUID_Generator
from hubmap_commons.entity import Entity
from hubmap_commons.hm_auth import AuthHelper, AuthCache

class ProvConst(object):
    PROV_ENTITY_TYPE = 'prov:Entity'
    PROV_ACTIVITY_TYPE = 'prov:Activity'
    PROV_AGENT_TYPE = 'prov:Agent'
    PROV_COLLECTION_TYPE = 'prov:Collection'
    PROV_ORGANIZATION_TYPE = 'prov:Organization'
    PROV_PERSON_TYPE = 'prov:Person'
    PROV_LABEL_ATTRIBUTE = 'prov:label'
    PROV_TYPE_ATTRIBUTE = 'prov:type'
    PROV_GENERATED_TIME_ATTRIBUTE = 'prov:generatedAtTime'
    #prov:generatedAtTime "2012-04-03T13:35:23"^^xsd:dateTime;

class Provenance:
    
    provenance_config = {}
    
    def __init__(self, app_client_id, app_client_secret, uuid_webservice_url):
        self.provenance_config['APP_CLIENT_ID'] = app_client_id
        self.provenance_config['APP_CLIENT_SECRET'] = app_client_secret
        self.provenance_config['UUID_WEBSERVICE_URL'] = uuid_webservice_url
        
        
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

    def get_provenance_data_object(self, token, groupUUID=None):
        provenance_group = None
        try:
            if groupUUID != None:
                provenance_group = self.get_group_by_identifier(groupUUID)
            else:
                #manually find the group id given the current user:
                group_uuid = None
                entity = Entity(self.provenance_config['APP_CLIENT_ID'], self.provenance_config['APP_CLIENT_SECRET'], self.provenance_config['UUID_WEBSERVICE_URL'])
                group_list = entity.get_user_groups(token)
                for grp in group_list:
                    if grp['generateuuid'] == True:
                        groupUUID = grp['uuid']
                        # if provenance_group is already set, this means the user belongs to more than one writable group
                        if provenance_group != None:
                            ValueError('Error: Current user is a member of multiple groups allowed to create new entities.  The user must select which one to use')
                        provenance_group = self.get_group_by_identifier(groupUUID)
                        
                        
                        #TODO: THIS IS HARDCODED!!  WE NEED TO CHANGE THIS TO TRACK TEST GROUPS DIFFERENTLY
                        
                        # for now if the group is the IEC Testing group, keep looking for a different group
                        # only use the IEC Testing group if no other writable group is found for the user
                        # NOTE: this code will simply return the first writable group it encounters
                        if groupUUID != '5bd084c8-edc2-11e8-802f-0e368f3075e8':
                            break    
                if groupUUID == None:
                    raise ValueError('Unauthorized: Current user is not a member of a group allowed to create new entities')
        except ValueError as ve:
            raise ve
        ret_provenance_group = {HubmapConst.PROVENANCE_GROUP_UUID_ATTRIBUTE : groupUUID, 
                                   HubmapConst.PROVENANCE_GROUP_NAME_ATTRIBUTE: provenance_group['displayname']}
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.provenance_config['appclientid'], self.provenance_config['appclientsecret'])
        else:
            authcache = AuthHelper.instance()
        userinfo = authcache.getUserInfo(token, True)
        ret_provenance_group[HubmapConst.PROVENANCE_SUB_ATTRIBUTE] = userinfo['sub']
        ret_provenance_group[HubmapConst.PROVENANCE_USER_EMAIL_ATTRIBUTE] = userinfo['email']
        ret_provenance_group[HubmapConst.PROVENANCE_USER_DISPLAYNAME_ATTRIBUTE] = userinfo['name']
        return ret_provenance_group
    
    
    def get_group_by_identifier(self, identifier):
        if len(identifier) == 0:
            raise ValueError("identifier cannot be blank")
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.provenance_config['APP_CLIENT_ID'], self.provenance_config['APP_CLIENT_SECRET'])
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
    
    def get_provenance_history(self, driver, uuid, depth):
        return_data = {}
        prov_doc = ProvDocument()
        prov_doc.add_namespace('ex', 'http://example.org')
        prov_doc.add_namespace('hubmap', 'https://hubmapconsortium.org')
        updated_node_list = []
        relation_list = []
        with driver.session() as session:
            try:
                
                stmt = """MATCH (n:Entity {{ uuid: '{uuid}' }}) 
                CALL apoc.path.subgraphAll(n, {{ maxLevel: {depth}, relationshipFilter:'<ACTIVITY_INPUT|<ACTIVITY_OUTPUT|HAS_METADATA' }}) YIELD nodes, relationships
                WITH [node in nodes | node {{ .*, label:labels(node)[0] }} ] as nodes, 
                     [rel in relationships | rel {{ .*, fromNode: {{ label:labels(startNode(rel))[0], uuid:startNode(rel).uuid }} , toNode: {{ label:labels(endNode(rel))[0], uuid:endNode(rel).uuid }}, rel_data: {{ type: type(rel) }} }} ] as rels
                WITH {{ nodes:nodes, relationships:rels }} as json
                RETURN json""".format(uuid=uuid, depth=depth)
                
                result = session.run(stmt)
                
                #there should only be one record
                for jsonData in result:
                    try:
                        record = dict(jsonData)['json']

                        if 'relationships' not in record:
                            raise LookupError('Error, unable to find relationships for uuid:' + uuid)
                        if 'nodes' not in record:
                            raise LookupError('Error, unable to find nodes for uuid:' + uuid)
                        
                        node_dict = {}
                        # pack the nodes into a dictionary using the uuid as a key
                        for node_record in record['nodes']:
                            node_dict[node_record['uuid']] = node_record
 
                            """
                              "398400024fda58e293cdb435db3c777e": {
                                  "display_doi": "HBM756.PMTZ.842",
                                  "doi": "756PMTZ842",
                                  "entitytype": "Sample",
                                  "hubmap_identifier": "TEST0016-LV",
                                  "label": "Entity",
                                  "metadata": {
                                    "entitytype": "Metadata",
                                    "label": "Metadata",
                                    "organ": "LV",
                                    "protocols": [
                                      {
                                        "id": "protocol_1",
                                        "protocol_url": "http://protocols.io/vaijroirwjv",
                                        "protocol_file": ""
                                      }
                                    ],
                                    "provenance_create_timestamp": 1570131434442,
                                    "provenance_group_name": "hubmap-testing",
                                    "provenance_group_uuid": "5bd084c8-edc2-11e8-802f-0e368f3075e8",
                                    "provenance_modified_timestamp": 1570131434442,
                                    "provenance_user_displayname": "Chuck Borromeo",
                                    "provenance_user_email": "chuck.hubmaptest@gmail.com",
                                    "provenance_user_sub": "a79606b3-e9be-4f1b-a01f-4aa1e8b900d8",
                                    "reference_uuid": [
                                      "398400024fda58e293cdb435db3c777e"
                                    ],
                                    "source_uuid": "HBM334.ZZXR.329",
                                    "specimen_type": "organ",
                                    "uuid": "673520f8fb45f2533c99819106e9d24d"
                                  },
                                  "next_identifier": "1",
                                  "provenance_create_timestamp": 1570131434425,
                                  "provenance_modified_timestamp": 1570131434425,
                                  "uuid": "398400024fda58e293cdb435db3c777e"
                                },
                            """
 
 
 
                        
                        # now, connect the nodes
                        for rel_record in record['relationships']:
                            from_uuid = rel_record['fromNode']['uuid']
                            to_uuid = rel_record['toNode']['uuid']
                            from_node = node_dict[from_uuid]
                            to_node = node_dict[to_uuid]
                            if rel_record['rel_data']['type'] == HubmapConst.HAS_METADATA_REL:
                                # assign the metadata node as the metadata attribute
                                # just extract the provenance information from the metadata node
                                from_node['provenance_data'] = {HubmapConst.PROVENANCE_CREATE_TIMESTAMP_ATTRIBUTE : to_node[HubmapConst.PROVENANCE_CREATE_TIMESTAMP_ATTRIBUTE],
                                                         HubmapConst.PROVENANCE_GROUP_NAME_ATTRIBUTE : to_node[HubmapConst.PROVENANCE_GROUP_NAME_ATTRIBUTE],
                                                         HubmapConst.PROVENANCE_GROUP_UUID_ATTRIBUTE : to_node[HubmapConst.PROVENANCE_GROUP_UUID_ATTRIBUTE],
                                                         HubmapConst.PROVENANCE_MODIFIED_TIMESTAMP_ATTRIBUTE : to_node[HubmapConst.PROVENANCE_MODIFIED_TIMESTAMP_ATTRIBUTE],
                                                         HubmapConst.PROVENANCE_SUB_ATTRIBUTE : to_node[HubmapConst.PROVENANCE_SUB_ATTRIBUTE],
                                                         HubmapConst.PROVENANCE_USER_DISPLAYNAME_ATTRIBUTE : to_node[HubmapConst.PROVENANCE_USER_DISPLAYNAME_ATTRIBUTE]}
                                #d1.entity('govftp:oesm11st.zip', {'prov:label': 'employment-stats-2011', 'prov:type': 'void:Dataset'})
                                prov_doc.entity('ex:' + str(from_node['uuid']), other_attributes)
                            elif rel_record['rel_data']['type'] in [HubmapConst.ACTIVITY_OUTPUT_REL, HubmapConst.ACTIVITY_INPUT_REL]:
                                # for now, simply create a "relation" where the fromNode's uuid is connected to a toNode's uuid via a relationship:
                                # ex: {'fromNodeUUID': '42e10053358328c9079f1c8181287b6d', 'relationship': 'ACTIVITY_OUTPUT', 'toNodeUUID': '398400024fda58e293cdb435db3c777e'}
                                rel_data_record = {'fromNodeUUID' : from_node['uuid'], 'relationship' : rel_record['rel_data']['type'], 'toNodeUUID' : to_node['uuid']}
                                relation_list.append(rel_data_record)
                        return_data = {'nodes' : node_dict, 'relations' : relation_list}  
                    except Exception as e:
                        print("ERROR!: " + str(e))
      
                #pprint(return_data)        
                return return_data
            except ConnectionError as ce:
                print('A connection error occurred: ', str(ce.args[0]))
                raise ce
            except ValueError as ve:
                print('A value error occurred: ', ve.value)
                raise ve
            except CypherError as cse:
                print('A Cypher error was encountered: ', cse.message)
                raise cse
            except:
                print('A general error occurred: ')
                traceback.print_exc()
    

if __name__ == "__main__":    
    """confdata = Provenance.load_config_file()
    conn = Neo4jConnection(confdata['neo4juri'], confdata['neo4jusername'], confdata['neo4jpassword'])
    driver = conn.get_driver()
    prov = Provenance(confdata['appclientid'], confdata['appclientsecret'], confdata['UUID_WEBSERVICE_URL'])
    uuid = '398400024fda58e293cdb435db3c777e'
    uuid = 'd6be7b5ec50dacd4e8faf45c78e4b7c9'
    history_data = prov.get_provenance_history(driver, uuid, 4)
    pprint(history_data)"""
    
    your_timestamp = 1571248740444
    eastern = timezone('US/Eastern')
    date = datetime.datetime.fromtimestamp(your_timestamp / 1e3)
    localized_timestamp = eastern.localize(date)
    #utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
    #date.replace(tzinfo=timezone.utc).astimezone(tz=None)
    #pprint(localized_timestamp)
    
    