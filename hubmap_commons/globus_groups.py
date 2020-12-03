import json
from cachetools import cached, TTLCache
import functools
import logging

# HuBMAP commons
from hubmap_commons import string_helper
from hubmap_commons.hm_auth import AuthHelper, AuthCache

# LRU Cache implementation with per-item time-to-live (TTL) value
# with a memoizing callable that saves up to maxsize results based on a Least Frequently Used (LFU) algorithm
# with a per-item time-to-live (TTL) value
# The maximum integer number of entries in the cache queue: 128
# Expire the cache after the time-to-live (seconds): two hours, 7200 seconds
cache = TTLCache(128, ttl=7200)

logger = logging.getLogger(__name__)

"""
Load the globus groups information json file

Returns
-------
dict
    A dict containing the groups details
"""
@cached(cache)
def get_globus_groups_info():
    with open(AuthCache.groupJsonFilename) as file:
        groups = json.load(file)

        logger.info("Globus groups json file loaded successfully")

        groups_by_id = {}
        groups_by_name = {}
        groups_by_tmc_prefix = {}

        for group in groups:
            if 'name' in group and 'uuid' in group and 'generateuuid' in group and 'displayname' in group and not string_helper.isBlank(group['name']) and not string_helper.isBlank(group['uuid']) and not string_helper.isBlank(group['displayname']):
                group_obj = {
                    'name' : group['name'].lower().strip(), 
                    'uuid' : group['uuid'].lower().strip(),
                    'displayname' : group['displayname'], 
                    'generateuuid': group['generateuuid']
                }

                if 'tmc_prefix' in group:
                    group_obj['tmc_prefix'] = group['tmc_prefix']

                    if 'uuid' in group and 'displayname' in group and not string_helper.isBlank(group['uuid']) and not string_helper.isBlank(group['displayname']):
                        group_info = {}
                        group_info['uuid'] = group['uuid']
                        group_info['displayname'] = group['displayname']
                        group_info['tmc_prefix'] = group['tmc_prefix']
                       
                        groups_by_tmc_prefix[group['tmc_prefix'].upper().strip()] = group_info
                
                groups_by_name[group['name'].lower().strip()] = group_obj
                groups_by_id[group['uuid']] = group_obj

                logger.debug("======groups_by_id======")
                logger.debug(groups_by_id)

                logger.debug("======groups_by_name======")
                logger.debug(groups_by_name)

                logger.debug("======groups_by_tmc_prefix======")
                logger.debug(groups_by_tmc_prefix)
        
        # Wrap the final data
        globus_groups = {
            'by_id': groups_by_id,
            'by_name': groups_by_name,
            'by_tmc_prefix': groups_by_tmc_prefix
        }
        
        return globus_groups

"""
Clear or invalidate the function cache even before it expires
"""
def clear_globus_groups_cache():
    logger.info("Globus groups json cache cleared")
    cache.clear()