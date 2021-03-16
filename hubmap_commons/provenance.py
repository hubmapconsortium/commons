'''
Created on Sep 1, 2019

@author: chb69
'''
#from neo4j import TransactionError, CypherError
from hubmap_commons import string_helper, file_helper
import os
import sys
import configparser
import requests
import traceback
from pprint import pprint
import json
import prov
from prov.model import ProvDocument, PROV_TYPE, Namespace, NamespaceManager
from prov.serializers.provjson import ProvJSONSerializer
import datetime
from pytz import timezone
import pytz


from hubmap_commons.hubmap_const import HubmapConst 
from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.uuid_generator import UUID_Generator
from hubmap_commons.entity import Entity
from hubmap_commons.hm_auth import AuthHelper, AuthCache
from builtins import staticmethod



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

    HUBMAP_DOI_ATTRIBUTE = 'hubmap:doi' #the doi concept here might be a good alternative: https://sparontologies.github.io/datacite/current/datacite.html
    HUBMAP_DISPLAY_DOI_ATTRIBUTE = 'hubmap:displayDOI' 
    HUBMAP_SPECIMEN_TYPE_ATTRIBUTE = 'hubmap:specimenType' 
    HUBMAP_DISPLAY_IDENTIFIER_ATTRIBUTE = 'hubmap:displayIdentifier' 
    HUBMAP_UUID_ATTRIBUTE = 'hubmap:uuid' 
    #HUBMAP_SOURCE_UUID_ATTRIBUTE = 'hubmap:sourceUUID'
    HUBMAP_METADATA_ATTRIBUTE = 'hubmap:metadata'
    HUBMAP_MODIFIED_TIMESTAMP = 'hubmap:modifiedTimestamp'
    HUBMAP_PROV_GROUP_NAME = 'hubmap:groupName'
    HUBMAP_PROV_GROUP_UUID = 'hubmap:groupUUID'
    HUBMAP_PROV_USER_DISPLAY_NAME = 'hubmap:userDisplayName'
    HUBMAP_PROV_USER_EMAIL = 'hubmap:userEmail'
    HUBMAP_PROV_USER_UUID = 'hubmap:userUUID'
    groupJsonFilename = file_helper.ensureTrailingSlash(os.path.dirname(os.path.realpath(__file__))) + 'hubmap-globus-groups.json'
     

class Provenance:
    
    provenance_config = {}
    
    metadata_ignore_attributes = [HubmapConst.ENTITY_TYPE_ATTRIBUTE, HubmapConst.PROVENANCE_CREATE_TIMESTAMP_ATTRIBUTE, HubmapConst.REFERENCE_UUID_ATTRIBUTE, 
                                  HubmapConst.UUID_ATTRIBUTE, HubmapConst.SOURCE_UUID_ATTRIBUTE, HubmapConst.SOURCE_DISPLAY_ID_ATTRIBUTE, HubmapConst.NAME_ATTRIBUTE]
    
    known_attribute_map = {HubmapConst.PROVENANCE_GROUP_NAME_ATTRIBUTE : ProvConst.HUBMAP_PROV_GROUP_NAME, HubmapConst.PROVENANCE_GROUP_UUID_ATTRIBUTE : ProvConst.HUBMAP_PROV_GROUP_UUID,
                           HubmapConst.PROVENANCE_USER_DISPLAYNAME_ATTRIBUTE: ProvConst.HUBMAP_PROV_USER_DISPLAY_NAME, HubmapConst.PROVENANCE_USER_EMAIL_ATTRIBUTE: ProvConst.HUBMAP_PROV_USER_EMAIL,
                           HubmapConst.PROVENANCE_SUB_ATTRIBUTE : ProvConst.HUBMAP_PROV_USER_UUID, HubmapConst.PROVENANCE_MODIFIED_TIMESTAMP_ATTRIBUTE : ProvConst.HUBMAP_MODIFIED_TIMESTAMP}

    agent_attribute_map = {HubmapConst.PROVENANCE_USER_DISPLAYNAME_ATTRIBUTE: ProvConst.HUBMAP_PROV_USER_DISPLAY_NAME, HubmapConst.PROVENANCE_USER_EMAIL_ATTRIBUTE: ProvConst.HUBMAP_PROV_USER_EMAIL,
                           HubmapConst.PROVENANCE_SUB_ATTRIBUTE : ProvConst.HUBMAP_PROV_USER_UUID}
    
    organization_attribute_map = {'displayname' : ProvConst.HUBMAP_PROV_GROUP_NAME, 'uuid' : ProvConst.HUBMAP_PROV_GROUP_UUID}
    
    groupsById = {}
    groupsByName = {}
    
    def __init__(self, app_client_id, app_client_secret, uuid_webservice_url):
        self.provenance_config['APP_CLIENT_ID'] = app_client_id
        self.provenance_config['APP_CLIENT_SECRET'] = app_client_secret
        self.provenance_config['UUID_WEBSERVICE_URL'] = uuid_webservice_url
        self.load_group_data()

    def load_group_data(self):
        with open(AuthCache.groupJsonFilename) as jsFile:
            self.groups = json.load(jsFile)
            self.groups_by_tmc_prefix = {}
            for group in self.groups:
                if 'name' in group and 'uuid' in group and 'generateuuid' in group and 'displayname' in group and not string_helper.isBlank(group['name']) and not string_helper.isBlank(group['uuid']) and not string_helper.isBlank(group['displayname']):
                    group_obj = {'name' : group['name'].lower().strip(), 'uuid' : group['uuid'].lower().strip(),
                                 'displayname' : group['displayname'], 'generateuuid': group['generateuuid']}
                    if 'tmc_prefix' in group:
                        group_obj['tmc_prefix'] = group['tmc_prefix']
                        if 'uuid' in group and 'displayname' in group and not string_helper.isBlank(group['uuid']) and not string_helper.isBlank(group['displayname']):
                            group_info = {}
                            group_info['uuid'] = group['uuid']
                            group_info['displayname'] = group['displayname']
                            group_info['tmc_prefix'] = group['tmc_prefix']
                            self.groups_by_tmc_prefix[group['tmc_prefix'].upper().strip()] = group_info
                    self.groupsByName[group['name'].lower().strip()] = group_obj
                    self.groupsById[group['uuid']] = group_obj

        
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
    
    def get_provenance_history(self, driver, uuid, depth=None):
        prov_doc = ProvDocument()
        #prov_doc.
        #NOTE!! There is a bug with the JSON serializer.  I can't add the prov prefix using this mechanism
        
        prov_doc.add_namespace('ex', 'http://example.org/')
        prov_doc.add_namespace('hubmap', 'https://hubmapconsortium.org/')
        
        #prov_doc.add_namespace('dct', 'http://purl.org/dc/terms/')
        #prov_doc.add_namespace('foaf','http://xmlns.com/foaf/0.1/')
        relation_list = []
        with driver.session() as session:
            try:
                # max_level_str is the string used to put a limit on the number of levels to traverse
                max_level_str = ''
                if depth is not None and len(str(depth)) > 0:
                    max_level_str = """maxLevel: {depth},""".format(depth=depth)

                """
                Basically this Cypher query returns a collection of nodes and relationships.  The relationships include ACTIVITY_INPUT, ACTIVITY_OUTPUT and
                HAS_METADATA.  First, we build a dictionary of the nodes using uuid as a key.  Next, we loop through the relationships looking for HAS_METADATA 
                relationships.  The HAS_METADATA relationships connect the Entity nodes with their metadata.  The data from the Metadata node
                becomes the 'metadata' attribute for the Entity node.
                """


                """Possible replacement:
                THIS WORKS...NEEDS LOTS of COMMENTS!!
                MATCH (entity_metadata)<-[r1:HAS_METADATA]-(e)<-[r2:ACTIVITY_OUTPUT]-(a:Activity)-[r3:HAS_METADATA]->(activity_metadata) 
                                WHERE e.hubmap_identifier = 'TEST0010-LK-1-1'
                                WITH [e,a, entity_metadata, activity_metadata] AS entities, COLLECT(r1) + COLLECT(r2) + COLLECT(r3) AS relationships
                                WITH [node in entities | node {.*, label:labels(node)}] AS nodes, [rel in relationships | rel { .*, fromNode: { label:labels(startNode(rel))[0], uuid:startNode(rel).uuid } , toNode: { label:labels(endNode(rel))[0], uuid:endNode(rel).uuid }, rel_data: { type: type(rel) } } ] as rels
                                RETURN nodes, rels
                UNION OPTIONAL MATCH (activity_metadata)<-[r1:HAS_METADATA]-(a:Activity)<-[r2:ACTIVITY_INPUT|:ACTIVITY_OUTPUT*]-(parent)-[r3:HAS_METADATA]->(parent_metadata),
                (e)<-[r4:ACTIVITY_OUTPUT]-(a:Activity) 
                                WHERE e.hubmap_identifier = 'TEST0010-LK-1-1'
                                WITH [parent,parent_metadata, a, activity_metadata] AS nodes, [rel in COLLECT(r1) + COLLECT(r3) + COLLECT(r4)+COLLECT(apoc.convert.toRelationship(r2)) | rel { .*, fromNode: { label:labels(startNode(rel))[0], uuid:startNode(rel).uuid } , toNode: { label:labels(endNode(rel))[0], uuid:endNode(rel).uuid }, rel_data: { type: type(rel) } } ] as rels
                                RETURN DISTINCT nodes, rels                

                uuid for TEST0010-LK-1-1 for testing: eda3916db4695d834eb6c51a893d06f1
                """
                
                stmt = """MATCH (n:Entity {{ uuid: '{uuid}' }}) 
                CALL apoc.path.subgraphAll(n, {{ {max_level_str} relationshipFilter:'<ACTIVITY_INPUT|<ACTIVITY_OUTPUT|HAS_METADATA>' }}) YIELD nodes, relationships
                WITH [node in nodes | node {{ .*, label:labels(node)[0] }} ] as nodes, 
                     [rel in relationships | rel {{ .*, fromNode: {{ label:labels(startNode(rel))[0], uuid:startNode(rel).uuid }} , toNode: {{ label:labels(endNode(rel))[0], uuid:endNode(rel).uuid }}, rel_data: {{ type: type(rel) }} }} ] as rels
                WITH {{ nodes:nodes, relationships:rels }} as json
                RETURN json""".format(uuid=uuid, max_level_str=max_level_str)
                    
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
                            
                        # TODO: clean up nodes
                        # remove nodes that lack metadata
                        
                        # need to devise a methodology for this
                        # try preprocessing the record['relationships'] here:
                        # make a copy of the node_dict called unreferenced_node_dict
                        # loop through the relationships and find all the has_metadata relationships
                        # for each node pair in the has_metadata relationship, delete it from the unreferenced_node_dict
                        # once the loop is finished, continue as before
                        # add some logic when generating the wasGenerated and used relationships.  If either node is in the 
                        # unreferenced_node_dict, then ignore the relationship
                            
                        # now, connect the nodes
                        for rel_record in record['relationships']:
                            from_uuid = rel_record['fromNode']['uuid']
                            to_uuid = rel_record['toNode']['uuid']
                            from_node = node_dict[from_uuid]
                            to_node = node_dict[to_uuid]
                            if rel_record['rel_data']['type'] == HubmapConst.HAS_METADATA_REL:
                                # assign the metadata node as the metadata attribute
                                # just extract the provenance information from the metadata node
                                
                                entity_timestamp_json = Provenance.get_json_timestamp(int(to_node[HubmapConst.PROVENANCE_CREATE_TIMESTAMP_ATTRIBUTE]))
                                provenance_data = {ProvConst.PROV_GENERATED_TIME_ATTRIBUTE : entity_timestamp_json}
                                type_code = None
                                isEntity = True
                                if HubmapConst.ENTITY_TYPE_ATTRIBUTE in from_node:
                                    type_code = from_node[HubmapConst.ENTITY_TYPE_ATTRIBUTE]
                                elif HubmapConst.ACTIVITY_TYPE_ATTRIBUTE in from_node:
                                    type_code = from_node[HubmapConst.ACTIVITY_TYPE_ATTRIBUTE]
                                    isEntity = False
                                label_text = None                                
                                if HubmapConst.LAB_IDENTIFIER_ATTRIBUTE in from_node:
                                    label_text = from_node[HubmapConst.LAB_IDENTIFIER_ATTRIBUTE]
                                else:
                                    label_text = from_node[HubmapConst.UUID_ATTRIBUTE]
                                    
                                # build metadata attribute from the Metadata node
                                metadata_attribute = {}
                                for attribute_key in to_node:
                                    if attribute_key not in self.metadata_ignore_attributes:
                                        if attribute_key in self.known_attribute_map:                                            
                                            # special case: timestamps
                                            if attribute_key == HubmapConst.PROVENANCE_MODIFIED_TIMESTAMP_ATTRIBUTE:
                                                provenance_data[self.known_attribute_map[attribute_key]] = Provenance.get_json_timestamp(int(to_node[attribute_key]))
                                        else: #add any extraneous data to the metadata attribute
                                            metadata_attribute[attribute_key] = to_node[attribute_key]
                                       
                                # Need to add the agent and organization here, plus the appropriate relationships (between the entity and the agent plus orgainzation)
                                agent_record = self.get_agent_record(to_node)
                                agent_unique_id = str(agent_record[ProvConst.HUBMAP_PROV_USER_EMAIL]).replace('@', '-')
                                agent_unique_id = str(agent_unique_id).replace('.', '-')
                                if ProvConst.HUBMAP_PROV_USER_UUID in agent_record:
                                    agent_unique_id =agent_record[ProvConst.HUBMAP_PROV_USER_UUID]
                                agent_uri = Provenance.build_uri('hubmap','agent',agent_unique_id)
                                organization_record = self.get_organization_record(to_node)
                                organization_uri = Provenance.build_uri('hubmap','organization',organization_record[ProvConst.HUBMAP_PROV_GROUP_UUID])
                                doc_agent = None
                                doc_org = None
                                
                                get_agent = prov_doc.get_record(agent_uri)
                                # only add this once
                                if len(get_agent) == 0:
                                    doc_agent = prov_doc.agent(agent_uri, agent_record)
                                else:
                                    doc_agent = get_agent[0]

                                get_org = prov_doc.get_record(organization_uri)
                                # only add this once
                                if len(get_org) == 0:
                                    doc_org = prov_doc.agent(organization_uri, organization_record)
                                else:
                                    doc_org = get_org[0]
                                
                                
                                                                
                                other_attributes = {ProvConst.PROV_LABEL_ATTRIBUTE : label_text,
                                                    ProvConst.PROV_TYPE_ATTRIBUTE : type_code, 
                                                    ProvConst.HUBMAP_DOI_ATTRIBUTE : from_node[HubmapConst.DOI_ATTRIBUTE],
                                                    ProvConst.HUBMAP_DISPLAY_DOI_ATTRIBUTE : from_node[HubmapConst.DISPLAY_DOI_ATTRIBUTE],
                                                    ProvConst.HUBMAP_DISPLAY_IDENTIFIER_ATTRIBUTE : label_text, 
                                                    ProvConst.HUBMAP_UUID_ATTRIBUTE : from_node[HubmapConst.UUID_ATTRIBUTE]                                                    
                                                    }
                                # only add metadata if it contains data
                                if len(metadata_attribute) > 0:
                                    other_attributes[ProvConst.HUBMAP_METADATA_ATTRIBUTE] = json.dumps(metadata_attribute)
                                # add the provenance data to the other_attributes
                                other_attributes.update(provenance_data)
                                if isEntity == True:
                                    prov_doc.entity(Provenance.build_uri('hubmap','entities',from_node['uuid']), other_attributes)
                                else:
                                    activity_timestamp_json = Provenance.get_json_timestamp(int(to_node[HubmapConst.PROVENANCE_CREATE_TIMESTAMP_ATTRIBUTE]))
                                    doc_activity = prov_doc.activity(Provenance.build_uri('hubmap','activities',from_node['uuid']), activity_timestamp_json, activity_timestamp_json, other_attributes)
                                    prov_doc.actedOnBehalfOf(doc_agent, doc_org, doc_activity)
                            elif rel_record['rel_data']['type'] in [HubmapConst.ACTIVITY_OUTPUT_REL, HubmapConst.ACTIVITY_INPUT_REL]:
                                to_node_uri = None
                                from_node_uri = None
                                if HubmapConst.ENTITY_TYPE_ATTRIBUTE in to_node:
                                    to_node_uri = Provenance.build_uri('hubmap', 'entities', to_node['uuid'])
                                else:
                                    to_node_uri = Provenance.build_uri('hubmap', 'activities', to_node['uuid'])
                                if HubmapConst.ENTITY_TYPE_ATTRIBUTE in from_node:
                                    from_node_uri = Provenance.build_uri('hubmap', 'entities', from_node['uuid'])
                                else:
                                    from_node_uri = Provenance.build_uri('hubmap', 'activities', from_node['uuid'])
                                
                                if rel_record['rel_data']['type'] == 'ACTIVITY_OUTPUT':
                                    #prov_doc.wasGeneratedBy(entity, activity, time, identifier, other_attributes)
                                    prov_doc.wasGeneratedBy(to_node_uri, from_node_uri)

                                if rel_record['rel_data']['type'] == 'ACTIVITY_INPUT':
                                    #prov_doc.used(activity, entity, time, identifier, other_attributes)
                                    prov_doc.used(to_node_uri, from_node_uri)
                                
                                # for now, simply create a "relation" where the fromNode's uuid is connected to a toNode's uuid via a relationship:
                                # ex: {'fromNodeUUID': '42e10053358328c9079f1c8181287b6d', 'relationship': 'ACTIVITY_OUTPUT', 'toNodeUUID': '398400024fda58e293cdb435db3c777e'}
                                rel_data_record = {'fromNodeUUID' : from_node['uuid'], 'relationship' : rel_record['rel_data']['type'], 'toNodeUUID' : to_node['uuid']}
                                relation_list.append(rel_data_record)
                        return_data = {'nodes' : node_dict, 'relations' : relation_list}  
                    except Exception as e:
                        raise e
      
      
                 
                # there is a bug in the JSON serializer.  So manually insert the prov prefix
                
                output_doc = prov_doc.serialize(indent=2) 
                output_doc = output_doc.replace('"prefix": {', '"prefix": {\n    "prov" : "http://www.w3.org/ns/prov#", ')
                
                #output_doc = prov_doc.serialize(format='rdf', rdf_format='trig')
                #output_doc = prov_doc.serialize(format='provn')
                return output_doc
            
            except ConnectionError as ce:
                print('A connection error occurred: ', str(ce.args[0]))
                raise ce
            except ValueError as ve:
                print('A value error occurred: ', ve.value)
                raise ve
            except Exception as e:
                print('An exception occurred in get_provenance_history: ' + str(e))
                traceback.print_exc()

    @staticmethod
    def build_uri(prefix, uri_type, identifier):
        return prefix + ':' + str(uri_type) + '/' + str(identifier)
    
    @staticmethod
    def get_json_timestamp(int_timestamp):
        date = datetime.datetime.fromtimestamp(int_timestamp / 1e3)
        jsondate = date.strftime("%Y-%m-%dT%H:%M:%S")
        return jsondate
     
    def get_agent_record(self, node_data):
        return_dict = {}
        for attribute_key in node_data:
            if attribute_key in self.agent_attribute_map:
                return_dict[self.agent_attribute_map[attribute_key]] = node_data[attribute_key]
        return_dict[PROV_TYPE] = 'prov:Person'
        return return_dict
    
    def get_organization_record(self, node_data):
    # lookup the node's provenance group using the group JSON file as a source
    # previously it relied on data found in the nodes, but that might be incomplete
        return_dict = {}
        group_record = {}
        if HubmapConst.PROVENANCE_GROUP_UUID_ATTRIBUTE in node_data:
            group_uuid = node_data[HubmapConst.PROVENANCE_GROUP_UUID_ATTRIBUTE]
            if group_uuid in self.groupsById:
                group_record = self.groupsById[group_uuid]
            else:
                raise LookupError('Cannot find group for uuid: ' + group_uuid)
        elif HubmapConst.PROVENANCE_GROUP_NAME_ATTRIBUTE in node_data:
            group_name = node_data[HubmapConst.PROVENANCE_GROUP_NAME_ATTRIBUTE]
            if group_name in self.groupsByName:
                group_record = self.groupsByName[group_name]
            #handle the case where the group UUID is incorrectly stored in the name field:
            elif group_name in self.groupsById:
                group_record = self.groupsById[group_name]
            else:
                raise LookupError('Cannot find group for name: ' + group_name)
        for attribute_key in group_record:
            if attribute_key in self.organization_attribute_map:
                return_dict[self.organization_attribute_map[attribute_key]] = group_record[attribute_key]
        return_dict[PROV_TYPE] = 'prov:Organization'
        return return_dict
    
    #get all group (tmc/component/Globus Groups/etc...) info as a dict directly from the
    #hubmap-globus-groups.json file
    def get_group_info(self):
        return self.groups
    
    def get_group_info_by_id(self):
        return self.groupsById
    
    def get_groups_by_tmc_prefix(self):
        return self.groups_by_tmc_prefix
    
if __name__ == "__main__":

    NEO4J_SERVER = ''
    NEO4J_USERNAME = ''
    NEO4J_PASSWORD = ''
    APP_CLIENT_ID = ''
    APP_CLIENT_SECRET = ''
    UUID_WEBSERVICE_URL = ''
    HUBMAP_WEBSERVICE_FILEPATH = ''
    
       
    conf_data = {'NEO4J_SERVER' : NEO4J_SERVER, 'NEO4J_USERNAME': NEO4J_USERNAME, 
                 'NEO4J_PASSWORD': NEO4J_PASSWORD,
                 'APP_CLIENT_ID': APP_CLIENT_ID,
                 'APP_CLIENT_SECRET': APP_CLIENT_SECRET,
                 'UUID_WEBSERVICE_URL': UUID_WEBSERVICE_URL,
                 'HUBMAP_WEBSERVICE_FILEPATH': HUBMAP_WEBSERVICE_FILEPATH}

    prov = Provenance(conf_data['APP_CLIENT_ID'], conf_data['APP_CLIENT_SECRET'], conf_data['UUID_WEBSERVICE_URL'])
    # this is a Vanderbilt uuid:  uuid = '4614ea24338ec820569f988196a5c503'
    uuid = ''
    conn = Neo4jConnection(NEO4J_SERVER, NEO4J_USERNAME, NEO4J_PASSWORD)
    nexus_token = ''
    driver = conn.get_driver()
    

    provenance_data = prov.get_provenance_history(driver, uuid)

    print("Provenance data: " + str(provenance_data))
    #print('max depth')
    #history_data = prov.get_provenance_history(driver, uuid, None)
    
    #g.serialize(format='rdf', rdf_format='trig')
    
    #print(history_data.serialize(indent=2))
    #print(history_data.serialize(format='rdf', rdf_format='trig'))
    #print(history_data.serialize(format='provn'))

    
    #print('depth=4')
    #history_data = prov.get_provenance_history(driver, uuid)
    #print(history_data)
    #print(history_data.serialize(format='rdf', rdf_format='trig'))
    #print(history_data.serialize(format='provn'))
    
    """
    print('depth=4')
    history_data = prov.get_provenance_history(driver, uuid, 4)
    print(history_data.serialize(indent=2))
    """
    
    """
    your_timestamp = 1571248733444
    eastern = timezone('US/Eastern')
    date = datetime.datetime.fromtimestamp(your_timestamp / 1e3)
    jsondate= date.strftime("%Y-%m-%dT%H:%M:%S")
    #2012-04-03T13:35:23
    print(jsondate)
    print(date)
    #localized_timestamp = eastern.localize(date)
    """
