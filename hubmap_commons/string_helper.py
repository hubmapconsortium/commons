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

"""
Convert a string representation of the Python list/dict (either nested or not) to a Python list/dict object
with removing any non-printable control characters if presents.

Note: string representation of Python string can still contain control characters and should not be used by this method
But if a string representation of Python string is used as input by mistake, control characters gets removed as a result.

This was copied from:
https://github.com/hubmapconsortium/entity-api/blob/a832a906124623a889a943c15ff7c8d93f2bb068/src/schema/schema_manager.py#L1666

Parameters
----------
data_str: str
    The string representation of the Python list/dict stored in Neo4j.
    It's not stored in Neo4j as a json string! And we can't store it as a json string
    due to the way that Cypher handles single/double quotes.

Returns
-------
list or dict or str
    The desired Python list or dict object after evaluation or the original string input
"""
def convert_str_literal(data_str):
    if isinstance(data_str, str):
        # First remove those non-printable control characters that will cause SyntaxError
        # Use unicodedata.category(), we can check each character starting with "C" is the control character
        data_str = "".join(char for char in data_str if unicodedata.category(char)[0] != "C")

        # ast uses compile to compile the source string (which must be an expression) into an AST
        # If the source string is not a valid expression (like an empty string), a SyntaxError will be raised by compile
        # If, on the other hand, the source string would be a valid expression (e.g. a variable name like foo),
        # compile will succeed but then literal_eval() might fail with a ValueError
        # Also this fails with a TypeError: literal_eval("{{}: 'value'}")
        try:
            data = ast.literal_eval(data_str)

            if isinstance(data, (list, dict)):
                # The input string literal has been converted to {type(data)} successfully
                return data
        except (SyntaxError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid expression (string value): {data_str} from ast.literal_eval(); "
                             f"specific error: {str(e)}")
    # Skip any non-string data types, or a string literal that is not list or dict after evaluation
    return data_str

"""
Convert a List of dictionaries to the format used in the database to store a
List or dictionary as a string.

Parameters
----------
value_obj : a List or a dict
    The value to be converted to the Python string format used in the database
    to store dictionaries or Lists as a string.

Returns
-------
str
    A string representation of the dictionary or List that can be stored as a string in the database
"""
def convert_py_obj_to_string(value_obj):
    separator = ', '
    node_properties_list = []

    if isinstance(value_obj, list):
        str_val = '['
        first = True
        for ent in value_obj:
            if not first:
                str_val = str_val + separator
            else:
                first = False
            str_val = str_val + convert_py_obj_to_string(ent)
        str_val = str_val + ']'
        return str_val
    else:
        for key, value in value_obj.items():
            if isinstance(value, (int, bool)):
                # Treat integer and boolean as is
                key_value_pair = f"'{key}': {value}"
            elif isinstance(value, str):
                # Special case is the value is 'TIMESTAMP()' string
                # Remove the quotes since neo4j only takes TIMESTAMP() as a function
                if value == 'TIMESTAMP()':
                    key_value_pair = f"'{key}': {value}"
                else:
                    # Escape single quote
                    escaped_str = value.replace("'", r"\'")
                    # Quote the value
                    key_value_pair = f"'{key}': '{escaped_str}'"
            else:
                # Convert list and dict to string, retain the original data without removing any control characters
                # Will need to call schema_manager.convert_str_literal() to convert the list/dict literal back to object
                # Note that schema_manager.convert_str_literal() removes any control characters to avoid SyntaxError
                # Must also escape single quotes in the string to build a valid Cypher query
                escaped_str = str(value).replace("'", r"\'")
                # Also need to quote the string value
                key_value_pair = f"'{key}': '{escaped_str}'"
    
            # Add to the list
            node_properties_list.append(key_value_pair)
    
        # Example: {uuid: 'eab7fd6911029122d9bbd4d96116db9b', rui_location: 'Joe <info>', lab_tissue_sample_id: 'dadsadsd'}
        # Note: all the keys are not quoted, otherwise Cypher syntax error
        node_properties_map = f"{{ {separator.join(node_properties_list)} }}"
    
        return node_properties_map
