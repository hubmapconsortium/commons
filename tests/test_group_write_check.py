from hubmap_commons.hm_auth import AuthHelper
from hubmap_commons.exceptions import HTTPException
APP_CLIENT_ID = '21f293b0-5fa5-4ee1-9e0e-3cf88bd70114'                                                                  
APP_CLIENT_SECRET = 'gimzYEgm/jMtPmNJ0qoV11gdicAK8dgu+yigj2m3MTE=' 

helper = AuthHelper(APP_CLIENT_ID, APP_CLIENT_SECRET)

#provide nexus tokens for the following, BE CAREFUL TO NOT CHECK THESE IN!

#member of HuBMAP-Read group only
read_only = ''

#member of HuBMAP-Read and HuBMAP-Testing groups only
test_only = ''

#member of HuBMAP-Read and HuBMAP-Data-Admin groups only
data_admin_only = ''

#member of HuBMAP-Read and all HuBMAP data provider groups
all_write = ''

#member of no HuBMAP groups
nothing = ''

read_group = '5777527e-ec11-11e8-ab41-0af86edb4424'
test_group = '5bd084c8-edc2-11e8-802f-0e368f3075e8'
vandy_group = '73bb26e4-ed43-11e8-8f19-0a7c1eab007a'
invalid_group = '73bb26e4-ed43-11e8-8f19-0a7c1eab007z'


def check_access(token, group_uuid, access, access_msg):
    try:
        if access == helper.check_write_privs(token, group_uuid):
            print(f"PASSED: {access_msg}")
        else:
            print(f"FAILED: {access_msg}")
    except HTTPException:
        if not access:
            print(f"PASSED: {access_msg}")
        else:
            print(f"FAILED: {access_msg}")
            
check_access(read_only, read_group, False, 'read token, read group')
check_access(read_only, test_group, False, 'read token, test group')
check_access(read_only, vandy_group, False, 'read token, vandy group')
check_access(read_only, invalid_group, False, 'read token, invalid group')

check_access(test_only, read_group, False, 'test token, read group')
check_access(test_only, test_group, True, 'test token, test group')
check_access(test_only, vandy_group, False, 'test token, vandy group')
check_access(test_only, invalid_group, False, 'test token, invalid group')

check_access(data_admin_only, read_group, False, 'data admin token, read group')
check_access(data_admin_only, test_group, True, 'data admin token, test group')
check_access(data_admin_only, vandy_group, True, 'data admin token, vandy group')
check_access(data_admin_only, invalid_group, False, 'data admin token, invalid group')

check_access(all_write, read_group, False, 'all write token, read group')
check_access(all_write, test_group, True, 'all write token, test group')
check_access(all_write, vandy_group, True, 'all write token, vandy group')
check_access(all_write, invalid_group, False, 'all write token, invalid group')

check_access(nothing, read_group, False, 'nothing token, read group')
check_access(nothing, test_group, False, 'nothing token, test group')
check_access(nothing, vandy_group, False, 'nothing token, vandy group')
check_access(nothing, invalid_group, False, 'nothing token, invalid group')
            
