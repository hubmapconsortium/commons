from neo4j import GraphDatabase

# Python modules are first-class runtime objects, 
# they effectively become singletons, 
# initialized at the time of first import.
__NEO4J_DRIVER__ = None

"""
Create a neo4j.Driver singleton instance

Parameters
----------
uri : str
    Neo4j server uri, bolt://host[:port]
username : str
    Neo4j username
password : str
    Neo4j password

Returns
-------
neo4j.Driver
    A neo4j.Driver instance
"""
def initialize(uri, username, password):
    # Two leading underscores signals to Python that 
    # you want the variable to be "private" to the module
    global __NEO4J_DRIVER__

    if __NEO4J_DRIVER__ is not None:
        raise RuntimeError("You cannot create another neo4j_driver instance")

    __NEO4J_DRIVER__ = GraphDatabase.driver(uri, auth=(username, password))

    return __NEO4J_DRIVER__
