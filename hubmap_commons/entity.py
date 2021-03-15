'''
Created on Apr 18, 2019

@author: chb69
'''
#from neo4j import TransactionError, CypherError
import sys
from hubmap_commons.hubmap_const import HubmapConst 
from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.uuid_generator import UUID_Generator
from hubmap_commons.hm_auth import AuthCache, AuthHelper
import pprint
from flask import Response
from hubmap_commons.autherror import AuthError
import ast
from hubmap_commons import string_helper
import json
from builtins import staticmethod
import traceback

#import appconfig

class Entity(object):
    '''
    classdocs
    '''
    
    entity_config = {}

    def __init__(self, app_client_id, app_client_secret, uuid_webservice_url):
        self.entity_config['APP_CLIENT_ID'] = app_client_id
        self.entity_config['APP_CLIENT_SECRET'] = app_client_secret
        self.entity_config['UUID_WEBSERVICE_URL'] = uuid_webservice_url

    @staticmethod
    def get_uuid_list(uuid_webservice_url, token, identifier_list):
        uuid_data = []
        ug = UUID_Generator(uuid_webservice_url)
        try:
            for identifer in identifier_list:
                hmuuid_data = ug.getUUID(token, identifer)
                if len(hmuuid_data) != 1:
                    raise ValueError("Could not find information for identifier " + identifer)
                if 'hm_uuid' not in hmuuid_data[0]:
                    raise ValueError("Could not find information for identifier " + identifer)
                uuid_data.append(hmuuid_data[0]['hm_uuid'])
        except:
            raise ValueError('Unable to resolve UUID for: ' + identifer)
        return uuid_data
    
    @staticmethod
    # NOTE: This will return a single entity, activity, or agent
    def get_entity(driver, identifier): 
        with driver.session() as session:
            return_list = []
            try:
                match_clause = "MATCH (entity) "
                where_clause = " WHERE entity.{uuid_attrib}= $identifier ".format(uuid_attrib=HubmapConst.UUID_ATTRIBUTE)
                stmt = Entity.get_generic_entity_stmt(match_clause, where_clause)

                current_uuid = None
                
                # this code assumes there will be only one entity returned
                for record in session.run(stmt, identifier=identifier):
                    dataset_record = record['entity_properties']
                    #while running through the data returned, only
                    #keep one set of entity properties per uuid
                    #in general, there should only be one entity returned
                    # but the entities may have multiple descendants 
                    if current_uuid != record['uuid']:
                        current_uuid = record['uuid']                    
                        return_list.append(dataset_record)
                if len(return_list) == 0:
                    raise LookupError('Unable to find entity using identifier:' + identifier)
                if len(return_list) > 1:
                    raise LookupError('Error more than one entity found with identifier:' + identifier)
                return return_list[0]                    
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except:
                print ('A general error occurred: ')
                for x in sys.exc_info():
                    print (x)
                raise


    @staticmethod
    # NOTE: This will return a list of all entities matching a type
    def get_entity_type_list(driver): 
        with driver.session() as session:
            return_list = []
            try:
                #TODO: I can use the OR operator to match on either uuid or doi:
                #MATCH (e) WHERE e.label= 'test dataset create file10' OR e.label= 'test dataset create file7' RETURN e
                stmt = "MATCH (e:Entity) RETURN DISTINCT e.{type_attrib} AS type_name".format(type_attrib=HubmapConst.ENTITY_TYPE_ATTRIBUTE)

                for record in session.run(stmt):
                    dataset_record = record['type_name']
                    return_list.append(dataset_record)
                return return_list                   
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except:
                print ('A general error occurred: ')
                for x in sys.exc_info():
                    print (x)
                raise

    @staticmethod
    def does_identifier_exist(driver, identifier):
        try:
            entity = Entity.get_entity(driver, identifier)
            return True
        except:
            return False

    # Note: when editing an entity, you are really editing the metadata attached to the entity
    def edit_entity(self, driver, token, entityuuid, entityjson): 
        tx = None
        try:
            if Entity.does_identifier_exist(driver, entityuuid) == False:
                raise ValueError("Cannot find entity with uuid: " + entityuuid)
            metadata_list = Entity.get_entities_by_relationship(driver, entityuuid, HubmapConst.HAS_METADATA_REL)
            if len(metadata_list) > 1:
                raise ValueError("Found more than one metadata entry attached to uuid: " + entityuuid)
            metadata_entity = metadata_list[0]
            authcache = None
            if AuthHelper.isInitialized() == False:
                authcache = AuthHelper.create(
                    self.entity_config['APP_CLIENT_ID'], self.entity_config['APP_CLIENT_SECRET'])
            else:
                authcache = AuthHelper.instance()
            userinfo = authcache.getUserInfo(token, True)
            #replace the uuid with the metadata uuid
            entityjson[HubmapConst.UUID_ATTRIBUTE] = metadata_entity[HubmapConst.UUID_ATTRIBUTE]
            stmt = Neo4jConnection.get_update_statement(entityjson, True)
            with driver.session() as session:
                tx = session.begin_transaction()
                tx.run(stmt)
                tx.commit()
                return metadata_entity[HubmapConst.UUID_ATTRIBUTE]
        except TransactionError as te: 
            print ('A transaction error occurred: ', te.value)
            if tx.closed() == False:
                tx.rollback()
            raise te
        except CypherError as cse:
            print ('A Cypher error was encountered: ', cse.message)
            if tx.closed() == False:
                tx.rollback()
            raise cse               
        except:
            print ('A general error occurred: ')
            for x in sys.exc_info():
                print (x)
            if tx.closed() == False:
                tx.rollback()
            raise
        
    
    def can_user_edit_entity(self, driver, token, entityuuid): 
        try:
            if Entity.does_identifier_exist(driver, entityuuid) == False:
                raise ValueError("Cannot find entity with uuid: " + entityuuid)
            metadata_list = Entity.get_entities_by_relationship(driver, entityuuid, HubmapConst.HAS_METADATA_REL)
            if len(metadata_list) > 1:
                raise ValueError("Found more than one metadata entry attached to uuid: " + entityuuid)
            metadata_entity = metadata_list[0]
            authcache = None
            if AuthHelper.isInitialized() == False:
                authcache = AuthHelper.create(
                    self.entity_config['APP_CLIENT_ID'], self.entity_config['APP_CLIENT_SECRET'])
            else:
                authcache = AuthHelper.instance()
            userinfo = authcache.getUserInfo(token, True)
            if 'hmgroupids' not in userinfo:
                raise ValueError("Cannot find Hubmap Group information for token")
            if HubmapConst.PROVENANCE_GROUP_UUID_ATTRIBUTE not in metadata_entity:
                raise ValueError("Cannot find Hubmap Group information in metadata entity associated with uuid: " + entityuuid)
                
            hmgroups = userinfo['hmgroupids']
            for g in hmgroups:
                if str(g).lower() == str(metadata_entity[HubmapConst.PROVENANCE_GROUP_UUID_ATTRIBUTE]).lower():
                    return True
            return False
        except BaseException as be:
            pprint(be)
            raise be

    def get_user_groups(self, token):
        try:
            authcache = None
            if AuthHelper.isInitialized() == False:
                authcache = AuthHelper.create(
                    self.entity_config['APP_CLIENT_ID'], self.entity_config['APP_CLIENT_SECRET'])
            else:
                authcache = AuthHelper.instance()
            userinfo = authcache.getUserInfo(token, True)

            if type(userinfo) == Response and userinfo.status_code == 401:
                raise AuthError('token is invalid.', 401)

            if 'hmgroupids' not in userinfo:
                raise ValueError("Cannot find Hubmap Group information for token")
            return_list = []
            group_list = AuthCache.getHMGroups()
            for group_uuid in userinfo['hmgroupids']:
                for group_name in group_list.keys():
                    if group_list[group_name]['uuid'] == group_uuid:
                        return_list.append(group_list[group_name])
                        break
            return return_list
        except:
            print ('A general error occurred: ')
            for x in sys.exc_info():
                print (x)
            raise

    def get_user_roles(self, token):
        try:
            authcache = None
            if AuthHelper.isInitialized() == False:
                authcache = AuthHelper.create(
                    self.entity_config['APP_CLIENT_ID'], self.entity_config['APP_CLIENT_SECRET'])
            else:
                authcache = AuthHelper.instance()
            userinfo = authcache.getUserInfo(token, True)

            if type(userinfo) == Response and userinfo.status_code == 401:
                raise AuthError('token is invalid.', 401)

            if 'hmgroupids' not in userinfo:
                raise ValueError("Cannot find Hubmap Group information for token")
            return_list = []
            role_list = AuthCache.getHMRoles()
            for role_uuid in userinfo['hmroleids']:
                for role_name in role_list.keys():
                    if role_list[role_name]['uuid'] == role_uuid:
                        return_list.append(role_list[role_name])
                        break
            return return_list
        except:
            print ('A general error occurred: ')
            for x in sys.exc_info():
                print (x)
            raise
    
    def get_readonly_user_groups(self, token):
        return self.get_user_groups_generic(token, 'READONLY')

    def get_writeable_user_groups(self, token):
        return self.get_user_groups_generic(token, 'WRITEABLE')

    def get_user_groups_generic(self, token, group_type):
        try:
            authcache = None
            if AuthHelper.isInitialized() == False:
                authcache = AuthHelper.create(
                    self.entity_config['APP_CLIENT_ID'], self.entity_config['APP_CLIENT_SECRET'])
            else:
                authcache = AuthHelper.instance()
            userinfo = authcache.getUserInfo(token, True)

            if type(userinfo) == Response and userinfo.status_code == 401:
                raise AuthError('token is invalid.', 401)

            if 'hmgroupids' not in userinfo:
                raise ValueError("Cannot find Hubmap Group information for token")
            return_list = []
            bWriteable = False
            if group_type == 'WRITEABLE':
                bWriteable = True
            
            
            group_list = AuthCache.getHMGroups()
            
            # if the users is a member of the READONLY group and you want a list
            # of read only groups, then just return all the groups
            readonly_group_uuid = '5777527e-ec11-11e8-ab41-0af86edb4424'            
            if group_type == 'READONLY' and readonly_group_uuid in userinfo['hmgroupids']:
                for group_name in group_list.keys():
                    return_list.append(group_list[group_name])
                return return_list
                    
            for group_uuid in userinfo['hmgroupids']:
                for group_name in group_list.keys():
                    if group_list[group_name]['uuid'] == group_uuid:
                        if group_list[group_name]['generateuuid'] == bWriteable:
                            return_list.append(group_list[group_name])
                        break
            return return_list
        except:
            print ('A general error occurred: ')
            for x in sys.exc_info():
                print (x)
            raise
       
    def get_editable_entities_by_type(self, driver, token, type_code=None): 
        with driver.session() as session:
            return_list = []

            try:
                #if type_code != None:
                #    general_type = HubmapConst.get_general_node_type_attribute(type_code)
                group_list = []            
                hmgroups = self.get_user_groups(token)
                for g in hmgroups:
                    group_record = self.get_group_by_identifier(g['name'])
                    group_list.append(group_record['uuid'])
                matching_stmt = ""
                if type_code != None:
                    if str(type_code).lower() == 'donor':
                        # ensure proper case
                        type_code = 'Donor'
                        type_attrib = HubmapConst.ENTITY_TYPE_ATTRIBUTE
                        matching_stmt = "MATCH (entity {{{type_attrib}: '{type_code}'}})".format(
                            type_attrib=type_attrib, type_code=type_code, 
                            rel_code=HubmapConst.HAS_METADATA_REL)
                        where_clause = " WHERE entity.{entitytype_attr} IS NOT NULL ".format(entitytype_attr=HubmapConst.ENTITY_TYPE_ATTRIBUTE)
                    else:
                        type_attrib = HubmapConst.SPECIMEN_TYPE_ATTRIBUTE                        
                        matching_stmt = "MATCH (entity)-[:{rel_code}]->(m {{ {type_attrib}: '{type_code}' }})".format(
                            type_attrib=type_attrib, type_code=type_code, rel_code=HubmapConst.HAS_METADATA_REL)
                        where_clause = " WHERE entity.{entitytype_attr} IS NOT NULL ".format(entitytype_attr=HubmapConst.ENTITY_TYPE_ATTRIBUTE)
                        
                else:
                    matching_stmt = "MATCH (entity:Entity) "
                    where_clause = " WHERE entity.{entitytype_attr} IS NOT NULL AND entity.{entitytype_attr} <> 'Lab'".format(entitytype_attr=HubmapConst.ENTITY_TYPE_ATTRIBUTE)
                order_clause = " ORDER BY entity_metadata_properties.{provenance_timestamp} DESC ".format(provenance_timestamp=HubmapConst.PROVENANCE_MODIFIED_TIMESTAMP_ATTRIBUTE)
                """stmt = matching_stmt + " WHERE a.{entitytype_attr} IS NOT NULL RETURN a.{uuid_attr} AS entity_uuid, a.{hubmapid_attr} AS hubmap_identifier, a.{entitytype_attr} AS datatype, a.{doi_attr} AS entity_doi, a.{display_doi_attr} as entity_display_doi, properties(m) AS metadata_properties ORDER BY m.{provenance_timestamp} DESC".format(
                    uuid_attr=HubmapConst.UUID_ATTRIBUTE, entitytype_attr=HubmapConst.ENTITY_TYPE_ATTRIBUTE, hubmapid_attr=HubmapConst.LAB_IDENTIFIER_ATTRIBUTE,
                    activitytype_attr=HubmapConst.ACTIVITY_TYPE_ATTRIBUTE, doi_attr=HubmapConst.DOI_ATTRIBUTE, 
                    display_doi_attr=HubmapConst.DISPLAY_DOI_ATTRIBUTE, provenance_timestamp=HubmapConst.PROVENANCE_MODIFIED_TIMESTAMP_ATTRIBUTE)"""
                stmt = Entity.get_generic_entity_stmt(matching_stmt, where_clause, "", order_clause)

                print("Here is the query: " + stmt)
                
                readonly_group_list = self.get_readonly_user_groups(token)
                writeable_group_list = self.get_writeable_user_groups(token)
                readonly_uuid_list = []
                writeable_uuid_list = []
                #build UUID group list
                for readonly_group_data in readonly_group_list:
                    readonly_uuid_list.append(readonly_group_data['uuid'])
                for writeable_group_data in writeable_group_list:
                    writeable_uuid_list.append(writeable_group_data['uuid'])
                
                return_dict = {}
                for record in session.run(stmt):
                    data_record = {}
                    data_record['uuid'] = record['uuid']
                    data_record['entity_display_doi'] = record['display_doi']
                    data_record['entity_doi'] = record['doi']
                    data_record['datatype'] = record['datatype']
                    data_record['properties'] = record['entity_metadata_properties']
                    data_record['hubmap_identifier'] = record['hubmap_identifier']
                    # determine if the record is writable by the current user
                    data_record['writeable'] = False
                    if record['entity_metadata_properties'] != None:
                        if 'provenance_group_uuid' in record['entity_metadata_properties']:
                            if record['entity_metadata_properties']['provenance_group_uuid'] in writeable_uuid_list:
                                data_record['writeable'] = True
                    return_dict[data_record['uuid']] = data_record
                return list(return_dict.values())                    
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except:
                print ('A general error occurred: ')
                for x in sys.exc_info():
                    print (x)
                raise

    def get_group_by_identifier(self, identifier):
        if len(identifier) == 0:
            raise ValueError("identifier cannot be blank")
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.entity_config['APP_CLIENT_ID'], self.entity_config['APP_CLIENT_SECRET'])
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

    def get_group_by_name(self, group_name):
        if len(group_name) == 0:
            raise ValueError("group_name cannot be blank")
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.entity_config['APP_CLIENT_ID'], self.entity_config['APP_CLIENT_SECRET'])
        else:
            authcache = AuthHelper.instance()
        groupinfo = authcache.getHuBMAPGroupInfo()
        # search through the keys for the identifier, return the value
        for k in groupinfo.values():
            if str(k['name']).lower() == str(group_name).lower()  or str(k['displayname']).lower() == str(group_name).lower():
                group = k
                return group
            if 'tmc_prefix' in k:
                if str(k['tmc_prefix']).lower() == str(group_name).lower():
                    group = k
                    return group

        raise ValueError("cannot find a Hubmap group matching: [" + group_name + "]")
        
    @staticmethod
    def get_entities_by_type(driver, type_code): 
        with driver.session() as session:
            return_list = []

            # by default assume Entity type
            type_attrib = HubmapConst.ENTITY_TYPE_ATTRIBUTE
            type_code = getTypeCode(type_code)

            try:
                match_clause = "MATCH (entity {{{type_attrib}: '{type_code}'}}) ".format(type_attrib=type_attrib, type_code=type_code)
                stmt = Entity.get_generic_entity_stmt(match_clause)

                # build a unique list of uuids
                return_dict = {}
                for record in session.run(stmt):
                    current_uuid = record['uuid']
                    return_dict[current_uuid] = current_uuid
                return_list = list(return_dict.keys())
                return return_list                    
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except:
                print ('A general error occurred: ')
                for x in sys.exc_info():
                    print (x)
                raise

    @staticmethod
    def get_entities_by_types(driver, types): 
        with driver.session() as session:
            entities = []

            if len(types) == 0: return entities

            # by default assume Entity type
            type_attrib = HubmapConst.ENTITY_TYPE_ATTRIBUTE
            type_codes_str = "[" + ','.join([f"'{getTypeCode(t)}'" for t in types]) + "]"

            try:     
                #match_clause = "MATCH (entity {{{type_attrib}: '{type_code}'}}) ".format(type_attrib=type_attrib, type_code=type_code)
                #stmt = Entity.get_generic_entity_stmt(match_clause)
                #stmt = f'MATCH (e:Entity), (e)-[r1:HAS_METADATA]->(m) WHERE e.entitytype IN {type_codes_str} RETURN e, m'

                match_clause = "MATCH (entity) "
                where_clause = " WHERE entity.entitytype IN {type_codes_str} ".format(type_codes_str=type_codes_str)
                stmt = Entity.get_generic_entity_stmt(match_clause, where_clause)
                entity_dict = {}
                for record in session.run(stmt):
                    entity = {}
                    entity.update(record.get('entity_properties'))
                    entity['metadata'] = record.get('entity_metadata_properties')
                    uuid = record.get('uuid')
                    entity_dict[uuid] = entity

                return list(entity_dict.values())
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except:
                print ('A general error occurred: ')
                for x in sys.exc_info():
                    print (x)
                raise


    @staticmethod
    def get_entity_count_by_type(driver, type_code): 
        try:
            entity_list = Entity.get_entities_by_type(driver, type_code)
            return len(entity_list)
        except CypherError as cse:
            print ('A Cypher error was encountered: '+ cse.message)
            raise
        except:
            print ('A general error occurred: ')
            for x in sys.exc_info():
                print (x)
            raise
        


    """This method builds a Cypher statement that returns a set of nodes constrained on the given UUID
    and relationship type.  This method also includes an optional "direction" parameter.  This can be used 
    to constrain the Cypher query further to only return the matching nodes adhering to the directionality of the query.
    For more details: https://neo4j.com/docs/cypher-manual/current/clauses/match/#directed-rels-and-variable.
    By default, the direction parameter is None.  This is the most inclusive parameter and will match nodes regardless of direction."""
    @staticmethod
    def get_entity_from_relationship_statement(identifier, relationship_label, direction=None):
        left_dir = ''
        right_dir = ''
        if str(direction).lower() not in ['left', 'right']:
            direction = None
        if str(direction).lower() == 'left':
            left_dir = '<'
        elif str(direction).lower() == 'right':
            right_dir = '>'
        
        stmt = "MATCH (e){left_dir}-[:{relationship_label}]-{right_dir}(a) WHERE e.{uuid_attrib}= '{identifier}' RETURN CASE WHEN e.{entitytype} is not null THEN e.{entitytype} WHEN e.{activitytype} is not null THEN e.{activitytype} ELSE e.{agenttype} END AS datatype, e.{uuid_attrib} AS uuid, e.{doi_attrib} AS doi, e.{doi_display_attrib} AS display_doi, e.{hubmap_identifier_attrib} AS hubmap_identifier, properties(a) AS properties".format(
            identifier=identifier,uuid_attrib=HubmapConst.UUID_ATTRIBUTE, doi_attrib=HubmapConst.DOI_ATTRIBUTE, doi_display_attrib=HubmapConst.DISPLAY_DOI_ATTRIBUTE,
                entitytype=HubmapConst.ENTITY_TYPE_ATTRIBUTE, activitytype=HubmapConst.ACTIVITY_TYPE_ATTRIBUTE, agenttype=HubmapConst.AGENT_TYPE_ATTRIBUTE,
                hubmap_identifier_attrib=HubmapConst.LAB_IDENTIFIER_ATTRIBUTE,
                relationship_label=relationship_label, right_dir=right_dir, left_dir=left_dir)
        return stmt                  

    @staticmethod
    def get_entity_metadata(driver, identifier):
        entity_list = Entity.get_entities_by_relationship(driver, identifier, HubmapConst.HAS_METADATA_REL, "right")
        if len(entity_list) > 1:
            raise ValueError("Error: more than one metadata object found for identifier: " + identifier)
        if len(entity_list) == 0:
            raise ValueError("Error: no metadata object found for identifier: " + identifier)
        return entity_list[0]                  

    @staticmethod
    def get_entities_and_children_by_relationship(driver, identifier, relationship_label): 
        '''Return an object representing the identifier plus its children associated with the relationship_label
        
        :param driver: the neo4j connection
        :param identifier: a uuid for an entity.  This uuid will be used to find all the "children" entities
            related to the uuid.
        :param relationship_label: the name of a relationship in the neo4j graph.
        
        :return an object with the uuid attributes, plus an array with the children objects
        '''
        
        """This Cypher query will return data about the incoming entity (identified by the identifier parameter)
        and a list of all the entities associated with it given a particular relationship (the relationship_label parameter).
        The query returns entity level information regarding the incoming entity (datatype, uuid, doi, display_doi, hubmap_identifier)
        plus any connected metadata (entity_metadata_properties).  These records will repeat for each child returned.  For each
        child, the query returns: child_entity_properties, child_metadata_properties.          
        """
        
        #this is a collection, so we only return only collections which 
        #are marked for doi registration (has_doi can be true or false)
        addl_where = ""
        if relationship_label == HubmapConst.IN_COLLECTION_REL:
            addl_where = " and not entity.has_doi is null "
            
        match_clause = """MATCH (entity)<-[:{relationship_label}]-(child_entity)
        WHERE entity.{uuid_attrib}= '{identifier}' {addl_where}
        OPTIONAL MATCH (child_entity)-[:{has_metadata_attr}]->(child_metadata)""".format(relationship_label=relationship_label,
                                                                                         uuid_attrib=HubmapConst.UUID_ATTRIBUTE, identifier=identifier, 
                                                                                         has_metadata_attr=HubmapConst.HAS_METADATA_REL,
                                                                                         addl_where=addl_where)
        additional_return_clause = ", properties(child_entity) AS child_entity_properties, properties(child_metadata) AS child_metadata_properties "

        
        #
        #    additional_return_clause = additional_return_clause + ", entity."
        order_by_clause = " ORDER BY entity.{uuid_attrib} ".format(uuid_attrib=HubmapConst.UUID_ATTRIBUTE)
        stmt = Entity.get_generic_entity_stmt(match_clause, "", additional_return_clause, order_by_clause)
        print(stmt)
        with driver.session() as session:
            child_dict = {}
            return_object = {}
            try:
                vals = session.run(stmt)
                for record in vals:
                    #only create the return object once
                    if return_object == {}:
                        return_object['uuid'] = record['uuid']
                        return_object['entitytype'] = record['datatype']
                        return_object['doi'] = record['doi']
                        return_object['display_doi'] = record['display_doi']
                        return_object['hubmap_identifier'] = record['hubmap_identifier']
                        return_object['properties'] = record['entity_metadata_properties']
                        if 'has_doi' in record['entity_properties']:
                            return_object['has_doi'] = record['entity_properties']['has_doi']
                        if 'creators' in record['entity_properties'] and not string_helper.isBlank(record['entity_properties']['creators']):
                            creators_arry = json.loads(record['entity_properties']['creators'])
                            return_object['creators'] = creators_arry
                        if 'contacts' in record['entity_properties'] and not string_helper.isBlank(record['entity_properties']['contacts']):
                            contacts_arry = json.loads(record['entity_properties']['contacts'])
                            return_object['contacts'] = contacts_arry                            
                        if 'provenance_create_timestamp' in record['entity_properties']:
                            return_object['provenance_create_timestamp'] = record['entity_properties']['provenance_create_timestamp']
                        if 'provenance_modified_timestamp' in record['entity_properties']:
                            return_object['provenance_modified_timestamp'] = record['entity_properties']['provenance_modified_timestamp']
                        if  'description' in record['entity_properties'] and not string_helper.isBlank(record['entity_properties']['description']):
                            return_object['description'] = record['entity_properties']['description']
                        if  'provenance_user_displayname' in record['entity_properties'] and not string_helper.isBlank(record['entity_properties']['provenance_user_displayname']):
                            return_object['provenance_user_displayname'] = record['entity_properties']['provenance_user_displayname']

                        if  'label' in record['entity_properties'] and not string_helper.isBlank(record['entity_properties']['label']):
                            return_object['name'] = record['entity_properties']['label']
                        if 'doi_url' in record['entity_properties'] and not string_helper.isBlank(record['entity_properties']['doi_url']):
                            return_object['doi_url'] = record['entity_properties']['doi_url']
                        if 'registered_doi' in record['entity_properties'] and not string_helper.isBlank(record['entity_properties']['registered_doi']):
                            return_object['registered_doi'] = record['entity_properties']['registered_doi']
                            
                        if record['entity_metadata_properties'] != None:
                            new_metadata_dict = {}
                            for key in record['entity_metadata_properties'].keys():
                                new_metadata_dict[key] = record['entity_metadata_properties'][key]
                                # check to see if the current property contains an array or object
                                if isinstance(record['entity_metadata_properties'][key], str):
                                    if str(record['entity_metadata_properties'][key]).startswith('[') or str(record['child_metadata_properties'][key]).startswith('{'):
                                        new_metadata_dict[key] = ast.literal_eval(record['entity_metadata_properties'][key])
                            return_object['properties'] = new_metadata_dict
                        else:
                            return_object['child_metadata_properties'] = None
                    child_object = {}
                    if record['child_entity_properties'] != None:
                        child_object['uuid'] = record['child_entity_properties']['uuid']
                        child_object['entitytype'] = record['child_entity_properties']['entitytype']
                        child_object['doi'] = record['child_entity_properties']['doi']
                        child_object['display_doi'] = record['child_entity_properties']['display_doi']
                        if 'hubmap_identifier' in record['child_entity_properties']:
                            child_object['hubmap_identifier'] = record['child_entity_properties']['hubmap_identifier']
                        if record['child_metadata_properties'] != None:
                            new_metadata_dict = {}
                            for key in record['child_metadata_properties'].keys():
                                new_metadata_dict[key] = record['child_metadata_properties'][key]
                                # check to see if the current property contains an array or object
                                if isinstance(record['child_metadata_properties'][key], str):
                                    if str(record['child_metadata_properties'][key]).startswith('[') or str(record['child_metadata_properties'][key]).startswith('{'):
                                        new_metadata_dict[key] = ast.literal_eval(record['child_metadata_properties'][key])
                            child_object['properties'] = new_metadata_dict
                        # only add the child object if it has child_enity_properties
                        child_dict[child_object['uuid']] = child_object
                return_object['items'] = list(child_dict.values())
                return return_object                   
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except:
                print ('A general error occurred: ')
                for x in sys.exc_info():
                    print (x)
                raise
        


    @staticmethod
    def get_entities_by_relationship(driver, identifier, relationship_label, direction=None): 
        with driver.session() as session:
            return_list = []

            try:
                stmt = Entity.get_entity_from_relationship_statement(identifier, relationship_label, direction)

                for record in session.run(stmt):
                    # add some data elements
                    # since metadata lacks doi and display_doi
                    # use the doi and display doi from the entity
                    dataset_record = record['properties']
                    #dataset_record['entity_uuid'] = record['uuid']
                    if record.get('hubmap_identifier', None) != None:
                        dataset_record['hubmap_identifier'] = record['hubmap_identifier']
                    dataset_record['doi'] = record['doi']
                    dataset_record['display_doi'] = record['display_doi']
                    #remove entitytype since it will be the other entity's type
                    dataset_record.pop('entitytype')
                    # re-insert the entity type corresponding to the original entity                    
                    dataset_record['entitytype'] = record['datatype']
                    return_list.append(dataset_record)
                return return_list                    
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except:
                print ('A general error occurred: ')
                for x in sys.exc_info():
                    print (x)
                raise
            
    ''' unused method?
    @staticmethod
    def add_datafile_entity(self, driver, entity_uuid, activity_uuid, filepath, label): 
        # step 1: the filepath exists
        """TODO: fix this code
           check that the filepath exists
        """
        
        # step 2: check that the entity_uuid already exists
        if Entity.does_identifier_exist(driver, entity_uuid) != True:
            raise LookupError('Cannot find entity_uuid: ' + entity_uuid)        
        
        # step 3: check that the activity_uuid already exists
        if Entity.does_identifier_exist(driver, activity_uuid) != True:
            raise LookupError('Cannot find activity_uuid: ' + activity_uuid)        

        with driver.session() as session:
            tx = None
            try:
                ug = UUID_Generator(self.entity_config['UUID_WEBSERVICE_URL'])
                file_uuid = ug.getNewUUID()

                tx = session.begin_transaction()
                # step 4: create the entity representing the file
                file_record = {HubmapConst.UUID_ATTRIBUTE : file_uuid,  
                                    HubmapConst.ENTITY_TYPE_ATTRIBUTE: HubmapConst.FILE_TYPE_CODE, HubmapConst.FILE_PATH_ATTRIBUTE: filepath }
                stmt = Neo4jConnection.get_create_statement(file_record, HubmapConst.ENTITY_NODE_NAME, HubmapConst.FILE_TYPE_CODE, False)
                tx.run(stmt)
                # step 5: create the associated activity
                activity_uuid = ug.getNewUUID()
                
                #TODO: Add provenance data in addition to the TIMESTAMP
                activity_record = {HubmapConst.UUID_ATTRIBUTE : activity_uuid, HubmapConst.ACTIVITY_TYPE_ATTRIBUTE : HubmapConst.ADD_FILE_ACTIVITY_TYPE_CODE}
                stmt = Neo4jConnection.get_create_statement(activity_record, HubmapConst.ACTIVITY_NODE_NAME, HubmapConst.ADD_FILE_ACTIVITY_TYPE_CODE, True)
                tx.run(stmt)                
                # step 6: create the relationships
                stmt = Neo4jConnection.create_relationship_statement(entity_uuid, HubmapConst.ACTIVITY_INPUT_REL, activity_uuid)
                tx.run(stmt)
                stmt = Neo4jConnection.create_relationship_statement(activity_uuid, HubmapConst.ACTIVITY_OUTPUT_REL, file_uuid)
                tx.run(stmt)
                tx.commit()
                return file_uuid
            except TransactionError as te: 
                print ('A transaction error occurred: ', te.value)
                if tx.closed() == False:
                    tx.rollback()
            except CypherError as cse:
                print ('A Cypher error was encountered: ', cse.message)
                if tx.closed() == False:
                    tx.rollback()
            except:
                print ('A general error occurred: ')
                for x in sys.exc_info():
                    print (x)
                if tx.closed() == False:
                    tx.rollback()
    '''

    ''' unused method?
    @staticmethod
    #TODO: I could abstract this more with a signature like:
    #connect_entities(self, driver, orig_uuid, connected_uuid, relationship_activity_type_code)
    def derive_entity(self, driver, orig_uuid, derived_uuid): 
        
        # step 1: check that the uuids already exist
        if Entity.does_identifier_exist(orig_uuid) != True:
            raise LookupError('Cannot find orig_uuid: ' + orig_uuid)        
        if Entity.does_identifier_exist(derived_uuid) != True:
            raise LookupError('Cannot find derived_uuid: ' + derived_uuid)        
        
        with driver.session() as session:
            tx = None
            try:
                # step 2: create the associated activity
                ug = UUID_Generator(self.entity_config['UUID_WEBSERVICE_URL'])
                activity_uuid = ug.getNewUUID()
                
                #TODO: Add provenance data in addition to the TIMESTAMP
                activity_record = {HubmapConst.UUID_ATTRIBUTE : activity_uuid, HubmapConst.ACTIVITY_TYPE_ATTRIBUTE : HubmapConst.DERIVED_ACTIVITY_TYPE_CODE}
                stmt = Neo4jConnection.get_create_statement(activity_record, HubmapConst.ACTIVITY_NODE_NAME, HubmapConst.DERIVED_ACTIVITY_TYPE_CODE, True)
                tx.run(stmt)                
                # step 5: create the relationships
                stmt = Neo4jConnection.create_relationship_statement(orig_uuid, HubmapConst.ACTIVITY_INPUT_REL, activity_uuid)
                tx.run(stmt)
                stmt = Neo4jConnection.create_relationship_statement(activity_uuid, HubmapConst.ACTIVITY_OUTPUT_REL, derived_uuid)
                tx.run(stmt)
                tx.commit()
                return activity_uuid
            except TransactionError as te: 
                print ('A transaction error occurred: ', te.value)
                if tx.closed() == False:
                    tx.rollback()
            except CypherError as cse:
                print ('A Cypher error was encountered: ', cse.message)
                if tx.closed() == False:
                    tx.rollback()
            except:
                print ('A general error occurred: ')
                for x in sys.exc_info():
                    print (x)
                if tx.closed() == False:
                    tx.rollback()
    '''

    @staticmethod
    def get_node_properties(driver, stmt, there_can_be_only_one=False): 
        with driver.session() as session:
            return_list = []
            try:
                for record in session.run(stmt):
                    entity_record = record['properties']
                    return_list.append(entity_record)
                if len(return_list) == 0:
                    raise LookupError('Unable to find entity in statement:' + stmt)
                if len(return_list) > 1 and there_can_be_only_one == True:
                    raise LookupError('Error more than one entity found in statement:' + stmt)
                if there_can_be_only_one == True:
                    return return_list[0]
                return return_list                    
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except:
                print ('A general error occurred: ')
                for x in sys.exc_info():
                    print (x)
                raise

    @staticmethod
    def get_ancestors(driver, uuid):
        '''
        Get all ancestors by uuid
        '''
        with driver.session() as session:
            ancestor_ids = []
            ancestors = []
            try:
                matching_stmt = """MATCH (entity {{ {uuid_attr}: '{uuid}' }})<-[:ACTIVITY_OUTPUT]-(e1)<-[r:ACTIVITY_INPUT|:ACTIVITY_OUTPUT*]-(all_ancestors:Entity)-[:{metadata_rel}]->(all_ancestors_metadata) 
                """.format(uuid=uuid, uuid_attr=HubmapConst.UUID_ATTRIBUTE, metadata_rel=HubmapConst.HAS_METADATA_REL )
                return_clause = " RETURN apoc.coll.toSet(COLLECT(all_ancestors { .*, metadata: properties(all_ancestors_metadata) } )) AS all_ancestors "
                stmt = str(matching_stmt) + str(return_clause)

                print ("Here is the statement: " + stmt)
                for record in session.run(stmt, uuid=uuid):
                    if record.get('all_ancestors', None) != None:
                        ancestors = record['all_ancestors']
                return ancestors               
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except BaseException as be:
                pprint(be)
                raise be

    @staticmethod
    def get_descendants(driver, uuid):
        '''
        Get all descendants by uuid
        '''
        with driver.session() as session:
            descendants = []
            try:
                matching_stmt = """MATCH (entity {{ {uuid_attr}: '{uuid}' }})-[:ACTIVITY_INPUT]-(a:Activity)-[r:ACTIVITY_INPUT|:ACTIVITY_OUTPUT*]->(all_descendants:Entity)-[:{metadata_rel}]->(all_descendants_metadata) 
                """.format(uuid=uuid, uuid_attr=HubmapConst.UUID_ATTRIBUTE, metadata_rel=HubmapConst.HAS_METADATA_REL )
                return_clause = " RETURN apoc.coll.toSet(COLLECT(all_descendants { .*, metadata: properties(all_descendants_metadata) } )) AS all_descendants "
                stmt = str(matching_stmt) + str(return_clause)

                print ("Here is the statement: " + stmt)
                for record in session.run(stmt, uuid=uuid):
                    if record.get('all_descendants', None) != None:
                        descendants = record['all_descendants']
                return descendants               
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except BaseException as be:
                pprint(be)
                raise be
    
    @staticmethod
    def get_parents(driver, uuid):
        '''
        Get all parents by uuid
        '''
        with driver.session() as session:
            parents = []
            try:
                match_clause = "MATCH (entity {{ {uuid_attrib}: '{uuid}' }}) ".format(uuid_attrib=HubmapConst.UUID_ATTRIBUTE,uuid=uuid)
                stmt = Entity.get_generic_entity_stmt(match_clause, "")

                for record in session.run(stmt, uuid=uuid):
                    if record.get('immediate_ancestors', None) != None:
                        parents = record['immediate_ancestors']
                
                return parents               
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except BaseException as be:
                pprint(be)
                raise be
    
    @staticmethod
    def get_children(driver, uuid):
        '''
        Get all children by uuid
        '''
        with driver.session() as session:
            children = []
            try:
                match_clause = "MATCH (entity {{ {uuid_attrib}: '{uuid}' }}) ".format(uuid_attrib=HubmapConst.UUID_ATTRIBUTE,uuid=uuid)
                stmt = Entity.get_generic_entity_stmt(match_clause, "")

                for record in session.run(stmt, uuid=uuid):
                    if record.get('immediate_descendants', None) != None:
                        children = record['immediate_descendants']

                return children               
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                raise
            except BaseException as be:
                pprint(be)
                raise be
    
    @staticmethod
    def get_collection(driver, dataset_uuid):
        """ Get collection by dataset's uuid

        Args:
            driver: Neo4j connection driver
            dataset_uuid: uuid of dataset
        Returns:
            collection of the dataset
        """
        with driver.session() as session:
            try:
                stmt = f"""MATCH (dataset {{ {HubmapConst.UUID_ATTRIBUTE}: '{dataset_uuid}' }})
                -[:{HubmapConst.IN_COLLECTION_REL}]->(c:{HubmapConst.COLLECTION_NODE_NAME}) RETURN c"""

                for record in session.run(stmt):
                    if record.get('c', None) != None:
                        return record['c']
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

    @staticmethod
    def get_generic_entity_stmt(match_clause="", where_clause="", additional_return_clause ="",order_clause=""):

        # these OPTIONAL MATCH statements connect the entity to its immediate ancestors and descendants        
        default_optional_match_clause = """ OPTIONAL MATCH (entity)-[:HAS_METADATA]->(entity_metadata)
        OPTIONAL MATCH (anc_meta)<-[:{metadata_rel}]-(ancestor)-[r2]->(ancestor_act)-[r1]->(entity)
        OPTIONAL MATCH (entity)-[r3]->(descendant_act)-[r4]->(descendant)-[:{metadata_rel}]->(desc_meta) """.format(
            metadata_rel=HubmapConst.HAS_METADATA_REL)

        
        """This RETURN clause returns a set of entity data, all of the entity node properties (as entity_properties),
        the all the properties of the metadata node (as entity_metadata_properties), and the entity node's immediate ancestors and descendants.
        The ancestors and descendents are collated into a unique object array using the COLLECT statement
        followed by the apoc.coll.toSet function.  The apoc.coll.toSet takes an array of items and returns the
        unique set.  This is necessary because the COLLECT statement will make items repeat.
        """

        default_return_clause = """ RETURN CASE WHEN entity.{entitytype} is not null THEN entity.{entitytype} 
        WHEN entity.{activitytype} is not null THEN entity.{activitytype} ELSE entity.{agenttype} END AS datatype, 
        entity.{uuid_attrib} AS uuid, entity.{doi_attrib} AS doi, entity.{doi_display_attrib} AS display_doi, 
        entity.{hubmap_identifier_attrib} AS hubmap_identifier, properties(entity) AS entity_properties, properties(entity_metadata) AS entity_metadata_properties,
        apoc.coll.toSet(COLLECT(descendant {{ .*, metadata: properties(desc_meta) }} )) AS immediate_descendants,
        apoc.coll.toSet(COLLECT(ancestor {{ .*, metadata: properties(anc_meta) }} )) AS immediate_ancestors """.format(
            uuid_attrib=HubmapConst.UUID_ATTRIBUTE, doi_attrib=HubmapConst.DOI_ATTRIBUTE, doi_display_attrib=HubmapConst.DISPLAY_DOI_ATTRIBUTE,
                entitytype=HubmapConst.ENTITY_TYPE_ATTRIBUTE, activitytype=HubmapConst.ACTIVITY_TYPE_ATTRIBUTE, agenttype=HubmapConst.AGENT_TYPE_ATTRIBUTE,
                hubmap_identifier_attrib=HubmapConst.LAB_IDENTIFIER_ATTRIBUTE)
        
        stmt = match_clause + where_clause + default_optional_match_clause + default_return_clause + additional_return_clause + order_clause
        return stmt
    
def getTypeCode(type_code):
    typeCodeDict = {str(HubmapConst.DATASET_TYPE_CODE).lower() : HubmapConst.DATASET_TYPE_CODE,
                    str(HubmapConst.DATASTAGE_TYPE_CODE).lower() : HubmapConst.DATASTAGE_TYPE_CODE,
                    str(HubmapConst.SUBJECT_TYPE_CODE).lower() : HubmapConst.SUBJECT_TYPE_CODE,
                    str(HubmapConst.SOURCE_TYPE_CODE).lower() : HubmapConst.SOURCE_TYPE_CODE,
                    str(HubmapConst.SAMPLE_TYPE_CODE).lower() : HubmapConst.SAMPLE_TYPE_CODE,
                    str(HubmapConst.DONOR_TYPE_CODE).lower() : HubmapConst.DONOR_TYPE_CODE,
                    str(HubmapConst.FILE_TYPE_CODE).lower() : HubmapConst.FILE_TYPE_CODE,
                    str(HubmapConst.ORGAN_TYPE_CODE).lower() : HubmapConst.ORGAN_TYPE_CODE,
                    str(HubmapConst.SAMPLE_TYPE_CODE).lower() : HubmapConst.SAMPLE_TYPE_CODE,
                    str(HubmapConst.LAB_TYPE_CODE).lower() : HubmapConst.LAB_TYPE_CODE,
                    str(HubmapConst.DATASET_TYPE_CODE).lower() : HubmapConst.DATASET_TYPE_CODE,
                    str(HubmapConst.METADATA_TYPE_CODE).lower() : HubmapConst.METADATA_TYPE_CODE,
                    str(HubmapConst.COLLECTION_TYPE_CODE).lower() : HubmapConst.COLLECTION_TYPE_CODE,
                    
                    }
    return typeCodeDict[str(type_code).lower()]

if __name__ == "__main__":
    from hubmap_commons.test_helper import load_config
    #app_client_id, app_client_secret, uuid_webservice_url
    
    """
    webservice_url = 'http://localhost:5001/hmuuid'
    token = 'AgqmNezWyzbWp798lav9pe0yXnDdl11757kd7aopwDn0Me6rx2hqCMpwD41dbOE7vPJ9V646GeK0JViPkJMrbcky6Q'
    
    identifier_list = ['HBM252.GWGP.442','HBM685.VGCM.923','HBM524.SHKC.684','HBM989.NCVW.829','HBM226.KTZR.937','HBM434.HPXW.499']
    uuid_list = Entity.get_uuid_list(webservice_url, token, identifier_list)
    print('Given: ' + str(identifier_list))
    print('Returned: '+ str(uuid_list))

    identifier_list = ['TEST0060-LB-2-1','TEST0061','TEST0060-LB-1','TEST0060-LB']
    uuid_list = Entity.get_uuid_list(webservice_url, token, identifier_list)
    print('Given: ' + str(identifier_list))
    print('Returned: '+ str(uuid_list))
    
    identifier_list = ['b9e44b95fcf8550a3978d7d8e19df6b5', 'd4a9d88b24f460f30a50475b63d66cd5', '8c8d0d4e07c9b5cf9173f5519aca7dd3','HBM252.GWGP.442','HBM685.VGCM.923','HBM524.SHKC.684','TEST0060-LB-2-1','TEST0061','TEST0060-LB-1','TEST0060-LB']
    uuid_list = Entity.get_uuid_list(webservice_url, token, identifier_list)
    print('Given: ' + str(identifier_list))
    print('Returned: '+ str(uuid_list))
    """
    
          
    """
    confdata = appconfig.__dict__
    entity = Entity(confdata['APP_CLIENT_ID'],confdata['APP_CLIENT_SECRET'],confdata['UUID_WEBSERVICE_URL'])
    conn = Neo4jConnection(confdata['NEO4J_SERVER'], confdata['NEO4J_USERNAME'], confdata['NEO4J_PASSWORD'])
    driver = conn.get_driver()
    
    new_ent = Entity.get_entity(driver, '13ceb39891c4d06fc8fb5dbb5b0c16a0')
    print(new_ent)
    
    sample_uuid_list = Entity.get_entities_by_type(driver, 'Sample')
    print(sample_uuid_list)

    dataset_uuid_list = Entity.get_entities_by_type(driver, 'Dataset')
    print(dataset_uuid_list)
    
    type_list = ["Donor"]
    type_return_list = Entity.get_entities_by_types(driver, type_list)
    pprint.pprint(type_return_list)
    """
    
    """
    token = "AgV70V9a22mgr9N09WMmOW4b8eEzobyzmy1znPd6Jawme0VOzGTbCa999zM8bnb6x1OkEnEW14XGlYtlKxzPvu9k8G"
    type_code = "organ"
    editable_list = entity.get_editable_entities_by_type(driver, token, type_code)
    print("Editable list with type = " + type_code)
    print("Count: " + str(len(editable_list)))

    type_code = "ffpe_block"
    editable_list = entity.get_editable_entities_by_type(driver, token, type_code)
    print("Editable list with type = " + type_code)
    print("Count: " + str(len(editable_list)))

    editable_list = entity.get_editable_entities_by_type(driver, token)
    print("Editable list with type = None")
    print("Count: " + str(len(editable_list)))
    """
    
    file_path = '/home/chb69/git/ingest-ui/src/ingest-api/instance'
    filename = 'app.cfg'
    confdata = load_config(file_path, filename)
    conn = Neo4jConnection(confdata['NEO4J_SERVER'], confdata['NEO4J_USERNAME'], confdata['NEO4J_PASSWORD'])
    driver = conn.get_driver()
    
    collection_uuid = "cc82c72adc8bb032b5044725107d2c7a"
    collection_list = Entity.get_entities_and_children_by_relationship(driver, collection_uuid, HubmapConst.IN_COLLECTION_REL)
    print("Collections")
    print(collection_list)
        
    anc_dec_uuid = "f3faaae262c4370f6ab9157b4b500b21"
    ancestor_list = Entity.get_ancestors(driver, anc_dec_uuid)
    print("Ancestors")
    print(ancestor_list)
    print("count: " + str(len(ancestor_list)))

    descendant_list = Entity.get_descendants(driver, anc_dec_uuid)
    print("Descendants")
    print(descendant_list)
    print("count: " + str(len(descendant_list)))

    parent_list = Entity.get_parents(driver, anc_dec_uuid)
    print("Parents")
    print(parent_list)
    print("count: " + str(len(parent_list)))

    children_list = Entity.get_children(driver, anc_dec_uuid)
    print("Children")
    print(children_list)
    print("count: " + str(len(children_list)))
    
    


    """
    descendant_list = Entity.get_descendants(driver, anc_dec_uuid)
    print("Descendants")
    print(descendant_list)
    """
    
    """group_info = entity.get_group_by_name('HuBMAP-UFlorida')
    print(group_info)
    group_info = entity.get_group_by_name('University of Florida TMC')
    print(group_info)
    group_info = entity.get_group_by_name('UFL')
    print(group_info)"""
    
    """
    type_list = entity.get_entity_type_list(driver)
    print(type_list)
    
    entities_list = entity.get_entities_by_type(driver, 'daTaset')
    print(entities_list) 

    entities_count = entity.get_entity_count_by_type(driver, 'daTaset')
    print(entities_count) 
    
    
    entities_list = entity.get_entities_by_metadata_attribute(driver, HubmapConst.SPECIMEN_TYPE_ATTRIBUTE, 'ffpe_block')
    print(entities_list) 
    """
    #entities_list = entity.get_entities_and_children_by_relationship(driver, 'cc82c72adc8bb032b5044725107d2c7a', HubmapConst.IN_COLLECTION_REL) 
    #print(entities_list) 
   
    
    """token = "AggQN13V56BW10NMY9e18vPen0rEEeDW5aorWD39gBx1j48pwycJC31pG8WXdvYdevkD8vGJa210qxc1ke58WSBgD6"
    writeable_groups = entity.get_writeable_user_groups(token)
    print('Writeable groups:')
    print(writeable_groups)
    readonly_groups = entity.get_readonly_user_groups(token)
    print('Readonly groups:')
    print(readonly_groups)"""
    
    
    
    
    """conn = Neo4jConnection()
    driver = conn.get_driver()
    name = 'Test Dataset'
    description= 'This dataset is a test'
    parentCollection = '4470c8e8-3836-4986-9773-398912831'
    hasPHI = False
    labCreatedAt = '0ce5be9b-8b7f-47e9-a6d9-16a08df05f50'
    createdBy = '70a43e57-c4fd-4616-ad41-ca8c80d6d827'

    uuid_to_modify = 'b7094763d7d8581ce0cdcee2c59440c4'
    dr_x_uuid = '33a46e57-c55d-4617-ad41-ca8a30d6d844'
    metadata_uuid = '11ba247d1deac704fd1ee96c3619f527'
    register_datastage_activity = '177a1b530092b8bdd283c238e7d0166a'
    
    current_token = "AgeYjkWV9mr79xKqJNzX8ojdlGyvy9nvj9dw2eaqKjE0Km7eXzfVCPv6zYwmxmjoj1MGgByep61ewgIK3jjwkupPoa"

    entity = Entity()
    file_uuid = entity.get_entity(driver, uuid_to_modify)
    print (file_uuid)
    file_uuid = entity.get_entity(driver, metadata_uuid)
    print (file_uuid)
    file_uuid = entity.get_entity(driver, register_datastage_activity)
    print (file_uuid)
    
    stmt = Entity.get_entity_from_relationship_statement("cafd03e784d2fd091dd2bafc71db911d", "HAS_METADATA", "left")
    print(stmt)
    
    editable_entity = 'a3c44910213907cbc8d8d3fe53b63b53'
    status = entity.can_user_edit_entity(driver, current_token, editable_entity)
    if status == True:
        print ("I can edit " + editable_entity) 
    else:
        print ("I cannot edit " + editable_entity) 
    
    e_list = entity.get_editable_entities_by_type(driver, current_token, 'Donor')
    print(e_list)

    e_list = entity.get_editable_entities_by_type(driver, current_token)
    print(e_list)

    entity = Entity()
    #edit_record = {'uuid' : 'b8f5fcbe0b891ac0361b361b722de4b4', 'description' :'new description'}
    #entity.edit_entity(driver, current_token, 'b8f5fcbe0b891ac0361b361b722de4b4', edit_record)
    metadata_obj = Entity.get_entity_metadata(driver, '55f3673543e4843e04f7c19161b47104')
    print(metadata_obj)
    
    group_list = entity.get_user_groups(current_token)
    print(group_list)

    
    
    conn.close()"""
