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
from hubmap_commons import file_helper
from hubmap_commons import hubmap_const
from hubmap_commons import exceptions

TOKEN_EXPIRATION = 900 #15 minutes
GLOBUS_GROUP_SCOPE = 'urn:globus:auth:scope:nexus.api.globus.org:groups'

#this is only used by the secured decorator below as it needs access 
#to client information.  It is initialized the first time an AuthHelper is
#created.
helperInstance = None

def secured(func=None, groups=None, scopes=None):
    def secured_decorator(func):
        @functools.wraps(func)
        def secured_inner(*args, **kwargs):
            if helperInstance is None:
                return Response("Error checking security credentials.  A valid auth worker not found.  Make sure you create a hm_auth.AuthHelper during service initialization", 500)            
            hasGroups = groups is not None

            #make sure we have a valid, active auth token
            userInfo = helperInstance.getUserInfoUsingRequest(flask.request, hasGroups)
            if isinstance(userInfo, Response):
                return userInfo
            
            sys_acct = False
            if "is_system_account" in userInfo: sys_acct = userInfo['is_system_account'] 
            
            #check that auth is in required scope
            tScopes = []
            if hasGroups and sys_acct is False: tScopes.append(GLOBUS_GROUP_SCOPE)
            if scopes is not None:
                if isinstance(scopes, list): tScopes.extend(scopes)
                else: tScopes.append(scopes)
                tScopes = [x.lower() for x in tScopes]
                tScopes = [x.strip() for x in tScopes]
            if len(tScopes) > 0:
                for scope in tScopes:
                    if scope not in userInfo['hmscopes']:
                        msg = "Not in user scope " + scope
                        if scope == GLOBUS_GROUP_SCOPE:
                            msg = msg + " which is required for access to user groups"
                        return Response(msg, 403)
            
            #check for group access
            if hasGroups:
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
    
    def __init__(self, clientId, clientSecret):
        global helperInstance
        if helperInstance is not None:
            raise Exception("An instance of singleton AuthHelper exists already.  Use AuthHelper.instance() to retrieve it")
        
        if clientId is None or clientSecret is None or string_helper.isBlank(clientId) or string_helper.isBlank(clientSecret):
            raise Exception("Globus client id and secret are required in AuthHelper")
        
        self.applicationClientId = clientId
        self.applicationClientSecret = clientSecret
        AuthCache.setProcessSecret(re.sub(r'[^a-zA-Z0-9]', '', clientSecret))
        if helperInstance is None:
            helperInstance = self
        
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
        tokenResp = self.getAuthorizationTokens(httpReq.headers)
        if isinstance(tokenResp, Response):
            return tokenResp;

        if isinstance(tokenResp, dict):
            if getGroups and not 'nexus_token' in tokenResp:
                return Response("Nexus token required to get group information.")
            elif 'nexus_token' in tokenResp:
                return self.getUserInfo(tokenResp['nexus_token'], getGroups)
            elif 'auth_token' in tokenResp:
                return self.getUserInfo(tokenResp['auth_token'], getGroups)
            elif 'transfer_token' in tokenResp:
                return self.getUserInfo(tokenResp['transfer_token'], getGroups)
            else:
                return Response("A valid token was not found in the MAuthorization header") 
        else:
            return self.getUserInfo(tokenResp, getGroups)
    
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
    #if public access and no token just {"data_access_level":"level"} dictionary is returned
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
            if 'nexus_token' in tokenResp:
                user_info = self.getUserInfo(tokenResp['nexus_token'], True)
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
            protected_group_id = self.groupNameToId('HUBMAP-PROTECTED-DATA')['uuid']
            read_id = self.groupNameToId('HuBMAP-READ')['uuid']
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

class AuthCache:
    cache = {}
    userLock = threading.RLock()
    groupLock = threading.RLock()
    groupIdByName = None
    roleIdByName = None
    groupsById = {}
    rolesById = {}
    groupLastRefreshed = None
    groupJsonFilename = file_helper.ensureTrailingSlash(os.path.dirname(os.path.realpath(__file__))) + 'hubmap-globus-groups.json'
    roleJsonFilename = file_helper.ensureTrailingSlash(os.path.dirname(os.path.realpath(__file__))) + 'hubmap-globus-roles.json'
    procSecret = None
    processUserFilename = file_helper.ensureTrailingSlash(os.path.dirname(os.path.realpath(__file__))) + 'hubmap-process-user.json'
    processUser = None
         
    @staticmethod
    def setProcessSecret(secret):
        if AuthCache.procSecret is None:
            AuthCache.procSecret = secret

    @staticmethod
    def getHMGroups():
        with AuthCache.groupLock:
            now = datetime.datetime.now()
            diff = None
            if AuthCache.groupLastRefreshed is not None:
                diff = now - AuthCache.groupLastRefreshed
            if diff is None or diff.days > 0 or diff.seconds > TOKEN_EXPIRATION:
                groupIdByName = {}                    
                #groupsById = {}                    
                with open(AuthCache.groupJsonFilename) as jsFile:
                    groups = json.load(jsFile)
                    for group in groups:
                        if 'name' in group and 'uuid' in group and 'generateuuid' in group and 'displayname' in group and not string_helper.isBlank(group['name']) and not string_helper.isBlank(group['uuid']) and not string_helper.isBlank(group['displayname']):
                            group_obj = {'name' : group['name'].lower().strip(), 'uuid' : group['uuid'].lower().strip(),
                                         'displayname' : group['displayname'], 'generateuuid': group['generateuuid']}
                            if 'tmc_prefix' in group:
                                group_obj['tmc_prefix'] = group['tmc_prefix']
                            groupIdByName[group['name'].lower().strip()] = group_obj
                            AuthCache.groupsById[group['uuid']] = group_obj
            return groupIdByName

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
    def __userGroups(token):
        if token == AuthCache.procSecret:
            return ["5777527e-ec11-11e8-ab41-0af86edb4424"]
        getHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + token
        }
        url='https://nexus.api.globusonline.org/groups?fields=id,name,description,group_type,has_subgroups,identity_set_properties&for_all_identities=false&include_identaaaaay_set_properties=false&my_statuses=active'
        response = requests.get(url, headers=getHeaders)
        if response.status_code != 200:
            return Response("Unable to get user groups\n"+response.text, 500)
        try:
            jsonResp = response.json()
            ids = []
            for value in jsonResp:
                if 'id' in value:
                    ids.append(value['id'].lower().strip())
            return ids
        except Exception as e:
            return Response('Unable to parse json response while gathering user groups\n' + str(e), 500)

    @staticmethod
    def __userInfo(applicationKey, authToken, getGroups=False):
        if authToken == AuthCache.procSecret:
            if AuthCache.processUser is None:
                with open(AuthCache.processUserFilename) as jsFile:
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
                    groups = AuthCache.__userGroups(authToken)
                    if isinstance(groups, Response):
                        return groups
                    grp_list = []
                    role_list = []
                    for group_uuid in groups:
                        if group_uuid in AuthCache.groupsById:
                            grp_list.append(group_uuid)
                        elif group_uuid in AuthCache.rolesById:
                            role_list.append(group_uuid)
                    jsonResp['hmgroupids'] = grp_list
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
    group_list = AuthCache.getHMGroups()
    print(group_list)
    