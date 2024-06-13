from hubmap_commons import string_helper
from flask import Response

import flask
import base64
import requests
import datetime
import functools
import threading
import json
import os
import re
from hubmap_commons.exceptions import HTTPException
from hubmap_commons import file_helper
from hubmap_commons import hubmap_const
from hubmap_commons import exceptions

TOKEN_EXPIRATION = 900 #15 minutes
#GLOBUS_NEXUS_GROUP_SCOPE = 'urn:globus:auth:scope:nexus.api.globus.org:groups'
GLOBUS_GROUPS_API_SCOPE_ALL = 'urn:globus:auth:scope:groups.api.globus.org:all'
GLOBUS_GROUPS_API_SCOPE_PART = 'urn:globus:auth:scope:groups.api.globus.org:view_my_groups_and_memberships'
ALL_GROUP_SCOPES = [GLOBUS_GROUPS_API_SCOPE_ALL, GLOBUS_GROUPS_API_SCOPE_PART]

#this is only used by the secured decorator below as it needs access 
#to client information.  It is initialized the first time an AuthHelper is
#created.
helperInstance = None

def secured(func=None, groups=None, scopes=None, has_read=False, has_write=False):
    def secured_decorator(func):
        @functools.wraps(func)
        def secured_inner(*args, **kwargs):
            if helperInstance is None:
                return Response("Error checking security credentials.  A valid auth worker not found.  Make sure you create a hm_auth.AuthHelper during service initialization", 500)            
            hasGroups = groups is not None or has_read or has_write

            #make sure we have a valid, active auth token
            user_token = helperInstance.getUserTokenFromRequest(flask.request, hasGroups)
            if isinstance(user_token, Response):
                return user_token
            
            userInfo = helperInstance.getUserInfo(user_token, hasGroups)
            if isinstance(userInfo, Response):
                return userInfo
            
            sys_acct = False
            if "is_system_account" in userInfo: sys_acct = userInfo['is_system_account'] 
            
            #check that auth is in required scope
            if hasGroups and sys_acct is False:
                in_scope = False
                for scope in ALL_GROUP_SCOPES:
                    if scope in userInfo['hmscopes']:
                        in_scope = True
                        break
                if not in_scope:
                    msg = "Not in one of user scopes " + ",".join(ALL_GROUP_SCOPES) + " which is required for access to user groups"
                    return Response(msg, 403)
            
            if has_read == True:
                check_read = helperInstance.has_read_privs(user_token)
                if isinstance(check_read, Response):
                    return check_read
                if check_read == False:
                    msg = "User does not have read privileges, must be member of a data-provider group or the default data-read group"
                    return Response(msg, 403)
            
            if has_write == True:
                check_write = helperInstance.has_write_privs(user_token)
                if isinstance(check_write, Response):
                    return(check_write)
                if check_write == False:
                    msg = "User does not have required write privileges, must be a member of any data-provider group or the data-admin group"
                    return Response(msg, 403)
    
            #check for group access
            if groups is not None:
                if isinstance(groups, list): tGroups = groups
                else: tGroups = [groups]
                for group in tGroups:
                    gid = helperInstance.groupNameToId(group)
                    if gid is None:
                        return Response("Group " + group + " not found.", 500)
                    if not gid['uuid'] in userInfo['hmgroupids']:
                        return Response('User is not a member of group ' + group, 403)

            return (func(*args, **kwargs))
        return secured_inner

    if func is not None:
        return secured_decorator(func)
    return secured_decorator

def isAuthorized(conn, token, entity, entity_uuid):
    try:
        driver = conn.get_driver()
        return entity.can_user_edit_entity(driver, token, entity_uuid)
    except:
        return False

#A class to help with Globus authentication and authorization
#this class is meant to be a singleton and should be accessed only
#via static create and instance methodds.

class AuthHelper:
    applicationClientId = None
    applicationClientSecret = None

    @staticmethod
    def configured_instance(clientId, clientSecret):
        if not helperInstance is None:
            if clientId == helperInstance.applicationClientId and clientSecret == helperInstance.applicationClientSecret:
                return(helperInstance)
            else:
                raise Exception("AuthHelper instance exists already with a different client id/secret pair")
        else:
            return(AuthHelper.create(clientId, clientSecret))

    @staticmethod
    def create(clientId, clientSecret):
        if helperInstance is not None:
            raise Exception("An instance of AuthHelper exists already.  Use the AuthHelper.instance method to retrieve it.")
        return AuthHelper(clientId, clientSecret)
    
    @staticmethod
    def instance():
        if helperInstance is None:
            raise Exception("An instance of AuthHelper does not yet exist.  Use AuthHelper.create(...) to create a new instance")
        return helperInstance
    
    @staticmethod
    def isInitialized():
        return(helperInstance is not None)
    
    @staticmethod
    def getHuBMAPGroupInfo():
        return(AuthCache.getHMGroups())
    
    @staticmethod
    def getHMGroupsById():
        return(AuthCache.getHMGroupsById())

    @staticmethod
    def getGroupDisplayName(group_uuid):
        grps_by_id = AuthCache.getHMGroupsById()
        if not group_uuid in grps_by_id: return None
        return grps_by_id[group_uuid]['displayname']

    def __init__(self, clientId, clientSecret):
        global helperInstance
        baseGroupFilename = '-globus-groups.json'

        if helperInstance is not None:
            raise Exception("An instance of singleton AuthHelper exists already.  Use AuthHelper.instance() to retrieve it")
        
        if clientId is None or clientSecret is None or string_helper.isBlank(clientId) or string_helper.isBlank(clientSecret):
            raise Exception("Globus client id and secret are required in AuthHelper")
        
        self.applicationClientId = clientId.strip()
        self.applicationClientSecret = clientSecret
        group_filename_prefix = self.applicationClientId[0:8]
        self.groupJsonFilename = file_helper.ensureTrailingSlash(os.path.dirname(os.path.realpath(__file__))) + group_filename_prefix + baseGroupFilename
        
        with open(self.groupJsonFilename) as jsFile:
            groups = json.load(jsFile)
            AuthCache.setGlobusGroups(groups)

        #from the group definition file find the group of type data-admin
        all_groups = AuthCache.getHMGroups()
        self.data_admin_group_uuid = None
        self.data_read_group_uuid = None
        self.protected_data_group_uuid = None
        for grp_name in all_groups.keys():
            grp = all_groups[grp_name]
            if 'group_type' in grp:
                if grp['group_type'] == 'data-admin':
                    self.data_admin_group_uuid = grp['uuid']
                elif grp['group_type'] == 'data-read':
                    self.data_read_group_uuid = grp['uuid']
                elif grp['group_type'] == 'protected-data':
                    self.protected_data_group_uuid = grp['uuid']

        AuthCache.setProcessSecret(re.sub(r'[^a-zA-Z0-9]', '', clientSecret))
        if helperInstance is None:
            helperInstance = self
            
        AuthCache.setClientId(clientId)



    def get_globus_groups_info(self):
        groups = AuthCache.globusGroups

        groups_by_id = {}
        groups_by_name = {}
        groups_by_tmc_prefix = {}
    
        required_keys = ['name', 'uuid', 'generateuuid', 'displayname', 'data_provider']
        non_empty_keys = ['name', 'displayname']
        boolean_keys = ['data_provider']
    
        for group_key in groups.keys():
            group = groups[group_key]
            # A bit data integrity check
            for key in required_keys:
                if key not in group:
                    msg = f'Key "{key}" is required for each object in the globus groups json file'
                    raise KeyError(msg)
    
            for key in non_empty_keys:
                if string_helper.isBlank(group[key]):
                    msg = f'The value of key "{key}" can not be empty string in each object in the globus groups json file'
                    raise ValueError(msg)
    
            for key in boolean_keys:
                if not isinstance(group[key], bool):
                    msg = f'The value of key "{key}" must be a boolean in each object in the globus groups json file'
                    raise ValueError(msg)
    
            # By now all the checks passed, we are good for the business
            group_obj = {
                'name' : group['name'].lower().strip(),
                'uuid' : group['uuid'].lower().strip(),
                'displayname' : group['displayname'],
                'generateuuid': group['generateuuid'],
                'data_provider': group['data_provider']
            }

            # Key "description" is optional
            if 'description' in group:
                group_obj['description'] = group['description']

            # Key "tmc_prefix" is optional
            if 'tmc_prefix' in group:
                group_obj['tmc_prefix'] = group['tmc_prefix']
    
                group_info = {}
                group_info['uuid'] = group['uuid'].lower().strip()
                group_info['displayname'] = group['displayname']
                group_info['tmc_prefix'] = group['tmc_prefix']
    
                groups_by_tmc_prefix[group['tmc_prefix'].upper().strip()] = group_info
    
            groups_by_name[group['name'].lower().strip()] = group_obj
            groups_by_id[group['uuid']] = group_obj
    
        # Wrap the final data
        globus_groups = {
            'by_id': groups_by_id,
            'by_name': groups_by_name,
            'by_tmc_prefix': groups_by_tmc_prefix
        }
        return globus_groups

            
    #method to check if an auth token has write privileges
    #for a given group
    #
    # inputs
    #      Globus groups_token: a Globus Groups API auth token, with Groups API scope
    #       group_uuid: the group_uuid to check to see if the user has write privs for
    #
    # outputs
    #     True if the token is authorized for the group
    #
    #   otherwise an HTTPException is thrown with the following status values
    #
    #     403 - user is not authorized to write for the group
    #     401 - invalid token
    #     400 - invalid group uuid provided
    #
    #   a standard Exception will be raise if an unexpected error occurs
    #     500 - any unexpected exception
    #
    def check_write_privs(self, groups_token, group_uuid):
        user_info = self.getUserInfo(groups_token, getGroups=True)
        if isinstance(user_info, Response):
            raise HTTPException(user_info.text, user_info.status_code)
        
        groups_by_id = self.getHMGroupsById()
        if not group_uuid in groups_by_id:
            raise HTTPException(f"{group_uuid} is not a valid group uuid", 400)
        grp = groups_by_id[group_uuid]
        if not 'data_provider' in grp or not grp['data_provider']:
            raise HTTPException(f"grop with uuid {group_uuid} is not a valid data provider group", 400)
        
        if 'hmgroupids' in user_info:
            if not self.data_admin_group_uuid is None and self.data_admin_group_uuid in user_info['hmgroupids']:
                return True
            elif group_uuid not in user_info['hmgroupids']:
                raise HTTPException("User not authorized for group.", 403)
            else:
                return True
        else:
            raise HTTPException("User is not authorized, no group membership", 403)
    
    #method to check to see if a user has any write privileges at all
    #user (via token) must have membership in any group with a "data_provider" == true attribute or
    #a member of a group with type data-admin
    def has_write_privs(self, groups_token):
        user_info = self.getUserInfo(groups_token, getGroups=True)
        if isinstance(user_info, Response):
            return user_info 

        #if the user is a member of the data-admin group, they have write privs        
        if not self.data_admin_group_uuid is None and self.data_admin_group_uuid in user_info['hmgroupids']:
            return True
        
        #loop through all groups that a user is a member of and if any of these groups has "data_provider" set to true, the user has write privs
        groups_by_id = self.getHMGroupsById()
        for grp_id in user_info['hmgroupids']:
            if grp_id in groups_by_id and 'data_provider' in groups_by_id[grp_id] and groups_by_id[grp_id]['data_provider'] == True:
                return True
            
        return False
    
    #method to check to see if a user is a member of a group with type data-admin
    def has_data_admin_privs(self, groups_token):
        user_info = self.getUserInfo(groups_token, getGroups=True)
        if isinstance(user_info, Response):
            return user_info 
        
        if not self.data_admin_group_uuid is None and self.data_admin_group_uuid in user_info['hmgroupids']:
            return True
            
        return False

    #method, give a user's token, will return a list of groups that the user is a member of with write
    #privs.  Any group that the user is a member of with a "data_provider" == true attribute is added
    #to the return list.  If the user isn't a member of any write/data_provider groups an emptly list
    #is returned
    #
    #A Flask Response object is returned in case of an error containing the correct response code and message
    #that can be returned directly from a WS endpoint
    def get_user_write_groups(self, groups_token):
        user_info = self.getUserInfo(groups_token, getGroups=True)
        if isinstance(user_info, Response):
            return user_info 

        write_groups = []
        #loop through all groups that a user is a member of and if any of these groups has "data_provider"
        #add it to the list of returned groups.
        groups_by_id = self.getHMGroupsById()
        for grp_id in user_info['hmgroupids']:
            if grp_id in groups_by_id and 'data_provider' in groups_by_id[grp_id] and groups_by_id[grp_id]['data_provider'] == True:
                write_groups.append(groups_by_id[grp_id])
            
        return write_groups

    #check to see if a user has read privileges
    #the user has read privileges if they are a member of the
    #default read group or if they have write privileges at all per the above has_write_privs method
    def has_read_privs(self, groups_token):
        user_info = self.getUserInfo(groups_token, getGroups = True)
        if isinstance(user_info, Response):
            return user_info
        if not self.data_read_group_uuid is None and self.data_read_group_uuid in user_info['hmgroupids']:
            return True
        return self.has_write_privs(groups_token)

    def get_default_read_group_uuid(self):
        return self.data_read_group_uuid
    
    def getProcessSecret(self):
        return AuthCache.procSecret

    def getAuthorizationTokens(self, requestHeaders):
        hasMauth=False
        hasAuth=False
        if 'Mauthorization' in requestHeaders: hasMauth=True
        if 'Authorization' in requestHeaders: hasAuth=True
        
        if hasMauth:
            mauthHeader = requestHeaders['Mauthorization']
            if string_helper.isBlank(mauthHeader):
                return Response("Empty Mauthorization header", 401)
            mauthHeader = mauthHeader.strip()
            """if len(mauthHeader) <= 8:
                return Response("Invalid Mauthorization header", 401)"""
            jsonTokens = mauthHeader
            if mauthHeader.upper().startswith("MBEARER"):
                jsonTokens = mauthHeader[7:].strip()
            try:
                tokens = json.loads(jsonTokens)
            except Exception as e:
                print("ERROR!: " + str(e))
                return Response("Error decoding json included in Mauthorization header", 401)    
            return tokens
        
        elif hasAuth:
            authHeader = requestHeaders['Authorization']
            if string_helper.isBlank(authHeader):
                return Response("Empty Authorization header", 401)
            authHeader = authHeader.strip()
            if len(authHeader) <= 7:
                return Response("Invalid Authorization header", 401)
            if not authHeader.upper().startswith("BEARER"):
                return Response("Bearer Authorization required", 401)
            token = authHeader[6:].strip()
            if string_helper.isBlank(token):
                return Response('Invalid Bearer Authorization', 401)
            return(token)
        else:
            return Response('No Authorization header', 401)

    @staticmethod
    def parseAuthorizationTokens(requestHeaders):
        hasMauth=False
        hasAuth=False
        if 'Mauthorization' in requestHeaders: hasMauth=True
        if 'Authorization' in requestHeaders: hasAuth=True
        
        if hasMauth:
            mauthHeader = requestHeaders['Mauthorization']
            if string_helper.isBlank(mauthHeader):
                raise ValueError("Empty Mauthorization header")
            mauthHeader = mauthHeader.strip()
            """if len(mauthHeader) <= 8:
                return Response("Invalid Mauthorization header", 401)"""
            jsonTokens = mauthHeader
            if mauthHeader.upper().startswith("MBEARER"):
                jsonTokens = mauthHeader[7:].strip()
            try:
                tokens = json.loads(jsonTokens)
            except Exception as e:
                raise ValueError("Error decoding json included in Mauthorization header")    
            return tokens
        
        elif hasAuth:
            authHeader = requestHeaders['Authorization']
            if string_helper.isBlank(authHeader):
                raise ValueError("Empty Authorization header")
            authHeader = authHeader.strip()
            if len(authHeader) <= 7:
                raise ValueError("Invalid Authorization header")
            if not authHeader.upper().startswith("BEARER"):
                raise ValueError("Bearer Authorization required")
            token = authHeader[6:].strip()
            if string_helper.isBlank(token):
                raise ValueError('Invalid Bearer Authorization')
            return(token)
        else:
            raise ValueError('No Authorization header')
    
    def getUserInfoUsingRequest(self, httpReq, getGroups = False):
        token = self.getUserTokenFromRequest(httpReq, getGroups)
        if isinstance(token, Response):
            return token;

        return self.getUserInfo(token, getGroups)
    
    def getUserTokenFromRequest(self, httpReq, getGroups):
        tokenResp = self.getAuthorizationTokens(httpReq.headers)
        if isinstance(tokenResp, Response):
            return tokenResp;

        if isinstance(tokenResp, dict):
            if getGroups and not ('groups_token' in tokenResp):
                return Response("Groups API scoped token required to get group information.")
            elif 'groups_token' in tokenResp:
                return tokenResp['groups_token']
            elif 'auth_token' in tokenResp:
                return tokenResp['auth_token']
            elif 'transfer_token' in tokenResp:
                return tokenResp['transfer_token']
            else:
                return Response("A valid token was not found in the MAuthorization header") 
        else:
            return tokenResp        
    
    def getUserInfo(self, token, getGroups = False):
        userInfo = AuthCache.getUserInfo(self.getApplicationKey(), token, getGroups)
        
        if isinstance(userInfo, Response):
            return userInfo
                
        if not isinstance(userInfo, dict) or not 'active' in userInfo or userInfo['active'] is None:
            return Response("Nonactive or invalid auth token", 401)
        
        return userInfo
    
    def groupNameToId(self, name):
        tName = name.lower().strip()
        groups = AuthCache.getHMGroups()
        if tName in groups:
            return groups[tName]
        else:
            return None
            
    def getApplicationKey(self):
        return base64.b64encode(bytes(self.applicationClientId + ':' + self.applicationClientSecret, 'utf-8')).decode('utf-8')
            


    #get the highest level access level given the token embedded in the HTTP request
    #if a valid token is found in the HTTP request the full user_info dictionary is returned with "data_access_level" attribute added
    #if public access and no token just {"data_access_level":"public"} dictionary is returned
    #returns "data_access_level : public" (HubmapConst.ACCESS_LEVEL_PUBLIC) for valid token, but no HuBMAP Read access or no token
    #returns "data_access_level : protected" (HubmapConst.ACCESS_LEVEL_PROTECTED) for valid token with membership in the HuBMAP-Protected-Data group
    #returns "data_access_level : consortium" (HuBMAPConst.ACCESS_LEVEL_CONSORTIUM) for valid token with membership in the HuBMAP-Read group, but not the HuBMAP-Protected-Data group
    #raises an HTTPException with a 401 if any auth issues are found
    def getUserDataAccessLevel(self, request):
        if not 'Authorization' in request.headers and not 'Mauthorization' in request.headers:
            user_info = {}
            user_info['data_access_level'] = hubmap_const.HubmapConst.ACCESS_LEVEL_PUBLIC
            return user_info

        tokenResp = self.getAuthorizationTokens(request.headers)
        if isinstance(tokenResp, Response):
            raise exceptions.HTTPException("Invalid Authorization header", 401)

        user_info = None
        if isinstance(tokenResp, dict):
            if 'groups_token' in tokenResp:
                user_info = self.getUserInfo(tokenResp['groups_token'], True)
            elif 'auth_token' in tokenResp:
                user_info = self.getUserInfo(tokenResp['auth_token'], False) 
            elif 'transfer_token' in tokenResp:
                user_info = self.getUserInfo(tokenResp['transfer_token'], False)
            else:
                raise exceptions.HTTPException("No valid tokens found in MAuthorization Header", 401) 
        else:
            user_info = self.getUserInfo(tokenResp, True)
            if isinstance(user_info, Response):
                user_info = self.getUserInfo(tokenResp, False)
        
        if user_info is None or isinstance(user_info, Response):
            raise exceptions.HTTPException("No valid authorization token found.", 401)
        
        if 'hmgroupids' in user_info:
            protected_group_id = self.protected_data_group_uuid
            read_id = self.data_read_group_uuid
            ids = user_info['hmgroupids']
            if protected_group_id in ids:
                user_info['data_access_level'] = hubmap_const.HubmapConst.ACCESS_LEVEL_PROTECTED 
            elif read_id in ids:
                user_info['data_access_level'] = hubmap_const.HubmapConst.ACCESS_LEVEL_CONSORTIUM
            else:
                user_info['data_access_level'] = hubmap_const.HubmapConst.ACCESS_LEVEL_PUBLIC
        else:
            user_info['data_access_level'] = hubmap_const.HubmapConst.ACCESS_LEVEL_PUBLIC
            
        return user_info

    #checks to see if the user identified by the Groups API scoped token in the request
    #is allowed to write to either specified by the group_uuid field or barring
    #a specific group_uuid checks to see if the user is a member of one (and only one)
    #group that is allowed to write
    #
    #If an auth error occurs a HTTPException is thrown
    #which can be easily handled to return a good error Response
    #for a web service method
    def get_write_group_uuid(self, request_or_token, group_uuid = None):
        if isinstance(request_or_token, str): 
            user_info = self.getUserInfo(request_or_token, getGroups=True)
        else:
            user_info = self.getUserInfoUsingRequest(request_or_token, getGroups=True)

        if isinstance(user_info, Response):
            raise HTTPException("Error while getting user information from token. " + user_info.get_data(as_text=True), user_info.status_code)
        
        if len(AuthCache.groupsById) == 0:
            AuthCache.getHMGroups()
        groups_by_id = AuthCache.groupsById
        
        if not group_uuid is None:
            if group_uuid in groups_by_id:
                if not 'data_provider' in groups_by_id[group_uuid] or not groups_by_id[group_uuid]['data_provider']:
                    raise HTTPException(f"Group {groups_by_id[group_uuid]['displayname']} is not a valid group for submitting data.", 403)
                #user must be a member of the group or a member of the data admin group
                elif not (group_uuid in user_info['hmgroupids'] or (not self.data_admin_group_uuid is None and self.data_admin_group_uuid in user_info['hmgroupids'])):
                    raise HTTPException(f"User is not a member of the group {groups_by_id[group_uuid]['displayname']}", 403)
                else:
                    return group_uuid
            else:
                raise HTTPException("Invalid group_uuid", 400) 
        else:
            count = 0
            found_group_uuid = None
            for grp_id in groups_by_id.keys():
                grp_info = groups_by_id[grp_id]
                if grp_id in user_info['hmgroupids'] and 'data_provider' in grp_info and grp_info['data_provider'] == True:
                    count = count + 1
                    found_group_uuid = grp_id
            if count == 0:
                if not self.data_admin_group_uuid is None and self.data_admin_group_uuid in user_info['hmgroupids']:
                    raise HTTPException("User is not a member of any groups that can provide data, but is a member of the data admin group. Please specify which group in the group_uuid field")
                else:
                    raise HTTPException("User is not a member of any groups that can provide data.", 403)
            elif count > 1:
                raise HTTPException("The user is a member of multiple groups that can provide data.  Please specify which group in the group_uuid field", 400)
            else:
                return found_group_uuid
                    
    def get_user_groups_deprecated(self, token):
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.entity_config['APP_CLIENT_ID'], self.entity_config['APP_CLIENT_SECRET'])
        else:
            authcache = AuthHelper.instance()
        userinfo = authcache.getUserInfo(token, True)
    
        if type(userinfo) == Response and userinfo.status_code == 401:
            raise HTTPException('token is invalid.', 401)
    
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

    def get_user_roles_deprecated(self, token):
        authcache = None
        if AuthHelper.isInitialized() == False:
            authcache = AuthHelper.create(
                self.entity_config['APP_CLIENT_ID'], self.entity_config['APP_CLIENT_SECRET'])
        else:
            authcache = AuthHelper.instance()
        userinfo = authcache.getUserInfo(token, True)

        if type(userinfo) == Response and userinfo.status_code == 401:
            raise HTTPException('token is invalid.', 401)

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


def identifyGroups(groups):
    groupIdByName = {}
    for group in groups:
        if 'name' in group and 'uuid' in group and 'generateuuid' in group and 'displayname' in group and not string_helper.isBlank(
                group['name']) and not string_helper.isBlank(group['uuid']) and not string_helper.isBlank(
            group['displayname']):
            group_obj = {'name': group['name'].lower().strip(), 'uuid': group['uuid'].lower().strip(),
                         'displayname': group['displayname'], 'generateuuid': group['generateuuid']}
            if 'tmc_prefix' in group:
                group_obj['tmc_prefix'] = group['tmc_prefix']
            if 'description' in group:
                group_obj['description'] = group['description']
            if 'data_provider' in group:
                group_obj['data_provider'] = group['data_provider']
            if 'shortname' in group:
                group_obj['shortname'] = group['shortname']
            if 'group_type' in group:
                group_obj['group_type'] = group['group_type']

            groupIdByName[group['name'].lower().strip()] = group_obj
            AuthCache.groupsById[group['uuid']] = group_obj
    return groupIdByName

class AuthCache:
    cache = {}
    userLock = threading.RLock()
    groupLock = threading.RLock()
    groupIdByName = None
    roleIdByName = None
    groupsById = {}
    rolesById = {}
    groupLastRefreshed = None
    globusGroups = None
    roleJsonFilename = file_helper.ensureTrailingSlash(os.path.dirname(os.path.realpath(__file__))) + 'hubmap-globus-roles.json'
    procSecret = None
    client_id = None
    admin_groups = None
    processUserFilename = file_helper.ensureTrailingSlash(os.path.dirname(os.path.realpath(__file__))) + '-process-user.json'
    processUser = None
    
    @staticmethod
    def setClientId(cliId):
        AuthCache.client_id = cliId
    
    @staticmethod
    def setProcessSecret(secret):
        if AuthCache.procSecret is None:
            AuthCache.procSecret = secret

    @staticmethod
    def setGlobusGroups(globusJson):
        AuthCache.globusGroups = identifyGroups(globusJson)

    @staticmethod
    def getGlobusGroups():
        return AuthCache.globusGroups

    @staticmethod
    def getHMGroups():
        if AuthCache.globusGroups is not None:
            return AuthCache.globusGroups
        else:
            with open(AuthCache.groupJsonFilename) as jsFile:
                groups = json.load(jsFile)
                return identifyGroups(groups)

    @staticmethod
    def getHMGroupsById():
        if len(AuthCache.groupsById) == 0:
            AuthCache.getHMGroups()
        return(AuthCache.groupsById)
    
    @staticmethod
    def getHMRoles():
        with AuthCache.groupLock:
            now = datetime.datetime.now()
            diff = None
            if AuthCache.groupLastRefreshed is not None:
                diff = now - AuthCache.groupLastRefreshed
            if diff is None or diff.days > 0 or diff.seconds > TOKEN_EXPIRATION:
                roleIdByName = {}                    
                #rolesById = {}                    
                with open(AuthCache.roleJsonFilename) as jsFile:
                    roles = json.load(jsFile)
                    for role in roles:
                        if 'name' in role and 'uuid' in role and 'displayname' in role and not string_helper.isBlank(role['name']) and not string_helper.isBlank(role['uuid']) and not string_helper.isBlank(role['displayname']):
                            role_obj = {'name' : role['name'].lower().strip(), 'uuid' : role['uuid'].lower().strip(),
                                         'displayname' : role['displayname']}
                            roleIdByName[role['name'].lower().strip()] = role_obj
                            AuthCache.rolesById[role['uuid']] = role_obj
            return roleIdByName

    @staticmethod
    def getUserWithGroups(appKey, token):
        return AuthCache.getUserInfo(appKey, token, getGroups=True)
    
    @staticmethod
    def getUserInfo(appKey, token, getGroups=False):
        with AuthCache.userLock:
            if token in AuthCache.cache:
                now = datetime.datetime.now()
                diff = now - AuthCache.cache[token]['timestamp']
                if diff.days > 0 or diff.seconds > TOKEN_EXPIRATION:  #15 minutes
                    AuthCache.cache[token] = AuthCache.__authRecord(appKey, token, getGroups)
            else:
                AuthCache.cache[token] = AuthCache.__authRecord(appKey, token, getGroups)
            
            if isinstance(AuthCache.cache[token]['info'], Response):
                return AuthCache.cache[token]['info']
            
            if getGroups and "hmgroupids" not in AuthCache.cache[token]['info']:
                AuthCache.cache[token] = AuthCache.__authRecord(appKey, token, getGroups)

            return AuthCache.cache[token]['info']

    @staticmethod
    def __authRecord(appKey, token, getGroups=False):
        rVal = {}
        now = datetime.datetime.now()
        info = AuthCache.__userInfo(appKey, token, getGroups)
        rVal['info'] = info
        rVal['timestamp'] = now
        
        if isinstance(rVal['info'], Response):        
            rVal['valid'] = False
        elif not 'active' in info or info['active'] is None:
            rVal['valid'] = False
        else:
            rVal['valid'] = info['active']

        if rVal['valid'] and 'scope' in info and not string_helper.isBlank(info['scope']):
            info['hmscopes'] = info['scope'].lower().strip().split()
        
        return rVal

    @staticmethod
    def __get_admin_groups():
        if AuthCache.admin_groups is None:
            admin_grps = []
            all_groups = AuthCache.getHMGroups()
            #add all data provider groups plus any group marked as "group_type" data-read or data-admin
            for grp_name in all_groups.keys():
                grp = all_groups[grp_name]
                if ('data_provider' in grp and grp['data_provider']) or ('group_type' in grp and (grp['group_type'] == 'data-read' or grp['group_type'] == 'data-admin')):
                    admin_grps.append(grp)
            AuthCache.admin_groups = admin_grps
        return AuthCache.admin_groups

    #try to get user's group info via both deprecated Nexus token and new Groups API token
    #@staticmethod
    #def __userGroupsComb(token):
    #    groups = AuthCache.__userGroupsNexus(token)
    #    if isinstance(groups, Response):
    #        #if the nexus call failed try the Groups API
    #        groups = AuthCache.__get_user_groups_via_groups_api(token)
    #    return groups


    #@staticmethod
    #def __userGroupsNexus(token):
    #    if token == AuthCache.procSecret:
    #        return AuthCache.__get_admin_groups()

    #    getHeaders = {
    #        'Content-Type': 'application/json',
    #        'Accept': 'application/json',
    #        'Authorization': 'Bearer ' + token
    #    }
    #    url='https://nexus.api.globusonline.org/groups?fields=id,name,description,group_type,has_subgroups,identity_set_properties&for_all_identities=false&include_identaaaaay_set_properties=false&my_statuses=active'
    #    response = requests.get(url, headers=getHeaders)
    #    if response.status_code != 200:
    #        return Response("Unable to get user groups\n"+response.text, 500)
    #    try:
    #        jsonResp = response.json()
    #        ids = []
    #        for value in jsonResp:
    #            if 'id' in value:
    #                ids.append(value['id'].lower().strip())
    #        return ids
    #    except Exception as e:
    #        return Response('Unable to parse json response while gathering user groups\n' + str(e), 500)

    @staticmethod
    def __get_user_groups_via_groups_api(token):
        if token == AuthCache.procSecret:
            return AuthCache.__get_admin_groups()
        #GET /v2/groups/my_groups
        url = 'https://groups.api.globus.org/v2/groups/my_groups'
        headers = { 'Authorization' : 'Bearer ' + token }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return Response("Unable to get user groups\n"+response.text, 500)
        try:
            jsonResp = response.json()
#            print(json.dumps(jsonResp, indent=4))
            ids = []
#            if 'my_memberships' in jsonResp and isinstance(jsonResp['my_memberships'], list):
            for grp in jsonResp:
                if 'id' in grp:
                    ids.append(grp['id'])
                                
            return ids
        except Exception as e:
            return Response("unable to get groups from Groups api while gathering user groups\n" + str(e), 500)

    @staticmethod
    def __userInfo(applicationKey, authToken, getGroups=False):
        if authToken == AuthCache.procSecret:
            if AuthCache.processUser is None:
                filename = re.sub('-process-user.json$', AuthCache.client_id[0:8] + '-process-user.json', AuthCache.processUserFilename)
                with open(filename) as jsFile:
                    AuthCache.processUser = json.load(jsFile)
            return AuthCache.processUser

        postHeaders = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic ' + applicationKey
            }
        tdata = 'token=' + authToken
        url='https://auth.globus.org/v2/oauth2/token/introspect'
        response = requests.post(url, headers=postHeaders, data=tdata)
        if response.status_code != 200:
            return Response("Unable to introspect user from token", 500)
        try:
            jsonResp = response.json()
            if 'active' in jsonResp and jsonResp['active']:
                if getGroups:
                    if len(AuthCache.groupsById) == 0:
                        AuthCache.getHMGroups()
                    if len(AuthCache.rolesById) == 0:
                        AuthCache.getHMRoles()
                    #groups = AuthCache.__userGroupsComb(authToken)
                    groups = AuthCache.__get_user_groups_via_groups_api(authToken)

                    if isinstance(groups, Response):
                        return groups
                    grp_list = []
                    role_list = []
                    for group_uuid in groups:
                        #if group_uuid in AuthCache.groupsById:
                        #    grp_list.append(group_uuid)
                        #elif group_uuid in AuthCache.rolesById:
                        #    role_list.append(group_uuid)
                        if not group_uuid in grp_list:
                            grp_list.append(group_uuid)
                    jsonResp['hmgroupids'] = grp_list
                    jsonResp['group_membership_ids'] = grp_list
                    jsonResp['hmroleids'] = role_list
                return jsonResp
            else:
                return Response("Non-active login", 401)
        except Exception as e:
            print("ERROR!: " + str(e))            
            return Response("Unable to parse json response on user introspect", 500)
        if not 'active' in jsonResp or not jsonResp['active']:
            return Response("Login session not active.", 401)

if __name__ == "__main__":
    #group_list = AuthCache.getHMGroups()
    #print(group_list)
    #print(AuthCache.groupsById)
    clientId = ''
    clientSecret = ''
    token = ''
    helper = AuthHelper.configured_instance(clientId, clientSecret)
    print(helper.get_user_write_groups(token))
    
