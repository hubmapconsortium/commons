import traceback
import logging


class HubmapError(Exception):
    def __init__(self, message, errors=''):

        # Call the base class constructor with the parameters it needs
        super().__init__(message)

        # TODO maybe check if errors is None.  If it is None, try using traceback 
        self.errors = errors
        self.message = message
        
    def getJson(self):
        return {'displayMessage' : self.message, 'internalMessage' : self.errors}