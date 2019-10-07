# commons
This repository contains the code supporting several HuBMAP restful microservices.

The code includes:

* **activity.py** creates Cyhper statements for creating and getting HuBMAP Activitiy node types

* **autherror.py** a class to handle authentiation errors

* **entity.py** a base class that executes many Cypher queries against Neo4j to return information about the HuBMAP Entity nodes

* **file_helper.py** contains methods to execute files and parse files

* **globus_file_helper.py** contains methods for creating Globus directories

* **hm_auth.py** contains several methods and classes relating to system security

* **hubmap_const.py** a file that maintains the names and strings used in the code and the Neo4j system

* **neo4j_connection.py** provides connections to Neo4j and some generic Cypher statements (e.g. CREATE and UPDATE)

* **provenance.py** extracts provenance related information from a token

* **stirng_helper.py** contains several string related functions (listToCommaSeparated, getYesNo, etc.)

* **test_ws.py** contains a test Web Service method 

* **uuid_generator.py** this is a wrapper for calls to the /hmuuid Web Service
