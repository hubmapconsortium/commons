from neo4j import GraphDatabase, Driver

# Python modules are first-class runtime objects, 
# they effectively become singletons, initialized at the time of first import.

# In Python, "privacy" depends on "consenting adults'" levels of agreement, we can't force it.
# A single leading underscore means you're not supposed to access it "from the outside"
_driver = None

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
def instance(uri, username, password):
    # Specify as module-scope variable
    global _driver

    if _driver is None:
        _driver = GraphDatabase.driver(uri, auth=(username, password))
    
    return _driver

"""
Shut down, closing any open connections in the pool
"""
def close():
    # Specify as module-scope variable
    global _driver

    if isinstance(_driver, Driver):
        _driver.close()
        _driver = None
    else:
        raise TypeError("The private module variable '_driver' is not a neo4j.Driver object")
        