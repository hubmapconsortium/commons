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

        required_keys = ['name', 'uuid', 'generateuuid', 'displayname', 'data_provider']
        non_empty_keys = ['name', 'displayname']
        boolean_keys = ['data_provider']

        for group in groups:
            # A bit data integrity check
            for key in required_keys:
                if key not in group:
                    msg = f'Key "{key}" is required for each object in the globus groups json file'
                    logger.error(msg)
                    raise KeyError(msg)

            for key in non_empty_keys:
                if string_helper.isBlank(group[key]):
                    msg = f'The value of key "{key}" can not be empty string in each object in the globus groups json file'
                    logger.error(msg)
                    raise ValueError(msg)

            for key in boolean_keys:
                if not isinstance(group[key], bool):
                    msg = f'The value of key "{key}" must be a boolean in each object in the globus groups json file'
                    logger.error(msg)
                    raise ValueError(msg)

            # By now all the checks passed, we are good for the business
            group_obj = {
                'name' : group['name'].lower().strip(), 
                'uuid' : group['uuid'].lower().strip(),
                'displayname' : group['displayname'], 
                'generateuuid': group['generateuuid'],
                'data_provider': group['data_provider']
            }

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

"""
Clear or invalidate the function cache even before it expires
"""
def clear_globus_groups_cache():
    logger.info("Globus groups json cache cleared")
    cache.clear()