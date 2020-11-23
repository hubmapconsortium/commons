'''
Created on November 22, 2020

@author: welling
'''

import requests
import json
import os
import sys
from typing import Union, List, TypeVar, Iterable, Dict, Any
from pprint import pprint
from flask import session
from requests.exceptions import TooManyRedirects
from singleton_metaclass import ClassIsInstanceMeta

BoolOrNone = Union[bool, None]

JSONType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]

class _AssayType(object):
    name: str
    description: str
    primary: bool

    def __init__(self, info: JSONType):
        # Needs to set self.name, self.description, self.primary
        self.name = info['name']
        self.description = info['description']
        self.primary = info['primary']
        pass

    def to_json(self) -> JSONType:
        """
        Returns a JSON-compatible representation of the assay type
        """
        return {'name': self.name, 'primary': self.primary,
                'description': self.description}
    
    def __str__(self):
        return(f'AssayType({self.description})')
    
    def __repr__(self):
        return(f'AssayType({self.to_json()})')


class TypeClient(object, metaclass=ClassIsInstanceMeta):
    
    app_config = {}
    
    def __init__(self, type_webservice_url: str):
        """
        """
        assert 'TYPE_WEBSERVICE_URL' not in self.app_config, 'initialized twice!'
        self.app_config['TYPE_WEBSERVICE_URL'] = type_webservice_url

    def _wrapped_transaction(self, url, data=None, method="GET"):
        try:
            if method=="GET":
                assert data is None, "No message body for GET transactions"
                r = requests.get(url, headers={'Content-Type':'application/json'})
            elif method=="POST":
                r = requests.post(url, headers={'Content-Type':'application/json'},
                                  json=data)
            else:
                raise RuntimeError("Unsupported transaction type")
            if r.ok == True:
                return json.loads(r.content.decode())
            else:
                msg = 'HTTP Response: ' + str(r.status_code) + ' msg: ' + str(r.text) 
                raise Exception(msg)
        except ConnectionError as connerr: # "connerr"...get it? like "ConAir"... chb69 
            pprint(connerr)
            raise connerr
        except TimeoutError as toerr:
            pprint(toerr)
            raise toerr
        except TooManyRedirects as toomany:
            pprint(toomany)
            raise toomany
        except Exception as e:
            pprint(e)
            raise e

    def getAssayType(self, name: str) -> _AssayType:
        url = self.app_config['TYPE_WEBSERVICE_URL'] + 'assayname'
        data = self._wrapped_transaction(url, method='POST', data={'name':name})
        return _AssayType(data)
        print(f'getAssayType({name}) -> {data}')

    def iterAssayNames(self, primary: BoolOrNone = None)-> Iterable[str]:
        url = self.app_config['TYPE_WEBSERVICE_URL'] + 'assaytype?simple=true'
        if primary is not None:
            if primary:
                url += '&primary=true'
            else:
                url += '&primary=false'
        data = self._wrapped_transaction(url)
        for elt in data['result']:
            yield elt

    def iterAssays(self, primary: BoolOrNone = None)-> Iterable[str]:
        url = self.app_config['TYPE_WEBSERVICE_URL'] + 'assaytype?simple=false'
        if primary is not None:
            if primary:
                url += '&primary=true'
            else:
                url += '&primary=false'
        data = self._wrapped_transaction(url)
        for elt in data['result']:
            yield _AssayType(elt)


if __name__ == '__main__':
    try:
        tc = TypeClient("http://localhost:8686/")
        print('all assay names: ',)
        pprint([elt for elt in tc.iterAssayNames()], compact=True)
        print('primary assay names: ',)
        pprint([elt for elt in tc.iterAssayNames(primary=True)], compact=True)
        print('non-primary assay names:')
        pprint([elt for elt in tc.iterAssayNames(primary=False)], compact=True)
        print('primary assay types as str:')
        pprint([str(elt) for elt in tc.iterAssays(primary=True)], compact=True)
        print('non-primary assay types:')
        pprint([elt for elt in tc.iterAssays(primary=False)], compact=True)
        print('testing name translations:')
        for name, note in [('codex', 'this should fail'),
                           ('CODEX', 'this should work'),
                           ('codex_cytokit', 'this is not primary'),
                           ('salmon_rnaseq_bulk', 'this is an alt name'),
                           (['PAS', 'Image Pyramid'],
                            'this is a complex alt name'),
                           (['IMC', 'foo'],
                            'this is an invalid complex alt name')]:
            try:
                assay = tc.getAssayType(name)
                print(f'{name} produced {assay.name} {assay.description}')
                print(f'{assay.to_json()}')
            except Exception as e:
                print(f'{name} ({note}) -> exception {e}')
    except Exception as e:
        pprint(e)
    