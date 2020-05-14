
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

def listToCommaSeparated(lst, quoteChar = None, trimAndUpperCase = False):
    return(listToDelimited(lst, ", ", quoteChar, trimAndUpperCase))

def allIndexes(value, character):
    return [i for i, ltr in enumerate(value) if ltr == character]