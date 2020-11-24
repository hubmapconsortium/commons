'''
Created on November 22, 2020

@author: welling
'''

import requests
import json
from typing import Union, List, TypeVar, Iterable, Dict, Any
from requests.exceptions import TooManyRedirects
from pprint import pprint
from .singleton_metaclass import SingletonMetaClass

BoolOrNone = Union[bool, None]

StringOrNone = Union[str, None]

JSONType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]

class _AssayType(object):
    """
    A class representing a single assay type, accessible only via TypeClient.getAssayType
    and .iterAssays
    """
    name: str
    description: str
    primary: bool

    def __init__(self, info: JSONType):
        """
        The instance is initialized based on a dict provided by TypeClient.  The
        dict must match the format produced by self.to_json().
        """
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
    
    def __str__(self) -> str:
        return(f'AssayType({self.description})')
    
    def __repr__(self)-> str:
        return(f'AssayType({self.to_json()})')
    
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.to_json() == other.to_json()
        else:
            raise NotImplemented()

    def __ne__(self, other):
        if isinstance(other, type(self)):
            return self.to_json() != other.to_json()
        else:
            raise NotImplemented()


class TypeClient(object, metaclass=SingletonMetaClass):
    """
    This is a singleton- only a single instance of this class is ever created.  If
    the constructor is called again, it returns the same instance as before.  This
    is for convenience in initializing the service.
    """
        
    def __init__(self, type_webservice_url:StringOrNone = None):
        """
        type_webservice_url must be provided the first time the constructor is
        called.  Thereafter, all calls return the same instance and are already
        initialized with that service URL.
        """
        if type_webservice_url is None:
            if not (hasattr(self, 'app_config')
                    and 'TYPE_WEBSERVICE_URL' in self.app_config):
                raise RuntimeError('TypeClient has not been initialized')
        else:
            self.app_config = {}
            self.app_config['TYPE_WEBSERVICE_URL'] = type_webservice_url
        

    def _wrapped_transaction(self, url, data=None, method="GET") -> JSONType:
        """
        Provide error and exception handling for requests.
        """
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
        """
        Given an assay name, return the associated assay type.  If a deprecated
        alt-name is provided, the returned assay type will use the up-to-date name.
        """
        url = self.app_config['TYPE_WEBSERVICE_URL'] + 'assayname'
        data = self._wrapped_transaction(url, method='POST', data={'name':name})
        return _AssayType(data)

    def iterAssayNames(self, primary: BoolOrNone = None)-> Iterable[str]:
        """
        Return an iterator over valid assay name strings.
        
        primary: controls the subset of valid names, as follows:
            None or not specified: return all valid names.
            True: return only the names of primary assay types, that is, those for
                which no parent is an assay.
            False: return only the names of non-primary assay types.
        """
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
        """
        Return an iterator over valid assay types.
        
        primary: controls the subset of valid assay types, as follows:
            None or not specified: return all valid types.
            True: return only primary assay types, that is, those for which no 
                parent is an assay.
            False: return only non-primary assay types.
        """
        url = self.app_config['TYPE_WEBSERVICE_URL'] + 'assaytype?simple=false'
        if primary is not None:
            if primary:
                url += '&primary=true'
            else:
                url += '&primary=false'
        data = self._wrapped_transaction(url)
        for elt in data['result']:
            yield _AssayType(elt)

    