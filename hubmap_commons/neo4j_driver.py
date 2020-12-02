from neo4j import GraphDatabase, Driver

# Python modules are first-class runtime objects, 
# they effectively become singletons, 
# initialized at the time of first import.

# Two leading underscores signals to Python that 
# you want the variable to be "private" to the module
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
def get_instance(uri, username, password):
    # Specify as module-scope variable
    global __NEO4J_DRIVER__

    if __NEO4J_DRIVER__ is None:
        __NEO4J_DRIVER__ = GraphDatabase.driver(uri, auth=(username, password))
    
    return __NEO4J_DRIVER__

"""
Shut down, closing any open connections in the pool
"""
def close():
    # Specify as module-scope variable
    global __NEO4J_DRIVER__

    if isinstance(__NEO4J_DRIVER__, Driver):
        __NEO4J_DRIVER__.close()
        __NEO4J_DRIVER__ = None
    else:
        raise TypeError("The private module variable '__NEO4J_DRIVER__' is not a neo4j.Driver object")
        