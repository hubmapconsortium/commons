import ast
import unicodedata


def isBlank(val):
    if val is None:
        return(True)
    if val.strip() == "":
        return(True)
    return(False)

def isYes(val):
    if isBlank(val): return False
    cVal = val.upper().strip()
    return (cVal == "Y" or cVal == "YES" or cVal == "TRUE")

def getYesNo(msg):
    ans = None
    while ans not in ("y", "n"):
        ans = input(msg)
        ans = ans.lower().strip()
        if ans == "y":
            return True
        elif ans == "n":
            return False     

def padLeadingZeros(int_val, n_chars_with_padding):
    for n in range(1, n_chars_with_padding):
        chk_val = int_val/10**n
        if chk_val < 1:
            return str(str('0') * (n_chars_with_padding - n)) + str(int_val)
    return str(int_val)
    
def listToDelimited(lst, delimitChar = ", ", quoteChar = None, trimAndUpperCase = False):
    delimiter = ""
    rVal = ""
    first = True
    if quoteChar is None:
        quoteChar = ""
    for val in lst:
        if isinstance(val, tuple):
            pVal = val[0]
        else:
            pVal = val
        if trimAndUpperCase:
            pVal = pVal.strip().upper()
        rVal = rVal + delimiter + quoteChar + pVal + quoteChar
        if first:
            first = False
            delimiter = delimitChar
    return(rVal)

def listToTabSeparated(lst, quoteChar = None, trimAndUpperCase = False):
    return(listToDelimited(lst, '\t', quoteChar, trimAndUpperCase))

def listToCommaSeparated(lst, quoteChar = None, trimAndUpperCase = False):
    return(listToDelimited(lst, ", ", quoteChar, trimAndUpperCase))

def allIndexes(value, character):
    return [i for i, ltr in enumerate(value) if ltr == character]

def convert_str_literal(data_str):
    if isinstance(data_str, str):
        """
        This was copied from:
        https://github.com/hubmapconsortium/entity-api/blob/a832a906124623a889a943c15ff7c8d93f2bb068/src/schema/schema_manager.py#L1666
        """
        data_str = "".join(char for char in data_str if unicodedata.category(char)[0] != "C")
        try:
            data = ast.literal_eval(data_str)

            if isinstance(data, (list, dict)):
                logger.info(f"The input string literal has been converted to {type(data)} successfully")
                return data
            else:
                logger.info(f"The input string literal is not list or dict after evaluation, return the original string input")
                return data_str
        except (SyntaxError, ValueError, TypeError) as e:
            msg = f"Invalid expression (string value): {data_str} to be evaluated by ast.literal_eval()"
            logger.exception(msg)
    else:
        # Skip any non-string data types
        return data_str

"""
Build the property key-value pairs to be used in the Cypher clause for node creation/update

Parameters
----------
entity_data_dict : dict
    The target Entity node to be created

Returns
-------
str
    A string representation of the node properties map containing
    key-value pairs to be used in Cypher clause
"""
def build_properties_map(entity_data_dict):
    """
    This was copied from:
    https://github.com/hubmapconsortium/entity-api/blob/1aa6c868df25514f8ac2130005d8080f3fbe229a/src/schema/schema_neo4j_queries.py#L1361
    """
    separator = ', '
    node_properties_list = []

    for key, value in entity_data_dict.items():
        if isinstance(value, (int, bool)):
            # Treat integer and boolean as is
            key_value_pair = f"{key}: {value}"
        elif isinstance(value, str):
            # Special case is the value is 'TIMESTAMP()' string
            # Remove the quotes since neo4j only takes TIMESTAMP() as a function
            if value == 'TIMESTAMP()':
                key_value_pair = f"{key}: {value}"
            else:
                # Escape single quote
                escaped_str = value.replace("'", r"\'")
                # Quote the value
                key_value_pair = f"{key}: '{escaped_str}'"
        else:
            # Convert list and dict to string, retain the original data without removing any control characters
            # Will need to call schema_manager.convert_str_literal() to convert the list/dict literal back to object
            # Note that schema_manager.convert_str_literal() removes any control characters to avoid SyntaxError
            # Must also escape single quotes in the string to build a valid Cypher query
            escaped_str = str(value).replace("'", r"\'")
            # Also need to quote the string value
            key_value_pair = f"{key}: '{escaped_str}'"

        # Add to the list
        node_properties_list.append(key_value_pair)

    # Example: {uuid: 'eab7fd6911029122d9bbd4d96116db9b', rui_location: 'Joe <info>', lab_tissue_sample_id: 'dadsadsd'}
    # Note: all the keys are not quoted, otherwise Cypher syntax error
    node_properties_map = f"{{ {separator.join(node_properties_list)} }}"

    return node_properties_map
