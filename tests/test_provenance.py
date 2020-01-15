'''
Created on Jan 15, 2020

@author: chb69
'''
import unittest
import configparser
import sys
import os

from hubmap_commons.provenance import Provenance
from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.entity import Entity


class TestProvenance(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def test_get_provenance_history(self):
        # in general, the display id (ex: TEST0010-LK-1-1-1) will dictate the corresponding
        # number of entity entries returned.  Basically, the entity entry count should equal the number of hyphens 
        # in the display id plus one.  For example, TEST0010 will have 1 entity entry.  TEST0010-LK will have two: one for the donor TEST0010
        # and one for the organ TEST0010-LK.
        confdata = Provenance.load_config_file()
        conn = Neo4jConnection(confdata['neo4juri'], confdata['neo4jusername'], confdata['neo4jpassword'])
        driver = conn.get_driver()
        donor_list = Entity.get_entities_by_type(driver, 'Donor')
        prov = Provenance(confdata['appclientid'], confdata['appclientsecret'], confdata['UUID_WEBSERVICE_URL'])
        
        # walk through the first 5 donors and test them
        for x in range(6):
            history_data_str = prov.get_provenance_history(driver, donor_list[x])
            history_data = eval(history_data_str)
            self.assertEqual(len(history_data['entity']), 1)

        sample_list = Entity.get_entities_by_type(driver, 'Sample')
        # walk through the first 20 samples and test them
        for x in range(20):
            sample_item = Entity.get_entity(driver, sample_list[x])
            history_data_str = prov.get_provenance_history(driver, sample_list[x])
            history_data = eval(history_data_str)
            display_id = sample_item['hubmap_identifier']
            hypen_count = str(display_id).count('-')
            self.assertEqual(len(history_data['entity']), hypen_count+1)
            


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()