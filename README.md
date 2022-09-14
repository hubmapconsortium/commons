# commons

[![PyPI version](https://badge.fury.io/py/hubmap-commons.svg)](https://badge.fury.io/py/hubmap-commons)

This repository contains the code supporting several HuBMAP restful microservices.

### Getting Started

The hubmap commons library is available through PyPi via the command:

```bash
pip install hubmap-commons
```

The hubmap-commons requirements can be found [here](requirements.txt)



### Contents

The code includes:

* **~~activity.py~~ (deprecated)** creates Cyhper statements for creating and getting HuBMAP Activitiy node types

* **autherror.py** a class to handle authentiation errors

* **~~entity.py~~(deprecated)** a base class that executes many Cypher queries against Neo4j to return information about the HuBMAP Entity nodes

* **file_helper.py** contains methods to execute files and parse files

* **globus_file_helper.py** contains methods for creating Globus directories

* **hm_auth.py** contains several methods and classes relating to system security

* **hubmap_const.py** a file that maintains the names and strings used in the code and the Neo4j system

* **~~neo4j_connection.py~~(deprecated)** provides connections to Neo4j and some generic Cypher statements (e.g. CREATE and UPDATE)

* **neo4j_driver.py** creates a neo4j.Driver singleton instance

* **~~provenance.py~~(deprecated)** extracts provenance related information from a token

* **schema_tools.py** checks a JSON structure vs a schema definition using two main methods. 

    - `check_json_matches_schema(jsondata, schema_filename: str, base_path: str = "", base_uri: str = "")`
    Checks the given json data against the jsonschema in the given schema file, raising an exception on error. The exception text includes one or more validation error messages.
    - `assert_json_matches_schema(jsondata, schema_filename: str, base_path: str = "", base_uri: str = "")` 
    Raises AssertionError if the schema in schema_filename is invalid, or if the given jsondata does not match the schema.
    
* **stirng_helper.py** contains several string related functions (listToCommaSeparated, getYesNo, etc.)

* **test_ws.py** contains a test Web Service.  This service can be run by copying hubmap_commons/common_app.conf.example to hubmap_commons/common_app.conf and providing a Globus client id and secret (available at https://developers.globus.org) then directly running test_ws.py from the hubmap_commons/ directory.  The service has a useful /login method that can be used to generate Globus auth tokens for testing.  Note: For much of HuBMAP a Globus "nexus" token used to access the globus Nexus APIs.  To generate a nexus token the Client ID must be authorized for this.  Client IDs are available from the developers of this repository to generate nexus tokens for use against HuBMAP APIs.

* **~~uuid_generator.py~~(deprecated)** this is a wrapper for calls to the /hmuuid Web Service
