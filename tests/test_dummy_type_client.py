import unittest
from unittest.mock import patch
from hubmap_commons.type_client import DummyTypeClient
from test_type_client import *

if __name__ == '__main__':
    with patch('test_type_client.TypeClient', DummyTypeClient):
        unittest.main()
