import unittest
import configparser
import sys
import os

from hubmap_commons.singleton_metaclass import SingletonMetaClass


class TestSingleton(unittest.TestCase):


    def test_singletonmeta(self):
        class MyClass(object, metaclass=SingletonMetaClass):
            instanceCounter = 0

            def __init__(self):
                self.id = self.instanceCounter
                self.instanceCounter += 1

        inst1 = MyClass()
        inst2 = MyClass()
        self.assertTrue(inst1 is inst2, "Singleton is-ness failed")
        self.assertTrue(inst1.id == inst2.id, "Singleton ids do not match")

#     def setUp(self):
#         self.config = load_config_file()
#         self.conn = Neo4jConnection(self.config['neo4juri'], self.config['neo4jusername'], self.config['neo4jpassword'])
#         self.driver = self.conn.get_driver()
# 
#     def tearDown(self):
#         if self.driver != None:
#             if self.driver.closed() == False:
#                 self.driver.close()

if __name__ == '__main__':
    unittest.main()
